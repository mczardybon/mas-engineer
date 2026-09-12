"""R110-445 — coverage-push r8: tools/dev_pytest_hook.py 0% → 100%.

Pytest checker-hook (74 lines). Pre-test health + post-test failure
recommendation.

Targets:
- run_pre_test_checks: dev_rule_checker.py missing → print
  "not found" + return True (don't block); checker exists with
  non-zero exit → score<5 prints warning + return True; checker
  exists with non-zero exit + non-JSON output → except → return
  True; checker exists with zero exit → "Health OK" + return True
- run_post_test_checks: pytest_exit_code == 0 → no output, True;
  pytest_exit_code > 0 + _CHECKER missing → no output, True;
  pytest_exit_code > 0 + _CHECKER present → prints "[failed]"
  + Recommendation + audit_deps path
- main: --checker-hook in sys.argv → runs pre + post; missing
  → prints usage + exits 1
"""

import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_pytest_hook as ph  # noqa: E402


@pytest.fixture
def checker_present(tmp_path, monkeypatch):
    """Create a fake dev_rule_checker.py so _CHECKER.exists() = True."""
    fake_checker = tmp_path / "dev_rule_checker.py"
    fake_checker.write_text("# stub")
    fake_audit = tmp_path / "dev_audit_deps.py"
    fake_audit.write_text("# stub")
    # Monkey-patch _CHECKER and _AUDIT_DEPS in module
    monkeypatch.setattr(ph, "_CHECKER", fake_checker)
    monkeypatch.setattr(ph, "_AUDIT_DEPS", fake_audit)


# ─────────────────────────────────────────────────────────────────────
# run_pre_test_checks
# ─────────────────────────────────────────────────────────────────────
class TestRunPreTestChecks:
    def test_checker_missing(self, tmp_path, monkeypatch, capsys):
        # No checker file in tmp_path → exists() False
        monkeypatch.setattr(ph, "_CHECKER",
                            tmp_path / "nope.py")
        r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        assert "not found" in out

    def test_checker_returns_zero(self, checker_present, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch.object(subprocess, "run",
                          return_value=mock_result) as mock_run:
            r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        assert "Health OK" in out or "✅" in out
        # Verify subprocess.run called with expected args
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "--health" in args
        assert "--mode" in args

    def test_checker_returns_nonzero_low_score(self, checker_present,
                                                 capsys):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = '{"score": 3}'
        with patch.object(subprocess, "run", return_value=mock_result):
            r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        assert "failed" in out or "⚠" in out
        assert "3" in out

    def test_checker_returns_nonzero_high_score(self, checker_present,
                                                  capsys):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = '{"score": 9}'
        with patch.object(subprocess, "run", return_value=mock_result):
            r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        # High score → no "Rule-system ist schwach" message
        assert "schwach" not in out

    def test_checker_returns_nonzero_invalid_json(self,
                                                    checker_present,
                                                    capsys):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "not json"
        with patch.object(subprocess, "run", return_value=mock_result):
            r = ph.run_pre_test_checks()
        # Exception caught → return True
        assert r is True


# ─────────────────────────────────────────────────────────────────────
# run_post_test_checks
# ─────────────────────────────────────────────────────────────────────
class TestRunPostTestChecks:
    def test_zero_exit_no_output(self, capsys):
        r = ph.run_post_test_checks(0)
        assert r is True
        assert capsys.readouterr().out == ""

    def test_failed_exit_no_checker(self, tmp_path, monkeypatch,
                                      capsys):
        monkeypatch.setattr(ph, "_CHECKER", tmp_path / "nope.py")
        r = ph.run_post_test_checks(1)
        assert r is True
        # No output because checker doesn't exist
        assert capsys.readouterr().out == ""

    def test_failed_exit_with_checker(self, checker_present, capsys):
        r = ph.run_post_test_checks(1)
        assert r is True
        out = capsys.readouterr().out
        assert "[failed]" in out
        assert "Recommendation" in out
        assert "dev_audit_deps" in out

    def test_higher_exit_code(self, checker_present, capsys):
        r = ph.run_post_test_checks(5)
        assert r is True
        out = capsys.readouterr().out
        assert "[failed]" in out


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_missing_flag_exits_1(self, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_pytest_hook.py"]
        code = 0
        try:
            try:
                ph.main()
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        assert code == 1
        err = capsys.readouterr().out
        assert "Usage" in err

    def test_with_flag_no_fail(self, checker_present, monkeypatch,
                                  capsys):
        # Mock pre + post to avoid subprocess
        monkeypatch.setattr(ph, "run_pre_test_checks",
                            lambda: True)
        monkeypatch.setattr(ph, "run_post_test_checks",
                            lambda code: True)
        old_argv = sys.argv
        sys.argv = ["dev_pytest_hook.py", "--checker-hook", "0"]
        try:
            ph.main()
        finally:
            sys.argv = old_argv

    def test_with_flag_and_exit_code(self, checker_present,
                                       monkeypatch, capsys):
        pre_calls = []
        post_calls = []
        monkeypatch.setattr(ph, "run_pre_test_checks",
                            lambda: pre_calls.append(True) or True)
        monkeypatch.setattr(ph, "run_post_test_checks",
                            lambda code: post_calls.append(code) or True)
        old_argv = sys.argv
        sys.argv = ["dev_pytest_hook.py", "--checker-hook", "5"]
        try:
            ph.main()
        finally:
            sys.argv = old_argv
        assert len(pre_calls) == 1
        assert post_calls == [5]

    def test_with_flag_no_exit_code_arg(self, checker_present,
                                          monkeypatch, capsys):
        # argv length > 2 but last arg not digit
        pre_called = []
        post_called = []
        monkeypatch.setattr(ph, "run_pre_test_checks",
                            lambda: pre_called.append(True) or True)
        monkeypatch.setattr(ph, "run_post_test_checks",
                            lambda code: post_called.append(code) or True)
        old_argv = sys.argv
        sys.argv = ["dev_pytest_hook.py", "--checker-hook", "somename"]
        try:
            ph.main()
        finally:
            sys.argv = old_argv
        # post called with default 0
        assert post_called == [0]


# ─────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_calls_main(self, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_pytest_hook.py"]
        code = 0
        try:
            try:
                exec(compile(Path(__file__).resolve().parents[1]
                             .joinpath("tools/dev_pytest_hook.py")
                             .read_text(),
                             "dev_pytest_hook.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_pytest_hook.py",
                      "sys": sys,
                      "Path": Path,
                      "subprocess": subprocess})
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        assert code == 1
