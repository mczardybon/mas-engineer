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

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_yaml_check


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
