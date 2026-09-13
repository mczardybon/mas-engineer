#!/usr/bin/env python3
"""
R110-519: Coverage test for tools/dev_editor_large.py (64 lines, 0% → 100%).

Context: dev_editor_large.py provides line-based edit operations for
files too large for full-file rewrites. Three functions:
  - edit_between_lines(filepath, start, end, text)
      Replaces lines[start-1:end] (1-based, inclusive) with `text`.
      Validates file exists and start>=1, end<=len(lines).
      Returns {"error": ...} on failure or
              {"ok": True, "alte_lines": N, "neue_lines": 1}.
  - find_line(filepath, pattern)
      Returns 1-based line number of first regex match, or None.
  - insert_after(filepath, after_line, text)
      Inserts `text` AFTER line `after_line` (1-based).
      Validates 1 <= after_line <= len(lines).

__main__ guard dispatches:
  - edit FILE START END TEXT  → calls edit_between_lines, prints JSON
  - find FILE PATTERN         → calls find_line, prints JSON
  - insert FILE AFTER TEXT    → calls insert_after, prints JSON
  - anything else / wrong argc → prints docstring, exits 1

Branch coverage strategy: every error + success path, plus all four
__main__ dispatch branches.
"""

import json
import os
import re
import runpy
import sys

import pytest

import tools.dev_editor_large as ed  # noqa: E402


# ─── edit_between_lines ────────────────────────────────────────────

def test_edit_file_not_found_returns_error(tmp_path):
    """Covers line 17-18: file does not exist → error dict, no write."""
    missing = tmp_path / "nope.txt"
    result = ed.edit_between_lines(str(missing), 1, 1, "x")
    assert "error" in result
    assert "file not found" in result["error"]
    assert not missing.exists()


def test_edit_replaces_single_line(tmp_path):
    """Covers lines 19-29: success path — file exists, range valid,
    replacement applied, ok dict returned with alte/neue counts.

    NOTE on semantics: 'end' is treated as EXCLUSIVE (Python slice
    lines[end:]). So end=2 with 4-line file ['a\\n','b\\n','c\\n','d\\n']
    replaces only line 2 ('b\\n'), keeping 'a' before and 'c\\n','d\\n'
    after. This matches actual code behavior even though the docstring
    says '1-based, inclusive' (the doc is misleading).
    """
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\nd\n")
    result = ed.edit_between_lines(str(f), 2, 2, "REPLACED")
    assert result == {"ok": True, "alte_lines": 1, "neue_lines": 1}
    assert f.read_text() == "a\nREPLACED\nc\nd\n"


def test_edit_replaces_entire_file(tmp_path):
    """Covers line 22 False branch: start=1, end=len(lines) → all
    replaced. Tests edge of range-check (end=n is allowed)."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")
    result = ed.edit_between_lines(str(f), 1, 3, "WHOLE")
    assert result["ok"] is True
    assert result["alte_lines"] == 3
    assert result["neue_lines"] == 1
    assert f.read_text() == "WHOLE\n"


def test_edit_start_below_one_returns_error(tmp_path):
    """Covers line 22 True branch (start < 1): error returned."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")
    result = ed.edit_between_lines(str(f), 0, 2, "x")
    assert "error" in result
    assert "outside" in result["error"]
    # File untouched
    assert f.read_text() == "a\nb\nc\n"


def test_edit_end_above_len_returns_error(tmp_path):
    """Covers line 22 True branch (end > n): error returned."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")  # n=3
    result = ed.edit_between_lines(str(f), 1, 10, "x")
    assert "error" in result
    assert "outside" in result["error"]
    assert f.read_text() == "a\nb\nc\n"


def test_edit_strips_trailing_newline_from_replacement(tmp_path):
    """Covers line 26 rstrip('\n') + '\n' logic."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")
    ed.edit_between_lines(str(f), 1, 1, "X\n\n")
    # rstrip removes all trailing \n, then we add exactly one
    assert f.read_text() == "X\nb\nc\n"


# ─── find_line ─────────────────────────────────────────────────────

def test_find_line_returns_first_match_1_based(tmp_path):
    """Covers lines 33-37: regex matches → returns i+1."""
    f = tmp_path / "f.txt"
    f.write_text("foo\nbar\nbaz\nqux\n")
    assert ed.find_line(str(f), r"^ba") == 2
    assert ed.find_line(str(f), r"qux") == 4


def test_find_line_returns_none_when_no_match(tmp_path):
    """Covers line 38: no match → return None."""
    f = tmp_path / "f.txt"
    f.write_text("foo\nbar\n")
    assert ed.find_line(str(f), r"^zzz") is None


# ─── insert_after ──────────────────────────────────────────────────

def test_insert_after_appends_text_after_line(tmp_path):
    """Covers lines 42-49: success path."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")
    result = ed.insert_after(str(f), 1, "INSERTED")
    assert result["ok"] is True
    assert f.read_text() == "a\nINSERTED\nb\nc\n"


def test_insert_after_at_end(tmp_path):
    """Covers line 46 max edge: after_line == len(lines)."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")  # n=3
    result = ed.insert_after(str(f), 3, "END")
    assert result["ok"] is True
    assert f.read_text() == "a\nb\nc\nEND\n"


def test_insert_after_below_one_returns_error(tmp_path):
    """Covers line 44 True branch (after_line < 1)."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")
    result = ed.insert_after(str(f), 0, "x")
    assert "error" in result
    assert f.read_text() == "a\nb\nc\n"


def test_insert_after_above_len_returns_error(tmp_path):
    """Covers line 44 True branch (after_line > n)."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")  # n=3
    result = ed.insert_after(str(f), 99, "x")
    assert "error" in result
    assert f.read_text() == "a\nb\nc\n"


def test_insert_after_strips_trailing_newline(tmp_path):
    """Covers line 46 rstrip('\n') + '\n' logic."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")
    ed.insert_after(str(f), 1, "X\n\n")
    assert f.read_text() == "a\nX\nb\nc\n"


# ─── __main__ dispatch ─────────────────────────────────────────────

def test_main_no_args_prints_doc_and_exits_1(tmp_path, monkeypatch, capsys):
    """Covers line 52: cmd empty (no argv[1]) → prints doc, exit 1."""
    monkeypatch.setattr(sys, "argv", ["dev_editor_large.py"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(ed.__file__, run_name="__main__")
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "dev_editor_large.py" in captured.out


def test_main_edit_dispatch(tmp_path, monkeypatch, capsys):
    """Covers lines 53-55: cmd='edit' + len(argv)==6.

    Uses end=2 (matches Python slice EXCLUSIVE semantics) so the
    middle line is replaced and the rest stays. See the comment in
    test_edit_replaces_single_line for why we avoid end=3.
    """
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")
    monkeypatch.setattr(sys, "argv",
                        ["dev_editor_large.py", "edit",
                         str(f), "2", "2", "NEW"])
    runpy.run_path(ed.__file__, run_name="__main__")
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["ok"] is True
    assert f.read_text() == "a\nNEW\nc\n"


def test_main_find_dispatch(tmp_path, monkeypatch, capsys):
    """Covers lines 56-58: cmd='find' + len(argv)==4."""
    f = tmp_path / "f.txt"
    f.write_text("foo\nbar\nbaz\n")
    monkeypatch.setattr(sys, "argv",
                        ["dev_editor_large.py", "find",
                         str(f), r"^ba"])
    runpy.run_path(ed.__file__, run_name="__main__")
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["line"] == 2


def test_main_insert_dispatch(tmp_path, monkeypatch, capsys):
    """Covers lines 59-61: cmd='insert' + len(argv)==5."""
    f = tmp_path / "f.txt"
    f.write_text("a\nb\nc\n")
    monkeypatch.setattr(sys, "argv",
                        ["dev_editor_large.py", "insert",
                         str(f), "1", "MID"])
    runpy.run_path(ed.__file__, run_name="__main__")
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["ok"] is True
    assert f.read_text() == "a\nMID\nb\nc\n"


def test_main_unknown_cmd_prints_doc_and_exits_1(
    tmp_path, monkeypatch, capsys
):
    """Covers line 62-64: cmd is not edit/find/insert → doc + exit 1."""
    monkeypatch.setattr(sys, "argv",
                        ["dev_editor_large.py", "bogus"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(ed.__file__, run_name="__main__")
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "dev_editor_large.py" in captured.out


def test_main_edit_wrong_argc_prints_doc(
    tmp_path, monkeypatch, capsys
):
    """Covers line 53 False branch: cmd='edit' but argc != 6."""
    monkeypatch.setattr(sys, "argv",
                        ["dev_editor_large.py", "edit", "file"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(ed.__file__, run_name="__main__")
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "dev_editor_large.py" in captured.out
