"""
test_r110302_update_schedule.py — R110-302 Coverage Sprint for
tools/dev_update_schedule.py.

Target: dev_update_schedule.py (90 lines, 46 stmts).
Pattern: see test_r110302_mq_topic_depth.py — import tool as a library,
exercise pure functions, then subprocess + runpy for the __main__ guard.

Branch map for update_schedule():
  L22-30   open existing schedule.yaml OR FileNotFoundError fallback
  L33-38   append new round (setdefault("history", []))
  L41      truncate history to last 10
  L49-55   n > 1: compute avg_interval_min   (branch L52-53: time is
           datetime OR string)
  L57-59   always-on metrics: avg_duration_sec,
           avg_findings_per_round, rounds_without_findings
  L62-72   recommendation block:
             findings_sum == 0    → "3 Runden ohne Findings"
             findings_sum < 5     → "Wenige Findings"
             else (>= 5)         → "Enough findings"
  L65      setdefault("recommendation", {}) — missing/present branch
  L74-78   set last_updated + version, write yaml
  L80-82   print summary line

__main__ block:
  L86-88   len(sys.argv) < 4 → usage + sys.exit(1)
  L90      else → update_schedule(argv[1], argv[2], argv[3])

Total: 14 tests covering all branches.
"""
import runpy
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOL = REPO_ROOT / "tools" / "dev_update_schedule.py"
TOOLS_DIR = TOOL.parent


def _import_tool():
    """Import dev_update_schedule as a library, return the module."""
    sys.path.insert(0, str(TOOLS_DIR))
    if "dev_update_schedule" in sys.modules:
        del sys.modules["dev_update_schedule"]
    import dev_update_schedule
    return dev_update_schedule


def _workspace_with_no_schedule(tmp_path: Path) -> Path:
    """Return a workspace path that does NOT have a schedule.yaml yet.

    The tool appends 'mas-engineer/.mase/schedule.yaml' to whatever
    we pass in as `workspace`, so we just create the parent dir and
    return tmp_path itself as the workspace root.
    """
    workspace = tmp_path
    # Ensure mas-engineer/.mase parent dirs exist (the tool will
    # write into the .mase dir, but its parent must exist).
    (workspace / "mas-engineer" / ".mase").mkdir(parents=True, exist_ok=True)
    return workspace


def _workspace_with_schedule(tmp_path: Path, payload: dict) -> Path:
    """Return a workspace that already has a populated schedule.yaml."""
    workspace = _workspace_with_no_schedule(tmp_path)
    bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
    with open(bp_path, "w") as f:
        yaml.dump(payload, f, default_flow_style=False)
    return workspace


def _read_schedule(workspace: Path) -> dict:
    bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
    with open(bp_path) as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────────
# update_schedule() — FileNotFoundError fallback (lines 24-30)
# ─────────────────────────────────────────────────────────────────────

def test_update_schedule_creates_default_when_missing(capsys, tmp_path):
    """No schedule.yaml present → tool creates a default skeleton
    (version/history/metrics/recommendation) and adds round 1.
    """
    mod = _import_tool()
    workspace = _workspace_with_no_schedule(tmp_path)

    mod.update_schedule(str(workspace), findings_count=3, duration_sec=120)

    bp = _read_schedule(workspace)
    assert bp["version"] == "1.0.0"
    assert len(bp["history"]) == 1
    assert bp["history"][0]["round"] == 1
    assert bp["history"][0]["findings_count"] == 3
    assert bp["history"][0]["duration_sec"] == 120
    # "last_updated" is set after metrics are written
    assert "last_updated" in bp
    # The default skeleton is created via the except branch, but then
    # setdefault("history", []) is a no-op since "history" already
    # exists from the fallback. setdefault("metrics") likewise.
    # setdefault("recommendation") likewise.
    # findings_sum = 3 (single round). 0 < 3 < 5 → "Wenige Findings" → pause.
    assert bp["recommendation"]["status"] == "pause_recommended"
    assert "Wenige Findings" in bp["recommendation"]["reason"]
    assert bp["recommendation"]["next_round_after"] == "30m"
    captured = capsys.readouterr()
    assert "saved in schedule.yaml" in captured.out


# ─────────────────────────────────────────────────────────────────────
# update_schedule() — single-round, n==1, no-intervals branch (L49 false)
# ─────────────────────────────────────────────────────────────────────

def test_update_schedule_single_round_skips_intervals(capsys, tmp_path):
    """With n==1 the `if n > 1:` block is skipped → avg_interval_min
    is NOT set on metrics. avg_duration_sec / avg_findings_per_round /
    rounds_without_findings ARE always set.
    """
    mod = _import_tool()
    workspace = _workspace_with_no_schedule(tmp_path)

    mod.update_schedule(str(workspace), findings_count=0, duration_sec=60)

    bp = _read_schedule(workspace)
    metrics = bp["metrics"]
    # Always-on metrics present
    assert metrics["avg_duration_sec"] == 60
    assert metrics["avg_findings_per_round"] == 0.0
    assert metrics["rounds_without_findings"] == 1
    # Skipped because n==1
    assert "avg_interval_min" not in metrics
    # Single round with findings_count=0 → findings_sum=0 → "3 Runden ohne Findings"
    assert bp["recommendation"]["status"] == "pause_recommended"
    assert "3 Runden ohne Findings" in bp["recommendation"]["reason"]
    assert bp["recommendation"]["next_round_after"] == "30m"


# ─────────────────────────────────────────────────────────────────────
# update_schedule() — n > 1: intervals computed from existing history
# ─────────────────────────────────────────────────────────────────────

def test_update_schedule_multi_round_computes_avg_interval(capsys, tmp_path):
    """With 2+ rounds the interval block runs, and existing string-typed
    `time` values get parsed via datetime.fromisoformat(). Also exercises
    the `bp.setdefault("history", [])` no-op (history already exists).
    """
    mod = _import_tool()
    now = datetime.now()
    t1 = (now.replace(microsecond=0) - __import__("datetime").timedelta(minutes=10)).isoformat()
    t2 = now.replace(microsecond=0).isoformat()
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": t1, "findings_count": 2, "duration_sec": 100},
            {"round": 2, "time": t2, "findings_count": 4, "duration_sec": 200},
        ],
        "metrics": {},
        "recommendation": {"status": "ready"},
    }
    workspace = _workspace_with_schedule(tmp_path, existing)

    mod.update_schedule(str(workspace), findings_count=6, duration_sec=300)

    bp = _read_schedule(workspace)
    assert len(bp["history"]) == 3
    assert bp["history"][-1]["round"] == 3
    # The interval block ran (n > 1)
    assert "avg_interval_min" in bp["metrics"]
    # t1..new_round interval: t1 → t2 (10 min), t2 → new (≈0 min).
    # avg ≈ 5 min, truncated to int.
    assert isinstance(bp["metrics"]["avg_interval_min"], int)


def test_update_schedule_multi_round_with_datetime_objects(capsys, tmp_path):
    """If a history entry's `time` is already a datetime (not str),
    the `isinstance(..., datetime)` branch in L52-53 is taken.
    """
    mod = _import_tool()
    now = datetime.now()
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": now - __import__("datetime").timedelta(minutes=5),
             "findings_count": 1, "duration_sec": 50},
            {"round": 2, "time": now, "findings_count": 1, "duration_sec": 50},
        ],
        "metrics": {},
        "recommendation": {"status": "ready"},
    }
    workspace = _workspace_with_schedule(tmp_path, existing)

    mod.update_schedule(str(workspace), findings_count=1, duration_sec=50)

    bp = _read_schedule(workspace)
    # n=3, last 3 = all → findings_sum=1+1+1=3 → 0 < 3 < 5 → "Wenige Findings"
    assert bp["recommendation"]["status"] == "pause_recommended"
    assert "Wenige Findings" in bp["recommendation"]["reason"]


# ─────────────────────────────────────────────────────────────────────
# update_schedule() — recommendation branches
# ─────────────────────────────────────────────────────────────────────

def test_update_schedule_recommendation_pause_3_rounds_no_findings(capsys, tmp_path):
    """findings_sum == 0 → status='pause_recommended', reason mentions
    '3 Runden ohne Findings'.
    """
    mod = _import_tool()
    now = datetime.now()
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": now - __import__("datetime").timedelta(minutes=10),
             "findings_count": 0, "duration_sec": 100},
            {"round": 2, "time": now - __import__("datetime").timedelta(minutes=5),
             "findings_count": 0, "duration_sec": 100},
        ],
        "metrics": {},
        "recommendation": {"status": "ready"},
    }
    workspace = _workspace_with_schedule(tmp_path, existing)

    mod.update_schedule(str(workspace), findings_count=0, duration_sec=100)

    bp = _read_schedule(workspace)
    rec = bp["recommendation"]
    assert rec["status"] == "pause_recommended"
    assert "3 Runden ohne Findings" in rec["reason"]


def test_update_schedule_recommendation_pause_few_findings(capsys, tmp_path):
    """0 < findings_sum < 5 → status='pause_recommended', reason mentions
    'Wenige Findings'.
    """
    mod = _import_tool()
    now = datetime.now()
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": now - __import__("datetime").timedelta(minutes=10),
             "findings_count": 1, "duration_sec": 100},
            {"round": 2, "time": now - __import__("datetime").timedelta(minutes=5),
             "findings_count": 1, "duration_sec": 100},
        ],
        "metrics": {},
        "recommendation": {"status": "ready"},
    }
    workspace = _workspace_with_schedule(tmp_path, existing)

    mod.update_schedule(str(workspace), findings_count=2, duration_sec=100)

    bp = _read_schedule(workspace)
    rec = bp["recommendation"]
    # last 3 = [1, 1, 2] → sum=4 → 0 < 4 < 5 → "Wenige Findings"
    assert rec["status"] == "pause_recommended"
    assert "Wenige Findings" in rec["reason"]


def test_update_schedule_recommendation_ready_enough_findings(capsys, tmp_path):
    """findings_sum >= 5 → status='ready', reason mentions 'Enough findings'."""
    mod = _import_tool()
    now = datetime.now()
    existing = {
        "version": "1.0.0",
        "history": [
            {"round": 1, "time": now - __import__("datetime").timedelta(minutes=10),
             "findings_count": 2, "duration_sec": 100},
            {"round": 2, "time": now - __import__("datetime").timedelta(minutes=5),
             "findings_count": 3, "duration_sec": 100},
        ],
        "metrics": {},
        "recommendation": {"status": "ready"},
    }
    workspace = _workspace_with_schedule(tmp_path, existing)

    mod.update_schedule(str(workspace), findings_count=5, duration_sec=100)

    bp = _read_schedule(workspace)
    rec = bp["recommendation"]
    # last 3 = [2, 3, 5] → sum=10 → >= 5 → "Enough findings"
    assert rec["status"] == "ready"
    assert "Enough findings" in rec["reason"]


# ─────────────────────────────────────────────────────────────────────
# update_schedule() — history truncation to last 10
# ─────────────────────────────────────────────────────────────────────

def test_update_schedule_truncates_to_last_10(capsys, tmp_path):
    """When history has >= 10 entries, only the most recent 10 are kept."""
    mod = _import_tool()
    now = datetime.now()
    history = []
    for i in range(1, 12):  # 11 entries
        history.append({
            "round": i,
            "time": (now - __import__("datetime").timedelta(minutes=11 - i)).isoformat(),
            "findings_count": 1,
            "duration_sec": 50,
        })
    existing = {
        "version": "1.0.0",
        "history": history,
        "metrics": {},
        "recommendation": {"status": "ready"},
    }
    workspace = _workspace_with_schedule(tmp_path, existing)

    mod.update_schedule(str(workspace), findings_count=1, duration_sec=50)

    bp = _read_schedule(workspace)
    assert len(bp["history"]) == 10
    # The new round is the 12th overall; round number is len(history)+1
    # BEFORE truncation, which would have been 12. After truncation,
    # the last 10 entries are kept (the new one + 9 prior).
    assert bp["history"][-1]["findings_count"] == 1
    # The first entry of the original (round 1) should be dropped
    rounds_kept = [h["round"] for h in bp["history"]]
    assert 1 not in rounds_kept


# ─────────────────────────────────────────────────────────────────────
# update_schedule() — setdefault branches for metrics + recommendation
# ─────────────────────────────────────────────────────────────────────

def test_update_schedule_yaml_without_metrics_or_recommendation(capsys, tmp_path):
    """If the existing yaml has NO 'metrics' or NO 'recommendation' keys,
    setdefault populates them. This covers the `setdefault` truthy-fallback
    branch at L47 and L65.
    """
    mod = _import_tool()
    now = datetime.now()
    existing = {
        "version": "1.0.0",
        "history": [
            # Two rounds, so the interval block runs and metrics dict is populated.
            {"round": 1, "time": now - __import__("datetime").timedelta(minutes=5),
             "findings_count": 1, "duration_sec": 50},
            {"round": 2, "time": now, "findings_count": 1, "duration_sec": 50},
        ],
        # NOTE: no "metrics" or "recommendation" keys
    }
    workspace = _workspace_with_schedule(tmp_path, existing)

    mod.update_schedule(str(workspace), findings_count=1, duration_sec=50)

    bp = _read_schedule(workspace)
    assert "metrics" in bp and isinstance(bp["metrics"], dict)
    assert "recommendation" in bp and isinstance(bp["recommendation"], dict)
    # And the always-on metrics got filled in
    assert "avg_duration_sec" in bp["metrics"]


def test_update_schedule_yaml_history_key_missing(capsys, tmp_path):
    """If the existing yaml has NO 'history' key, setdefault("history", [])
    creates an empty list. The new round is then round=1.
    """
    mod = _import_tool()
    existing = {
        "version": "1.0.0",
        "metrics": {},
        "recommendation": {"status": "ready"},
        # NOTE: no "history" key
    }
    workspace = _workspace_with_schedule(tmp_path, existing)

    mod.update_schedule(str(workspace), findings_count=2, duration_sec=80)

    bp = _read_schedule(workspace)
    assert len(bp["history"]) == 1
    assert bp["history"][0]["round"] == 1


# ─────────────────────────────────────────────────────────────────────
# update_schedule() — print summary
# ─────────────────────────────────────────────────────────────────────

def test_update_schedule_prints_round_summary(capsys, tmp_path):
    """The tool prints '✅ Round N saved in schedule.yaml. Status: <status>'."""
    mod = _import_tool()
    workspace = _workspace_with_no_schedule(tmp_path)

    mod.update_schedule(str(workspace), findings_count=7, duration_sec=200)

    captured = capsys.readouterr()
    # 1 round, findings_sum=7 → "ready Enough findings"
    assert "Round 1" in captured.out
    assert "saved in schedule.yaml" in captured.out
    assert "Status: ready" in captured.out


# ─────────────────────────────────────────────────────────────────────
# __main__ guard — subprocess invocation (full script)
# ─────────────────────────────────────────────────────────────────────

def test_main_subprocess_missing_args(tmp_path, monkeypatch):
    """Running the tool with < 4 argv → rc=1 and usage printed to stdout."""
    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [sys.executable, str(TOOL), "ws"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "Usage:" in result.stdout
    assert "dev_update_schedule.py" in result.stdout


def test_main_subprocess_with_valid_args(tmp_path, monkeypatch):
    """Running the tool with a real workspace creates schedule.yaml
    and prints the success summary. End-to-end CLI smoke test.
    """
    monkeypatch.chdir(tmp_path)
    workspace = tmp_path / "subproc-ws"
    workspace.mkdir()
    (workspace / "mas-engineer" / ".mase").mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, str(TOOL), str(workspace), "4", "90"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "Round 1" in result.stdout
    # schedule.yaml should now exist with the new round
    bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
    assert bp_path.exists()
    with open(bp_path) as f:
        bp = yaml.safe_load(f)
    assert len(bp["history"]) == 1
    assert bp["history"][0]["findings_count"] == 4
    assert bp["history"][0]["duration_sec"] == 90


# ─────────────────────────────────────────────────────────────────────
# __main__ guard — runpy in-process for coverage attribution
# ─────────────────────────────────────────────────────────────────────

def test_main_runpy_missing_args_uses_dunder_main(monkeypatch, capsys, tmp_path):
    """Execute the script via `runpy.run_path(run_name='__main__')` to
    hit the `if __name__ == "__main__":` block IN-PROCESS, so coverage.py
    attributes the line to this test. With < 4 argv → sys.exit(1).
    """
    monkeypatch.setattr(sys, "argv", ["dev_update_schedule.py", "ws"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(TOOL), run_name="__main__")
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Usage:" in captured.out


def test_main_runpy_valid_args_uses_dunder_main(monkeypatch, capsys, tmp_path):
    """Execute the script via `runpy.run_path(run_name='__main__')` with
    4 argv → update_schedule runs successfully → sys.exit(0) NOT raised
    (update_schedule doesn't sys.exit, so runpy returns normally).
    """
    workspace = _workspace_with_no_schedule(tmp_path)
    monkeypatch.setattr(
        sys, "argv",
        ["dev_update_schedule.py", str(workspace), "5", "150"],
    )
    # update_schedule doesn't call sys.exit, so runpy completes normally
    # (no SystemExit).
    runpy.run_path(str(TOOL), run_name="__main__")
    captured = capsys.readouterr()
    # 1 round, findings_sum=5 → "ready Enough findings"
    assert "Round 1" in captured.out
    assert "Status: ready" in captured.out
    # schedule.yaml was written
    bp = _read_schedule(workspace)
    assert bp["history"][-1]["findings_count"] == 5
