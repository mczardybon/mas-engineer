#!/usr/bin/env python3
"""dev_message_queue.py — File-Based Message Queue v1.0.0
=========================================================

A persistent, at-least-once, topic-based message queue for mas-engineer
sub-recipes and workflows. Solves the "direct delegation becomes a
bottleneck" problem (R110-153 design): parallel agents can enqueue
signals / dispatches / results without blocking, and consumers
(dashboard, signal-handler, recovery-loop) can pick them up
asynchronously with retry, backoff, and DLQ semantics.

Design (R110-153):
  - File-based, no external broker (Redis/RabbitMQ not required)
  - Topics = separate NDJSON files in .mase/mq/<topic>.ndjson
  - At-least-once delivery: in_flight messages are re-queued on crash
  - Per-message retry policy with exponential backoff
  - Dead-letter-queue (DLQ) for messages exceeding max_retries
  - Idempotency: enqueue with idempotency_key dedupes duplicates
  - File-locking (fcntl.flock) for concurrent-process safety
  - Atomic writes (write to .tmp, then os.rename)

Public API:
  enqueue(topic, payload, *, retry_policy=None,
          idempotency_key=None, request_id=None) -> msg_id
  consume(topic, timeout_sec=5.0, *, consumer_id=None) -> dict | None
  ack(msg_id) -> bool
  nack(msg_id, reason) -> bool
  depth(topic) -> int
  stats() -> dict
  replay(topic, since=None) -> list

Storage layout:
  .mase/mq/
    ├── cpdone.ndjson
    ├── cpdone.completed.ndjson
    ├── error.ndjson
    ├── signals_dlq.ndjson
    ├── _locks/
    │   └── <topic>.lock
    └── stats.json

CLI:
  python3 dev_message_queue.py --enqueue <topic> '<json-payload>'
      [--idempotency-key KEY] [--request-id RID]
      [--max-retries N] [--backoff 1,2,4,8]
  python3 dev_message_queue.py --consume <topic> [--timeout N] [--consumer-id ID]
  python3 dev_message_queue.py --ack <msg_id>
  python3 dev_message_queue.py --nack <msg_id> --reason REASON
  python3 dev_message_queue.py --depth <topic>
  python3 dev_message_queue.py --stats
  python3 dev_message_queue.py --replay <topic> [--since ISO8601]
  python3 dev_message_queue.py --gc  # garbage-collect stale in_flight
"""
import argparse
import fcntl
import json
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Storage paths ───────────────────────────────────────────────

# Default MQ root: <workspace>/.mase/mq.  Allows override via env
# (used by tests to point at tmp_path without polluting .mase/).
DEFAULT_MQ_ROOT = ".mase/mq"


def _mq_root() -> Path:
    """Resolve MQ root directory (env override for tests)."""
    root = os.environ.get("MAS_MQ_ROOT")
    if root:
        p = Path(root)
    else:
        p = Path.cwd() / DEFAULT_MQ_ROOT
    p.mkdir(parents=True, exist_ok=True)
    (p / "_locks").mkdir(exist_ok=True)
    return p


def _topic_path(topic: str, *, completed: bool = False) -> Path:
    """NDJSON file for a topic.  `completed=True` → archive file."""
    suffix = ".completed.ndjson" if completed else ".ndjson"
    # Sanitize topic name: only [a-zA-Z0-9_-]
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in topic)
    return _mq_root() / f"{safe}{suffix}"


def _lock_path(topic: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in topic)
    return _mq_root() / "_locks" / f"{safe}.lock"


def _dlq_path() -> Path:
    return _mq_root() / "signals_dlq.ndjson"


def _stats_path() -> Path:
    return _mq_root() / "stats.json"


# ─── Message schema ──────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _make_msg(topic: str, payload: dict, *,
              retry_policy: Optional[dict] = None,
              idempotency_key: Optional[str] = None,
              request_id: Optional[str] = None) -> dict:
    """Create a new message record.  Retry policy defaults are sane
    (max 3, exponential backoff 1/2/4/8s)."""
    rp = retry_policy or {}
    return {
        "msg_id": str(uuid.uuid4()),
        "idempotency_key": idempotency_key,
        "request_id": request_id,
        "topic": topic,
        "payload": payload,
        "enqueued_at": _now_iso(),
        "next_retry_at": None,
        "retry_count": 0,
        "max_retries": int(rp.get("max", 3)),
        "backoff_schedule": rp.get("backoff", [1, 2, 4, 8]),
        "status": "pending",  # pending | in_flight | done | dlq
        "consumer_id": None,
        "last_error": None,
    }


# ─── File-locking helpers ────────────────────────────────────────

class _TopicLock:
    """Context manager for per-topic file-lock (fcntl.flock).

    Blocks until lock acquired.  Used to make enqueue/consume
    atomic across concurrent processes."""

    def __init__(self, topic: str):
        self.path = _lock_path(topic)
        self.fd = None

    def __enter__(self):
        self.fd = open(self.path, "w")
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()
        return False


# ─── NDJSON I/O (with atomic-write) ──────────────────────────────

def _read_topic(topic: str, *, include_in_flight: bool = True) -> list:
    """Read all messages for a topic.  Atomic with respect to writers
    because the underlying NDJSON file is replaced (not appended-during-
    read)."""
    path = _topic_path(topic)
    if not path.exists():
        return []
    msgs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not include_in_flight and m.get("status") == "in_flight":
                continue
            msgs.append(m)
    return msgs


def _write_topic_atomic(topic: str, msgs: list) -> None:
    """Atomic write: write to .tmp, then os.replace() to the real path.
    Safe across processes because OS guarantees rename is atomic."""
    path = _topic_path(topic)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        for m in msgs:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


# ─── Public API: enqueue ─────────────────────────────────────────

def enqueue(topic: str, payload: dict, *,
            retry_policy: Optional[dict] = None,
            idempotency_key: Optional[str] = None,
            request_id: Optional[str] = None) -> str:
    """Enqueue a message.  Returns msg_id.

    Idempotency: if `idempotency_key` is provided AND a pending/in_flight
    message with the same key already exists, return the existing
    msg_id instead of creating a new message (deduplication)."""
    with _TopicLock(topic):
        # Idempotency check
        if idempotency_key:
            for m in _read_topic(topic):
                if (m.get("idempotency_key") == idempotency_key
                        and m.get("status") in ("pending", "in_flight")):
                    return m["msg_id"]

        msg = _make_msg(topic, payload,
                        retry_policy=retry_policy,
                        idempotency_key=idempotency_key,
                        request_id=request_id)
        msgs = _read_topic(topic)
        msgs.append(msg)
        _write_topic_atomic(topic, msgs)
    return msg["msg_id"]


# ─── Public API: consume ─────────────────────────────────────────

def consume(topic: str, timeout_sec: float = 5.0, *,
            consumer_id: Optional[str] = None) -> Optional[dict]:
    """Consume the next pending message (FIFO order).

    Returns the message dict and marks it `in_flight`.  The message
    stays in the topic file until `ack()` or `nack()` is called.
    Returns None on timeout (no message available).

    Retry-aware: messages with `next_retry_at` in the future are
    skipped (treated as not yet ready)."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        with _TopicLock(topic):
            msgs = _read_topic(topic)
            now = datetime.now(timezone.utc)
            for m in msgs:
                if m.get("status") != "pending":
                    continue
                # Skip if retry-scheduled in future
                next_retry = _parse_iso(m.get("next_retry_at") or "")
                if next_retry and next_retry > now:
                    continue
                # Mark in_flight
                m["status"] = "in_flight"
                m["consumer_id"] = consumer_id or f"anon-{os.getpid()}"
                _write_topic_atomic(topic, msgs)
                return m
        # No message available, sleep briefly before next attempt
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
    return None


# ─── Public API: ack / nack ──────────────────────────────────────

def _find_msg(msg_id: str) -> Optional[tuple]:
    """Find a message by msg_id across all topics.  Returns
    (topic, msg_dict) or None."""
    if not _mq_root().exists():
        return None
    for ndjson in _mq_root().glob("*.ndjson"):
        # Skip lock-files and DLQ (DLQ handled separately)
        if ndjson.name.startswith("_") or ndjson.name == "signals_dlq.ndjson":
            continue
        topic = ndjson.name.replace(".ndjson", "")
        try:
            with _TopicLock(topic):
                msgs = _read_topic(topic)
                for i, m in enumerate(msgs):
                    if m.get("msg_id") == msg_id:
                        return topic, (i, m, msgs)
        except Exception:
            continue
    return None


def ack(msg_id: str) -> bool:
    """Acknowledge a message: remove from topic file, append to
    `<topic>.completed.ndjson`.  Returns True on success."""
    found = _find_msg(msg_id)
    if not found:
        return False
    topic, (idx, msg, msgs) = found
    with _TopicLock(topic):
        # Re-read to avoid races (msg may have changed since _find_msg)
        msgs = _read_topic(topic)
        if idx >= len(msgs) or msgs[idx].get("msg_id") != msg_id:
            return False
        msgs.pop(idx)
        _write_topic_atomic(topic, msgs)
        # Archive
        msg["status"] = "done"
        msg["acked_at"] = _now_iso()
        comp_path = _topic_path(topic, completed=True)
        with open(comp_path, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    return True


def nack(msg_id: str, reason: str) -> bool:
    """Negative-acknowledge: increment retry_count, reschedule with
    backoff, OR route to DLQ if max_retries exhausted.

    Returns True on success (whether rescheduled or DLQ'd)."""
    found = _find_msg(msg_id)
    if not found:
        return False
    topic, (idx, msg, msgs) = found
    with _TopicLock(topic):
        msgs = _read_topic(topic)
        if idx >= len(msgs) or msgs[idx].get("msg_id") != msg_id:
            return False
        m = msgs[idx]
        m["retry_count"] = m.get("retry_count", 0) + 1
        m["last_error"] = reason
        if m["retry_count"] >= m.get("max_retries", 3):
            # Exhausted → DLQ
            m["status"] = "dlq"
            m["dlq_at"] = _now_iso()
            with open(_dlq_path(), "a") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
            msgs.pop(idx)
        else:
            # Reschedule with backoff
            schedule = m.get("backoff_schedule", [1, 2, 4, 8])
            delay = schedule[min(m["retry_count"] - 1, len(schedule) - 1)]
            m["next_retry_at"] = (
                datetime.now(timezone.utc).timestamp() + delay
            )
            from datetime import datetime as _dt
            m["next_retry_at"] = _dt.fromtimestamp(
                m["next_retry_at"], tz=timezone.utc
            ).isoformat()
            m["status"] = "pending"
            m["consumer_id"] = None
        _write_topic_atomic(topic, msgs)
    return True


# ─── Public API: depth / stats / replay ──────────────────────────

def depth(topic: str) -> int:
    """Number of pending + in_flight messages for a topic."""
    return sum(1 for m in _read_topic(topic)
               if m.get("status") in ("pending", "in_flight"))


def _lag_ms(msg: dict) -> Optional[int]:
    """Milliseconds since enqueue (for a message).  None if no
    enqueued_at."""
    enq = _parse_iso(msg.get("enqueued_at") or "")
    if not enq:
        return None
    return int((datetime.now(timezone.utc) - enq).total_seconds() * 1000)


def stats() -> dict:
    """Aggregate stats across all topics.  Shape:
        {"topics": {<topic>: {"depth": N, "lag_p95_ms": N, "dlq_count": N,
                               "retry_rate": 0.0, "completed_total": N}},
         "generated_at": ISO8601}
    """
    out = {"topics": {}, "generated_at": _now_iso()}
    if not _mq_root().exists():
        return out
    # R110-163: pre-compute completed counts per topic BEFORE
    # the live scan.  Otherwise glob() iteration order (alphabetical:
    # `dispatches.completed.ndjson` < `dispatches.ndjson`) processes
    # the .completed file first (sets only completed_total), then
    # the live .ndjson branch overwrites the topic dict with a new
    # one that omits completed_total.
    completed_counts = {}
    for ndjson in _mq_root().glob("*.ndjson"):
        if ndjson.name.startswith("_"):
            continue
        if ndjson.name == "signals_dlq.ndjson":
            continue
        if ndjson.name.endswith(".completed.ndjson"):
            base = ndjson.name.replace(".completed.ndjson", "")
            try:
                with open(ndjson) as f:
                    completed_counts[base] = sum(1 for _ in f)
            except OSError:
                completed_counts[base] = 0
    for ndjson in _mq_root().glob("*.ndjson"):
        if ndjson.name.startswith("_"):
            continue
        if ndjson.name == "signals_dlq.ndjson":
            continue
        topic = ndjson.name.replace(".ndjson", "")
        if ndjson.name.endswith(".completed.ndjson"):
            continue  # already counted in completed_counts
        live = _read_topic(topic)
        lats = sorted([l for l in (_lag_ms(m) for m in live) if l is not None])
        lag_p95 = lats[int(0.95 * len(lats))] if lats else 0
        retried = sum(1 for m in live if m.get("retry_count", 0) > 0)
        out["topics"][topic] = {
            "depth": sum(1 for m in live
                         if m.get("status") in ("pending", "in_flight")),
            "lag_p95_ms": lag_p95,
            "dlq_count": _dlq_count(),
            "retry_rate": (retried / len(live)) if live else 0.0,
            "completed_total": completed_counts.get(topic, 0),
        }
    return out


def _dlq_count() -> int:
    p = _dlq_path()
    if not p.exists():
        return 0
    return sum(1 for _ in open(p))


def replay(topic: str, since: Optional[str] = None) -> list:
    """Re-read all messages for a topic (for crash-recovery / audit).
    If `since` (ISO8601) is given, only return messages enqueued
    on/after that time."""
    cutoff = _parse_iso(since) if since else None
    out = []
    for m in _read_topic(topic):
        enq = _parse_iso(m.get("enqueued_at") or "")
        if cutoff and enq and enq < cutoff:
            continue
        out.append(m)
    return out


# ─── Public API: garbage-collector ───────────────────────────────

def gc_stale_in_flight(max_age_sec: float = 300.0) -> int:
    """Recover messages that have been `in_flight` longer than
    `max_age_sec` (default 5 min).  Re-queues them (status=pending,
    retry_count+=1, next_retry_at=now+1s).  Returns count recovered.

    Run periodically (e.g., from a cron or before each consume() call)."""
    recovered = 0
    if not _mq_root().exists():
        return 0
    now = datetime.now(timezone.utc)
    for ndjson in _mq_root().glob("*.ndjson"):
        if ndjson.name.startswith("_") or ndjson.name == "signals_dlq.ndjson":
            continue
        if ndjson.name.endswith(".completed.ndjson"):
            continue
        topic = ndjson.name.replace(".ndjson", "")
        with _TopicLock(topic):
            msgs = _read_topic(topic)
            changed = False
            for m in msgs:
                if m.get("status") != "in_flight":
                    continue
                # Heuristic: if no `in_flight_at` field, use enqueued_at
                ref = _parse_iso(m.get("in_flight_at") or m.get("enqueued_at") or "")
                if not ref:
                    continue
                age = (now - ref).total_seconds()
                if age < max_age_sec:
                    continue
                # Recover: back to pending with retry++
                m["status"] = "pending"
                m["retry_count"] = m.get("retry_count", 0) + 1
                m["consumer_id"] = None
                m["next_retry_at"] = now.isoformat()
                m["last_error"] = f"stale in_flight (age={age:.0f}s), recovered"
                changed = True
                recovered += 1
            if changed:
                _write_topic_atomic(topic, msgs)
    return recovered


# ─── CLI ─────────────────────────────────────────────────────────

def _cli():
    p = argparse.ArgumentParser(
        description="dev_message_queue.py — file-based message queue")
    p.add_argument("--mq-root", default=None,
                   help="Override MQ root dir (default: .mase/mq)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--enqueue", nargs=2, metavar=("TOPIC", "PAYLOAD_JSON"),
                   help="Enqueue payload (JSON string) on topic")
    g.add_argument("--consume", metavar="TOPIC",
                   help="Consume next message from topic")
    g.add_argument("--ack", metavar="MSG_ID", help="Ack a message")
    g.add_argument("--nack", metavar="MSG_ID", help="Nack a message")
    g.add_argument("--depth", metavar="TOPIC", help="Queue depth")
    g.add_argument("--stats", action="store_true", help="Aggregate stats")
    g.add_argument("--replay", metavar="TOPIC",
                   help="Replay all messages for topic")
    g.add_argument("--gc", action="store_true",
                   help="Garbage-collect stale in_flight")
    p.add_argument("--idempotency-key", default=None)
    p.add_argument("--request-id", default=None)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--backoff", default="1,2,4,8",
                   help="Comma-separated backoff in seconds")
    p.add_argument("--reason", default="unspecified",
                   help="Reason for --nack")
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--consumer-id", default=None)
    p.add_argument("--since", default=None,
                   help="ISO8601 cutoff for --replay")
    args = p.parse_args()

    if args.mq_root:
        os.environ["MAS_MQ_ROOT"] = args.mq_root

    if args.enqueue:
        topic, payload_str = args.enqueue
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid JSON payload: {e}", file=sys.stderr)
            return 2
        backoff = [int(x) for x in args.backoff.split(",")]
        msg_id = enqueue(
            topic, payload,
            retry_policy={"max": args.max_retries, "backoff": backoff},
            idempotency_key=args.idempotency_key,
            request_id=args.request_id,
        )
        print(msg_id)
        return 0
    if args.consume:
        msg = consume(args.consume, timeout_sec=args.timeout,
                      consumer_id=args.consumer_id)
        if msg is None:
            return 1  # timeout
        print(json.dumps(msg, ensure_ascii=False))
        return 0
    if args.ack:
        return 0 if ack(args.ack) else 1
    if args.nack:
        return 0 if nack(args.nack, args.reason) else 1
    if args.depth:
        print(depth(args.depth))
        return 0
    if args.stats:
        print(json.dumps(stats(), ensure_ascii=False, indent=2))
        return 0
    if args.replay:
        msgs = replay(args.replay, since=args.since)
        for m in msgs:
            print(json.dumps(m, ensure_ascii=False))
        return 0
    if args.gc:
        n = gc_stale_in_flight()
        print(n)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
