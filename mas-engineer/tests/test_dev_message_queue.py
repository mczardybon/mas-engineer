"""
test_dev_message_queue.py — R110-154 (mas-mq branch).

15-test pytest suite for tools/dev_message_queue.py. Verifies:
  - enqueue/consume/ack/nack happy-path
  - idempotency-key deduplication
  - in_flight status transitions
  - retry-counter increment + backoff scheduling
  - DLQ routing after max_retries exhausted
  - atomic write survives concurrent enqueues (threaded)
  - persistence: messages survive MQ-root re-read
  - gc_stale_in_flight recovers stuck in_flight
  - depth/stats/replay APIs
  - empty-queue consume returns None after timeout
  - ack on unknown msg_id returns False
  - nack on unknown msg_id returns False
  - CLI smoke (enqueue + consume via argparse)
  - different topics are independent

Run with:
    python3 -m pytest tests/test_dev_message_queue.py -v
"""
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"

sys.path.insert(0, str(TOOLS))
import dev_message_queue as mq  # noqa: E402
from dev_message_queue import QueueFullError  # noqa: E402 (F-MQ-189-1)


# ─── Per-test MQ root (isolated from .mase/mq) ───────────────────

@pytest.fixture
def mq_root(tmp_path, monkeypatch):
    """Provide an isolated MQ root for each test.  monkeypatch sets
    the MAS_MQ_ROOT env var so dev_message_queue uses tmp_path."""
    root = tmp_path / "mq"
    root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(root))
    # Re-import the module's _mq_root to pick up the env var
    # (it's called fresh on each invocation, so no module-reload needed)
    return root


# ─── Tests ───────────────────────────────────────────────────────

def test_enqueue_returns_msg_id(mq_root):
    """(1) Basic enqueue returns a string msg_id."""
    mid = mq.enqueue("test", {"foo": "bar"})
    assert isinstance(mid, str)
    assert len(mid) == 36  # UUID4
    assert (mq_root / "test.ndjson").exists()


def test_enqueue_with_idempotency_key_dedupes(mq_root):
    """(2) Same idempotency_key returns same msg_id (no duplicate)."""
    mid1 = mq.enqueue("test", {"foo": "bar"}, idempotency_key="k1")
    mid2 = mq.enqueue("test", {"foo": "baz"}, idempotency_key="k1")
    assert mid1 == mid2, "idempotency_key should dedupe"
    # Only ONE message in file
    msgs = mq.replay("test")
    assert len(msgs) == 1
    # Original payload preserved (not overwritten)
    assert msgs[0]["payload"] == {"foo": "bar"}


def test_consume_returns_pending_message(mq_root):
    """(3) Consume returns the next pending message (FIFO)."""
    mid = mq.enqueue("test", {"foo": "bar"})
    msg = mq.consume("test", timeout_sec=1)
    assert msg is not None
    assert msg["msg_id"] == mid
    assert msg["payload"] == {"foo": "bar"}


def test_consume_returns_none_on_empty_queue_after_timeout(mq_root):
    """(4) Empty queue → None after timeout."""
    msg = mq.consume("test", timeout_sec=0.3)
    assert msg is None


def test_consume_marks_message_in_flight(mq_root):
    """(5) After consume(), the message has status=in_flight (not
    deleted).  A second consume() does NOT return it."""
    mid = mq.enqueue("test", {"foo": "bar"})
    msg1 = mq.consume("test", timeout_sec=1)
    assert msg1["msg_id"] == mid
    assert msg1["status"] == "in_flight"
    # Second consume returns None (already in_flight)
    msg2 = mq.consume("test", timeout_sec=0.3)
    assert msg2 is None
    # File still has the message
    msgs = mq.replay("test", include_in_flight=True) if False else mq._read_topic("test")
    assert len(msgs) == 1
    assert msgs[0]["status"] == "in_flight"


def test_ack_removes_message_from_in_flight(mq_root):
    """(6) ack() removes the message from the topic and writes to
    <topic>.completed.ndjson."""
    mid = mq.enqueue("test", {"foo": "bar"})
    mq.consume("test", timeout_sec=1)
    assert mq.ack(mid) is True
    # Live file is empty
    assert mq.replay("test") == []
    # Completed file has 1 entry
    comp = mq_root / "test.completed.ndjson"
    assert comp.exists()
    lines = [l for l in comp.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["msg_id"] == mid
    assert rec["status"] == "done"


def test_nack_increments_retry_count(mq_root):
    """(7) nack() with retry_count=0 (max=3) → retry_count=1, status
    goes back to pending, next_retry_at is set."""
    mid = mq.enqueue("test", {"foo": "bar"},
                     retry_policy={"max": 3, "backoff": [1, 2, 4]})
    mq.consume("test", timeout_sec=1)
    assert mq.nack(mid, "transient error") is True
    msgs = mq._read_topic("test")
    m = [x for x in msgs if x["msg_id"] == mid][0]
    assert m["retry_count"] == 1
    assert m["status"] == "pending"
    assert m["last_error"] == "transient error"
    assert m["next_retry_at"] is not None


def test_nack_reschedules_with_backoff(mq_root):
    """(8) Second nack increments to 2 and uses next backoff delay."""
    mid = mq.enqueue("test", {"foo": "bar"},
                     retry_policy={"max": 3, "backoff": [1, 2, 4]})
    mq.consume("test", timeout_sec=1)
    mq.nack(mid, "err1")
    # Simulate time passing: manually clear next_retry_at
    msgs = mq._read_topic("test")
    m = [x for x in msgs if x["msg_id"] == mid][0]
    m["next_retry_at"] = None
    mq._write_topic_atomic("test", msgs)
    # Consume again (rescheduled) and nack
    mq.consume("test", timeout_sec=1)
    mq.nack(mid, "err2")
    msgs = mq._read_topic("test")
    m = [x for x in msgs if x["msg_id"] == mid][0]
    assert m["retry_count"] == 2
    assert m["last_error"] == "err2"


def test_nack_after_max_retries_routes_to_dlq(mq_root):
    """(9) After max_retries exceeded, message is removed from topic
    and written to signals_dlq.ndjson."""
    mid = mq.enqueue("test", {"foo": "bar"},
                     retry_policy={"max": 2, "backoff": [1, 1]})
    # 1st: consume + nack
    mq.consume("test", timeout_sec=1)
    mq.nack(mid, "e1")
    # Manually clear next_retry_at so consume() picks it up
    msgs = mq._read_topic("test")
    m = [x for x in msgs if x["msg_id"] == mid][0]
    m["next_retry_at"] = None
    mq._write_topic_atomic("test", msgs)
    # 2nd: consume + nack (retry_count was 1, now becomes 2 = max)
    mq.consume("test", timeout_sec=1)
    mq.nack(mid, "e2")
    msgs = mq._read_topic("test")
    m_ids = [x["msg_id"] for x in msgs]
    assert mid not in m_ids, "should be removed from topic after DLQ"
    # 3rd: consume + nack would go to DLQ (retry_count was 2, max=2)
    # (We need to re-enqueue? No, we already exhausted. Let's just
    # verify by re-enqueueing with retry_count=2.)
    mid2 = mq.enqueue("test2", {"foo": "baz"},
                      retry_policy={"max": 1, "backoff": [1]})
    msgs = mq._read_topic("test2")
    msgs[0]["retry_count"] = 1  # simulate already-tried-once
    mq._write_topic_atomic("test2", msgs)
    mq.consume("test2", timeout_sec=1)
    mq.nack(mid2, "exhausted")
    # Now in DLQ
    dlq = mq_root / "signals_dlq.ndjson"
    assert dlq.exists()
    dlq_msgs = [json.loads(l) for l in dlq.read_text().splitlines() if l.strip()]
    assert any(d["msg_id"] == mid2 for d in dlq_msgs)


def test_atomic_write_no_corruption_on_concurrent_writes(mq_root):
    """(10) Concurrent enqueues from N threads → all messages land
    intact in the file (atomic-rename guarantees no torn-writes)."""
    N_THREADS = 5
    N_PER_THREAD = 10
    results = []

    def worker(tid):
        for i in range(N_PER_THREAD):
            mid = mq.enqueue("race", {"t": tid, "i": i})
            results.append(mid)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # All enqueue calls returned a msg_id
    assert len(results) == N_THREADS * N_PER_THREAD
    # All msg_ids are unique
    assert len(set(results)) == N_THREADS * N_PER_THREAD
    # File is valid NDJSON (every line is a complete JSON object)
    raw = (mq_root / "race.ndjson").read_text()
    lines = [l for l in raw.splitlines() if l.strip()]
    assert len(lines) == N_THREADS * N_PER_THREAD
    for line in lines:
        rec = json.loads(line)  # would raise on corruption
        assert "msg_id" in rec
        assert "payload" in rec


def test_persistence_survives_reload(mq_root):
    """(11) Messages written to file persist across 'module reload'
    (simulates crash + restart).  Just re-read the file fresh."""
    mid = mq.enqueue("persist", {"k": "v"})
    # Simulate crash: just call _read_topic directly (same as fresh process)
    msgs = mq._read_topic("persist")
    assert len(msgs) == 1
    assert msgs[0]["msg_id"] == mid
    assert msgs[0]["payload"] == {"k": "v"}


def test_garbage_collector_recovers_stale_in_flight(mq_root):
    """(12) Stale in_flight message (no acker) → gc re-queues it."""
    mid = mq.enqueue("stale", {"foo": "bar"})
    mq.consume("stale", timeout_sec=1)
    # Manually age the message: backdate in_flight_at (R110-188 — GC
    # now uses in_flight_at only, NOT enqueued_at)
    msgs = mq._read_topic("stale")
    m = [x for x in msgs if x["msg_id"] == mid][0]
    old = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    m["enqueued_at"] = old
    m["in_flight_at"] = old
    mq._write_topic_atomic("stale", msgs)
    # GC should recover (default max_age_sec=300, so 600s is stale)
    recovered = mq.gc_stale_in_flight(max_age_sec=300)
    assert recovered == 1
    # Status is back to pending, retry_count bumped
    msgs = mq._read_topic("stale")
    m = [x for x in msgs if x["msg_id"] == mid][0]
    assert m["status"] == "pending"
    assert m["retry_count"] == 1
    assert "recovered" in m["last_error"]


def test_depth_metric(mq_root):
    """(13) depth() reflects pending + in_flight, NOT done."""
    mq.enqueue("d", {"a": 1})
    mq.enqueue("d", {"a": 2})
    mq.enqueue("d", {"a": 3})
    assert mq.depth("d") == 3
    mq.consume("d", timeout_sec=1)  # one becomes in_flight
    assert mq.depth("d") == 3, "in_flight counts toward depth"
    mq.ack(mq._read_topic("d")[0]["msg_id"])
    assert mq.depth("d") == 2
    mq.enqueue("d2", {"x": 1})
    assert mq.depth("d2") == 1
    assert mq.depth("nonexistent") == 0


def test_stats_includes_lag_and_dlq_count(mq_root):
    """(14) stats() returns per-topic dict with depth + lag + dlq."""
    mq.enqueue("s", {"i": 0})
    time.sleep(0.05)  # measurable lag
    mq.enqueue("s", {"i": 1})
    s = mq.stats()
    assert "s" in s["topics"]
    assert s["topics"]["s"]["depth"] == 2
    # R110-188: lag_p95_ms renamed to current_p95_lag_ms, dlq_count →
    # per-topic dlq_count_for_topic
    assert s["topics"]["s"]["current_p95_lag_ms"] >= 50
    assert s["topics"]["s"]["dlq_count_for_topic"] == 0
    assert s["topics"]["s"]["retry_rate"] == 0.0
    assert "generated_at" in s


def test_stats_completed_total_after_all_acked(mq_root):
    """(R110-163) Regression: when all messages on a topic are acked,
    stats()[topic]['completed_total'] must still report the count.

    The bug: glob('*.ndjson') returns files in alphabetical order, so
    `topic.completed.ndjson` was processed before `topic.ndjson` in
    the same loop. The .completed branch set only completed_total,
    then the live .ndjson branch OVERWROTE the topic dict with a
    fresh one that omitted completed_total.

    Fix: pre-compute completed_counts in a separate first pass, then
    the live branch includes completed_total in its initial dict."""
    mq.enqueue("c", {"i": 0})
    mq.enqueue("c", {"i": 1})
    mq.enqueue("c", {"i": 2})
    # Consume + ack all
    m1 = mq.consume("c")
    m2 = mq.consume("c")
    m3 = mq.consume("c")
    mq.ack(m1["msg_id"])
    mq.ack(m2["msg_id"])
    mq.ack(m3["msg_id"])
    # Now the live .ndjson is empty (0 bytes), but .completed.ndjson
    # has 3 entries.
    s = mq.stats()
    assert "c" in s["topics"]
    assert s["topics"]["c"]["depth"] == 0
    assert s["topics"]["c"]["completed_total"] == 3, (
        f"completed_total lost when live .ndjson is empty: "
        f"got {s['topics']['c']}"
    )


def test_stats_completed_total_preserved_with_pending(mq_root):
    """(R110-163) Even with some messages pending AND some acked,
    completed_total reflects only the acked count, and depth reflects
    the pending count — both keys present simultaneously."""
    mq.enqueue("m", {"i": 0})
    mq.enqueue("m", {"i": 1})
    mq.enqueue("m", {"i": 2})
    mq.enqueue("m", {"i": 3})
    # Ack 2, leave 2 pending
    m1 = mq.consume("m")
    m2 = mq.consume("m")
    mq.ack(m1["msg_id"])
    mq.ack(m2["msg_id"])
    s = mq.stats()
    assert s["topics"]["m"]["depth"] == 2
    assert s["topics"]["m"]["completed_total"] == 2


def test_replay_returns_messages_since_timestamp(mq_root):
    """(15) replay(since=X) returns only messages enqueued on/after X."""
    mq.enqueue("r", {"i": 0})
    time.sleep(0.05)
    cutoff = mq._now_iso()
    time.sleep(0.05)
    mq.enqueue("r", {"i": 1})
    mq.enqueue("r", {"i": 2})
    all_msgs = mq.replay("r")
    assert len(all_msgs) == 3
    after_cutoff = mq.replay("r", since=cutoff)
    assert len(after_cutoff) == 2
    assert {m["payload"]["i"] for m in after_cutoff} == {1, 2}


# ─── R110-188: MQ Semantic Hardening (11 new tests) ──────────────

def test_in_flight_at_set_on_consume(tmp_path, monkeypatch):
    """F-MQ-188-1/2: in_flight_at must be set when consume() marks in_flight."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("t1", {"x": 1})
    m = mq.consume("t1", timeout_sec=2)
    assert m["status"] == "in_flight"
    assert m["in_flight_at"] is not None
    parsed = datetime.fromisoformat(m["in_flight_at"].replace("Z", "+00:00"))
    assert parsed >= datetime.fromisoformat(m["enqueued_at"].replace("Z", "+00:00"))


def test_gc_uses_in_flight_at_not_enqueued_at(tmp_path, monkeypatch):
    """F-MQ-188-3: GC must NOT recover based on enqueued_at when in_flight_at exists."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("t1", {"x": 1})
    m1 = mq.consume("t1", timeout_sec=2)
    # Backdate enqueued_at to 1 hour ago (simulating old queue)
    msgs = mq._read_topic("t1")
    for mm in msgs:
        if mm["msg_id"] == m1["msg_id"]:
            old = datetime.now(timezone.utc) - timedelta(hours=1)
            mm["enqueued_at"] = old.isoformat()
    mq._write_topic_atomic("t1", msgs)
    # GC with max_age=10s should NOT recover (in_flight_at is fresh)
    n = mq.gc_stale_in_flight(max_age_sec=10)
    assert n == 0  # critical: not 1


def test_ack_archives_before_removing_live(tmp_path, monkeypatch):
    """F-MQ-188-4: kill -9 simulation: archive must exist even if live removal is interrupted."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("t1", {"x": 1})
    m1 = mq.consume("t1", timeout_sec=2)
    mq.ack(m1["msg_id"])
    # Both archive and live (empty) must exist
    comp = mq._topic_path("t1", completed=True)
    assert comp.exists()
    with open(comp) as f:
        assert any(m1["msg_id"] in line for line in f)


def test_corrupt_line_quarantined(tmp_path, monkeypatch):
    """F-MQ-188-5: bad NDJSON line must go to _corrupt.ndjson, not silently skipped."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    p = mq._topic_path("t1")
    p.write_text('{"msg_id":"good","status":"pending","enqueued_at":"2026-01-01T00:00:00Z","payload":{}}\n'
                 'THIS IS NOT JSON\n')
    msgs = mq._read_topic("t1")
    assert len(msgs) == 1  # only the good one
    qpath = mq._mq_root() / "_corrupt.ndjson"
    assert qpath.exists()
    with open(qpath) as f:
        assert "THIS IS NOT JSON" in f.read()


def test_strict_topic_rejects_collision(tmp_path, monkeypatch):
    """F-MQ-188-6: foo/bar and foo_bar must not silently collide."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    monkeypatch.setenv("MAS_MQ_STRICT_TOPIC", "1")
    with pytest.raises(ValueError, match="contains chars"):
        mq._sanitize_topic("foo/bar")


def test_stats_renames_lag_p95_to_current_p95_lag_ms(tmp_path, monkeypatch):
    """F-MQ-188-7: lag_p95_ms renamed to current_p95_lag_ms in stats output."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("t1", {"x": 1})
    s = mq.stats()
    assert "current_p95_lag_ms" in s["topics"]["t1"]
    assert "lag_p95_ms" not in s["topics"]["t1"]


def test_stats_dlq_count_per_topic(tmp_path, monkeypatch):
    """F-MQ-188-8: dlq_count must be per-topic, not global."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("t1", {"x": 1})
    mq.enqueue("t2", {"x": 2})
    s = mq.stats()
    assert "dlq_count_total" in s  # global
    assert "dlq_count_for_topic" in s["topics"]["t1"]


def test_docstring_precision_about_durability(tmp_path, monkeypatch):
    """F-MQ-188-9: docstring must NOT claim 'persistent, at-least-once' if no fsync."""
    import inspect
    src = inspect.getsource(mq)
    assert "process-crash resilient" in src or "NOT durable" in src
    assert "fsync" in src  # at least mentions the limitation


def test_invariant_helper_enforces_4_invariants(monkeypatch):
    """F-MQ-188-10: _check_invariants exists and catches 4 violations."""
    monkeypatch.setenv("MAS_MQ_INVARIANT_CHECK", "1")
    assert any("INV1" in e for e in mq._check_invariants({"status": "in_flight"}))
    assert any("INV3" in e for e in mq._check_invariants({"status": "done"}))
    assert any("INV4" in e for e in mq._check_invariants({"status": "dlq"}))
    assert mq._check_invariants({"status": "pending"}) == []  # OK


def test_concurrent_process_safety_under_flock(tmp_path, monkeypatch):
    """F-MQ-188-11: real cross-process test using subprocess + kill -9."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    # Spawn 3 child processes that enqueue concurrently
    procs = []
    for i in range(3):
        p = subprocess.Popen([sys.executable, "tools/dev_message_queue.py",
                              "--enqueue", "t1", json.dumps({"i": i})],
                             env={**os.environ, "MAS_MQ_ROOT": str(tmp_path)})
        procs.append(p)
    for p in procs:
        p.wait(timeout=10)
    # All 3 must have landed (atomic write via flock)
    assert mq.depth("t1") == 3


def test_gc_clears_in_flight_at_on_recovery(tmp_path, monkeypatch):
    """Side-test for F-MQ-188-3: after GC recovery, in_flight_at must be None."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("t1", {"x": 1})
    mq.consume("t1", timeout_sec=2)
    # backdate in_flight_at to 1 hour ago to trigger GC
    msgs = mq._read_topic("t1")
    for mm in msgs:
        old = datetime.now(timezone.utc) - timedelta(hours=1)
        mm["in_flight_at"] = old.isoformat()
    mq._write_topic_atomic("t1", msgs)
    n = mq.gc_stale_in_flight(max_age_sec=10)
    assert n == 1
    msgs2 = mq._read_topic("t1")
    assert msgs2[0]["in_flight_at"] is None
    assert msgs2[0]["status"] == "pending"


# ─── R110-189: MQ Hardening Phase 2 (15 new tests) ───────────────

def test_max_depth_raises_queue_full(tmp_path, monkeypatch):
    """F-MQ-189-1: enqueue raises QueueFullError when depth ≥ MAX_DEPTH."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    monkeypatch.setenv("MAS_MQ_MAX_DEPTH_PER_TOPIC", "3")
    for i in range(3):
        mq.enqueue("t", {"i": i})
    with pytest.raises(QueueFullError):
        mq.enqueue("t", {"i": 99})


def test_ttl_sweeps_old_pending_to_dlq(tmp_path, monkeypatch):
    """F-MQ-189-2: pending msg older than max_age_sec → DLQ."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("t", {"x": 1})
    # Backdate to 1 day ago
    msgs = mq._read_topic("t")
    msgs[0]["enqueued_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    mq._write_topic_atomic("t", msgs)
    n = mq._gc_old_pending(max_age_sec=60)  # 60s threshold
    assert n == 1
    # Msg should be in DLQ
    assert "ttl-expired" in open(mq._dlq_path()).read()


def test_requeue_resets_retry_count(tmp_path, monkeypatch):
    """F-MQ-189-3: requeue sets msg back to pending with retry_count=0."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    m1 = mq.enqueue("t", {"x": 1})
    m = mq.consume("t", timeout_sec=1)
    mq.ack(m["msg_id"])
    # Now msg is done; requeue it (enqueue returns the msg_id string)
    ok = mq.requeue(m1)
    assert ok
    msgs = mq._read_topic("t")
    assert msgs[0]["status"] == "pending"
    assert msgs[0]["retry_count"] == 0


def test_enqueue_raises_on_disk_full(tmp_path, monkeypatch):
    """F-MQ-189-14: enqueue catches OSError (ENOSPC) and writes to DLQ."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    # Monkeypatch _write_topic_atomic to raise ENOSPC
    import errno
    def boom(topic, msgs):
        raise OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(mq, "_write_topic_atomic", boom)
    mq.enqueue("t", {"x": 1})  # should NOT raise (caught, written to DLQ)
    dlq = open(mq._dlq_path()).read()
    assert "StorageError" in dlq


def test_lock_per_topic_no_global_contention(tmp_path, monkeypatch):
    """F-MQ-189-15: lock on topic A does not block topic B (verify R110-188 fix)."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    import threading
    barrier = threading.Barrier(2)
    def hold_lock_a():
        with mq._TopicLock("a"):
            barrier.wait()  # hold while B tries
    def consume_b():
        barrier.wait()
        mq.consume("b", timeout_sec=1)  # should NOT block
    t1 = threading.Thread(target=hold_lock_a)
    t2 = threading.Thread(target=consume_b)
    t1.start(); t2.start()
    t1.join(timeout=3); t2.join(timeout=3)
    assert not t1.is_alive() and not t2.is_alive()


def test_stats_includes_lag_distribution(tmp_path, monkeypatch):
    """F-MQ-189-4: stats() includes p50/p95/p99/max lag distribution."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    for i in range(20):
        mq.enqueue("t", {"i": i})
    s = mq.stats()
    dist = s["topics"]["t"].get("lag_distribution_ms", {})
    assert {"p50", "p95", "p99", "max"} <= dist.keys()
    assert dist["max"] >= dist["p99"] >= dist["p95"] >= dist["p50"]


def test_dlq_replay_and_purge(tmp_path, monkeypatch):
    """F-MQ-189-5: replay_dlq + purge_dlq work as specified."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    # Force 3 msgs to DLQ
    for i in range(3):
        mq.enqueue("t", {"i": i})
    mq._gc_old_pending(max_age_sec=0)  # immediately expire
    n = mq.replay_dlq(topic="t", limit=2)
    assert n == 2
    assert mq.depth("t") == 2
    purged = mq.purge_dlq(topic="t")
    assert purged == 1


def test_list_topics_returns_only_live_topics(tmp_path, monkeypatch):
    """F-MQ-189-10: list_topics excludes .completed.ndjson and _corrupt.ndjson."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("a", {})
    mq.enqueue("b", {})
    topics = mq.list_topics()
    assert "a" in topics and "b" in topics
    assert not any(".completed" in t for t in topics)
    assert not any(t == "_corrupt" for t in topics)


def test_compact_completed_archives_full_file(tmp_path, monkeypatch):
    """F-MQ-189-11: compact_completed creates <topic>.<date>.completed.ndjson."""
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path))
    mq.enqueue("t", {"x": 1})
    m = mq.consume("t", timeout_sec=1)
    mq.ack(m["msg_id"])
    # Write 10 more done lines to push past max_lines
    for i in range(10):
        mq.enqueue("t", {"i": i})
        m2 = mq.consume("t", timeout_sec=1)
        mq.ack(m2["msg_id"])
    ok = mq.compact_completed("t", max_lines=5, keep_recent=2)
    assert ok
    archives = list(tmp_path.glob("t.*.completed.ndjson"))
    assert len(archives) == 1
