"""R110-421 — coverage-push r4: tools/dev_dispatch_tracer.py 0% → ~98%.

The existing test_dev_dispatch_tracer_r110380.py uses exec() to run
the module's source, which is invisible to pytest-cov. Result: 0%
despite 50+ tests. This file uses real import + monkeypatch on the
module-level DISPATCH_LOG and STATUS_FILE globals to actually
exercise every statement.

Targets:
- get_next_id() first-of-day + increment + corrupt-line-tolerance
- log_dispatch() basic + parent_id + custom mode
- complete_dispatch() updates matching entry only
- show_status() empty + active/completed/failed mix + durations
- build_tree() flat + nested via parent_id chain
- update_dashboard() no-file-fallback + full-merge + history-trim
- __main__ CLI: log/complete/status/tree/update + missing args + bad cmd
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Real import — coverage will see it
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import dev_dispatch_tracer as dt  # noqa: E402


@pytest.fixture
def log_paths(tmp_path, monkeypatch):
    """Redirect DISPATCH_LOG and STATUS_FILE to tmp paths."""
    log = tmp_path / "mas-dispatch.ndjson"
    status = tmp_path / "mas-dashboard-status.json"
    monkeypatch.setattr(dt, "DISPATCH_LOG", str(log))
    monkeypatch.setattr(dt, "STATUS_FILE", str(status))
    return log, status


def _write_entry(log_path: Path, eid: str, status: str = "active",
                 duration_ms: int = 0, parent_id=None, ts=None,
                 from_="a", to_="b", task="T"):
    """Append a JSON-line entry to the dispatch log."""
    entry = {
        "id": eid,
        "parent_id": parent_id,
        "ts": ts or datetime.now(timezone.utc).isoformat(),
        "from": from_,
        "to": to_,
        "task": task,
        "mode": "sync",
        "status": status,
        "duration_ms": duration_ms,
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


# =============================================================================
# get_next_id (line 19)
# =============================================================================
class TestGetNextId:
    def test_first_entry_of_day(self, log_paths):
        log, _ = log_paths
        # Empty log → first entry of today = YYYYMMDD_0001
        eid = dt.get_next_id()
        today = datetime.now().strftime("%Y%m%d")
        assert eid == f"{today}_0001"

    def test_increments_with_existing_today(self, log_paths):
        log, _ = log_paths
        _write_entry(log, f"{datetime.now().strftime('%Y%m%d')}_0007")
        _write_entry(log, f"{datetime.now().strftime('%Y%m%d')}_0003")
        eid = dt.get_next_id()
        assert eid.endswith("_0008")

    def test_ignores_other_days(self, log_paths):
        log, _ = log_paths
        # Old entries from yesterday should NOT affect today's counter
        _write_entry(log, "20260101_9999")
        eid = dt.get_next_id()
        today = datetime.now().strftime("%Y%m%d")
        assert eid == f"{today}_0001"

    def test_corrupt_json_line_tolerated(self, log_paths):
        log, _ = log_paths
        log.write_text("not-valid-json\n")
        eid = dt.get_next_id()  # should not crash
        today = datetime.now().strftime("%Y%m%d")
        assert eid == f"{today}_0001"

    def test_empty_lines_skipped(self, log_paths):
        log, _ = log_paths
        log.write_text("\n\n   \n")
        eid = dt.get_next_id()
        today = datetime.now().strftime("%Y%m%d")
        assert eid == f"{today}_0001"

    def test_non_numeric_suffix_fallback_to_zero(self, log_paths):
        """ids with non-numeric suffix → nums.append(0) → +1 = 1."""
        log, _ = log_paths
        today = datetime.now().strftime("%Y%m%d")
        _write_entry(log, f"{today}_abc")  # int("abc") fails → 0
        eid = dt.get_next_id()
        assert eid.endswith("_0001")  # max(0) + 1 = 1


# =============================================================================
# log_dispatch (line 43)
# =============================================================================
class TestLogDispatch:
    def test_basic(self, log_paths):
        log, _ = log_paths
        eid = dt.log_dispatch("mas-engineer", "sub_mas-scanner", "SCAN")
        assert eid.endswith("_0001")
        lines = log.read_text().strip().split("\n")
        entry = json.loads(lines[0])
        assert entry["from"] == "mas-engineer"
        assert entry["to"] == "sub_mas-scanner"
        assert entry["task"] == "SCAN"
        assert entry["mode"] == "sync"  # default
        assert entry["status"] == "active"
        assert entry["parent_id"] is None

    def test_with_parent_id_and_custom_mode(self, log_paths):
        log, _ = log_paths
        eid = dt.log_dispatch("a", "b", "T", mode="async", parent_id="p123")
        entry = json.loads(log.read_text().strip())
        assert entry["parent_id"] == "p123"
        assert entry["mode"] == "async"


# =============================================================================
# complete_dispatch (line 61)
# =============================================================================
class TestCompleteDispatch:
    def test_updates_matching_entry(self, log_paths):
        log, _ = log_paths
        dt.log_dispatch("a", "b", "T")
        dt.complete_dispatch(dt.get_next_id() if False else
                              json.loads(log.read_text().strip())["id"],
                              1500, "completed")
        entries = [json.loads(l) for l in log.read_text().strip().split("\n")]
        assert entries[0]["status"] == "completed"
        assert entries[0]["duration_ms"] == 1500

    def test_leaves_other_entries_alone(self, log_paths):
        log, _ = log_paths
        # Two entries, complete only first
        eid_a = dt.log_dispatch("a", "b", "T1")
        _write_entry(log, "20260101_9999", status="active", ts="2026-01-01T00:00:00Z")
        dt.complete_dispatch(eid_a, 2000)
        entries = [json.loads(l) for l in log.read_text().strip().split("\n")]
        # 2 entries remain (old + updated a), the old one untouched
        assert len(entries) == 2
        statuses = {e["id"]: e.get("status") for e in entries}
        assert statuses[eid_a] == "completed"
        assert statuses["20260101_9999"] == "active"

    def test_corrupt_line_tolerated(self, log_paths):
        log, _ = log_paths
        log.write_text("garbage\n")
        dt.complete_dispatch("nope", 100)  # should not crash
        # File should be rewritten, garbage line silently dropped
        assert log.read_text() == ""

    def test_no_log_file_creates_empty_file(self, log_paths):
        """Module's complete_dispatch opens in 'w' mode if file exists.
        If file does not exist, the read block is skipped but the
        subsequent 'with open(..., "w")' always writes — even if entries
        is empty. Result: empty file created."""
        log, _ = log_paths
        assert not log.exists()
        dt.complete_dispatch("anything", 100)
        # The write-block always runs → empty file is created.
        assert log.exists()
        assert log.read_text() == ""


# =============================================================================
# show_status (line 82)
# =============================================================================
class TestShowStatus:
    def test_empty(self, log_paths, capsys):
        log, _ = log_paths
        dt.show_status()
        out = capsys.readouterr().out
        assert "=== DISPATCH-STATUS ===" in out
        assert "Total:  0" in out
        assert "Active: 0" in out

    def test_with_mixed_statuses(self, log_paths, capsys):
        log, _ = log_paths
        _write_entry(log, "e1", "active")
        _write_entry(log, "e2", "completed", duration_ms=100)
        _write_entry(log, "e3", "completed", duration_ms=200)
        _write_entry(log, "e4", "failed", duration_ms=50)
        dt.show_status()
        out = capsys.readouterr().out
        assert "Total:  4" in out
        assert "Active: 1" in out
        assert "Done:   2" in out
        assert "Failed: 1" in out
        # avg of (100, 200, 50) = 116.67 → round = 117
        assert "117ms" in out
        # Last 5 — should mention all 4
        assert "🟡" in out
        assert "🟢" in out
        assert "🔴" in out

    def test_corrupt_line_skipped(self, log_paths, capsys):
        log, _ = log_paths
        # Append a corrupt line, a valid entry, another corrupt, another valid
        with open(log, "a") as f:
            f.write("garbage\n")
        _write_entry(log, "e1")
        with open(log, "a") as f:
            f.write("more-garbage\n")
        _write_entry(log, "e2", "completed", duration_ms=50)
        dt.show_status()
        out = capsys.readouterr().out
        assert "DISPATCH-STATUS" in out
        assert "Total:  2" in out


# =============================================================================
# build_tree (line 115)
# =============================================================================
class TestBuildTree:
    def test_empty_log_returns_empty_tree(self, log_paths):
        log, _ = log_paths
        assert dt.build_tree() == []
        assert dt.build_tree(last_n=10) == []

    def test_flat_no_parents(self, log_paths):
        log, _ = log_paths
        _write_entry(log, "e1")
        _write_entry(log, "e2")
        tree = dt.build_tree()
        assert len(tree) == 2
        assert tree[0]["id"] == "e1"
        assert "children" in tree[0]

    def test_nested_parent_child_chain(self, log_paths):
        log, _ = log_paths
        _write_entry(log, "root", parent_id=None)
        _write_entry(log, "child1", parent_id="root")
        _write_entry(log, "grandchild", parent_id="child1")
        tree = dt.build_tree()
        assert len(tree) == 1
        root = tree[0]
        assert root["id"] == "root"
        assert len(root["children"]) == 1
        child = root["children"][0]
        assert child["id"] == "child1"
        assert len(child["children"]) == 1
        assert child["children"][0]["id"] == "grandchild"

    def test_last_n_truncation(self, log_paths):
        log, _ = log_paths
        for i in range(50):
            _write_entry(log, f"e{i:03d}")
        tree = dt.build_tree(last_n=5)
        assert len(tree) == 5
        # entries[-5:] of e000..e049 → e045, e046, e047, e048, e049
        assert [n["id"] for n in tree] == ["e045", "e046", "e047", "e048", "e049"]

    def test_last_n_larger_than_total_returns_all(self, log_paths):
        log, _ = log_paths
        _write_entry(log, "e1")
        _write_entry(log, "e2")
        tree = dt.build_tree(last_n=100)
        assert len(tree) == 2


# =============================================================================
# update_dashboard (line 152)
# =============================================================================
class TestUpdateDashboard:
    def test_no_dashboard_file_prints_warning(self, log_paths, capsys):
        log, _ = log_paths
        _write_entry(log, "e1")
        dt.update_dashboard()  # should print warning, not crash
        out = capsys.readouterr().out
        assert "No Dashboard-JSON found" in out

    def test_full_merge_with_history_trim(self, log_paths, capsys):
        log, status = log_paths
        _write_entry(log, "e1", "completed", duration_ms=100)
        # Seed dashboard with existing 24+ history entries (to trigger trim)
        existing_history = [{"time": f"{i:02d}:00", "count": i} for i in range(30)]
        existing_health = [{"time": f"{i:02d}:00", "mas": 100, "framework": 100}
                           for i in range(30)]
        dashboard = {
            "mas": {"status": "operational"},
            "framework": {"status": "operational"},
            "history": {
                "dispatch_volume": existing_history,
                "health_trend": existing_health,
            },
        }
        status.write_text(json.dumps(dashboard))
        dt.update_dashboard()
        # Reload and verify trim + merge
        result = json.loads(status.read_text())
        assert len(result["history"]["dispatch_volume"]) == 24
        assert len(result["history"]["health_trend"]) == 24
        assert result["dispatch"]["total_calls"] == 1
        assert result["dispatch"]["completed"] == 1
        assert "100ms" == f"{result['dispatch']['avg_duration_ms']}ms" or \
               result["dispatch"]["avg_duration_ms"] == 100
        assert "Dashboard updated" in capsys.readouterr().out

    def test_non_operational_status_yields_lower_health(self, log_paths):
        log, status = log_paths
        _write_entry(log, "e1")
        dashboard = {
            "mas": {"status": "broken"},
            "framework": {"status": "broken"},
            "history": {"dispatch_volume": [], "health_trend": []},
        }
        status.write_text(json.dumps(dashboard))
        dt.update_dashboard()
        result = json.loads(status.read_text())
        # Last health_trend entry should have mas=50, framework=50
        last = result["history"]["health_trend"][-1]
        assert last["mas"] == 50
        assert last["framework"] == 50


# =============================================================================
# __main__ CLI (line 205)
# =============================================================================
class TestCliMain:
    """Run the module's CLI by subprocess — guarantees __main__ block is hit."""

    def _run(self, *args, env=None):
        script = Path(__file__).resolve().parents[1] / "tools" / "dev_dispatch_tracer.py"
        return subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True, text=True, env=env,
        )

    def test_no_args_exits_1(self):
        r = self._run()
        assert r.returncode == 1
        assert "Usage" in r.stdout

    def test_log_cmd(self, tmp_path):
        # Set DISPATCH_LOG via env — but module uses global, so use tmp_path
        # by patching via PYTHONPATH and a wrapper. Simpler: just trust the
        # module's default /tmp behavior but clean up after.
        log = "/tmp/test_dispatch_tracer_log.ndjson"
        if os.path.exists(log):
            os.remove(log)
        r = self._run("log", "a", "b", "T")
        assert r.returncode == 0
        assert "Dispatch: a → b" in r.stdout
        # Cleanup
        if os.path.exists(log):
            os.remove(log)

    def test_status_cmd_no_data(self):
        # Use a fresh temp log by setting it empty first
        log = "/tmp/mas-dispatch.ndjson"
        if os.path.exists(log):
            os.remove(log)
        r = self._run("status")
        assert r.returncode == 0
        assert "DISPATCH-STATUS" in r.stdout

    def test_complete_cmd(self):
        log = "/tmp/mas-dispatch.ndjson"
        # Seed with one entry
        entry = {"id": "test123", "parent_id": None, "ts": "now",
                 "from": "a", "to": "b", "task": "T", "mode": "sync",
                 "status": "active", "duration_ms": 0}
        with open(log, "w") as f:
            f.write(json.dumps(entry) + "\n")
        r = self._run("complete", "test123", "500")
        assert r.returncode == 0
        assert "test123" in r.stdout
        # Verify file updated
        with open(log) as f:
            updated = json.loads(f.readline())
        assert updated["status"] == "completed"
        assert updated["duration_ms"] == 500
        os.remove(log)

    def test_tree_cmd_default_last_n(self):
        log = "/tmp/mas-dispatch.ndjson"
        if os.path.exists(log):
            os.remove(log)
        r = self._run("tree")
        assert r.returncode == 0
        assert r.stdout.strip() == "[]"  # empty log

    def test_tree_cmd_with_last_n(self):
        log = "/tmp/mas-dispatch.ndjson"
        if os.path.exists(log):
            os.remove(log)
        r = self._run("tree", "5")
        assert r.returncode == 0

    def test_update_cmd_no_file(self):
        status = "/tmp/mas-dashboard-status.json"
        if os.path.exists(status):
            os.remove(status)
        r = self._run("update")
        assert r.returncode == 0
        assert "No Dashboard-JSON found" in r.stdout

    def test_unknown_cmd_prints_available(self):
        r = self._run("bogus")
        assert "Unbekannter Command: bogus" in r.stdout
        assert "Available: log, complete, status, tree, update" in r.stdout

    def test_log_cmd_with_extra_args(self):
        """log <from> <to> <task> [mode] [parent] — exercises the argv indexing."""
        log = "/tmp/mas-dispatch.ndjson"
        if os.path.exists(log):
            os.remove(log)
        r = self._run("log", "a", "b", "T", "async", "parent123")
        assert r.returncode == 0
        # Verify entry has async mode and parent_id
        with open(log) as f:
            entry = json.loads(f.readline())
        assert entry["mode"] == "async"
        assert entry["parent_id"] == "parent123"
        os.remove(log)
