"""
test_dev_phase4_escalation.py — R110-169 phase 4

End-to-end tests for the cross-subsystem auto-escalation:
  phoenix.recovery.completed (degraded)
    -> dev_phoenix_log_persister enqueues
       monitor.health.degraded (command=PHOENIX_DEGRADED)
         -> dev_recovery_defib classifies as
            phoenix_recovery_incomplete -> rebuild_phoenix

This is the last closed-loop test for the MQ ecosystem: 3
publishers and 3 consumers, with one cross-topic escalation
(phoenix -> monitor -> defib). After this commit, the story
of the R110-154..R110-169 arc is end-to-end tested.

Isolation: MAS_MQ_ROOT, MAS_PHOENIX_LOG_DIR, MAS_RECOVERY_LOG_DIR
are all pointed at per-test tmp dirs.
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
    return f"{prefix}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"


def _isolated_env() -> dict:
    passthrough = ("MAS_MQ_ROOT", "MAS_PHOENIX_LOG_DIR",
                   "MAS_RECOVERY_LOG_DIR")
    return {**os.environ,
            **{k: os.environ[k] for k in passthrough if k in os.environ}}


# ─── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def tmp_workspace(tmp_path, monkeypatch):
    ws = tmp_path / "mas-ws"
    ws.mkdir()
    (ws / ".mase").mkdir()
    (ws / ".mase" / "phoenix_logs").mkdir()
    (ws / ".mase" / "recovery").mkdir()
    (ws / ".mase" / "recovery" / "log").mkdir()
    mq_root = tmp_path / "mq"
    mq_root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(mq_root))
    monkeypatch.setenv("MAS_PHOENIX_LOG_DIR",
                       str(ws / ".mase" / "phoenix_logs"))
    monkeypatch.setenv("MAS_RECOVERY_LOG_DIR",
                       str(ws / ".mase" / "recovery" / "log"))
    return ws


def _enqueue_phoenix_completed(request_id: str, *,
                                final_status: str = "ok",
                                levels_passed: int = 5,
                                levels_total: int = 5) -> None:
    levels = {}
    for i, name in enumerate(["immune", "checkpoint", "safezone",
                                "timeline", "defib"]):
        levels[name] = {
            "ok": i < levels_passed,
            "exit": 0 if i < levels_passed else 1,
            "log": f"/tmp/.mase/phoenix_logs/{request_id}_{name}.log",
            "cmd": f"wf_{name}_run",
        }
    mq.enqueue(
        "phoenix.recovery.completed",
        {
            "request_id": request_id,
            "from": "5",
            "to": "1",
            "timestamp": "2026-08-16T19:00:00Z",
            "levels": levels,
            "levels_passed": levels_passed,
            "levels_total": levels_total,
            "final_status": final_status,
            "duration_ms": 999,
        },
    )


def _consume_monitor_degraded(workspace: Path, timeout: str = "5") -> dict:
    """Helper: run the defib consumer once and return parsed stdout."""
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "monitor.health.degraded",
         "--consumer-id", "wf_recovery_defib",
         "--processor", "dev_recovery_defib:process_msg",
         "--timeout", timeout],
        capture_output=True, text=True, timeout=20,
        cwd=str(workspace), env=_isolated_env(),
    )
    assert r.returncode == 0, f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    return json.loads(r.stdout)


# ─── Cross-subsystem tests ────────────────────────────────

def test_phoenix_ok_does_not_escalate(tmp_workspace):
    """(P4.1.1) final_status=ok → no escalation msg, no
    monitor.health.degraded message enqueued, escalation_msg_id
    remains None in the log."""
    request_id = _unique_id("r110-169-ok")
    _enqueue_phoenix_completed(request_id, final_status="ok",
                                levels_passed=5, levels_total=5)
    depth_before = mq.depth("monitor.health.degraded")

    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20,
        cwd=str(tmp_workspace), env=_isolated_env(),
    )
    assert r.returncode == 0, f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    out = json.loads(r.stdout)
    assert out["result"] == "acked"
    assert out["count"] == 1

    # Read the process_msg result from the persisted log file
    # (dev_mq_consumer.py returns only the envelope on stdout; the
    # processor's return value is internal — the source of truth
    # is the per-run log file).
    log = json.loads((tmp_workspace / ".mase" / "phoenix_logs"
                      / f"{request_id}.json").read_text())
    assert log["final_status"] == "ok"
    assert log["classification"]["attention_required"] is False
    assert log["escalation_msg_id"] is None
    assert mq.depth("monitor.health.degraded") == depth_before


def test_phoenix_degraded_enqueues_monitor_msg(tmp_workspace):
    """(P4.1.2) final_status=degraded → escalation_msg_id is set
    in the log, monitor.health.degraded topic depth increases by
    exactly 1, and the enqueued payload carries command=
    PHOENIX_DEGRADED with the right summary."""
    request_id = _unique_id("r110-169-deg")
    _enqueue_phoenix_completed(request_id, final_status="degraded",
                                levels_passed=3, levels_total=5)
    depth_before = mq.depth("monitor.health.degraded")

    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20,
        cwd=str(tmp_workspace), env=_isolated_env(),
    )
    assert r.returncode == 0, f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    out = json.loads(r.stdout)
    assert out["result"] == "acked"
    assert out["count"] == 1

    # The processor's return value is captured in the persisted
    # log file (dev_mq_consumer.py returns only the envelope).
    log = json.loads((tmp_workspace / ".mase" / "phoenix_logs"
                      / f"{request_id}.json").read_text())
    assert log["classification"]["attention_required"] is True
    assert log["escalation_msg_id"], (
        f"expected escalation_msg_id in log, got {log!r}"
    )
    assert mq.depth("monitor.health.degraded") == depth_before + 1

    # Inspect the enqueued payload by reading the topic directly
    # (private API: _read_topic returns msgs in enqueue order).
    peeked = mq._read_topic("monitor.health.degraded",
                            include_in_flight=True)
    assert any(m.get("payload", {}).get("command") == "PHOENIX_DEGRADED"
               for m in peeked), (
        f"no PHOENIX_DEGRADED payload in monitor.health.degraded; "
        f"got: {peeked!r}"
    )


def test_defib_dispatches_phoenix_recovery_incomplete(tmp_workspace):
    """(P4.1.3) After escalation, the defib consumer drains the
    monitor.health.degraded message and emits a 'rebuild_phoenix'
    action with the originating phoenix request id and the
    degraded levels."""
    request_id = _unique_id("r110-169-defib")
    # Drive the full cross-topic flow: enqueue phoenix, drain via
    # persister (which escalates), then drain monitor via defib.
    _enqueue_phoenix_completed(request_id, final_status="degraded",
                                levels_passed=2, levels_total=5)
    subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "phoenix.recovery.completed",
         "--consumer-id", "wf_phoenix_log_persist",
         "--processor", "dev_phoenix_log_persister:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20,
        cwd=str(tmp_workspace), env=_isolated_env(),
        check=True,
    )
    # Now the escalated message should be on monitor.health.degraded
    r = _consume_monitor_degraded(tmp_workspace, timeout="5")
    assert r["result"] == "acked"
    assert r["count"] == 1

    # The defib consumer writes a per-request log file
    defib_log = json.loads((tmp_workspace / ".mase" / "recovery"
                             / "log" / f"{request_id}.json").read_text())
    action_names = [a["action"] for a in defib_log["actions_taken"]]
    assert "rebuild_phoenix" in action_names, (
        f"expected rebuild_phoenix in actions_taken, got {action_names}"
    )
    # The action carries the phoenix request id
    rebuild_actions = [a for a in defib_log["actions_taken"]
                       if a["action"] == "rebuild_phoenix"]
    assert rebuild_actions[0]["phoenix_request_id"] == request_id
    assert rebuild_actions[0]["levels_passed"] == 2
    assert rebuild_actions[0]["levels_total"] == 5
    # 3 failed levels (timeline, defib, safezone order doesn't matter)
    assert len(rebuild_actions[0]["degraded_levels"]) == 3


def test_defib_unaffected_for_other_commands(tmp_workspace):
    """(P4.1.4) Regression: defib's new PHOENIX_DEGRADED branch
    does not affect existing classifications. A CHECK_DAEMON
    message still classifies as daemon_down / rebuild_daemon
    (not phoenix_recovery_incomplete)."""
    request_id = _unique_id("r110-169-reg")
    mq.enqueue(
        "monitor.health.degraded",
        {
            "request_id": request_id,
            "source": "dev_health_monitor",
            "command": "CHECK_DAEMON",
            "has_problem": True,
            "issues_found": 1,
            "findings_count": 0,
            "summary": {"daemon_alive": False},
        },
    )
    _consume_monitor_degraded(tmp_workspace, timeout="5")
    log = json.loads((tmp_workspace / ".mase" / "recovery"
                      / "log" / f"{request_id}.json").read_text())
    action_names = [a["action"] for a in log["actions_taken"]]
    assert "rebuild_daemon" in action_names
    assert "rebuild_phoenix" not in action_names, (
        "PHOENIX_DEGRADED classifier leaked into CHECK_DAEMON path"
    )


# ─── Unit-level tests of the helpers themselves ────────────

def test_phoenix_persister_escalation_failure_does_not_lose_log(
        tmp_workspace, monkeypatch):
    """(P4.1.5) If the MQ enqueue raises, the original log file
    must still be on disk and the return value must surface the
    error (not crash). The orchestrator / dashboard can then
    surface the failure."""
    request_id = _unique_id("r110-169-fail")
    _enqueue_phoenix_completed(request_id, final_status="degraded",
                                levels_passed=3, levels_total=5)

    # Force the enqueue to raise
    import dev_phoenix_log_persister as persister
    original_enqueue = mq.enqueue

    def boom(*a, **kw):
        raise RuntimeError("simulated MQ outage")

    monkeypatch.setattr(mq, "enqueue", boom)
    # The processor imports the module lazily inside process_msg;
    # re-import to pick up the patched function on the module's
    # own `dev_message_queue` reference.
    monkeypatch.setattr(persister, "_mq", None, raising=False)
    # Patch the import: replace the name _mq already in the local
    # of process_msg. Easiest: directly call process_msg and
    # patch the symbol it sees via sys.modules.
    sys.modules["dev_message_queue"].enqueue = boom

    msg = {
        "msg_id": "test-msg-1",
        "status": "ok",
        "topic": "phoenix.recovery.completed",
        "payload": {
            "request_id": request_id,
            "from": "5", "to": "1",
            "timestamp": "2026-08-16T19:00:00Z",
            "levels": {},
            "levels_passed": 3, "levels_total": 5,
            "final_status": "degraded", "duration_ms": 0,
        },
    }
    out = persister.process_msg(msg)
    assert "escalation_error" in out, f"expected escalation_error, got {out!r}"
    assert out["attention_required"] is True
    # The log must still exist on disk
    log_path = tmp_workspace / ".mase" / "phoenix_logs" / f"{request_id}.json"
    assert log_path.exists()
    log = json.loads(log_path.read_text())
    assert log["final_status"] == "degraded"
    assert log["escalation_msg_id"] is None

    # Restore (so the fixture teardown / other tests are clean)
    sys.modules["dev_message_queue"].enqueue = original_enqueue
