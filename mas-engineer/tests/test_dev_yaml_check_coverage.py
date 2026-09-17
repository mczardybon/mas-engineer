"""Tests for tools/dev_yaml_check.py — coverage gap closer.

Covers the 11 missed statements across 3 functions:
- check_yaml: lines 70-73 (generic Exception in file-read), 85-88
  (generic Exception in yaml.safe_load)
- check_python_syntax: lines 138-140 (generic Exception in compile)
"""
import json
import sys
from pathlib import Path

import pytest

# Import as tools.dev_yaml_check so pytest-cov tracks it under tools.X
# (NOT as a bare import — that bypasses coverage since the file lives in
# tools/dev_yaml_check.py and pytest-cov measures per-name).
import tools.dev_yaml_check  # noqa: E402

dev_yaml_check = tools.dev_yaml_check


def test_check_yaml_handles_generic_read_exception(tmp_path, monkeypatch):
    """Covers lines 70-73: when file read raises a non-UnicodeDecodeError
    exception (e.g. OSError), check_yaml returns an error result instead
    of crashing."""
    # Create a file we can reference
    p = tmp_path / "f.yaml"
    p.write_text("a: 1")
    # Patch open() to raise OSError for this file
    import builtins
    real_open = builtins.open
    def fake_open(path, *args, **kwargs):
        if str(path) == str(p):
            raise OSError("simulated disk error")
        return real_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", fake_open)

    result = dev_yaml_check.check_yaml(str(p))
    assert result["status"] == "error"
    assert "Read error" in result["error"]


def test_check_yaml_handles_yaml_parse_exception(tmp_path, monkeypatch):
    """Covers lines 85-88: when yaml.safe_load raises a non-YAMLError
    exception (e.g. ValueError), check_yaml returns error."""
    p = tmp_path / "f.yaml"
    p.write_text("a: 1")
    # Patch yaml.safe_load to raise ValueError
    import yaml
    real_safe_load = yaml.safe_load
    def fake_safe_load(content):
        if "a: 1" in content:
            raise ValueError("simulated non-yaml exception")
        return real_safe_load(content)
    monkeypatch.setattr(yaml, "safe_load", fake_safe_load)

    result = dev_yaml_check.check_yaml(str(p))
    assert result["status"] == "error"
    assert "Non-YAML" in result["error"] or "ValueError" in result["error"]


def test_check_python_syntax_handles_generic_exception(tmp_path, monkeypatch):
    """Covers lines 138-140: when compile() raises a non-SyntaxError
    exception (e.g. ValueError), check_python_syntax returns error."""
    p = tmp_path / "f.py"
    p.write_text("x = 1")
    # Patch the built-in compile() to raise ValueError
    import builtins
    real_compile = builtins.compile
    def fake_compile(source, filename, mode, *args, **kwargs):
        if "x = 1" in source:
            raise ValueError("simulated compile failure")
        return real_compile(source, filename, mode, *args, **kwargs)
    monkeypatch.setattr(builtins, "compile", fake_compile)

    result = dev_yaml_check.check_python_syntax(str(p))
    assert result["status"] == "error"


def test_main_block_via_subprocess(tmp_path):
    """Covers line 351: `if __name__ == '__main__': sys.exit(main())` block.

    Runs the script directly (python tools/dev_yaml_check.py HELP) so the
    module-level __main__ guard fires sys.exit(main()).

    NOTE: pytest-cov cannot track this subprocess call's coverage, so this
    test verifies the contract (script exits cleanly with HELP) but the
    line is exercised separately in CI by .githooks/pre-push validator
    (which runs `python tools/dev_yaml_check.py HELP`).
    """
    import subprocess
    script = dev_yaml_check.__file__
    proc = subprocess.run(
        [sys.executable, script, "HELP"],
        capture_output=True, text=True, timeout=15,
    )
    # HELP → main() prints usage and returns 0
    assert proc.returncode == 0
    assert "yaml" in (proc.stdout + proc.stderr).lower() or "usage" in (proc.stdout + proc.stderr).lower()


def test_main_guard_via_runpy(monkeypatch):
    """Covers line 351 in-process via runpy.run_path(__name__='__main__').

    runpy.run_path() with run_name='__main__' makes the loaded module
    see __name__ == '__main__', so the `if __name__ == "__main__":`
    guard at line 350 evaluates True and line 351 executes under THIS
    process (where pytest-cov tracks coverage).
    """
    import runpy
    exit_calls = []
    # Stub sys.exit to capture the return code without exiting the test
    monkeypatch.setattr(sys, "exit", lambda code: exit_calls.append(code))
    # Stub argv so main() sees the HELP command
    monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "HELP"])
    # run_path with run_name='__main__' sets the module's __name__ to '__main__'
    runpy.run_path(dev_yaml_check.__file__, run_name="__main__")
    assert len(exit_calls) == 1, f"expected 1 sys.exit call, got {len(exit_calls)}"
    assert exit_calls[0] == 0, f"HELP should return 0, got {exit_calls[0]}"
