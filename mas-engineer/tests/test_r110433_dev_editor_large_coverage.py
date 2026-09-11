"""R110-433 — coverage-push r6: tools/dev_editor_large.py 0% → 100%.

Line-based editor (64 lines). Edit/find/insert operations on files
>1000 lines without YAML-parse.

Targets:
- edit_between_lines: missing file (error dict), start<1 (error),
  end>len (error), valid edit (lines replaced, rstrip newline
  handling, multiline text), result has alte_lines/neue_lines/ok
- find_line: regex match returns 1-based line, no match returns None,
  empty pattern matches first line
- insert_after: insert at start (after line 1), insert at end (after
  last line), invalid after_line <1 (error), invalid after_line
  >len (error), text rstripped of newline
- __main__ exec: edit command, find command, insert command,
  unknown command (exit 1 + prints docstring), missing args (exit 1)
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_editor_large as ed  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# edit_between_lines
# ─────────────────────────────────────────────────────────────────────
class TestEditBetweenLines:
    def test_missing_file(self, tmp_path):
        result = ed.edit_between_lines(str(tmp_path / "nope.txt"), 1, 2, "x")
        assert "error" in result
        assert "file not found" in result["error"]

    def test_start_below_1(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        result = ed.edit_between_lines(str(f), 0, 2, "x")
        assert "error" in result
        assert "outside" in result["error"]

    def test_end_above_n(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        result = ed.edit_between_lines(str(f), 1, 99, "x")
        assert "error" in result

    def test_valid_replacement(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\nd\n")
        result = ed.edit_between_lines(str(f), 2, 3, "REPLACED")
        assert result["ok"] is True
        assert result["alte_lines"] == 2  # end-start+1
        assert result["neue_lines"] == 1
        # Verify file
        assert f.read_text() == "a\nREPLACED\nd\n"

    def test_rstrip_newline_in_replacement(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        # Pass with trailing newline — should be rstripped
        ed.edit_between_lines(str(f), 2, 2, "X\n\n\n")
        assert f.read_text() == "a\nX\nc\n"

    def test_multiline_replacement(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        ed.edit_between_lines(str(f), 2, 2, "line1\nline2")
        assert f.read_text() == "a\nline1\nline2\nc\n"

    def test_first_line_replacement(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        ed.edit_between_lines(str(f), 1, 1, "FIRST")
        assert f.read_text() == "FIRST\nb\nc\n"

    def test_last_line_replacement(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        ed.edit_between_lines(str(f), 3, 3, "LAST")
        assert f.read_text() == "a\nb\nLAST\n"


# ─────────────────────────────────────────────────────────────────────
# find_line
# ─────────────────────────────────────────────────────────────────────
class TestFindLine:
    def test_match_found(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\nd\n")
        assert ed.find_line(str(f), r"^c$") == 3

    def test_no_match_returns_none(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        assert ed.find_line(str(f), r"x+") is None

    def test_first_line_match(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello\nworld\n")
        assert ed.find_line(str(f), r"hello") == 1

    def test_empty_pattern_matches_line1(self, tmp_path):
        # Empty regex matches every line — first match is line 1
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        assert ed.find_line(str(f), "") == 1

    def test_partial_match(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("foo\nbar\nbaz\n")
        assert ed.find_line(str(f), r"^ba") == 2


# ─────────────────────────────────────────────────────────────────────
# insert_after
# ─────────────────────────────────────────────────────────────────────
class TestInsertAfter:
    def test_insert_at_start(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        result = ed.insert_after(str(f), 1, "INSERTED")
        assert result["ok"] is True
        assert f.read_text() == "a\nINSERTED\nb\nc\n"

    def test_insert_at_end(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        result = ed.insert_after(str(f), 3, "INSERTED")
        assert result["ok"] is True
        assert f.read_text() == "a\nb\nc\nINSERTED\n"

    def test_after_line_below_1(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        result = ed.insert_after(str(f), 0, "x")
        assert "error" in result

    def test_after_line_above_n(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        result = ed.insert_after(str(f), 99, "x")
        assert "error" in result

    def test_text_rstripped_of_newline(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        ed.insert_after(str(f), 1, "X\n\n\n")
        # Trailing newlines collapsed to one
        assert f.read_text() == "a\nX\nb\n"

    def test_lines_insgesamt_count(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")  # 2 lines
        result = ed.insert_after(str(f), 1, "X")
        # Now 3 lines
        assert result["lines_insgesamt"] == 3


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
def _run_main(script, argv, capsys):
    """Exec the module's __main__ block and capture stdout + exit code."""
    old_argv = sys.argv
    sys.argv = argv
    out = ""
    code = 0
    try:
        try:
            exec(compile(script, argv[0], "exec"),
                 {"__name__": "__main__",
                  "__file__": argv[0]})
        except SystemExit as e:
            code = e.code if e.code is not None else 0
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    return out, code


class TestMainExec:
    def test_edit_command(self, tmp_path, capsys):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_editor_large.py").read_text()
        out, code = _run_main(script,
                              ["dev_editor_large.py", "edit",
                               str(f), "2", "2", "REPLACED"], capsys)
        assert code == 0
        assert f.read_text() == "a\nREPLACED\nc\n"

    def test_find_command(self, tmp_path, capsys):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_editor_large.py").read_text()
        out, code = _run_main(script,
                              ["dev_editor_large.py", "find",
                               str(f), r"^b$"], capsys)
        assert code == 0
        assert json.loads(out) == {"line": 2}

    def test_insert_command(self, tmp_path, capsys):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\n")
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_editor_large.py").read_text()
        out, code = _run_main(script,
                              ["dev_editor_large.py", "insert",
                               str(f), "1", "INSERTED"], capsys)
        assert code == 0
        assert f.read_text() == "a\nINSERTED\nb\n"

    def test_unknown_command(self, capsys):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_editor_large.py").read_text()
        out, code = _run_main(script,
                              ["dev_editor_large.py", "BOGUS"], capsys)
        assert code == 1
        # Prints docstring
        assert "dev_editor_large" in out or "Usage" in out

    def test_missing_args(self, capsys):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_editor_large.py").read_text()
        out, code = _run_main(script, ["dev_editor_large.py"], capsys)
        assert code == 1
