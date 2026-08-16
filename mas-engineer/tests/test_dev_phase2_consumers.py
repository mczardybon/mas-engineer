"""
test_dev_phase2_consumers.py — R110-166 phase 2.1 + 2.2

End-to-end tests for the two new consumer flows:
  - wf_im_design_patches (consumes im.finding.created → writes
    .mase/im/patches/<request_id>.yaml)
  - wf_recovery_defib   (consumes monitor.health.degraded → writes
    .mase/recovery/log/<request_id>.json)

The consumer helper dev_mq_consumer.py is exercised directly here.
The workflow YAML wiring is tested separately via
test_dev_workflow_runner_mq_actions.py (existing).

We isolate MAS_MQ_ROOT and the workspace so these tests cannot
interfere with the live queue. Each test uses a unique request_id
(per the R110-165 lesson about MQ-2 idempotency dedup).
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
    """Return env-dict that propagates the test-isolation env vars to
    subprocesses (MAS_MQ_ROOT, MAS_PATCHES_DIR, MAS_RECOVERY_LOG_DIR).
    Without this, subprocesses default to the real install paths and
    pollute the live state.
    """
    passthrough = ("MAS_MQ_ROOT", "MAS_PATCHES_DIR", "MAS_RECOVERY_LOG_DIR")
    return {**os.environ, **{k: os.environ[k] for k in passthrough if k in os.environ}}


# ─── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def tmp_workspace(tmp_path, monkeypatch):
    """Minimal mas-engineer workspace in tmp_path with isolated MQ,
    patches, and recovery-log directories. Each env-var override
    keeps a test's writes inside its own tmp dir so we never pollute
    the real install or the live queue."""
    ws = tmp_path / "mas-ws"
    ws.mkdir()
    (ws / ".mase").mkdir()
    (ws / ".mase" / "im").mkdir()
    (ws / ".mase" / "im" / "patches").mkdir()
    (ws / ".mase" / "recovery").mkdir()
    (ws / ".mase" / "recovery" / "log").mkdir()
    mq_root = tmp_path / "mq"
    mq_root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(mq_root))
    monkeypatch.setenv("MAS_PATCHES_DIR", str(ws / ".mase" / "im" / "patches"))
    monkeypatch.setenv("MAS_RECOVERY_LOG_DIR", str(ws / ".mase" / "recovery" / "log"))
    return ws


# ─── dev_mq_consumer.py: helper-level tests ────────────────

def test_helper_no_message_returns_no_message(tmp_workspace):
    """(C.1) When topic is empty, helper returns 'no-message' (exit 1)."""
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "im.finding.created",
         "--consumer-id", "wf_im_design_patches",
         "--processor", "dev_im_design_patches:process_msg",
         "--timeout", "1"],
        capture_output=True, text=True, timeout=15, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["result"] == "no-message"
    assert out["topic"] == "im.finding.created"


def test_helper_invalid_processor_exits_3(tmp_workspace):
    """(C.2) Bad processor spec → error (exit 3) before any consume."""
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "im.finding.created",
         "--consumer-id", "wf_im_design_patches",
         "--processor", "no_such_module:foo",
         "--timeout", "1"],
        capture_output=True, text=True, timeout=15, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 3
    out = json.loads(r.stdout)
    assert out["result"] == "error"
    assert "processor-load-failed" in out["reason"]


# ─── Phase 2.1: im → patch ────────────────────────────────

def test_im_consumer_writes_patch(tmp_workspace):
    """(P2.1.1) Consume im.finding.created → writes
    .mase/im/patches/<request_id>.yaml with correct priority/severity."""
    request_id = _unique_id("r110-166-c1")
    mq.enqueue(
        "im.finding.created",
        {
            "request_id": request_id,
            "source": "dev_im_finder_scan",
            "findings_total": 4,
            "findings_by_severity": {"blocker": 1, "high": 1, "medium": 2},
            "findings_by_type": {"yaml_typo": 4},
            "findings_top": [
                {"type": "yaml_typo", "severity": "blocker",
                 "location": "recipe/a.yaml:1", "description": "bad"},
                {"type": "yaml_typo", "severity": "high",
                 "location": "recipe/b.yaml:2", "description": "bad"},
            ],
        },
    )
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "im.finding.created",
         "--consumer-id", "wf_im_design_patches",
         "--processor", "dev_im_design_patches:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0, f"helper failed: {r.stderr}"
    out = json.loads(r.stdout)
    assert out["result"] == "acked"
    # Patch file must exist and be valid YAML
    patch_path = tmp_workspace / ".mase" / "im" / "patches" / f"{request_id}.yaml"
    assert patch_path.exists(), f"patch not written: {patch_path}"
    import yaml as _yaml
    patch = _yaml.safe_load(patch_path.read_text())
    assert patch["request_id"] == request_id
    assert patch["patch_type"] == "blocker_remediation"
    assert patch["priority"] == "P0"
    assert patch["findings_total"] == 4
    assert len(patch["actions"]) == 2
    assert patch["actions"][0]["action"] == "fix_yaml_syntax"


def test_im_consumer_nacks_on_processor_error(tmp_workspace):
    """(P2.1.2) When the processor raises, helper NACKs the message
    (exit 2) and records the failure reason. We trigger a real
    failure by passing a findings_top that the processor cannot
    iterate as expected."""
    request_id = _unique_id("r110-166-c2")
    mq.enqueue(
        "im.finding.created",
        {
            "request_id": request_id,
            "source": "dev_im_finder_scan",
            "findings_total": 1,
            "findings_by_severity": {"high": 1},
            "findings_by_type": {"yaml_typo": 1},
            # Pass an int where a list of dicts is expected; the
            # processor slices it and then calls .get("type") on
            # an int (which has no .get), raising AttributeError.
            "findings_top": 12345,
        },
    )
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "im.finding.created",
         "--consumer-id", "wf_im_design_patches",
         "--processor", "dev_im_design_patches:process_msg",
         "--timeout", "5"],
        capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 2, (
        f"expected NACK (exit 2), got {r.returncode}\n"
        f"STDOUT: {r.stdout}\nSTDERR: {r.stderr}"
    )
    out = json.loads(r.stdout)
    assert out["result"] == "nacked"
    # Some key indicating the failure cause must be present
    assert any(k in out for k in ("exception", "error", "reason", "traceback"))


def test_im_consumer_drains_max_messages(tmp_workspace):
    """(P2.1.3) --max-messages=N drains N msgs in one call."""
    for i in range(3):
        mq.enqueue(
            "im.finding.created",
            {"request_id": _unique_id(f"r110-166-c3-{i}"),
             "findings_total": 0, "findings_by_severity": {},
             "findings_by_type": {}, "findings_top": []},
        )
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "im.finding.created",
         "--consumer-id", "wf_im_design_patches",
         "--processor", "dev_im_design_patches:process_msg",
         "--timeout", "3", "--max-messages", "3"],
         capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["result"] == "acked"
    assert "3 messages" in out["reason"]


# ─── Phase 2.2: monitor → defib ───────────────────────────

def test_health_consumer_writes_log(tmp_workspace):
    """(P2.2.1) Consume monitor.health.degraded → writes
    .mase/recovery/log/<request_id>.json with classified actions."""
    request_id = _unique_id("r110-166-d1")
    mq.enqueue(
        "monitor.health.degraded",
        {
            "request_id": request_id,
            "source": "dev_health_monitor",
            "command": "CHECK_HEALTH",
            "has_problem": True,
            "issues_found": 2,
            "findings_count": 0,
            "escalate": False,
            "summary": {"stale_in_flight_count": 4, "dlq_count": 0},
        },
    )
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "monitor.health.degraded",
         "--consumer-id", "wf_recovery_defib",
         "--processor", "dev_recovery_defib:process_msg",
         "--timeout", "5"],
         capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0
    log_path = tmp_workspace / ".mase" / "recovery" / "log" / f"{request_id}.json"
    assert log_path.exists()
    log = json.loads(log_path.read_text())
    assert log["request_id"] == request_id
    assert log["has_problem"] is True
    assert log["defib_outcome"] == "ok"
    actions = log["actions_taken"]
    # must include gc_stale_in_flight for stale>0
    action_names = [a["action"] for a in actions]
    assert "gc_stale_in_flight" in action_names


def test_health_consumer_noop_when_no_problem(tmp_workspace):
    """(P2.2.2) has_problem=False (consumer-shouldn't-have-been-invoked
    edge case) → defib logs a noop action."""
    request_id = _unique_id("r110-166-d2")
    mq.enqueue(
        "monitor.health.degraded",
        {"request_id": request_id, "source": "dev_health_monitor",
         "command": "CHECK_HEALTH", "has_problem": False,
         "issues_found": 0, "findings_count": 0,
         "summary": {}},
    )
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "monitor.health.degraded",
         "--consumer-id", "wf_recovery_defib",
         "--processor", "dev_recovery_defib:process_msg",
         "--timeout", "5"],
         capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0
    log_path = tmp_workspace / ".mase" / "recovery" / "log" / f"{request_id}.json"
    log = json.loads(log_path.read_text())
    assert log["has_problem"] is False
    assert log["actions_taken"][0]["action"] == "noop"


def test_health_consumer_classifies_knowledge_stale(tmp_workspace):
    """(P2.2.3) rules_last_refresh_age_hours > 168 → refresh_knowledge action."""
    request_id = _unique_id("r110-166-d3")
    mq.enqueue(
        "monitor.health.degraded",
        {"request_id": request_id, "source": "dev_health_monitor",
         "command": "CHECK_KNOWLEDGE", "has_problem": True,
         "issues_found": 1, "findings_count": 0,
         "summary": {"rules_last_refresh_age_hours": 200}},
    )
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "monitor.health.degraded",
         "--consumer-id", "wf_recovery_defib",
         "--processor", "dev_recovery_defib:process_msg",
         "--timeout", "5"],
         capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0
    log = json.loads((tmp_workspace / ".mase" / "recovery" / "log" / f"{request_id}.json").read_text())
    action_names = [a["action"] for a in log["actions_taken"]]
    assert "refresh_knowledge" in action_names


def test_health_consumer_classifies_daemon_down(tmp_workspace):
    """(P2.2.4) CHECK_DAEMON + daemon_alive=False → rebuild_daemon action."""
    request_id = _unique_id("r110-166-d4")
    mq.enqueue(
        "monitor.health.degraded",
        {"request_id": request_id, "source": "dev_health_monitor",
         "command": "CHECK_DAEMON", "has_problem": True,
         "issues_found": 1, "findings_count": 0,
         "summary": {"daemon_alive": False}},
    )
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_mq_consumer.py"),
         "--topic", "monitor.health.degraded",
         "--consumer-id", "wf_recovery_defib",
         "--processor", "dev_recovery_defib:process_msg",
         "--timeout", "5"],
         capture_output=True, text=True, timeout=20, cwd=str(tmp_workspace),
        env=_isolated_env(),
    )
    assert r.returncode == 0
    log = json.loads((tmp_workspace / ".mase" / "recovery" / "log" / f"{request_id}.json").read_text())
    action_names = [a["action"] for a in log["actions_taken"]]
    assert "rebuild_daemon" in action_names


# ─── Workflow YAML wiring: 2.1 + 2.2 are real CONSUMERs now ─

def test_wf_im_design_patches_uses_consumer(tmp_workspace):
    """(P2.1.W) wf_im_design_patches runs dev_mq_consumer (not a stub echo)."""
    import yaml as _yaml
    wf = _yaml.safe_load(
        (REPO_ROOT / ".mase" / "workflows.yaml").read_text()
    )["task_workflows"]["wf_im_design_patches"]
    desc = wf["desc"]
    assert "Consumer" in desc or "im.finding.created" in desc
    # Find the consume step
    consume_step = next((s for s in wf["steps"]
                         if s.get("id") == "consume"), None)
    assert consume_step is not None, "no 'consume' step in wf_im_design_patches"
    assert "dev_mq_consumer" in consume_step["cmd"]
    assert "dev_im_design_patches:process_msg" in consume_step["cmd"]


def test_wf_recovery_defib_uses_consumer(tmp_workspace):
    """(P2.2.W) wf_recovery_defib runs dev_mq_consumer (not a stub echo)."""
    import yaml as _yaml
    wf = _yaml.safe_load(
        (REPO_ROOT / ".mase" / "workflows.yaml").read_text()
    )["task_workflows"]["wf_recovery_defib"]
    desc = wf["desc"]
    assert "Consumer" in desc or "monitor.health.degraded" in desc
    consume_step = next((s for s in wf["steps"]
                         if s.get("id") == "consume"), None)
    assert consume_step is not None
    assert "dev_mq_consumer" in consume_step["cmd"]
    assert "dev_recovery_defib:process_msg" in consume_step["cmd"]
