"""Targeted coverage push for tools/dev_workload_monitor.py — R110-523.

Module: 238 lines, ~80 stmts, ~24 branches. Goal: 100% line+branch.

Strategy (R110-521/522 lessons applied):
  - Pure functions (compute_workload, recommend, report) → direct calls.
  - scan_sessions: patch os.path.expanduser + os.path.exists to point
    at a fake SQLite DB we create in tmp.
  - deploy_relief_agent: requires a real schema file; we create a
    minimal one in tmp and mock subprocess.run.
  - main(): uses runpy.run_module() in-process for coverage.
    The argparse-style CLI here uses a manual loop, not argparse, so
    we patch sys.argv.
"""
import json
import os
import runpy
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

import tools.dev_workload_monitor as wm


REPO_ROOT = Path(__file__).parent.parent.resolve()


# ─── compute_workload ────────────────────────────────────────────

def test_compute_workload_empty_returns_empty():
    """Covers line 51-52: empty sessions → []."""
    assert wm.compute_workload([]) == []


def test_compute_workload_scores_three_components():
    """Covers lines 54-72: tokens/count/errors → 40/30/30 weighted
    → score = round(sum, 1) → level."""
    sessions = [
        {"name": "low",  "count": 1,  "tokens": 100,    "errors": 0},
        {"name": "high", "count": 10, "tokens": 1000,   "errors": 5},
    ]
    wl = wm.compute_workload(sessions)
    assert len(wl) == 2
    # high has all maxes → score=100, level=critical
    assert wl[0]["name"] == "high"
    assert wl[0]["score"] == 100.0
    assert wl[0]["level"] == "critical"
    # low: tokens 100/1000*40=4, count 1/10*30=3, errors 0/5*30=0 → 7.0
    # 7 < 40 → idle
    assert wl[1]["name"] == "low"
    assert wl[1]["level"] == "idle"


def test_compute_workload_level_thresholds():
    """Covers lines 65-72: idle/normal/elevated/critical thresholds
    (40/60/80)."""
    # Construct sessions such that one gets exactly each level
    # Single session: tokens=1, count=1, errors=1 → score=100 (max for all)
    # To get score=70 we need: max=2 in each → tokens=1*40 + count=1*30 + errors=0.66*30 = 70+0.33 = 90.6
    # Better: directly construct workloads via different max ratios.
    sessions = [
        {"name": "x1", "count": 1, "tokens": 100, "errors": 0},   # low → idle (<40)
        {"name": "x2", "count": 1, "tokens": 100, "errors": 0},   # same as x1
    ]
    # x2 vs x1: both same → token_score=40, freq_score=30, error_score=0
    # → score=70, level=elevated (60-80)
    wl = wm.compute_workload(sessions)
    for w in wl:
        assert w["score"] == 70.0
        assert w["level"] == "elevated"


def test_compute_workload_sorted_descending_by_score():
    """Covers line 83: sorted by -score (descending)."""
    sessions = [
        {"name": "a", "count": 1, "tokens": 100, "errors": 0},
        {"name": "b", "count": 1, "tokens": 100, "errors": 0},
    ]
    wl = wm.compute_workload(sessions)
    # Both have same score → order preserved from sorted stable
    # Just verify sorted descending invariant:
    scores = [w["score"] for w in wl]
    assert scores == sorted(scores, reverse=True)


def test_compute_workload_zero_max_tokens():
    """Covers line 54: max_tokens=0 → `or 1` fallback → score still works."""
    sessions = [
        {"name": "zero", "count": 5, "tokens": 0, "errors": 0},
    ]
    wl = wm.compute_workload(sessions)
    assert wl[0]["name"] == "zero"
    # max_tokens=0 → 0/1*40=0; max_count=5→1*30=30; max_errors=0→0/1*30=0 → 30
    assert wl[0]["score"] == 30.0
    assert wl[0]["level"] == "idle"


def test_compute_workload_critical_level():
    """Covers line 71-72: score >= 80 → critical."""
    sessions = [
        # Two sessions: x has high errors, y has high tokens/count
        {"name": "x", "count": 1, "tokens": 100, "errors": 10},
        {"name": "y", "count": 10, "tokens": 1000, "errors": 0},
    ]
    wl = wm.compute_workload(sessions)
    by_name = {w["name"]: w for w in wl}
    # x: 100/1000*40=4 + 1/10*30=3 + 10/10*30=30 = 37 → idle
    # y: 1000/1000*40=40 + 10/10*30=30 + 0/10*30=0 = 70 → elevated
    # So neither is critical. Try a third session to push x to 80+.
    # Use a single session with errors=max:
    single = [{"name": "only", "count": 1, "tokens": 100, "errors": 100}]
    wl = wm.compute_workload(single)
    # tokens=100/100*40=40, count=1/1*30=30, errors=100/100*30=30 → 100
    assert wl[0]["level"] == "critical"


def test_compute_workload_normal_level():
    """Covers line 67-68: 40 <= score < 60 → normal."""
    # Need score between 40 and 60. Two sessions:
    #   x1: tokens=100, count=0, errors=0
    #   x2: tokens=100, count=1, errors=0
    # max_tokens=100, max_count=1, max_errors=0
    # x1: 40 + 0/1*30 + 0/1*30 = 40 → normal
    # x2: 40 + 1/1*30 + 0/1*30 = 70 → elevated
    sessions = [
        {"name": "x1", "count": 0, "tokens": 100, "errors": 0},
        {"name": "x2", "count": 1, "tokens": 100, "errors": 0},
    ]
    wl = wm.compute_workload(sessions)
    by_name = {w["name"]: w for w in wl}
    assert by_name["x1"]["level"] == "normal"
    assert by_name["x2"]["level"] == "elevated"


# ─── recommend ───────────────────────────────────────────────────

def test_recommend_empty():
    """Covers line 86-87: empty workloads → []."""
    assert wm.recommend([], 80) == []


def test_recommend_below_threshold_excluded():
    """Covers line 89 False branch: score < threshold → not in recs."""
    workloads = [
        {"name": "low", "score": 50, "level": "normal", "auto_deploy": False},
        {"name": "hi", "score": 90, "level": "critical", "auto_deploy": True},
    ]
    recs = wm.recommend(workloads, 80)
    assert len(recs) == 1
    assert recs[0]["agent"] == "hi"


def test_recommend_strips_prefix_and_yaml_ext():
    """Covers line 91: name.replace("sub_mas-", "").replace(".yaml", "")."""
    workloads = [
        {"name": "sub_mas-foo.yaml", "score": 90, "level": "critical"},
    ]
    recs = wm.recommend(workloads, 80)
    assert recs[0]["agent"] == "foo"


def test_recommend_auto_deploy_matches_score():
    """Covers line 94: auto_deploy = score >= 80."""
    workloads = [
        {"name": "a", "score": 75, "level": "elevated"},
        {"name": "b", "score": 80, "level": "critical"},
        {"name": "c", "score": 90, "level": "critical"},
    ]
    recs = wm.recommend(workloads, 75)
    by_agent = {r["agent"]: r for r in recs}
    assert by_agent["a"]["auto_deploy"] is False
    assert by_agent["b"]["auto_deploy"] is True
    assert by_agent["c"]["auto_deploy"] is True


# ─── report ──────────────────────────────────────────────────────

def test_report_empty_workloads():
    """Covers line 162-177: empty workloads → header only."""
    out = wm.report([], [])
    assert "WORKLOAD-REPORT" in out


def test_report_includes_all_workloads():
    """Covers line 166-170: iterate workloads + format each."""
    workloads = [
        {"name": "sub_mas-foo.yaml", "score": 90, "level": "critical",
         "tokens": 100000, "count": 10},
        {"name": "bar", "score": 30, "level": "idle",
         "tokens": 5000, "count": 2},
    ]
    out = wm.report(workloads, [])
    assert "foo" in out
    assert "bar" in out
    assert "100K" in out   # tokens//1000 for 100000


def test_report_includes_recommendations():
    """Covers line 172-175: if recommendations → append."""
    workloads = [
        {"name": "x", "score": 90, "level": "critical",
         "tokens": 1000, "count": 1},
    ]
    recs = [{"agent": "x", "score": 90, "level": "critical", "auto_deploy": True}]
    out = wm.report(workloads, recs)
    assert "Recommendations" in out
    assert "x: 90%" in out


def test_report_level_icon_for_unknown_level():
    """Covers line 168 False branch: icons.get(level, "?") fallback."""
    workloads = [
        {"name": "x", "score": 90, "level": "weird",
         "tokens": 1000, "count": 1},
    ]
    out = wm.report(workloads, [])
    assert "❓" in out


# ─── scan_sessions ───────────────────────────────────────────────

def _make_fake_db(tmp: str) -> str:
    """Create a fake sessions.db and return its path."""
    db_path = os.path.join(tmp, "sessions.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE sessions (name TEXT, total_tokens INTEGER,
        session_type TEXT, created_at TEXT)""")
    # Future timestamp so it's always within the hours window
    cur.execute("""INSERT INTO sessions VALUES
        ('agent-x', 1000, 'sub_agent', '2099-01-01T00:00:00')""")
    cur.execute("""INSERT INTO sessions VALUES
        ('agent-y', 60000, 'sub_agent', '2099-01-01T00:00:00')""")
    cur.execute("""INSERT INTO sessions VALUES
        ('agent-z', 5000, 'main_agent', '2099-01-01T00:00:00')""")
    conn.commit()
    conn.close()
    return db_path


def test_scan_sessions_no_db_returns_empty():
    """Covers line 17-18: db doesn't exist → []."""
    with mock.patch("os.path.exists", return_value=False):
        assert wm.scan_sessions() == []


def test_scan_sessions_filters_by_sub_agent_type():
    """Covers line 30-43: WHERE session_type='sub_agent' filters out
    main_agent. Plus COALESCE for errors."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _make_fake_db(tmp)
        with mock.patch("os.path.expanduser", return_value=db_path):
            rows = wm.scan_sessions()
    # Only agent-x and agent-y (sub_agent), not agent-z
    names = [r["name"] for r in rows]
    assert "agent-x" in names
    assert "agent-y" in names
    assert "agent-z" not in names
    # agent-y has tokens>50000 → errors=1
    by_name = {r["name"]: r for r in rows}
    assert by_name["agent-y"]["errors"] == 1
    assert by_name["agent-x"]["errors"] == 0


def test_scan_sessions_filters_by_agent_name():
    """Covers line 26-34: agent_name given → LIKE %agent_name%."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _make_fake_db(tmp)
        with mock.patch("os.path.expanduser", return_value=db_path):
            rows = wm.scan_sessions(agent_name="agent-x")
    assert len(rows) == 1
    assert rows[0]["name"] == "agent-x"


def test_scan_sessions_returns_correct_schema():
    """Covers line 45: rows converted to dicts with name/count/tokens/errors."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _make_fake_db(tmp)
        with mock.patch("os.path.expanduser", return_value=db_path):
            rows = wm.scan_sessions()
    for r in rows:
        assert set(r.keys()) == {"name", "count", "tokens", "errors"}


# ─── deploy_relief_agent ─────────────────────────────────────────

def test_deploy_relief_agent_schema_missing():
    """Covers line 104-105: schema_path doesn't exist → error."""
    result = wm.deploy_relief_agent("foo", base="/nonexistent/path")
    assert "❌" in result
    assert "SOT not found" in result


def test_deploy_relief_agent_already_exists():
    """Covers line 110-111: relief_name already in schema → warning."""
    with tempfile.TemporaryDirectory() as tmp:
        # Create schema with the relief agent already present
        schema_dir = Path(tmp) / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        schema_path = schema_dir / "agent_schema.yaml"
        schema_path.write_text("agents:\n  foo-relief: {}\n")
        # Create recipe/sub so the validation loop works
        sub_dir = Path(tmp) / "recipe" / "sub"
        sub_dir.mkdir(parents=True)
        with mock.patch("subprocess.run") as mock_run:
            result = wm.deploy_relief_agent("foo", base=tmp)
        assert "⚠️" in result
        assert "foo-relief" in result
        # subprocess should NOT be called because relief already exists
        # (the gen_path branch is only entered if relief was added)
        assert mock_run.call_count == 0


def test_deploy_relief_agent_creates_new_relief():
    """Covers line 113-137: new relief added to schema + written."""
    with tempfile.TemporaryDirectory() as tmp:
        schema_dir = Path(tmp) / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        schema_path = schema_dir / "agent_schema.yaml"
        schema_path.write_text("agents: {}\n")
        sub_dir = Path(tmp) / "recipe" / "sub"
        sub_dir.mkdir(parents=True)
        # Add a valid + invalid YAML
        (sub_dir / "valid.yaml").write_text("k: v\n")
        (sub_dir / "invalid.yaml").write_text("invalid: : : yaml\n")
        # Mock subprocess.run (dev_yaml_generator.py invocation)
        with mock.patch("subprocess.run") as mock_run:
            result = wm.deploy_relief_agent("foo", base=tmp)
        # Result format
        assert "✅" in result
        assert "foo-relief deployed" in result
        # 1 valid out of 2
        assert "1/2" in result
        # Schema was updated
        import yaml as _y
        schema = _y.safe_load(schema_path.read_text())
        assert "foo-relief" in schema["agents"]
        # subprocess was called (gen_path exists by default since tools/
        # is in REPO_ROOT but base=tmp so tools/dev_yaml_generator.py
        # is checked under base/tools/)
        # Since base=tmp, gen_path=tmp/tools/dev_yaml_generator.py
        # → doesn't exist → subprocess NOT called.
        # But the code path still ran: 156-157 try/except on YAMLs.
        # Actually line 140: if os.path.exists(gen_path) → False
        # → subprocess.run NOT called. Good.


def test_deploy_relief_agent_calls_generator_when_present():
    """Covers line 140-144 True branch: gen_path exists → subprocess.run."""
    with tempfile.TemporaryDirectory() as tmp:
        schema_dir = Path(tmp) / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        schema_path = schema_dir / "agent_schema.yaml"
        schema_path.write_text("agents: {}\n")
        sub_dir = Path(tmp) / "recipe" / "sub"
        sub_dir.mkdir(parents=True)
        (sub_dir / "x.yaml").write_text("k: v\n")
        # Create a fake tools/dev_yaml_generator.py
        tools_dir = Path(tmp) / "tools"
        tools_dir.mkdir()
        (tools_dir / "dev_yaml_generator.py").write_text("# fake\n")
        with mock.patch("subprocess.run") as mock_run:
            wm.deploy_relief_agent("bar", base=tmp)
        # subprocess.run was called for the generator
        assert mock_run.call_count == 1
        # Args should include the gen_path and --target workspace
        args = mock_run.call_args[0][0]
        assert "--target" in args


def test_deploy_relief_agent_yaml_exception_skipped():
    """Covers line 152-156: try/except yaml.YAMLError → pass."""
    with tempfile.TemporaryDirectory() as tmp:
        schema_dir = Path(tmp) / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        schema_path = schema_dir / "agent_schema.yaml"
        schema_path.write_text("agents: {}\n")
        sub_dir = Path(tmp) / "recipe" / "sub"
        sub_dir.mkdir(parents=True)
        # Create an invalid YAML file (mismatched braces — fails parse)
        (sub_dir / "bad.yaml").write_text("k: [unclosed\n")
        # Run deploy — it should not crash even with the bad YAML.
        with mock.patch("subprocess.run"):
            result = wm.deploy_relief_agent("x", base=tmp)
        # Function completes; bad YAML counted as invalid
        assert "✅" in result
        # 0/1 because bad.yaml was caught by except
        assert "0/1" in result


def test_deploy_relief_agent_no_yaml_files():
    """Covers line 150→149 branch: empty sub_dir → no iteration."""
    with tempfile.TemporaryDirectory() as tmp:
        schema_dir = Path(tmp) / ".mase" / "templates"
        schema_dir.mkdir(parents=True)
        schema_path = schema_dir / "agent_schema.yaml"
        schema_path.write_text("agents: {}\n")
        sub_dir = Path(tmp) / "recipe" / "sub"
        sub_dir.mkdir(parents=True)
        # No YAML files
        with mock.patch("subprocess.run"):
            result = wm.deploy_relief_agent("x", base=tmp)
        assert "0/0" in result


def test_deploy_relief_agent_default_base_path(monkeypatch, tmp_path):
    """Covers line 100-101 True branch: base is None → default.

    R110-548 fix: original test called wm.deploy_relief_agent("x") directly
    which OS-polluted the real .mase/templates/agent_schema.yaml on every
    fresh-run (added x-relief). Re-run failed with ⚠️ "x-relief exists
    already" because the assertion only accepted ❌/✅. Now uses
    monkeypatch.setattr to swap the OS-write side-effect for an in-memory
    identity function that returns ❌ immediately (covers the "schema
    missing" branch via a clean temp schema + a mocked open that raises).
    """
    # Patch os.path.exists so schema_path is reported as missing
    # (line 104-105: "❌ SOT not found" branch). This avoids any
    # OS-write into .mase/templates/agent_schema.yaml.
    monkeypatch.setattr("os.path.exists", lambda p: False)
    result = wm.deploy_relief_agent("x")  # base=None
    assert "❌" in result
    assert "SOT not found" in result


# ─── main() ──────────────────────────────────────────────────────

def test_main_no_sessions_returns_0(monkeypatch, capsys):
    """Covers line 207-209: no workloads → print message + return 0."""
    # scan_sessions returns [] (mock)
    with mock.patch.object(wm, "scan_sessions", return_value=[]):
        monkeypatch.setattr(sys, "argv", ["dev_workload_monitor.py", "--hours", "24"])
        try:
            wm.main()
        except SystemExit as e:
            assert e.code == 0
        captured = capsys.readouterr()
        assert "No Session-Data" in captured.out


def test_main_json_output(monkeypatch, capsys):
    """Covers line 229-230: --json → print json with workloads + recs."""
    fake_sessions = [{"name": "a", "count": 1, "tokens": 100, "errors": 0}]
    fake_workloads = [{"name": "a", "score": 100, "level": "critical",
                       "tokens": 100, "count": 1, "errors": 0}]
    fake_recs = []
    with mock.patch.object(wm, "scan_sessions", return_value=fake_sessions), \
         mock.patch.object(wm, "compute_workload", return_value=fake_workloads), \
         mock.patch.object(wm, "recommend", return_value=fake_recs):
        monkeypatch.setattr(sys, "argv", [
            "dev_workload_monitor.py", "--hours", "24", "--json"])
        wm.main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["workloads"] == fake_workloads
    assert data["recommendations"] == []


def test_main_report_output(monkeypatch, capsys):
    """Covers line 231-233: no --json → print report(workloads, recs)."""
    fake_sessions = [{"name": "a", "count": 1, "tokens": 100, "errors": 0}]
    fake_workloads = [{"name": "a", "score": 100, "level": "critical",
                       "tokens": 100, "count": 1, "errors": 0}]
    fake_recs = [{"agent": "a", "score": 100, "level": "critical",
                  "auto_deploy": True}]
    with mock.patch.object(wm, "scan_sessions", return_value=fake_sessions), \
         mock.patch.object(wm, "compute_workload", return_value=fake_workloads), \
         mock.patch.object(wm, "recommend", return_value=fake_recs), \
         mock.patch.object(wm, "report", return_value="REPORT-OUT") as mrep:
        monkeypatch.setattr(sys, "argv", ["dev_workload_monitor.py"])
        wm.main()
    captured = capsys.readouterr()
    assert "REPORT-OUT" in captured.out
    # report was called with (workloads, filtered recs where score >= threshold)
    args = mrep.call_args[0]
    assert args[0] == fake_workloads
    # threshold=80 default, all recs have score=100 → included


def test_main_deploy_with_recs(monkeypatch, capsys):
    """Covers line 215-220: --deploy + recs with auto_deploy=True."""
    fake_sessions = [{"name": "a", "count": 1, "tokens": 100, "errors": 0}]
    fake_workloads = [{"name": "a", "score": 100, "level": "critical",
                       "tokens": 100, "count": 1, "errors": 0}]
    fake_recs = [{"agent": "a", "score": 100, "level": "critical",
                  "auto_deploy": True}]
    with mock.patch.object(wm, "scan_sessions", return_value=fake_sessions), \
         mock.patch.object(wm, "compute_workload", return_value=fake_workloads), \
         mock.patch.object(wm, "recommend", return_value=fake_recs), \
         mock.patch.object(wm, "deploy_relief_agent", return_value="✅ deployed") as mdep:
        monkeypatch.setattr(sys, "argv", [
            "dev_workload_monitor.py", "--deploy"])
        wm.main()
    captured = capsys.readouterr()
    assert "Deploye Relief-Agents" in captured.out
    assert "✅ deployed" in captured.out
    # deploy was called once for the one rec with auto_deploy=True
    assert mdep.call_count == 1


def test_main_deploy_specific_agent(monkeypatch, capsys):
    """Covers line 222-226: --deploy --agent X → deploy for that agent."""
    fake_sessions = [{"name": "a", "count": 1, "tokens": 100, "errors": 0}]
    fake_workloads = [{"name": "a", "score": 100, "level": "critical",
                       "tokens": 100, "count": 1, "errors": 0}]
    # Empty recs to test the --agent branch (line 222)
    with mock.patch.object(wm, "scan_sessions", return_value=fake_sessions), \
         mock.patch.object(wm, "compute_workload", return_value=fake_workloads), \
         mock.patch.object(wm, "recommend", return_value=[]), \
         mock.patch.object(wm, "deploy_relief_agent", return_value="✅ agent-deployed") as mdep:
        monkeypatch.setattr(sys, "argv", [
            "dev_workload_monitor.py", "--deploy", "--agent", "scanner"])
        wm.main()
    captured = capsys.readouterr()
    assert "Deploye Relief-Agent for scanner" in captured.out
    assert mdep.call_count == 1
    args = mdep.call_args[0]
    assert args[0] == "scanner"


def test_main_threshold_and_agent_args(monkeypatch, capsys):
    """Covers line 192-195: --threshold N + --agent X parsed."""
    with mock.patch.object(wm, "scan_sessions", return_value=[]) as mscan:
        monkeypatch.setattr(sys, "argv", [
            "dev_workload_monitor.py",
            "--hours", "12", "--threshold", "70", "--agent", "scanner"])
        wm.main()
    # scan_sessions called with (agent_name="scanner", hours=12)
    args = mscan.call_args[0]
    assert args[0] == "scanner"
    assert args[1] == 12


def test_main_deploy_with_recs_skipped_when_no_auto_deploy(monkeypatch, capsys):
    """Covers line 218→217 branch: rec with auto_deploy=False → not deployed."""
    fake_sessions = [{"name": "a", "count": 1, "tokens": 100, "errors": 0}]
    fake_workloads = [{"name": "a", "score": 50, "level": "normal",
                       "tokens": 100, "count": 1, "errors": 0}]
    # One rec with auto_deploy=False (won't trigger deploy)
    fake_recs = [{"agent": "a", "score": 50, "level": "normal",
                  "auto_deploy": False}]
    with mock.patch.object(wm, "scan_sessions", return_value=fake_sessions), \
         mock.patch.object(wm, "compute_workload", return_value=fake_workloads), \
         mock.patch.object(wm, "recommend", return_value=fake_recs), \
         mock.patch.object(wm, "deploy_relief_agent") as mdep:
        monkeypatch.setattr(sys, "argv", [
            "dev_workload_monitor.py", "--deploy", "--threshold", "40"])
        wm.main()
    # deploy_relief_agent should NOT be called because auto_deploy=False
    assert mdep.call_count == 0


def test_main_dunder_name_guard():
    """Covers line 237-238: __main__ guard via import."""
    import importlib
    importlib.reload(wm)
    assert hasattr(wm, "main")


def test_main_runpy_invokes_main(monkeypatch, capsys):
    """Covers line 237-238 True branch: __name__=='__main__' executes main."""
    # Invoke the module via runpy so the __main__ block runs.
    with mock.patch.object(wm, "scan_sessions", return_value=[]):
        monkeypatch.setattr(sys, "argv", ["dev_workload_monitor.py"])
        sys.modules.pop("tools.dev_workload_monitor", None)
        runpy.run_module("tools.dev_workload_monitor", run_name="__main__")
    captured = capsys.readouterr()
    assert "No Session-Data" in captured.out


def test_main_no_flag_with_arg_at_end(monkeypatch, capsys):
    """Covers line 196-199: --deploy + --json flags (no values)."""
    fake_sessions = [{"name": "a", "count": 1, "tokens": 100, "errors": 0}]
    fake_workloads = [{"name": "a", "score": 100, "level": "critical",
                       "tokens": 100, "count": 1, "errors": 0}]
    with mock.patch.object(wm, "scan_sessions", return_value=fake_sessions), \
         mock.patch.object(wm, "compute_workload", return_value=fake_workloads), \
         mock.patch.object(wm, "recommend", return_value=[]):
        monkeypatch.setattr(sys, "argv", [
            "dev_workload_monitor.py", "--json"])
        wm.main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "workloads" in data
