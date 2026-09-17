"""
test_dev_phase3_phoenix_log.py — R110-168 phase 3

End-to-end tests for the phoenix.recovery.completed consumer:
  - wf_phoenix_log_persist (consumes phoenix.recovery.completed →
    writes .mase/phoenix_logs/<request_id>.json)

The consumer helper dev_phoenix_log_persister.py is exercised via
dev_mq_consumer.py. The workflow YAML wiring is verified against
.mase/workflows.yaml.

We isolate MAS_MQ_ROOT and MAS_PHOENIX_LOG_DIR so these tests
cannot interfere with the live queue or the real install paths.
Each test uses a unique request_id (R110-165 lesson about MQ-2
idempotency dedup).
"""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import dev_message_queue as mq  # noqa: E402


def _unique_id(prefix: str) -> str:
    """Per-test-run unique id (R110-165 lesson: avoid MQ-2 dedup)."""
    return f"{prefix}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"


def _isolated_env() -> dict:
    """Return env-dict that propagates test-isolation env vars to
    subprocesses (MAS_MQ_ROOT, MAS_PHOENIX_LOG_DIR).

    Without this, subprocesses default to the real install path
    (.mase/phoenix_logs/) and pollute the live state.
    """
    passthrough = ("MAS_MQ_ROOT", "MAS_PHOENIX_LOG_DIR")
    return {**os.environ, **{k: os.environ[k] for k in passthrough if k in os.environ}}


# ─── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def tmp_workspace(tmp_path, monkeypatch):
    """Minimal mas-engineer workspace in tmp_path with isolated MQ
    and phoenix-log directories. Each env-var override keeps a
    test's writes inside its own tmp dir so we never pollute the
    real install or the live queue."""
    ws = tmp_path / "mas-ws"
    ws.mkdir()
    (ws / ".mase").mkdir()
    (ws / ".mase" / "phoenix_logs").mkdir()
    mq_root = tmp_path / "mq"
    mq_root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(mq_root))
    monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(ws / ".mase" / "phoenix_logs"))
    return ws


def _enqueue_phoenix_completed(request_id: str, final_status: str = "ok",
                                levels_passed: int = 5,
                                levels_total: int = 5) -> None:
    """Helper: enqueue a phoenix.recovery.completed message in the
    exact shape dev_phoenix_recovery_run.py publishes."""
    levels = {}
    for i, name in enumerate(["immune", "checkpoint", "safezone", "timeline", "defib"]):
        levels[name] = {"ok": i < levels_passed, "exit": 0 if i < levels_passed else 1,
                        "log": f"/tmp/.mase/phoenix_logs/{request_id}_{name}.log",
                        "cmd": f"wf_{name}_run"}
    mq.enqueue(
        "phoenix.recovery.completed",
        {
            "request_id": request_id,
            "from": "5",
            "to": "1",
            "timestamp": "2026-08-16T18:00:00Z",
            "levels": levels,
            "levels_passed": levels_passed,
            "levels_total": levels_total,
            "final_status": final_status,
            "duration_ms": 1234,
        },
    )


# ─── dev_mq_consumer.py: helper-level tests ────────────────

def test_helper_no_message_returns_no_message(tmp_workspace):
    """(C.1) When phoenix.recovery.completed is empty, helper
    returns 'no-message' (exit 1)."""
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "1"],
        capture_output=True, text=True, timeout=15, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["result"] == "no-message"
    assert out["topic"] == "phoenix.recovery.completed"


# ─── Phase 3.1: phoenix → log-persister ────────────────────

def test_phoenix_consumer_writes_log_ok(tmp_workspace):
    """(P3.1.1) Consume phoenix.recovery.completed with all 5
    levels passed → writes .mase/phoenix_logs/<request_id>.json
    with final_status=ok and attention_required=False."""
    request_id = _unique_id("r110-168-p1")
    _enqueue_phoenix_completed(request_id, final_status="ok",
                                levels_passed=5, levels_total=5)
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0, f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    log_path = tmp_workspace / ".mase" / "phoenix_logs" / f"{request_id}.json"
    log = json.loads(log_path.read_text())
    assert log["schema_version"] == 1
    assert log["request_id"] == request_id
    assert log["source_topic"] == "phoenix.recovery.completed"
    assert log["final_status"] == "ok"
    assert log["levels_passed"] == 5
    assert log["levels_total"] == 5
    assert log["classification"]["attention_required"] is False
    # The level digest has 5 entries, all ok
    digest = log["level_digest"]
    assert len(digest) == 5
    assert all(d["ok"] for d in digest)


def test_phoenix_consumer_writes_log_degraded(tmp_workspace):
    """(P3.1.2) Consume phoenix.recovery.completed with 3/5
    levels passed → final_status=degraded, attention_required=True,
    levels_failed=2."""
    request_id = _unique_id("r110-168-p2")
    _enqueue_phoenix_completed(request_id, final_status="degraded",
                                levels_passed=3, levels_total=5)
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0, f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    log_path = tmp_workspace / ".mase" / "phoenix_logs" / f"{request_id}.json"
    log = json.loads(log_path.read_text())
    assert log["final_status"] == "degraded"
    assert log["levels_passed"] == 3
    assert log["levels_total"] == 5
    assert log["classification"]["levels_failed"] == 2
    assert log["classification"]["attention_required"] is True
    # Level digest should show 3 ok + 2 failed
    ok_count = sum(1 for d in log["level_digest"] if d["ok"])
    fail_count = sum(1 for d in log["level_digest"] if not d["ok"])
    assert ok_count == 3
    assert fail_count == 2


def test_phoenix_consumer_drains_max_messages(tmp_workspace):
    """(P3.1.3) --max-messages=N drains N phoenix completions
    in one helper call (mirrors the phase-2 pattern)."""
    for i in range(3):
        _enqueue_phoenix_completed(
            _unique_id(f"r110-168-p3-{i}"),
            final_status="ok", levels_passed=5, levels_total=5,
        )
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "3", "--max-messages", "3"],
        capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0, f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    out = json.loads(r.stdout)
    assert out["result"] == "acked"
    assert out["count"] == 3
    assert "drained 3" in out["reason"]


def test_phoenix_consumer_idempotent_reprocess(tmp_workspace):
    """(P3.1.4) Re-processing the same request_id overwrites the
    log file (idempotent). R110-166 lesson: consumer must not
    double-write or append."""
    request_id = _unique_id("r110-168-p4")
    # First run: ok
    _enqueue_phoenix_completed(request_id, final_status="ok",
                                levels_passed=5, levels_total=5)
    r1 = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r1.returncode == 0
    log_path = tmp_workspace / ".mase" / "phoenix_logs" / f"{request_id}.json"
    first_log = json.loads(log_path.read_text())
    assert first_log["final_status"] == "ok"

    # Re-enqueue (same request_id) and consume again
    _enqueue_phoenix_completed(request_id, final_status="degraded",
                                levels_passed=3, levels_total=5)
    r2 = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r2.returncode == 0
    second_log = json.loads(log_path.read_text())
    # File overwritten (not appended): single JSON object, not an array
    raw = log_path.read_text()
    assert not raw.lstrip().startswith("[")
    assert second_log["final_status"] == "degraded"
    assert second_log["levels_passed"] == 3


# ─── Workflow YAML wiring: 3.1 is a real CONSUMER now ─────

def test_wf_phoenix_log_persist_uses_consumer(tmp_workspace):
    """(P3.1.W) wf_phoenix_log_persist runs dev_mq_consumer
    (not a stub echo)."""
    import yaml as _yaml
    wf = _yaml.safe_load(
        (REPO_ROOT / ".mase" / "workflows.yaml").read_text()
    )["task_workflows"]["wf_phoenix_log_persist"]
    desc = wf["desc"]
    assert "Consumer" in desc or "phoenix.recovery.completed" in desc
    consume_step = next((s for s in wf["steps"]
                         if s.get("id") == "consume"), None)
    assert consume_step is not None, "no 'consume' step in wf_phoenix_log_persist"
    assert "dev_mq_consumer" in consume_step["cmd"]
    assert "dev_phoenix_log_persister:process_msg" in consume_step["cmd"]
