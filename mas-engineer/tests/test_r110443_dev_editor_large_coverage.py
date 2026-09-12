"""R110-443 — coverage-push r8: tools/dev_editor_large.py 0% → 100%.

Lines-based editor for large files (64 lines).

Targets:
- edit_between_lines: missing file → {error}; start<1 or end>len
  → {error}; valid range → replaces text.rstrip('\n')+'\n';
  returns {ok, alte_lines, neue_lines}; single-line range;
  multi-line range; replacement preserves surrounding lines
- find_line: pattern matches first line → returns 1-based line
  number; no match → None; regex special chars supported; empty
  file → None
- insert_after: after_line<1 or >len → {error}; valid → text
  inserted as one new line at position after_line (0-based
  insert at index N means new line becomes N+1 1-based);
  returns {ok, lines_insgesamt}
- __main__: 'edit <file> <s> <e> <text>' → JSON result; 'find
  <file> <regex>' → JSON {"line": N}; 'insert <file> <line>
  <text>' → JSON; unknown/short arg → docstring + exit 1
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_editor_large as el  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# edit_between_lines
# ─────────────────────────────────────────────────────────────────────
class TestEditBetweenLines:
    def test_file_not_found(self):
        r = el.edit_between_lines("/nonexistent/path/file.txt", 1, 1, "x")
        assert "error" in r
        assert "file not found" in r["error"]

    def test_basic_replace(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("line1\nline2\nline3\nline4\n")
        r = el.edit_between_lines(str(f), 2, 3, "NEW")
        assert r["ok"] is True
        assert r["alte_lines"] == 2
        assert r["neue_lines"] == 1
        assert f.read_text() == "line1\nNEW\nline4\n"

    def test_single_line_replace(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 2, 2, "B")
        assert r["ok"] is True
        assert f.read_text() == "a\nB\nc\n"

    def test_replace_first_line(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 1, 1, "A")
        assert r["ok"] is True
        assert f.read_text() == "A\nb\nc\n"

    def test_replace_last_line(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 3, 3, "C")
        assert r["ok"] is True
        assert f.read_text() == "a\nb\nC\n"

    def test_text_strips_trailing_newline(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 1, 1, "NEW\n")
        assert f.read_text() == "NEW\nb\nc\n"

    def test_start_below_1(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 0, 1, "x")
        assert "error" in r
        assert "outside" in r["error"]

    def test_end_beyond_length(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.edit_between_lines(str(f), 1, 10, "x")
        assert "error" in r
        assert "outside" in r["error"]


# ─────────────────────────────────────────────────────────────────────
# find_line
# ─────────────────────────────────────────────────────────────────────
class TestFindLine:
    def test_first_match(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hello\nworld\nfoo\n")
        assert el.find_line(str(f), "world") == 2

    def test_no_match(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        assert el.find_line(str(f), "xyz") is None

    def test_regex_special(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("foo123\nbar456\nfoo789\n")
        assert el.find_line(str(f), r"foo\d+") == 1

    def test_empty_file(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("")
        assert el.find_line(str(f), "anything") is None

    def test_first_of_many(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("match\nmatch\nmatch\n")
        # Returns first match
        assert el.find_line(str(f), "match") == 1

    def test_line_at_end(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nfoo\n")
        assert el.find_line(str(f), "foo") == 3


# ─────────────────────────────────────────────────────────────────────
# insert_after
# ─────────────────────────────────────────────────────────────────────
class TestInsertAfter:
    def test_basic_insert(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.insert_after(str(f), 1, "INSERTED")
        assert r["ok"] is True
        assert r["lines_insgesamt"] == 4
        assert f.read_text() == "a\nINSERTED\nb\nc\n"

    def test_insert_at_end(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.insert_after(str(f), 3, "END")
        assert r["ok"] is True
        assert f.read_text() == "a\nb\nc\nEND\n"

    def test_text_strips_trailing_newline(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.insert_after(str(f), 1, "X\n")
        assert f.read_text() == "a\nX\nb\nc\n"

    def test_below_1(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.insert_after(str(f), 0, "x")
        assert "error" in r
        assert "outside" in r["error"]

    def test_beyond_length(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        r = el.insert_after(str(f), 10, "x")
        assert "error" in r
        assert "outside" in r["error"]


# ─────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def _exec(self, argv, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_editor_large.py"] + argv
        code = 0
        try:
            try:
                exec(compile(Path(__file__).resolve().parents[1]
                             .joinpath("tools/dev_editor_large.py")
                             .read_text(),
                             "dev_editor_large.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_editor_large.py",
                      "sys": sys,
                      "json": json,
                      "Path": Path})
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        return capsys.readouterr().out, code

    def test_edit_cmd(self, tmp_path, capsys):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        out, code = self._exec(
            ["edit", str(f), "1", "1", "A"], capsys)
        assert code == 0
        data = json.loads(out)
        assert data["ok"] is True

    def test_find_cmd(self, tmp_path, capsys):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        out, code = self._exec(
            ["find", str(f), "b"], capsys)
        assert code == 0
        data = json.loads(out)
        assert data["line"] == 2

    def test_insert_cmd(self, tmp_path, capsys):
        f = tmp_path / "f.txt"
        f.write_text("a\nb\nc\n")
        out, code = self._exec(
            ["insert", str(f), "1", "INSERTED"], capsys)
        assert code == 0
        data = json.loads(out)
        assert data["ok"] is True

    def test_unknown_cmd(self, capsys):
        out, code = self._exec(["unknown"], capsys)
        assert code == 1
        assert "dev_editor_large.py" in out  # docstring

    def test_short_args(self, capsys):
        # edit with too few args → docstring + exit 1
        out, code = self._exec(["edit"], capsys)
        assert code == 1

    def test_no_args(self, capsys):
        out, code = self._exec([], capsys)
        assert code == 1
        assert "Usage" in out or "edit" in out  # docstring present
