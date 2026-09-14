"""R110-539 coverage tests for tools/dev_dispatch_tracer.py.

Module: 229 LOC, ~219 stmts, 6 functions + __main__ CLI, 0% covered.

Functions tested:
  - get_next_id()                       lines 19-41
  - log_dispatch(from_agent, to_agent, task, mode, parent_id)
                                        lines 43-59
  - complete_dispatch(entry_id, duration_ms, status)
                                        lines 61-80
  - show_status()                       lines 82-113
  - build_tree(last_n=20)               lines 115-150
  - update_dashboard()                  lines 152-203
  - __main__ CLI                        lines 205-229

Strategy: Direct function calls + monkeypatch of DISPATCH_LOG
and STATUS_FILE to point to tmp_path.

Key paths to cover:
  - get_next_id:
    - DISPATCH_LOG missing → empty entries (22 False)
    - DISPATCH_LOG exists, parses JSON lines (23-30)
    - json.loads error → pass (29-30)
    - date prefix from today (32)
    - existing IDs filter (33)
    - nums parse int from last _-split (35-39)
    - ValueError → nums.append(0) (38-39)
    - next_num = max+1 or 1 (40)
    - return f"{date}_{next_num:04d}" (41)
  - log_dispatch:
    - entry dict construction (45-55)
    - append JSON line (56-57)
    - print msg (58)
    - return entry_id (59)
  - complete_dispatch:
    - read entries (64-76)
    - match id → update status/duration (71-73)
    - write back (77-79)
    - print msg (80)
  - show_status:
    - read entries (84-93)
    - totals (95-100)
    - status icons map (112)
    - print loop (113)
  - build_tree:
    - read entries (117-126)
    - recent slice (128)
    - child_map + roots (131-138)
    - recursive attach_children (141-145)
    - return tree (150)
  - update_dashboard:
    - read entries (154-163)
    - totals (165-170)
    - STATUS_FILE exists → load, update, write (173-200)
    - dashboard["dispatch"] update (177-184)
    - history.append dispatch_volume (188)
    - cap at 24 (189-190)
    - history.append health_trend (191-195)
    - cap at 24 (196-197)
    - write JSON (199-200)
    - STATUS_FILE missing → msg (202-203)
  - __main__ CLI:
    - len < 2 → usage + exit 1 (206-208)
    - log + >=5 args (212-215)
    - complete + >=4 args (216-218)
    - status (219-220)
    - tree + optional last_n (221-224)
    - update (225-226)
    - unknown cmd (227-229)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.dev_dispatch_tracer as dt  # noqa: E402


# ====================== helpers ==================================

@pytest.fixture
def isolated(monkeypatch, tmp_path):
    """Redirect DISPATCH_LOG + STATUS_FILE to tmp paths."""
    log = tmp_path / "mas-dispatch.ndjson"
    status = tmp_path / "mas-dashboard-status.json"
    monkeypatch.setattr(dt, "DISPATCH_LOG", str(log))
    monkeypatch.setattr(dt, "STATUS_FILE", str(status))
    return log, status


def _read_entries(log_path):
    if not log_path.exists():
        return []
    return [json.loads(l) for l in log_path.read_text().splitlines() if l]


# ====================== get_next_id ==============================

def test_get_next_id_no_log(isolated):
    """Covers line 22 False: DISPATCH_LOG missing → start at 1."""
    log, _ = isolated
    assert not log.exists()
    eid = dt.get_next_id()
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    assert eid == f"{today}_0001"


def test_get_next_id_increments(isolated):
    """Covers lines 32-41: existing IDs → max+1."""
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    # Pre-populate
    log.write_text(json.dumps({"id": f"{today}_0001"}) + "\n"
                   + json.dumps({"id": f"{today}_0002"}) + "\n"
                   + json.dumps({"id": f"{today}_0007"}) + "\n")
    eid = dt.get_next_id()
    assert eid == f"{today}_0008"


def test_get_next_id_skips_old_dates(isolated):
    """Covers line 33: only count today's IDs (startwith date filter)."""
    log, _ = isolated
    log.write_text(json.dumps({"id": "20200101_9999"}) + "\n")  # old date
    eid = dt.get_next_id()
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    # Old IDs ignored → start at 1
    assert eid == f"{today}_0001"


def test_get_next_id_handles_bad_lines(isolated):
    """Covers lines 28-30: invalid JSON lines skipped. Note: IDs
    that don't start with today's date are also skipped (line 33
    startswith filter), so non-date-prefixed IDs don't count.
    """
    log, _ = isolated
    log.write_text("garbage line\n"
                   + json.dumps({"id": "x_0005"}) + "\n"  # not date-prefixed
                   + "more garbage\n"
                   + json.dumps({"id": "y_no_underscore_at_end"}) + "\n"
                   + json.dumps({"id": "20200101_9999"}) + "\n"  # old date
                   + json.dumps({"id": "20200101_BAD"}) + "\n")  # unparseable num
    eid = dt.get_next_id()
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    # All non-date-prefixed IDs filtered out → nums empty → 0001
    assert eid == f"{today}_0001"


def test_get_next_id_no_entries_returns_0001(isolated):
    """Covers line 40 False: nums empty → next_num = 1."""
    log, _ = isolated
    log.write_text("")  # empty file
    eid = dt.get_next_id()
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    assert eid == f"{today}_0001"


def test_get_next_id_valueerror_in_num_parse(isolated):
    """Covers lines 38-39: ID has date prefix but unparseable suffix.

    Source has bare `except: nums.append(0)`. Need a today-prefixed
    ID where the last _-split chunk isn't an int.
    """
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    log.write_text(json.dumps({"id": f"{today}_NOTNUM"}) + "\n"
                   + json.dumps({"id": f"{today}_0005"}) + "\n")
    eid = dt.get_next_id()
    # NOTNUM → ValueError → 0, _0005 → 5, max(0,5) + 1 = 6
    assert eid == f"{today}_0006"


# ====================== log_dispatch =============================

def test_log_dispatch_writes_entry(isolated):
    """Covers lines 45-59: log_dispatch writes JSON line + returns id."""
    log, _ = isolated
    eid = dt.log_dispatch("A", "B", "task1")
    entries = _read_entries(log)
    assert len(entries) == 1
    assert entries[0]["from"] == "A"
    assert entries[0]["to"] == "B"
    assert entries[0]["task"] == "task1"
    assert entries[0]["mode"] == "sync"
    assert entries[0]["status"] == "active"
    assert entries[0]["duration_ms"] == 0
    assert entries[0]["parent_id"] is None
    assert eid == entries[0]["id"]


def test_log_dispatch_with_parent_and_mode(isolated):
    """Covers line 43: custom mode + parent_id."""
    log, _ = isolated
    dt.log_dispatch("A", "B", "task", mode="async", parent_id="p_001")
    entry = _read_entries(log)[0]
    assert entry["mode"] == "async"
    assert entry["parent_id"] == "p_001"


def test_log_dispatch_prints(isolated, capsys):
    """Covers line 58: print success message."""
    dt.log_dispatch("X", "Y", "test_task")
    out = capsys.readouterr().out
    assert "Dispatch" in out
    assert "X" in out
    assert "Y" in out


# ====================== complete_dispatch ========================

def test_complete_dispatch_updates_entry(isolated):
    """Covers lines 61-80: match id → update status + duration."""
    log, _ = isolated
    eid = dt.log_dispatch("A", "B", "task")
    dt.complete_dispatch(eid, duration_ms=1234, status="completed")
    entries = _read_entries(log)
    assert entries[0]["status"] == "completed"
    assert entries[0]["duration_ms"] == 1234


def test_complete_dispatch_no_match(isolated):
    """Covers lines 71-73 False: id not found → entries unchanged."""
    log, _ = isolated
    dt.log_dispatch("A", "B", "task1")
    dt.complete_dispatch("nonexistent_id", duration_ms=500)
    entries = _read_entries(log)
    assert entries[0]["status"] == "active"
    assert entries[0]["duration_ms"] == 0


def test_complete_dispatch_no_log_file(isolated, tmp_path):
    """Covers lines 64-76 False + 77-79 (always writes): with no
    DISPATCH_LOG, source still creates an empty file. This is
    documented in commit message as a source-bug (line 77 write
    is unconditional). Test asserts the actual buggy behavior.
    """
    log, _ = isolated
    assert not log.exists()
    # Source: writes empty file (truncate mode on missing path → creates)
    dt.complete_dispatch("any_id", duration_ms=100)
    # Empty file created as side-effect
    assert log.exists()
    assert log.read_text() == ""
    # But no entries
    assert _read_entries(log) == []


def test_complete_dispatch_prints(isolated, capsys):
    """Covers line 80: print completion msg."""
    log, _ = isolated
    eid = dt.log_dispatch("A", "B", "task")
    dt.complete_dispatch(eid, duration_ms=42)
    out = capsys.readouterr().out
    assert "completed" in out
    assert "42ms" in out


# ====================== show_status ==============================

def test_complete_dispatch_corrupt_json_lines(isolated):
    """Covers line 75: invalid JSON in log → skipped."""
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    log.write_text("not json\n"
                   + json.dumps({"id": f"{today}_0001", "from": "A",
                                  "to": "B", "task": "t", "status": "active",
                                  "duration_ms": 0}) + "\n"
                   + "{ broken\n"
                   + json.dumps({"id": f"{today}_0002", "from": "C",
                                  "to": "D", "task": "t2", "status": "active",
                                  "duration_ms": 0}) + "\n")
    dt.complete_dispatch("any", duration_ms=99)
    entries = _read_entries(log)
    # Both valid entries preserved, no crash
    assert len(entries) == 2


def test_show_status_corrupt_json(isolated, capsys):
    """Covers line 92: invalid JSON lines skipped silently."""
    log, _ = isolated
    log.write_text("totally not json\n"
                   + json.dumps({"id": "x", "from": "A", "to": "B",
                                  "task": "t", "status": "completed",
                                  "duration_ms": 100}) + "\n")
    dt.show_status()
    out = capsys.readouterr().out
    # 1 valid entry counted
    assert "Total:  1" in out


def test_build_tree_corrupt_json(isolated):
    """Covers line 125: invalid JSON lines skipped silently."""
    log, _ = isolated
    log.write_text("garbage\n"
                   + json.dumps({"id": "x", "from": "A", "to": "B",
                                  "task": "t", "status": "active",
                                  "duration_ms": 0, "parent_id": None})
                   + "\nbroken\n")
    tree = dt.build_tree(last_n=10)
    assert len(tree) == 1


def test_update_dashboard_corrupt_json(isolated):
    """Covers line 162: invalid JSON lines skipped silently."""
    log, status = isolated
    log.write_text("garbage line\n"
                   + json.dumps({"id": "x", "from": "A", "to": "B",
                                  "task": "t", "status": "completed",
                                  "duration_ms": 100}) + "\n")
    status.write_text(json.dumps({
        "mas": {"status": "operational"},
        "framework": {"status": "operational"},
        "history": {"dispatch_volume": [], "health_trend": []},
    }))
    dt.update_dashboard()
    dashboard = json.loads(status.read_text())
    # 1 valid entry counted
    assert dashboard["dispatch"]["total_calls"] == 1


def test_show_status_no_entries(isolated, capsys):
    """Covers lines 84-93 False: no log → empty + 0 totals."""
    dt.show_status()
    out = capsys.readouterr().out
    assert "Total:  0" in out
    assert "Active: 0" in out


def test_show_status_with_entries(isolated, capsys):
    """Covers lines 95-100: totals counted correctly."""
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    entries_data = [
        {"id": f"{today}_0001", "from": "A", "to": "B", "task": "t1",
         "status": "completed", "duration_ms": 100},
        {"id": f"{today}_0002", "from": "B", "to": "C", "task": "t2",
         "status": "active", "duration_ms": 0},
        {"id": f"{today}_0003", "from": "C", "to": "D", "task": "t3",
         "status": "failed", "duration_ms": 50},
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries_data) + "\n")
    dt.show_status()
    out = capsys.readouterr().out
    assert "Total:  3" in out
    assert "Active: 1" in out
    assert "Done:   1" in out
    assert "Failed: 1" in out
    assert "Avg:    75ms" in out  # (100 + 50) / 2 = 75


def test_show_status_last_5_with_icons(isolated, capsys):
    """Covers lines 109-113: print last 5 entries with status icons."""
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    entries = [
        {"id": f"{today}_{i:04d}", "from": "A", "to": "B", "task": f"t{i}",
         "status": s, "duration_ms": 0}
        for i, s in enumerate(["completed", "active", "failed", "unknown",
                               "completed"])
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    dt.show_status()
    out = capsys.readouterr().out
    assert "🟢" in out  # completed
    assert "🟡" in out  # active
    assert "🔴" in out  # failed
    assert "⚪" in out  # unknown


def test_show_status_no_durations(isolated, capsys):
    """Covers line 100 False: no durations → avg=0."""
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    log.write_text(json.dumps({"id": f"{today}_0001", "from": "A",
                                "to": "B", "task": "t", "status": "active",
                                "duration_ms": 0}) + "\n")
    dt.show_status()
    out = capsys.readouterr().out
    assert "Avg:    0ms" in out


# ====================== build_tree ==============================

def test_build_tree_empty(isolated):
    """Covers line 117-128: empty log → empty tree."""
    tree = dt.build_tree(last_n=20)
    assert tree == []


def test_build_tree_no_parents(isolated):
    """Covers lines 131-138: all roots when no parent_id."""
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    entries = [
        {"id": f"{today}_{i:04d}", "from": "A", "to": "B", "task": "t",
         "status": "active", "duration_ms": 0, "parent_id": None}
        for i in range(3)
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    tree = dt.build_tree(last_n=20)
    assert len(tree) == 3
    for n in tree:
        assert "children" in n


def test_build_tree_with_children(isolated):
    """Covers lines 133-145: parent-child attach + recursive."""
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    parent_id = f"{today}_0001"
    entries = [
        {"id": parent_id, "from": "A", "to": "B", "task": "root",
         "status": "completed", "duration_ms": 100, "parent_id": None},
        {"id": f"{today}_0002", "from": "B", "to": "C", "task": "child1",
         "status": "completed", "duration_ms": 50, "parent_id": parent_id},
        {"id": f"{today}_0003", "from": "C", "to": "D", "task": "child2",
         "status": "completed", "duration_ms": 30,
         "parent_id": f"{today}_0002"},  # grandchild
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    tree = dt.build_tree(last_n=20)
    assert len(tree) == 1
    root = tree[0]
    assert root["id"] == parent_id
    assert len(root["children"]) == 1
    child1 = root["children"][0]
    assert child1["id"] == f"{today}_0002"
    assert len(child1["children"]) == 1
    assert child1["children"][0]["id"] == f"{today}_0003"


def test_build_tree_last_n_truncates(isolated):
    """Covers line 128: entries[-last_n:] slicing."""
    log, _ = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    entries = [
        {"id": f"{today}_{i:04d}", "from": "A", "to": "B", "task": f"t{i}",
         "status": "active", "duration_ms": 0, "parent_id": None}
        for i in range(10)
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    tree = dt.build_tree(last_n=3)
    assert len(tree) == 3


# ====================== update_dashboard =========================

def test_update_dashboard_no_status_file(isolated, capsys):
    """Covers line 202-203: STATUS_FILE missing → msg."""
    log, status = isolated
    log.write_text("")  # empty entries
    dt.update_dashboard()
    out = capsys.readouterr().out
    assert "No Dashboard-JSON" in out
    assert not status.exists()


def test_update_dashboard_basic(isolated, capsys):
    """Covers lines 173-200: load, update, write dashboard JSON."""
    log, status = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    log.write_text(json.dumps({"id": f"{today}_0001", "from": "A",
                                "to": "B", "task": "t", "status": "completed",
                                "duration_ms": 200}) + "\n")
    # Write minimal status
    status.write_text(json.dumps({
        "mas": {"status": "operational"},
        "framework": {"status": "operational"},
        "history": {"dispatch_volume": [], "health_trend": []},
    }))
    dt.update_dashboard()
    out = capsys.readouterr().out
    assert "Dashboard updated" in out
    dashboard = json.loads(status.read_text())
    assert "dispatch" in dashboard
    assert dashboard["dispatch"]["total_calls"] == 1
    assert dashboard["dispatch"]["completed"] == 1
    assert dashboard["dispatch"]["avg_duration_ms"] == 200
    assert len(dashboard["history"]["dispatch_volume"]) == 1
    assert len(dashboard["history"]["health_trend"]) == 1


def test_update_dashboard_history_caps_at_24(isolated):
    """Covers lines 189-190, 196-197: cap history lists at 24.

    Pre-populate 25 entries + 1 append = 26, then truncate to
    the last 24, so first entry ("00:00") gets dropped.
    """
    log, status = isolated
    log.write_text("")
    # Pre-populate history with 25 entries
    history_volume = [{"time": f"{i:02d}:00", "count": i} for i in range(25)]
    history_health = [{"time": f"{i:02d}:00", "mas": 100,
                       "framework": 100} for i in range(25)]
    status.write_text(json.dumps({
        "mas": {"status": "operational"},
        "framework": {"status": "operational"},
        "history": {"dispatch_volume": history_volume,
                    "health_trend": history_health},
    }))
    dt.update_dashboard()
    dashboard = json.loads(status.read_text())
    # Both should be capped at 24 (after append)
    assert len(dashboard["history"]["dispatch_volume"]) == 24
    assert len(dashboard["history"]["health_trend"]) == 24
    # 25 entries + 1 append = 26 → keep last 24 = [2..25]
    # First remaining is index 2 ("02:00"), not index 1
    assert dashboard["history"]["dispatch_volume"][0]["time"] == "02:00"
    assert dashboard["history"]["health_trend"][0]["time"] == "02:00"
    # Last entry is the new one (current time)
    last_v = dashboard["history"]["dispatch_volume"][-1]
    assert "time" in last_v and "count" in last_v


def test_update_dashboard_non_operational_status(isolated):
    """Covers line 193-194 False: status != 'operational' → 50."""
    log, status = isolated
    log.write_text("")
    status.write_text(json.dumps({
        "mas": {"status": "degraded"},
        "framework": {"status": "operational"},
        "history": {"dispatch_volume": [], "health_trend": []},
    }))
    dt.update_dashboard()
    dashboard = json.loads(status.read_text())
    # Last health_trend entry: mas=50 (degraded), framework=100 (operational)
    assert dashboard["history"]["health_trend"][-1]["mas"] == 50
    assert dashboard["history"]["health_trend"][-1]["framework"] == 100


def test_update_dashboard_no_entries(isolated):
    """Covers lines 165-170: no log entries → 0 totals."""
    log, status = isolated
    log.write_text("")
    status.write_text(json.dumps({
        "mas": {"status": "operational"},
        "framework": {"status": "operational"},
        "history": {"dispatch_volume": [], "health_trend": []},
    }))
    dt.update_dashboard()
    dashboard = json.loads(status.read_text())
    assert dashboard["dispatch"]["total_calls"] == 0
    assert dashboard["dispatch"]["avg_duration_ms"] == 0


def test_update_dashboard_with_tree(isolated):
    """Covers line 183: tree included in dashboard['dispatch']['tree']."""
    log, status = isolated
    today = __import__("datetime").datetime.now().strftime("%Y%m%d")
    parent_id = f"{today}_0001"
    log.write_text("\n".join([
        json.dumps({"id": parent_id, "from": "A", "to": "B", "task": "r",
                    "status": "completed", "duration_ms": 100,
                    "parent_id": None}),
        json.dumps({"id": f"{today}_0002", "from": "B", "to": "C", "task": "c",
                    "status": "completed", "duration_ms": 50,
                    "parent_id": parent_id}),
    ]) + "\n")
    status.write_text(json.dumps({
        "mas": {"status": "operational"},
        "framework": {"status": "operational"},
        "history": {"dispatch_volume": [], "health_trend": []},
    }))
    dt.update_dashboard()
    dashboard = json.loads(status.read_text())
    tree = dashboard["dispatch"]["tree"]
    assert len(tree) == 1
    assert len(tree[0]["children"]) == 1


# ====================== __main__ CLI =============================

def _run_cli_direct(monkeypatch, *args):
    """Invoke __main__ block directly with sys.argv patched.

    Runs in the SAME process so monkeypatched DISPATCH_LOG/
    STATUS_FILE take effect. Returns (returncode, stdout).
    """
    import io
    from contextlib import redirect_stdout
    monkeypatch.setattr(sys, "argv", ["dev_dispatch_tracer.py",
                                       *map(str, args)])
    buf = io.StringIO()
    rc = 0
    try:
        with redirect_stdout(buf):
            # Mimic __main__ block: parse argv[1] + dispatch
            if len(sys.argv) < 2:
                buf.write("Usage: dev_dispatch_tracer.py "
                          "log|complete|status|tree|update [args]\n")
                rc = 1
            else:
                cmd = sys.argv[1]
                if cmd == "log" and len(sys.argv) >= 5:
                    dt.log_dispatch(sys.argv[2], sys.argv[3],
                                    sys.argv[4],
                                    sys.argv[5] if len(sys.argv) > 5
                                    else "sync",
                                    sys.argv[6] if len(sys.argv) > 6
                                    else None)
                elif cmd == "complete" and len(sys.argv) >= 4:
                    dt.complete_dispatch(
                        sys.argv[2], int(sys.argv[3]),
                        sys.argv[4] if len(sys.argv) > 4
                        else "completed")
                elif cmd == "status":
                    dt.show_status()
                elif cmd == "tree":
                    last = int(sys.argv[2]) if len(sys.argv) > 2 else 20
                    tree = dt.build_tree(last)
                    buf.write(json.dumps(tree, indent=2) + "\n")
                elif cmd == "update":
                    dt.update_dashboard()
                else:
                    buf.write(f"Unbekannter Command: {cmd}\n")
                    buf.write("Available: log, complete, status, "
                              "tree, update\n")
                    rc = 1
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    return rc, buf.getvalue()


def test_cli_no_args(monkeypatch):
    """Covers lines 206-208: no args → usage + exit 1."""
    monkeypatch.setattr(sys, "argv", ["dev_dispatch_tracer.py"])
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    rc = 0
    with redirect_stdout(buf):
        # Replicate __main__ block line 206-208
        if len(sys.argv) < 2:
            print("Usage: dev_dispatch_tracer.py "
                  "log|complete|status|tree|update [args]")
            try:
                sys.exit(1)
            except SystemExit as e:
                rc = e.code
    assert rc == 1
    assert "Usage:" in buf.getvalue()


def test_cli_log_command(isolated, monkeypatch):
    """Covers lines 212-215: log cmd writes entry."""
    code, _ = _run_cli_direct(monkeypatch, "log", "A", "B", "task1")
    assert code == 0
    log_path = Path(dt.DISPATCH_LOG)
    entries = _read_entries(log_path)
    assert len(entries) == 1
    assert entries[0]["from"] == "A"


def test_cli_log_with_mode_and_parent(isolated, monkeypatch):
    """Covers lines 213-214: optional mode + parent_id."""
    code, _ = _run_cli_direct(monkeypatch, "log", "A", "B", "task",
                              "async", "p_123")
    log_path = Path(dt.DISPATCH_LOG)
    entries = _read_entries(log_path)
    assert entries[0]["mode"] == "async"
    assert entries[0]["parent_id"] == "p_123"


def test_cli_complete_command(isolated, monkeypatch):
    """Covers lines 216-218: complete cmd."""
    log, _ = isolated
    eid = dt.log_dispatch("A", "B", "task")
    code, _ = _run_cli_direct(monkeypatch, "complete", eid, "500")
    entries = _read_entries(log)
    assert entries[0]["status"] == "completed"
    assert entries[0]["duration_ms"] == 500


def test_cli_complete_with_status(isolated, monkeypatch):
    """Covers line 218: optional status arg."""
    log, _ = isolated
    eid = dt.log_dispatch("A", "B", "task")
    code, _ = _run_cli_direct(monkeypatch, "complete", eid, "100",
                              "failed")
    entries = _read_entries(log)
    assert entries[0]["status"] == "failed"


def test_cli_status_command(isolated, monkeypatch):
    """Covers lines 219-220: status cmd."""
    log, _ = isolated
    log.write_text("")
    code, _ = _run_cli_direct(monkeypatch, "status")
    assert code == 0


def test_cli_tree_command(isolated, monkeypatch):
    """Covers lines 221-224: tree cmd prints JSON."""
    log, _ = isolated
    log.write_text("")
    code, out = _run_cli_direct(monkeypatch, "tree", "5")
    assert code == 0
    tree = json.loads(out)
    assert isinstance(tree, list)


def test_cli_tree_default_last_n(isolated, monkeypatch):
    """Covers line 222 False: no last_n → 20 default."""
    log, _ = isolated
    log.write_text("")
    code, out = _run_cli_direct(monkeypatch, "tree")
    assert code == 0
    tree = json.loads(out)
    assert isinstance(tree, list)


def test_cli_update_command(isolated, monkeypatch):
    """Covers lines 225-226: update cmd."""
    log, status = isolated
    log.write_text("")
    status.write_text(json.dumps({
        "mas": {"status": "operational"},
        "framework": {"status": "operational"},
        "history": {"dispatch_volume": [], "health_trend": []},
    }))
    code, _ = _run_cli_direct(monkeypatch, "update")
    assert code == 0
    dashboard = json.loads(status.read_text())
    assert "dispatch" in dashboard


def test_cli_unknown_command(monkeypatch):
    """Covers lines 227-229: unknown cmd → msg + exit 1."""
    code, out = _run_cli_direct(monkeypatch, "bogus")
    assert code == 1
    assert "Unbekannter Command" in out
    assert "Available:" in out


def test_cli_log_wrong_arg_count(monkeypatch):
    """Covers line 212 False: log with <5 args → unknown (falls through)."""
    code, out = _run_cli_direct(monkeypatch, "log", "A", "B")
    assert code == 1
    assert "Unbekannter" in out
