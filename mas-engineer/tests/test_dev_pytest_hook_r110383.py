"""R110-383 — dev_pytest_hook.py 0% → 100% coverage push.

Module: tools/dev_pytest_hook.py (74 lines, 39 stmts, 3 top-level fns)
  - run_pre_test_checks()  → bool
  - run_post_test_checks(pytest_exit_code: int) → bool
  - main()                 → None (uses sys.exit)

Module-level constants (set at import time):
  - _HERE          = Path(__file__).resolve().parent  (line 19)
  - _CHECKER       = _HERE / "dev_rule_checker.py"     (line 20)
  - _AUDIT_DEPS    = _HERE / "dev_audit_deps.py"       (line 21)

Total: 5 TestClasses, ~25 test methods, 100% line+branch coverage.

Patterns applied per R110-375..R110-382 R-sprint precedent:
  - subprocess.run always mocked (we don't actually run dev_rule_checker)
  - All file-existence checks for _CHECKER / _AUDIT_DEPS tested by creating
    real files in tmp_path and temporarily monkeypatching _HERE
  - sys.argv + sys.stdout + sys.stderr monkeypatched for main()
  - print() output captured via monkeypatched sys.stdout
  - Return values checked (run_*_checks always returns True per source)
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Import the module-under-test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_pytest_hook


# ============================================================
# TestRunPreTestChecks
# ============================================================
class TestRunPreTestChecks:
    """run_pre_test_checks: invoke dev_rule_checker --health, warn on bad score."""

    def test_checker_not_found_returns_true(self, monkeypatch, tmp_path, capsys):
        """If _CHECKER doesn't exist → 'not found' message, returns True."""
        # Point _HERE at an empty dir so _CHECKER doesn't resolve
        fake_here = tmp_path / "empty_tools"
        fake_here.mkdir()
        monkeypatch.setattr(dev_pytest_hook, "_HERE", fake_here)
        # _CHECKER is computed at import time, so monkeypatch it directly
        fake_checker = fake_here / "dev_rule_checker.py"
        # Confirm it doesn't exist
        assert not fake_checker.exists()
        monkeypatch.setattr(dev_pytest_hook, "_CHECKER", fake_checker)

        result = dev_pytest_hook.run_pre_test_checks()
        # Per source: if not exists, return True
        assert result is True
        # Capture: 'DEV-CHECKER: not found (no Generic-Improver)' on stdout
        out = capsys.readouterr().out
        assert "not found" in out

    def test_checker_healthy_returns_true(self, monkeypatch, capsys):
        """Checker runs with rc=0 → 'Health OK' message, returns True."""
        # Mock subprocess.run to return rc=0
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        with patch("dev_pytest_hook.subprocess.run", return_value=mock_proc) as mock_run:
            result = dev_pytest_hook.run_pre_test_checks()
        assert result is True
        mock_run.assert_called_once()
        # The args should include --mode generic --health
        args = mock_run.call_args[0][0]
        assert "--mode" in args
        assert "generic" in args
        assert "--health" in args
        out = capsys.readouterr().out
        assert "Health OK" in out or "OK" in out

    def test_checker_unhealthy_low_score_warns(self, monkeypatch, capsys):
        """Checker rc≠0 + score<5 → 'Health-Check failed' + 'Rule-system ist schwach'."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = json.dumps({"score": 3})
        mock_proc.stderr = ""
        with patch("dev_pytest_hook.subprocess.run", return_value=mock_proc):
            result = dev_pytest_hook.run_pre_test_checks()
        # Per source: return True (only warn, don't block)
        assert result is True
        out = capsys.readouterr().out
        assert "Health-Check failed" in out
        assert "Rule-system ist schwach" in out
        # Score 3/10 is shown
        assert "3/10" in out

    def test_checker_unhealthy_high_score_warns_only(self, monkeypatch, capsys):
        """Checker rc≠0 + score≥5 → 'Health-Check failed' but no 'schwach'."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = json.dumps({"score": 7})
        mock_proc.stderr = ""
        with patch("dev_pytest_hook.subprocess.run", return_value=mock_proc):
            result = dev_pytest_hook.run_pre_test_checks()
        assert result is True
        out = capsys.readouterr().out
        assert "Health-Check failed" in out
        # Score 7 ≥ 5 → no 'schwach' message
        assert "schwach" not in out

    def test_checker_unhealthy_invalid_json_swallowed(self, monkeypatch, capsys):
        """Checker rc≠0 + invalid JSON → 'Health-Check failed' but no score line."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "{ not valid json"
        mock_proc.stderr = ""
        with patch("dev_pytest_hook.subprocess.run", return_value=mock_proc):
            result = dev_pytest_hook.run_pre_test_checks()
        # Per source: bare except → pass → no score line, no exception
        assert result is True
        out = capsys.readouterr().out
        assert "Health-Check failed" in out
        # No 'Score:' line because json.loads failed
        assert "Score:" not in out

    def test_checker_uses_str_executable(self, monkeypatch):
        """subprocess.run is called with sys.executable as the python."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        with patch("dev_pytest_hook.subprocess.run", return_value=mock_proc) as mock_run:
            dev_pytest_hook.run_pre_test_checks()
        args = mock_run.call_args[0][0]
        # First arg must be sys.executable
        assert args[0] == sys.executable
        # Second arg is the checker path
        assert str(dev_pytest_hook._CHECKER) in args[1]


# ============================================================
# TestRunPostTestChecks
# ============================================================
class TestRunPostTestChecks:
    """run_post_test_checks: print [failed] line + audit_deps recommendation if rc>0."""

    def test_zero_exit_code_silent(self, monkeypatch, capsys):
        """pytest_exit_code=0 → no output, returns True."""
        result = dev_pytest_hook.run_post_test_checks(0)
        assert result is True
        out = capsys.readouterr().out
        # No [failed] line, no recommendation
        assert "failed" not in out.lower()
        assert "Recommendation" not in out

    def test_positive_exit_code_with_checker_prints_recommendation(self, monkeypatch, tmp_path, capsys):
        """pytest_exit_code>0 + _CHECKER exists → [failed] + Recommendation + audit_deps path."""
        # Make _CHECKER exist
        fake_here = tmp_path / "tools_dir"
        fake_here.mkdir()
        checker = fake_here / "dev_rule_checker.py"
        checker.write_text("# fake\n")
        monkeypatch.setattr(dev_pytest_hook, "_HERE", fake_here)
        monkeypatch.setattr(dev_pytest_hook, "_CHECKER", checker)
        # _AUDIT_DEPS doesn't need to exist for the print (it's just embedded in f-string)
        monkeypatch.setattr(
            dev_pytest_hook, "_AUDIT_DEPS", fake_here / "dev_audit_deps.py"
        )

        result = dev_pytest_hook.run_post_test_checks(1)
        assert result is True
        out = capsys.readouterr().out
        # The [failed] line and the Recommendation line
        assert "[failed]" in out
        assert "Recommendation" in out
        assert "dev_audit_deps.py" in out
        # The recommendation includes --target .
        assert "--target" in out

    def test_positive_exit_code_without_checker_silent(self, monkeypatch, tmp_path, capsys):
        """pytest_exit_code>0 + _CHECKER missing → silent (the if guard skips)."""
        fake_here = tmp_path / "empty"
        fake_here.mkdir()
        fake_checker = fake_here / "dev_rule_checker.py"  # doesn't exist
        monkeypatch.setattr(dev_pytest_hook, "_HERE", fake_here)
        monkeypatch.setattr(dev_pytest_hook, "_CHECKER", fake_checker)
        assert not fake_checker.exists()

        result = dev_pytest_hook.run_post_test_checks(2)
        assert result is True
        out = capsys.readouterr().out
        # The if guard skips → no output
        assert "Recommendation" not in out
        assert "[failed]" not in out

    def test_always_returns_true_regardless_of_code(self, monkeypatch):
        """run_post_test_checks always returns True (per source)."""
        # Even with weird values like negative
        with patch("dev_pytest_hook._CHECKER", Path("/nonexistent")):
            assert dev_pytest_hook.run_post_test_checks(0) is True
            assert dev_pytest_hook.run_post_test_checks(1) is True
            assert dev_pytest_hook.run_post_test_checks(255) is True

    def test_post_test_uses_audited_deps_path(self, monkeypatch, tmp_path, capsys):
        """The audit_deps path printed uses _AUDIT_DEPS constant."""
        # Set a custom _AUDIT_DEPS path
        fake_here = tmp_path / "tools"
        fake_here.mkdir()
        checker = fake_here / "dev_rule_checker.py"
        checker.write_text("# fake\n")
        custom_audit = fake_here / "my_custom_audit.py"
        monkeypatch.setattr(dev_pytest_hook, "_HERE", fake_here)
        monkeypatch.setattr(dev_pytest_hook, "_CHECKER", checker)
        monkeypatch.setattr(dev_pytest_hook, "_AUDIT_DEPS", custom_audit)

        dev_pytest_hook.run_post_test_checks(1)
        out = capsys.readouterr().out
        assert "my_custom_audit.py" in out


# ============================================================
# TestMain
# ============================================================
class TestMain:
    """main(): dispatch on --checker-hook flag, pass exit code through."""

    def test_no_checker_hook_prints_usage_and_exits_1(self, monkeypatch, capsys):
        """No --checker-hook in argv → 'Usage:' printed, sys.exit(1)."""
        monkeypatch.setattr(sys, "argv", ["dev_pytest_hook.py"])
        with pytest.raises(SystemExit) as exc:
            dev_pytest_hook.main()
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Usage" in out
        assert "--checker-hook" in out

    def test_checker_hook_default_zero_exit(self, monkeypatch, capsys):
        """--checker-hook + no trailing int → exit_code=0, run_pre + run_post called."""
        # Mock both runners to avoid subprocess
        with patch.object(dev_pytest_hook, "run_pre_test_checks", return_value=True) as pre, \
             patch.object(dev_pytest_hook, "run_post_test_checks", return_value=True) as post:
            monkeypatch.setattr(sys, "argv", ["dev_pytest_hook.py", "--checker-hook"])
            # main() does NOT call sys.exit — it just returns
            dev_pytest_hook.main()
        pre.assert_called_once()
        post.assert_called_once_with(0)  # default exit code

    def test_checker_hook_with_explicit_zero(self, monkeypatch, capsys):
        """--checker-hook 0 → run_post_test_checks(0) called."""
        with patch.object(dev_pytest_hook, "run_pre_test_checks", return_value=True), \
             patch.object(dev_pytest_hook, "run_post_test_checks", return_value=True) as post:
            monkeypatch.setattr(sys, "argv", ["dev_pytest_hook.py", "--checker-hook", "0"])
            dev_pytest_hook.main()
        post.assert_called_once_with(0)

    def test_checker_hook_with_nonzero_exit(self, monkeypatch, capsys):
        """--checker-hook 5 → run_post_test_checks(5) called."""
        with patch.object(dev_pytest_hook, "run_pre_test_checks", return_value=True), \
             patch.object(dev_pytest_hook, "run_post_test_checks", return_value=True) as post:
            monkeypatch.setattr(sys, "argv", ["dev_pytest_hook.py", "--checker-hook", "5"])
            dev_pytest_hook.main()
        post.assert_called_once_with(5)

    def test_checker_hook_with_non_digit_trailing_arg_defaults_zero(self, monkeypatch, capsys):
        """--checker-hook foo (non-digit) → exit_code defaults to 0."""
        with patch.object(dev_pytest_hook, "run_pre_test_checks", return_value=True), \
             patch.object(dev_pytest_hook, "run_post_test_checks", return_value=True) as post:
            monkeypatch.setattr(sys, "argv", ["dev_pytest_hook.py", "--checker-hook", "foo"])
            dev_pytest_hook.main()
        # Source: int(sys.argv[-1]) if isdigit() else 0
        post.assert_called_once_with(0)

    def test_checker_hook_runs_pre_before_post(self, monkeypatch, capsys):
        """run_pre_test_checks is called BEFORE run_post_test_checks (order matters)."""
        call_order = []
        def fake_pre():
            call_order.append("pre")
            return True
        def fake_post(code):
            call_order.append(f"post:{code}")
            return True
        monkeypatch.setattr(dev_pytest_hook, "run_pre_test_checks", fake_pre)
        monkeypatch.setattr(dev_pytest_hook, "run_post_test_checks", fake_post)
        monkeypatch.setattr(sys, "argv", ["dev_pytest_hook.py", "--checker-hook", "3"])
        dev_pytest_hook.main()
        assert call_order == ["pre", "post:3"]


# ============================================================
# TestModulePathAnchoring
# ============================================================
class TestModulePathAnchoring:
    """Verify _HERE / _CHECKER / _AUDIT_DEPS are anchored to the script's directory."""

    def test_HERE_anchored_to_script_dir(self):
        """_HERE = Path(__file__).resolve().parent."""
        expected = Path(dev_pytest_hook.__file__).resolve().parent
        assert dev_pytest_hook._HERE == expected

    def test_CHECKER_path_under_tools_dir(self):
        """_CHECKER = _HERE / 'dev_rule_checker.py'."""
        expected = dev_pytest_hook._HERE / "dev_rule_checker.py"
        assert dev_pytest_hook._CHECKER == expected

    def test_AUDIT_DEPS_path_under_tools_dir(self):
        """_AUDIT_DEPS = _HERE / 'dev_audit_deps.py'."""
        expected = dev_pytest_hook._HERE / "dev_audit_deps.py"
        assert dev_pytest_hook._AUDIT_DEPS == expected

    def test_subprocess_uses_string_path(self, monkeypatch):
        """The path passed to subprocess.run is stringified (subprocess needs str)."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        with patch("dev_pytest_hook.subprocess.run", return_value=mock_proc) as mock_run:
            dev_pytest_hook.run_pre_test_checks()
        args = mock_run.call_args[0][0]
        # The 2nd arg (checker path) should be a string, not a Path
        assert isinstance(args[1], str)


# ============================================================
# TestPreTestChecksMessagingEmojis
# ============================================================
class TestPreTestChecksMessagingEmojis:
    """Verify the emoji-prefixed messages in run_pre_test_checks."""

    def test_not_found_message_has_no_emoji(self, monkeypatch, tmp_path, capsys):
        """The 'not found' branch has no emoji (plain text)."""
        fake_here = tmp_path / "empty"
        fake_here.mkdir()
        fake_checker = fake_here / "dev_rule_checker.py"
        monkeypatch.setattr(dev_pytest_hook, "_CHECKER", fake_checker)
        dev_pytest_hook.run_pre_test_checks()
        out = capsys.readouterr().out
        assert "DEV-CHECKER: not found" in out
        # No checkmark or warning emoji in the not-found branch
        assert "✅" not in out
        assert "⚠" not in out

    def test_healthy_message_has_checkmark(self, monkeypatch, capsys):
        """Healthy branch has ✅ checkmark."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        with patch("dev_pytest_hook.subprocess.run", return_value=mock_proc):
            dev_pytest_hook.run_pre_test_checks()
        out = capsys.readouterr().out
        assert "✅" in out

    def test_unhealthy_message_has_warning_emoji(self, monkeypatch, capsys):
        """Unhealthy branch has ⚠️ warning emoji."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = json.dumps({"score": 3})
        mock_proc.stderr = ""
        with patch("dev_pytest_hook.subprocess.run", return_value=mock_proc):
            dev_pytest_hook.run_pre_test_checks()
        out = capsys.readouterr().out
        assert "⚠" in out
