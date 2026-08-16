"""
test_dev_workflow_runner_mq_actions.py — R110-164.

Verifies the R110-164 follow-up to R110-155:
  - dev_workflow_runner.py now supports actions: enqueue, consume, ack, nack
  - cross-step reference substitution works: {consume.msg_id} → msg_id
  - the 5 R110-155 task_workflows (wf_signal_cpdone/error/sessionend,
    wf_mq_consumer_cpdone/error) actually run end-to-end via the runner,
    not just via direct dev_message_queue.py calls (which is what
    R110-155's claimed "smoke" actually did — verification theater).

Run with:
    python3 -m pytest tests/test_dev_workflow_runner_mq_actions.py -v
"""
import os
import sys
import subprocess
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"


def _run_runner(workflow, *args, timeout=30):
    """Run a workflow via dev_workflow_runner.py and return (rc, stdout, stderr)."""
    proc = subprocess.run(
        ["python3", str(TOOLS / "dev_workflow_runner.py"), workflow, *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr


def _mq_cli(*args):
    """Run dev_message_queue.py and parse JSON output."""
    proc = subprocess.run(
        ["python3", str(TOOLS / "dev_message_queue.py"), *args],
        capture_output=True, text=True, timeout=15, cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        return None
    try:
        import json
        return json.loads(proc.stdout)
    except Exception:
        return None


def _drain(topic):
    """Ack all in_flight + pending messages on a topic. Returns list of msg_ids."""
    drained = []
    while True:
        msg = _mq_cli("--consume", topic, "--consumer-id", f"test-drain-{os.getpid()}")
        if not msg or not msg.get("msg_id"):
            break
        drained.append(msg["msg_id"])
        _mq_cli("--ack", msg["msg_id"])
    return drained


def _latest_log(workflow_name):
    """Return the path to the most recent workflow run log, or None."""
    log_dir = REPO_ROOT / ".mase" / "workflow_runs"
    if not log_dir.exists():
        return None
    candidates = sorted(
        log_dir.glob(f"{workflow_name}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


# ── Section 1: action handler dispatch table ─────────────────────────

def test_runner_handles_enqueue_action():
    """Runner must recognize `action: enqueue` (R110-155 was missing this)."""
    src = (TOOLS / "dev_workflow_runner.py").read_text()
    assert 'action == "enqueue"' in src, \
        "R110-164: dev_workflow_runner.py missing enqueue action handler"
    assert "enqueue(" in src, \
        "R110-164: enqueue handler must call dev_message_queue.enqueue()"


def test_runner_handles_consume_action():
    """Runner must recognize `action: consume`."""
    src = (TOOLS / "dev_workflow_runner.py").read_text()
    assert 'action == "consume"' in src, \
        "R110-164: dev_workflow_runner.py missing consume action handler"
    assert "consume(" in src


def test_runner_handles_ack_action():
    """Runner must recognize `action: ack`."""
    src = (TOOLS / "dev_workflow_runner.py").read_text()
    assert 'action == "ack"' in src, \
        "R110-164: dev_workflow_runner.py missing ack action handler"
    assert "ack(" in src


def test_runner_handles_nack_action():
    """Runner must recognize `action: nack`."""
    src = (TOOLS / "dev_workflow_runner.py").read_text()
    assert 'action == "nack"' in src, \
        "R110-164: dev_workflow_runner.py missing nack action handler"
    assert "nack(" in src


# ── Section 2: cross-step reference substitution ────────────────────

def test_runner_supports_cross_step_refs():
    """{step_id.field} must substitute to a prior step's output value.

    R110-164: wf_mq_consumer_cpdone step 3 uses msg_id: '{consume.msg_id}'.
    Pre-fix this resolved to "" (empty) and the ack silently no-op'd.
    """
    src = (TOOLS / "dev_workflow_runner.py").read_text()
    assert "results.get(sid_ref" in src, \
        "R110-164: runner must look up prior step results for cross-refs"
    assert 'msg_id=([a-f0-9-]+)' in src, \
        "R110-164: runner must extract msg_id from consume output string"


# ── Section 3: end-to-end mq roundtrip via runner ────────────────────

def test_wf_signal_cpdone_runs_via_runner():
    """wf_signal_cpdone must enqueue successfully when run via dev_workflow_runner.py.

    R110-155 claimed "End-to-end smoke (2 enqueue → 2 consume → 2 ack → depth=0)"
    but that smoke used dev_message_queue.py directly, NOT the runner. This test
    is the corrected smoke that proves the runner actually wires up the action.
    """
    topic = "cpdone"
    _drain(topic)
    assert _mq_cli("--depth", topic) == 0, "test setup: topic should be empty"

    rid = f"r110-164-test-{uuid.uuid4().hex[:8]}"
    rc, out, err = _run_runner("wf_signal_cpdone",
                               "--request_id", rid,
                               "--from", "test",
                               "--to", "dashboard")
    assert rc == 0, f"wf_signal_cpdone failed: rc={rc} stderr={err}\nout={out}"
    assert "enqueue_cpdone... ✅" in out, \
        f"expected ✅ on enqueue_cpdone step, got: {out}"
    assert "status: ok" in out

    # The message must have actually arrived
    depth = _mq_cli("--depth", topic)
    assert depth == 1, f"expected depth=1 after signal, got depth={depth}"
def test_wf_mq_consumer_cpdone_drains_via_runner():
    """wf_mq_consumer_cpdone must consume + ack via the runner.

    The critical bug this catches: pre-R110-164, the ack step's msg_id
    was empty (cross-ref not resolved), so the message stayed in_flight
    and the depth never returned to 0.

    The process (shell) step has a pre-existing R110-153 {workspace}
    substitution bug (writes to /.mase/) — we tolerate that. The ack
    step has on_error: continue so it must still run with the right msg_id.
    """
    topic = "cpdone"
    _drain(topic)

    # First enqueue something to consume
    rid = f"r110-164-consumer-{uuid.uuid4().hex[:8]}"
    rc, out, _ = _run_runner("wf_signal_cpdone",
                             "--request_id", rid,
                             "--from", "test",
                             "--to", "dashboard")
    assert rc == 0, f"enqueue step failed: {out}"
    assert _mq_cli("--depth", topic) == 1, "expected depth=1 after enqueue"

    # Now consume. The workflow as a whole may report status=failed
    # because the shell process-step has a pre-existing R110-153 bug,
    # but the ack step must still succeed (on_error: continue).
    rc, out, _ = _run_runner("wf_mq_consumer_cpdone")
    # rc non-zero is OK here — it's the R110-153 process-step bug, not R110-164
    assert "consume... ✅" in out
    assert "ack... ✅" in out, f"ack step must succeed; got: {out}"

    # Read the JSON log to verify the cross-ref substitution worked
    log = _latest_log("wf_mq_consumer_cpdone")
    assert log is not None, "no workflow log produced"
    import json
    with open(log) as f:
        log_data = json.load(f)
    ack_output = log_data["results"]["ack"]["output"]
    assert ack_output.startswith("acked msg_id="), \
        f"ack output malformed: {ack_output}"
    # Cross-ref check: ack msg_id must NOT be empty (this was the pre-fix bug)
    assert "acked msg_id= " not in ack_output, \
        f"acked msg_id is empty — cross-ref not resolved: {ack_output}"
    msg_id_part = ack_output.split("acked msg_id=")[1].strip()
    assert len(msg_id_part) >= 32, \
        f"acked msg_id looks invalid (too short): {msg_id_part!r}"

    depth = _mq_cli("--depth", topic)
    assert depth == 0, \
        f"depth must return to 0 after consumer drains; got depth={depth}"


# ── Section 4: full roundtrip (signal → consumer → archived) ────────

def test_full_mq_roundtrip_via_runner_archives_message():
    """Full proof: enqueue via runner, drain via runner, message lands in
    .completed.ndjson (not stuck in_flight).

    This is the corrected version of R110-155's claimed smoke test.

    Tolerates pre-existing R110-153 {workspace} bug in the process step
    (we only care about the mq roundtrip, not the log line written).
    """
    topic = "cpdone"
    _drain(topic)

    rid = f"r110-164-full-{uuid.uuid4().hex[:8]}"
    rc, out, _ = _run_runner("wf_signal_cpdone",
                             "--request_id", rid, "--from", "phoenix", "--to", "dashboard")
    assert rc == 0, out
    assert _mq_cli("--depth", topic) == 1

    rc, out, _ = _run_runner("wf_mq_consumer_cpdone")
    # ack step must have succeeded even if overall rc != 0 (process step fails)
    assert "ack... ✅" in out, f"ack must run: {out}"
    assert _mq_cli("--depth", topic) == 0, "depth must return to 0 after consumer"

    # Read the completed file
    completed = REPO_ROOT / ".mase" / "mq" / f"{topic}.completed.ndjson"
    assert completed.exists(), f"completed file missing: {completed}"
    import json
    found = False
    with open(completed) as f:
        for line in f:
            d = json.loads(line)
            if d.get("payload", {}).get("request_id") == rid:
                found = True
                assert d["status"] == "done", f"expected status=done, got {d.get('status')}"
                assert d["consumer_id"] == "wf_mq_consumer_cpdone", \
                    f"expected consumer_id=wf_mq_consumer_cpdone, got {d.get('consumer_id')}"
                break
    assert found, f"request_id={rid} not found in {completed}"


# ── Section 5: regression — pre-existing action handlers still work ──

def test_shell_action_still_works():
    """Regression: shell action must still function (used by 100+ workflows).

    We invoke wf_yaml_validate (a real, simple shell-based workflow) and
    check the JSON log shows the shell step produced real output.
    """
    rc, out, _ = _run_runner("wf_yaml_validate", timeout=60)
    log = _latest_log("wf_yaml_validate")
    assert log is not None, f"wf_yaml_validate produced no log; out={out}"
    import json
    with open(log) as f:
        data = json.load(f)
    # At least one step should have non-empty output (shell step ran)
    outputs = [v.get("output", "") for v in data.get("results", {}).values()]
    assert any(o for o in outputs), \
        f"no shell step produced output; results={data.get('results')}"


# ── Section 6: documentation requirement ────────────────────────────

def test_workflows_yaml_declares_5_mq_workflows():
    """R110-155 added 5 task_workflows using mq actions; they must still exist."""
    import yaml
    wfs = yaml.safe_load((REPO_ROOT / ".mase" / "workflows.yaml").read_text())
    task_wfs = wfs.get("task_workflows", {})
    expected = {
        "wf_signal_cpdone", "wf_signal_error", "wf_signal_sessionend",
        "wf_mq_consumer_cpdone", "wf_mq_consumer_error",
    }
    missing = expected - set(task_wfs.keys())
    assert not missing, f"R110-155 workflows missing: {missing}"


# ── Section 7: process step failure does not block ack (regression) ─

def test_process_step_failure_does_not_prevent_ack():
    """Spec: ack has on_error: continue; it must run even if process failed.

    Currently the wf_mq_consumer_cpdone.process step (shell) writes to
    {workspace}/.mase/cpdone_consumed.log. If {workspace} substitution
    fails (R110-153 pre-existing bug, writes to /.mase/), the process step
    fails but ack must still run — and it does, per the YAML's on_error: continue.
    """
    topic = "cpdone"
    _drain(topic)

    rc, _, _ = _run_runner("wf_signal_cpdone",
                           "--request_id", f"r110-164-acktest-{uuid.uuid4().hex[:6]}",
                           "--from", "test", "--to", "dashboard")
    assert rc == 0

    rc, out, _ = _run_runner("wf_mq_consumer_cpdone")
    # Ack step must show ✅ even if process step shows ❌
    assert "ack... ✅" in out, f"ack must run regardless of process failure: {out}"
    assert "consume... ✅" in out

    depth = _mq_cli("--depth", topic)
    assert depth == 0, f"ack must have drained the message; depth={depth}"
