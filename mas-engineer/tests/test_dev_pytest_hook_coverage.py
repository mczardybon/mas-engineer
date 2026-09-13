#!/usr/bin/env python3
"""
R110-517: Coverage test for tools/dev_pytest_hook.py (37 stmts, 0% → 100%).

Context: dev_pytest_hook.py is a pytest pre/post-test checker hook that
verifies Rule-compliance before and after a test run. Activated via
`pytest --checker-hook`. Pre-test runs the Generic-Improver health-check
and prints a warning if score < 5/10 (but does not block). Post-test
checks for failed tests and recommends running dev_audit_deps.

Module structure (74 lines, 37 stmts, 8 branches):
  - Module constants: _HERE, _CHECKER, _AUDIT_DEPS (paths anchored to
    this module's directory — R110-303 CWD-robustness fix).
  - run_pre_test_checks() — prints status, returns True.
    - 4 branches:
      * _CHECKER doesn't exist → "not found" + return True
      * _CHECKER exists + rc != 0 → "Health-Check failed" + json parse
        (line 36: bare except covers JSONDecodeError + KeyError)
      * _CHECKER exists + rc == 0 → "Heoldh OK" + return True
  - run_post_test_checks(pytest_exit_code) — if exit_code > 0, prints
    the recommendation block (only when _CHECKER exists).
  - main() — argparse-like gate on '--checker-hook', runs pre/post.
    - sys.exit(1) on missing flag.
    - exit_code derived from last argv element if digit.

This file tests all kernel code paths.
"""

import json
import runpy
import sys
from pathlib import Path
from unittest import mock

import pytest

import tools.dev_pytest_hook as hook  # noqa: E402


# ─── run_pre_test_checks ─────────────────────────────────────────────

def test_pre_test_checker_not_found_returns_true(capsys, monkeypatch):
    """Covers line 25-27: _CHECKER.exists() == False path.

    Monkeypatches the module's _CHECKER constant to a non-existent
    path so the existence check fails. The function should print the
    'not found' message and return True.
    """
    fake = Path("/this/path/definitely/does/not/exist/checker.py")
    monkeypatch.setattr(hook, "_CHECKER", fake)
    rc = hook.run_pre_test_checks()
    captured = capsys.readouterr()
    assert rc is True
    assert "not found" in captured.out


def test_pre_test_health_check_passes_prints_ok(capsys, monkeypatch, tmp_path):
    """Covers line 40-41: rc == 0 path.

    Creates a real file at tmp_path so _CHECKER.exists() returns True,
    then mocks subprocess.run to return a fake CompletedProcess with
    rc=0.
    """
    fake_checker = tmp_path / "fake_checker.py"
    fake_checker.write_text("# fake")  # make the file actually exist
    monkeypatch.setattr(hook, "_CHECKER", fake_checker)
    fake_result = mock.Mock()
    fake_result.returncode = 0
    fake_result.stdout = json.dumps({"score": 8})
    with mock.patch.object(hook.subprocess, "run",
                           return_value=fake_result) as mrun:
        rc = hook.run_pre_test_checks()
    captured = capsys.readouterr()
    assert rc is True
    assert "OK" in captured.out
    # subprocess.run called once with our fake checker
    args, _ = mrun.call_args
    assert str(fake_checker) in args[0]


def test_pre_test_health_check_fails_prints_warning(capsys, monkeypatch, tmp_path):
    """Covers lines 30-38: rc != 0 + score >= 5 (warning without score line)."""
    fake_checker = tmp_path / "fake_checker.py"
    fake_checker.write_text("# fake")
    monkeypatch.setattr(hook, "_CHECKER", fake_checker)
    fake_result = mock.Mock()
    fake_result.returncode = 1
    fake_result.stdout = json.dumps({"score": 8})  # >= 5, no extra line
    with mock.patch.object(hook.subprocess, "run",
                           return_value=fake_result):
        rc = hook.run_pre_test_checks()
    captured = capsys.readouterr()
    assert rc is True
    assert "Health-Check failed" in captured.out


def test_pre_test_health_check_fails_low_score_prints_score_line(
    capsys, monkeypatch, tmp_path
):
    """Covers line 34-35: data['score'] < 5 → extra 'Score: X/10' line."""
    fake_checker = tmp_path / "fake_checker.py"
    fake_checker.write_text("# fake")
    monkeypatch.setattr(hook, "_CHECKER", fake_checker)
    fake_result = mock.Mock()
    fake_result.returncode = 1
    fake_result.stdout = json.dumps({"score": 3})  # < 5, score line printed
    with mock.patch.object(hook.subprocess, "run",
                           return_value=fake_result):
        rc = hook.run_pre_test_checks()
    captured = capsys.readouterr()
    assert rc is True
    assert "Health-Check failed" in captured.out
    assert "Score: 3/10" in captured.out


def test_pre_test_health_check_fails_unparseable_stdout(
    capsys, monkeypatch, tmp_path
):
    """Covers line 36: bare except — stdout is not JSON, json.loads
    raises, except branch passes silently. Still returns True."""
    fake_checker = tmp_path / "fake_checker.py"
    fake_checker.write_text("# fake")
    monkeypatch.setattr(hook, "_CHECKER", fake_checker)
    fake_result = mock.Mock()
    fake_result.returncode = 1
    fake_result.stdout = "not json at all"  # raises JSONDecodeError
    with mock.patch.object(hook.subprocess, "run",
                           return_value=fake_result):
        rc = hook.run_pre_test_checks()
    captured = capsys.readouterr()
    assert rc is True
    assert "Health-Check failed" in captured.out
    # The Score: X/10 line is NOT printed (parse failed)
    assert "Score:" not in captured.out


def test_pre_test_health_check_fails_json_missing_score_key(
    capsys, monkeypatch, tmp_path
):
    """Covers line 34 default: data.get('score', 10) — when key
    missing, default is 10, so 10 < 5 is False → no Score line."""
    fake_checker = tmp_path / "fake_checker.py"
    fake_checker.write_text("# fake")
    monkeypatch.setattr(hook, "_CHECKER", fake_checker)
    fake_result = mock.Mock()
    fake_result.returncode = 1
    fake_result.stdout = json.dumps({"other": "value"})  # no 'score' key
    with mock.patch.object(hook.subprocess, "run",
                           return_value=fake_result):
        rc = hook.run_pre_test_checks()
    captured = capsys.readouterr()
    assert rc is True
    assert "Health-Check failed" in captured.out
    assert "Score:" not in captured.out  # default 10 >= 5


# ─── run_post_test_checks ───────────────────────────────────────────

def test_post_test_zero_exit_does_nothing(capsys, monkeypatch, tmp_path):
    """Covers line 54 False branch: pytest_exit_code == 0 → no output."""
    fake_checker = tmp_path / "fake_checker.py"
    monkeypatch.setattr(hook, "_CHECKER", fake_checker)
    rc = hook.run_post_test_checks(0)
    captured = capsys.readouterr()
    assert rc is True
    assert captured.out == ""


def test_post_test_failed_with_checker_present(capsys, monkeypatch, tmp_path):
    """Covers lines 54-61: exit > 0 + _CHECKER exists → recommendation."""
    fake_checker = tmp_path / "fake_checker.py"
    fake_checker.write_text("# fake")
    fake_audit = tmp_path / "fake_audit_deps.py"
    fake_audit.write_text("# fake audit")
    monkeypatch.setattr(hook, "_CHECKER", fake_checker)
    monkeypatch.setattr(hook, "_AUDIT_DEPS", fake_audit)
    rc = hook.run_post_test_checks(1)
    captured = capsys.readouterr()
    assert rc is True
    assert "[failed]" in captured.out
    assert "Recommendation:" in captured.out
    assert str(fake_audit) in captured.out


def test_post_test_failed_without_checker_silent(capsys, monkeypatch):
    """Covers line 57 False branch: _CHECKER doesn't exist → silent."""
    monkeypatch.setattr(hook, "_CHECKER", Path("/nonexistent/x.py"))
    rc = hook.run_post_test_checks(2)
    captured = capsys.readouterr()
    assert rc is True
    assert captured.out == ""


# ─── main() ─────────────────────────────────────────────────────────

def test_main_without_checker_hook_flag_exits_1(monkeypatch, capsys):
    """Covers line 64-66: --checker-hook missing → sys.exit(1)."""
    monkeypatch.setattr(sys, "argv", ["dev_pytest_hook.py"])
    with pytest.raises(SystemExit) as exc_info:
        hook.main()
    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "Usage:" in captured.out


def test_main_with_checker_hook_passes_exit_code_zero(monkeypatch, capsys):
    """Covers line 64 True branch + line 68-71 with exit_code=0 path.

    Mocks run_pre_test_checks and run_post_test_checks to be no-ops
    so we don't actually invoke subprocess.
    """
    monkeypatch.setattr(sys, "argv",
                        ["dev_pytest_hook.py", "--checker-hook", "0"])
    with mock.patch.object(hook, "run_pre_test_checks",
                           return_value=True), \
         mock.patch.object(hook, "run_post_test_checks",
                           return_value=True):
        hook.main()  # no SystemExit
    captured = capsys.readouterr()
    assert "Usage:" not in captured.out


def test_main_with_checker_hook_passes_nondigit_last_arg(
    monkeypatch, capsys
):
    """Covers line 70 else branch: last argv not digit → exit_code=0."""
    monkeypatch.setattr(sys, "argv",
                        ["dev_pytest_hook.py", "--checker-hook",
                         "some-other-arg"])
    with mock.patch.object(hook, "run_pre_test_checks",
                           return_value=True), \
         mock.patch.object(hook, "run_post_test_checks",
                           return_value=True):
        hook.main()
    captured = capsys.readouterr()
    assert "Usage:" not in captured.out


# ─── __main__ guard ─────────────────────────────────────────────────

def test_main_block_via_runpy_no_hook_flag(monkeypatch, capsys):
    """Covers lines 73-74: __main__ guard calls main().

    When --checker-hook is missing, main() exits 1, which propagates
    through runpy.
    """
    monkeypatch.setattr(sys, "argv", ["dev_pytest_hook.py"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(hook.__file__, run_name="__main__")
    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert "Usage:" in captured.out


def test_main_block_via_runpy_with_hook(monkeypatch, capsys):
    """Covers lines 73-74 + main() happy path via runpy."""
    monkeypatch.setattr(sys, "argv",
                        ["dev_pytest_hook.py", "--checker-hook", "0"])
    with mock.patch.object(hook, "run_pre_test_checks",
                           return_value=True), \
         mock.patch.object(hook, "run_post_test_checks",
                           return_value=True):
        # No SystemExit because main() doesn't sys.exit on success
        runpy.run_path(hook.__file__, run_name="__main__")
    captured = capsys.readouterr()
    assert "Usage:" not in captured.out
