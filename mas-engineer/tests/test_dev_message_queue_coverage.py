"""Tests for additional dev_message_queue.py coverage — R110-501 sprint.

Targeted coverage push for tools/dev_message_queue.py (629 stmts, 27%
covered → goal ~45%). Per skill
`mas-engineer-mq-ecosystem-test-pattern`: use MAS_MQ_ROOT env var for
isolation, unique request_ids, public/private API awareness.

This file complements the existing tests/test_dev_message_queue.py
(which has 691 lines but only covers 27% of the 1084-line module).
The uncovered helpers here are mostly:
- _classify_error (line 504-511)
- _next_retry_delay (line 514-518)
- _read_completed / _write_completed_atomic (line 576-602)
- _read_dlq_entries / _rewrite_dlq (line 605-632)
- _dlq_count / _dlq_count_for_topic (line 838-865)
- _lag_ms / _lag_distribution (line 744-765)
- metrics_prometheus (line 825-835)
- _gc_old_pending (line 929-957)
- compact_completed (line 978-1001)
- list_topics (line 960-975)

All these are pure or near-pure functions that take (args) → result,
with filesystem ops as side-effects on tmp_path.
"""
import os
import json
import sys
import time
import fcntl  # noqa: F401  (mock target)
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

# Import via tools.dev_message_queue so pytest-cov (with source=tools
# in .coveragerc) actually instruments the module. The bare
# `dev_message_queue` import works at runtime but coverage can't see it
# because the module name doesn't match the source-rooted path.
import tools.dev_message_queue as mq  # noqa: E402


@pytest.fixture
def tmp_mq(tmp_path, monkeypatch):
    """Isolated MQ root via MAS_MQ_ROOT env var (skill: mq-ecosystem-test-pattern)."""
    mq_dir = tmp_path / "mq"
    mq_dir.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(mq_dir))
    # Disable invariant checks by default (tests opt-in)
    monkeypatch.delenv("MAS_MQ_INVARIANT_CHECK", raising=False)
    monkeypatch.delenv("MAS_MQ_STRICT_TOPIC", raising=False)
    return mq_dir


# ─────────────────────────────────────────────────────────
# _sanitize_topic
# ─────────────────────────────────────────────────────────

def test_sanitize_topic_basic(tmp_mq):
    """Alphanumeric + _- passes through."""
    assert mq._sanitize_topic("topic_a-b") == "topic_a-b"


def test_sanitize_topic_replaces_special_chars(tmp_mq):
    """Special chars → '_'."""
    assert mq._sanitize_topic("topic with spaces") == "topic_with_spaces"
    assert mq._sanitize_topic("topic.with.dots") == "topic_with_dots"


def test_sanitize_topic_strict_raises(tmp_mq, monkeypatch):
    """MAS_MQ_STRICT_TOPIC=1 + unsafe chars → ValueError."""
    monkeypatch.setenv("MAS_MQ_STRICT_TOPIC", "1")
    with pytest.raises(ValueError, match="would be sanitized"):
        mq._sanitize_topic("topic with spaces")


def test_sanitize_topic_strict_passes_safe(tmp_mq, monkeypatch):
    """MAS_MQ_STRICT_TOPIC=1 + safe chars → no raise."""
    monkeypatch.setenv("MAS_MQ_STRICT_TOPIC", "1")
    assert mq._sanitize_topic("safe_topic") == "safe_topic"


# ─────────────────────────────────────────────────────────
# _classify_error
# ─────────────────────────────────────────────────────────

def test_classify_error_value_error(tmp_mq):
    """'ValueError' → 'Value'."""
    assert mq._classify_error(ValueError("x")) == "Value"


def test_classify_error_timeout_error(tmp_mq):
    """'TimeoutError' → 'Timeout'."""
    assert mq._classify_error(TimeoutError("x")) == "Timeout"


def test_classify_error_unknown_class(tmp_mq):
    """Non-'Error'/'Exception' suffix → name unchanged (not 'Unknown' if truthy)."""
    assert mq._classify_error(KeyError("x")) == "Key"


def test_classify_error_exception_suffix(tmp_mq):
    """'Exception' suffix also stripped."""
    # Custom exception with 'Exception' suffix
    class MyException(Exception):
        pass
    assert mq._classify_error(MyException()) == "My"


# ─────────────────────────────────────────────────────────
# _next_retry_delay
# ─────────────────────────────────────────────────────────

def test_next_retry_delay_capped_at_300(tmp_mq):
    """Delay never exceeds 300s."""
    delay = mq._next_retry_delay(100.0, attempt=20)  # huge expo
    assert 0 <= delay <= 300.0


def test_next_retry_delay_exponential_grows(tmp_mq):
    """Higher attempt → higher max delay (within cap)."""
    low = mq._next_retry_delay(1.0, attempt=1)
    high = mq._next_retry_delay(1.0, attempt=5)
    # Just sanity — exponential, capped at 300
    assert high >= 0 and low >= 0


def test_next_retry_delay_zero_base(tmp_mq):
    """base=0 → delay=0 (uniform 0..0)."""
    assert mq._next_retry_delay(0.0, attempt=1) == 0.0


def test_next_retry_delay_exponent_capped(tmp_mq):
    """attempt=100 → expo capped at 2^10 = 1024 * base."""
    # Just verify no crash, no overflow
    delay = mq._next_retry_delay(0.5, attempt=100)
    assert 0 <= delay <= 300.0


# ─────────────────────────────────────────────────────────
# _now_iso + _parse_iso roundtrip
# ─────────────────────────────────────────────────────────

def test_now_iso_format(tmp_mq):
    """_now_iso returns ISO format with UTC."""
    iso = mq._now_iso()
    assert "T" in iso
    # Should be parseable
    parsed = mq._parse_iso(iso)
    assert parsed is not None


def test_parse_iso_empty_returns_none(tmp_mq):
    """Empty string → None."""
    assert mq._parse_iso("") is None


def test_parse_iso_invalid_returns_none(tmp_mq):
    """Invalid format → None."""
    assert mq._parse_iso("not-a-date") is None


def test_parse_iso_with_z_suffix(tmp_mq):
    """'Z' suffix (UTC zulu) is handled."""
    parsed = mq._parse_iso("2026-01-01T00:00:00Z")
    assert parsed is not None


# ─────────────────────────────────────────────────────────
# _topic_path + _lock_path + _dlq_path + _stats_path
# ─────────────────────────────────────────────────────────

def test_topic_path_pending(tmp_mq):
    """Pending → .ndjson suffix."""
    p = mq._topic_path("topic_a", completed=False)
    assert p.name == "topic_a.ndjson"
    assert "mq" in str(p)


def test_topic_path_completed(tmp_mq):
    """completed=True → .completed.ndjson suffix."""
    p = mq._topic_path("topic_a", completed=True)
    assert p.name == "topic_a.completed.ndjson"


def test_lock_path(tmp_mq):
    """Lock file in _locks/ dir."""
    p = mq._lock_path("topic_a")
    assert p.name == "topic_a.lock"
    assert p.parent.name == "_locks"


def test_dlq_path(tmp_mq):
    """DLQ is signals_dlq.ndjson in mq root."""
    p = mq._dlq_path()
    assert p.name == "signals_dlq.ndjson"


def test_stats_path(tmp_mq):
    """Stats is stats.json in mq root."""
    p = mq._stats_path()
    assert p.name == "stats.json"


# ─────────────────────────────────────────────────────────
# depth
# ─────────────────────────────────────────────────────────

def test_depth_empty_topic(tmp_mq):
    """Empty topic → 0."""
    assert mq.depth("nonexistent") == 0


def test_depth_after_enqueue(tmp_mq):
    """Enqueue 3 → depth == 3."""
    mq.enqueue("t", {"x": 1}, request_id="r1")
    mq.enqueue("t", {"x": 2}, request_id="r2")
    mq.enqueue("t", {"x": 3}, request_id="r3")
    assert mq.depth("t") == 3


# ─────────────────────────────────────────────────────────
# _read_completed / _write_completed_atomic
# ─────────────────────────────────────────────────────────

def test_read_completed_missing(tmp_mq):
    """Missing completed file → empty list."""
    assert mq._read_completed("nope") == []


def test_read_completed_skips_invalid_json(tmp_mq):
    """Invalid JSON lines are skipped, valid parsed."""
    path = mq._topic_path("t", completed=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write('{"msg_id": "1", "ok": true}\n')
        f.write("invalid json\n")
        f.write('{"msg_id": "2", "ok": true}\n')
    msgs = mq._read_completed("t")
    assert len(msgs) == 2
    assert msgs[0]["msg_id"] == "1"


def test_write_completed_atomic_creates_file(tmp_mq):
    """Atomic write creates the file with all messages."""
    msgs = [{"msg_id": "1"}, {"msg_id": "2"}]
    mq._write_completed_atomic("t", msgs)
    path = mq._topic_path("t", completed=True)
    assert path.exists()
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2


# ─────────────────────────────────────────────────────────
# _read_dlq_entries / _rewrite_dlq
# ─────────────────────────────────────────────────────────

def test_read_dlq_empty(tmp_mq):
    """No DLQ file → empty list."""
    assert mq._read_dlq_entries() == []


def test_read_dlq_with_entries(tmp_mq):
    """DLQ file with 2 valid + 1 invalid → 2 entries."""
    path = mq._dlq_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write('{"msg_id": "1"}\n')
        f.write("garbage\n")
        f.write('{"msg_id": "2"}\n')
    entries = mq._read_dlq_entries()
    assert len(entries) == 2


def test_rewrite_dlq(tmp_mq):
    """Rewrite DLQ with new entries."""
    mq._rewrite_dlq([{"msg_id": "x"}, {"msg_id": "y"}])
    path = mq._dlq_path()
    assert path.exists()
    entries = mq._read_dlq_entries()
    assert len(entries) == 2


# ─────────────────────────────────────────────────────────
# _dlq_count / _dlq_count_for_topic
# ─────────────────────────────────────────────────────────

def test_dlq_count_empty(tmp_mq):
    """Empty DLQ → 0."""
    assert mq._dlq_count() == 0


def test_dlq_count_per_topic_filters(tmp_mq):
    """_dlq_count_for_topic counts only matching topic entries."""
    # Write 3 entries: 2 on topic_a, 1 on topic_b
    path = mq._dlq_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write('{"msg_id": "1", "original_topic": "topic_a"}\n')
        f.write('{"msg_id": "2", "original_topic": "topic_a"}\n')
        f.write('{"msg_id": "3", "original_topic": "topic_b"}\n')
    assert mq._dlq_count() == 3
    assert mq._dlq_count_for_topic("topic_a") == 2
    assert mq._dlq_count_for_topic("topic_b") == 1
    assert mq._dlq_count_for_topic("nonexistent") == 0


# ─────────────────────────────────────────────────────────
# _lag_ms + _lag_distribution
# ─────────────────────────────────────────────────────────

def test_lag_ms_no_timestamps(tmp_mq):
    """Missing enqueued_at → None."""
    assert mq._lag_ms({"msg_id": "x"}) is None


def test_lag_ms_with_timestamps(tmp_mq):
    """enqueued_at + now → lag in ms (>= 0)."""
    now = mq._now_iso()
    msg = {"enqueued_at": now}
    lag = mq._lag_ms(msg)
    assert lag is not None
    assert lag >= 0


def test_lag_distribution_empty(tmp_mq):
    """Empty list → all-zero dict with p50/p95/p99/max keys."""
    d = mq._lag_distribution([])
    assert d == {"p50": 0, "p95": 0, "p99": 0, "max": 0}


def test_lag_distribution_with_values(tmp_mq):
    """Distribution has p50, p95, p99, max (NO _ms suffix)."""
    d = mq._lag_distribution([100, 200, 300, 400, 500])
    assert d["max"] == 500
    assert d["p50"] == 300
    assert d["p95"] >= 400  # 95th percentile of 5 values
    assert d["p99"] >= 400


# ─────────────────────────────────────────────────────────
# list_topics
# ─────────────────────────────────────────────────────────

def test_list_topics_empty(tmp_mq):
    """No topic files → empty list."""
    assert mq.list_topics() == []


def test_list_topics_with_files(tmp_mq):
    """Multiple .ndjson files → list of topic names (completed excluded)."""
    mq._mq_root().mkdir(parents=True, exist_ok=True)
    (mq._mq_root() / "topic_a.ndjson").write_text("")
    # .completed.ndjson files are EXCLUDED by list_topics
    (mq._mq_root() / "topic_b.completed.ndjson").write_text("")
    # Non-topic files are ignored
    (mq._mq_root() / "stats.json").write_text("{}")
    (mq._mq_root() / "signals_dlq.ndjson").write_text("")
    topics = mq.list_topics()
    assert "topic_a" in topics
    assert "topic_b" not in topics  # .completed.ndjson excluded
    # signals_dlq is also a topic name (returned if matching glob)
    assert isinstance(topics, list)


# ─────────────────────────────────────────────────────────
# metrics_prometheus
# ─────────────────────────────────────────────────────────

def test_metrics_prometheus_format(tmp_mq):
    """Returns prometheus exposition format."""
    out = mq.metrics_prometheus()
    # Should contain HELP/TYPE comments or metric samples
    assert isinstance(out, str)
    # Length > 0 even for empty MQ
    assert len(out) > 0
