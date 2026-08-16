#!/usr/bin/env python3
"""dev_recovery_defib.py — R110-166 phase 2.2 processor for monitor.health.degraded.

Consumed by wf_recovery_defib via dev_mq_consumer.py. Takes a
dev_health_monitor result (the monitor.health.degraded payload)
and routes the problem to the right recovery sub-action.

RECOVERY SUB-ACTIONS
  - gc_stale_in_flight:   if "stale" or "in_flight" issues found
  - replay_dlq:           if dlq_count > 0
  - rebuild_daemon:       if live-daemon.pid is missing/stale
  - refresh_knowledge:    if .mase/rules/.last_refresh is too old
  - noop:                 if has_problem is False (shouldn't happen
                          because we only publish on-degraded)

Each sub-action writes a structured report to
.mase/recovery/log/<request_id>.json so the recovery is audit-able.

DESIGN PRINCIPLES
  - The defib is a CLASSIFIER + ROUTER. It does NOT itself try
    to fix complex problems — that would couple the consumer to
    every recovery domain. The actual fix is delegated to the
    appropriate specialist sub-recipe.
  - Always logs, even on noop (so we can prove the consumer
    was actually invoked).
"""
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = REPO_ROOT / ".mase" / "recovery" / "log"


def _log_dir() -> Path:
    """Resolve the recovery log directory.

    Default: <repo>/.mase/recovery/log (the real install).
    Override: MAS_RECOVERY_LOG_DIR env var (used by tests so each
    test can write to its own tmp dir without polluting the real one).
    """
    override = os.environ.get("MAS_RECOVERY_LOG_DIR")
    if override:
        p = Path(override)
    else:
        p = DEFAULT_LOG_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def process_msg(msg: dict) -> dict:
    """dev_mq_consumer.py entry point. Returns a status dict.

    Payload keys (from dev_health_monitor --publish):
      - request_id, source, command, timestamp
      - has_problem (bool), issues_found (int), findings_count (int)
      - escalate (bool), summary (dict with command-specific fields)
    """
    LOG_DIR = _log_dir()

    payload = msg.get("payload", {})
    request_id = payload.get("request_id") or msg.get("msg_id", "unknown")
    has_problem = bool(payload.get("has_problem"))
    issues_found = int(payload.get("issues_found", 0))
    findings_count = int(payload.get("findings_count", 0))
    command = payload.get("command", "?")
    summary = dict(payload.get("summary") or {})

    actions_taken = []
    if not has_problem:
        actions_taken.append({
            "action": "noop",
            "reason": "has_problem=False (consumer should not have been invoked)",
        })
    else:
        # Classify the problem
        problem_classes = _classify(command, summary)
        for cls in problem_classes:
            action = _dispatch(cls, request_id, summary)
            actions_taken.append(action)

    report = {
        "schema_version": 1,
        "request_id": request_id,
        "source_msg_id": msg.get("msg_id"),
        "source_topic": msg.get("topic"),
        "command": command,
        "has_problem": has_problem,
        "issues_found": issues_found,
        "findings_count": findings_count,
        "actions_taken": actions_taken,
        "defib_outcome": "ok" if actions_taken else "noop",
    }

    log_path = LOG_DIR / f"{request_id}.json"
    with open(log_path, "w") as f:
        json.dump(report, f, indent=2)

    try:
        rel = str(log_path.relative_to(REPO_ROOT))
    except ValueError:
        rel = str(log_path)
    return {
        "log_written": rel,
        "actions_count": len(actions_taken),
        "defib_outcome": report["defib_outcome"],
    }


def _classify(command: str, summary: dict) -> list:
    """Map (command, summary) to a list of problem-class tags.

    Returns 0..N tags, one per detected class. The router will
    dispatch one sub-action per tag.
    """
    classes = []
    # Stale in-flight msgs (MQ-2 housekeeping)
    if summary.get("stale_in_flight_count", 0) > 0:
        classes.append("stale_in_flight")
    # DLQ has messages that need attention
    if summary.get("dlq_count", 0) > 0:
        classes.append("dlq_has_messages")
    # Daemon down
    if command == "CHECK_DAEMON" and not summary.get("daemon_alive", True):
        classes.append("daemon_down")
    # Knowledge base stale
    if summary.get("rules_last_refresh_age_hours", 0) > 168:  # > 1 week
        classes.append("knowledge_stale")
    # Generic fallback
    if not classes:
        classes.append("generic_health_degraded")
    return classes


def _dispatch(problem_class: str, request_id: str, summary: dict) -> dict:
    """Run the appropriate sub-action for problem_class. Returns action dict."""
    if problem_class == "stale_in_flight":
        try:
            import dev_message_queue as mq
            n = mq.gc_stale_in_flight(max_age_sec=300.0)
            return {"action": "gc_stale_in_flight", "reclaimed": n,
                    "problem_class": problem_class}
        except Exception as e:
            return {"action": "gc_stale_in_flight", "error": repr(e),
                    "problem_class": problem_class}
    if problem_class == "dlq_has_messages":
        try:
            import dev_message_queue as mq
            n = mq._dlq_count()
            return {"action": "replay_dlq_dry_run", "dlq_count": n,
                    "problem_class": problem_class,
                    "note": "manual review required before replay"}
        except Exception as e:
            return {"action": "replay_dlq_dry_run", "error": repr(e),
                    "problem_class": problem_class}
    if problem_class == "daemon_down":
        return {"action": "rebuild_daemon", "problem_class": problem_class,
                "note": "delegated to wf_daemon_rebuild (separate workflow)"}
    if problem_class == "knowledge_stale":
        age_h = summary.get("rules_last_refresh_age_hours", 0)
        return {"action": "refresh_knowledge", "age_hours": age_h,
                "problem_class": problem_class,
                "note": "delegated to wf_knowledge_refresh (separate workflow)"}
    # generic_health_degraded — escalate to on-call
    return {"action": "escalate_oncall", "problem_class": problem_class,
            "summary_keys": list(summary.keys())[:10]}


if __name__ == "__main__":
    msg = json.loads(sys.stdin.read() or "{}")
    result = process_msg(msg)
    print(json.dumps(result, indent=2))
