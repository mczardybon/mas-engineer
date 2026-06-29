#!/usr/am/env python3
"""
dev_workflow_runner.py — Workflow CLI

Nutzung:
  python3 tools/dev_workflow_runner.py build-test
  python3 tools/dev_workflow_runner.py build-test --VERSION=2.43.0
  python3 tools/dev_workflow_runner.py --list
  python3 tools/dev_workflow_runner.py --help
"""
import yaml, os, sys, json, datetime, subprocess, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF_FILE = os.path.join(BASE, ".state", "workflows.yaml")
RUNS_DIR = os.path.join(BASE, ".state", "workflow_runs")
os.makedirs(RUNS_DIR, exist_ok=True)

def load():
    with open(WF_FILE) as f:
        return yaml.safe_load(f)["workflows"]

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
        try:
            if action == "shell":
                cmd_str = step["cmd"]
                if '\n' in cmd_str:
                    import tempfile
                    tf = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, dir='/tmp')
                    tf.write(cmd_str)
                    tf.close()
                    r = subprocess.run(['bash', tf.name], capture_output=True, text=True, timeout=timeout)
                    os.unlink(tf.name)
                else:
                    r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=timeout)
                r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=timeout)
                out = (r.stdout.strip() + "\n" + r.stderr.strip()).strip()
                ok = r.returncode == 0
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
    print(f"Status: {run['status']}")
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
    for a in args[1:]:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            params[k] = v
    if name not in wfs:
        print(f"❌ Workflow '{name}' not found. --list for available.")
        list_workflows(wfs)
        sys.exit(1)
    run_workflow(name, params, wfs)
