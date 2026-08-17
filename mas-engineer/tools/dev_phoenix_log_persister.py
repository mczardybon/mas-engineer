#!/usr/bin/env python3
"""dev_phoenix_log_persister.py — R110-168 phase 3 processor for
phoenix.recovery.completed.

Consumed by wf_phoenix_log_persist via dev_mq_consumer.py. Takes
a dev_phoenix_recovery_run result (the phoenix.recovery.completed
payload) and writes a structured, audit-able per-run log to
.mase/phoenix_logs/<request_id>.json.

DESIGN PRINCIPLES
  - Idempotent: re-running on the same request_id overwrites the
    log file (no duplicate audit entries).
  - Audit: every log includes the source request_id, levels_passed,
    final_status, duration_ms, from/to, and a per-level ok/exit
    digest so the run is reconstructable from a single file.
  - Small: the log is a structured summary, NOT a re-run. The
    per-level wf_recovery_<level>.log files in the same directory
    already hold the verbose run output.
  - Classifier: distinguishes the "ok" case (all 5 levels passed)
    from the "degraded" case (>=1 level failed) and surfaces a
    derived `attention_required` field for downstream dashboards.
    No auto-escalation in phase 3 — that is phase 4 territory
    (re-enqueue to monitor.health.degraded if degraded).

The processor's job is PERSIST, not RESPOND. Recovery actions are
delegated to dev_recovery_defib (consumer of monitor.health.degraded).
"""
import json
import os
import sys
from pathlib import Path

# Re-evaluated at function call time so tests can monkeypatch the
# env var and the directory resolves correctly under isolation.
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = REPO_ROOT / ".mase" / "phoenix_logs"


def _log_dir() -> Path:
    """Resolve the phoenix-log output directory.

    Default: <repo>/.mase/phoenix_logs (the real install, already
    created by dev_phoenix_recovery_run.py on every run).
    Override: MAS_PHOENIX_LOG_DIR env var (used by tests so each
    test can write to its own tmp dir without polluting the real
    one).
    """
    override = os.environ.get("MAS_PHOENIX_LOG_DIR")
    if override:
        p = Path(override)
    else:
        p = DEFAULT_LOG_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def _classify(final_status: str, levels_passed: int, levels_total: int) -> dict:
    """Return a small classification dict derived from the run.

    attention_required is True iff the run was degraded (any level
    failed). The dashboard reads this field to surface a badge
    on the phoenix block. Phase 4 may add auto-escalation here.
    """
    return {
        "final_status": final_status,
        "levels_passed": levels_passed,
        "levels_failed": max(0, levels_total - levels_passed),
        "attention_required": final_status != "ok",
    }


def _digest_levels(levels: dict) -> list:
    """Compact per-level summary for the audit log.

    Input shape (from dev_phoenix_recovery_run.py):
      levels: {
        "immune":     {"ok": bool, "exit": int, "log": str, "cmd": str},
        "checkpoint": {...},
        ...
      }
    Output shape (in the log file):
      [{"level": "immune", "ok": True}, ...]
    """
    out = []
    for level_name, level_result in levels.items():
        if not isinstance(level_result, dict):
            out.append({"level": str(level_name), "ok": False, "error": "non-dict result"})
            continue
        out.append({
            "level": str(level_name),
            "ok": bool(level_result.get("ok", False)),
        })
    return out


def process_msg(msg: dict) -> dict:
    """dev_mq_consumer.py entry point. Returns a status dict.

    The msg is the full MQ message dict (with 'msg_id', 'status',
    'payload', 'topic'). The payload comes from
    dev_phoenix_recovery_run.py (the publisher), with these keys:
      - request_id, from, to, timestamp
      - levels (dict of {level_name: {ok, exit, log, cmd}})
      - levels_passed (int), levels_total (int)
      - final_status ("ok" | "degraded")
      - duration_ms (int)
    """
    LOG_DIR = _log_dir()

    payload = msg.get("payload", {})
    request_id = (
        payload.get("request_id")
        or msg.get("msg_id", "unknown")
    )
    final_status = str(payload.get("final_status", "unknown"))
    levels_passed = int(payload.get("levels_passed", 0))
    levels_total = int(payload.get("levels_total", 0))
    levels = dict(payload.get("levels") or {})

    classification = _classify(final_status, levels_passed, levels_total)

    log_entry = {
        "schema_version": 1,
        "request_id": request_id,
        "source_msg_id": msg.get("msg_id"),
        "source_topic": msg.get("topic"),
        "from": payload.get("from"),
        "to": payload.get("to"),
        "timestamp": payload.get("timestamp"),
        "levels_passed": levels_passed,
        "levels_total": levels_total,
        "final_status": final_status,
        "duration_ms": int(payload.get("duration_ms", 0)),
        "level_digest": _digest_levels(levels),
        "classification": classification,
        # Phase 4 (R110-169): when the run is degraded we
        # auto-escalate by enqueuing a monitor.health.degraded
        # message that the defib consumer classifies as
        # phoenix_recovery_incomplete. Filled below.
        "escalation_msg_id": None,
    }

    log_path = LOG_DIR / f"{request_id}.json"
    with open(log_path, "w") as f:
        json.dump(log_entry, f, indent=2)

    # Phase 4 (R110-169): auto-escalate degraded runs. We import
    # the MQ module here (not at top of file) so that this module
    # remains importable in test environments that do not have the
    # MQ runtime dir set up — same pattern used in
    # dev_recovery_defib._dispatch.
    escalation_msg_id = None
    if classification["attention_required"]:
        try:
            import dev_message_queue as _mq
            failed_levels = [d["level"] for d in _digest_levels(levels)
                             if not d.get("ok", False)]
            esc_payload = {
                "request_id": request_id,
                "source": "dev_phoenix_log_persister",
                "command": "PHOENIX_DEGRADED",
                "has_problem": True,
                "issues_found": classification["levels_failed"],
                "findings_count": 0,
                "summary": {
                    "phoenix_request_id": request_id,
                    "levels_passed": levels_passed,
                    "levels_total": levels_total,
                    "final_status": final_status,
                    "degraded_levels": failed_levels,
                },
            }
            escalation_msg_id = _mq.enqueue(
                "monitor.health.degraded", esc_payload
            )
            # Re-write the log with the escalation msg id
            log_entry["escalation_msg_id"] = escalation_msg_id
            with open(log_path, "w") as f:
                json.dump(log_entry, f, indent=2)
        except Exception as e:
            # Escalation failure must not lose the original log.
            # Surface the error in the return value; defib can
            # still pick up the run via the persisted log file.
            try:
                rel = str(log_path.relative_to(REPO_ROOT))
            except ValueError:
                rel = str(log_path)
            return {
                "log_written": rel,
                "final_status": final_status,
                "levels_passed": levels_passed,
                "attention_required": True,
                "escalation_error": repr(e),
            }

    try:
        rel = str(log_path.relative_to(REPO_ROOT))
    except ValueError:
        rel = str(log_path)
    return {
        "log_written": rel,
        "final_status": final_status,
        "levels_passed": levels_passed,
        "attention_required": classification["attention_required"],
        "escalation_msg_id": escalation_msg_id,
    }


if __name__ == "__main__":
    msg = json.loads(sys.stdin.read() or "{}")
    result = process_msg(msg)
    print(json.dumps(result, indent=2))
