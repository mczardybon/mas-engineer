"""
test_r110308_parallel_subprocess.py — R110-308: cover the 4 task-type branches
in dev_parallel.ParlllPool._execute_legacy_task that are not exercised by
R110-299 batch_dispatch tests.

Branches covered here:
  - type="subprocess"  (L193-208: real subprocess.run with cmd list)
  - type="shell"       (L223-237: subprocess.run with shell=True)
  - type="python"      (L239-247: compile+exec arbitrary python code)
  - default / unknown  (L249+: subprocess.run with shell=True fallback)

The legacy pool's _execute_legacy_task is normally called by worker threads
inside ParalllPool. We test it directly via pool._legacy_tasks queue
(added via add_task) and pool._run_legacy() synchronous helper, OR by
calling the method directly with a pre-built task dict.

Run with:
    python3 -m pytest tests/test_r110308_parallel_subprocess.py -v
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOL = REPO_ROOT / "tools" / "dev_parallel.py"


@pytest.fixture
def pool():
    """Fresh ParalllPool (uses defaults: max_workers=4)."""
    sys.path.insert(0, str(TOOL.parent))
    import dev_parallel
    p = dev_parallel.ParalllPool()
    yield p
    sys.path.pop(0)


def _make_task(name, type_, payload):
    return {
        "name": name,
        "type": type_,
        "payload": payload,
        "status": "queued",
    }


def test_execute_legacy_subprocess_runs_real_command(pool):
    """type='subprocess' with cmd list invokes subprocess.run and stores result."""
    task = _make_task("echo-test", "subprocess", {"cmd": "echo hello"})
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"
    assert result["result"]["returncode"] == 0
    assert "hello" in result["result"]["stdout"]
    assert result["result"]["stderr"] == ""


def test_execute_legacy_subprocess_with_command_alias(pool):
    """type='subprocess' accepts 'command' as alias for 'cmd'."""
    task = _make_task("alias-test", "subprocess", {"command": "echo via-alias"})
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"
    assert "via-alias" in result["result"]["stdout"]


def test_execute_legacy_subprocess_with_cwd(tmp_path, pool):
    """type='subprocess' honors 'cwd' payload field."""
    task = _make_task(
        "cwd-test", "subprocess",
        {"cmd": "pwd", "cwd": str(tmp_path)},
    )
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"
    assert str(tmp_path) in result["result"]["stdout"]


def test_execute_legacy_shell_runs_shell_command(pool):
    """type='shell' uses subprocess.run with shell=True."""
    task = _make_task("shell-test", "shell", {"command": "echo via-shell"})
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"
    assert "via-shell" in result["result"]["stdout"]


def test_execute_legacy_shell_empty_command_marks_completed(pool):
    """type='shell' with empty command is a no-op, status=completed."""
    task = _make_task("shell-empty", "shell", {"command": ""})
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"
    # result field not set when cmd is empty
    assert "result" not in result or result.get("result") is None


def test_execute_legacy_python_runs_code(pool):
    """type='python' compiles and execs the payload code, captures locals."""
    task = _make_task(
        "py-test", "python",
        {"code": "x = 42\ny = 'hello'"},
    )
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"
    assert "locals" in result["result"]
    # local_vars: x and y should be in the captured locals (as strings)
    assert "42" in result["result"]["locals"]["x"]
    assert "hello" in result["result"]["locals"]["y"]


def test_execute_legacy_python_empty_code_marks_completed(pool):
    """type='python' with empty code is a no-op, status=completed."""
    task = _make_task("py-empty", "python", {"code": ""})
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"


def test_execute_legacy_unknown_type_uses_shell_fallback(pool):
    """Unknown type falls back to subprocess.run with shell=True."""
    task = _make_task(
        "unknown-test", "mystery_type",
        {"command": "echo fallback"},
    )
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"
    assert "fallback" in result["result"]["stdout"]


def test_execute_legacy_unknown_type_empty_command_marks_completed(pool):
    """Unknown type with no command is a no-op, status=completed."""
    task = _make_task("unknown-empty", "mystery_type", {})
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"


def test_execute_legacy_subprocess_nonzero_returncode(pool):
    """type='subprocess' captures nonzero returncodes correctly."""
    task = _make_task(
        "fail-test", "subprocess",
        {"cmd": "false"},  # always returns 1
    )
    result = pool._execute_legacy_task(task)
    assert result["status"] == "completed"
    assert result["result"]["returncode"] == 1
