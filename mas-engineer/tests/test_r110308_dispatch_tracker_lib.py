"""
test_r110308_dispatch_tracker_lib.py — R110-308: cover the library
functions of dev_dispatch_tracker (not the __main__ CLI).

Missing-line targets:
  - L73 _read_all: import + defensive except (L64-68)
  - L97 add: real write of a new entry
  - L138 done: real update of an existing entry
  - L183 get_tree: real tree computation
  - L228 mq_stats: returns None if dev_message_queue unavailable
  - L252 clear: deletes all entries
"""
import sys
import json
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"


@pytest.fixture
def dt(tmp_path, monkeypatch):
    """Import dev_dispatch_tracker with a sandboxed dispatch-log dir."""
    # Reset module cache so each test gets a fresh import
    sys.modules.pop("dev_dispatch_tracker", None)
    # Redirect dispatch log to tmp_path via MAS_DISPATCH_LOG env var
    # (the module reads it at import time, L49-52)
    log_file = tmp_path / "dispatch.ndjson"
    monkeypatch.setenv("MAS_DISPATCH_LOG", str(log_file))
    # Also clear MQ to avoid real enqueue attempts
    monkeypatch.setenv("DISPATCH_MQ_DISABLED", "1")
    sys.path.insert(0, str(TOOLS))
    try:
        # Need to reimport with the env var set
        import importlib
        if "dev_dispatch_tracker" in sys.modules:
            importlib.reload(sys.modules["dev_dispatch_tracker"])
        else:
            import dev_dispatch_tracker
        return dev_dispatch_tracker
    finally:
        sys.path.pop(0)


def test_read_all_empty(dt):
    """_read_all on a non-existent dir returns [] (the except branch L65-68)."""
    # tmp_path is empty, so the file doesn't exist yet
    result = dt._read_all()
    assert result == []


def test_add_writes_entry(dt):
    """add() writes a JSONL line to the dispatch log and _read_all sees it."""
    dt.add("2026-08-30T12:00:00Z", "e1", None, "dev", "to-agent", "task", "mas")
    entries = dt._read_all()
    assert len(entries) == 1
    assert entries[0]["id"] == "e1"
    assert entries[0]["status"] == "running"
    # The legacy log uses "to" not "to_agent" (see L104-106)
    assert entries[0]["to"] == "to-agent"


def test_done_marks_entry(dt):
    """done() updates an existing entry's status, duration, turns."""
    dt.add("2026-08-30T12:00:00Z", "e2", None, "dev", "to", "t", "mas")
    dt.done("e2", 1234, 5, "all good", None)
    entries = dt._read_all()
    assert len(entries) == 1
    assert entries[0]["status"] == "done"
    assert entries[0]["duration_ms"] == 1234
    assert entries[0]["turns"] == 5
    assert entries[0]["result_summary"] == "all good"
    assert "errors" not in entries[0] or entries[0]["errors"] is None


def test_done_with_errors(dt):
    """done() marks the entry as 'error' when errors are provided (L145)."""
    dt.add("2026-08-30T12:00:00Z", "e3", None, "dev", "to", "t", "mas")
    dt.done("e3", 500, 1, "failed", "timeout")
    entries = dt._read_all()
    assert entries[0]["errors"] == "timeout"
    # Per L145: status is "error" if errors else "done"
    assert entries[0]["status"] == "error"


def test_get_tree_empty(dt):
    """get_tree() on an empty log returns empty structure."""
    tree = dt.get_tree()
    assert tree["total"] == 0
    assert tree["entries"] == [] or "entries" in tree
    # The 'tree' key is a list of ASCII lines
    assert tree["tree"] == []


def test_get_tree_with_entries(dt):
    """get_tree() on a populated log returns the right structure."""
    dt.add("2026-08-30T12:00:00Z", "root1", None, "dev", "a", "t1", "mas")
    dt.add("2026-08-30T12:00:01Z", "child1", "root1", "a", "b", "t2", "mas")
    tree = dt.get_tree()
    assert tree["total"] == 2
    assert len(tree["tree"]) >= 2


def test_mq_stats_unavailable_returns_none(dt, monkeypatch):
    """mq_stats() returns None when dev_message_queue import fails.

    The _mq() function in dev_dispatch_tracker does a fresh
    'import dev_message_queue' each call. We simulate the
    ImportError by putting a fake module in sys.modules that
    raises on import by removing the real one AND
    making the next import fail.
    """
    import importlib
    # Remove real module so import statement would re-import
    sys.modules.pop("dev_message_queue", None)
    # Replace the import machinery temporarily: when importlib._bootstrap
    # tries to load 'dev_message_queue', it will use sys.path. We
    # block it by registering a meta-path finder that raises.
    class BlockingFinder:
        def find_spec(self, name, path=None, target=None):
            if name == "dev_message_queue":
                raise ImportError("simulated: dev_message_queue blocked")
            return None

    blocker = BlockingFinder()
    sys.meta_path.insert(0, blocker)
    try:
        result = dt.mq_stats()
    finally:
        sys.meta_path.remove(blocker)
    assert result is None


def test_clear_empties_log(dt):
    """clear() removes all entries from the dispatch log."""
    dt.add("2026-08-30T12:00:00Z", "c1", None, "dev", "x", "t", "mas")
    dt.add("2026-08-30T12:00:01Z", "c2", None, "dev", "y", "t", "mas")
    assert len(dt._read_all()) == 2
    dt.clear()
    assert dt._read_all() == []
