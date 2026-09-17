"""R110-463 — coverage-push r8: tools/dev_editor_large.py 0% → 100%

Line-based editor for >1000-line files. CLI:
  edit   <file> <start_line> <end_line> <replacement_text>
  find   <file> <regex_pattern>
  insert <file> <after_line> <text>

Targets:
- edit_between_lines(file, start, end, text):
  - file missing → {error: "file not found"}
  - start<1 or end>len → {error: "outside"}
  - normal → read, replace lines[start-1:end] with
    [text.rstrip('\n')+'\n'], write, return {ok, alte_lines,
    neue_lines}
  - rstrip normalizes line endings

- find_line(file, pattern):
  - regex match on first hit → 1-based line number
  - no match → None

- insert_after(file, after_line, text):
  - after_line<1 or >len → {error: "outside"}
  - normal → insert lines[after_line:after_line] = [text+\n],
    write, return {ok, lines_insgesamt}

- CLI: dispatch on cmd + argc; else prints __doc__ + exit 1
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import tools.dev_editor_large as el  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# edit_between_lines
# ─────────────────────────────────────────────────────────────────────
class TestEditBetweenLines:
    def test_file_missing(self, tmp_path):
        r = el.edit_between_lines(
            str(tmp_path / "no.txt"), 1, 2, "x")
        assert "error" in r
        assert "not found" in r["error"]

    def test_start_out_of_range(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 0, 2, "x")
        assert "error" in r
        assert "outside" in r["error"]

    def test_end_out_of_range(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 1, 10, "x")
        assert "error" in r
        assert "outside" in r["error"]

    def test_replacement(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\nd\n")
        r = el.edit_between_lines(str(f), 2, 3, "X")
        assert r["ok"] is True
        assert r["alte_lines"] == 2
        assert r["neue_lines"] == 1
        assert f.read_text() == "a\nX\nd\n"

    def test_rstrip_normalizes(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        # text with trailing newline → rstrip removes it
        r = el.edit_between_lines(str(f), 1, 1, "X\n")
        assert r["ok"] is True
        assert f.read_text() == "X\nb\n"

    def test_single_line_replacement(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 2, 2, "Z")
        assert r["ok"] is True
        assert f.read_text() == "a\nZ\nc\n"


# ─────────────────────────────────────────────────────────────────────
# find_line
# ─────────────────────────────────────────────────────────────────────
class TestFindLine:
    def test_first_match(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nfoo\nbar\nfoo\n")
        r = el.find_line(str(f), "foo")
        assert r == 2

    def test_no_match_returns_none(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        r = el.find_line(str(f), "zzz")
        assert r is None

    def test_match_first_line(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("foo\nbar\n")
        r = el.find_line(str(f), "foo")
        assert r == 1

    def test_regex(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb123\nc\n")
        r = el.find_line(str(f), r"b\d+")
        assert r == 2


# ─────────────────────────────────────────────────────────────────────
# insert_after
# ─────────────────────────────────────────────────────────────────────
class TestInsertAfter:
    def test_zero_line(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        r = el.insert_after(str(f), 0, "X")
        assert "error" in r

    def test_overflow(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        r = el.insert_after(str(f), 10, "X")
        assert "error" in r

    def test_insert_after_first(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        r = el.insert_after(str(f), 1, "X")
        assert r["ok"] is True
        assert f.read_text() == "a\nX\nb\n"

    def test_insert_after_last(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        # after_line == len(lines) → append after last
        r = el.insert_after(str(f), 2, "X")
        assert r["ok"] is True
        assert f.read_text() == "a\nb\nX\n"

    def test_rstrip_normalizes(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\n")
        el.insert_after(str(f), 1, "X\n")
        # text+\n → rstrip removes the \n then adds \n back
        assert f.read_text() == "a\nX\n"


# ─────────────────────────────────────────────────────────────────────
# CLI subprocess (covers __main__)
# ─────────────────────────────────────────────────────────────────────
class TestCli:
    def test_edit_cli(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = subprocess.run(
            ['python3', 'tools/dev_editor_large.py',
             'edit', str(f), '1', '2', 'Z'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["ok"] is True
        assert f.read_text() == "Z\nc\n"

    def test_find_cli_match(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nfoo\nb\n")
        r = subprocess.run(
            ['python3', 'tools/dev_editor_large.py',
             'find', str(f), 'foo'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["line"] == 2

    def test_find_cli_no_match(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        r = subprocess.run(
            ['python3', 'tools/dev_editor_large.py',
             'find', str(f), 'zzz'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert out["line"] is None

    def test_insert_cli(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        r = subprocess.run(
            ['python3', 'tools/dev_editor_large.py',
             'insert', str(f), '1', 'X'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        assert f.read_text() == "a\nX\nb\n"

    def test_no_cmd_prints_doc(self):
        r = subprocess.run(
            ['python3', 'tools/dev_editor_large.py'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 1
        assert "Usage" in r.stdout

    def test_unknown_cmd_prints_doc(self):
        r = subprocess.run(
            ['python3', 'tools/dev_editor_large.py', 'frobnicate'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 1
        assert "Usage" in r.stdout

    def test_wrong_argc_prints_doc(self):
        # find needs 4 args, only 3 given → wrong argc
        r = subprocess.run(
            ['python3', 'tools/dev_editor_large.py',
             'find', 'x'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 1
