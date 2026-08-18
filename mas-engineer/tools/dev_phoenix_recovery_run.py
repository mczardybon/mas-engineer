#!/usr/bin/env python3
"""dev_phoenix_recovery_run.py — R110-165 phase 1.1

Run the 5 phoenix recovery levels in sequence and publish a
'phoenix.recovery.completed' message to the message queue.

Levels (from sub_mas-phoenix-recovery.yaml):
  1. immune       — YAML preflight (R01-R18 violations)
  2. checkpoint   — checkpoint content + C-01/C-02 fix
  3. safezone     — recovery templates in template/recovery/
  4. timeline     — find best recovery point
  5. defib        — defibrillator (reanimate on death/drift/loop)

Each level is invoked as a task_workflow via
`python3 tools/dev_workflow_runner.py wf_recovery_<level>`.

A level is considered "passed" if the runner exits 0 and does not write
"FAIL"/"CRITICAL" into its per-level log. We collect the outcome of all 5
levels and emit one mq message:

  topic:  phoenix.recovery.completed
  payload: {
    request_id, from, to, timestamp,
    levels: {immune: {ok, exit, log}, ...},
    levels_passed: int,
    levels_total: 5,
    final_status: "ok" | "degraded",
    duration_ms: int,
  }

Exit code 0 if at least one level ran (best-effort), 1 if all 5 failed to
even start, 2 if mq enqueue itself failed.

Usage:
  python3 tools/dev_phoenix_recovery_run.py \
    --request_id r110-165-phoenix-1 \
    --from dashboard --to archive
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
RUNNER = TOOLS_DIR / "dev_workflow_runner.py"
LEVELS = ["immune", "checkpoint", "safezone", "timeline", "defib"]


def _run_level(level: str, request_id: str, level_timeout: int = 120) -> dict:
    """Run a single recovery-level task_workflow. Return {ok, exit, log, cmd}."""
    log_dir = REPO_ROOT / ".mase" / "phoenix_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"phoenix_{level}.log"
    cmd = [
        "python3", str(RUNNER),
        f"wf_recovery_{level}",
        "--request_id", f"{request_id}-level-{level}",
        "--from", "phoenix",
        "--to", level,
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=level_timeout,
        )
        log = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
        log_path.write_text(log)
        ok = proc.returncode == 0
        return {"ok": ok, "exit": proc.returncode, "log": str(log_path), "cmd": " ".join(cmd)}
    except subprocess.TimeoutExpired as e:
        log_path.write_text(f"[TIMEOUT after {level_timeout}s] {e}")
        return {"ok": False, "exit": -1, "log": str(log_path), "cmd": " ".join(cmd),
                "error": "timeout"}
    except Exception as e:  # pragma: no cover
        log_path.write_text(f"[EXCEPTION] {e!r}")
        return {"ok": False, "exit": -2, "log": str(log_path), "cmd": " ".join(cmd),
                "error": repr(e)}


def _enqueue_completion(payload: dict, request_id: str) -> tuple[bool, str]:
    """Enqueue 'phoenix.recovery.completed' via the message_queue CLI."""
    cmd = [
        "python3", str(TOOLS_DIR / "dev_message_queue.py"),
        "--enqueue", "phoenix.recovery.completed", json.dumps(payload),
        "--idempotency-key", f"{request_id}-phoenix-completion",
        "--request-id", request_id,
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return False, f"enqueue exit {proc.returncode}: {proc.stderr.strip()}"
        # enqueue CLI prints the bare msg_id (see tools/dev_message_queue.py L540)
        msg_id = (proc.stdout or "").strip()
        if not msg_id:
            return False, f"enqueue returned empty msg_id. stdout={proc.stdout!r} stderr={proc.stderr!r}"
        return True, msg_id
    except Exception as e:
        return False, f"enqueue exception: {e!r}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--request_id", required=True)
    p.add_argument("--from", dest="frm", default="dashboard")
    p.add_argument("--to", default="archive")
    p.add_argument("--levels", default=",".join(LEVELS),
                   help="comma-separated subset of levels to run (default: all 5)")
    p.add_argument("--dry-run", action="store_true",
                   help="run levels but skip enqueue (for local testing)")
    p.add_argument("--level-timeout", type=int, default=120,
                   help="timeout per level in seconds (default 120)")
    args = p.parse_args()

    request_id = args.request_id
    levels = [l.strip() for l in args.levels.split(",") if l.strip()]
    t0 = time.time()
    level_results = {}
    for level in levels:
        level_results[level] = _run_level(level, request_id, args.level_timeout)
    duration_ms = int((time.time() - t0) * 1000)
    levels_passed = sum(1 for r in level_results.values() if r.get("ok"))
    final_status = "ok" if levels_passed == len(level_results) else "degraded"
    payload = {
        "request_id": request_id,
        "from": args.frm,
        "to": args.to,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "levels": level_results,
        "levels_passed": levels_passed,
        "levels_total": len(level_results),
        "final_status": final_status,
        "duration_ms": duration_ms,
    }

    if args.dry_run:
        print(json.dumps({"payload": payload, "enqueue": "skipped (dry-run)"}, indent=2))
        return 0

    ok, info = _enqueue_completion(payload, request_id)
    if not ok:
        print(json.dumps({"error": "enqueue failed", "detail": info, "payload": payload}, indent=2))
        return 2
    result = {
        "msg_id": info,
        "topic": "phoenix.recovery.completed",
        "levels_passed": levels_passed,
        "levels_total": len(level_results),
        "final_status": final_status,
        "duration_ms": duration_ms,
    }
    print(json.dumps(result, indent=2))
    # Exit 0 if any level passed; 1 only if all 5 failed
    return 0 if levels_passed >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
