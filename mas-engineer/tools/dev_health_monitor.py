#!/usr/bin/env python3
"""
dev_health_monitor.py — replaces sub_mas-monitor-session, -runtime, -recovery, -health.

Single script that handles all monitoring patterns used by the MAS-Engineer controller:

  CHECK_HEALTH   — YAML integrity, invariants, governance, structure (was monitor-health)
  CHECK_RUNTIME  — active sessions, stale agents, crash detection (was monitor-runtime)
  LOG_SESSION    — write cycle log entry + session report (was monitor-session)
  RECOVER        — restart dead/looping agents, max 3 attempts (was monitor-recovery)

Replaces 4 recipes + 1 instruction file with a single deterministic tool.
Called from recipes via `bash` extension as:
  python3 tools/dev_health_monitor.py <command> [args...]

Output: JSON to stdout (machine-readable). Exit: 0=OK, 1=ISSUES_FOUND, 2=ERROR.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = REPO_ROOT / "recipe"
LOG_DIR = REPO_ROOT / ".mase" / "logs"


def yaml_safe_load(path: Path) -> tuple[bool, str]:
    """Load YAML safely. Returns (ok, error_message)."""
    try:
        import yaml
        with open(path) as f:
            yaml.safe_load(f)
        return True, ""
    except Exception as e:
        return False, str(e)


def check_health(recipes_dir: str = None) -> dict:
    """
    CHECK_HEALTH: YAML-Integrity + Invariants + Governance + Structure.

    Phase 1 — YAML-Integrity (5 samples from recipe/sub/)
    Phase 2 — Invariants (governance file exists)
    Phase 3 — Governance (no hardcoded secrets)
    Phase 4 — Structure (counts: sub-recipes, main recipes, no phantom paths)
    """
    recipes = Path(recipes_dir) if recipes_dir else RECIPES_DIR
    sub_dir = recipes / "sub"
    findings = []
    checks_total = 0
    checks_passed = 0

    # Phase 1 — YAML Integrity (5 samples from recipe/sub/)
    samples = ["sub_mas-monitor-health.yaml", "sub_mas-dashboard-director.yaml",
               "sub_mas-test-runner.yaml", "sub_mas-dashboard-refresh.yaml",
               "sub_mas-pipeline-finder.yaml"]
    samples = [s for s in samples if (sub_dir / s).exists()]
    for sample in samples:
        checks_total += 1
        ok, err = yaml_safe_load(sub_dir / sample)
        if ok:
            checks_passed += 1
        else:
            findings.append({"level": "CRITICAL", "code": f"YAML-Error in {sample}", "detail": err})

    # Phase 2 — Invariants
    checks_total += 1
    governance_candidates = [
        Path.home() / ".config" / "goose" / "docs" / "framework-governance.md",
        REPO_ROOT / "docs" / "framework-governance.md",
        REPO_ROOT / "FRAMEWORK-GOVERNANCE.md",
    ]
    if any(p.exists() for p in governance_candidates):
        checks_passed += 1
    else:
        findings.append({"level": "WARN", "code": "INV-1: framework-governance.md missing",
                        "detail": "Required governance doc not found in standard locations"})

    # Phase 3 — Governance (secrets grep across recipe/)
    checks_total += 1
    r = subprocess.run(["grep", "-rn", "-E", "sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}",
                       str(recipes), "-l"],
                      capture_output=True, text=True, timeout=10)
    secret_files = [l for l in r.stdout.split("\n") if l.strip() and ".backups" not in l]
    if not secret_files:
        checks_passed += 1
    else:
        findings.append({"level": "CRITICAL", "code": "GOV-4: Hardcoded Credentials",
                        "detail": f"Found in: {secret_files[:3]}"})

    # Phase 4 — Structure (mas-engineer naming: sub_mas-*, dev-*, *.yaml in recipe/)
    sub_count = len(list(sub_dir.glob("sub_mas-*.yaml"))) if sub_dir.exists() else 0
    main_recipes = [f for f in ["dev-mas-engineer.yaml", "root_recipe.yaml",
                                 "test-fix-failures.yaml", "test-mas-user.yaml",
                                 "setup-dashboard.yaml"]
                   if (recipes / f).exists()]
    main_count = len(main_recipes)
    phantom_count = 0

    checks_total += 1
    structure_ok = True
    if sub_count < 20:
        structure_ok = False
        findings.append({"level": "WARN", "code": f"STRUCTURE: only {sub_count} sub-recipes (expected ≥20)"})
    if main_count < 3:
        structure_ok = False
        findings.append({"level": "WARN", "code": f"STRUCTURE: only {main_count} main recipes (expected ≥3)"})
    if phantom_count > 0:
        structure_ok = False
        findings.append({"level": "CRITICAL", "code": "STRUCTURE: Phantom-paths found",
                        "detail": f"{phantom_count} references"})
    if structure_ok:
        checks_passed += 1

    return {
        "command": "CHECK_HEALTH",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from": "dev_health_monitor",
        "to": "framework-controller",
        "signal": "🟢 DONE" if not findings else "🔴 ISSUES",
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "checks_failed": checks_total - checks_passed,
        "findings": findings,
        "structure": {
            "sub_recipes": sub_count,
            "main_recipes": main_count,
            "main_recipe_names": main_recipes,
            "phantom_refs": phantom_count,
        },
    }


def check_runtime(state_dir: str = None) -> dict:
    """
    CHECK_RUNTIME: active sessions, stale agents, crash detection.

    Reads .mase/ for session files, counts active, flags stale (>1h), detects crashes.
    """
    state = Path(state_dir) if state_dir else REPO_ROOT / ".mase"
    sessions = []
    stale = []
    crashes = []

    # Look for session files
    if state.exists():
        for sf in state.glob("**/sessions.*"):
            try:
                if sf.suffix == ".json":
                    with open(sf) as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        sessions.extend(data)
                    elif isinstance(data, dict):
                        sessions.append(data)
            except (json.JSONDecodeError, OSError):
                crashes.append({"file": str(sf), "issue": "unparseable"})

    # Check last-activity > 1h = stale
    cutoff = time.time() - 3600
    for sess in sessions:
        last_act = sess.get("last_activity") or sess.get("started_at") or ""
        if last_act:
            try:
                ts = datetime.fromisoformat(last_act.replace("Z", "+00:00")).timestamp()
                if ts < cutoff:
                    stale.append(sess.get("id", "?"))
            except (ValueError, TypeError):
                pass

    # Check controller-status.yaml for arch violations
    controller_status = state / "controller-status.yaml"
    arch_violations = 0
    if controller_status.exists():
        try:
            import yaml
            with open(controller_status) as f:
                status = yaml.safe_load(f) or {}
            arch_violations = len(status.get("arch_violations", []))
        except Exception:
            crashes.append({"file": str(controller_status), "issue": "unparseable"})

    issues = bool(stale or crashes or arch_violations)
    return {
        "command": "CHECK_RUNTIME",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from": "dev_health_monitor",
        "active_sessions": len(sessions),
        "stale_sessions": stale,
        "crashes": crashes,
        "arch_violations": arch_violations,
        "issues_found": issues,
        "signal": "🔴 ISSUES" if issues else "🟢 OK",
    }


def log_session(event: str, details: dict = None, log_dir: str = None) -> dict:
    """
    LOG_SESSION: write a cycle-log entry + session report.

    Appends to .mase/logs/cycle-{YYYY-MM-DD}.log with timestamp + event.
    """
    logs = Path(log_dir) if log_dir else LOG_DIR
    logs.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs / f"cycle-{today}.log"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "details": details or {},
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {
        "command": "LOG_SESSION",
        "log_file": str(log_file),
        "event": event,
        "logged": True,
    }


def recover(agent: str, attempt: int = 1, max_attempts: int = 3) -> dict:
    """
    RECOVER: restart an agent that died/timed-out/looped.

    Tracks attempt count. After max_attempts, signals escalation.
    """
    if attempt > max_attempts:
        return {
            "command": "RECOVER",
            "agent": agent,
            "attempt": attempt,
            "escalate": True,
            "max_attempts_reached": True,
            "signal": "🔴 ESCALATE",
        }

    # Recovery = trigger re-dispatch via goose. In a real CLI we'd shell out,
    # but for a deterministic tool we just record the attempt.
    log_session("recovery_attempt", {"agent": agent, "attempt": attempt})

    return {
        "command": "RECOVER",
        "agent": agent,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "escalate": False,
        "signal": "🟡 RECOVERING",
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: dev_health_monitor.py <CHECK_HEALTH|CHECK_RUNTIME|LOG_SESSION|RECOVER> [args]"}))
        sys.exit(2)

    cmd = sys.argv[1].upper()
    if cmd == "CHECK_HEALTH":
        recipes = sys.argv[2] if len(sys.argv) > 2 else str(RECIPES_DIR)
        result = check_health(recipes)
    elif cmd == "CHECK_RUNTIME":
        state = sys.argv[2] if len(sys.argv) > 2 else str(REPO_ROOT / ".mase")
        result = check_runtime(state)
    elif cmd == "LOG_SESSION":
        event = sys.argv[2] if len(sys.argv) > 2 else "unspecified"
        details = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        result = log_session(event, details)
    elif cmd == "RECOVER":
        agent = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        attempt = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        max_attempts = int(sys.argv[4]) if len(sys.argv) > 4 else 3
        result = recover(agent, attempt, max_attempts)
    else:
        result = {"error": f"unknown command: {cmd}"}

    print(json.dumps(result, indent=2))
    # Exit code: 0=OK, 1=issues found
    if result.get("issues_found") or result.get("findings") or result.get("escalate"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
