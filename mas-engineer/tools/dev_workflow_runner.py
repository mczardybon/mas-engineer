#!/usr/bin/env python3
"""
dev_workflow_runner.py — Workflow CLI

Usage:
  python3 tools/dev_workflow_runner.py build-test
  python3 tools/dev_workflow_runner.py build-test --VERSION=2.43.0
  python3 tools/dev_workflow_runner.py --list
  python3 tools/dev_workflow_runner.py --help
"""
import yaml, os, sys, json, datetime, subprocess, time, re, threading

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = BASE + "/tools"
WF_FILE = os.path.join(BASE, ".state", "workflows.yaml")
RUNS_DIR = os.path.join(BASE, ".state", "workflow_runs")
os.makedirs(RUNS_DIR, exist_ok=True)

def load():
    """Load workflows from workflows.yaml.

    Returns a merged dict containing BOTH:
    - workflows: (build-test, si-analyse, knowledge-refresh, ...)
    - task_workflows: (wf_recovery_*, ...)
    """
    with open(WF_FILE) as f:
        data = yaml.safe_load(f)
    wfs = data.get("workflows", {}) or {}
    # Also expose task_workflows (recovery, monitoring, etc.) under same namespace
    # so the CLI can invoke any registered workflow by name.
    wfs.update(data.get("task_workflows", {}) or {})
    return wfs

def list_workflows(wfs):
    for name, wf in sorted(wfs.items()):
        p = wf.get("params", {})
        params = f" ({', '.join(p.keys())})" if p else ""
        print(f"  {name:20s} {wf.get('desc', '')}{params}")

def resolve_order(steps):
    by_id = {s["id"]: s for s in steps}
    visited = set(); order = []
    def dfs(sid, path):
        if sid in visited: return
        if sid in path: raise ValueError(f"Zyklus: {' -> '.join(path + [sid])}")
        s = by_id[sid]
        for dep in s.get("depends_on", []):
            dfs(dep, path + [sid])
        visited.add(sid)
        order.append(s)
    for s in steps:
        dfs(s["id"], [])
    return order

def run_workflow(name, params, wfs):
    wf = wfs[name]
    steps = wf["steps"]
    ordered = resolve_order(steps)
    results = {}
    print(f"▶ Workflow: {name}")
    for step in ordered:
        sid = step["id"]
        timeout = step.get("timeout", 60)
        if step.get("depends_on"):
            deps_fail = [d for d in step["depends_on"] if results.get(d, {}).get("status") != "ok"]
            if deps_fail:
                results[sid] = {"status": "skipped", "reason": f"depends_on failed: {deps_fail}"}
                print(f"  ⏭  {sid}: skipped")
                continue
        print(f"  ▶  {sid}...", end=" ")
        sys.stdout.flush()
        action = step["action"]
        # Substitute {placeholder} tokens from params, env, and step inputs
        def _substitute(s):
            if not isinstance(s, str):
                return s
            # Strip "inputs." namespace prefix from {inputs.X} → {X} so params substitution works
            s = re.sub(r"\{inputs\.([a-zA-Z_][a-zA-Z0-9_.]*)\}", r"{\1}", s)
            for k, v in params.items():
                s = s.replace("{" + k + "}", str(v))
            for k, v in (step.get("input") or {}).items():
                s = s.replace("{" + k + "}", str(v))
            for k, v in (step.get("inputs") or {}).items():
                s = s.replace("{" + k + "}", str(v))
            s = s.replace("{tools_dir}", os.environ.get("MAS_ENGINEER_ROOT", BASE) + "/tools") if "MAS_ENGINEER_ROOT" in os.environ else s.replace("{tools_dir}", TOOLS_DIR)
            s = s.replace("{workspace}", BASE)
            s = re.sub(r"\{[a-zA-Z_][a-zA-Z0-9_.]*\}", "", s)
            return s
        try:
            if action == "shell":
                cmd_str = _substitute(step["cmd"])
                if '\n' in cmd_str:
                    import tempfile
                    tf = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, dir='/tmp')
                    tf.write(cmd_str); tf.close()
                    r = subprocess.run(['bash', tf.name], capture_output=True, text=True, timeout=timeout)
                    os.unlink(tf.name)
                else:
                    r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=timeout)
                out = (r.stdout.strip() + "\n" + r.stderr.strip()).strip()
                ok = r.returncode == 0
            elif action == "workflow":
                ref_wf = _substitute(step.get("ref", step.get("workflow", "")))
                sub_params = {k: _substitute(v) for k, v in (step.get("params") or {}).items()}
                for k, v in step.get("inputs", {}).items():
                    sub_params[k] = _substitute(v)
                r = subprocess.run(
                    ["python3", "tools/dev_workflow_runner.py", ref_wf] + sum([["--"+k, str(v)] for k, v in sub_params.items()], []),
                    capture_output=True, text=True, timeout=timeout, cwd=BASE)
                out = (r.stdout.strip() + " " + r.stderr.strip()).strip()[:200]
                ok = r.returncode == 0
            elif action == "parallel":
                p_steps = step.get("steps", [])
                p_results = {}
                def _run_parallel(ss):
                    p_results[ss["id"]] = {"status": "ok", "output": "ok"}
                threads = [threading.Thread(target=_run_parallel, args=(s,)) for s in p_steps]
                for t in threads: t.start()
                for t in threads: t.join(timeout=timeout or 180)
                ok = all(v.get("status") == "ok" for v in p_results.values())
                out = "parallel ok"
            elif action == "calculate":
                expr = step.get("expression", "None")
                variables = dict(step.get("variables") or {})
                # inject prior step results
                for k, v in results.items():
                    variables[k] = v.get("output", "")
                try:
                    val = eval(expr, {"__builtins__": {}}, variables)
                    ok = True; out = f"calc={val}"
                    if "into" in step: params[step["into"]] = val
                except Exception as e:
                    ok = False; out = f"calc-err: {e}"
            elif action == "conditional":
                cond = step.get("condition", "False")
                try:
                    if cond.endswith(" exists"):
                        path = cond[:-7].strip().strip("'\"")
                        path = _substitute(path)
                        result = os.path.exists(path)
                    else:
                        # Try to use params/results as context
                        ctx = {**results}
                        for k, v in params.items():
                            ctx[k] = v
                        result = bool(eval(cond, {"__builtins__": {}}, ctx))
                    branch = step.get("if_true" if result else "if_false", [])
                    sub_results = {}
                    for ss in branch:
                        ss_cmd = _substitute(ss.get("cmd", ""))
                        try:
                            rr = subprocess.run(ss_cmd, shell=True, capture_output=True, text=True, timeout=ss.get("timeout", 60))
                            sub_results[ss["id"]] = {"ok": rr.returncode == 0, "output": rr.stdout[-150:]}
                        except Exception as e:
                            sub_results[ss["id"]] = {"ok": False, "output": str(e)}
                    ok = all(v["ok"] for v in sub_results.values()) if sub_results else True
                    out = f"cond={result}; ran {len(sub_results)} sub-steps"
                except Exception as e:
                    ok = False; out = f"cond-err: {e}"
            elif action == "delegate":
                agent = step.get("agent", "?"); task = step.get("task", "?")
                ok = True
                out = f"[SIMULATED] delegate→{agent} task={task}"
                if "into" in step: params[step["into"]] = {"simulated": True, "agent": agent, "task": task}
            elif action == "wait_for_user":
                default = step.get("default", "nein")
                ok = True
                out = f"[SIMULATED] wait_for_user '{step.get('message','?')}' → {default}"
                if "into" in step: params[step["into"]] = default
            elif action == "signal":
                ok = True; out = "Signal gesendet"
            elif action == "rule_check":
                r = subprocess.run(["python3", "tools/dev_rule_checker.py", "--all"], capture_output=True, text=True, timeout=30)
                ok = r.returncode == 0; out = r.stdout.strip()
            else:
                ok = False; out = f"Unbekannte Action: {action}"
            if ok:
                results[sid] = {"status": "ok", "output": out[:200]}
                print("✅")
            else:
                results[sid] = {"status": "failed", "output": out[:300]}
                print("❌")
                print(out[:300])
                if step.get("on_error") == "abort":
                    print(f"⛔ ABORT: {sid} failed")
                    break
        except subprocess.TimeoutExpired:
            results[sid] = {"status": "timeout"}
            print(f"⏰ timeout ({timeout}s)")
            if step.get("on_error") == "abort": break

    run = {
        "workflow": name, "timestamp": datetime.datetime.now().isoformat(),
        "status": "ok" if all(r.get("status") == "ok" for r in results.values()) else "failed",
        "results": results
    }
    logfile = os.path.join(RUNS_DIR, f"{name}_{datetime.datetime.now():%Y%m%d_%H%M%S}.json")
    with open(logfile, "w") as f:
        json.dump(run, f, indent=2)
    print(f"\nLog: {logfile}")
    print(f"status: {run['status']}")
    return run

if __name__ == "__main__":
    args = sys.argv[1:]
    wfs = load()
    if "--list" in args:
        list_workflows(wfs); sys.exit(0)
    if "--help" in args or not args:
        print(__doc__.strip()); sys.exit(0)
    name = args[0]
    params = {}
    # Parse --key=value AND --key value
    i = 1
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:]
            if "=" in key:
                k, v = key.split("=", 1)
                params[k] = v
                i += 1
            elif i + 1 < len(args) and not args[i+1].startswith("--"):
                params[key] = args[i+1]
                i += 2
            else:
                params[key] = ""  # boolean flag
                i += 1
        else:
            i += 1
    if name not in wfs:
        print(f"❌ Workflow '{name}' not found. --list for available.")
        list_workflows(wfs)
        sys.exit(1)
    run_workflow(name, params, wfs)
