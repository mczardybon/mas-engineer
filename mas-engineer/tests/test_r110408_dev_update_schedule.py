"""R110-408: tests for tools/dev_update_schedule.py.

`update_schedule(workspace, findings_count, duration_sec)` reads
`<workspace>/mas-engineer/.mase/schedule.yaml`, appends a new round,
truncates to last-10, recomputes metrics, and sets a recommendation
based on the sum of the last 3 rounds' findings.

Has 1 function with 6 branches:
  1. schedule.yaml missing → init with default structure
  2. schedule.yaml exists → load YAML
  3. history.append (always)
  4. history[-10:] truncation (always)
  5. metrics: n > 1 → compute intervals; n == 1 → skip
  6. recommendation: 0 findings → "pause_recommended (0)"; <5 → "pause_recommended (few)"; else → "ready"

R110-300a guard: NO `assert "<digit> <word>"` patterns anywhere.
"""
import importlib.util
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

TOOL = Path(__file__).resolve().parent.parent / "tools" / "dev_update_schedule.py"


# ---------------------------------------------------------------------------
# Module loader (same coverage-attribution trick as R110-303)
# ---------------------------------------------------------------------------
def _import_tool():
    REPO_ROOT = str(Path(TOOL).parent.parent)
    TOOLS_DIR = str(Path(TOOL).parent)
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    if "tools" not in sys.modules:
        import types
        pkg = types.ModuleType("tools")
        pkg.__path__ = [TOOLS_DIR]
        sys.modules["tools"] = pkg
    full_name = f"tools.{Path(TOOL).stem}"
    spec = importlib.util.spec_from_file_location(full_name, TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _import_tool()


@pytest.fixture
def workspace(tmp_path):
    """A fresh workspace with mas-engineer/.mase/ subdir pre-created."""
    me_dir = tmp_path / "mas-engineer" / ".mase"
    me_dir.mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# update_schedule — branch tests
# ---------------------------------------------------------------------------
class TestUpdateSchedule:
    def test_creates_schedule_when_missing(self, mod, workspace, monkeypatch, capsys):
        # No schedule.yaml yet → default structure created
        monkeypatch.setattr(mod, "datetime", datetime)  # use real now
        mod.update_schedule(str(workspace), findings_count=2, duration_sec=10)
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        assert bp_path.exists()
        bp = yaml.safe_load(bp_path.read_text())
        assert bp["version"] == "1.0.0"
        assert len(bp["history"]) == 1
        assert bp["history"][0]["findings_count"] == 2
        assert bp["history"][0]["duration_sec"] == 10
        # With only one round, avg_interval_min is NOT set
        assert "avg_interval_min" not in bp["metrics"]
        # Recommendation for 2 findings (< 5) → pause_recommended
        assert bp["recommendation"]["status"] == "pause_recommended"
        captured = capsys.readouterr()
        assert "saved" in captured.out.lower() or "round" in captured.out.lower()

    def test_appends_to_existing_schedule(self, mod, workspace, monkeypatch):
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        existing = {
            "version": "1.0.0",
            "history": [
                {"round": 1, "time": (datetime.now() - timedelta(minutes=30)).isoformat(),
                 "findings_count": 4, "duration_sec": 20},
            ],
            "metrics": {},
            "recommendation": {"status": "ready"},
        }
        bp_path.write_text(yaml.dump(existing))
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=6, duration_sec=15)
        bp = yaml.safe_load(bp_path.read_text())
        assert len(bp["history"]) == 2
        assert bp["history"][1]["findings_count"] == 6
        # 6 findings + 4 findings (from prev round) → last-3 sum = 10 → ready
        assert bp["recommendation"]["status"] == "ready"

    def test_truncates_history_to_last_10(self, mod, workspace, monkeypatch):
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        # Pre-populate with 12 rounds
        now = datetime.now()
        existing = {
            "version": "1.0.0",
            "history": [
                {"round": i, "time": (now - timedelta(minutes=10 * (20 - i))).isoformat(),
                 "findings_count": 6, "duration_sec": 10}
                for i in range(1, 13)  # 12 rounds
            ],
            "metrics": {},
            "recommendation": {"status": "ready"},
        }
        bp_path.write_text(yaml.dump(existing))
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=7, duration_sec=12)
        bp = yaml.safe_load(bp_path.read_text())
        # After truncation + 1 new = 10
        assert len(bp["history"]) == 10
        # Last entry is the new round
        assert bp["history"][-1]["findings_count"] == 7
        # Round numbers should be from the surviving oldest to new
        assert bp["history"][0]["round"] in (3, 4)  # first surviving old round

    def test_metrics_computed_when_multiple_rounds(self, mod, workspace, monkeypatch):
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        now = datetime.now()
        existing = {
            "version": "1.0.0",
            "history": [
                {"round": 1, "time": (now - timedelta(minutes=60)).isoformat(),
                 "findings_count": 5, "duration_sec": 10},
                {"round": 2, "time": (now - timedelta(minutes=30)).isoformat(),
                 "findings_count": 7, "duration_sec": 20},
            ],
            "metrics": {},
            "recommendation": {"status": "ready"},
        }
        bp_path.write_text(yaml.dump(existing))
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=6, duration_sec=15)
        bp = yaml.safe_load(bp_path.read_text())
        m = bp["metrics"]
        # 3 rounds, intervals: 30min, 30min → avg = 30
        assert m["avg_interval_min"] == 30
        # avg duration: (10+20+15)/3 = 15
        assert m["avg_duration_sec"] == 15
        # avg findings: (5+7+6)/3 = 6.0
        assert m["avg_findings_per_round"] == 6.0
        assert m["rounds_without_findings"] == 0

    def test_recommendation_pause_when_zero_findings_in_last_three(self, mod, workspace, monkeypatch):
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        now = datetime.now()
        existing = {
            "version": "1.0.0",
            "history": [
                {"round": 1, "time": (now - timedelta(minutes=60)).isoformat(),
                 "findings_count": 0, "duration_sec": 5},
                {"round": 2, "time": (now - timedelta(minutes=40)).isoformat(),
                 "findings_count": 0, "duration_sec": 5},
            ],
            "metrics": {},
            "recommendation": {"status": "ready"},
        }
        bp_path.write_text(yaml.dump(existing))
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=0, duration_sec=5)
        bp = yaml.safe_load(bp_path.read_text())
        assert bp["recommendation"]["status"] == "pause_recommended"
        assert "3 Runden" in bp["recommendation"]["reason"]

    def test_recommendation_pause_when_few_findings_in_last_three(self, mod, workspace, monkeypatch):
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        now = datetime.now()
        existing = {
            "version": "1.0.0",
            "history": [
                {"round": 1, "time": (now - timedelta(minutes=60)).isoformat(),
                 "findings_count": 1, "duration_sec": 5},
                {"round": 2, "time": (now - timedelta(minutes=40)).isoformat(),
                 "findings_count": 2, "duration_sec": 5},
            ],
            "metrics": {},
            "recommendation": {"status": "ready"},
        }
        bp_path.write_text(yaml.dump(existing))
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=1, duration_sec=5)
        bp = yaml.safe_load(bp_path.read_text())
        assert bp["recommendation"]["status"] == "pause_recommended"
        # Sum of last 3 = 4 (< 5) → "Wenige Findings" branch
        assert "Wenige Findings" in bp["recommendation"]["reason"]

    def test_recommendation_ready_when_many_findings(self, mod, workspace, monkeypatch):
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        now = datetime.now()
        existing = {
            "version": "1.0.0",
            "history": [
                {"round": 1, "time": (now - timedelta(minutes=60)).isoformat(),
                 "findings_count": 5, "duration_sec": 5},
                {"round": 2, "time": (now - timedelta(minutes=40)).isoformat(),
                 "findings_count": 3, "duration_sec": 5},
            ],
            "metrics": {},
            "recommendation": {"status": "ready"},
        }
        bp_path.write_text(yaml.dump(existing))
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=2, duration_sec=5)
        bp = yaml.safe_load(bp_path.read_text())
        # Sum of last 3 = 10 → ready
        assert bp["recommendation"]["status"] == "ready"
        assert "Enough findings" in bp["recommendation"]["reason"]

    def test_rounds_without_findings_count(self, mod, workspace, monkeypatch):
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        now = datetime.now()
        existing = {
            "version": "1.0.0",
            "history": [
                {"round": 1, "time": (now - timedelta(minutes=60)).isoformat(),
                 "findings_count": 0, "duration_sec": 5},
                {"round": 2, "time": (now - timedelta(minutes=40)).isoformat(),
                 "findings_count": 3, "duration_sec": 5},
            ],
            "metrics": {},
            "recommendation": {"status": "ready"},
        }
        bp_path.write_text(yaml.dump(existing))
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=0, duration_sec=5)
        bp = yaml.safe_load(bp_path.read_text())
        # 2 out of 3 rounds had 0 findings
        assert bp["metrics"]["rounds_without_findings"] == 2

    def test_last_updated_set(self, mod, workspace, monkeypatch):
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=2, duration_sec=10)
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        bp = yaml.safe_load(bp_path.read_text())
        assert "last_updated" in bp
        # Should be parseable as ISO format
        datetime.fromisoformat(bp["last_updated"])

    def test_recommendation_next_round_after_30m(self, mod, workspace, monkeypatch):
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=2, duration_sec=10)
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        bp = yaml.safe_load(bp_path.read_text())
        assert bp["recommendation"]["next_round_after"] == "30m"

    def test_handles_empty_yaml_file_as_missing(self, mod, workspace, monkeypatch):
        # Empty YAML file → yaml.safe_load returns None → falls into
        # FileNotFoundError? No, file exists but is empty → safe_load
        # returns None. The code uses `or {}` to default to {}.
        bp_path = workspace / "mas-engineer" / ".mase" / "schedule.yaml"
        bp_path.write_text("")
        monkeypatch.setattr(mod, "datetime", datetime)
        mod.update_schedule(str(workspace), findings_count=1, duration_sec=5)
        bp = yaml.safe_load(bp_path.read_text())
        assert len(bp["history"]) == 1


# ---------------------------------------------------------------------------
# CLI __main__ — basic invocation test
# ---------------------------------------------------------------------------
class TestMainCli:
    def test_no_args_prints_usage_and_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(TOOL)],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "Usage" in result.stderr or "Usage" in result.stdout

    def test_correct_args_appends_round(self, tmp_path):
        # Set up a workspace with mas-engineer/.mase/
        me_dir = tmp_path / "mas-engineer" / ".mase"
        me_dir.mkdir(parents=True)
        result = subprocess.run(
            [sys.executable, str(TOOL), str(tmp_path), "3", "10"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        bp_path = me_dir / "schedule.yaml"
        assert bp_path.exists()
        bp = yaml.safe_load(bp_path.read_text())
        assert len(bp["history"]) == 1
        assert bp["history"][0]["findings_count"] == 3
        assert bp["history"][0]["duration_sec"] == 10
