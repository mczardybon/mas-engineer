"""R110-534 coverage tests for tools/dev_update_schedule.py.

Module: 91 LOC, 1 main function + CLI wrapper, 0% covered.

Function tested:
  - update_schedule(workspace, findings_count, duration_sec)  lines 16-83

CLI:
  - line 87-90: argcount check, exit 1
  - line 91: call update_schedule (not exercised if we mock)

Strategy: Direct function calls. Use tmp_path for workspace fixture.
All paths need a workspace dir with `mas-engineer/.mase/schedule.yaml`
(bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml").

Key paths to cover:
  - Line 21-23: open existing yaml
  - Line 24-30: FileNotFoundError → default dict
  - Line 23: yaml.safe_load returns None → or {}
  - Line 33-38: append round entry
  - Line 41: truncate to last 10
  - Line 49: n > 1 → compute avg_interval_min
  - Line 52-53: handles datetime OR str via fromisoformat
  - Line 57-59: avg_duration_sec, avg_findings_per_round, rounds_without_findings
  - Line 62-72: recommendation logic (0 findings, <5, >=5)
  - Line 74-75: last_updated, version
  - Line 77: makedirs(parents=True, exist_ok=True)
  - Line 78-79: yaml.dump
  - Line 81-83: print output
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import yaml
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.dev_update_schedule as us  # noqa: E402


# ====================== helpers ==================================

def _make_workspace(tmp_path, *, existing_schedule=None, missing=False):
    """Build a tmp workspace mimicking expected layout:
        workspace/mas-engineer/.mase/schedule.yaml
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()
    me = workspace / "mas-engineer"
    mase = me / ".mase"
    mase.mkdir(parents=True)
    if existing_schedule is not None and not missing:
        (mase / "schedule.yaml").write_text(yaml.dump(existing_schedule))
    return workspace


def _read_schedule(workspace):
    p = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
    return yaml.safe_load(open(p))


# ====================== update_schedule ==========================

def test_update_schedule_no_existing_file(tmp_path, capsys):
    """Covers lines 24-30: FileNotFoundError → default dict."""
    workspace = _make_workspace(tmp_path, missing=True)
    us.update_schedule(str(workspace), findings_count=3, duration_sec=120)
    bp = _read_schedule(workspace)
    assert bp["version"] == "1.0.0"
    assert len(bp["history"]) == 1
    assert bp["history"][0]["findings_count"] == 3
    assert bp["history"][0]["duration_sec"] == 120
    assert bp["recommendation"]["status"] in ("ready", "pause_recommended")
    out = capsys.readouterr().out
    assert "Round 1 saved" in out


def test_update_schedule_existing_file(tmp_path):
    """Covers lines 21-23: existing yaml loaded."""
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": "2026-09-10T12:00:00",
             "findings_count": 5, "duration_sec": 100}
        ],
        "metrics": {"old": "kept"},
        "recommendation": {"status": "ready"},
    }
    workspace = _make_workspace(tmp_path, existing_schedule=existing)
    us.update_schedule(str(workspace), findings_count=7, duration_sec=200)
    bp = _read_schedule(workspace)
    assert len(bp["history"]) == 2
    assert bp["history"][1]["findings_count"] == 7
    # old metrics preserved (setdefault doesn't overwrite)
    assert bp["metrics"].get("old") == "kept"


def test_update_schedule_empty_yaml_returns_none(tmp_path):
    """Covers line 23: yaml.safe_load returns None → `or {}` fallback."""
    workspace = _make_workspace(tmp_path)
    # Write empty file
    (workspace / "mas-engineer" / ".mase" / "schedule.yaml").write_text("")
    us.update_schedule(str(workspace), findings_count=1, duration_sec=10)
    bp = _read_schedule(workspace)
    assert len(bp["history"]) == 1


def test_update_schedule_appends_round(tmp_path):
    """Covers line 33-38: round number = len(history) + 1."""
    workspace = _make_workspace(tmp_path)
    us.update_schedule(str(workspace), findings_count=1, duration_sec=10)
    us.update_schedule(str(workspace), findings_count=2, duration_sec=20)
    us.update_schedule(str(workspace), findings_count=3, duration_sec=30)
    bp = _read_schedule(workspace)
    assert bp["history"][0]["round"] == 1
    assert bp["history"][1]["round"] == 2
    assert bp["history"][2]["round"] == 3


def test_update_schedule_truncates_to_10(tmp_path):
    """Covers line 41: history[-10:] keeps only last 10."""
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": i, "time": f"2026-09-{i:02d}T12:00:00",
             "findings_count": 1, "duration_sec": 10}
            for i in range(1, 13)  # 12 entries
        ],
    }
    workspace = _make_workspace(tmp_path, existing_schedule=existing)
    us.update_schedule(str(workspace), findings_count=1, duration_sec=10)
    bp = _read_schedule(workspace)
    assert len(bp["history"]) == 10
    # First entry should be round 4 (12-10+1+1=4? No: kept last 10 of 13, so rounds 4..13)
    assert bp["history"][0]["round"] == 4
    assert bp["history"][-1]["round"] == 13


def test_update_schedule_metrics_single_round(tmp_path):
    """Covers line 49 False (n==1): no avg_interval_min, but other metrics computed."""
    workspace = _make_workspace(tmp_path)
    us.update_schedule(str(workspace), findings_count=10, duration_sec=100)
    bp = _read_schedule(workspace)
    assert "avg_interval_min" not in bp["metrics"]  # n==1 skip
    assert bp["metrics"]["avg_duration_sec"] == 100
    assert bp["metrics"]["avg_findings_per_round"] == 10.0
    assert bp["metrics"]["rounds_without_findings"] == 0


def test_update_schedule_metrics_avg_interval(tmp_path):
    """Covers lines 50-55: n>1 → avg_interval_min computed."""
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": "2026-09-10T12:00:00",
             "findings_count": 5, "duration_sec": 100},
        ],
    }
    workspace = _make_workspace(tmp_path, existing_schedule=existing)
    us.update_schedule(str(workspace), findings_count=5, duration_sec=100)
    bp = _read_schedule(workspace)
    # 2 rounds, ~5min apart (instant in test, but at least >= 0)
    assert "avg_interval_min" in bp["metrics"]
    assert bp["metrics"]["avg_interval_min"] >= 0


def test_update_schedule_metrics_avg_interval_with_datetime_objects(tmp_path):
    """Covers line 52-53 True: time is datetime object (not str)."""
    from datetime import datetime, timedelta
    workspace = _make_workspace(tmp_path)
    me = workspace / "mas-engineer" / ".mase"
    # Pre-populate with a YAML that loads as datetime (yaml 1.1 parses ISO timestamps)
    # If yaml doesn't auto-parse, the fromisoformat path is taken.
    # Either way, the code handles both paths — we just verify no crash.
    t1 = datetime.now() - timedelta(minutes=10)
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": t1, "findings_count": 5, "duration_sec": 100},
        ],
    }
    (me / "schedule.yaml").write_text(yaml.dump(existing))
    us.update_schedule(str(workspace), findings_count=5, duration_sec=100)
    bp = _read_schedule(workspace)
    assert "avg_interval_min" in bp["metrics"]


def test_update_schedule_metrics_rounds_without_findings(tmp_path):
    """Covers line 59: rounds_without_findings counts zero-finding rounds."""
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": "2026-09-10T12:00:00",
             "findings_count": 5, "duration_sec": 100},
            {"round": 2, "time": "2026-09-10T13:00:00",
             "findings_count": 0, "duration_sec": 100},
        ],
    }
    workspace = _make_workspace(tmp_path, existing_schedule=existing)
    us.update_schedule(str(workspace), findings_count=0, duration_sec=100)
    bp = _read_schedule(workspace)
    # 3 rounds total: round 2 + new = 2 with 0 findings
    assert bp["metrics"]["rounds_without_findings"] == 2


def test_update_schedule_recommendation_zero_findings(tmp_path):
    """Covers lines 66-67: 3 rounds with sum=0 → pause_recommended."""
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": "2026-09-10T12:00:00",
             "findings_count": 0, "duration_sec": 100},
            {"round": 2, "time": "2026-09-10T13:00:00",
             "findings_count": 0, "duration_sec": 100},
        ],
    }
    workspace = _make_workspace(tmp_path, existing_schedule=existing)
    us.update_schedule(str(workspace), findings_count=0, duration_sec=100)
    bp = _read_schedule(workspace)
    assert bp["recommendation"]["status"] == "pause_recommended"
    assert "3 Runden" in bp["recommendation"]["reason"]


def test_update_schedule_recommendation_few_findings(tmp_path):
    """Covers lines 68-69: sum<5 → pause_recommended (wenige Findings)."""
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": "2026-09-10T12:00:00",
             "findings_count": 0, "duration_sec": 100},
            {"round": 2, "time": "2026-09-10T13:00:00",
             "findings_count": 2, "duration_sec": 100},
        ],
    }
    workspace = _make_workspace(tmp_path, existing_schedule=existing)
    us.update_schedule(str(workspace), findings_count=2, duration_sec=100)
    bp = _read_schedule(workspace)
    assert bp["recommendation"]["status"] == "pause_recommended"
    assert "Wenige Findings" in bp["recommendation"]["reason"]


def test_update_schedule_recommendation_enough_findings(tmp_path):
    """Covers lines 70-71: sum>=5 → ready."""
    workspace = _make_workspace(tmp_path)
    us.update_schedule(str(workspace), findings_count=10, duration_sec=100)
    bp = _read_schedule(workspace)
    assert bp["recommendation"]["status"] == "ready"
    assert "Enough findings" in bp["recommendation"]["reason"]


def test_update_schedule_next_round_after_set(tmp_path):
    """Covers line 72: next_round_after = '30m'."""
    workspace = _make_workspace(tmp_path)
    us.update_schedule(str(workspace), findings_count=10, duration_sec=100)
    bp = _read_schedule(workspace)
    assert bp["recommendation"]["next_round_after"] == "30m"


def test_update_schedule_last_updated_set(tmp_path):
    """Covers lines 74-75: last_updated + version fields."""
    workspace = _make_workspace(tmp_path)
    us.update_schedule(str(workspace), findings_count=10, duration_sec=100)
    bp = _read_schedule(workspace)
    assert "last_updated" in bp
    assert bp["version"] == "1.0.0"


def test_update_schedule_mkdir_parents(tmp_path):
    """Covers line 77: makedirs(parents=True, exist_ok=True).

    Pre-condition: no .mase/ exists yet. Function should create it.
    """
    workspace = tmp_path / "fresh"
    workspace.mkdir()
    # mas-engineer/.mase/ doesn't exist
    me = workspace / "mas-engineer"
    me.mkdir()
    # .mase/ is missing — function creates it
    us.update_schedule(str(workspace), findings_count=10, duration_sec=100)
    assert (me / ".mase" / "schedule.yaml").exists()


def test_update_schedule_yaml_dump(tmp_path):
    """Covers line 79: yaml.dump writes valid YAML."""
    workspace = _make_workspace(tmp_path)
    us.update_schedule(str(workspace), findings_count=5, duration_sec=50)
    # File exists, parses
    bp = _read_schedule(workspace)
    assert isinstance(bp, dict)
    assert "history" in bp


def test_update_schedule_prints_round_number(tmp_path, capsys):
    """Covers line 83: print(f'Round N saved...')."""
    workspace = _make_workspace(tmp_path)
    us.update_schedule(str(workspace), findings_count=5, duration_sec=50)
    out = capsys.readouterr().out
    assert "Round 1 saved" in out
    assert "Status: ready" in out


def test_update_schedule_uses_mas_engineer_subdir(tmp_path):
    """Covers line 19: bp_path = workspace / mas-engineer / .mase / schedule.yaml."""
    workspace = _make_workspace(tmp_path)
    us.update_schedule(str(workspace), findings_count=5, duration_sec=50)
    # File written under workspace/mas-engineer/.mase/, NOT workspace/.mase/
    assert (workspace / "mas-engineer" / ".mase" / "schedule.yaml").exists()
    assert not (workspace / ".mase" / "schedule.yaml").exists()


# ====================== CLI =======================================

def _run_cli(*args):
    cmd = [sys.executable, str(REPO_ROOT / "tools" / "dev_update_schedule.py")] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def test_cli_no_args():
    """CLI: < 4 args → exit 1, usage message."""
    code, out, _ = _run_cli()
    assert code == 1
    assert "Usage:" in out


def test_cli_two_args():
    """CLI: 2 args → len(sys.argv)=3 < 4 → exit 1."""
    code, out, _ = _run_cli("ws", "5")
    assert code == 1
    assert "Usage:" in out


def test_cli_happy_path(tmp_path):
    """CLI: 4 args → exit 0, schedule.yaml written."""
    workspace = _make_workspace(tmp_path)
    code, out, _ = _run_cli(str(workspace), "5", "100")
    assert code == 0
    assert "Round 1 saved" in out
    assert (workspace / "mas-engineer" / ".mase" / "schedule.yaml").exists()


def test_cli_passes_findings_and_duration(tmp_path):
    """CLI: findings_count and duration_sec are passed correctly."""
    workspace = _make_workspace(tmp_path)
    _run_cli(str(workspace), "42", "300")
    bp = _read_schedule(workspace)
    assert bp["history"][0]["findings_count"] == 42
    assert bp["history"][0]["duration_sec"] == 300

# ====================== CLI direct-call (R110-553 fix) ============
# R110-534's _run_cli() approach uses subprocess which is silently
# broken by /usr/local/lib/python3.11/site-packages/a1_coverage.pth
# (slug="pth" doesn't combine subprocess .coverage.* into in-process
# data file). Replace subprocess calls with in-process direct calls.


def _call_main(argv):
    """Execute dev_update_schedule's __name__=='__main__' guard in-process.

    The trap: import + run_module(run_name='__main__') doesn't execute
    the __name__ guard, because the import already ran it with
    __name__='tools.dev_update_schedule' (the real name). To re-execute
    it as if it were a fresh interpreter run we must exec the source
    code in a fresh namespace where __name__=='__main__'. Then ALL
    guards + module-level code runs again.
    """
    import io as _io
    source_path = REPO_ROOT / "tools" / "dev_update_schedule.py"
    source = source_path.read_text()

    saved_argv = sys.argv
    try:
        sys.argv = ['dev_update_schedule.py'] + list(argv)
        namespace = {
            "__name__": "__main__",
            "__file__": str(source_path),
            "__builtins__": __builtins__,
        }
        # Stop at the __name__=='__main__' guard by raising SystemExit
        # AFTER the guard fires. The guard is a 5-line block
        # (if len(argv) < 4: print; exit; update_schedule()).
        # We capture exit via exec by catching SystemExit via exec
        # running in a single statement; OR we set up signal-trap.
        # Simplest: use redirect_stdout to capture print, then let
        # the guard raise SystemExit normally.
        captured_stdout = _io.StringIO()
        import contextlib
        try:
            with contextlib.redirect_stdout(captured_stdout):
                with contextlib.redirect_stderr(captured_stdout):
                    exec(compile(source, str(source_path), 'exec'), namespace)
        except SystemExit as ei:
            code = ei.code if isinstance(ei.code, int) else 1
            return code, captured_stdout.getvalue()
        # No SystemExit → script ran but didn't call sys.exit.
        # Check stdout for "Round 1 saved" or "Usage:" markers.
        return 0, captured_stdout.getvalue()
    finally:
        sys.argv = saved_argv


def test_cli_direct_no_args():
    """CLI: 0 args → exit 1 (lines 87-89).

    `if len(sys.argv) < 4` triggers Usage print + sys.exit(1).
    """
    code, out = _call_main([])  # len(argv) is just sys.argv[0] + 0 = 1
    assert code == 1
    assert "Usage: dev_update_schedule.py" in out


def test_cli_direct_partial_args():
    """CLI: 2 args → argv length 3 < 4 → exit 1.

    Covers same block as no-args but with realistic partial argv
    (2 user args + the script name = 3 total < 4).
    """
    code, out = _call_main(['ws', '5'])  # 2 args → argv len 3 → < 4
    assert code == 1


def test_cli_direct_full_args(tmp_path):
    """CLI: 4 args → exit 0 (lines 86-91 entirely).

    Covers line 87 (condition False) + line 91 (call update_schedule).
    """
    workspace = _make_workspace(tmp_path)
    code, out = _call_main([str(workspace), '5', '100'])
    assert code == 0
    assert 'Round 1 saved' in out
    bp = _read_schedule(workspace)
    assert len(bp['history']) == 1
    assert bp['history'][0]['findings_count'] == 5
    assert bp['history'][0]['duration_sec'] == 100

