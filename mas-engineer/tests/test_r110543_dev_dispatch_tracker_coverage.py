"""R110-543 — coverage test sprint: tools/dev_dispatch_tracker.py 0%→100%.

Unit tests for the dispatch tree tracker with NDJSON legacy log +
MQ topic dual-write. Tests use tmp_path fixtures with a
monkeypatched LEGACY_LOG (via MAS_DISPATCH_LOG env var) so nothing
touches the real /tmp/mas-dispatch.ndjson.

Coverage of 350 LOC / 8 modules:
  - _mq() (lines 59-68): import success + import failure fallback
  - _read_all() (lines 73-85): missing file, normal, broken-line skip
  - _write_all() (lines 88-92): write + parent-dir creation
  - add() (lines 97-135): legacy append + MQ enqueue (mocked),
    no-MQ fallback, mq.enqueue exception → no crash
  - done() (lines 138-180): update + write, errors branch, no-MQ,
    mq.enqueue exception, updated=None branch (id not found)
  - get_tree() (lines 183-225): mode filter, last_n, status icons
    (done/running/error/unknown), result_summary, errors, depth
    recursion, no entries
  - mq_stats() (lines 228-249): mq=None → None, success path,
    exception → {"error": str}
  - clear() (lines 252-255): file exists + missing
  - CLI (lines 260-350): --add, --done (with all 4-arg variants),
    --log, --json (with + without --mode), --tree (with + without
    --mode), --stats, --mq-stats (mq=None + mq available),
    --clear, default (no args)
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_dispatch_tracker as dt


# ────────────────────── Helpers / fixtures ────────────────────────

@pytest.fixture
def log_file(tmp_path, monkeypatch):
    """Per-test log path with MAS_DISPATCH_LOG env var."""
    p = tmp_path / "dispatch.ndjson"
    monkeypatch.setenv("MAS_DISPATCH_LOG", str(p))
    # Force re-import so LEGACY_LOG is re-evaluated
    import importlib
    importlib.reload(dt)
    return p


def _read_ndjson(path):
    """Read NDJSON, return list of entries."""
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


# ────────────────────── _mq() ─────────────────────────────────────

def test_mq_import_success(monkeypatch):
    """Lines 61-66: import dev_message_queue returns the module."""
    import sys
    fake_mq = MagicMock()
    monkeypatch.setitem(sys.modules, "dev_message_queue", fake_mq)
    # Need to bypass the actual import — patch the import statement
    # by making 'dev_message_queue' available in tools dir
    # Easiest: patch the import
    fake_module = MagicMock()
    with patch.dict(sys.modules, {"dev_message_queue": fake_module}):
        # Reset sys.path state
        result = dt._mq()
    assert result is fake_module


def test_mq_import_failure_fallback():
    """Lines 67-68: Exception during import → None."""
    # Simulate import failure by blocking import
    import sys
    # Remove if present, then break import
    orig = sys.modules.pop("dev_message_queue", None)
    # Create a meta-path finder that blocks
    class Blocker:
        def find_module(self, name, path=None):
            if name == "dev_message_queue":
                return self
        def load_module(self, name):
            raise ImportError("blocked for test")
    sys.meta_path.insert(0, Blocker())
    try:
        result = dt._mq()
    finally:
        sys.meta_path.pop(0)
        if orig is not None:
            sys.modules["dev_message_queue"] = orig
    assert result is None


# ────────────────────── _read_all() ───────────────────────────────

def test_read_all_missing_file(log_file):
    """Lines 74-75: file doesn't exist → []."""
    assert dt._read_all() == []


def test_read_all_normal(log_file):
    """Lines 77-82: parse NDJSON into entries."""
    log_file.write_text(
        '{"id":"a","status":"running"}\n'
        '{"id":"b","status":"done"}\n'
    )
    entries = dt._read_all()
    assert len(entries) == 2
    assert entries[0]["id"] == "a"
    assert entries[1]["id"] == "b"


def test_read_all_skip_broken_lines(log_file):
    """Lines 83-84: json.loads fails → skip line."""
    log_file.write_text(
        '{"id":"a"}\n'
        'NOT_JSON\n'
        '{"id":"b"}\n'
    )
    entries = dt._read_all()
    assert len(entries) == 2
    assert entries[0]["id"] == "a"
    assert entries[1]["id"] == "b"


def test_read_all_skip_empty_lines(log_file):
    """Line 80: empty lines ignored."""
    log_file.write_text(
        '\n'
        '{"id":"a"}\n'
        '\n'
        '{"id":"b"}\n'
        '\n'
    )
    entries = dt._read_all()
    assert len(entries) == 2


# ────────────────────── _write_all() ──────────────────────────────

def test_write_all_basic(log_file):
    """Lines 88-92: write entries as NDJSON."""
    dt._write_all([{"id": "a"}, {"id": "b"}])
    entries = _read_ndjson(log_file)
    assert entries == [{"id": "a"}, {"id": "b"}]


def test_write_all_creates_parent_dir(tmp_path, monkeypatch):
    """Line 89: parent dir doesn't exist → makedirs."""
    log_path = tmp_path / "subdir" / "deep" / "log.ndjson"
    monkeypatch.setenv("MAS_DISPATCH_LOG", str(log_path))
    import importlib
    importlib.reload(dt)
    dt._write_all([{"id": "x"}])
    assert log_path.exists()
    assert _read_ndjson(log_path) == [{"id": "x"}]


def test_write_all_empty_list(log_file):
    """Edge case: write empty list."""
    dt._write_all([])
    # File should exist but be empty
    assert log_file.exists()
    assert log_file.read_text() == ""


def test_write_all_unicode(log_file):
    """ensure_ascii=False: non-ASCII chars preserved."""
    dt._write_all([{"task": "äöü 中文 🚀"}])
    entries = _read_ndjson(log_file)
    assert entries[0]["task"] == "äöü 中文 🚀"


# ────────────────────── add() ─────────────────────────────────────

def test_add_writes_to_legacy(log_file):
    """Lines 100-118: build entry + append to NDJSON."""
    eid = "20250914_120000_123456"
    ts = "2025-09-14T12:00:00Z"
    dt.add(ts, eid, None, "agent-a", "agent-b", "task-1", "mas")
    entries = _read_ndjson(log_file)
    assert len(entries) == 1
    e = entries[0]
    assert e["id"] == eid
    assert e["ts"] == ts
    assert e["parent_id"] is None
    assert e["from"] == "agent-a"
    assert e["to"] == "agent-b"
    assert e["task"] == "task-1"
    assert e["mode"] == "mas"
    assert e["status"] == "running"
    assert e["duration_ms"] is None
    assert e["turns"] == 0
    assert e["workspace"] == os.getcwd()


def test_add_with_parent(log_file):
    """parent_id passed through."""
    dt.add("t", "id1", "parent-id", "a", "b", "t")
    e = _read_ndjson(log_file)[0]
    assert e["parent_id"] == "parent-id"


def test_add_default_mode(log_file):
    """Line 107: mode default = 'mas'."""
    dt.add("t", "id1", None, "a", "b", "t")
    assert _read_ndjson(log_file)[0]["mode"] == "mas"


def test_add_default_workspace(log_file, monkeypatch):
    """Line 113: workspace=None → os.getcwd()."""
    monkeypatch.chdir("/tmp")
    dt.add("t", "id1", None, "a", "b", "t")
    assert _read_ndjson(log_file)[0]["workspace"] == "/tmp"


def test_add_explicit_workspace(log_file):
    """Line 113: workspace passed → used."""
    dt.add("t", "id1", None, "a", "b", "t",
           workspace="/my/ws")
    assert _read_ndjson(log_file)[0]["workspace"] == "/my/ws"


def test_add_creates_parent_dir(tmp_path, monkeypatch):
    """Line 116: parent dir missing → makedirs."""
    log_path = tmp_path / "newsub" / "log.ndjson"
    monkeypatch.setenv("MAS_DISPATCH_LOG", str(log_path))
    import importlib
    importlib.reload(dt)
    dt.add("t", "id1", None, "a", "b", "t")
    assert log_path.exists()


def test_add_appends_not_overwrites(log_file):
    """Line 117: 'a' mode, not 'w'."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.add("t", "id2", None, "a", "b", "t")
    assert len(_read_ndjson(log_file)) == 2


def test_add_with_mq_enqueue(log_file):
    """Lines 120-132: mq.enqueue called with right args."""
    with patch.object(dt, "_mq") as mock_mq:
        mock_mq.return_value = MagicMock()
        dt.add("t", "id1", None, "a", "b", "t", "mas")
    mock_mq.return_value.enqueue.assert_called_once()
    args, kwargs = mock_mq.return_value.enqueue.call_args
    assert args[0] == "dispatches"
    assert args[1]["event_type"] == "dispatch_start"
    assert args[1]["id"] == "id1"
    assert kwargs["idempotency_key"] == "dispatch_start-id1"
    assert kwargs["retry_policy"] == {"max": 3, "backoff": [1, 2, 4]}
    assert kwargs["request_id"] == "id1"


def test_add_mq_unavailable_no_crash(log_file):
    """Lines 121,134: mq=None → no enqueue, no crash."""
    with patch.object(dt, "_mq", return_value=None):
        dt.add("t", "id1", None, "a", "b", "t", "mas")
    assert len(_read_ndjson(log_file)) == 1


def test_add_mq_enqueue_exception_caught(log_file):
    """Lines 133-134: mq.enqueue raises → silently swallowed."""
    fake_mq = MagicMock()
    fake_mq.enqueue.side_effect = OSError("mq down")
    with patch.object(dt, "_mq", return_value=fake_mq):
        dt.add("t", "id1", None, "a", "b", "t", "mas")
    # Legacy write still happened
    assert len(_read_ndjson(log_file)) == 1


def test_add_returns_entry(log_file):
    """Line 135: add() returns the entry dict."""
    result = dt.add("t", "id1", None, "a", "b", "t", "mas")
    assert result["id"] == "id1"
    assert result["from"] == "a"


# ────────────────────── done() ────────────────────────────────────

def test_done_updates_existing(log_file):
    """Lines 141-152: find entry, update fields, rewrite."""
    dt.add("t", "id1", None, "a", "b", "task1", "mas")
    dt.done("id1", 5000, 3, "completed ok", None)
    e = _read_ndjson(log_file)[0]
    assert e["status"] == "done"
    assert e["duration_ms"] == 5000
    assert e["turns"] == 3
    assert e["result_summary"] == "completed ok"
    assert e["errors"] is None


def test_done_with_errors_marks_error(log_file):
    """Line 145: errors param truthy → status='error'."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.done("id1", 1000, 1, "failed", "boom")
    e = _read_ndjson(log_file)[0]
    assert e["status"] == "error"
    assert e["errors"] == "boom"


def test_done_id_not_found(log_file):
    """Line 151: no entry matches → updated=None, no MQ event."""
    dt.add("t", "id1", None, "a", "b", "t")
    with patch.object(dt, "_mq") as mock_mq:
        mock_mq.return_value = MagicMock()
        dt.done("nonexistent", 1000, 1, "x", None)
    mock_mq.return_value.enqueue.assert_not_called()
    # Legacy file unchanged
    assert _read_ndjson(log_file)[0]["status"] == "running"


def test_done_with_mq_enqueue(log_file):
    """Lines 154-179: mq.enqueue dispatch_done event."""
    dt.add("t", "id1", None, "from-a", "to-b", "task-x", "mas")
    with patch.object(dt, "_mq") as mock_mq:
        mock_mq.return_value = MagicMock()
        dt.done("id1", 2000, 2, "ok", None)
    mock_mq.return_value.enqueue.assert_called_once()
    args, kwargs = mock_mq.return_value.enqueue.call_args
    assert args[0] == "dispatches"
    payload = args[1]
    assert payload["event_type"] == "dispatch_done"
    assert payload["id"] == "id1"
    assert payload["from"] == "from-a"
    assert payload["to"] == "to-b"
    assert payload["task"] == "task-x"
    assert payload["mode"] == "mas"
    assert payload["status"] == "done"
    assert payload["duration_ms"] == 2000
    assert kwargs["idempotency_key"] == "dispatch_done-id1"


def test_done_mq_unavailable(log_file):
    """Line 156: mq=None → no enqueue."""
    dt.add("t", "id1", None, "a", "b", "t")
    with patch.object(dt, "_mq", return_value=None):
        dt.done("id1", 100, 1, "ok", None)
    assert _read_ndjson(log_file)[0]["status"] == "done"


def test_done_mq_enqueue_exception(log_file):
    """Lines 178-179: mq.enqueue raises → swallowed."""
    dt.add("t", "id1", None, "a", "b", "t")
    fake_mq = MagicMock()
    fake_mq.enqueue.side_effect = RuntimeError("nope")
    with patch.object(dt, "_mq", return_value=fake_mq):
        dt.done("id1", 100, 1, "ok", None)
    assert _read_ndjson(log_file)[0]["status"] == "done"


def test_done_returns_entries(log_file):
    """Line 180: returns the (now-updated) entries list."""
    dt.add("t", "id1", None, "a", "b", "t")
    result = dt.done("id1", 100, 1, "ok", None)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == "id1"


def test_done_empty_log(log_file):
    """Edge: _read_all returns [] → updated=None, returns []."""
    with patch.object(dt, "_mq", return_value=MagicMock()):
        result = dt.done("any-id", 0, 0, "")
    assert result == []


# ────────────────────── get_tree() ────────────────────────────────

def test_get_tree_empty(log_file):
    """Lines 184-185: no entries → all counts zero."""
    r = dt.get_tree()
    assert r["total"] == 0
    assert r["running"] == 0
    assert r["done"] == 0
    assert r["errors"] == 0
    assert r["tree"] == []
    assert r["entries"] == []


def test_get_tree_basic(log_file):
    """Lines 184-225: aggregate stats from entries."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.add("t", "id2", None, "a", "b", "t")
    dt.done("id1", 1000, 1, "ok", None)
    dt.done("id2", 2000, 1, "failed", "err")
    r = dt.get_tree()
    assert r["total"] == 2
    assert r["running"] == 0
    assert r["done"] == 1
    assert r["errors"] == 1  # id2 had errors


def test_get_tree_running_count(log_file):
    """Line 220: status='running' counted."""
    dt.add("t", "id1", None, "a", "b", "t")
    r = dt.get_tree()
    assert r["running"] == 1


def test_get_tree_mode_filter(log_file):
    """Lines 186-187: mode filter excludes other modes."""
    dt.add("t", "id1", None, "a", "b", "t", mode="mas")
    dt.add("t", "id2", None, "a", "b", "t", mode="framework")
    r = dt.get_tree(mode="mas")
    assert r["total"] == 1
    assert r["entries"][0]["id"] == "id1"


def test_get_tree_last_n(log_file):
    """Line 188: last_n slice."""
    for i in range(10):
        dt.add("t", f"id{i}", None, "a", "b", "t")
    r = dt.get_tree(last_n=3)
    assert r["total"] == 3


def test_get_tree_default_last_n_50(log_file):
    """Line 188: default last_n=50."""
    for i in range(60):
        dt.add("t", f"id{i}", None, "a", "b", "t")
    r = dt.get_tree()
    assert r["total"] == 50


def test_get_tree_icon_done(log_file):
    """Line 200: status='done' → ✅."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.done("id1", 1000, 1, "ok", None)
    r = dt.get_tree()
    assert "✅" in r["tree"][0]


def test_get_tree_icon_running(log_file):
    """Line 200: status='running' → ⏳."""
    dt.add("t", "id1", None, "a", "b", "t")
    r = dt.get_tree()
    assert "⏳" in r["tree"][0]


def test_get_tree_icon_error(log_file):
    """Line 200: status='error' → ❌."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.done("id1", 100, 1, "x", "boom")
    r = dt.get_tree()
    assert "❌" in r["tree"][0]


def test_get_tree_icon_unknown(log_file):
    """Line 200: unknown status → ⏹️."""
    # Build entry with weird status
    dt.add("t", "id1", None, "a", "b", "t")
    # Manually mutate the legacy file
    import json
    entries = _read_ndjson(log_file)
    entries[0]["status"] = "paused"
    log_file.write_text(json.dumps(entries[0]) + "\n")
    r = dt.get_tree()
    assert "⏹️" in r["tree"][0]


def test_get_tree_icon_mas_mode(log_file):
    """Line 201: mode='mas' → 🎩."""
    dt.add("t", "id1", None, "a", "b", "t", mode="mas")
    r = dt.get_tree()
    assert "🎩" in r["tree"][0]


def test_get_tree_icon_framework_mode(log_file):
    """Line 201: mode='framework' → 🏗️."""
    dt.add("t", "id1", None, "a", "b", "t", mode="framework")
    r = dt.get_tree()
    assert "🏗️" in r["tree"][0]


def test_get_tree_duration_format(log_file):
    """Lines 202-203: duration_ms/1000 with 1f format."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.done("id1", 5500, 1, "ok", None)
    r = dt.get_tree()
    assert "5.5s" in r["tree"][0]


def test_get_tree_duration_none(log_file):
    """Line 203: duration_ms=None → '...'."""
    dt.add("t", "id1", None, "a", "b", "t")
    r = dt.get_tree()
    assert "..." in r["tree"][0]


def test_get_tree_turns_format(log_file):
    """Line 204: turns formatted as '<n>t'."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.done("id1", 100, 7, "ok", None)
    r = dt.get_tree()
    assert "7t" in r["tree"][0]


def test_get_tree_turns_default_zero(log_file):
    """Line 204: turns missing → '0t'."""
    dt.add("t", "id1", None, "a", "b", "t")
    r = dt.get_tree()
    assert "0t" in r["tree"][0]


def test_get_tree_result_summary_truncated(log_file):
    """Line 205-206: summary truncated to 60 chars + ' — '."""
    dt.add("t", "id1", None, "a", "b", "t")
    long_summary = "x" * 100
    dt.done("id1", 100, 1, long_summary, None)
    r = dt.get_tree()
    assert " — " in r["tree"][0]
    # First 60 chars present, 61st truncated
    assert "x" * 60 in r["tree"][0]
    # Make sure full 100 not there
    assert "x" * 100 not in r["tree"][0]


def test_get_tree_no_summary_no_dash(log_file):
    """Line 206: no result_summary → no ' — ' prefix."""
    dt.add("t", "id1", None, "a", "b", "t")
    r = dt.get_tree()
    assert " — " not in r["tree"][0]


def test_get_tree_errors_format(log_file):
    """Line 207: errors present → ' ⚠️ <errors>'."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.done("id1", 100, 1, "x", "some error")
    r = dt.get_tree()
    assert "⚠️" in r["tree"][0]
    assert "some error" in r["tree"][0]


def test_get_tree_nested_children(log_file):
    """Lines 210-211: child entries indented one level deeper."""
    dt.add("t", "parent", None, "a", "b", "t")
    dt.add("t", "child1", "parent", "a", "b", "t")
    dt.add("t", "child2", "parent", "a", "b", "t")
    r = dt.get_tree()
    # Parent: no indent; children: 2-space indent
    tree = r["tree"]
    assert len(tree) == 3
    # First line is parent (no indent)
    assert not tree[0].startswith(" ")
    # Children indented
    assert tree[1].startswith("  ")
    assert tree[2].startswith("  ")


def test_get_tree_deeply_nested(log_file):
    """Lines 197,211: recursion → grandchildren indented 4 spaces."""
    dt.add("t", "p", None, "a", "b", "t")
    dt.add("t", "c", "p", "a", "b", "t")
    dt.add("t", "gc", "c", "a", "b", "t")
    r = dt.get_tree()
    # gc should be indented 4 spaces
    assert any(line.startswith("    ") for line in r["tree"])


def test_get_tree_error_count_via_errors_field(log_file):
    """Line 222: errors counted even without status='error'."""
    # Add entry with status='done' but errors set (full shape)
    dt.add("t", "id1", None, "a", "b", "task1")
    # Patch the legacy file to set errors on done entry
    entries = _read_ndjson(log_file)
    entries[0]["status"] = "done"
    entries[0]["errors"] = "post-mortem error"
    entries[0]["duration_ms"] = 1000
    entries[0]["turns"] = 1
    entries[0]["result_summary"] = "ok"
    log_file.write_text(json.dumps(entries[0]) + "\n")
    r = dt.get_tree()
    assert r["errors"] == 1


# ────────────────────── mq_stats() ────────────────────────────────

def test_mq_stats_mq_unavailable():
    """Lines 236-237: mq=None → return None."""
    with patch.object(dt, "_mq", return_value=None):
        result = dt.mq_stats()
    assert result is None


def test_mq_stats_success():
    """Lines 239-247: full success path with all 5 keys."""
    fake_mq = MagicMock()
    fake_mq.stats.return_value = {
        "topics": {
            "dispatches": {
                "depth": 5,
                "current_p95_lag_ms": 100,
                "dlq_count_for_topic": 2,
                "retry_rate": 0.5,
                "completed_total": 200,
            }
        }
    }
    with patch.object(dt, "_mq", return_value=fake_mq):
        result = dt.mq_stats()
    assert result == {
        "depth": 5,
        "lag_p95_ms": 100,
        "dlq_count": 2,
        "retry_rate": 0.5,
        "completed_total": 200,
    }


def test_mq_stats_no_topic_data():
    """Lines 240-246: topic missing → empty dict → all 0."""
    fake_mq = MagicMock()
    fake_mq.stats.return_value = {"topics": {}}
    with patch.object(dt, "_mq", return_value=fake_mq):
        result = dt.mq_stats()
    assert result == {
        "depth": 0, "lag_p95_ms": 0, "dlq_count": 0,
        "retry_rate": 0.0, "completed_total": 0,
    }


def test_mq_stats_exception():
    """Lines 248-249: mq.stats raises → {'error': str}."""
    fake_mq = MagicMock()
    fake_mq.stats.side_effect = RuntimeError("mq broke")
    with patch.object(dt, "_mq", return_value=fake_mq):
        result = dt.mq_stats()
    assert "error" in result
    assert "mq broke" in result["error"]


# ────────────────────── clear() ───────────────────────────────────

def test_clear_existing(log_file):
    """Lines 252-255: file exists → remove."""
    log_file.write_text("x")
    result = dt.clear()
    assert result == {"status": "cleared"}
    assert not log_file.exists()


def test_clear_missing(log_file):
    """Line 254: missing file → no-op, still returns cleared."""
    assert not log_file.exists()
    result = dt.clear()
    assert result == {"status": "cleared"}


# ────────────────────── CLI block ────────────────────────────────

def _run_cli(*args, monkeypatch=None, log_file=None):
    """Run the CLI block as a subprocess with the test log path."""
    if log_file is None:
        # Caller didn't pass log_file, use default tmp
        log_file_path = tempfile.mktemp(suffix=".ndjson")
    else:
        log_file_path = str(log_file)
    env = os.environ.copy()
    env["MAS_DISPATCH_LOG"] = log_file_path
    # Clear PYTHONPATH interference
    env.pop("PYTHONPATH", None)
    cmd = [sys.executable, "-c",
           "import sys; sys.path.insert(0, '.');"
           "exec(open('tools/dev_dispatch_tracker.py').read())"] + list(args)
    p = subprocess.run(cmd, capture_output=True, text=True, env=env,
                       cwd=str(REPO_ROOT), timeout=15)
    return p


def test_cli_add(log_file):
    """Lines 261-270: --add → adds entry, prints eid."""
    r = _run_cli("--add", "agent-x", "test-task", "mas", log_file=log_file)
    assert r.returncode == 0
    assert r.stdout.strip() != ""
    entries = _read_ndjson(log_file)
    assert len(entries) == 1
    assert entries[0]["to"] == "agent-x"
    assert entries[0]["task"] == "test-task"
    assert entries[0]["mode"] == "mas"


def test_cli_add_minimal(log_file):
    """Lines 264-266: minimal args → task='?' mode='mas' parent=None."""
    r = _run_cli("--add", "agent-y", log_file=log_file)
    assert r.returncode == 0
    entries = _read_ndjson(log_file)
    assert entries[0]["to"] == "agent-y"
    assert entries[0]["task"] == "?"
    assert entries[0]["mode"] == "mas"


def test_cli_add_with_parent(log_file):
    """Line 266: parent id passed."""
    r = _run_cli("--add", "agent", "task", "mas", "parent-id",
                 log_file=log_file)
    assert r.returncode == 0
    entries = _read_ndjson(log_file)
    assert entries[0]["parent_id"] == "parent-id"


def test_cli_done(log_file):
    """Lines 272-280: --done → marks done."""
    # First add via direct API
    dt.add("t", "id123", None, "a", "b", "task")
    r = _run_cli("--done", "id123", "5", "3", "ok", log_file=log_file)
    assert r.returncode == 0
    assert "done: id123" in r.stdout
    entries = _read_ndjson(log_file)
    assert entries[0]["status"] == "done"
    assert entries[0]["duration_ms"] == 5000  # 5 sec * 1000
    assert entries[0]["turns"] == 3


def test_cli_done_with_error(log_file):
    """Line 278: error param passed."""
    dt.add("t", "id123", None, "a", "b", "task")
    r = _run_cli("--done", "id123", "1", "1", "failed", "boom",
                 log_file=log_file)
    assert r.returncode == 0
    entries = _read_ndjson(log_file)
    assert entries[0]["status"] == "error"


def test_cli_done_minimal(log_file):
    """Lines 275-277: minimal args → dur=0, turns=0, summary=''."""
    dt.add("t", "id123", None, "a", "b", "task")
    r = _run_cli("--done", "id123", log_file=log_file)
    assert r.returncode == 0
    entries = _read_ndjson(log_file)
    assert entries[0]["duration_ms"] == 0
    assert entries[0]["turns"] == 0
    assert entries[0]["result_summary"] == ""


def test_cli_log(log_file):
    """Lines 282-286: --log '<json>' → direct add() with **entry.

    Note: SUT prints entry.get('id', '?'), but the docstring specifies
    'entry_id' as the key (not 'id'). So it falls back to '?'."""
    entry_json = json.dumps({
        "ts": "2025-09-14T12:00:00Z",
        "entry_id": "log-id",
        "parent_id": None,
        "from_agent": "x",
        "to_agent": "y",
        "task": "logged task",
        "mode": "mas",
        "workspace": "/tmp"
    })
    r = _run_cli("--log", entry_json, log_file=log_file)
    assert r.returncode == 0
    # SUT prints entry.get('id', '?') — our entry uses 'entry_id' so '?'
    assert r.stdout.strip() == "?"
    # But add() did happen
    entries = _read_ndjson(log_file)
    assert entries[0]["task"] == "logged task"


def test_cli_json(log_file):
    """Lines 288-295: --json → returns JSON without 'entries' key."""
    dt.add("t", "id1", None, "a", "b", "t")
    r = _run_cli("--json", log_file=log_file)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert "total" in data
    assert "tree" in data
    assert "entries" not in data  # popped on L294


def test_cli_json_with_mode(log_file):
    """Lines 290-292: --json --mode mas → filter."""
    dt.add("t", "id1", None, "a", "b", "t", mode="mas")
    dt.add("t", "id2", None, "a", "b", "t", mode="framework")
    r = _run_cli("--json", "--mode", "mas", log_file=log_file)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["total"] == 1


def test_cli_tree(log_file):
    """Lines 297-307: --tree → ASCII tree."""
    dt.add("t", "id1", None, "a", "b", "task-1")
    r = _run_cli("--tree", log_file=log_file)
    assert r.returncode == 0
    assert "Dispatch Tree" in r.stdout
    assert "1 entries" in r.stdout
    assert "⏳" in r.stdout  # running icon


def test_cli_tree_with_mode(log_file):
    """Lines 299-301: --tree --mode framework."""
    dt.add("t", "id1", None, "a", "b", "t", mode="framework")
    r = _run_cli("--tree", "--mode", "framework", log_file=log_file)
    assert r.returncode == 0
    assert "Dispatch Tree" in r.stdout


def test_cli_stats(log_file):
    """Lines 309-327: --stats → aggregate JSON."""
    dt.add("t", "id1", None, "a", "b", "t")
    dt.add("t", "id2", None, "a", "b", "t")
    dt.done("id1", 3000, 1, "ok", None)
    dt.done("id2", 2000, 1, "x", "err")
    r = _run_cli("--stats", log_file=log_file)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["total"] == 2
    assert data["completed"] == 1
    assert data["failed"] == 1
    # avg_dur: (3000 + 2000) / 2 = 2500
    assert data["avg_duration_ms"] == 2500


def test_cli_stats_no_durations(log_file):
    """Lines 319-320: no durations → avg_dur=0."""
    dt.add("t", "id1", None, "a", "b", "t")  # duration_ms=None
    r = _run_cli("--stats", log_file=log_file)
    data = json.loads(r.stdout)
    assert data["avg_duration_ms"] == 0


def test_cli_mq_stats_unavailable(log_file, tmp_path):
    """Lines 332-335: mq import fails → error JSON."""
    # Block the import via a fake module that raises on load
    fake_dir = tmp_path / "block"
    fake_dir.mkdir()
    (fake_dir / "dev_message_queue.py").write_text(
        "raise ImportError('blocked for test')\n"
    )
    # Put it FIRST in PYTHONPATH so it's found before real tools/dev_message_queue
    env = os.environ.copy()
    env["MAS_DISPATCH_LOG"] = str(log_file)
    # Empty PYTHONPATH + only this dir → only the broken module is importable
    env["PYTHONPATH"] = str(fake_dir)
    p = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path=[p for p in sys.path if 'mas-engineer' not in p];"
         "exec(open('tools/dev_dispatch_tracker.py').read())",
         "--mq-stats"],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT), timeout=15
    )
    assert p.returncode == 0, f"stderr: {p.stderr}"
    data = json.loads(p.stdout)
    assert data == {"error": "dev_message_queue unavailable"}


def test_cli_mq_stats_available(log_file, tmp_path):
    """Lines 336-338: mq available → JSON with stats (with indent=2).

    Strategy: exec the SUT source in a fresh namespace after
    monkey-patching the source to point _mq() at our fake.
    """
    # Read SUT and patch _mq() body
    sut = (REPO_ROOT / "tools" / "dev_dispatch_tracker.py").read_text()
    # Replace the body of _mq() so it always returns our fake
    # Original: def _mq(): try: import dev_message_queue; return ... ; except: return None
    # Patch by adding a monkey-patch line at the top of the file
    patched = (
        "class _FakeMQ:\n"
        "    def stats(self):\n"
        "        return {'topics': {'dispatches': {\n"
        "            'depth': 3, 'current_p95_lag_ms': 50,\n"
        "            'dlq_count_for_topic': 0, 'retry_rate': 0.1,\n"
        "            'completed_total': 100,\n"
        "        }}, 'generated_at': 'x', 'dlq_count_total': 0}\n"
        "    def enqueue(self, *a, **kw): return True\n"
        "_ORIG_MQ = _mq if False else None  # placeholder\n"
        + sut.replace(
            "def _mq():\n    \"\"\"Import dev_message_queue, return None if not available.\"\"\"\n    try:\n        tools_dir = os.path.dirname(os.path.abspath(__file__))\n        if tools_dir not in sys.path:\n            sys.path.insert(0, tools_dir)\n        import dev_message_queue  # type: ignore\n        return dev_message_queue\n    except Exception:\n        return None",
            "def _mq():\n    return _FakeMQ()",
        )
    )
    bootstrap = tmp_path / "_bootstrap.py"
    bootstrap.write_text(
        "import sys, json\n"
        "sys.path.insert(0, '.')\n"
        "sys.argv = ['dev_dispatch_tracker.py', '--mq-stats']\n"
        "exec(" + repr(patched) + ", {'__name__': '__main__', '__file__': 'tools/dev_dispatch_tracker.py'})\n"
    )
    env = os.environ.copy()
    env["MAS_DISPATCH_LOG"] = str(log_file)
    p = subprocess.run(
        [sys.executable, str(bootstrap)],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT), timeout=15
    )
    assert p.returncode == 0, f"stderr: {p.stderr}"
    data = json.loads(p.stdout)
    assert data["depth"] == 3
    assert data["lag_p95_ms"] == 50
    assert data["dlq_count"] == 0
    assert data["completed_total"] == 100


def test_cli_clear(log_file):
    """Lines 340-342: --clear → removes log + prints msg."""
    log_file.write_text("x")
    r = _run_cli("--clear", log_file=log_file)
    assert r.returncode == 0
    assert "dispatch log cleared" in r.stdout
    assert not log_file.exists()


def test_cli_default_no_args(log_file):
    """Lines 344-350: no args → recent tree."""
    dt.add("t", "id1", None, "a", "b", "task-default")
    r = _run_cli(log_file=log_file)
    assert r.returncode == 0
    assert "Dispatch Tree" in r.stdout
