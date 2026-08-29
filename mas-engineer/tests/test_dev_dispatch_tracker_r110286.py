"""Tests for mas-engineer/tools/dev_dispatch_tracker.py — R110-286.

Coverage target: dev_dispatch_tracker.py 49% → ~85%.

Tests:
- _read_all: missing file, empty file, malformed lines, valid JSON
- _write_all: creates dir, writes one per line
- add(): dual-write legacy + MQ, default workspace, mode default
- done(): updates existing entry, no-match no-update, errors set status=error
- get_tree(): mode filter, last_n slicing, status counts, tree building
- mq_stats(): MQ unavailable returns None, error in mq.stats, success
- clear(): removes file, no-op if missing
"""
import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_dispatch_tracker as dt


@pytest.fixture
def tmp_log(monkeypatch, tmp_path):
    """Point LEGACY_LOG at a per-test file."""
    log = tmp_path / "mas-dispatch.ndjson"
    monkeypatch.setattr(dt, "LEGACY_LOG", str(log))
    return log


@pytest.fixture
def no_mq(monkeypatch):
    """Force _mq() to return None (MQ unavailable)."""
    monkeypatch.setattr(dt, "_mq", lambda: None)
    return None


class TestReadAll:
    def test_missing_file_returns_empty_list(self, tmp_log):
        assert dt._read_all() == []

    def test_empty_file_returns_empty(self, tmp_log):
        tmp_log.write_text("")
        assert dt._read_all() == []

    def test_valid_lines(self, tmp_log):
        tmp_log.write_text(
            json.dumps({"id": "1", "task": "x"}) + "\n" +
            json.dumps({"id": "2", "task": "y"}) + "\n"
        )
        entries = dt._read_all()
        assert len(entries) == 2
        assert entries[0]["id"] == "1"
        assert entries[1]["task"] == "y"

    def test_malformed_lines_skipped(self, tmp_log):
        tmp_log.write_text(
            "not valid json\n" +
            json.dumps({"id": "1"}) + "\n" +
            "{broken\n"
        )
        entries = dt._read_all()
        assert len(entries) == 1
        assert entries[0]["id"] == "1"

    def test_blank_lines_skipped(self, tmp_log):
        tmp_log.write_text(
            "\n" +
            json.dumps({"id": "1"}) + "\n" +
            "   \n"
        )
        entries = dt._read_all()
        assert len(entries) == 1


class TestWriteAll:
    def test_creates_parent_dir(self, tmp_path, monkeypatch):
        nested = tmp_path / "deep" / "dir" / "log.ndjson"
        monkeypatch.setattr(dt, "LEGACY_LOG", str(nested))
        dt._write_all([{"id": "x"}])
        assert nested.exists()
        assert nested.parent.is_dir()

    def test_writes_one_per_line(self, tmp_log):
        dt._write_all([{"id": "1"}, {"id": "2"}, {"id": "3"}])
        content = tmp_log.read_text()
        lines = [l for l in content.split("\n") if l]
        assert len(lines) == 3
        assert json.loads(lines[0])["id"] == "1"
        assert json.loads(lines[2])["id"] == "3"

    def test_unicode_safe(self, tmp_log):
        """R110-270: ensure_ascii=False — unicode in task names preserved."""
        dt._write_all([{"id": "1", "task": "übung"}])
        content = tmp_log.read_text()
        assert "übung" in content

    def test_empty_list_writes_empty_file(self, tmp_log):
        dt._write_all([])
        assert tmp_log.exists()
        assert tmp_log.read_text() == ""


class TestAdd:
    def test_writes_to_legacy(self, tmp_log, no_mq):
        e = dt.add("2026-08-29T10:00:00Z", "abc123", None,
                   "from-agent", "to-agent", "do thing", "mas")
        assert e["id"] == "abc123"
        assert e["status"] == "running"
        assert e["duration_ms"] is None
        assert e["turns"] == 0
        # File was written
        assert tmp_log.exists()
        content = tmp_log.read_text()
        assert "abc123" in content
        assert "to-agent" in content

    def test_default_workspace(self, tmp_log, no_mq):
        e = dt.add("ts", "id1", None, "a", "b", "t")
        # workspace defaults to os.getcwd()
        assert e["workspace"] == os.getcwd()

    def test_explicit_workspace(self, tmp_log, no_mq):
        e = dt.add("ts", "id1", None, "a", "b", "t",
                   mode="mas", workspace="/custom/path")
        assert e["workspace"] == "/custom/path"

    def test_default_mode_is_mas(self, tmp_log, no_mq):
        e = dt.add("ts", "id1", None, "a", "b", "t")
        assert e["mode"] == "mas"

    def test_framework_mode(self, tmp_log, no_mq):
        e = dt.add("ts", "id1", None, "a", "b", "t", mode="framework")
        assert e["mode"] == "framework"

    def test_mq_enqueue_called(self, tmp_log, monkeypatch):
        """When MQ is available, add() enqueues a dispatch_start event."""
        mock_mq = MagicMock()
        monkeypatch.setattr(dt, "_mq", lambda: mock_mq)
        dt.add("ts", "id1", None, "a", "b", "t", "mas")
        mock_mq.enqueue.assert_called_once()
        kwargs = mock_mq.enqueue.call_args
        assert kwargs[0][0] == "dispatches"
        assert kwargs[0][1]["event_type"] == "dispatch_start"
        assert kwargs[1]["idempotency_key"] == "dispatch_start-id1"

    def test_mq_exception_does_not_crash(self, tmp_log, monkeypatch):
        """MQ enqueue failure is best-effort — should not raise."""
        mock_mq = MagicMock()
        mock_mq.enqueue.side_effect = RuntimeError("MQ down")
        monkeypatch.setattr(dt, "_mq", lambda: mock_mq)
        # Should not raise
        e = dt.add("ts", "id1", None, "a", "b", "t", "mas")
        assert e["id"] == "id1"


class TestDone:
    def test_updates_existing_entry_status_done(self, tmp_log, no_mq):
        dt.add("ts", "id1", None, "a", "b", "t", "mas")
        result = dt.done("id1", 5000, 3, "all good")
        assert len(result) == 1
        assert result[0]["status"] == "done"
        assert result[0]["duration_ms"] == 5000
        assert result[0]["turns"] == 3
        assert result[0]["result_summary"] == "all good"
        assert result[0]["errors"] is None

    def test_sets_status_error_when_errors(self, tmp_log, no_mq):
        dt.add("ts", "id1", None, "a", "b", "t", "mas")
        result = dt.done("id1", 1000, 1, "partial", errors="boom")
        assert result[0]["status"] == "error"
        assert result[0]["errors"] == "boom"

    def test_nonexistent_id_no_update(self, tmp_log, no_mq):
        dt.add("ts", "id1", None, "a", "b", "t", "mas")
        # Try to done a non-existing id — should not crash
        result = dt.done("nope", 1000, 1, "x")
        # id1 is still running
        assert result[0]["id"] == "id1"
        assert result[0]["status"] == "running"

    def test_empty_log_returns_empty(self, tmp_log, no_mq):
        result = dt.done("anything", 1000, 1, "x")
        assert result == []

    def test_mq_done_enqueued(self, tmp_log, monkeypatch):
        mock_mq = MagicMock()
        monkeypatch.setattr(dt, "_mq", lambda: mock_mq)
        dt.add("ts", "id1", None, "a", "b", "t", "mas")
        mock_mq.enqueue.reset_mock()
        dt.done("id1", 5000, 3, "ok")
        mock_mq.enqueue.assert_called_once()
        kwargs = mock_mq.enqueue.call_args
        assert kwargs[0][1]["event_type"] == "dispatch_done"
        assert kwargs[1]["idempotency_key"] == "dispatch_done-id1"

    def test_no_mq_when_id_missing(self, tmp_log, monkeypatch):
        """When done() is called for a non-existent id, no MQ enqueue happens."""
        mock_mq = MagicMock()
        monkeypatch.setattr(dt, "_mq", lambda: mock_mq)
        dt.done("nope", 1000, 1, "x")
        mock_mq.enqueue.assert_not_called()


class TestGetTree:
    def _seed(self, tmp_log):
        # 3 dispatches: 1 root, 1 child of root, 1 grandchild
        dt.add("ts", "root", None, "a", "x", "root task", "mas")
        dt.add("ts", "child", "root", "x", "y", "child task", "framework")
        dt.add("ts", "grand", "child", "y", "z", "grand task", "mas")
        dt.done("root", 5000, 3, "root done")
        # child and grand still running

    def test_total_count(self, tmp_log, no_mq):
        self._seed(tmp_log)
        tree = dt.get_tree()
        assert tree["total"] == 3

    def test_status_counts(self, tmp_log, no_mq):
        self._seed(tmp_log)
        tree = dt.get_tree()
        assert tree["done"] == 1
        assert tree["running"] == 2
        assert tree["errors"] == 0

    def test_error_count(self, tmp_log, no_mq):
        self._seed(tmp_log)
        dt.done("child", 100, 1, "failed", errors="oops")
        tree = dt.get_tree()
        assert tree["errors"] == 1
        assert tree["done"] == 1
        assert tree["running"] == 1

    def test_mode_filter_mas(self, tmp_log, no_mq):
        self._seed(tmp_log)
        tree = dt.get_tree(mode="mas")
        # root (mas) + grand (mas) = 2
        assert tree["total"] == 2
        assert all(e.get("mode") == "mas" for e in tree["entries"])

    def test_mode_filter_framework(self, tmp_log, no_mq):
        self._seed(tmp_log)
        tree = dt.get_tree(mode="framework")
        # child (framework) = 1
        assert tree["total"] == 1

    def test_last_n_slicing(self, tmp_log, no_mq):
        for i in range(5):
            dt.add("ts", f"id{i}", None, "a", "b", f"task{i}", "mas")
        tree = dt.get_tree(last_n=3)
        assert tree["total"] == 3
        assert tree["entries"][0]["id"] == "id2"
        assert tree["entries"][-1]["id"] == "id4"

    def test_tree_building_root_first(self, tmp_log, no_mq):
        self._seed(tmp_log)
        tree = dt.get_tree()
        # The tree should have root → child → grand with indentation
        assert any("root" in line for line in tree["tree"])
        # All entries with parent_id should be in children, not roots
        root_lines = [l for l in tree["tree"] if l.startswith("  ") is False]
        assert any("root" in l for l in root_lines)

    def test_returns_entries(self, tmp_log, no_mq):
        self._seed(tmp_log)
        tree = dt.get_tree()
        assert "entries" in tree
        assert len(tree["entries"]) == 3

    def test_empty_returns_empty_tree(self, tmp_log, no_mq):
        tree = dt.get_tree()
        assert tree["total"] == 0
        assert tree["tree"] == []
        assert tree["entries"] == []


class TestMqStats:
    def test_returns_none_when_mq_unavailable(self, no_mq):
        assert dt.mq_stats() is None

    def test_returns_aggregated_dict(self, monkeypatch):
        mock_mq = MagicMock()
        mock_mq.stats.return_value = {
            "topics": {
                "dispatches": {
                    "depth": 7,
                    "current_p95_lag_ms": 250,
                    "dlq_count_for_topic": 2,
                    "retry_rate": 0.15,
                    "completed_total": 42,
                }
            }
        }
        monkeypatch.setattr(dt, "_mq", lambda: mock_mq)
        stats = dt.mq_stats()
        assert stats["depth"] == 7
        assert stats["lag_p95_ms"] == 250
        assert stats["dlq_count"] == 2
        assert stats["retry_rate"] == 0.15
        assert stats["completed_total"] == 42

    def test_missing_topic_returns_zeros(self, monkeypatch):
        mock_mq = MagicMock()
        mock_mq.stats.return_value = {"topics": {}}  # no dispatches
        monkeypatch.setattr(dt, "_mq", lambda: mock_mq)
        stats = dt.mq_stats()
        assert stats["depth"] == 0
        assert stats["lag_p95_ms"] == 0
        assert stats["dlq_count"] == 0

    def test_error_in_stats_returns_error_dict(self, monkeypatch):
        mock_mq = MagicMock()
        mock_mq.stats.side_effect = RuntimeError("kaboom")
        monkeypatch.setattr(dt, "_mq", lambda: mock_mq)
        result = dt.mq_stats()
        assert "error" in result
        assert "kaboom" in result["error"]


class TestClear:
    def test_removes_existing_file(self, tmp_log):
        tmp_log.write_text("garbage")
        result = dt.clear()
        assert result == {"status": "cleared"}
        assert not tmp_log.exists()

    def test_no_op_when_missing(self, tmp_log):
        # File does not exist — should not crash
        result = dt.clear()
        assert result == {"status": "cleared"}
        assert not tmp_log.exists()
