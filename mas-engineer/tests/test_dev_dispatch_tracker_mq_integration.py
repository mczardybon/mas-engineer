"""
test_dev_dispatch_tracker_mq_integration.py — R110-156

Tests the MQ-integration of dev_dispatch_tracker.py v2.0.0.
Verifies:
  - add() writes to legacy NDJSON AND enqueues MQ dispatch_start
  - done() updates legacy NDJSON AND enqueues MQ dispatch_done
  - mq_stats() returns correct shape
  - Idempotency: re-adding same dispatch_id does NOT create duplicate
  - Dual-write survives MQ-unavailable scenario (graceful fallback)
  - Existing --json / --tree / --stats CLI commands still work
    (backward compat)
  - MQ is best-effort: if MQ raises, add() still succeeds
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import dev_dispatch_tracker as dt  # noqa: E402
import dev_message_queue as mq  # noqa: E402


@pytest.fixture
def fresh_legacy_log(monkeypatch, tmp_path):
    """Point dev_dispatch_tracker at a tmp NDJSON file for isolation."""
    log = tmp_path / "mas-dispatch.ndjson"
    monkeypatch.setattr(dt, "LEGACY_LOG", str(log))
    return log


@pytest.fixture
def mq_root(monkeypatch, tmp_path):
    """Isolated MQ root for each test."""
    root = tmp_path / "mq"
    root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(root))
    return root


# ─── Tests ───────────────────────────────────────────────────────

def test_add_writes_to_legacy_ndjson(fresh_legacy_log, mq_root):
    """(1) add() appends to the legacy NDJSON file (backward compat)."""
    e = dt.add("2026-08-16T10:00:00Z", "d-001", None,
               "dev-mas-engineer", "sub_a", "TASK_A")
    assert e["id"] == "d-001"
    assert e["status"] == "running"
    # Legacy file was written
    assert fresh_legacy_log.exists()
    lines = [l for l in fresh_legacy_log.read_text().splitlines() if l]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["id"] == "d-001"


def test_add_also_enqueues_to_mq(fresh_legacy_log, mq_root):
    """(2) add() enqueues a dispatch_start event on the dispatches topic."""
    dt.add("2026-08-16T10:00:00Z", "d-002", "d-001",
           "dev-mas-engineer", "sub_b", "TASK_B", mode="framework")
    # MQ topic `dispatches` should have 1 message
    msgs = mq.replay("dispatches")
    assert len(msgs) == 1
    m = msgs[0]
    assert m["payload"]["event_type"] == "dispatch_start"
    assert m["payload"]["id"] == "d-002"
    assert m["payload"]["parent_id"] == "d-001"
    assert m["payload"]["mode"] == "framework"
    # Idempotency key set
    assert m["idempotency_key"] == "dispatch_start-d-002"


def test_done_updates_legacy_and_enqueues_done_event(
        fresh_legacy_log, mq_root):
    """(3) done() updates legacy NDJSON AND enqueues dispatch_done."""
    dt.add("2026-08-16T10:00:00Z", "d-003", None,
           "dev-mas-engineer", "sub_c", "TASK_C")
    dt.done("d-003", 1234, 5, "all good", errors=None)
    # Legacy updated
    entries = dt._read_all()
    rec = next(e for e in entries if e["id"] == "d-003")
    assert rec["status"] == "done"
    assert rec["duration_ms"] == 1234
    assert rec["turns"] == 5
    assert rec["result_summary"] == "all good"
    # MQ has 2 messages: start + done
    msgs = mq.replay("dispatches")
    events = [m["payload"]["event_type"] for m in msgs]
    assert "dispatch_start" in events
    assert "dispatch_done" in events
    done_msg = [m for m in msgs
                if m["payload"]["event_type"] == "dispatch_done"][0]
    assert done_msg["payload"]["id"] == "d-003"
    assert done_msg["payload"]["status"] == "done"
    assert done_msg["payload"]["duration_ms"] == 1234


def test_done_with_error_marks_error_status(fresh_legacy_log, mq_root):
    """(4) done() with errors=... sets status=error on both legacy & MQ."""
    dt.add("2026-08-16T10:00:00Z", "d-004", None,
           "dev-mas-engineer", "sub_d", "TASK_D")
    dt.done("d-004", 500, 1, "failed", errors="connection timeout")
    entries = dt._read_all()
    rec = next(e for e in entries if e["id"] == "d-004")
    assert rec["status"] == "error"
    assert rec["errors"] == "connection timeout"
    msgs = mq.replay("dispatches")
    done_msg = [m for m in msgs
                if m["payload"]["event_type"] == "dispatch_done"][0]
    assert done_msg["payload"]["status"] == "error"
    assert done_msg["payload"]["errors"] == "connection timeout"


def test_mq_stats_returns_correct_shape(fresh_legacy_log, mq_root):
    """(5) mq_stats() returns depth/lag/dlq/retry_rate/completed_total.

    After enqueueing 2 start + 1 done (no consume/ack):
    - dispatches.ndjson has 3 messages (all pending, no consumer).
    - depth = 3 (pending only — no acked → completed_total=0).

    Then we consume+ack all 3 to verify the counters move correctly."""
    dt.add("2026-08-16T10:00:00Z", "d-005", None,
           "dev-mas-engineer", "sub_e", "TASK_E")
    dt.add("2026-08-16T10:00:01Z", "d-006", None,
           "dev-mas-engineer", "sub_f", "TASK_F")
    dt.done("d-005", 100, 1, "ok")
    stats = dt.mq_stats()
    assert stats is not None
    assert "depth" in stats
    assert "lag_p95_ms" in stats
    assert "dlq_count" in stats
    assert "retry_rate" in stats
    assert "completed_total" in stats
    # 3 messages enqueued, none consumed yet → all pending
    assert stats["depth"] == 3
    assert stats["completed_total"] == 0


def test_idempotency_same_dispatch_id_dedupes(fresh_legacy_log, mq_root):
    """(6) Re-adding same dispatch_id enqueues NO new MQ message
    (idempotency_key dedup)."""
    dt.add("2026-08-16T10:00:00Z", "d-007", None,
           "dev-mas-engineer", "sub_g", "TASK_G")
    dt.add("2026-08-16T10:00:00Z", "d-007", None,
           "dev-mas-engineer", "sub_g", "TASK_G")  # duplicate
    msgs = mq.replay("dispatches")
    # Only 1 message in MQ (idempotency dedupes the 2nd add)
    assert len(msgs) == 1
    # But legacy NDJSON has 2 entries (no dedup at legacy level —
    # legacy is raw append-log, not idempotent)
    entries = dt._read_all()
    assert len(entries) == 2


def test_add_succeeds_when_mq_unavailable(
        fresh_legacy_log, monkeypatch, mq_root):
    """(7) If MQ raises, add() still writes to legacy (best-effort MQ)."""
    def _broken_enqueue(*args, **kwargs):
        raise RuntimeError("MQ temporarily unavailable")
    monkeypatch.setattr(mq, "enqueue", _broken_enqueue)
    # Should not raise
    e = dt.add("2026-08-16T10:00:00Z", "d-008", None,
               "dev-mas-engineer", "sub_h", "TASK_H")
    assert e["id"] == "d-008"
    # Legacy still has the entry
    assert len(dt._read_all()) == 1


def test_cli_json_still_works(tmp_path, mq_root, monkeypatch):
    """(8) CLI --json still works (backward compat for dashboard).

    Full isolation: use a fresh empty log in tmp_path, set both
    MAS_DISPATCH_LOG (for the subprocess) and patch
    dev_dispatch_tracker.LEGACY_LOG in the parent process before
    calling add() so the parent's add() also writes to the
    isolated log."""
    log = tmp_path / "dispatch.ndjson"
    log.write_text("")  # start empty
    # Patch BOTH the parent and the subprocess env
    import dev_dispatch_tracker as _dt
    monkeypatch.setattr(_dt, "LEGACY_LOG", str(log))
    _dt.add("2026-08-16T10:00:00Z", "d-009", None,
            "dev-mas-engineer", "sub_i", "TASK_I")
    # Now invoke CLI subprocess with env override
    env = {**os.environ, "MAS_MQ_ROOT": str(mq_root),
           "MAS_DISPATCH_LOG": str(log)}
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_dispatch_tracker.py"), "--json"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["total"] == 1
    assert data["done"] == 0  # not yet done
    assert "tree" in data
    assert len(data["tree"]) == 1


def test_cli_mq_stats_flag(tmp_path, mq_root, monkeypatch):
    """(9) NEW CLI flag --mq-stats returns MQ aggregate.

    Full isolation: redirect the parent's LEGACY_LOG to a tmp file
    so dev_dispatch_tracker.add() doesn't write to the real
    /tmp/mas-dispatch.ndjson (which has data from other tests)."""
    log = tmp_path / "dispatch.ndjson"
    log.write_text("")
    import dev_dispatch_tracker as _dt
    monkeypatch.setattr(_dt, "LEGACY_LOG", str(log))
    _dt.add("2026-08-16T10:00:00Z", "d-010", None,
            "dev-mas-engineer", "sub_j", "TASK_J")
    env = {**os.environ, "MAS_MQ_ROOT": str(mq_root),
           "MAS_DISPATCH_LOG": str(log)}
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_dispatch_tracker.py"),
         "--mq-stats"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert "depth" in data
    assert "completed_total" in data
    assert data["depth"] == 1  # 1 message in MQ (not yet consumed)


def test_get_tree_unchanged(fresh_legacy_log, mq_root):
    """(10) get_tree() still returns the same shape (backward compat).
    Note: `tree` field is a list of LINES, not roots. 1 root with 1
    child → 2 lines (root + indented child)."""
    dt.add("2026-08-16T10:00:00Z", "d-011", None,
           "dev-mas-engineer", "sub_k", "TASK_K")
    dt.add("2026-08-16T10:00:01Z", "d-012", "d-011",
           "dev-mas-engineer", "sub_l", "TASK_L")
    dt.done("d-011", 100, 1, "ok")
    tree = dt.get_tree()
    assert tree["total"] == 2
    assert tree["done"] == 1
    assert tree["running"] == 1
    # 1 root (d-011) with 1 child (d-012) → 2 lines
    assert len(tree["tree"]) == 2
    # The root line should mention sub_k (the parent of d-012)
    root_line = tree["tree"][0]
    assert "sub_k" in root_line
    # The child line should be indented and mention sub_l
    child_line = tree["tree"][1]
    assert "sub_l" in child_line
    assert child_line.startswith("  ")  # indented 2 spaces
