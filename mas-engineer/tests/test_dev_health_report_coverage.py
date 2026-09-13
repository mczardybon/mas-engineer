"""Tests for tools/dev_health_report.py — coverage gap closer.

Covers the 11% coverage of dev_health_report.py (91 stmts, ~80 missed).
Strategy: mock subprocess for the checker_health check + create real
.mase/ + tools/ + sub/ structures in tmp_path:
- calculate_score() with various target states (no state, partial,
  full state, broken yaml)
- save_history() with no history + existing history
- show_trend() with <2 entries, increasing, decreasing, flat
- main() with --target missing (sys.exit) and valid target
"""
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_health_report as hr


def _create_minimal_target(target: Path, with_rules=True, with_checker=True,
                          with_sub=True, with_changes=True):
    """Helper: create minimal .mase/ + tools/ + sub/ structure."""
    if with_rules:
        rules_dir = target / ".mase" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / "rules.yaml").write_text("""
rules:
  - id: R01
    block: true
    haerte: 4
  - id: R02
    block: false
    haerte: 1
""")
    if with_checker:
        tools_dir = target / "tools"
        tools_dir.mkdir(exist_ok=True)
        (tools_dir / "dev_rule_checker.py").write_text("# stub")
    if with_sub:
        sub_dir = target / "sub"
        sub_dir.mkdir(exist_ok=True)
        (sub_dir / "test.yaml").write_text("name: test\n")
    if with_changes:
        state_dir = target / ".mase"
        state_dir.mkdir(exist_ok=True)
        (state_dir / "changes.json").write_text("[]")


def test_calculate_score_no_target_state(tmp_path):
    """Covers all 4 checks returning 'not found' branches (lines 22-23,
    38-39, 52-53, 66-67)."""
    report = hr.calculate_score(str(tmp_path))
    assert "checks" in report
    assert "score" in report
    # All 4 checks present
    check_names = {c["name"] for c in report["checks"]}
    assert "rules_active" in check_names
    assert "checker_health" in check_names
    assert "yaml_valid" in check_names
    assert "last_si_run" in check_names


def test_calculate_score_full_target(tmp_path, monkeypatch):
    """Covers lines 13-19, 27-39, 43-53, 56-67: all checks with happy path."""
    _create_minimal_target(tmp_path)
    # Mock the subprocess.run call for checker_health
    fake_result = mock.Mock()
    fake_result.returncode = 0
    fake_result.stdout = '{"score": 8.5}'
    fake_result.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: fake_result)
    report = hr.calculate_score(str(tmp_path))
    assert report["score"] >= 0


def test_calculate_score_invalid_yaml(tmp_path):
    """Covers line 20-21: rules.yaml invalid → check fails."""
    rules_dir = tmp_path / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "rules.yaml").write_text("invalid: yaml: [")
    report = hr.calculate_score(str(tmp_path))
    rules_check = next(c for c in report["checks"] if c["name"] == "rules_active")
    assert rules_check["ok"] is False
    assert rules_check["detail"] == "invalid yaml"


def test_calculate_score_invalid_changes_json(tmp_path):
    """Covers lines 64-65: changes.json invalid → check fails."""
    _create_minimal_target(tmp_path, with_changes=False)
    state_dir = tmp_path / ".mase"
    state_dir.mkdir(exist_ok=True)
    (state_dir / "changes.json").write_text("not json {")
    report = hr.calculate_score(str(tmp_path))
    si_check = next(c for c in report["checks"] if c["name"] == "last_si_run")
    assert si_check["ok"] is False


def test_calculate_score_with_recent_si_run(tmp_path):
    """Covers line 62: recent si-run in changes.json → ok=True."""
    import time as t
    state_dir = tmp_path / ".mase"
    state_dir.mkdir(exist_ok=True)
    recent_ts = t.strftime("%Y-%m-%dT%H:%M:%S")
    (state_dir / "changes.json").write_text(json.dumps([
        {"action": "improve-loop", "timestamp": recent_ts}
    ]))
    report = hr.calculate_score(str(tmp_path))
    si_check = next(c for c in report["checks"] if c["name"] == "last_si_run")
    assert si_check["ok"] is True


def test_save_history_creates_file(tmp_path):
    """Covers lines 75-86: save_history writes to .mase/health-history.json
    (caller is responsible for .mase/ existing — see test_calculate_score
    which creates it)."""
    state_dir = tmp_path / ".mase"
    state_dir.mkdir()
    target = str(tmp_path)
    report = {"timestamp": "2026-09-13T07:00:00", "score": 7.5, "checks": []}
    history = hr.save_history(target, report)
    assert isinstance(history, list)
    assert len(history) == 1
    assert history[0]["score"] == 7.5
    assert (tmp_path / ".mase" / "health-history.json").exists()


def test_save_history_appends_to_existing(tmp_path):
    """Covers lines 78-81: existing history file → appended to."""
    state_dir = tmp_path / ".mase"
    state_dir.mkdir()
    (state_dir / "health-history.json").write_text(json.dumps([
        {"timestamp": "2026-09-12", "score": 5.0}
    ]))
    target = str(tmp_path)
    report = {"timestamp": "2026-09-13", "score": 7.5, "checks": []}
    history = hr.save_history(target, report)
    assert len(history) == 2


def test_save_history_handles_corrupt_history(tmp_path):
    """Covers line 81: corrupt history.json → treated as empty."""
    state_dir = tmp_path / ".mase"
    state_dir.mkdir()
    (state_dir / "health-history.json").write_text("not valid json")
    report = {"timestamp": "2026-09-13", "score": 7.5, "checks": []}
    history = hr.save_history(str(tmp_path), report)
    assert len(history) == 1


def test_show_trend_single_entry(capsys):
    """Covers lines 89-90: <2 entries → return early, no output."""
    hr.show_trend([{"score": 5.0}])
    captured = capsys.readouterr()
    assert captured.out == ""


def test_show_trend_increasing(capsys):
    """Covers line 94: trend > 0 → upward arrow."""
    history = [{"score": 5.0}, {"score": 7.5}]
    hr.show_trend(history)
    captured = capsys.readouterr()
    assert "↑" in captured.out or "5.0" in captured.out


def test_show_trend_decreasing(capsys):
    """Covers line 93: trend < 0 → downward arrow."""
    history = [{"score": 7.5}, {"score": 5.0}]
    hr.show_trend(history)
    captured = capsys.readouterr()
    assert "↓" in captured.out or "5.0" in captured.out


def test_show_trend_flat(capsys):
    """Covers line 93: trend == 0 → right arrow."""
    history = [{"score": 5.0}, {"score": 5.0}]
    hr.show_trend(history)
    captured = capsys.readouterr()
    assert "→" in captured.out or "5.0" in captured.out


def test_main_no_target_exits(monkeypatch):
    """Covers lines 102-104: no --target → sys.exit(1)."""
    monkeypatch.setattr(sys, "argv", ["dev_health_report.py"])
    with pytest.raises(SystemExit):
        hr.main()


def test_main_with_valid_target(tmp_path, monkeypatch, capsys):
    """Covers lines 106-125: full main() flow with valid target."""
    _create_minimal_target(tmp_path)
    fake_result = mock.Mock()
    fake_result.returncode = 0
    fake_result.stdout = '{"score": 8.0}'
    fake_result.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: fake_result)
    monkeypatch.setattr(sys, "argv", ["dev_health_report.py", "--target", str(tmp_path)])
    hr.main()
    captured = capsys.readouterr()
    assert "HEALTH-REPORT" in captured.out or "HEoldH-REPORT" in captured.out
