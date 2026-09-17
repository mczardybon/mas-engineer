"""R110-428 — coverage-push r6: tools/dev_directive_parser.py 0% → 100%.

Pure-stdlib R-directive markdown parser (107 lines). Parses a
.mase/directives/R<NR>-<topic>.md file into a structured dict.

Targets:
- parse_directive: missing file → error dict, R-number extracted,
  topic extracted, no-R-number (None), no .md suffix (uses stem),
  no DIREKTIVE blocks (empty), single block, multiple blocks, block
  with title, block without title (fallback "DIREKTIVE N"), block
  with action paragraph, block without action, files mentioned
  (deduplicated via sorted(set)), no files, scope section, scope
  SCOPE upper, pre-conditions section, ACCEPTANCE upper, missing
  scope/pre/accept → empty
- main: no args (exit 2 + stderr usage), missing file (exit 1),
  --json prints JSON, normal human-readable output, error file path
- __main__ exec via in-process exec()
"""

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_directive_parser as dp  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────
def _write_directive(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def _make_body(nr=1, title="Title", action="Do the thing",
               files=None, with_scope=True, with_pre=True, with_acc=True,
               extra_blocks=0, with_accept_section=True):
    """Build a directive markdown body with one DIREKTIVE block."""
    parts = ["# R-foo bar baz\n"]
    if with_scope:
        parts.append("Scope: recipe/,tools/\n")
    if with_pre:
        parts.append("\nPre-conditions: must work\n")
    if with_acc and with_accept_section:
        parts.append("\nAcceptance: all tests pass\n")
    parts.append("\n## DIREKTIVE {}: {}\n\n".format(nr, title))
    parts.append("{}\n".format(action))
    if files:
        for f in files:
            parts.append("- file: `{}`\n".format(f))
    for i in range(extra_blocks):
        parts.append("\n## DIREKTIVE {}\n".format(nr + i + 1))
        parts.append("\nBlock {}\n".format(i + 1))
    return "".join(parts)


# ─────────────────────────────────────────────────────────────────────
# parse_directive
# ─────────────────────────────────────────────────────────────────────
class TestParseDirective:
    def test_missing_file(self, tmp_path):
        result = dp.parse_directive(str(tmp_path / "nope.md"))
        assert "error" in result
        assert "not found" in result["error"]

    def test_r_number_extracted(self, tmp_path):
        path = _write_directive(tmp_path, "R110-foo.md", _make_body())
        r = dp.parse_directive(path)
        assert r["r_number"] == 110

    def test_topic_extracted(self, tmp_path):
        path = _write_directive(tmp_path, "R110-foo-bar.md", _make_body())
        r = dp.parse_directive(path)
        assert r["topic"] == "foo-bar"

    def test_no_r_number_returns_none(self, tmp_path):
        path = _write_directive(tmp_path, "directive.md", _make_body())
        r = dp.parse_directive(path)
        assert r["r_number"] is None
        # topic falls back to stem
        assert r["topic"] == "directive"

    def test_topic_falls_back_to_stem(self, tmp_path):
        # Filename with no .md suffix → topic uses full stem
        path = _write_directive(tmp_path, "R110-foo", _make_body())
        r = dp.parse_directive(path)
        assert r["topic"] == "R110-foo"

    def test_no_directive_blocks(self, tmp_path):
        path = _write_directive(tmp_path, "R110-noblocks.md",
                                "# R110 nothing here\n\nJust text\n")
        r = dp.parse_directive(path)
        assert r["direktive_blocks"] == []

    def test_single_block_with_title(self, tmp_path):
        path = _write_directive(tmp_path, "R110-single.md",
                                _make_body(nr=1, title="My Title"))
        r = dp.parse_directive(path)
        assert len(r["direktive_blocks"]) == 1
        assert r["direktive_blocks"][0]["title"] == "My Title"

    def test_single_block_with_action(self, tmp_path):
        path = _write_directive(tmp_path, "R110-action.md",
                                _make_body(action="Do the X"))
        r = dp.parse_directive(path)
        assert r["direktive_blocks"][0]["action"] == "Do the X"

    def test_block_without_action(self, tmp_path):
        # Block with no following paragraph → action empty
        path = _write_directive(tmp_path, "R110-noact.md",
                                "# R110 x\n\n## DIREKTIVE 1: T\n")
        r = dp.parse_directive(path)
        assert r["direktive_blocks"][0]["action"] == ""

    def test_multiple_blocks(self, tmp_path):
        path = _write_directive(tmp_path, "R110-multi.md",
                                _make_body(extra_blocks=2))
        r = dp.parse_directive(path)
        assert len(r["direktive_blocks"]) == 3
        assert r["direktive_blocks"][0]["nr"] == 1
        assert r["direktive_blocks"][1]["nr"] == 2
        assert r["direktive_blocks"][2]["nr"] == 3

    def test_files_deduplicated(self, tmp_path):
        path = _write_directive(
            tmp_path, "R110-files.md",
            _make_body(files=["a.py", "a.py", "b.yaml", "c.md"]))
        r = dp.parse_directive(path)
        files = r["direktive_blocks"][0]["files"]
        # Sorted, deduplicated
        assert files == ["a.py", "b.yaml", "c.md"]

    def test_files_various_extensions(self, tmp_path):
        path = _write_directive(
            tmp_path, "R110-fext.md",
            _make_body(files=["x.py", "y.yaml", "z.md", "s.sh",
                              "j.json", "notmatch.txt"]))
        r = dp.parse_directive(path)
        files = r["direktive_blocks"][0]["files"]
        # Heuristic regex matches only py/yaml/md/sh/json
        assert "x.py" in files
        assert "y.yaml" in files
        assert "z.md" in files
        assert "s.sh" in files
        assert "j.json" in files
        # .txt not matched
        assert "notmatch.txt" not in files

    def test_files_in_single_quotes(self, tmp_path):
        # Files mentioned with single quotes too (regex covers both)
        path = _write_directive(
            tmp_path, "R110-sq.md",
            "# R\n\n## DIREKTIVE 1: T\n\n'some/file.py' here\n")
        r = dp.parse_directive(path)
        files = r["direktive_blocks"][0]["files"]
        assert "some/file.py" in files

    def test_no_files_in_block(self, tmp_path):
        path = _write_directive(
            tmp_path, "R110-nofile.md",
            "# R\n\n## DIREKTIVE 1: T\n\nJust action text\n")
        r = dp.parse_directive(path)
        assert r["direktive_blocks"][0]["files"] == []

    def test_scope_extracted(self, tmp_path):
        path = _write_directive(tmp_path, "R110-scope.md", _make_body())
        r = dp.parse_directive(path)
        assert "recipe/" in r["scope"]
        assert "tools/" in r["scope"]

    def test_scope_uppercase_section(self, tmp_path):
        path = _write_directive(
            tmp_path, "R110-scope2.md",
            "# R110 x\n\nSCOPE: recipe/\n\n## DIREKTIVE 1: T\n\nA\n")
        r = dp.parse_directive(path)
        assert "recipe/" in r["scope"]

    def test_no_scope(self, tmp_path):
        path = _write_directive(tmp_path, "R110-noscope.md",
                                "# R110\n\n## DIREKTIVE 1: T\n\nA\n")
        r = dp.parse_directive(path)
        assert r["scope"] == ""

    def test_pre_conditions_extracted(self, tmp_path):
        path = _write_directive(tmp_path, "R110-pre.md", _make_body())
        r = dp.parse_directive(path)
        assert any("must work" in p for p in r["pre_conditions"])

    def test_no_pre_conditions(self, tmp_path):
        path = _write_directive(tmp_path, "R110-nopre.md",
                                "# R110\n\n## DIREKTIVE 1: T\n\nA\n")
        r = dp.parse_directive(path)
        assert r["pre_conditions"] == []

    def test_acceptance_extracted(self, tmp_path):
        path = _write_directive(tmp_path, "R110-acc.md", _make_body())
        r = dp.parse_directive(path)
        assert any("all tests pass" in a for a in r["acceptance"])

    def test_no_acceptance(self, tmp_path):
        path = _write_directive(tmp_path, "R110-noacc.md",
                                "# R110\n\n## DIREKTIVE 1: T\n\nA\n")
        r = dp.parse_directive(path)
        assert r["acceptance"] == []

    def test_full_structure(self, tmp_path):
        path = _write_directive(tmp_path, "R110-full.md", _make_body())
        r = dp.parse_directive(path)
        assert r["directive_path"].endswith("R110-full.md")
        assert r["r_number"] == 110
        assert r["topic"] == "full"
        assert isinstance(r["direktive_blocks"], list)
        assert isinstance(r["pre_conditions"], list)
        assert isinstance(r["acceptance"], list)


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_args_exits_2(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_directive_parser.py"])
        with pytest.raises(SystemExit) as exc:
            dp.main()
        assert exc.value.code == 2
        out = capsys.readouterr()
        # Usage message on stderr
        assert "Usage" in out.err

    def test_missing_file_exits_1(self, monkeypatch, capsys, tmp_path):
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_parser.py",
                             str(tmp_path / "nope.md")])
        with pytest.raises(SystemExit) as exc:
            dp.main()
        assert exc.value.code == 1

    def test_json_output(self, monkeypatch, capsys, tmp_path):
        path = _write_directive(tmp_path, "R110-json.md", _make_body())
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_parser.py", path, "--json"])
        with pytest.raises(SystemExit) as exc:
            dp.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        # Valid JSON
        parsed = json.loads(out)
        assert parsed["r_number"] == 110
        assert parsed["topic"] == "json"

    def test_human_readable_output(self, monkeypatch, capsys, tmp_path):
        path = _write_directive(tmp_path, "R110-human.md",
                                _make_body(nr=1, title="T1"))
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_parser.py", path])
        with pytest.raises(SystemExit) as exc:
            dp.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "Directive:" in out
        assert "Scope:" in out
        assert "DIREKTIVE blocks:" in out
        assert "DIREKTIVE 1" in out

    def test_missing_file_no_json(self, monkeypatch, tmp_path):
        # Without --json, missing file → exit 1
        monkeypatch.setattr(sys, "argv",
                            ["dev_directive_parser.py",
                             str(tmp_path / "nope.md")])
        with pytest.raises(SystemExit) as exc:
            dp.main()
        assert exc.value.code == 1


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_main_no_args(self, monkeypatch):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_directive_parser.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_directive_parser.py"]
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                try:
                    exec(compile(script, "dev_directive_parser.py", "exec"),
                         {"__name__": "__main__",
                          "__file__": "dev_directive_parser.py"})
                except SystemExit as e:
                    assert e.code == 2
            assert "Usage" in buf_err.getvalue()
        finally:
            sys.argv = old_argv
