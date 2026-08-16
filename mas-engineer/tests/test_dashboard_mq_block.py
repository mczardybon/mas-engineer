"""
test_dashboard_mq_block.py — R110-162

Regression tests for the new `mq` block in dev_dashboard_data.py's
output (data.json).  Verifies:
  1. The `mq` key is always present
  2. All expected sub-keys exist (available, depth_total, lag_p95_ms,
     dlq_count, retry_rate, completed_total, topic_count, by_topic,
     generated_at)
  3. When MQ has no data: aggregates are 0, by_topic={}
  4. When MQ has data: aggregates are correct (sum, max, mean)
  5. Graceful degradation: if dev_message_queue import fails, the
     block still renders with available=false
  6. End-to-end: write to a tmp workspace, run dev_dashboard_data,
     verify the mq block matches the seeded state
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import dev_dashboard_data as dd  # noqa: E402
import dev_message_queue as mq  # noqa: E402


@pytest.fixture
def tmp_workspace(tmp_path, monkeypatch):
    """Build a minimal mas-engineer workspace in tmp_path with
    isolated MAS_MQ_ROOT."""
    ws = tmp_path / "mas-ws"
    ws.mkdir()
    (ws / "recipe" / "sub").mkdir(parents=True)
    (ws / ".mase").mkdir()
    (ws / ".mase" / "dashboards").mkdir()
    (ws / ".mase" / "guardian.yaml").write_text("guardian: {}\n")
    (ws / ".mas-mode").write_text("mas\n")
    # Isolated MQ root
    mq_root = tmp_path / "mq"
    mq_root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(mq_root))
    return ws


# ─── Schema tests ────────────────────────────────────────

def test_mq_block_present(tmp_workspace):
    """(1) The `mq` key is always present in the dashboard data."""
    data = dd.generate_data(str(tmp_workspace))
    assert "mq" in data, "mq block missing from dashboard data"


def test_mq_block_schema(tmp_workspace):
    """(2) All expected sub-keys exist in the mq block."""
    data = dd.generate_data(str(tmp_workspace))
    mq_block = data["mq"]
    required = [
        "available", "generated_at", "depth_total", "lag_p95_ms",
        "dlq_count", "retry_rate", "completed_total",
        "topic_count", "by_topic",
    ]
    for k in required:
        assert k in mq_block, f"mq.{k} missing"


def test_mq_block_empty_when_no_data(tmp_workspace):
    """(3) When MQ has no data, aggregates are 0 and by_topic={}."""
    data = dd.generate_data(str(tmp_workspace))
    mq_block = data["mq"]
    assert mq_block["available"] is True
    assert mq_block["depth_total"] == 0
    assert mq_block["lag_p95_ms"] == 0
    assert mq_block["dlq_count"] == 0
    assert mq_block["retry_rate"] == 0.0
    assert mq_block["completed_total"] == 0
    assert mq_block["topic_count"] == 0
    assert mq_block["by_topic"] == {}


def test_mq_block_aggregates_correct(tmp_workspace, monkeypatch):
    """(4) When MQ has data, aggregates match the underlying state.

    Seed: 1 dispatch_start on `dispatches` + 1 cpdone signal.
    The dispatch_tracker emits MQ on `dispatches`; the signal
    workflow emits MQ on `cpdone`. We enqueue manually here to
    avoid coupling to the tracker tests."""
    # Enqueue 3 messages on `dispatches`, 2 on `cpdone`
    mq.enqueue("dispatches", {"event_type": "dispatch_start",
                              "id": "d-001"})
    mq.enqueue("dispatches", {"event_type": "dispatch_start",
                              "id": "d-002"})
    mq.enqueue("dispatches", {"event_type": "dispatch_start",
                              "id": "d-003"})
    mq.enqueue("cpdone", {"signal": "CP_DONE", "id": "s-001"})
    mq.enqueue("cpdone", {"signal": "CP_DONE", "id": "s-002"})

    data = dd.generate_data(str(tmp_workspace))
    mq_block = data["mq"]
    # 3 + 2 = 5 pending, 2 topics
    assert mq_block["topic_count"] == 2
    assert mq_block["depth_total"] == 5
    # 0 messages acked yet → 0 completed
    assert mq_block["completed_total"] == 0
    # by_topic breakdown
    assert set(mq_block["by_topic"].keys()) == {"dispatches", "cpdone"}
    assert mq_block["by_topic"]["dispatches"]["depth"] == 3
    assert mq_block["by_topic"]["cpdone"]["depth"] == 2


def test_mq_block_completed_total_after_ack(tmp_workspace):
    """(5) completed_total reflects the sum of completed_total
    across topics, which only increments after ack."""
    mq.enqueue("dispatches", {"id": "d-001"})
    mq.enqueue("dispatches", {"id": "d-002"})
    # Consume + ack both
    m1 = mq.consume("dispatches")
    m2 = mq.consume("dispatches")
    mq.ack(m1["msg_id"])
    mq.ack(m2["msg_id"])
    # Enqueue 1 more, don't ack
    mq.enqueue("dispatches", {"id": "d-003"})

    data = dd.generate_data(str(tmp_workspace))
    mq_block = data["mq"]
    # 1 pending (d-003) + 2 completed
    assert mq_block["depth_total"] == 1
    assert mq_block["completed_total"] == 2
    assert mq_block["by_topic"]["dispatches"]["completed_total"] == 2
    assert mq_block["by_topic"]["dispatches"]["depth"] == 1


def test_mq_block_graceful_when_module_missing(tmp_path, monkeypatch):
    """(6) If dev_message_queue is not importable, the block
    still renders with available=false (and the other top-level
    fields are unchanged)."""
    # Build a workspace WITHOUT dev_message_queue in the path
    ws = tmp_path / "ws-no-mq"
    ws.mkdir()
    (ws / "recipe" / "sub").mkdir(parents=True)
    (ws / ".mase").mkdir()
    (ws / ".mase" / "dashboards").mkdir()
    (ws / ".mase" / "guardian.yaml").write_text("guardian: {}\n")
    (ws / ".mas-mode").write_text("mas\n")

    # Simulate MQ-unavailable by setting _MQ_AVAILABLE=False on the
    # already-imported module (we don't actually unimport).
    monkeypatch.setattr(dd, "_MQ_AVAILABLE", False)
    data = dd.generate_data(str(ws))
    assert data["mq"]["available"] is False
    assert data["mq"]["depth_total"] == 0
    assert data["mq"]["by_topic"] == {}
    # Other top-level keys still present
    assert "agents" in data
    assert "dispatch" in data


def test_end_to_end_subprocess(tmp_workspace):
    """(7) Run dev_dashboard_data.py as a subprocess against the
    tmp workspace. The output data.json must contain the mq block."""
    mq.enqueue("dispatches", {"id": "d-100"})
    mq.enqueue("dispatches", {"id": "d-101"})

    env = {**os.environ,
           "MAS_MQ_ROOT": str(tmp_workspace.parent / "mq")}
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_dashboard_data.py"),
         "--workspace", str(tmp_workspace)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr

    data_path = tmp_workspace / ".mase" / "dashboards" / "data.json"
    assert data_path.exists()
    data = json.loads(data_path.read_text())
    assert "mq" in data
    assert data["mq"]["depth_total"] == 2
    assert data["mq"]["topic_count"] == 1
    assert "dispatches" in data["mq"]["by_topic"]


def test_lag_p95_takes_max_across_topics(tmp_workspace):
    """(8) When multiple topics have different lag values,
    lag_p95_ms in the block is the worst-case (max)."""
    # Enqueue + don't ack — lag will be computed from enqueue time
    mq.enqueue("fast_topic", {"id": "f-1"})
    mq.enqueue("slow_topic", {"id": "s-1"})
    # Force a measurable lag on slow_topic by enqueuing earlier
    # (we can't actually control time here, but the formula is
    # max(lag_p95_ms across topics with lag > 0))
    data = dd.generate_data(str(tmp_workspace))
    mq_block = data["mq"]
    # Whatever the actual values are, lag_p95_ms must equal
    # max(per_topic.lag_p95_ms) — verify by computing manually.
    lags = [t.get("lag_p95_ms", 0) for t in mq_block["by_topic"].values()]
    expected_max = max([l for l in lags if l > 0], default=0)
    assert mq_block["lag_p95_ms"] == expected_max


def test_retry_rate_is_mean_across_topics(tmp_workspace):
    """(9) retry_rate is the arithmetic mean across topics."""
    # Enqueue on 2 topics
    mq.enqueue("topic_a", {"id": "a-1"})
    mq.enqueue("topic_b", {"id": "b-1"})
    data = dd.generate_data(str(tmp_workspace))
    rates = [t.get("retry_rate", 0.0)
             for t in data["mq"]["by_topic"].values()]
    expected_mean = round(sum(rates) / len(rates), 4) if rates else 0.0
    assert data["mq"]["retry_rate"] == expected_mean
