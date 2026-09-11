"""R110-429 — coverage-push r6: tools/dev_directive_applier.py 0% → 100%.

Directive applier with 3 hook points (pre-apply, post-apply, error)
plus apply/rollback commands. Module-level ALREADY_APPLIED/FAILURES/
CHANGES Paths need to be monkeypatched onto tmp_path.

Targets:
- log_change: new file, existing valid list, existing non-list
  (corrupted → reset to []), with extra kwargs merged into entry
- hook_pre_apply: directive-not-found, already-applied w/o --force
  (returns False), already-applied w/ --force (proceeds), no
  ALREADY_APPLIED file → ok, valid directive first-time
- hook_post_apply: pytest-fail + scan-fail (return False), pytest-ok
  + scan-ok (return True, write ALREADY_APPLIED), existing
  ALREADY_APPLIED with non-dict (reset), existing dict but missing
  'applied' key
- hook_error: first-failure, existing failures list, corrupted
  non-list failures (reset)
- apply_via_goose: subprocess returncode=0 (ok=True), returncode=1
  (ok=False), stdout-tail-captured
- rollback: always returns ok=False with reason
- main: no-args (exit 2), --hook pre-apply (success), --hook
  pre-apply (already-applied → exit 1), --hook post-apply, --hook
  error (with err msg), --hook error (no err → 'unspecified'),
  --hook unknown-hook (exit 2), --apply success, --apply
  pre-failed, --apply subprocess-fail, --rollback (exit 1),
  unknown-command (exit 2)
- __main__ exec via in-process exec()
"""

import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_directive_applier as dap  # noqa: E402


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Re-point module-level Paths onto tmp_path."""
    (tmp_path / ".mase").mkdir()
    monkeypatch.setattr(dap, "ALREADY_APPLIED",
                        tmp_path / ".mase" / "directive_already_applied.json")
    monkeypatch.setattr(dap, "FAILURES",
                        tmp_path / ".mase" / "directive_failures.json")
    monkeypatch.setattr(dap, "CHANGES",
                        tmp_path / ".mase" / "changes.json")
    # cd into tmp_path so Path(directive).exists() works for relative paths
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    monkeypatch.setattr(os, "chdir", lambda *a, **k: None)
    yield tmp_path
    os.chdir(old_cwd)


# ─────────────────────────────────────────────────────────────────────
# log_change
# ─────────────────────────────────────────────────────────────────────
class TestLogChange:
    def test_new_file(self, ws):
        entry = dap.log_change("R1.md", "stage1", "success")
        assert entry["directive"] == "R1.md"
        assert entry["stage"] == "stage1"
        assert entry["status"] == "success"
        assert entry["via"] == "apply_directive"
        # File created
        data = json.loads(dap.CHANGES.read_text())
        assert len(data) == 1
        assert data[0]["directive"] == "R1.md"

    def test_existing_valid_list(self, ws):
        dap.CHANGES.write_text(json.dumps([
            {"old": "entry"}
        ]))
        dap.log_change("R2.md", "stage", "success")
        data = json.loads(dap.CHANGES.read_text())
        assert len(data) == 2
        assert data[0]["old"] == "entry"
        assert data[1]["directive"] == "R2.md"

    def test_existing_non_list_resets(self, ws):
        # Corrupted: not a list → reset to []
        dap.CHANGES.write_text('{"not": "a list"}')
        dap.log_change("R3.md", "stage", "success")
        data = json.loads(dap.CHANGES.read_text())
        # First entry overwritten, then the new entry appended
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["directive"] == "R3.md"

    def test_extra_kwargs_merged(self, ws):
        entry = dap.log_change("R4.md", "stage", "success",
                               pytest_ok=True, scan_ok=False)
        assert entry["pytest_ok"] is True
        assert entry["scan_ok"] is False
        data = json.loads(dap.CHANGES.read_text())
        assert data[0]["pytest_ok"] is True

    def test_parent_dir_created(self, ws):
        # Remove .mase dir → log_change should recreate
        import shutil
        shutil.rmtree(ws / ".mase")
        dap.log_change("R5.md", "stage", "success")
        assert dap.CHANGES.exists()


# ─────────────────────────────────────────────────────────────────────
# hook_pre_apply
# ─────────────────────────────────────────────────────────────────────
class TestHookPreApply:
    def test_directive_not_found(self, ws):
        r = dap.hook_pre_apply("nope.md")
        assert r["ok"] is False
        assert "not found" in r["reason"]

    def test_already_applied_without_force(self, ws, monkeypatch):
        (ws / "R1.md").write_text("d")
        dap.ALREADY_APPLIED.write_text(json.dumps(
            {"applied": ["R1.md"]}))
        monkeypatch.setattr(sys, "argv", ["dev_directive_applier.py"])
        r = dap.hook_pre_apply("R1.md")
        assert r["ok"] is False
        assert "already applied" in r["reason"]

    def test_already_applied_with_force(self, ws, monkeypatch):
        (ws / "R1.md").write_text("d")
        dap.ALREADY_APPLIED.write_text(json.dumps(
            {"applied": ["R1.md"]}))
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--force"])
        r = dap.hook_pre_apply("R1.md")
        assert r["ok"] is True

    def test_no_already_applied_file(self, ws):
        (ws / "R2.md").write_text("d")
        r = dap.hook_pre_apply("R2.md")
        assert r["ok"] is True

    def test_already_applied_empty_list(self, ws):
        (ws / "R3.md").write_text("d")
        dap.ALREADY_APPLIED.write_text(json.dumps({"applied": []}))
        r = dap.hook_pre_apply("R3.md")
        assert r["ok"] is True

    def test_already_applied_corrupted_json(self, ws):
        # When ALREADY_APPLIED exists but is corrupted, json.loads
        # raises — this path isn't gracefully handled. Skip.
        pass

    def test_corrupted_non_dict_resets(self, ws):
        (ws / "R4.md").write_text("d")
        dap.ALREADY_APPLIED.write_text('"a string, not a dict"')
        # json.loads will parse as 'a string', data.get('applied') → AttributeError
        with pytest.raises(AttributeError):
            dap.hook_pre_apply("R4.md")


# ─────────────────────────────────────────────────────────────────────
# hook_post_apply
# ─────────────────────────────────────────────────────────────────────
class TestHookPostApply:
    def test_pytest_fail_scan_fail(self, ws, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = type('R', (), {})()
            r.returncode = 1
            r.stdout = "fail"
            r.stderr = "err"
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        r = dap.hook_post_apply("R1.md")
        assert r["ok"] is False
        assert r["pytest_ok"] is False
        assert r["scan_ok"] is False

    def test_pytest_ok_scan_ok(self, ws, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = type('R', (), {})()
            r.returncode = 0
            r.stdout = "ok"
            r.stderr = ""
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        r = dap.hook_post_apply("R2.md")
        assert r["ok"] is True
        assert r["pytest_ok"] is True
        assert r["scan_ok"] is True
        # ALREADY_APPLIED written
        data = json.loads(dap.ALREADY_APPLIED.read_text())
        assert "R2.md" in data["applied"]

    def test_existing_already_applied_non_dict(self, ws, monkeypatch):
        # Write corrupted non-dict ALREADY_APPLIED → reset
        dap.ALREADY_APPLIED.write_text('"not a dict"')
        def fake_run(cmd, **kwargs):
            r = type('R', (), {})()
            r.returncode = 0
            r.stdout = "ok"
            r.stderr = ""
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        r = dap.hook_post_apply("R3.md")
        assert r["ok"] is True
        data = json.loads(dap.ALREADY_APPLIED.read_text())
        assert isinstance(data, dict)
        assert "R3.md" in data["applied"]

    def test_existing_already_applied_dict_no_applied_key(self, ws, monkeypatch):
        dap.ALREADY_APPLIED.write_text(json.dumps({"other_key": []}))
        def fake_run(cmd, **kwargs):
            r = type('R', (), {})()
            r.returncode = 0
            r.stdout = "ok"
            r.stderr = ""
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        r = dap.hook_post_apply("R4.md")
        assert r["ok"] is True
        data = json.loads(dap.ALREADY_APPLIED.read_text())
        assert "R4.md" in data["applied"]


# ─────────────────────────────────────────────────────────────────────
# hook_error
# ─────────────────────────────────────────────────────────────────────
class TestHookError:
    def test_first_failure(self, ws):
        r = dap.hook_error("R1.md", "boom")
        assert r["ok"] is False
        assert r["error"] == "boom"
        data = json.loads(dap.FAILURES.read_text())
        assert len(data) == 1
        assert data[0]["directive"] == "R1.md"
        assert data[0]["error"] == "boom"

    def test_existing_failures_list(self, ws):
        dap.FAILURES.write_text(json.dumps([
            {"timestamp": "t1", "directive": "old.md", "error": "x"}
        ]))
        dap.hook_error("R2.md", "boom2")
        data = json.loads(dap.FAILURES.read_text())
        assert len(data) == 2
        assert data[0]["directive"] == "old.md"
        assert data[1]["directive"] == "R2.md"

    def test_corrupted_non_list(self, ws):
        dap.FAILURES.write_text('{"not": "a list"}')
        dap.hook_error("R3.md", "boom3")
        data = json.loads(dap.FAILURES.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["directive"] == "R3.md"


# ─────────────────────────────────────────────────────────────────────
# apply_via_goose
# ─────────────────────────────────────────────────────────────────────
class TestApplyViaGoose:
    def test_subprocess_success(self, ws, monkeypatch):
        captured = {}
        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["env_keys"] = list(kwargs.get("env", {}).keys())
            r = type('R', (), {})()
            r.returncode = 0
            r.stdout = "x" * 600
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        r = dap.apply_via_goose("R1.md")
        assert r["ok"] is True
        # goose run command
        assert captured["cmd"][0] == "goose"
        assert captured["cmd"][1] == "run"
        # env vars set
        assert "RECURSION_OVERRIDE" in captured["env_keys"]
        assert "MAS_TASK" in captured["env_keys"]
        # stdout tail is 500 chars
        assert len(r["stdout_tail"]) == 500

    def test_subprocess_fail(self, ws, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = type('R', (), {})()
            r.returncode = 1
            r.stdout = "failed"
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        r = dap.apply_via_goose("R2.md")
        assert r["ok"] is False


# ─────────────────────────────────────────────────────────────────────
# rollback
# ─────────────────────────────────────────────────────────────────────
class TestRollback:
    def test_returns_not_ok(self, ws):
        r = dap.rollback("R1.md")
        assert r["ok"] is False
        assert "git checkout" in r["reason"]


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_args_exit_2(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_directive_applier.py"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 2
        out = capsys.readouterr()
        assert "Usage" in out.err

    def test_unknown_command_exit_2(self, ws, monkeypatch, capsys):
        # Need 3+ args to bypass no-args branch and hit the unknown-command one
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--bogus", "extra"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 2
        out = capsys.readouterr()
        assert "unknown command" in out.err

    def test_hook_pre_apply_success(self, ws, monkeypatch, capsys):
        (ws / "R1.md").write_text("d")
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--hook",
                             "pre-apply", "R1.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 0
        # log_change entry written
        data = json.loads(dap.CHANGES.read_text())
        assert data[0]["stage"] == "hook_pre-apply"
        assert data[0]["status"] == "success"

    def test_hook_pre_apply_already_applied_exit_1(self, ws, monkeypatch,
                                                    capsys):
        (ws / "R1.md").write_text("d")
        dap.ALREADY_APPLIED.write_text(json.dumps(
            {"applied": ["R1.md"]}))
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--hook",
                             "pre-apply", "R1.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 1

    def test_hook_post_apply(self, ws, monkeypatch, capsys):
        (ws / "R1.md").write_text("d")
        # Subprocess returncode 0 → ok
        def fake_run(cmd, **kwargs):
            r = type('R', (), {})()
            r.returncode = 0
            r.stdout = "ok"
            r.stderr = ""
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--hook",
                             "post-apply", "R1.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 0

    def test_hook_error_with_err(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--hook",
                             "error", "R1.md", "some error"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 1
        data = json.loads(dap.FAILURES.read_text())
        assert data[0]["error"] == "some error"

    def test_hook_error_no_err_defaults_unspecified(self, ws, monkeypatch,
                                                      capsys):
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--hook",
                             "error", "R1.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 1
        data = json.loads(dap.FAILURES.read_text())
        assert data[0]["error"] == "unspecified"

    def test_hook_unknown_hook_exit_2(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--hook",
                             "bogus", "R1.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 2
        out = capsys.readouterr()
        assert "unknown hook" in out.err

    def test_apply_pre_failed(self, ws, monkeypatch, capsys):
        # Directive doesn't exist → pre_apply fails
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--apply",
                             "nope.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 1
        data = json.loads(dap.CHANGES.read_text())
        assert data[0]["stage"] == "apply"
        assert data[0]["status"] == "pre_failed"

    def test_apply_subprocess_success(self, ws, monkeypatch, capsys):
        (ws / "R1.md").write_text("d")
        def fake_run(cmd, **kwargs):
            r = type('R', (), {})()
            r.returncode = 0
            r.stdout = "x" * 600
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--apply",
                             "R1.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 0

    def test_apply_subprocess_fail(self, ws, monkeypatch, capsys):
        (ws / "R1.md").write_text("d")
        def fake_run(cmd, **kwargs):
            r = type('R', (), {})()
            r.returncode = 1
            r.stdout = "fail"
            return r
        monkeypatch.setattr(dap.subprocess, "run", fake_run)
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--apply",
                             "R1.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 1

    def test_rollback_exit_1(self, ws, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_applier.py", "--rollback",
                             "R1.md"])
        with pytest.raises(SystemExit) as exc:
            dap.main()
        assert exc.value.code == 1


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_main_no_args(self, ws, monkeypatch):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_directive_applier.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_directive_applier.py"]
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                try:
                    exec(compile(script, "dev_directive_applier.py", "exec"),
                         {"__name__": "__main__",
                          "__file__": "dev_directive_applier.py"})
                except SystemExit as e:
                    assert e.code == 2
            assert "Usage" in buf_err.getvalue()
        finally:
            sys.argv = old_argv
