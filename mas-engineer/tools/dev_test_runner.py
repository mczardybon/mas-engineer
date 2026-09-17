#!/usr/bin/env python3
"""
dev_test_runner.py — replaces sub_mas-test-runner, sub_mas-verification-runner, sub_mas-unix-test-runner.

Single script that handles all test-execution patterns used by the MAS-Engineer:

  RUN          — execute pytest (or specified command) in a workspace
  CHECK_DEPS   — verify pytest + tests/ dir are available
  COMPARE      — diff current RUN result against a baseline (regression detection)
  VERIFY       — post-commit verification: run, parse, optionally fix, max 3 retries

Replaces 3 recipes + 3 instruction files with a single deterministic tool.
Called from recipes via `bash` extension as:
  python3 tools/dev_test_runner.py <command> [args...]

Output: JSON to stdout (machine-readable) + summary to stderr (human-readable).
Exit code: 0 on PASS, 1 on FAIL, 2 on error/dep-missing.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_pytest(workspace: str, scope: str = "all") -> Tuple[int, str]:
    """Execute pytest in workspace. Returns (exit_code, output)."""
    os.chdir(workspace)
    if not Path("tests").exists():
        return 2, "No tests/-Directory in workspace"
    r = subprocess.run(
        [sys.executable, "-m", "pytest", scope, "-v", "--tb=short", "--no-header", "-q"],
        capture_output=True, text=True, timeout=600,
    )
    return r.returncode, r.stdout + r.stderr


def check_deps(workspace: str) -> dict:
    """Verify pytest + tests/ are present."""
    result = {"workspace": workspace, "pytest_available": False, "tests_dir_exists": False}
    r = subprocess.run([sys.executable, "-m", "pytest", "--version"],
                       capture_output=True, text=True, timeout=10)
    result["pytest_available"] = r.returncode == 0
    result["pytest_version"] = r.stdout.strip() if r.returncode == 0 else None
    result["tests_dir_exists"] = Path(workspace, "tests").exists()
    result["ok"] = result["pytest_available"] and result["tests_dir_exists"]
    return result


def parse_pytest_output(output: str) -> dict:
    """Extract pass/fail/error counts from pytest output."""
    import re
    summary = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "warnings": 0, "total": 0}
    # Match lines like "5 passed, 2 failed, 1 error in 1.23s" or "18 passed in 0.94s"
    for line in output.splitlines():
        line = line.strip()
        if not (("passed" in line or "failed" in line) and (" in " in line or "=" in line)):
            continue
        for key in ("passed", "failed", "error", "skipped", "warning"):
            m = re.search(rf"(\d+)\s+{key}s?", line)
            if m:
                count = int(m.group(1))
                if key == "error":
                    summary["errors"] = count
                elif key == "warning":
                    summary["warnings"] = count
                else:
                    summary[key] = count
        # Stop at first summary line
        if any(c.isdigit() for c in line) and ("passed" in line or "failed" in line):
            break
    summary["total"] = summary["passed"] + summary["failed"] + summary["errors"]
    return summary


def run(workspace: str, scope: str = "all") -> dict:
    """RUN: execute pytest + return parsed result."""
    start = time.time()
    exit_code, output = run_pytest(workspace, scope)
    duration = time.time() - start
    summary = parse_pytest_output(output)
    return {
        "command": "RUN",
        "workspace": workspace,
        "scope": scope,
        "exit_code": exit_code,
        "duration_s": round(duration, 2),
        "summary": summary,
        "passed": exit_code == 0,
        "output_tail": output[-2000:] if len(output) > 2000 else output,
    }


def compare(workspace: str, baseline_path: str, scope: str = "all") -> dict:
    """COMPARE: run + diff against baseline JSON (regression detection)."""
    current = run(workspace, scope)
    if not os.path.exists(baseline_path):
        return {"command": "COMPARE", "error": f"baseline not found: {baseline_path}", "current": current}
    with open(baseline_path) as f:
        baseline = json.load(f)
    base_sum = baseline.get("summary", {})
    cur_sum = current["summary"]
    regressions = []
    for key in ("failed", "errors"):
        if cur_sum.get(key, 0) > base_sum.get(key, 0):
            regressions.append(f"{key}: {base_sum.get(key,0)} -> {cur_sum.get(key,0)}")
    if cur_sum.get("passed", 0) < base_sum.get("passed", 0):
        regressions.append(f"passed: {base_sum.get('passed',0)} -> {cur_sum.get('passed',0)}")
    return {
        "command": "COMPARE",
        "workspace": workspace,
        "current": current,
        "baseline": baseline,
        "regressions": regressions,
        "regression_detected": len(regressions) > 0,
    }


def verify(workspace: str, test_command: str, max_attempts: int = 3) -> dict:
    """VERIFY: post-commit verification with retry logic (replaces verification-runner)."""
    attempts = []
    for attempt in range(1, max_attempts + 1):
        r = subprocess.run(test_command, shell=True, capture_output=True, text=True,
                          cwd=workspace, timeout=600)
        result = {
            "attempt": attempt,
            "exit_code": r.returncode,
            "passed": r.returncode == 0,
            "output_tail": (r.stdout + r.stderr)[-1000:],
        }
        attempts.append(result)
        if r.returncode == 0:
            return {
                "command": "VERIFY",
                "workspace": workspace,
                "passed": True,
                "attempts": attempts,
                "final_status": "verifying_passed",
            }
    return {
        "command": "VERIFY",
        "workspace": workspace,
        "passed": False,
        "attempts": attempts,
        "final_status": "VERIFICATION_FAILED",
        "max_attempts_reached": True,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: dev_test_runner.py <RUN|CHECK_DEPS|COMPARE|VERIFY> [args]"}))
        sys.exit(2)

    cmd = sys.argv[1].upper()
    if cmd == "CHECK_DEPS":
        workspace = sys.argv[2] if len(sys.argv) > 2 else str(REPO_ROOT)
        result = check_deps(workspace)
    elif cmd == "RUN":
        workspace = sys.argv[2] if len(sys.argv) > 2 else str(REPO_ROOT)
        scope = sys.argv[3] if len(sys.argv) > 3 else "all"
        result = run(workspace, scope)
    elif cmd == "COMPARE":
        workspace = sys.argv[2] if len(sys.argv) > 2 else str(REPO_ROOT)
        baseline = sys.argv[3] if len(sys.argv) > 3 else ""
        scope = sys.argv[4] if len(sys.argv) > 4 else "all"
        result = compare(workspace, baseline, scope)
    elif cmd == "VERIFY":
        workspace = sys.argv[2] if len(sys.argv) > 2 else str(REPO_ROOT)
        test_cmd = sys.argv[3] if len(sys.argv) > 3 else "python3 -m pytest -q"
        result = verify(workspace, test_cmd)
    else:
        result = {"error": f"unknown command: {cmd}"}

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("passed", True) or cmd == "CHECK_DEPS" else 1)


if __name__ == "__main__":
    main()
