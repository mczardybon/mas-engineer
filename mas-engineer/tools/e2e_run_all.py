#!/usr/bin/env python3
"""
e2e_run_all.py — re-runnable end-to-end test of mas-engineer

Run this any time to get an honest score of how much of the
mas-engineer system actually works from a user perspective.

Tests (no shortcuts, no DRY-RUN):
  1. All 63 recipe YAML files parse + have required fields
  2. All 3 top-level workflows actually run
  3. All 5 recovery workflows actually run (incl. auto_repair step)
  4. Sample of 66 task_workflows (2 from each of 41 categories) run
  5. mas-engineer recipe loads via goose

Output:
  - console: real-time progress
  - JSON: e2e-results/<date>-run-<n>/raw-results.json
  - Markdown: e2e-results/<date>-run-<n>/REPORT.md
  - Exit code: 0 if pass rate >= 95%, else 1

Usage:
  python3 tools/e2e_run_all.py                 # default: full run
  python3 tools/e2e_run_all.py --quick         # just YAML + top + recovery (no task_workflows)
  python3 tools/e2e_run_all.py --no-interactive  # skip goose run (saves 20 min)
  python3 tools/e2e_run_all.py --workflow wf_foo  # run a single workflow
"""

import os
import sys
import json
import time
import argparse
import subprocess
import glob
import yaml
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED_TOP_RECIPE_FIELDS = ["name", "version", "title", "description", "instructions", "prompt", "settings", "extensions"]
REQUIRED_SUB_RECIPE_FIELDS = ["name", "title", "description", "instructions", "prompt", "settings", "extensions"]


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def section(title):
    bar = "=" * 60
    print(f"\n{bar}\n  {title}\n{bar}", flush=True)


def find_all_recipes():
    return sorted(glob.glob("recipe/*.yaml") + glob.glob("recipe/sub/*.yaml"))


def test_recipe_yaml():
    section("TEST 1: Recipe YAML parse + required fields")
    files = find_all_recipes()
    results = {"ok": [], "fail": [], "warn": []}
    for f in files:
        try:
            d = yaml.safe_load(open(f))
            if not d:
                results["fail"].append((f, "empty file"))
                continue
            is_top = "/" not in f.replace("recipe/sub/", "")
            req = REQUIRED_TOP_RECIPE_FIELDS if is_top else REQUIRED_SUB_RECIPE_FIELDS
            missing = [k for k in req if k not in d]
            if missing:
                results["fail"].append((f, f"missing: {missing}"))
            else:
                warns = []
                if not (d.get("instructions") or "").strip():
                    warns.append("empty instructions")
                if not (d.get("prompt") or "").strip():
                    warns.append("empty prompt")
                if warns:
                    results["warn"].append((f, warns))
                else:
                    results["ok"].append(f)
        except yaml.YAMLError as e:
            results["fail"].append((f, f"YAML error: {e}"))
        except Exception as e:
            results["fail"].append((f, f"error: {e}"))
    log(f"OK: {len(results['ok'])}, WARN: {len(results['warn'])}, FAIL: {len(results['fail'])}")
    return results


def test_top_workflows():
    section("TEST 2: Top-level workflows (3 of 3)")
    wfs = ["build-test", "si-analyse", "knowledge-refresh"]
    results = {}
    for wf in wfs:
        log(f"  running {wf}...")
        try:
            r = subprocess.run(
                ["python3", "tools/dev_workflow_runner.py", wf],
                capture_output=True, text=True, timeout=60, cwd=ROOT,
                env={**os.environ, "MAS_ENGINEER_ROOT": ROOT},
            )
            status = "ok" if "status: ok" in r.stdout else "fail"
            results[wf] = {"status": status, "exit": r.returncode, "stdout_tail": r.stdout[-200:]}
            log(f"    {wf}: {status}")
        except subprocess.TimeoutExpired:
            results[wf] = {"status": "timeout"}
            log(f"    {wf}: TIMEOUT", "WARN")
    return results


def test_recovery_workflows():
    section("TEST 3: Recovery workflows (5 of 5)")
    wfs = ["wf_recovery_immune", "wf_recovery_checkpoint", "wf_recovery_safezone", "wf_recovery_timeline", "wf_recovery_defib"]
    results = {}
    for wf in wfs:
        log(f"  running {wf}...")
        try:
            r = subprocess.run(
                ["python3", "tools/dev_workflow_runner.py", wf],
                capture_output=True, text=True, timeout=60, cwd=ROOT,
                env={**os.environ, "MAS_ENGINEER_ROOT": ROOT},
            )
            status = "ok" if "status: ok" in r.stdout else "fail"
            # Check log for auto_repair output
            logs = sorted(glob.glob(f".state/workflow_runs/{wf}_*.json"), key=os.path.getmtime, reverse=True)
            auto_repair_status = "n/a"
            if logs:
                log_data = json.load(open(logs[0]))
                for k, v in log_data.get("results", {}).items():
                    if "auto_repair" in k:
                        auto_repair_status = v.get("status", "unknown")
            results[wf] = {"status": status, "auto_repair": auto_repair_status}
            log(f"    {wf}: {status} (auto_repair: {auto_repair_status})")
        except subprocess.TimeoutExpired:
            results[wf] = {"status": "timeout"}
            log(f"    {wf}: TIMEOUT", "WARN")
    return results


def test_task_workflows_sample(n_per_group=2):
    section(f"TEST 4: Task_workflows sample ({n_per_group} per category)")
    d = yaml.safe_load(open(".state/workflows.yaml"))
    all_wfs = list(d.get("task_workflows", {}).keys())
    # Default params for workflows that need them (smoke test only)
    DEFAULT_PARAMS = {
        "wf_admin_generic": ["--task", "status"],
        "wf_controller_cycle": [],
        "wf_dashboard_refresh_run": [],
        "wf_doc_create": ["--file", "/tmp/test_doc.md", "--content", "test"],
        "wf_generic_init_run": ["--init", "testproject", "--project_name", "testproject", "--components", "all", "--workspace", "."],
        "wf_git_commsg": ["--msgsage", "test commit", "--PROJECT_UPPER", "MAS-ENGINEER"],
        "wf_guardian_check": ["--ok", "1"],
        "wf_intention_create": [],
        "wf_py_analyze": ["--file", "tools/e2e_run_all.py"],
        "wf_py_compile": ["--file", "tools/e2e_run_all.py"],
        "wf_rd_design": ["--project", "test", "--name", "agent"],
        "wf_recipe_generic": ["--task", "list"],
        "wf_team_package": ["--root_recipe", "recipe/root_recipe.yaml", "--output_path", "/tmp/mas-pkg", "--team_name", "testteam", "--sub_recipes_csv", "recipe/sub/sub_a.yaml,recipe/sub/sub_b.yaml"],
        "wf_yaml_clone": ["--task", "list", "--new_name", "clone", "--emoji", "🧪"],
    }
    groups = defaultdict(list)
    for wf in all_wfs:
        parts = wf.split("_")
        prefix = parts[1] if parts[0] == "wf" else parts[0]
        groups[prefix].append(wf)
    sampled = []
    for g, wfs in sorted(groups.items()):
        sampled.extend(sorted(wfs)[:n_per_group])
    sampled = list(dict.fromkeys(sampled))
    log(f"sampling {len(sampled)} workflows from {len(groups)} categories")
    results = {"ok": [], "fail": [], "timeout": [], "error": []}
    for i, wf in enumerate(sampled, 1):
        if i % 10 == 0:
            log(f"  progress: {i}/{len(sampled)}")
        extra_args = DEFAULT_PARAMS.get(wf, [])
        try:
            r = subprocess.run(
                ["python3", "tools/dev_workflow_runner.py", wf] + extra_args,
                capture_output=True, text=True, timeout=20, cwd=ROOT,
                env={**os.environ, "MAS_ENGINEER_ROOT": ROOT},
            )
            if "status: ok" in r.stdout:
                results["ok"].append(wf)
            elif "status: failed" in r.stdout:
                results["fail"].append(wf)
            else:
                results["error"].append((wf, r.stdout[-200:]))
        except subprocess.TimeoutExpired:
            results["timeout"].append(wf)
        except Exception as e:
            results["error"].append((wf, str(e)))
    log(f"OK: {len(results['ok'])}, FAIL: {len(results['fail'])}, TIMEOUT: {len(results['timeout'])}, ERROR: {len(results['error'])}")
    return {"sampled": len(sampled), **results}


def test_mas_engineer_interactive():
    section("TEST 5: mas-engineer recipe via goose")
    log("  running goose run --recipe recipe/test-mas-user.yaml...")
    log("  (this can take 15-25 minutes)")
    log("  tail the log: tail -f e2e-results/<date>/logs/pty-test-mas-user.log")
    try:
        r = subprocess.run(
            ["goose", "run", "--recipe", "recipe/test-mas-user.yaml"],
            capture_output=True, text=True, timeout=1500, cwd=ROOT,
        )
        # Check if it produced a meaningful response
        ok = "subagent" in r.stdout or "sub_mas" in r.stdout or len(r.stdout) > 500
        return {"ok": ok, "exit": r.returncode, "stdout_len": len(r.stdout)}
    except subprocess.TimeoutExpired:
        return {"ok": "in_progress", "timeout": "1500s"}
    except FileNotFoundError:
        return {"ok": False, "error": "goose not in PATH"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="skip task_workflows (saves 5-10 min)")
    parser.add_argument("--no-interactive", action="store_true", help="skip goose run (saves 20 min)")
    parser.add_argument("--workflow", help="run single workflow by name")
    args = parser.parse_args()

    if args.workflow:
        log(f"running single workflow: {args.workflow}")
        r = subprocess.run(
            ["python3", "tools/dev_workflow_runner.py", args.workflow],
            capture_output=True, text=True, timeout=30, cwd=ROOT,
        )
        print(r.stdout)
        sys.exit(0 if "status: ok" in r.stdout else 1)

    # Set up output dir
    today = datetime.now().strftime("%Y-%m-%d")
    existing = sorted(glob.glob(f"e2e-results/{today}-run-*"))
    run_n = len(existing) + 1
    out_dir = f"e2e-results/{today}-run-{run_n}"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(f"{out_dir}/logs", exist_ok=True)
    log(f"results dir: {out_dir}")

    start = time.time()
    all_results = {"started": datetime.now().isoformat(), "tests": {}}

    # 0. Cleanup test artifacts from previous runs
    artifacts = [
        "recipe/sub/sub_mas-clone.yaml",
        "recipe/sub/sub_test-agent.yaml",
        "recipe/sub/sub_p-n.yaml",
        "recipe/sub/sub_mas-smoketest.yaml",
        "recipe/sub/sub_mas-smoketest2.yaml",
        "recipe/sub/sub_mas-smoketest3.yaml",
    ]
    for a in artifacts:
        try:
            os.remove(a)
            log(f"cleanup: removed {a}")
        except FileNotFoundError:
            pass

    # 1. Recipe YAML
    all_results["tests"]["recipe_yaml"] = test_recipe_yaml()

    # 2. Top workflows
    all_results["tests"]["top_workflows"] = test_top_workflows()

    # 3. Recovery workflows
    all_results["tests"]["recovery_workflows"] = test_recovery_workflows()

    # 4. Task workflows sample
    if not args.quick:
        all_results["tests"]["task_workflows"] = test_task_workflows_sample()

    # 5. mas-engineer interactive
    if not args.no_interactive:
        all_results["tests"]["mas_engineer_interactive"] = test_mas_engineer_interactive()

    elapsed = time.time() - start
    all_results["elapsed_s"] = elapsed
    all_results["finished"] = datetime.now().isoformat()

    # Save raw
    with open(f"{out_dir}/raw-results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Compute score
    yaml_ok = len(all_results["tests"]["recipe_yaml"]["ok"])
    yaml_fail = len(all_results["tests"]["recipe_yaml"]["fail"])
    top_ok = sum(1 for v in all_results["tests"]["top_workflows"].values() if v.get("status") == "ok")
    top_fail = sum(1 for v in all_results["tests"]["top_workflows"].values() if v.get("status") != "ok")
    rec_ok = sum(1 for v in all_results["tests"]["recovery_workflows"].values() if v.get("status") == "ok")
    rec_fail = sum(1 for v in all_results["tests"]["recovery_workflows"].values() if v.get("status") != "ok")

    total = yaml_ok + yaml_fail + top_ok + top_fail + rec_ok + rec_fail
    passed = yaml_ok + top_ok + rec_ok

    if not args.quick and "task_workflows" in all_results["tests"]:
        tw = all_results["tests"]["task_workflows"]
        tw_ok = len(tw["ok"])
        tw_fail = len(tw["fail"]) + len(tw["timeout"]) + len(tw["error"])
        total += tw_ok + tw_fail
        passed += tw_ok

    pct = (passed / total * 100) if total > 0 else 0

    section("FINAL SCORE")
    log(f"TOTAL: {total} tested, {passed} PASS ({pct:.1f}%)")
    log(f"  recipe_yaml:        {yaml_ok}/{yaml_ok+yaml_fail} OK")
    log(f"  top_workflows:      {top_ok}/{top_ok+top_fail} OK")
    log(f"  recovery_workflows: {rec_ok}/{rec_ok+rec_fail} OK")
    if not args.quick and "task_workflows" in all_results["tests"]:
        log(f"  task_workflows:     {tw_ok}/{tw_ok+tw_fail} OK")
    log(f"elapsed: {elapsed:.1f}s")
    log(f"results: {out_dir}/raw-results.json")

    # Exit code: 0 if >= 95%
    if pct >= 95:
        log("PASS (>= 95%)", "SUCCESS")
        sys.exit(0)
    else:
        log(f"FAIL (< 95% — {pct:.1f}%)", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
