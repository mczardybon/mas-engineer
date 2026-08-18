"""
test_dev_recovery_defib.py — R110-194 (mas-mq branch, MQ phase-2 wiring).

3-test pytest suite for tools/dev_recovery_defib.py. Verifies:
  - dlq_has_messages action: live (default) calls mq.replay_dlq and
    returns action='replay_dlq' with replayed count.
  - dlq_has_messages action: dry-run (summary.dlq_dry_run=True) calls
    mq._dlq_count and returns action='replay_dlq_dry_run' with dlq_count.
  - dry-run leaves the DLQ entries in place (no replay side-effect).

Run with:
    python3 -m pytest tests/test_dev_recovery_defib.py -v
"""
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"

sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent))  # so import dev_recovery_defib finds dev_message_queue

import dev_message_queue as mq  # noqa: E402
import dev_recovery_defib as defib  # noqa: E402


# ─── Per-test MQ root + recovery log dir (isolated) ──────────────

@pytest.fixture
def mq_root(tmp_path, monkeypatch):
    """Isolated MQ root for each test."""
    root = tmp_path / "mq"
    root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(root))
    return root


@pytest.fixture
def recovery_log_dir(tmp_path, monkeypatch):
    """Isolated recovery-log dir for each test."""
    d = tmp_path / "recovery-log"
    monkeypatch.setenv("MAS_RECOVERY_LOG_DIR", str(d))
    return d


def _seed_dlq(topic: str, payload: dict, dlq_path: Path) -> None:
    """Write a single DLQ entry that mq.replay_dlq() will replay.
    MQ uses signals_dlq.ndjson (see tools/dev_message_queue.py:114)."""
    import time as _t
    entry = {
        "msg_id": payload.get("msg_id", "seed-msg-id"),
        "original_topic": topic,
        "payload": payload,
        "max_retries": 3,
        "backoff_schedule": [1, 2, 4, 8],
        "dlq_at": _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
    }
    dlq_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dlq_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _dlq_path(mq_root: Path) -> Path:
    return mq_root / "signals_dlq.ndjson"


# ─── Tests ───────────────────────────────────────────────────────

def test_dlq_replay_live_calls_replay_dlq(mq_root, recovery_log_dir):
    """(1) Without dlq_dry_run, the defib calls mq.replay_dlq() and
    returns action='replay_dlq' with the replayed count."""
    # Seed one DLQ entry on a topic.
    topic = "monitor.health.degraded"
    _seed_dlq(topic, {"foo": "bar"}, _dlq_path(mq_root))

    msg = {
        "msg_id": "test-msg-1",
        "topic": topic,
        "payload": {
            "request_id": "req-replay-live",
            "command": "CHECK_DLQ",
            "has_problem": True,
            "issues_found": 1,
            "findings_count": 1,
            "summary": {"dlq_count": 1},
        },
    }

    result = defib.process_msg(msg)

    # The dispatched action should be 'replay_dlq' (LIVE), with replayed >= 1.
    actions = [a for a in _read_actions(result) if a.get("problem_class") == "dlq_has_messages"]
    assert actions, f"expected dlq_has_messages action in result, got {result}"
    action = actions[0]
    assert action["action"] == "replay_dlq", \
        f"BUG: expected live 'replay_dlq', got {action['action']!r}"
    assert "replayed" in action, f"BUG: live action must report replayed count, got {action}"
    assert action["replayed"] >= 1, f"expected replayed >= 1, got {action.get('replayed')!r}"


def test_dlq_replay_dry_run_reports_only(mq_root, recovery_log_dir):
    """(2) With summary.dlq_dry_run=True, the defib calls mq._dlq_count()
    and returns action='replay_dlq_dry_run' with dlq_count, NO replay."""
    topic = "monitor.health.degraded"
    _seed_dlq(topic, {"foo": "dry"}, _dlq_path(mq_root))

    msg = {
        "msg_id": "test-msg-2",
        "topic": topic,
        "payload": {
            "request_id": "req-replay-dry",
            "command": "CHECK_DLQ",
            "has_problem": True,
            "issues_found": 1,
            "findings_count": 1,
            "summary": {"dlq_count": 1, "dlq_dry_run": True},
        },
    }

    result = defib.process_msg(msg)
    actions = [a for a in _read_actions(result) if a.get("problem_class") == "dlq_has_messages"]
    assert actions, f"expected dlq_has_messages action, got {result}"
    action = actions[0]
    assert action["action"] == "replay_dlq_dry_run", \
        f"expected dry-run 'replay_dlq_dry_run', got {action['action']!r}"
    assert action.get("dlq_count", 0) >= 1, \
        f"dry-run action must report dlq_count >= 1, got {action}"


def test_dlq_dry_run_does_not_replay(mq_root, recovery_log_dir):
    """(3) Dry-run path MUST leave the DLQ entry in place.  This is the
    contract: dry-run reports state without side-effects."""
    topic = "monitor.health.degraded"
    _seed_dlq(topic, {"foo": "preserve-me"}, _dlq_path(mq_root))
    # Snapshot DLQ state before
    with open(_dlq_path(mq_root)) as f:
        before_lines = [l for l in f.read().splitlines() if l.strip()]
    assert len(before_lines) == 1, f"expected 1 DLQ entry, got {len(before_lines)}"

    msg = {
        "msg_id": "test-msg-3",
        "topic": topic,
        "payload": {
            "request_id": "req-dry-no-side-effect",
            "command": "CHECK_DLQ",
            "has_problem": True,
            "issues_found": 1,
            "findings_count": 1,
            "summary": {"dlq_count": 1, "dlq_dry_run": True},
        },
    }

    defib.process_msg(msg)

    with open(_dlq_path(mq_root)) as f:
        after_lines = [l for l in f.read().splitlines() if l.strip()]
    assert len(after_lines) == len(before_lines), \
        f"DRY-RUN SIDE-EFFECT: DLQ changed from {len(before_lines)} to {len(after_lines)} entries"
    assert after_lines == before_lines, "dry-run must not mutate DLQ content"


# ─── helpers ──────────────────────────────────────────────────────

def _read_actions(result: dict) -> list:
    """Read actions from the recovery log file (process_msg returns
    only a short status dict, so the full action list lives in the
    log on disk)."""
    log_rel = result.get("log_written", "")
    # log_written is a repo-relative path; in the test env MAS_RECOVERY_LOG_DIR
    # is an absolute tmp path, so the relative_to in defib falls through
    # and returns the absolute path.  Either way, open it directly.
    log_path = Path(log_rel)
    with open(log_path) as f:
        report = json.load(f)
    return report.get("actions_taken", [])
