"""R110-303 phase 2: 100% coverage tests for tools/dev_editor_large.py.

CRITICAL — pre-existing count-assertion pitfall (R110-300a):
  Do NOT use `assert "N type" in output` literals anywhere in this file.
  Also: the tool returns {"alte_lines": N, "neue_lines": N} dicts — these
  are TOOL OUTPUT values, not test assertions, so they are safe. But
  do not pattern-match on "N lines" in test asserts.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "dev_editor_large.py"
REPO_ROOT = str(Path(TOOL).parent.parent)
TOOLS_DIR = str(Path(TOOL).parent)


def _import_tool():
    """Coverage-attribution trick: synthetic `tools` package."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    if "tools" not in sys.modules:
        import types
        pkg = types.ModuleType("tools")
        pkg.__path__ = [TOOLS_DIR]
        sys.modules["tools"] = pkg
    full_name = f"tools.{Path(TOOL).stem}"
    spec = importlib.util.spec_from_file_location(full_name, TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sample_file(tmp_path):
    """Create a 10-line file at <tmp>/sample.txt."""
    p = tmp_path / "sample.txt"
    lines = [f"line{i}\n" for i in range(1, 11)]
    p.write_text("".join(lines))
    return p


# ---------- edit_between_lines ----------

def test_edit_between_lines_replaces_range(sample_file):
    """Replace lines 3..5 (inclusive) with 'replacement'. Old range is 3 lines."""
    mod = _import_tool()
    result = mod.edit_between_lines(str(sample_file), 3, 5, "replacement")
    assert result == {"ok": True, "alte_lines": 3, "neue_lines": 1}
    content = sample_file.read_text()
    lines = content.splitlines()
    assert lines[1] == "line2"  # unchanged
    assert lines[2] == "replacement"  # new
    # Total: was 10 lines, removed 3, added 1 → 8 lines
    assert len(lines) == 8


def test_edit_between_lines_strips_trailing_newline_and_re_adds(sample_file):
    """If replacement has a trailing newline, the resulting file should not
    have double newlines."""
    mod = _import_tool()
    mod.edit_between_lines(str(sample_file), 1, 1, "only-line\n")
    content = sample_file.read_text()
    # 9 lines were replaced; we should now have 1 line (the new text) + 9 remaining = 10
    lines = content.splitlines()
    assert lines[0] == "only-line"
    assert len(lines) == 10


def test_edit_between_lines_missing_file_returns_error(tmp_path):
    """If filepath doesn't exist, returns {"error": ...}."""
    mod = _import_tool()
    result = mod.edit_between_lines(str(tmp_path / "nope.txt"), 1, 1, "x")
    assert "error" in result


def test_edit_between_lines_out_of_range_returns_error(sample_file):
    """If start<1 or end>len, returns {"error": ...} and does not write."""
    mod = _import_tool()
    original = sample_file.read_text()
    r1 = mod.edit_between_lines(str(sample_file), 0, 3, "x")
    r2 = mod.edit_between_lines(str(sample_file), 1, 999, "x")
    assert "error" in r1
    assert "error" in r2
    assert sample_file.read_text() == original


# ---------- find_line ----------

def test_find_line_returns_1_based_line_number(sample_file):
    """find_line with pattern 'line5' returns 5 (not 4)."""
    mod = _import_tool()
    assert mod.find_line(str(sample_file), r"line5") == 5


def test_find_line_returns_none_when_no_match(sample_file):
    """find_line with a non-existent pattern returns None."""
    mod = _import_tool()
    assert mod.find_line(str(sample_file), r"^doesnotexist$") is None


def test_find_line_first_match_wins(sample_file):
    """If pattern matches multiple lines, the FIRST is returned (1-based)."""
    mod = _import_tool()
    # Every line contains "line" — return 1
    assert mod.find_line(str(sample_file), r"line") == 1


# ---------- insert_after ----------

def test_insert_after_adds_line(sample_file):
    """insert_after at line 5 places the new line at position 6 (0-based 5)."""
    mod = _import_tool()
    result = mod.insert_after(str(sample_file), 5, "inserted")
    assert result["ok"] is True
    lines = sample_file.read_text().splitlines()
    # line1..line5 (5 items), then 'inserted', then line6..line10
    assert lines[5] == "inserted"
    assert lines[6] == "line6"
    assert len(lines) == 11


def test_insert_after_strips_trailing_newline_and_re_adds(sample_file):
    """insert_after normalizes the input text (strips trailing \n, adds one)."""
    mod = _import_tool()
    mod.insert_after(str(sample_file), 1, "trailing\n")
    lines = sample_file.read_text().splitlines()
    assert lines[1] == "trailing"  # no extra blank line
    assert len(lines) == 11


def test_insert_after_out_of_range_returns_error(sample_file):
    """If after_line < 1 or > len, returns {"error": ...}."""
    mod = _import_tool()
    original = sample_file.read_text()
    r1 = mod.insert_after(str(sample_file), 0, "x")
    r2 = mod.insert_after(str(sample_file), 999, "x")
    assert "error" in r1
    assert "error" in r2
    assert sample_file.read_text() == original


# ---------- __main__ block ----------

def test_main_edit_via_subprocess(sample_file):
    """`edit <file> <start> <end> <repl>` from CLI prints json with ok=True."""
    result = subprocess.run(
        [sys.executable, str(TOOL), "edit", str(sample_file), "2", "4", "repl-text"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["alte_lines"] == 3
    assert data["neue_lines"] == 1


def test_main_find_via_subprocess(sample_file):
    """`find <file> <pattern>` from CLI prints json with a 1-based line."""
    result = subprocess.run(
        [sys.executable, str(TOOL), "find", str(sample_file), r"line7"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    data = json.loads(result.stdout)
    assert data["line"] == 7


def test_main_insert_via_subprocess(sample_file):
    """`insert <file> <after_line> <text>` from CLI prints json."""
    result = subprocess.run(
        [sys.executable, str(TOOL), "insert", str(sample_file), "3", "newline"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    data = json.loads(result.stdout)
    assert data["ok"] is True


def test_main_no_args_prints_docstring_and_exits_1(tmp_path):
    """No args → prints __doc__ and exits 1."""
    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    # Should contain the usage hint
    assert "dev_editor_large.py" in result.stdout


def test_main_unknown_command_prints_docstring_and_exits_1(tmp_path):
    """Unknown command → prints __doc__ and exits 1."""
    result = subprocess.run(
        [sys.executable, str(TOOL), "frobnicate"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "dev_editor_large.py" in result.stdout
