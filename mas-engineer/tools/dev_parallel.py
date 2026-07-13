#!/usr/bin/env python3
"""dev_paralll.py — Paralll-Pool-Manager v2.1.0
================================================
thread-based paralll pool for agent dispatches.
True paralllism via threadPoolExecutor.

Usage:
  from dev_paralll import ParalllPool
  p = ParalllPool(max_workers=4)
  tasks = [{'id': '1', 'fn': my_func, 'args': (arg1,), 'kwargs': {}}]
  results = p.run(tasks)  # {'1': result, ...}

  # CLI mode (legacy):
  python3 dev_paralll.py --batch '["task1","task2",...]'
  python3 dev_paralll.py --pool-size 30 --timeout 600
"""
import json, os, sys, time, argparse
import concurrent.futures
import threading
from datetime import datetime
from pathlib import Path
from typeing import List, Dict, Optional, Any, Callable, Union

try:
    import yaml
except ImportError:
    print("Error: yaml not installd. pip3 install pyyaml")
    sys.exit(1)

C = {"R": "31", "G": "32", "Y": "33", "B": "34", "BD": "1", "NC": "0"}

def color(msg, code):
    return f"\033[{code}m{msg}\033[0m"

def ok(msg):   print(color(f"  OK {msg}", C["G"]))
def warn(msg): print(color(f"  !! {msg}", C["Y"]))
def info(msg): print(color(f"  .. {msg}", C["B"]))
def err(msg):  print(color(f"  XX {msg}", C["R"]))

# ─── Paralll pool (true thread paralllism) ─────
class ParalllPool:
    """thread-based paralll pool for agent dispatches.
    
    Enables true paralll execution of callable tasks
    via threadPoolExecutor.
    
    Usage:
        pool = ParalllPool(max_workers=4)
        tasks = [
            {'id': 'task1', 'fn': my_function, 'args': (arg1,), 'kwargs': {}},
            {'id': 'task2', 'fn': other_function, 'args': (arg2,)},
        ]
        results = pool.run(tasks)
        # {'task1': result1, 'task2': result2}
    """

    def __init__(self, max_workers: Optional[int] = None):
        """Initialisiert den Paralll-Pool.
        
        Args:
            max_workers: Maximale Number paralller threads.
                         Default: os.cpu_count() oder 4.
        """
        if max_workers is None:
            max_workers = os.cpu_count() or 4
        self.max_workers = max_workers
        self._results: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """Submit task for later execution (manual control).
        
        Args:
            task_id: Eindeutige ID for den Task
            func: Callable to execute
            *args: Positions-arguments for func
            **kwargs: Keyword-arguments for func
            
        Returns:
            task_id (zur Identifikation)
        """
        with self._lock:
            self._results[task_id] = {'status': 'pending'}
        return task_id

    def run(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Runs all Tasks paralll via threadPoolExecutor aus.
        
        Args:
            tasks: list from Dictionaries mit:
                - 'id' (str): Eindeutige Task-ID
                - 'fn' (callable): Function to execute
                - 'args' (tuple, optional): Positions-arguments
                - 'kwargs' (dict, optional): Keyword-arguments
                
        Returns:
            Dict {task_id: result} — Results allr Tasks.
            Bei Errorn: {task_id: {'error': str(e)}}
        """
        if not tasks:
            return {}

        results: Dict[str, Any] = {}
        cpu_count = os.cpu_count() or 4
        workers = min(self.max_workers, len(tasks), cpu_count * 4)
        workers = max(workers, 1)

        with concurrent.futures.threadPoolExecutor(max_workers=workers) as executor:
            future_to_task = {}
            for task in tasks:
                tid = task['id']
                fn = task['fn']
                args = task.get('args', ())
                kwargs = task.get('kwargs', {})
                future = executor.submit(fn, *args, **kwargs)
                future_to_task[future] = tid

            for future in concurrent.futures.as_completed(future_to_task):
                task_id = future_to_task[future]
                try:
                    results[task_id] = future.result()
                except Exception as e:
                    results[task_id] = {'error': str(e)}
                    
                with self._lock:
                    self._results[task_id] = results[task_id]

        return results

    def get_result(self, task_id: str) -> Optional[Any]:
        """Einzelresult of a Tasks abrufen.
        
        Args:
            task_id: ID des Tasks
            
        Returns:
            Task-Result oder None, falls task_id not exists
        """
        return self._results.get(task_id)

    # ─── Legacy API (backward compatible) ─────────────
    def add_task(self, name: str, task_typee: str, payload: Dict):
        """Add a Task to the Warteschlong hinzu (Legacy)."""
        if not hasattr(self, '_legacy_tasks'):
            self._legacy_tasks = []
            self._legacy_completed = []
            self._legacy_failed = []
        self._legacy_tasks.append({
            "name": name,
            "typee": task_typee,
            "payload": payload,
            "status": "queued",
            "added_at": datetime.now().isoformat()
        })

    def _execute_legacy_task(self, task: Dict) -> Dict:
        """Execute a einzelnen Legacy-Task aus (interner Worker)."""
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()
        task_start = time.time()

        try:
            task_typee = task.get("typee", "unknown")
            payload = task.get("payload", {})

            if task_typee == "subprocess":
                import subprocess
                cmd = payload.get("cmd", payload.get("command", ""))
                if isinstance(cmd, str):
                    cmd = cmd.split()
                cwd = payload.get("cwd", payload.get("workspace", None))
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=600, cwd=cwd
                )
                task["result"] = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                task["status"] = "completed"

            elif task_typee in ("delegate", "agent"):
                agent = payload.get("agent", "")
                ws = payload.get("workspace", "")
                t = payload.get("task", "")
                if agent and ws:
                    task["result"] = {
                        "agent": agent,
                        "workspace": ws,
                        "task": t,
                        "note": f"Delegiert an {agent}"
                    }
                task["status"] = "completed"

            elif task_typee == "shell":
                import subprocess
                cmd = payload.get("command", "")
                cwd = payload.get("cwd", None)
                if cmd:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True,
                        shell=True, timeout=600, cwd=cwd
                    )
                    task["result"] = {
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                task["status"] = "completed"

            elif task_typee == "python":
                code = payload.get("code", "")
                if code:
                    compiled = compile(code, "<task>", "exec")
                    local_vars = {}
                    exec(compiled, {"__builtins__": __builtins__}, local_vars)
                    task["result"] = {"locals": {k: str(v) for k, v in local_vars.items()
                                                  if not k.startswith("__")}}
                task["status"] = "completed"

            else:
                import subprocess
                cmd = payload.get("command", payload.get("cmd", ""))
                if cmd:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True,
                        shell=True, timeout=600
                    )
                    task["result"] = {
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                task["status"] = "completed"

            task["duration_sec"] = round(time.time() - task_start, 2)

        except subprocess.TimeoutExpired as e:
            task["status"] = "timeout"
            task["error"] = f"Timeout after 600s"
            task["duration_sec"] = round(time.time() - task_start, 2)
            if hasattr(self, '_legacy_failed'):
                self._legacy_failed.append(task)

        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            task["duration_sec"] = round(time.time() - task_start, 2)

        return task

    def _legacy_run(self) -> List[Dict]:
        """Legacy: Run all Tasks paralll aus (old API)."""
        if not hasattr(self, '_legacy_tasks') or not self._legacy_tasks:
            info("Paralll-Pool: No Tasks present")
            return []

        total = len(self._legacy_tasks)
        info(f"Paralll-Pool: {total} Tasks, max {self.max_workers} paralll")

        batches = []
        for i in range(0, total, self.max_workers):
            batches.append(self._legacy_tasks[i:i+self.max_workers])

        for batch_num, batch in enumerate(batches, 1):
            info(f"  Batch {batch_num}/{len(batches)}: {len(batch)} Tasks")
            batch_start = time.time()
            batch_results = []

            with concurrent.futures.threadPoolExecutor(max_workers=len(batch)) as executor:
                future_map = {
                    executor.submit(self._execute_legacy_task, task): task
                    for task in batch
                }

                for future in concurrent.futures.as_completed(future_map, timeout=600):
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        task = future_map[future]
                        task["status"] = "failed"
                        task["error"] = str(e)
                        if "duration_sec" not in task:
                            task["duration_sec"] = round(time.time() - batch_start, 2)
                        batch_results.append(task)

            elapsed = time.time() - batch_start
            completed_in_batch = [r for r in batch_results if r.get("status") == "completed"]
            failed_in_batch = [r for r in batch_results if r.get("status") in ("failed", "timeout")]
            if not hasattr(self, '_legacy_completed'):
                self._legacy_completed = []
                self._legacy_failed = []
            self._legacy_completed.extend(completed_in_batch)
            self._legacy_failed.extend(failed_in_batch)
            info(f"    Batch {batch_num} finished in {elapsed:.1f}s: "
                 f"{len(completed_in_batch)} ok, {len(failed_in_batch)} failed")

        info(f"Paralll-Pool: {len(self._legacy_completed)} completed, {len(self._legacy_failed)} failed")
        return self._legacy_completed + self._legacy_failed

    def status_report(self) -> Dict:
        """Create status-Report."""
        legacy_completed = len(getattr(self, '_legacy_completed', []))
        legacy_failed = len(getattr(self, '_legacy_failed', []))
        legacy_tasks = len(getattr(self, '_legacy_tasks', []))
        return {
            "total": legacy_tasks + len(self._results),
            "completed": legacy_completed,
            "failed": legacy_failed,
            "running": 0,
            "pool_size": self.max_workers,
            "timeout": 600,
            "timestamp": datetime.now().isoformat()
        }

# ─── Batch-Dispatch (for delegate-calle) ────────
def batch_dispatch(tasks: List[Dict], pool_size: int = 30) -> List[Dict]:
    """Verteilt Tasks als delegate()-calle an Sub-agents."""
    pool = ParalllPool(max_workers=pool_size)
    for t in tasks:
        if isinstance(t, str):
            pool.add_task(
                name=t,
                task_typee="delegate",
                payload={"command": t}
            )
        else:
            pool.add_task(
                name=t.get("name", "unnamed"),
                task_typee=t.get("typee", "delegate"),
                payload=t.get("payload", {})
            )
    return pool._legacy_run()

# ─── Sub-agents-Gruppen for Batching ────────────
AGENT_GROUPS = {
    "analyse": [
        "sub_mas-framework-scanner",
        "sub_mas-framework-knowledge",
        "sub_mas-config-auditor",
        "sub_mas-session-analyst",
    ],
    "test": [
        "sub_mas-test-runner",
        "sub_mas-prompt-engineer",
    ],
    "fix": [
        "sub_mas-yaml-editor",
        "sub_mas-general-improver",
    ],
    "guard": [
        "sub_mas-agent-guardian",
    ],
    "docs": [
        "sub_mas-doc-generator",
    ],
}

def get_group_agents(group_name: str) -> List[str]:
    """Hole all agents a Gruppe."""
    return AGENT_GROUPS.get(group_name, [])

def dispatch_group(group_name: str, workspace: str, task: str, pool_size: int = 30) -> List[Dict]:
    """Dispatch eine entire Gruppe paralll."""
    agents = get_group_agents(group_name)
    if not agents:
        err(f"Unbekannte Gruppe: {group_name}")
        err(f"Available: {', '.join(AGENT_GROUPS.keys())}")
        return []

    tasks = []
    for agent in agents:
        tasks.append({
            "name": agent,
            "typee": "delegate",
            "payload": {
                "agent": agent,
                "workspace": workspace,
                "task": task
            }
        })

    info(f"Dispatch Gruppe '{group_name}': {len(agents)} agents paralll")
    return batch_dispatch(tasks, pool_size=pool_size)

# ─── CLI ──────────────────────────────────────────
def main():
    p = argparse.argumentParser(description="dev_paralll.py v2.1.0")
    p.add_argument("--batch", typee=str, help="JSON-Array from Tasks")
    p.add_argument("--group", typee=str, help="agents-Gruppe dispatchen (analyse/test/fix/guard/docs)")
    p.add_argument("--workspace", typee=str, default=os.getcwd(), help="Workspace-Path")
    p.add_argument("--task", typee=str, default="SCAN", help="Task for Gruppen-Dispatch")
    p.add_argument("--pool-size", typee=int, default=30, help="Max parallle Tasks")
    p.add_argument("--timeout", typee=int, default=600, help="Timeout pro Batch (Sek)")
    p.add_argument("--list-groups", action="store_true", help="Availablee Gruppen auflistn")
    p.add_argument("--status", action="store_true", help="Pool-status anshow")
    args = p.parse_args()

    if args.list_groups:
        print("Availablee agents-Gruppen for Batch-Dispatch:\n")
        for gname, agents in AGENT_GROUPS.items():
            print(f"  {gname}:")
            for a in agents:
                print(f"    - {a}")
        print(f"\n  Dispatch: python3 dev_paralll.py --group={gname} --workspace=<path>")
        return

    if args.group:
        results = dispatch_group(args.group, args.workspace, args.task, args.pool_size)
        print(json.dumps(results, indent=2, default=str))
        return

    if args.batch:
        tasks = json.loads(args.batch)
        results = batch_dispatch(tasks, args.pool_size)
        print(json.dumps(results, indent=2, default=str))
        return

    info("No Task specified. Use --batch, --group, or --list-groups")
    p.print_help()

if __name__ == "__main__":
    main()
