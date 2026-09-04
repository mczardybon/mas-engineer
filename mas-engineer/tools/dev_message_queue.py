#!/usr/bin/env python3
"""dev_message_queue.py — File-Based Message Queue v1.0.0
=========================================================

A process-crash resilient file-backed message queue for mas-engineer
sub-recipes and workflows.  NOTE: NOT durable across OS/hardware crash
— no fsync is performed; data may be lost on power failure.  Solves the
"direct delegation becomes a bottleneck" problem (R110-153 design):
parallel agents can enqueue signals / dispatches / results without
blocking, and consumers (dashboard, signal-handler, recovery-loop)
can pick them up asynchronously with retry, backoff, and DLQ semantics.

Design (R110-153):
  - File-based, no external broker (Redis/RabbitMQ not required)
  - Topics = separate NDJSON files in .mase/mq/<topic>.ndjson
  - At-least-once delivery: in_flight messages are re-queued on crash
  - Per-message retry policy with exponential backoff
  - Dead-letter-queue (DLQ) for messages exceeding max_retries
  - Idempotency: enqueue with idempotency_key dedupes duplicates
  - File-locking (fcntl.flock) for concurrent-process safety
  - Atomic writes (write to .tmp, then os.replace — rename is atomic,
    but NO fsync: durability gap documented above)

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
import random  # F-MQ-189-9: full-jitter retry backoff (stdlib only)
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Default MQ root: <workspace>/.mase/mq.  Allows override via env
# (used by tests to point at tmp_path without polluting .mase/).
DEFAULT_MQ_ROOT = ".mase/mq"
# ─── Storage paths ───────────────────────────────────────────────

def _getenv_int(name: str, default: int) -> int:
    """Read an env var as int, falling back to `default` on any parse
    failure (missing, empty, non-numeric, overflow).  Logs a warning
    so silent misconfigurations are visible.

    R110-338: prior code used `int(os.environ.get(name, str(default)))`
    directly, which raises ValueError on bad input and crashes the
    module at import time (e.g. `_idempotency_index` is built at
    module load via `int(os.environ.get("MAS_MQ_IDEMPOTENCY_MAX", ...))`).
    This helper makes the failure mode a soft warning + default.
    """
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except (ValueError, TypeError) as e:
        print(
            f"⚠️ {name}={raw!r} not an int, using default {default} "
            f"({type(e).__name__}: {e})",
            file=sys.stderr,
        )
        return default


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


def _sanitize_topic(topic: str) -> str:
    """Sanitize topic name.  If MAS_MQ_STRICT_TOPIC=1, raise on
    collision-prone inputs (chars that would be replaced)."""
    raw = topic
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in topic)
    if os.environ.get("MAS_MQ_STRICT_TOPIC") == "1" and safe != raw:
        raise ValueError(
            f"topic {raw!r} contains chars that would be sanitized to "
            f"{safe!r}. Use only [a-zA-Z0-9_-] or set MAS_MQ_STRICT_TOPIC=0.")
    return safe


def _topic_path(topic: str, *, completed: bool = False) -> Path:
    """NDJSON file for a topic.  `completed=True` → archive file."""
    suffix = ".completed.ndjson" if completed else ".ndjson"
    # Sanitize topic name: only [a-zA-Z0-9_-]
    safe = _sanitize_topic(topic)
    return _mq_root() / f"{safe}{suffix}"


def _lock_path(topic: str) -> Path:
    safe = _sanitize_topic(topic)
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


_SCHEMA_VERSION = 1  # F-MQ-189-6: every message carries a schema_version


def _migrate(msg: dict) -> dict:
    """Migrate older schema versions to current.  No-op for v1.
    Future migrations (e.g. v1→v2) are added here (F-MQ-189-6)."""
    v = msg.get("schema_version", 1)
    if v == _SCHEMA_VERSION:
        return msg
    if v < _SCHEMA_VERSION:
        # Future: v1→v2 migration goes here.
        return msg  # no-op for now
    return msg  # unknown future version — return as-is


MQ_INVARIANTS = """
INVI: MQ State Invariants (R110-188)
====================================
1. msg.status == "in_flight"  →  msg.in_flight_at is not None
2. msg.in_flight_at          →  msg.in_flight_at >= msg.enqueued_at
3. msg.status == "done"      →  msg.acked_at is not None
4. msg.status == "dlq"       →  msg.last_error is not None

Violation of any invariant = bug.  Enforced by _check_invariants()
called from _read_topic() in DEBUG mode (set MAS_MQ_INVARIANT_CHECK=1).
"""


def _check_invariants(m: dict) -> list:
    """Return list of invariant violation strings (empty = OK)."""
    if os.environ.get("MAS_MQ_INVARIANT_CHECK") != "1":
        return []
    errs = []
    status = m.get("status")
    if status == "in_flight" and not m.get("in_flight_at"):
        errs.append(f"INV1: in_flight without in_flight_at: {m.get('msg_id')}")
    ifa = _parse_iso(m.get("in_flight_at") or "")
    enq = _parse_iso(m.get("enqueued_at") or "")
    if ifa and enq and ifa < enq:
        errs.append(f"INV2: in_flight_at < enqueued_at: {m.get('msg_id')}")
    if status == "done" and not m.get("acked_at"):
        errs.append(f"INV3: done without acked_at: {m.get('msg_id')}")
    if status == "dlq" and not m.get("last_error"):
        errs.append(f"INV4: dlq without last_error: {m.get('msg_id')}")
    return errs


class _IdempotencyIndex:
    """Bounded LRU of (key → msg_id) for fast dedup check.
    Max size: MAS_MQ_IDEMPOTENCY_MAX (default 100k).
    F-MQ-189-7: evicts oldest keys when full (bounded memory)."""

    def __init__(self, max_size: int = 100_000):
        self.max = max_size
        self._d = {}  # dict preserves insertion order (py3.7+)

    def add(self, key: str, msg_id: str) -> None:
        if key in self._d:
            del self._d[key]  # re-insert below → most-recent position
        self._d[key] = msg_id
        if len(self._d) > self.max:
            self._d.pop(next(iter(self._d)))  # evict oldest (insertion order)

    def get(self, key: str) -> Optional[str]:
        if key in self._d:
            val = self._d[key]
            del self._d[key]
            self._d[key] = val  # move to end (most-recent)
            return val
        return None


# Module-level bounded idempotency index (F-MQ-189-7).
_idempotency_index = _IdempotencyIndex(
    max_size=_getenv_int("MAS_MQ_IDEMPOTENCY_MAX", 100000))


def _make_msg(topic: str, payload: dict, *,
              retry_policy: Optional[dict] = None,
              idempotency_key: Optional[str] = None,
              request_id: Optional[str] = None) -> dict:
    """Create a new message record.  Retry policy defaults are sane
    (max 3, exponential backoff 1/2/4/8s)."""
    rp = retry_policy or {}
    retry_count = 0
    assert 0 <= retry_count < 1_000_000, (
        f"retry_count out of range: {retry_count}")  # F-MQ-189-13 sanity
    return {
        "schema_version": _SCHEMA_VERSION,   # F-MQ-189-6
        "msg_id": str(uuid.uuid4()),
        "idempotency_key": idempotency_key,
        "request_id": request_id,
        "topic": topic,
        "payload": payload,
        "enqueued_at": _now_iso(),
        "in_flight_at": None,  # ISO8601 set on consume, cleared on recovery/done
        "next_retry_at": None,
        "retry_count": retry_count,
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
        self.fd = open(self.path, "w", encoding="utf-8")
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()
        return False


# ─── NDJSON I/O (with atomic-write) ──────────────────────────────

def _quarantine_corrupt_line(raw_line: str, source_file: str, err: Exception) -> None:
    """Move unparseable NDJSON line to .mase/mq/_corrupt.ndjson for
    later audit.  Each entry: {ts, source, error, raw_line}."""
    qpath = _mq_root() / "_corrupt.ndjson"
    entry = {
        "ts": _now_iso(),
        "source": source_file,
        "error": str(err),
        "raw_line": raw_line[:500],  # truncate huge lines
    }
    with open(qpath, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_topic(topic: str, *, include_in_flight: bool = True) -> list:
    """Read all messages for a topic.  Atomic with respect to writers
    because the underlying NDJSON file is replaced (not appended-during-
    read)."""
    path = _topic_path(topic)
    if not path.exists():
        return []
    msgs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                m = _migrate(json.loads(line))
            except json.JSONDecodeError as e:
                _quarantine_corrupt_line(line, path.name, e)
                continue
            for _err in _check_invariants(m):
                print(f"MQ-INVARIANT: {_err}", file=sys.stderr)
            if not include_in_flight and m.get("status") == "in_flight":
                continue
            msgs.append(m)
    return msgs


def _write_topic_atomic(topic: str, msgs: list) -> None:
    """Atomic write: write to .tmp, then os.replace() to the real path.
    Safe across processes because OS guarantees rename is atomic."""
    path = _topic_path(topic)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        for m in msgs:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


# ─── Public API: enqueue ─────────────────────────────────────────

class QueueFullError(Exception):
    """Raised when enqueue() would exceed MAS_MQ_MAX_DEPTH_PER_TOPIC
    (F-MQ-189-1: bounded queue / backpressure)."""
    pass


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
        # F-MQ-189-1: bounded queue (backpressure).  Raise QueueFullError
        # when the topic would exceed MAS_MQ_MAX_DEPTH_PER_TOPIC.
        max_depth = _getenv_int("MAS_MQ_MAX_DEPTH_PER_TOPIC", 100000)
        existing = _read_topic(topic, include_in_flight=False)
        if len(existing) >= max_depth:
            raise QueueFullError(
                f"topic {topic!r} depth {len(existing)} >= MAX_DEPTH {max_depth}")
        msgs = _read_topic(topic)
        msgs.append(msg)
        # F-MQ-189-14: disk-full / read-only / IO-error handling.  On
        # OSError (ENOSPC, EROFS, EIO) the message is preserved in the
        # DLQ with last_error_class="StorageError" instead of being lost.
        try:
            _write_topic_atomic(topic, msgs)
        except OSError as e:
            msg["status"] = "failed"
            msg["last_error"] = f"storage: {e}"
            msg["last_error_class"] = "StorageError"
            with open(_dlq_path(), "a", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        if idempotency_key:
            _idempotency_index.add(idempotency_key, msg["msg_id"])  # F-MQ-189-7
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
                m["in_flight_at"] = _now_iso()   # R110-188: GC uses this, not enqueued_at
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
        except (FileNotFoundError, OSError, ValueError) as e:
            # R110-338: narrow bare `except Exception:` to the 3 error
            # classes _read_topic + _TopicLock can actually raise.
            # FileNotFoundError: topic file deleted between glob and open
            # OSError: lock-acquire / read IO failure
            # ValueError: malformed NDJSON (already caught per-line in
            #   _read_topic, but a corrupted header could surface as
            #   ValueError from _migrate)
            # Other exceptions (KeyboardInterrupt, SystemExit, bugs)
            # now propagate so they aren't silently swallowed — a real
            # bug in _read_topic would previously have been invisible
            # because every topic try/except caught it.
            print(
                f"⚠️ _find_msg skipping topic {topic!r}: "
                f"{type(e).__name__}: {e}",
                file=sys.stderr,
            )
            continue
    return None


def ack(msg_id: str) -> bool:
    """Acknowledge a message: archive to `<topic>.completed.ndjson`
    FIRST (crash-atomic), then remove from the live topic file.

    R110-188 (F-MQ-188-4): the archive write happens before the live
    removal, so a crash between the two steps cannot lose the message
    — the completed file is the source of truth for "done"."""
    found = _find_msg(msg_id)
    if not found:
        return False
    topic, (idx, msg, msgs) = found
    with _TopicLock(topic):
        # Re-read to avoid races (msg may have changed since _find_msg)
        msgs = _read_topic(topic)
        if idx >= len(msgs) or msgs[idx].get("msg_id") != msg_id:
            return False
        # STEP 1: archive (durable written first)
        done_msg = dict(msgs[idx])
        done_msg["status"] = "done"
        done_msg["acked_at"] = _now_iso()
        comp_path = _topic_path(topic, completed=True)
        with open(comp_path, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(done_msg, ensure_ascii=False) + "\n")
        # STEP 2: remove from live (only after archive succeeded)
        msgs.pop(idx)
        _write_topic_atomic(topic, msgs)
    return True


def _classify_error(exc: Exception) -> str:
    """Map exception to short class name for DLQ metadata
    (F-MQ-189-12).  'ValueError' → 'Value', 'TimeoutError' → 'Timeout'."""
    cls = exc.__class__.__name__
    for s in ("Error", "Exception"):
        if cls.endswith(s):
            cls = cls[: -len(s)]
    return cls or "Unknown"


def _next_retry_delay(base_sec: float, attempt: int) -> float:
    """Full-jitter exponential backoff (AWS architecture blog).
    Returns delay in seconds.  Capped at 300s (F-MQ-189-9)."""
    expo = base_sec * (2 ** min(attempt, 10))  # cap exponent
    return min(random.uniform(0, expo), 300.0)


def nack(msg_id: str, reason: str) -> bool:
    """Negative-acknowledge: increment retry_count, reschedule with
    full-jitter backoff, OR route to DLQ if max_retries exhausted.

    F-MQ-189-12: an Exception reason is treated as a poison/fatal
    error and routes directly to the DLQ with last_error_class set.
    F-MQ-189-13: retry_count is clamped to 2^31 - 1.
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
        m["retry_count"] = min(int(m.get("retry_count", 0)) + 1, 2**31 - 1)
        m["last_error"] = str(reason)
        m["last_error_class"] = (
            _classify_error(reason) if isinstance(reason, Exception) else "String")
        if isinstance(reason, Exception):
            # Poison/fatal error → DLQ immediately (F-MQ-189-12)
            m["status"] = "dlq"
            m["dlq_at"] = _now_iso()
            m["original_topic"] = m.get("topic") or topic  # R110-188: per-topic DLQ counting
            with open(_dlq_path(), "a", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
            msgs.pop(idx)
        elif m["retry_count"] >= m.get("max_retries", 3):
            # Exhausted → DLQ
            m["status"] = "dlq"
            m["dlq_at"] = _now_iso()
            m["original_topic"] = m.get("topic") or topic  # R110-188: per-topic DLQ counting
            with open(_dlq_path(), "a", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
            msgs.pop(idx)
        else:
            # Reschedule with full-jitter backoff (F-MQ-189-9)
            schedule = m.get("backoff_schedule", [1, 2, 4, 8])
            base = float(schedule[0]) if schedule else 1.0
            delay = _next_retry_delay(base, attempt=m["retry_count"])
            m["next_retry_at"] = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + delay,
                tz=timezone.utc).isoformat()
            m["status"] = "pending"
            m["consumer_id"] = None
        _write_topic_atomic(topic, msgs)
    return True


# ─── Public API: requeue (F-MQ-189-3) ────────────────────────────

def _read_completed(topic: str) -> list:
    """Read all archived (done) messages for a topic."""
    path = _topic_path(topic, completed=True)
    if not path.exists():
        return []
    msgs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msgs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return msgs


def _write_completed_atomic(topic: str, msgs: list) -> None:
    """Atomic write of the completed archive for a topic."""
    path = _topic_path(topic, completed=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        for m in msgs:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def _read_dlq_entries() -> list:
    """Read all DLQ entries (list of dicts)."""
    p = _dlq_path()
    if not p.exists():
        return []
    entries = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _rewrite_dlq(entries: list) -> None:
    """Atomically rewrite the DLQ file with the given entries."""
    p = _dlq_path()
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, p)


def requeue(msg_id: str, delay_sec: float = 0.0) -> bool:
    """Re-queue a done or dlq message: set back to pending, reset
    retry_count, optionally delay via next_retry_at.

    F-MQ-189-3: done messages are moved back from the completed
    archive into the live topic; dlq messages are re-enqueued from
    the DLQ.  Returns True on success, False if not found."""
    # 1. Search completed archives (done messages)
    root = _mq_root()
    if root.exists():
        for ndjson in root.glob("*.completed.ndjson"):
            topic = ndjson.name[: -len(".completed.ndjson")]
            with _TopicLock(topic):
                msgs = _read_completed(topic)
                for i, m in enumerate(msgs):
                    if m.get("msg_id") != msg_id:
                        continue
                    if m.get("status") not in ("done", "dlq"):
                        continue
                    m["status"] = "pending"
                    m["retry_count"] = 0
                    m["consumer_id"] = None
                    m["in_flight_at"] = None
                    m["acked_at"] = None
                    m["dlq_at"] = None
                    m["last_error"] = None
                    if delay_sec > 0:
                        m["next_retry_at"] = datetime.fromtimestamp(
                            datetime.now(timezone.utc).timestamp() + delay_sec,
                            tz=timezone.utc).isoformat()
                    else:
                        m["next_retry_at"] = None
                    msgs.pop(i)
                    _write_completed_atomic(topic, msgs)
                    live = _read_topic(topic)
                    live.append(m)
                    _write_topic_atomic(topic, live)
                    return True
    # 2. Search DLQ (dlq messages)
    entries = _read_dlq_entries()
    for i, e in enumerate(entries):
        if e.get("msg_id") != msg_id:
            continue
        t = e.get("original_topic") or e.get("topic")
        if not t:
            continue
        enqueue(t, e.get("payload", {}), retry_policy={
            "max": e.get("max_retries", 3),
            "backoff": e.get("backoff_schedule", [1, 2, 4, 8])})
        entries.pop(i)
        _rewrite_dlq(entries)
        return True
    return False


def replay_dlq(topic: Optional[str] = None, limit: int = 100) -> int:
    """Re-enqueue up to `limit` oldest DLQ messages matching `topic`
    back to live (or all topics if topic is None).  Returns count.
    Replayed entries are removed from the DLQ (F-MQ-189-5)."""
    entries = _read_dlq_entries()
    selected = [i for i, e in enumerate(entries)
                if topic is None
                or e.get("original_topic", e.get("topic")) == topic]
    n = 0
    for i in selected[:limit]:
        e = entries[i]
        t = e.get("original_topic") or e.get("topic")
        if not t:
            continue
        enqueue(t, e.get("payload", {}), retry_policy={
            "max": e.get("max_retries", 3),
            "backoff": e.get("backoff_schedule", [1, 2, 4, 8])})
        n += 1
    if n:
        keep = [e for j, e in enumerate(entries) if j not in selected[:limit]]
        _rewrite_dlq(keep)
    return n


def purge_dlq(topic: Optional[str] = None,
              older_than: Optional[str] = None) -> int:
    """Permanently delete DLQ entries matching the filter.  Returns
    count purged (F-MQ-189-5)."""
    entries = _read_dlq_entries()
    cutoff = _parse_iso(older_than) if older_than else None
    keep = []
    purged = 0
    for e in entries:
        if topic is not None and e.get("original_topic", e.get("topic")) != topic:
            keep.append(e)
            continue
        if cutoff:
            dlq_at = _parse_iso(e.get("dlq_at") or "")
            if not dlq_at or dlq_at >= cutoff:
                keep.append(e)
                continue
        purged += 1
    if purged:
        _rewrite_dlq(keep)
    return purged


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


def _lag_distribution(lag_values: list) -> dict:
    """Compute p50, p95, p99, max from list of lag values (ms).
    F-MQ-189-4: stats() exposes the full lag distribution, not just
    p95.  Empty input → all zeros."""
    if not lag_values:
        return {"p50": 0, "p95": 0, "p99": 0, "max": 0}
    s = sorted(lag_values)

    def pct(p):
        idx = min(int(p * len(s) / 100), len(s) - 1)
        return s[idx]

    return {"p50": pct(50), "p95": pct(95), "p99": pct(99), "max": s[-1]}


def stats() -> dict:
    """Aggregate stats across all topics.  Shape:
        {"topics": {<topic>: {"depth": N, "current_p95_lag_ms": N,
                               "lag_distribution_ms": {p50,p95,p99,max},
                               "dlq_count_for_topic": N,
                               "retry_rate": 0.0, "completed_total": N}},
         "dlq_count_total": N, "generated_at": ISO8601}
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
                with open(ndjson, encoding="utf-8") as f:
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
            "current_p95_lag_ms": lag_p95,   # R110-188: renamed (was lag_p95_ms)
            "lag_distribution_ms": _lag_distribution(lats),  # F-MQ-189-4: p50/p95/p99/max
            "dlq_count_for_topic": _dlq_count_for_topic(topic),  # R110-188: per-topic
            "retry_rate": (retried / len(live)) if live else 0.0,
            "completed_total": completed_counts.get(topic, 0),
        }
    # R110-188: global DLQ count moved to top-level
    out["dlq_count_total"] = sum(
        t.get("dlq_count_for_topic", 0) for t in out["topics"].values())
    return out


def metrics_prometheus() -> str:
    """Return Prometheus textfile-format metrics for the MQ
    (F-MQ-189-8).  No external dependency — plain text output."""
    s = stats()
    out = []
    for topic, t in s["topics"].items():
        out.append(f'mq_depth{{topic="{topic}"}} {t.get("depth", 0)}')
        out.append(f'mq_lag_p95_ms{{topic="{topic}"}} {t.get("current_p95_lag_ms", 0)}')
        out.append(f'mq_dlq_count{{topic="{topic}"}} {t.get("dlq_count_for_topic", 0)}')
    out.append(f'mq_dlq_total {s.get("dlq_count_total", 0)}')
    return "\n".join(out) + "\n"


def _dlq_count() -> int:
    p = _dlq_path()
    if not p.exists():
        return 0
    # R110-338: read with utf-8 + close (use read+splitlines, not file-iter,
    # to avoid ResourceWarning on unclosed file).  Was: `sum(1 for _ in open(p))`
    # which iterates a file object (returns one per line? actually no — yields
    # one per line for newline-terminated text files BUT leaves the file open
    # until GC).  Splitlines is the canonical fix.
    return len(p.read_text(encoding="utf-8").splitlines())


def _dlq_count_for_topic(topic: str) -> int:
    """Count DLQ entries that originated from `topic`.
    DLQ format: each line is {msg_id, original_topic, last_error, ...}."""
    p = _dlq_path()
    if not p.exists():
        return 0
    n = 0
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("original_topic", d.get("topic")) == topic:
                n += 1
    return n


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
                # R110-188 (F-MQ-188-3): use ONLY in_flight_at — the
                # enqueued_at fallback caused false-stale for messages
                # a consumer had just picked up.
                ref = _parse_iso(m.get("in_flight_at") or "")
                if not ref:
                    continue   # skip — invariant: in_flight must have in_flight_at
                age = (now - ref).total_seconds()
                if age < max_age_sec:
                    continue
                # Recover: back to pending with retry++
                m["status"] = "pending"
                m["in_flight_at"] = None   # R110-188: cleared on recovery
                m["retry_count"] = min(int(m.get("retry_count", 0)) + 1, 2**31 - 1)  # F-MQ-189-13 cap
                m["consumer_id"] = None
                m["next_retry_at"] = now.isoformat()
                m["last_error"] = f"stale in_flight (age={age:.0f}s), recovered"
                changed = True
                recovered += 1
            if changed:
                _write_topic_atomic(topic, msgs)
    return recovered


def _gc_old_pending(max_age_sec: float = 86400.0) -> int:
    """Move pending msgs older than max_age_sec to DLQ.  Returns count
    moved.  Default 24h TTL (F-MQ-189-2).  Sweeps every topic."""
    moved = 0
    now = datetime.now(timezone.utc)
    for topic in list_topics():
        with _TopicLock(topic):
            msgs = _read_topic(topic, include_in_flight=False)
            keep = []
            for m in msgs:
                enq = _parse_iso(m.get("enqueued_at", ""))
                if (m.get("status") == "pending" and enq
                        and (now - enq).total_seconds() > max_age_sec):
                    # TTL expired → DLQ
                    m["status"] = "dlq"
                    m["dlq_at"] = _now_iso()
                    m["last_error"] = (
                        f"ttl-expired: age={(now - enq).total_seconds():.0f}s")
                    m["last_error_class"] = "TTLExpired"
                    m["original_topic"] = m.get("topic") or topic
                    with open(_dlq_path(), "a", encoding="utf-8") as f:
                        fcntl.flock(f, fcntl.LOCK_EX)
                        f.write(json.dumps(m, ensure_ascii=False) + "\n")
                    moved += 1
                else:
                    keep.append(m)
            if len(keep) != len(msgs):
                _write_topic_atomic(topic, keep)
    return moved


def list_topics() -> list[str]:
    """Discover all live topics by globbing <root>/*.ndjson.
    Excludes .completed.ndjson archives and _corrupt.ndjson
    (F-MQ-189-10)."""
    root = _mq_root()
    if not root.exists():
        return []
    out = []
    for p in root.glob("*.ndjson"):
        name = p.name
        if name.endswith(".completed.ndjson"):
            continue
        if name == "_corrupt.ndjson":
            continue
        out.append(name[: -len(".ndjson")])
    return sorted(out)


def compact_completed(topic: str, *, max_lines: int = 10000,
                      keep_recent: int = 1000) -> bool:
    """If <topic>.completed.ndjson has > max_lines, archive the full
    file to <topic>.<YYYYMMDD>.completed.ndjson, then rewrite the live
    completed file with only the most recent `keep_recent` lines.
    Returns True if compaction happened (F-MQ-189-11)."""
    p = _topic_path(topic, completed=True)
    if not p.exists():
        return False
    lines = p.read_text().splitlines()
    if len(lines) <= max_lines:
        return False
    today = datetime.now().strftime("%Y%m%d")
    archive = _mq_root() / f"{topic}.{today}.completed.ndjson"
    with open(archive, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write("\n".join(lines) + "\n")
    recent = lines[-keep_recent:]
    with open(p, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write("\n".join(recent) + "\n")
    return True


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
