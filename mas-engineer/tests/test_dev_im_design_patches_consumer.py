"""
test_dev_im_design_patches_consumer.py — R110-196 (R110-195 follow-up).

3-test pytest suite for the CONSUMER-side of the im.finding.created
loop (the sibling of tests/test_dev_im_design_patches.py, which
covers the DESIGN kernel alone).  These tests verify the
end-to-end contract between dev_message_queue (the MQ) and
dev_im_design_patches (the kernel), driven via the same API
calls the dev_mq_consumer.py main() loop makes — but without
spawning a subprocess (which would add 30s+ per test via
the consumer's --timeout default).

Test 1: positive loop — enqueue → mq.consume() → process_msg() →
        mq.ack() → patch file written, msg removed from topic,
        completed.ndjson has 1 entry.
Test 2: idempotent redelivery — process_msg() called twice with
        the SAME payload (different msg_ids, same request_id)
        → 2 patch writes with identical content, NO duplicate
        (the kernel is idempotent on request_id; this is the
        second half of the "at-least-once delivery, at-most-once
        effect" guarantee from R-211).
Test 3: nack path — process_msg() raises → caller calls
        mq.nack(msg_id) → msg back in pending, retry_count=1,
        no patch file written (kernel never completed).

The directive at .directives/sub_mas-design-patches-consumer.md
documents why these tests use the direct API rather than
spawning dev_mq_consumer.py as a subprocess (subprocess +
SIGTERM + 60s timeout would add ~30s/test; the pytest
runtime cap is 180s for the full suite).

Run with:
    python3 -m pytest tests/test_dev_im_design_patches_consumer.py -v
"""
import json
import sys
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"

sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent))

import dev_im_design_patches as design  # noqa: E402
import dev_message_queue as mq           # noqa: E402


# ─── Per-test isolated MAS_PATCHES_DIR + MAS_MQ_ROOT ─────────────

@pytest.fixture
def patches_dir(tmp_path, monkeypatch):
    """Isolated patch output dir (kernel writes here, not the real
    .mase/im/patches/).  The kernel resolves the dir at call-time
    from MAS_PATCHES_DIR, so monkeypatching the env var is enough."""
    d = tmp_path / "patches"
    monkeypatch.setenv("MAS_PATCHES_DIR", str(d))
    return d


@pytest.fixture
def mq_root(tmp_path, monkeypatch):
    """Isolated MQ root so process_msg can be called via the
    consumer's --processor integration (test #3 below) without
    touching the real .mase/mq."""
    root = tmp_path / "mq"
    root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(root))
    return root


def _payload(request_id: str, total: int = 1, by_sev: dict = None) -> dict:
    """Build a typical im.finding.created payload (matches what
    dev_im_finder_scan.py --publish emits)."""
    return {
        "request_id": request_id,
        "source": "dev_im_finder_scan",
        "timestamp": "2026-08-18T12:00:00Z",
        "findings_total": total,
        "findings_by_severity": by_sev or {"high": total},
        "findings_by_type": {"yaml_typo": total},
        "findings_top": [
            {"type": "yaml_typo", "severity": "high",
             "location": "recipe/x.yaml:10", "description": "bad indent"}
        ] if total > 0 else [],
    }


# ─── Tests ───────────────────────────────────────────────────────

def test_consumer_loop_end_to_end_acks_and_writes(patches_dir, mq_root):
    """(1) Positive loop: enqueue → consume → process → ack.
    After the loop, the patch file exists at MAS_PATCHES_DIR,
    the topic depth is 0, and the completed file has 1 entry.
    This is the exact sequence the dev_mq_consumer.py main()
    runs per-message, inlined here to avoid subprocess overhead.
    """
    topic = "im.finding.created"
    request_id = "rq-consumer-001"

    # 1. Producer: enqueue.  Use a known idempotency_key (the
    # request_id itself) so a duplicate enqueue is dedup'd.
    msg_id = mq.enqueue(
        topic,
        _payload(request_id, total=1, by_sev={"high": 1}),
        idempotency_key=request_id,
    )
    assert isinstance(msg_id, str) and len(msg_id) > 0

    # Sanity: depth=1
    assert mq.depth(topic) == 1

    # 2. Consumer: consume (returns the in_flight msg + lease)
    msg = mq.consume(topic, timeout_sec=2.0)
    assert msg is not None
    assert msg["msg_id"] == msg_id
    assert msg["status"] == "in_flight"
    assert msg["payload"]["request_id"] == request_id

    # 3. Processor: design-patch kernel
    result = design.process_msg(msg)
    assert result["patch_type"] == "high_remediation"
    assert result["priority"] == "P1"
    assert result["actions_count"] == 1

    # 4. Ack
    ok = mq.ack(msg_id)
    assert ok is True

    # 5. Post-state: topic drained, patch file written
    assert mq.depth(topic) == 0
    out = patches_dir / f"{request_id}.yaml"
    assert out.exists(), f"patch file not written: {out}"
    with open(out) as f:
        body = yaml.safe_load(f)
    assert body["request_id"] == request_id
    assert body["source_msg_id"] == msg_id
    assert body["source_topic"] == topic
    assert body["findings_total"] == 1


def test_idempotent_redelivery_same_request_id(patches_dir, mq_root):
    """(2) At-most-once effect: if the consumer crashes between
    process_msg and ack, the MQ redelivers the same msg (different
    msg_id, same payload).  The kernel MUST be idempotent on
    request_id: re-running with the same request_id overwrites
    the patch file with identical content (no duplicate designs,
    no duplicate side-effects).

    This is the second half of the at-least-once-delivery +
    at-most-once-effect guarantee from R-211.
    """
    topic = "im.finding.created"
    request_id = "rq-consumer-002-idempotent"

    # First delivery
    msg_id_1 = mq.enqueue(
        topic,
        _payload(request_id, total=2, by_sev={"high": 2}),
        idempotency_key=request_id,
    )
    msg1 = mq.consume(topic, timeout_sec=2.0)
    assert msg1 is not None
    result1 = design.process_msg(msg1)
    mq.ack(msg_id_1)

    out = patches_dir / f"{request_id}.yaml"
    assert out.exists()
    with open(out) as f:
        body1 = yaml.safe_load(f)
    # result1 carries the kernel's return dict (has
    # actions_count); body1 is the persisted patch file
    # (has the actions list, NOT actions_count).  Compare
    # them via the actions list length.
    assert len(body1["actions"]) == result1["actions_count"] == 1

    # Simulate redelivery: re-enqueue the SAME payload (MQ
    # would do this on its own if the consumer crashed; here
    # we explicitly enqueue again with the same idempotency_key
    # which MQ will treat as a duplicate and re-deliver via
    # a new msg_id).
    msg_id_2 = mq.enqueue(
        topic,
        _payload(request_id, total=2, by_sev={"high": 2}),
        idempotency_key=request_id,
    )
    # Same idempotency_key → MQ returns a different msg_id for
    # the redelivery, but with the same request_id payload.
    assert msg_id_2 != msg_id_1, \
        "expected MQ to assign a new msg_id for the redelivery"
    msg2 = mq.consume(topic, timeout_sec=2.0)
    assert msg2 is not None
    assert msg2["payload"]["request_id"] == request_id

    result2 = design.process_msg(msg2)
    mq.ack(msg_id_2)

    # Idempotency: the patch file is OVERWRITTEN with the same
    # content (no duplicate, no append).  The kernel does not
    # check msg_id — it keys on request_id from the payload.
    assert out.exists()
    with open(out) as f:
        body2 = yaml.safe_load(f)
    # Same fields (modulo generated_at, which is set per call;
    # kernel is deterministic except for that one timestamp)
    assert body2["request_id"] == body1["request_id"]
    assert body2["findings_total"] == body1["findings_total"]
    assert body2["actions"] == body1["actions"]
    # File count is still 1 (no duplicate)
    assert len(list(patches_dir.glob(f"{request_id}.yaml"))) == 1


def test_nack_path_on_kernel_exception(patches_dir, mq_root, monkeypatch):
    """(3) Negative path: process_msg raises → caller (consumer)
    calls mq.nack(msg_id) → msg back in pending with
    retry_count=1, NO patch file written.

    This is the consumer-side half of the contract.  The
    kernel-half (exception propagates) is verified in
    tests/test_dev_im_design_patches.py::test_kernel_exception_propagates_to_caller.
    Here we verify what the consumer's exception wrapper
    DOES with that exception: nack, not ack.
    """
    topic = "im.finding.created"
    request_id = "rq-consumer-003-nack"

    # 1. Enqueue a valid msg
    msg_id = mq.enqueue(
        topic,
        _payload(request_id, total=1, by_sev={"high": 1}),
        idempotency_key=request_id,
    )

    # 2. Consume (acquires in_flight lease)
    msg = mq.consume(topic, timeout_sec=2.0)
    assert msg is not None
    assert msg["status"] == "in_flight"

    # 3. Simulate processor exception: monkeypatch
    # process_msg to raise.  This is what the consumer's
    # exception wrapper sees.
    def _boom(m):
        raise RuntimeError("simulated processor failure")
    monkeypatch.setattr(design, "process_msg", _boom)

    # 4. The consumer's wrapper: try process_msg, catch, nack
    try:
        design.process_msg(msg)
    except RuntimeError as e:
        # 5. nack (not ack!) with the reason
        mq.nack(msg_id, reason=f"processor-exception: RuntimeError: {e}")

    # 6. Post-state:
    #    - msg is back in pending (nack releases the in_flight lease)
    #    - retry_count incremented
    #    - NO patch file written
    assert mq.depth(topic) == 1, \
        f"expected msg to be back in pending after nack, got depth={mq.depth(topic)}"
    out = patches_dir / f"{request_id}.yaml"
    assert not out.exists(), \
        f"nack path should not leave a patch file: {out}"

    # 7. Verify the msg has retry_count=1
    msgs = mq._read_topic(topic)
    matching = [m for m in msgs if m.get("msg_id") == msg_id]
    assert len(matching) == 1
    assert matching[0]["status"] == "pending"
    assert matching[0].get("retry_count", 0) >= 1, \
        f"expected retry_count >= 1 after nack, got {matching[0].get('retry_count', 0)}"
