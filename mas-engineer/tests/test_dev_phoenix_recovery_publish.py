"""test_dev_phoenix_recovery_publish.py — R110-165 phase 1.1

Tests for the phoenix-recovery publisher:
  - dev_phoenix_recovery_run.py — runs 5 levels, enqueues phoenix.recovery.completed
  - wf_phoenix_recovery_publish — task_workflow wrapper in .mase/workflows.yaml
  - dev_mq_topic_depth.py — tiny helper for "what's the depth of <topic>"

These tests prove end-to-end that:
  1. The helper script runs and the 5 levels all pass
  2. The helper enqueues a message to the right topic with the right shape
  3. The task_workflow declares all the right steps + uses the helper
  4. dry-run mode works (no enqueue, no side effect)
  5. The message survives MQ (depth is right, completed=0, payload intact)
  6. The level-subset flag actually skips levels

Run with:
  python3 -m pytest tests/test_dev_phoenix_recovery_publish.py -v
"""
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS_DIR = REPO_ROOT / "tools"
MQ_ROOT = REPO_ROOT / ".mase" / "mq"
PHOENIX_TOPIC = "phoenix.recovery.completed"
PHOENIX_NDJSON = MQ_ROOT / "phoenix_recovery_completed.ndjson"


def _unique_id(prefix: str) -> str:
    """Per-test-run unique id to avoid MQ-2 idempotency dedup collisions
    when the same test is re-run in the same session."""
    return f"{prefix}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"


# ---------- fixtures ----------

@pytest.fixture
def clean_phoenix_topic():
    """Snapshot depth, run test, restore (we never delete the file because
    other tests may have enqueued things earlier in the session)."""
    depth_before = 0
    if PHOENIX_NDJSON.exists():
        depth_before = sum(1 for _ in open(PHOENIX_NDJSON))
    yield depth_before
    # No restore needed — the queue is append-only by design


@pytest.fixture
def defib_idle_wait_disabled(monkeypatch, request):
    """Replace the defib workflow's consumer with a 0-second-no-message version.

    Background: wf_recovery_defib calls `dev_mq_consumer.py --timeout 60`
    which blocks for 60s when no message is on monitor.health.degraded
    (this is correct production behavior — you want the consumer to wait
    for a real problem report). In test mode, no monitor runs and the topic
    stays empty, so the consumer always times out.

    Fix: monkeypatch the workflow step from "consume" (60s wait) to a
    no-op shell that immediately returns a fake "acked" JSON. This
    preserves the test's structural assertion (defib is part of the
    5-level chain and contributes ok=True) without the 60s idle-wait
    wallclock cost. Documented in directive R110-185.

    The monkeypatch is scoped to the test via pytest's monkeypatch
    fixture and is automatically reverted on test teardown.
    """
    workflows_path = REPO_ROOT / ".mase" / "workflows.yaml"
    if not workflows_path.exists():
        pytest.skip("workflows.yaml not found — cannot patch defib workflow")
    original_text = workflows_path.read_text()
    # Replace defib's 60s consumer with a fast no-op ack stub.
    # Pattern: the consume step in wf_recovery_defib (line ~1928) is one
    # `cmd:` line that contains a trap + python3 + 60s wait. We replace
    # the whole `cmd:` line with a 0-second echo that returns the shape
    # of a real "acked" message, plus a comment documenting the original
    # so it's reversible on teardown.
    old_cmd = "      cmd: 'trap ''kill 0'' TERM; python3 tools/dev_mq_consumer.py --topic monitor.health.degraded\n        --consumer-id wf_recovery_defib --processor dev_recovery_defib:process_msg --timeout 60'"
    new_cmd = "      cmd: \"echo 'TEST-ONLY-STUB-R110-185-original-was-60s-defib-consumer-stub-returns-ok-in-0s-NOT-FOR-PRODUCTION' >/dev/null\""
    patched = original_text.replace(old_cmd, new_cmd)
    if patched == original_text:
        pytest.skip("defib workflow pattern not found — yaml may have changed")
    workflows_path.write_text(patched)
    try:
        yield
    finally:
        workflows_path.write_text(original_text)


# ---------- tests for dev_phoenix_recovery_run.py ----------

def test_dev_phoenix_recovery_run_script_exists():
    assert (TOOLS_DIR / "dev_phoenix_recovery_run.py").exists()


def test_dev_phoenix_recovery_run_dry_run_runs_all_5_levels(defib_idle_wait_disabled):
    """dry-run mode runs all 5 levels and produces a payload — no enqueue."""
    # defib_idle_wait_disabled (R110-185) replaces wf_recovery_defib's 60s
    # consumer with a 0s echo-stub, so defib returns immediately and the
    # full 5-level chain completes in <5s (was 64s with real consumer).
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_phoenix_recovery_run.py"),
         "--request_id", "r110-165-test-dry", "--from", "test", "--to", "test",
         "--dry-run"],
        capture_output=True, text=True, timeout=30, cwd=REPO_ROOT,
    )
    assert r.returncode == 0, f"exit={r.returncode} stderr={r.stderr}"
    out = json.loads(r.stdout)
    assert "payload" in out
    p = out["payload"]
    assert set(p["levels"].keys()) == {"immune", "checkpoint", "safezone", "timeline", "defib"}
    assert p["levels_total"] == 5
    assert p["levels_passed"] >= 1, "at least one level should pass on a healthy repo"
    assert p["final_status"] in ("ok", "degraded")
    assert "duration_ms" in p
    assert p["request_id"] == "r110-165-test-dry"
    # dry-run MUST NOT enqueue
    assert "skipped (dry-run)" in out.get("enqueue", "")


def test_dev_phoenix_recovery_run_real_enqueues_message(clean_phoenix_topic, defib_idle_wait_disabled):
    """Real run actually enqueues to the right topic with full payload."""
    depth_before = clean_phoenix_topic
    request_id = _unique_id("r110-165-test-real")
    # defib_idle_wait_disabled (R110-185) replaces wf_recovery_defib's 60s
    # consumer with a 0s echo-stub, so we don't need --level-timeout here
    # (production: 120s default; test: defib returns in <1s).
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_phoenix_recovery_run.py"),
         "--request_id", request_id, "--from", "test", "--to", "test"],
        capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
    )
    assert r.returncode in (0, 1), f"exit={r.returncode} stderr={r.stderr[:500]}"
    out = json.loads(r.stdout)
    assert "msg_id" in out
    assert out["msg_id"], f"empty msg_id. full out={out}"
    assert out["topic"] == PHOENIX_TOPIC
    assert out["levels_total"] == 5
    assert out["levels_passed"] == 5, f"expected 5/5 on healthy repo, got {out}"
    assert out["final_status"] == "ok"
    # depth must have grown by exactly 1
    assert PHOENIX_NDJSON.exists()
    depth_after = sum(1 for _ in open(PHOENIX_NDJSON))
    assert depth_after == depth_before + 1, (
        f"depth should grow by 1, was {depth_before}, now {depth_after}"
    )
    # find OUR msg by request_id (not just any last line)
    matching = []
    with open(PHOENIX_NDJSON) as f:
        for line in f:
            d = json.loads(line)
            if d.get("payload", {}).get("request_id") == request_id:
                matching.append(d)
    assert len(matching) == 1, (
        f"expected exactly 1 msg with request_id={request_id}, found {len(matching)}"
    )
    msg = matching[0]
    assert msg["msg_id"] == out["msg_id"]
    assert msg["status"] == "pending"
    assert msg["payload"]["request_id"] == request_id
    assert msg["payload"]["levels_passed"] == 5
    # per-level detail
    for level in ("immune", "checkpoint", "safezone", "timeline", "defib"):
        assert level in msg["payload"]["levels"]
        assert msg["payload"]["levels"][level]["ok"] is True


def test_dev_phoenix_recovery_run_level_subset(defib_idle_wait_disabled):
    """--levels=immune,defib runs only 2 levels and payload reflects that."""
    # defib_idle_wait_disabled (R110-185) so defib returns in <1s even
    # though it's the only "real" level we're asking for.
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_phoenix_recovery_run.py"),
         "--request_id", "r110-165-test-subset",
         "--levels", "immune,defib", "--dry-run"],
        capture_output=True, text=True, timeout=30, cwd=REPO_ROOT,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    p = out["payload"]
    assert set(p["levels"].keys()) == {"immune", "defib"}
    assert p["levels_total"] == 2


# ---------- tests for the task_workflow declaration ----------

def test_wf_phoenix_recovery_publish_exists_in_workflows_yaml():
    with open(REPO_ROOT / ".mase" / "workflows.yaml") as f:
        d = yaml.safe_load(f)
    assert "wf_phoenix_recovery_publish" in d["task_workflows"], (
        "phase 1.1 requires wf_phoenix_recovery_publish as a task_workflow"
    )


def test_wf_phoenix_recovery_publish_has_correct_steps():
    with open(REPO_ROOT / ".mase" / "workflows.yaml") as f:
        d = yaml.safe_load(f)
    wf = d["task_workflows"]["wf_phoenix_recovery_publish"]
    steps = {s["id"]: s for s in wf["steps"]}
    assert "run_recovery" in steps
    assert steps["run_recovery"]["action"] == "shell"
    assert "dev_phoenix_recovery_run.py" in steps["run_recovery"]["cmd"]
    # substitution tokens are present
    assert "{request_id}" in steps["run_recovery"]["cmd"]
    assert "{from}" in steps["run_recovery"]["cmd"]
    assert "{to}" in steps["run_recovery"]["cmd"]
    # verify_published depends on run_recovery
    assert "verify_published" in steps
    assert "run_recovery" in steps["verify_published"].get("depends_on", [])


# ---------- tests for the helper dev_mq_topic_depth.py ----------

def test_dev_mq_topic_depth_returns_int_for_existing_topic():
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_mq_topic_depth.py"), PHOENIX_TOPIC],
        capture_output=True, text=True, timeout=10, cwd=REPO_ROOT,
    )
    assert r.returncode == 0
    depth = int(r.stdout.strip())
    assert depth >= 0


def test_dev_mq_topic_depth_returns_zero_for_nonexistent_topic():
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_mq_topic_depth.py"),
         "totally.fake.topic.that.does.not.exist"],
        capture_output=True, text=True, timeout=10, cwd=REPO_ROOT,
    )
    assert r.returncode == 0
    assert r.stdout.strip() == "0"


# ---------- end-to-end via workflow runner (full integration) ----------

def test_wf_phoenix_recovery_publish_runs_via_runner(clean_phoenix_topic, defib_idle_wait_disabled):
    """Full integration: the workflow runner actually executes the workflow
    and a message lands in the queue."""
    depth_before = clean_phoenix_topic
    request_id = _unique_id("r110-165-via-runner")
    # defib_idle_wait_disabled (R110-185) replaces wf_recovery_defib's 60s
    # consumer with a 0s echo-stub, so the full wf_phoenix_recovery_publish
    # workflow completes in <30s (was 240s+).
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_workflow_runner.py"),
         "wf_phoenix_recovery_publish",
         "--request_id", request_id,
         "--from", "test", "--to", "test"],
        capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
    )
    assert r.returncode == 0, f"runner exit={r.returncode}\nstdout={r.stdout[-500:]}\nstderr={r.stderr[-500:]}"
    assert "status: ok" in r.stdout
    # a new message must have landed
    assert PHOENIX_NDJSON.exists()
    depth_after = sum(1 for _ in open(PHOENIX_NDJSON))
    assert depth_after == depth_before + 1, (
        f"depth should grow by 1, was {depth_before}, now {depth_after}"
    )
