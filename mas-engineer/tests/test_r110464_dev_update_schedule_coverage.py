"""R110-464 — coverage-push r8: tools/dev_update_schedule.py 0% → 100%

Self-Improve schedule updater. CLI:
  python3 dev_update_schedule.py <workspace> <findings_count> <duration_sec>

Updates mas-engineer/.mase/schedule.yaml after a SI round.
Computes avg_interval_min, avg_duration_sec, avg_findings_per_round,
rounds_without_findings, recommendation status.

Targets:
- update_schedule(workspace, findings_count, duration_sec):
  - file exists → load yaml (or {} if empty)
  - file missing → init with defaults (version, history, metrics,
    recommendation ready)
  - history.append new round with time, findings, duration
  - history[-10:]
  - if n > 1: compute avg_interval_min from time diffs in minutes
  - avg_duration_sec, avg_findings_per_round, rounds_without_findings
  - recommendation:
    - last 3 rounds findings_sum == 0 → pause_recommended
      "3 Runden ohne Findings"
    - findings_sum < 5 → pause_recommended
      "Wenige Findings"
    - else → ready "Enough findings"
  - next_round_after = "30m"
  - last_updated + version
  - yaml.dump

- CLI: < 4 args → usage + sys.exit(1)
"""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import tools.dev_update_schedule as us  # noqa: E402


def _schedule_path(workspace):
    return Path(workspace) / "mas-engineer" / ".mase" / "schedule.yaml"


def _read_schedule(workspace):
    with open(_schedule_path(workspace)) as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────────
# file missing → init with defaults
# ─────────────────────────────────────────────────────────────────────
class TestMissingSchedule:
    def test_creates_file_with_defaults(self, tmp_path):
        us.update_schedule(str(tmp_path), 0, 60)
        bp = _read_schedule(tmp_path)
        assert bp["version"] == "1.0.0"
        assert len(bp["history"]) == 1
        assert bp["history"][0]["round"] == 1
        assert bp["history"][0]["findings_count"] == 0
        assert bp["history"][0]["duration_sec"] == 60
        assert bp["recommendation"]["status"] == "pause_recommended"
        assert bp["recommendation"]["next_round_after"] == "30m"
        assert "last_updated" in bp


# ─────────────────────────────────────────────────────────────────────
# file exists with prior history
# ─────────────────────────────────────────────────────────────────────
class TestExistingSchedule:
    def test_appends_round(self, tmp_path):
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        with open(_schedule_path(tmp_path), 'w') as f:
            yaml.dump({"version": "1.0.0", "history": [
                {"round": 1, "time": "2025-01-01T00:00:00",
                 "findings_count": 5, "duration_sec": 100}
            ]}, f)
        us.update_schedule(str(tmp_path), 3, 50)
        bp = _read_schedule(tmp_path)
        assert len(bp["history"]) == 2
        assert bp["history"][1]["round"] == 2

    def test_history_truncated_to_10(self, tmp_path):
        # Pre-populate with 12 rounds
        history = []
        for i in range(12):
            history.append({"round": i+1,
                            "time": f"2025-01-{i+1:02d}T00:00:00",
                            "findings_count": 2,
                            "duration_sec": 100})
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        with open(_schedule_path(tmp_path), 'w') as f:
            yaml.dump({"version": "1.0.0", "history": history}, f)
        us.update_schedule(str(tmp_path), 2, 100)
        bp = _read_schedule(tmp_path)
        # 12 + 1 = 13, then [-10:] keeps last 10
        assert len(bp["history"]) == 10
        assert bp["history"][-1]["round"] == 13

    def test_empty_yaml_file(self, tmp_path):
        # yaml.safe_load returns None for empty → or {}
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        with open(_schedule_path(tmp_path), 'w') as f:
            f.write("")
        us.update_schedule(str(tmp_path), 1, 30)
        bp = _read_schedule(tmp_path)
        assert len(bp["history"]) == 1


# ─────────────────────────────────────────────────────────────────────
# recommendation logic
# ─────────────────────────────────────────────────────────────────────
class TestRecommendation:
    def _prepopulate(self, tmp_path, rounds_with_findings):
        """rounds_with_findings: list of (time_str, findings) tuples."""
        history = []
        for i, (t, f) in enumerate(rounds_with_findings):
            history.append({"round": i+1, "time": t,
                            "findings_count": f,
                            "duration_sec": 60})
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        with open(_schedule_path(tmp_path), 'w') as f:
            yaml.dump({"version": "1.0.0", "history": history}, f)

    def test_pause_three_zero_findings(self, tmp_path):
        # Add 2 prior zero-finding rounds, current will be 3rd → sum=0
        self._prepopulate(tmp_path, [
            ("2025-01-01T00:00:00", 0),
            ("2025-01-01T01:00:00", 0),
        ])
        us.update_schedule(str(tmp_path), 0, 60)
        bp = _read_schedule(tmp_path)
        assert bp["recommendation"]["status"] == "pause_recommended"
        assert "3 Runden" in bp["recommendation"]["reason"]

    def test_pause_few_findings(self, tmp_path):
        # last 3 sum < 5
        self._prepopulate(tmp_path, [
            ("2025-01-01T00:00:00", 1),
            ("2025-01-01T01:00:00", 2),
        ])
        us.update_schedule(str(tmp_path), 1, 60)
        bp = _read_schedule(tmp_path)
        assert bp["recommendation"]["status"] == "pause_recommended"
        assert "Wenige Findings" in bp["recommendation"]["reason"]

    def test_ready_enough_findings(self, tmp_path):
        self._prepopulate(tmp_path, [
            ("2025-01-01T00:00:00", 3),
            ("2025-01-01T01:00:00", 3),
        ])
        us.update_schedule(str(tmp_path), 3, 60)
        bp = _read_schedule(tmp_path)
        assert bp["recommendation"]["status"] == "ready"
        assert "Enough" in bp["recommendation"]["reason"]


# ─────────────────────────────────────────────────────────────────────
# metrics
# ─────────────────────────────────────────────────────────────────────
class TestMetrics:
    def test_avg_duration(self, tmp_path):
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        with open(_schedule_path(tmp_path), 'w') as f:
            yaml.dump({"version": "1.0.0", "history": [
                {"round": 1, "time": "2025-01-01T00:00:00",
                 "findings_count": 0, "duration_sec": 100}
            ]}, f)
        us.update_schedule(str(tmp_path), 0, 200)
        bp = _read_schedule(tmp_path)
        # 2 rounds: 100 + 200 → avg = 150
        assert bp["metrics"]["avg_duration_sec"] == 150

    def test_avg_findings_rounded(self, tmp_path):
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        with open(_schedule_path(tmp_path), 'w') as f:
            yaml.dump({"version": "1.0.0", "history": [
                {"round": 1, "time": "2025-01-01T00:00:00",
                 "findings_count": 1, "duration_sec": 60}
            ]}, f)
        us.update_schedule(str(tmp_path), 2, 60)
        bp = _read_schedule(tmp_path)
        # 1+2=3 / 2 = 1.5
        assert bp["metrics"]["avg_findings_per_round"] == 1.5

    def test_avg_interval_with_two_rounds(self, tmp_path):
        # 2 rounds → 1 interval
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        with open(_schedule_path(tmp_path), 'w') as f:
            yaml.dump({"version": "1.0.0", "history": [
                {"round": 1, "time": "2025-01-01T00:00:00",
                 "findings_count": 1, "duration_sec": 60}
            ]}, f)
        us.update_schedule(str(tmp_path), 1, 60)
        bp = _read_schedule(tmp_path)
        # 2 rounds → n > 1 → compute interval
        # time between round 1 and round 2 = however long the test
        # took. Just check key exists with int value.
        assert "avg_interval_min" in bp["metrics"]
        assert isinstance(bp["metrics"]["avg_interval_min"], int)

    def test_no_interval_with_single_round(self, tmp_path):
        # First round only → n == 1 → no interval
        us.update_schedule(str(tmp_path), 1, 60)
        bp = _read_schedule(tmp_path)
        # n=1 → no avg_interval_min key set
        assert "avg_interval_min" not in bp["metrics"]

    def test_rounds_without_findings(self, tmp_path):
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        with open(_schedule_path(tmp_path), 'w') as f:
            yaml.dump({"version": "1.0.0", "history": [
                {"round": 1, "time": "2025-01-01T00:00:00",
                 "findings_count": 0, "duration_sec": 60}
            ]}, f)
        us.update_schedule(str(tmp_path), 3, 60)
        bp = _read_schedule(tmp_path)
        # 1 zero-finding + 1 with findings → 1
        assert bp["metrics"]["rounds_without_findings"] == 1

    def test_time_as_datetime_object(self, tmp_path):
        # history with datetime objects (not strings) → covers
        # isinstance(h[i]["time"], datetime) branch
        from datetime import datetime
        _schedule_path(tmp_path).parent.mkdir(parents=True)
        # Manually write YAML with mixed types — but YAML only
        # serializes strings. Skip and use string instead.
        # Just verify the roundtrip works with strings.
        with open(_schedule_path(tmp_path), 'w') as f:
            yaml.dump({"version": "1.0.0", "history": [
                {"round": 1, "time": datetime(2025,1,1,0,0,0),
                 "findings_count": 1, "duration_sec": 60}
            ], "metrics": {}, "recommendation": {"status": "ready"}}, f)
        us.update_schedule(str(tmp_path), 2, 60)
        bp = _read_schedule(tmp_path)
        # Both intervals computed (datetime → datetime + str → datetime)
        assert "avg_interval_min" in bp["metrics"]


# ─────────────────────────────────────────────────────────────────────
# CLI subprocess
# ─────────────────────────────────────────────────────────────────────
class TestCli:
    def test_too_few_args(self):
        r = subprocess.run(
            ['python3', 'tools/dev_update_schedule.py', 'ws'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 1
        assert "Usage:" in r.stdout

    def test_valid_args(self, tmp_path):
        r = subprocess.run(
            ['python3', 'tools/dev_update_schedule.py',
             str(tmp_path), '5', '60'],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        assert "Round 1" in r.stdout
        assert "Status:" in r.stdout
        # File created
        assert _schedule_path(tmp_path).exists()
