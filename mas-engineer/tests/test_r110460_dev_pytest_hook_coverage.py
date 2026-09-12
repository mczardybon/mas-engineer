"""R110-460 — coverage-push r8: tools/dev_pytest_hook.py 0% → 100%.

Pytest-Checker-Hook. CLI: --checker-hook [pytest_exit_code].

Targets:
- run_pre_test_checks():
  - checker missing → print "not found" + return True
  - checker runs, rc != 0 → print warning + parse stdout
    as JSON. If data['score']<5 → print score message.
    On JSON parse error → silent. Return True (warn only).
  - checker runs, rc == 0 → print success + return True

- run_post_test_checks(pytest_exit_code):
  - exit_code > 0 + checker exists → print "[failed]"
    recommendation with audit_deps command
  - exit_code > 0 + checker missing → no output
  - exit_code == 0 → no output
  - always returns True

- main():
  - no --checker-hook in argv → usage + sys.exit(1)
  - else: run_pre + extract exit_code from last arg if digit
    else 0 + run_post
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import tools.dev_pytest_hook as ph  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# run_pre_test_checks — checker missing
# ─────────────────────────────────────────────────────────────────────
class TestPreCheckerMissing:
    def test_missing_returns_true(self, monkeypatch, tmp_path,
                                    capsys):
        # Point _CHECKER at a non-existent file
        monkeypatch.setattr(ph, "_CHECKER",
                            tmp_path / "no_such_checker.py")
        r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        assert "not found" in out


# ─────────────────────────────────────────────────────────────────────
# run_pre_test_checks — checker healthy
# ─────────────────────────────────────────────────────────────────────
class TestPreCheckerHealthy:
    def test_healthy_returns_true(self, monkeypatch, capsys):
        # Make _CHECKER exist
        checker = ph._HERE / "_fake_checker.py"
        checker.write_text("")
        monkeypatch.setattr(ph, "_CHECKER", checker)
        # Patch subprocess.run to return rc=0
        class FakeResult:
            returncode = 0
            stdout = '{"score": 8}'
            stderr = ""
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **kw: FakeResult())
        r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        # Source has typo "Heoldh" — match actual output
        assert "Heoldh OK" in out
        checker.unlink(missing_ok=True)

    def test_healthy_real_checker(self, tmp_path, capsys):
        # Use the actual dev_rule_checker.py if present
        r = ph.run_pre_test_checks()
        assert r is True


# ─────────────────────────────────────────────────────────────────────
# run_pre_test_checks — checker fails
# ─────────────────────────────────────────────────────────────────────
class TestPreCheckerFail:
    def test_fail_low_score(self, monkeypatch, capsys):
        checker = ph._HERE / "_fake_checker2.py"
        checker.write_text("")
        monkeypatch.setattr(ph, "_CHECKER", checker)
        class FakeResult:
            returncode = 1
            stdout = json.dumps({"score": 3})
            stderr = ""
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **kw: FakeResult())
        r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        assert "Health-Check failed" in out
        assert "Score: 3/10" in out
        checker.unlink(missing_ok=True)

    def test_fail_high_score(self, monkeypatch, capsys):
        # Fail (rc!=0) but score >=5 → no score message
        checker = ph._HERE / "_fake_checker3.py"
        checker.write_text("")
        monkeypatch.setattr(ph, "_CHECKER", checker)
        class FakeResult:
            returncode = 1
            stdout = json.dumps({"score": 7})
            stderr = ""
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **kw: FakeResult())
        r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        assert "Health-Check failed" in out
        assert "Score" not in out
        checker.unlink(missing_ok=True)

    def test_fail_invalid_json(self, monkeypatch, capsys):
        # Fail + non-JSON stdout → silent parse error
        checker = ph._HERE / "_fake_checker4.py"
        checker.write_text("")
        monkeypatch.setattr(ph, "_CHECKER", checker)
        class FakeResult:
            returncode = 1
            stdout = "not json"
            stderr = ""
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **kw: FakeResult())
        r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        assert "Health-Check failed" in out
        # No crash, no score message
        checker.unlink(missing_ok=True)

    def test_fail_score_key_missing(self, monkeypatch, capsys):
        # JSON without 'score' → defaults to 10 → no score message
        checker = ph._HERE / "_fake_checker5.py"
        checker.write_text("")
        monkeypatch.setattr(ph, "_CHECKER", checker)
        class FakeResult:
            returncode = 1
            stdout = '{"other": 1}'
            stderr = ""
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **kw: FakeResult())
        r = ph.run_pre_test_checks()
        assert r is True
        out = capsys.readouterr().out
        assert "Health-Check failed" in out
        assert "Score" not in out
        checker.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────
# run_post_test_checks
# ─────────────────────────────────────────────────────────────────────
class TestPost:
    def test_zero_exit_no_output(self, capsys):
        r = ph.run_post_test_checks(0)
        assert r is True
        assert capsys.readouterr().out == ""

    def test_positive_exit_no_checker(self, monkeypatch, capsys,
                                          tmp_path):
        monkeypatch.setattr(ph, "_CHECKER",
                            tmp_path / "no_checker.py")
        r = ph.run_post_test_checks(1)
        assert r is True
        # No "[failed]" because checker doesn't exist
        assert "[failed]" not in capsys.readouterr().out

    def test_positive_exit_with_checker(self, monkeypatch, capsys,
                                           tmp_path):
        # Make _CHECKER exist
        fake = tmp_path / "exists.py"
        fake.write_text("")
        monkeypatch.setattr(ph, "_CHECKER", fake)
        # _AUDIT_DEPS stays the real value (dev_audit_deps.py) so
        # the printed path contains 'dev_audit_deps' substring
        r = ph.run_post_test_checks(1)
        assert r is True
        out = capsys.readouterr().out
        assert "[failed]" in out
        assert "Recommendation:" in out
        # Source prints: f"  python3 {_AUDIT_DEPS} --target ."
        # _AUDIT_DEPS is tools/dev_audit_deps.py
        assert "dev_audit_deps.py" in out

    def test_positive_exit_real_checker(self, capsys):
        # Uses real _CHECKER (dev_rule_checker.py exists)
        r = ph.run_post_test_checks(5)
        assert r is True
        out = capsys.readouterr().out
        assert "[failed]" in out


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_checker_hook_exits_1(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["x"])
        with pytest.raises(SystemExit) as exc:
            ph.main()
        assert exc.value.code == 1

    def test_checker_hook_no_exit_code(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["x", "--checker-hook"])
        # Run pre (real) — prints health-check
        # Then post with exit_code=0 (default) → no output
        ph.main()
        out = capsys.readouterr().out
        # No "[failed]" since exit_code is 0
        assert "[failed]" not in out

    def test_checker_hook_with_exit_code(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv",
                            ["x", "--checker-hook", "1"])
        ph.main()
        out = capsys.readouterr().out
        assert "[failed]" in out

    def test_checker_hook_with_nondigit_arg(self, monkeypatch,
                                              capsys):
        # Last arg not digit → exit_code = 0
        monkeypatch.setattr(sys, "argv",
                            ["x", "--checker-hook", "abc"])
        ph.main()
        out = capsys.readouterr().out
        assert "[failed]" not in out

    def test_checker_hook_only_two_args(self, monkeypatch, capsys):
        # Exactly 2 args → len(argv) > 2 False → exit_code = 0
        monkeypatch.setattr(sys, "argv",
                            ["x", "--checker-hook"])
        ph.main()


# ─────────────────────────────────────────────────────────────────────
# CLI subprocess (covers __main__)
# ─────────────────────────────────────────────────────────────────────
class TestCli:
    def test_no_checker_hook_cli(self):
        r = subprocess.run(
            ['python3', 'tools/dev_pytest_hook.py'],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        assert r.returncode == 1
        assert "Usage:" in r.stdout

    def test_checker_hook_cli(self):
        r = subprocess.run(
            ['python3', 'tools/dev_pytest_hook.py',
             '--checker-hook', '1'],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        # Doesn't exit 1 because --checker-hook present
        assert r.returncode == 0
        assert "[failed]" in r.stdout
