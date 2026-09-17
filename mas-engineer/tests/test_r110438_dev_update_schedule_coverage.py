"""R110-438 — coverage-push r7: tools/dev_update_schedule.py 0% → 100%.

Self-improve timing update (90 lines). Appends a round to
.mase/schedule.yaml after each self-improvement round, keeps last
10, computes metrics, and sets recommendation.

Targets:
- update_schedule: missing schedule.yaml → creates default with
  history/metrics/recommendation, existing schedule loads, history
  capped at last 10, single round (n=1) → no avg_interval_min but
  avg_duration_sec + avg_findings_per_round computed, multiple
  rounds → avg_interval_min computed, recommendation:
  findings_sum == 0 (last 3) → pause_recommended "3 Runden ohne
  Findings", findings_sum < 5 → pause_recommended "Wenige Findings",
  findings_sum >= 5 → ready "Enough findings", next_round_after
  always set to "30m", last_updated + version set
- __main__ exec: <4 args (exit 1 + Usage), valid args → file
  written + ✅ printed
"""

import io
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_update_schedule as us  # noqa: E402


def _write_existing_schedule(workspace, history=None):
    """Pre-populate schedule.yaml with optional history."""
    schedule_path = (Path(workspace) / "mas-engineer" / ".mase"
                     / "schedule.yaml")
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": "1.0.0", "history": history or [],
            "metrics": {}, "recommendation": {"status": "ready"}}
    schedule_path.write_text(yaml.dump(data))


def _load_schedule(workspace):
    schedule_path = (Path(workspace) / "mas-engineer" / ".mase"
                     / "schedule.yaml")
    return yaml.safe_load(schedule_path.read_text())


# ─────────────────────────────────────────────────────────────────────
# update_schedule
# ─────────────────────────────────────────────────────────────────────
class TestUpdateSchedule:
    def test_missing_schedule_creates_default(self, tmp_path, capsys):
        # No schedule.yaml → creates with default structure
        # But we need to ensure the parent dir exists for write
        (tmp_path / "mas-engineer" / ".mase").mkdir(parents=True)
        us.update_schedule(str(tmp_path), findings_count=2,
                           duration_sec=10)
        sched = _load_schedule(tmp_path)
        assert sched["version"] == "1.0.0"
        assert len(sched["history"]) == 1
        assert sched["history"][0]["findings_count"] == 2
        assert sched["history"][0]["duration_sec"] == 10
        assert sched["recommendation"]["status"] in ("ready",
                                                      "pause_recommended")

    def test_round_numbering(self, tmp_path, capsys):
        _write_existing_schedule(tmp_path)
        us.update_schedule(str(tmp_path), findings_count=3, duration_sec=5)
        us.update_schedule(str(tmp_path), findings_count=4, duration_sec=6)
        sched = _load_schedule(tmp_path)
        assert sched["history"][0]["round"] == 1
        assert sched["history"][1]["round"] == 2

    def test_history_capped_at_10(self, tmp_path, capsys):
        # Pre-load 12 rounds + add 1 → should keep last 10
        history = [{"round": i, "time": "2025-01-01T00:00:00",
                     "findings_count": 1, "duration_sec": 1}
                   for i in range(1, 13)]
        _write_existing_schedule(tmp_path, history=history)
        us.update_schedule(str(tmp_path), findings_count=2, duration_sec=2)
        sched = _load_schedule(tmp_path)
        assert len(sched["history"]) == 10
        # Last entry is the new one (round 13)
        assert sched["history"][-1]["findings_count"] == 2

    def test_single_round_no_avg_interval(self, tmp_path, capsys):
        _write_existing_schedule(tmp_path)
        us.update_schedule(str(tmp_path), findings_count=2,
                           duration_sec=10)
        sched = _load_schedule(tmp_path)
        # No avg_interval_min with just 1 round
        assert "avg_interval_min" not in sched["metrics"]
        assert sched["metrics"]["avg_duration_sec"] == 10
        assert sched["metrics"]["avg_findings_per_round"] == 2.0

    def test_two_rounds_calculates_interval(self, tmp_path, capsys):
        _write_existing_schedule(tmp_path)
        us.update_schedule(str(tmp_path), findings_count=2, duration_sec=10)
        us.update_schedule(str(tmp_path), findings_count=3, duration_sec=20)
        sched = _load_schedule(tmp_path)
        assert "avg_interval_min" in sched["metrics"]
        # 2 rounds → 1 interval → int
        assert isinstance(sched["metrics"]["avg_interval_min"], int)

    def test_recommendation_pause_when_3_rounds_no_findings(
            self, tmp_path, capsys):
        history = [
            {"round": 1, "time": "2025-01-01T00:00:00",
             "findings_count": 0, "duration_sec": 1},
            {"round": 2, "time": "2025-01-01T00:01:00",
             "findings_count": 0, "duration_sec": 1},
            {"round": 3, "time": "2025-01-01T00:02:00",
             "findings_count": 1, "duration_sec": 1},
            {"round": 4, "time": "2025-01-01T00:03:00",
             "findings_count": 0, "duration_sec": 1},
            {"round": 5, "time": "2025-01-01T00:04:00",
             "findings_count": 0, "duration_sec": 1},
        ]
        _write_existing_schedule(tmp_path, history=history)
        # Last 3 rounds have findings_sum = 0+0+0 = 0
        us.update_schedule(str(tmp_path), findings_count=0,
                           duration_sec=1)
        sched = _load_schedule(tmp_path)
        assert sched["recommendation"]["status"] == "pause_recommended"
        assert "3 Runden" in sched["recommendation"]["reason"]

    def test_recommendation_pause_when_few_findings(self, tmp_path,
                                                      capsys):
        history = [
            {"round": 1, "time": "2025-01-01T00:00:00",
             "findings_count": 1, "duration_sec": 1},
            {"round": 2, "time": "2025-01-01T00:01:00",
             "findings_count": 1, "duration_sec": 1},
            {"round": 3, "time": "2025-01-01T00:02:00",
             "findings_count": 1, "duration_sec": 1},
            {"round": 4, "time": "2025-01-01T00:03:00",
             "findings_count": 1, "duration_sec": 1},
            {"round": 5, "time": "2025-01-01T00:04:00",
             "findings_count": 1, "duration_sec": 1},
        ]
        _write_existing_schedule(tmp_path, history=history)
        # Last 3: findings_sum = 3 < 5
        us.update_schedule(str(tmp_path), findings_count=1, duration_sec=1)
        sched = _load_schedule(tmp_path)
        assert sched["recommendation"]["status"] == "pause_recommended"
        assert "Wenige Findings" in sched["recommendation"]["reason"]

    def test_recommendation_ready_when_enough_findings(self, tmp_path,
                                                        capsys):
        history = [
            {"round": 1, "time": "2025-01-01T00:00:00",
             "findings_count": 5, "duration_sec": 1},
            {"round": 2, "time": "2025-01-01T00:01:00",
             "findings_count": 5, "duration_sec": 1},
            {"round": 3, "time": "2025-01-01T00:02:00",
             "findings_count": 5, "duration_sec": 1},
            {"round": 4, "time": "2025-01-01T00:03:00",
             "findings_count": 5, "duration_sec": 1},
            {"round": 5, "time": "2025-01-01T00:04:00",
             "findings_count": 5, "duration_sec": 1},
        ]
        _write_existing_schedule(tmp_path, history=history)
        # Last 3: findings_sum = 15 >= 5
        us.update_schedule(str(tmp_path), findings_count=5, duration_sec=1)
        sched = _load_schedule(tmp_path)
        assert sched["recommendation"]["status"] == "ready"
        assert "Enough findings" in sched["recommendation"]["reason"]

    def test_next_round_after_always_30m(self, tmp_path, capsys):
        _write_existing_schedule(tmp_path)
        us.update_schedule(str(tmp_path), findings_count=5, duration_sec=1)
        sched = _load_schedule(tmp_path)
        assert sched["recommendation"]["next_round_after"] == "30m"

    def test_last_updated_and_version_set(self, tmp_path, capsys):
        _write_existing_schedule(tmp_path)
        us.update_schedule(str(tmp_path), findings_count=2, duration_sec=1)
        sched = _load_schedule(tmp_path)
        assert "last_updated" in sched
        assert sched["version"] == "1.0.0"

    def test_existing_metrics_preserved_and_extended(self, tmp_path,
                                                       capsys):
        # Pre-set a metrics key, then call — should still be there
        schedule_path = (tmp_path / "mas-engineer" / ".mase"
                         / "schedule.yaml")
        schedule_path.parent.mkdir(parents=True)
        schedule_path.write_text(yaml.dump({
            "version": "1.0.0", "history": [],
            "metrics": {"custom_key": "preserved"},
            "recommendation": {"status": "ready"},
        }))
        us.update_schedule(str(tmp_path), findings_count=2, duration_sec=1)
        sched = _load_schedule(tmp_path)
        assert sched["metrics"]["custom_key"] == "preserved"

    def test_console_output(self, tmp_path, capsys):
        _write_existing_schedule(tmp_path)
        us.update_schedule(str(tmp_path), findings_count=2, duration_sec=1)
        out = capsys.readouterr().out
        assert "✅ Round" in out
        assert "schedule.yaml" in out

    def test_rounds_without_findings_counter(self, tmp_path, capsys):
        history = [
            {"round": 1, "time": "2025-01-01T00:00:00",
             "findings_count": 0, "duration_sec": 1},
            {"round": 2, "time": "2025-01-01T00:01:00",
             "findings_count": 5, "duration_sec": 1},
        ]
        _write_existing_schedule(tmp_path, history=history)
        us.update_schedule(str(tmp_path), findings_count=0, duration_sec=1)
        sched = _load_schedule(tmp_path)
        # 2 rounds with findings=0 (first + new one)
        assert sched["metrics"]["rounds_without_findings"] == 2


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_too_few_args_exits_1(self, capsys):
        old_argv = sys.argv
        try:
            sys.argv = ["dev_update_schedule.py", "ws"]
            with pytest.raises(SystemExit) as exc:
                exec(compile(Path(__file__).resolve().parents[1]
                             .joinpath("tools/dev_update_schedule.py")
                             .read_text(),
                             "dev_update_schedule.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_update_schedule.py"})
            assert exc.value.code == 1
            out = capsys.readouterr().out
            assert "Usage:" in out
        finally:
            sys.argv = old_argv

    def test_valid_args_writes_file(self, tmp_path, capsys):
        # Make sure schedule dir can be created
        (tmp_path / "mas-engineer" / ".mase").mkdir(parents=True)
        old_argv = sys.argv
        try:
            sys.argv = ["dev_update_schedule.py", str(tmp_path),
                        "3", "15"]
            exec(compile(Path(__file__).resolve().parents[1]
                         .joinpath("tools/dev_update_schedule.py")
                         .read_text(),
                         "dev_update_schedule.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_update_schedule.py"})
            out = capsys.readouterr().out
            assert "✅ Round" in out
            sched = _load_schedule(tmp_path)
            assert sched["history"][-1]["findings_count"] == 3
            assert sched["history"][-1]["duration_sec"] == 15
        finally:
            sys.argv = old_argv
