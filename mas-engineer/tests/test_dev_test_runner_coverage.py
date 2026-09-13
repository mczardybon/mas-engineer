"""Targeted coverage push for tools/dev_test_runner.py — R110-503.

Target: dev_test_runner.py (7214 bytes, ~150 stmts, 0% covered → goal ~30%).
Per skill `mas-engineer-coverage-push-workflow` pitfall 8: Always MEASURE
before setting target. Pre-run check showed 0% (no test file existed).

Strategy: Use inline imports + subprocess.run mocking to test the
test-runner logic without actually running pytest. The pure helper
`parse_pytest_output` is the easiest target.

Functions covered:
- parse_pytest_output (pure: extracts pass/fail/error counts)
- run_pytest (mocked subprocess: returns exit code + output)
- check_deps (mocked subprocess: pytest version + tests/ check)
- run (orchestrates run_pytest + parse_pytest_output)
- compare (loads baseline JSON, diffs current vs baseline)
- verify (loop with max_attempts, early-return on success)
- main (CLI dispatch — RUN/CHECK_DEPS/COMPARE/VERIFY)
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"


@pytest.fixture
def lib(tmp_path, monkeypatch):
    """Import dev_test_runner inline."""
    if "tools.dev_test_runner" in sys.modules:
        return sys.modules["tools.dev_test_runner"]
    sys.path.insert(0, str(TOOLS_DIR))
    import tools.dev_test_runner as lib  # noqa: E402
    return lib


# ─────────────────────────────────────────────────────────
# parse_pytest_output — pure helper, easiest target
# ─────────────────────────────────────────────────────────

def test_parse_pytest_output_all_passed(lib):
    """'18 passed in 0.94s' → 18 passed, 0 failed, 0 errors."""
    out = "tests/foo.py . [100%]\n18 passed in 0.94s\n"
    summary = lib.parse_pytest_output(out)
    assert summary["passed"] == 18
    assert summary["failed"] == 0
    assert summary["errors"] == 0
    assert summary["total"] == 18


def test_parse_pytest_output_mixed(lib):
    """'5 passed, 2 failed, 1 error in 1.23s' → counts each."""
    out = "tests/foo.py .::x .::y\n5 passed, 2 failed, 1 error in 1.23s\n"
    summary = lib.parse_pytest_output(out)
    assert summary["passed"] == 5
    assert summary["failed"] == 2
    assert summary["errors"] == 1
    assert summary["total"] == 8


def test_parse_pytest_output_with_skipped(lib):
    """'10 passed, 3 skipped in 1.5s' → counts each."""
    out = "10 passed, 3 skipped in 1.5s\n"
    summary = lib.parse_pytest_output(out)
    assert summary["passed"] == 10
    assert summary["skipped"] == 3


def test_parse_pytest_output_empty(lib):
    """Empty output → all zeros."""
    summary = lib.parse_pytest_output("")
    assert summary == {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "warnings": 0, "total": 0}


def test_parse_pytest_output_no_summary(lib):
    """Output without summary line → all zeros."""
    out = "tests/foo.py . [100%]\n========== no summary line ==========\n"
    summary = lib.parse_pytest_output(out)
    assert summary["passed"] == 0
    assert summary["total"] == 0


def test_parse_pytest_output_first_summary_wins(lib):
    """When multiple 'X passed' lines exist, first wins (stop at first)."""
    out = "5 passed in 0.5s\n10 passed in 1.0s\n"
    summary = lib.parse_pytest_output(out)
    # First line parsed → 5
    assert summary["passed"] == 5


# ─────────────────────────────────────────────────────────
# run_pytest — mocked subprocess
# ─────────────────────────────────────────────────────────

def test_run_pytest_no_tests_dir(lib, tmp_path, monkeypatch):
    """If tests/ doesn't exist → return (2, error msg)."""
    # No tests/ dir created → Path("tests").exists() is False
    monkeypatch.chdir(tmp_path)
    exit_code, output = lib.run_pytest(str(tmp_path))
    assert exit_code == 2
    assert "No tests/" in output


def test_run_pytest_runs_pytest(lib, tmp_path, monkeypatch):
    """If tests/ exists → runs pytest, returns (exit_code, output)."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass\n")
    monkeypatch.chdir(tmp_path)

    # Mock subprocess.run to return a fake result
    fake_result = mock.Mock()
    fake_result.returncode = 0
    fake_result.stdout = "1 passed in 0.1s\n"
    fake_result.stderr = ""
    with mock.patch.object(subprocess, "run", return_value=fake_result) as m:
        exit_code, output = lib.run_pytest(str(tmp_path))
    assert exit_code == 0
    assert "1 passed" in output
    # Verify pytest was invoked (argv = [sys.executable, '-m', 'pytest', ...])
    args = m.call_args[0][0]
    assert "pytest" in args[2]  # position 2 = 'pytest'


def test_run_pytest_with_scope(lib, tmp_path, monkeypatch):
    """Scope argument is passed to pytest."""
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    fake_result = mock.Mock(returncode=0, stdout="ok", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake_result) as m:
        lib.run_pytest(str(tmp_path), scope="tests/test_x.py")
    args = m.call_args[0][0]
    # The scope arg should be in the argv
    assert "tests/test_x.py" in args


# ─────────────────────────────────────────────────────────
# check_deps — mocked subprocess
# ─────────────────────────────────────────────────────────

def test_check_deps_all_present(lib, tmp_path, monkeypatch):
    """pytest available + tests/ exists → ok=True."""
    (tmp_path / "tests").mkdir()
    fake = mock.Mock(returncode=0, stdout="pytest 8.0.0", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.check_deps(str(tmp_path))
    assert result["pytest_available"] is True
    assert result["tests_dir_exists"] is True
    assert result["ok"] is True
    assert "pytest" in result["pytest_version"]


def test_check_deps_no_tests_dir(lib, tmp_path, monkeypatch):
    """tests/ missing → ok=False but pytest_available still true."""
    fake = mock.Mock(returncode=0, stdout="pytest 8.0.0", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.check_deps(str(tmp_path))
    assert result["pytest_available"] is True
    assert result["tests_dir_exists"] is False
    assert result["ok"] is False


def test_check_deps_pytest_missing(lib, tmp_path):
    """pytest not installed → ok=False, version=None."""
    fake = mock.Mock(returncode=1, stdout="", stderr="ModuleNotFoundError")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.check_deps(str(tmp_path))
    assert result["pytest_available"] is False
    assert result["pytest_version"] is None
    assert result["ok"] is False


# ─────────────────────────────────────────────────────────
# run — orchestrates run_pytest + parse_pytest_output
# ─────────────────────────────────────────────────────────

def test_run_command_basic(lib, tmp_path, monkeypatch):
    """run() returns JSON with summary + passed=True on exit 0."""
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    fake = mock.Mock(returncode=0, stdout="3 passed in 0.1s\n", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.run(str(tmp_path))
    assert result["command"] == "RUN"
    assert result["exit_code"] == 0
    assert result["passed"] is True
    assert result["summary"]["passed"] == 3


def test_run_command_failure(lib, tmp_path, monkeypatch):
    """run() with exit code 1 → passed=False, failed count extracted."""
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    fake = mock.Mock(returncode=1, stdout="1 failed in 0.1s\n", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.run(str(tmp_path))
    assert result["passed"] is False
    assert result["summary"]["failed"] == 1


def test_run_command_output_truncated(lib, tmp_path, monkeypatch):
    """Long output (>2000 chars) is truncated to last 2000 chars."""
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    long_output = "x" * 5000 + "\n1 passed in 0.1s\n"
    fake = mock.Mock(returncode=0, stdout=long_output, stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.run(str(tmp_path))
    # output_tail is exactly 2000 chars
    assert len(result["output_tail"]) == 2000


# ─────────────────────────────────────────────────────────
# compare — diff current vs baseline
# ─────────────────────────────────────────────────────────

def test_compare_no_regression(lib, tmp_path, monkeypatch):
    """If current == baseline → regression_detected=False."""
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    # Write baseline
    baseline = {"summary": {"passed": 10, "failed": 0, "errors": 0}}
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))
    # Mock pytest to produce same summary
    fake = mock.Mock(returncode=0, stdout="10 passed in 0.1s\n", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.compare(str(tmp_path), str(baseline_path))
    assert result["command"] == "COMPARE"
    assert result["regression_detected"] is False
    assert result["regressions"] == []


def test_compare_regression_more_failures(lib, tmp_path, monkeypatch):
    """If current has more failures than baseline → regression detected."""
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    baseline = {"summary": {"passed": 10, "failed": 0, "errors": 0}}
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))
    # Mock pytest to produce worse summary
    fake = mock.Mock(returncode=1, stdout="8 passed, 2 failed in 0.1s\n", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.compare(str(tmp_path), str(baseline_path))
    assert result["regression_detected"] is True
    assert any("failed" in r for r in result["regressions"])


def test_compare_regression_fewer_passed(lib, tmp_path, monkeypatch):
    """If current has fewer passed than baseline → regression."""
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    baseline = {"summary": {"passed": 10, "failed": 0, "errors": 0}}
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))
    # Mock pytest: fewer passed
    fake = mock.Mock(returncode=1, stdout="5 passed, 5 failed in 0.1s\n", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.compare(str(tmp_path), str(baseline_path))
    assert result["regression_detected"] is True
    assert any("passed" in r for r in result["regressions"])


def test_compare_missing_baseline(lib, tmp_path, monkeypatch):
    """Missing baseline file → error key set."""
    (tmp_path / "tests").mkdir()
    monkeypatch.chdir(tmp_path)
    fake = mock.Mock(returncode=0, stdout="1 passed\n", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.compare(str(tmp_path), "/nonexistent/baseline.json")
    assert "error" in result
    assert "baseline not found" in result["error"]
    # regression_detected is NOT set (impl returns early before that line)
    # but `current` is included
    assert "current" in result


# ─────────────────────────────────────────────────────────
# verify — retry logic
# ─────────────────────────────────────────────────────────

def test_verify_first_attempt_passes(lib, tmp_path, monkeypatch):
    """First attempt succeeds → returns immediately, no retry."""
    fake = mock.Mock(returncode=0, stdout="all green", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.verify(str(tmp_path), "echo ok", max_attempts=3)
    assert result["passed"] is True
    assert result["final_status"] == "verifying_passed"
    assert len(result["attempts"]) == 1


def test_verify_retries_then_fails(lib, tmp_path):
    """All attempts fail → returns passed=False after max_attempts."""
    fake = mock.Mock(returncode=1, stdout="FAILED", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        result = lib.verify(str(tmp_path), "exit 1", max_attempts=3)
    assert result["passed"] is False
    assert result["final_status"] == "VERIFICATION_FAILED"
    assert result["max_attempts_reached"] is True
    assert len(result["attempts"]) == 3


def test_verify_retries_until_success(lib, tmp_path):
    """Attempt 1 fails, attempt 2 succeeds → returns passed=True."""
    fail = mock.Mock(returncode=1, stdout="", stderr="")
    ok = mock.Mock(returncode=0, stdout="", stderr="")
    with mock.patch.object(subprocess, "run", side_effect=[fail, ok]):
        result = lib.verify(str(tmp_path), "echo", max_attempts=3)
    assert result["passed"] is True
    assert len(result["attempts"]) == 2


# ─────────────────────────────────────────────────────────
# main — CLI dispatch
# ─────────────────────────────────────────────────────────

def test_main_no_args(lib, monkeypatch, capsys):
    """No args → error JSON + exit code 2."""
    monkeypatch.setattr(sys, "argv", ["dev_test_runner"])
    with pytest.raises(SystemExit) as exc_info:
        lib.main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    err = json.loads(captured.out)
    assert "error" in err
    assert "usage" in err["error"]


def test_main_dispatches_check_deps(lib, tmp_path, monkeypatch):
    """CHECK_DEPS → calls check_deps()."""
    (tmp_path / "tests").mkdir()
    monkeypatch.setattr(sys, "argv", ["dev_test_runner", "CHECK_DEPS", str(tmp_path)])
    fake = mock.Mock(returncode=0, stdout="pytest 8.0.0", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        with mock.patch.object(sys, "exit") as mock_exit:
            lib.main()
            # check_deps returns ok=True → exit code 0
            mock_exit.assert_called_once_with(0)


def test_main_unknown_command(lib, monkeypatch, capsys):
    """Unknown command → error JSON + exit code 0 (per impl quirk)."""
    monkeypatch.setattr(sys, "argv", ["dev_test_runner", "FOO"])
    with mock.patch.object(sys, "exit") as mock_exit:
        lib.main()
    # Per impl: result has no "passed" key, so .get("passed", True) → True → exit(0)
    mock_exit.assert_called_once_with(0)
    captured = capsys.readouterr()
    err = json.loads(captured.out)
    assert "error" in err
    assert "FOO" in err["error"]


def test_main_dispatches_run(lib, tmp_path, monkeypatch):
    """RUN → calls run() + exits with exit code."""
    (tmp_path / "tests").mkdir()
    monkeypatch.setattr(sys, "argv", ["dev_test_runner", "RUN", str(tmp_path)])
    monkeypatch.chdir(tmp_path)
    fake = mock.Mock(returncode=0, stdout="1 passed\n", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        with mock.patch.object(sys, "exit") as mock_exit:
            lib.main()
            mock_exit.assert_called_once_with(0)


def test_main_dispatches_run_failure_exit_code(lib, tmp_path, monkeypatch):
    """RUN with pytest failure → exits with code 1."""
    (tmp_path / "tests").mkdir()
    monkeypatch.setattr(sys, "argv", ["dev_test_runner", "RUN", str(tmp_path)])
    monkeypatch.chdir(tmp_path)
    fake = mock.Mock(returncode=1, stdout="1 failed\n", stderr="")
    with mock.patch.object(subprocess, "run", return_value=fake):
        with mock.patch.object(sys, "exit") as mock_exit:
            lib.main()
            mock_exit.assert_called_once_with(1)
