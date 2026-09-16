"""Tests for tools/dev_gatekeeper.py — `check_responsibility_matrix()` + `main()`.

Coverage gap closer for the previously-uncovered ~85 stmts:
- check_responsibility_matrix() — 6 return paths (error/self via read_exception/
  self via load/delegate/delegate via file_map/delegate via action_map/blocked)
- main() — argparse parsing for --check-lock and --check-matrix, full rule
  dispatch loop (R01, R18, R19, R20, R10, R05) with mixed pass/fail, --stdin,
  --before/--after edit path, shell subprocess dispatch, and unknown-action /
  missing-args / missing-before-after error branches.

All state files are redirected via the `isolated_state` fixture from
test_dev_gatekeeper_coverage.py's pattern (monkeypatch the module-level
constants) so this file is safe to run without affecting the live .mase/ dir.

The `tmp_matrix` fixture writes a temp responsibility_matrix.yaml into the
caller's CWD so `check_responsibility_matrix()` picks it up via the
matrix_path = "mas-engineer/.mase/rules/..." lookup. We monkeypatch
`os.getcwd` so we don't need to chdir.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_gatekeeper as gk


# --- shared fixtures --------------------------------------------------------

@pytest.fixture
def isolated_state(monkeypatch, tmp_path):
    """Redirect gk.STATE_DIR/AUDIT_file/LOCK_file/CONFIRMATION_file to tmp_path."""
    state = tmp_path / ".mase"
    state.mkdir()
    monkeypatch.setattr(gk, "STATE_DIR", str(state))
    monkeypatch.setattr(gk, "AUDIT_file", str(state / "audit.log.jsonl"))
    monkeypatch.setattr(gk, "LOCK_file", str(state / ".disziplin_lock"))
    monkeypatch.setattr(gk, "CONFIRMATION_file", str(state / ".last_confirmation"))
    return state


@pytest.fixture
def tmp_matrix(tmp_path, monkeypatch):
    """Write a minimal responsibility_matrix.yaml and have os.getcwd() return its parent.

    check_responsibility_matrix() builds matrix_path from os.getcwd() + "mas-engineer/.mase/...".
    To avoid changing the real CWD we monkeypatch os.getcwd AND create the expected
    path under tmp_path.
    """
    cwd = tmp_path
    # The function does: os.path.join(os.getcwd(), "mas-engineer", ".mase", "rules", "responsibility_matrix.yaml")
    rules_dir = cwd / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    matrix_file = rules_dir / "responsibility_matrix.yaml"
    matrix_file.write_text(
        "version: 1.0.0\n"
        "read_exceptions:\n"
        "  - action: shell\n"
        "    cmds: [ls, cat, grep, find]\n"
        "file_map:\n"
        "  mas-engineer/tools/:\n"
        "    py_edit: sub_mas-python-repair\n"
        "  mas-engineer/.mase/rules/:\n"
        "    yaml_edit: sub_mas-yaml-editor\n"
        "action_map:\n"
        "  build:\n"
        "    agent: sub_mas-recipe-manager\n"
        "    task: BUILD\n"
        "  doc_edit:\n"
        "    agent: null\n"
        "  shell_write:\n"
        "    agent: sub_mas-git-operator\n"
        "    task: COMMIT\n"
        "  load:\n"
        "    agent: null\n"
        "  delegate:\n"
        "    agent: null\n"
    )
    monkeypatch.setattr(os, "getcwd", lambda: str(cwd))
    return matrix_file


# --- check_responsibility_matrix() tests ------------------------------------

def test_matrix_file_missing_returns_error(isolated_state, tmp_path, monkeypatch):
    """Covers lines 116-120: matrix_path does not exist → ('error', None, 'Matrix not found')."""
    # Point os.getcwd() at a tmp dir WITHOUT the mas-engineer/.mase/rules/responsibility_matrix.yaml
    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))
    status, agent, task = gk.check_responsibility_matrix("build")
    assert status == "error"
    assert agent is None
    assert "Matrix not found" in task


def test_matrix_shell_read_exception_returns_self(tmp_matrix):
    """Covers lines 126-130: shell+cmd in read_exceptions cmds → ('self', None, None)."""
    status, agent, task = gk.check_responsibility_matrix("shell", cmd="ls -la")
    assert status == "self"
    assert agent is None
    assert task is None


def test_matrix_shell_read_exception_no_match(tmp_matrix):
    """Covers lines 127-129: shell+cmd NOT in read_exceptions → falls through to action_map."""
    status, agent, task = gk.check_responsibility_matrix("shell", cmd="rm -rf /tmp/foo")
    # 'rm' is not in the matrix → blocked
    assert status == "blocked"
    assert agent is None


def test_matrix_load_delegate_returns_self(tmp_matrix):
    """Covers lines 132-133: action_type in ['load','delegate'] → ('self', None, None)."""
    for action in ["load", "delegate"]:
        status, agent, task = gk.check_responsibility_matrix(action)
        assert status == "self"
        assert agent is None
        assert task is None


def test_matrix_file_map_match_returns_delegate(tmp_matrix):
    """Covers lines 136-141: filepath matches a file_map pattern → ('delegate', agent, None)."""
    status, agent, task = gk.check_responsibility_matrix(
        "py_edit", filepath="mas-engineer/tools/foo.py"
    )
    assert status == "delegate"
    assert agent == "sub_mas-python-repair"
    assert task is None


def test_matrix_file_map_no_match_falls_through(tmp_matrix):
    """Covers lines 137-141: filepath doesn't match any pattern → no delegate, fall through."""
    status, agent, task = gk.check_responsibility_matrix(
        "py_edit", filepath="mas-engineer/recipe/foo.yaml"  # no .py in file_map
    )
    assert status == "blocked"


def test_matrix_action_map_match_returns_delegate(tmp_matrix):
    """Covers lines 144-149: action_map hit with agent + task → ('delegate', agent, task)."""
    status, agent, task = gk.check_responsibility_matrix("build")
    assert status == "delegate"
    assert agent == "sub_mas-recipe-manager"
    assert task == "BUILD"


def test_matrix_action_map_null_agent_returns_self(tmp_matrix):
    """Covers lines 145-148: action_map entry has agent=None → ('self', None, None)."""
    status, agent, task = gk.check_responsibility_matrix("doc_edit")
    assert status == "self"
    assert agent is None
    assert task is None


def test_matrix_action_map_load_returns_self(tmp_matrix):
    """Covers line 132-133 + 144-149: 'load' is in [load,delegate] short-circuit, not action_map."""
    # The fixture defines `load` in both [load,delegate] short-circuit AND action_map;
    # the short-circuit wins, so status='self'.
    status, agent, task = gk.check_responsibility_matrix("load")
    assert status == "self"


def test_matrix_no_match_anywhere_returns_blocked(tmp_matrix):
    """Covers line 152: action_type not in matrix → ('blocked', None, ...)."""
    status, agent, task = gk.check_responsibility_matrix("nonexistent_action")
    assert status == "blocked"
    assert agent is None
    assert "No Sub-Agent" in task


# --- main() tests ------------------------------------------------------------

@pytest.fixture
def fake_argv(monkeypatch):
    """Default to a safe argv; individual tests override per-case."""
    monkeypatch.setattr(sys, "argv", ["dev_gatekeeper.py"])


def _patch_lock():
    """Helper: prevent check_lock() from being a real side-effect."""
    return mock.patch.object(gk, "check_lock", return_value=None)


def _seed_passing_rules(isolated_state, tmp_path=None):
    """Seed .mase/ state so R01, R05, R18 pass (R20 always passes)."""
    (isolated_state / ".last_confirmation").write_text(str(int(time.time())))
    (isolated_state / "audit.log.jsonl").write_text(json.dumps(
        {"action": "DELEGATE", "target": "sub_mas-action-executor"}
    ) + "\n")
    cp_dir = isolated_state / "checkpoints"
    cp_dir.mkdir()
    (cp_dir / f"cp_x_{int(time.time()) - 60}").write_text("")


def test_main_check_lock_mode_passes(fake_argv, isolated_state, capsys):
    """Covers lines 162, 165-167: --check-lock + no lock → '✅ Lock-Check' + exit 0."""
    sys.argv = ["dev_gatekeeper.py", "--check-lock"]
    with _patch_lock():
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 0
    assert "✅ Lock-Check" in capsys.readouterr().out


def test_main_check_matrix_mode(fake_argv, isolated_state, tmp_matrix, capsys):
    """Covers lines 170-185: --check-matrix with --action/--file/--cmd kwargs."""
    sys.argv = ["dev_gatekeeper.py", "--check-matrix", "--action=shell", "--cmd=ls"]
    with _patch_lock():
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 0
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["status"] == "self"  # 'ls' is a read_exception


def test_main_check_matrix_mode_with_eq_args(fake_argv, isolated_state, tmp_matrix, capsys):
    """Covers line 173-175: --action=foo style args parsed via '='."""
    sys.argv = ["dev_gatekeeper.py", "--check-matrix", "--action=build"]
    with _patch_lock():
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 0
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["agent"] == "sub_mas-recipe-manager"


def test_main_missing_args(fake_argv, isolated_state, capsys):
    """Covers line 187-189: len(sys.argv) < 3 → exit 1 with help."""
    with _patch_lock():
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 1
    assert "❌" in capsys.readouterr().out


def test_main_unknown_action(fake_argv, isolated_state, capsys):
    """Covers lines 191-193: action not in (write/edit/shell/delete) → exit 1."""
    sys.argv = ["dev_gatekeeper.py", "frobnicate", "foo"]
    with _patch_lock():
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 1
    assert "Unknown action" in capsys.readouterr().out


def test_main_write_success(fake_argv, isolated_state, tmp_path, capsys):
    """Covers lines 195-221 + 228-231: full write path with all rules passing."""
    target = tmp_path / "out.txt"
    sys.argv = ["dev_gatekeeper.py", "write", str(target), "--content", "hello\n"]
    _seed_passing_rules(isolated_state)
    with _patch_lock():
        gk.main()  # success path does NOT sys.exit; just returns
    assert target.read_text() == "hello\n"
    out = capsys.readouterr().out
    assert "✅" in out
    assert "written" in out


def test_main_write_with_stdin(fake_argv, isolated_state, tmp_path, capsys, monkeypatch):
    """Covers lines 199-200: --stdin reads inhold from sys.stdin."""
    target = tmp_path / "out.txt"
    sys.argv = ["dev_gatekeeper.py", "write", str(target), "--stdin"]
    _seed_passing_rules(isolated_state)
    fake_stdin = mock.MagicMock()
    fake_stdin.read.return_value = "from-stdin\n"
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    with _patch_lock():
        gk.main()
    assert target.read_text() == "from-stdin\n"


def test_main_blocked_logs_audit(fake_argv, isolated_state, tmp_path, capsys):
    """Covers lines 202-218: rule violations → audit log entry + exit 1."""
    sys.argv = ["dev_gatekeeper.py", "write", str(tmp_path / "x"), "--content", "y\n"]
    # No .last_confirmation → R01 fails
    with _patch_lock():
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 1
    audit = (isolated_state / "audit.log.jsonl").read_text().strip().split("\n")
    blocked_entries = [json.loads(a) for a in audit if json.loads(a).get("status") == "BLOCKED"]
    assert len(blocked_entries) >= 1
    assert "GATEKEEPER BLOCKED" in capsys.readouterr().out


def test_main_edit_success(fake_argv, isolated_state, tmp_path, capsys):
    """Covers lines 232-242: edit with --before/--after replaces one occurrence."""
    target = tmp_path / "file.txt"
    target.write_text("hello world\n")
    sys.argv = ["dev_gatekeeper.py", "edit", str(target), "--before", "world", "--after", "universe"]
    _seed_passing_rules(isolated_state)
    with _patch_lock():
        gk.main()  # success path does NOT sys.exit
    assert target.read_text() == "hello universe\n"
    assert "edited" in capsys.readouterr().out


def test_main_edit_before_not_found(fake_argv, isolated_state, tmp_path, capsys):
    """Covers lines 238-239: --before not in file → exit 1."""
    target = tmp_path / "file.txt"
    target.write_text("nothing matches\n")
    sys.argv = ["dev_gatekeeper.py", "edit", str(target), "--before", "ZZZ", "--after", "AAA"]
    _seed_passing_rules(isolated_state)
    with _patch_lock():
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 1
    assert "'before' not found" in capsys.readouterr().out


def test_main_edit_missing_before_after(fake_argv, isolated_state, tmp_path, capsys):
    """Covers lines 243-244: edit without --before/--after → exit 1."""
    target = tmp_path / "file.txt"
    target.write_text("x")
    sys.argv = ["dev_gatekeeper.py", "edit", str(target)]
    _seed_passing_rules(isolated_state)
    with _patch_lock():
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 1
    assert "--before und --after required" in capsys.readouterr().out


def test_main_delete_success(fake_argv, isolated_state, tmp_path, capsys):
    """Covers lines 245-246: delete removes file."""
    target = tmp_path / "victim.txt"
    target.write_text("bye")
    sys.argv = ["dev_gatekeeper.py", "delete", str(target)]
    _seed_passing_rules(isolated_state)
    with _patch_lock():
        gk.main()  # success path does NOT sys.exit
    assert not target.exists()
    assert "deleted" in capsys.readouterr().out


def test_main_shell_subprocess_dispatch(fake_argv, isolated_state, monkeypatch):
    """Covers lines 223-227: shell action → subprocess.run + exit with returncode."""
    sys.argv = ["dev_gatekeeper.py", "shell", "echo", "hi"]
    _seed_passing_rules(isolated_state)
    fake_result = mock.MagicMock()
    fake_result.stdout = "hi\n"
    fake_result.stderr = ""
    fake_result.returncode = 0
    with _patch_lock(), mock.patch.object(gk.subprocess, "run", return_value=fake_result) as m:
        with pytest.raises(SystemExit) as e:
            gk.main()
    assert e.value.code == 0
    m.assert_called_once()
    assert "hi" in fake_result.stdout


def test_check_r10_invalid_yaml_returns_false():
    """Covers check_r10's YAML-load error branch directly (no main() roundtrip).

    The main()-roundtrip path is impractical because check_r10() reads the
    last word of action_str (which is --content's value, not the .yaml path),
    so the only reliable way to drive R10's error branch is to call it directly.
    """
    bad = "key: [\n  - invalid\n"  # python yaml raises ScannerError on this
    ok, det = gk.check_r10("write", "/tmp/bad.yaml", bad)
    assert ok is False
    assert "YAML-Error" in det


def test_check_r10_no_yaml_target_returns_true():
    """Covers check_r10's early-return when target doesn't end in .yaml/.yml."""
    ok, det = gk.check_r10("write", "/tmp/not.txt", "content")
    assert ok is True


def test_check_r10_non_write_edit_returns_true():
    """Covers check_r10's early-return for non-write/edit actions."""
    ok, det = gk.check_r10("shell", "/tmp/foo.yaml", "")
    assert ok is True


def test_main_lock_called_before_check_matrix(fake_argv, isolated_state):
    """Covers line 162: check_lock() is always called as the first thing in main()."""
    sys.argv = ["dev_gatekeeper.py", "--check-matrix", "--action=build"]
    with mock.patch.object(gk, "check_lock") as m:
        with pytest.raises(SystemExit):
            gk.main()
    m.assert_called_once_with()
