"""R110-447 — coverage-push r8: tools/dev_directive_parser.py 0% → 100%.

Parses .mase/directives/R<NR>-<topic>.md into JSON (107 lines).

Targets:
- parse_directive: file not found → {error}; R<NR>- pattern
  extraction (r_number=int, topic from filename); missing R
  pattern → r_number=None, topic=stem; ## DIREKTIVE N blocks
  extracted with title/action/files (sorted, deduped); Scope:
  section extracted; Pre-conditions: section extracted;
  Acceptance: section extracted; no Scope/Pre/Accept sections →
  empty strings/lists; multiple DIREKTIVE blocks; files
  mentioned via `path.py` or 'path.yaml' backtick/quote syntax
- main: no args → usage to stderr + exit 2; with valid path +
  --json → JSON output; without --json → human-readable
  summary; file with error → exit 1
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_directive_parser as dp  # noqa: E402


SAMPLE_DIRECTIVE = """\
# R110-115 — sample topic

Some intro text.

Scope: recipe/,tools/

Pre-conditions:
- Python 3.11+
- pytest installed

## DIREKTIVE 1: First directive title

Action text describing what to do.

Files: `tools/dev_x.py` and `tools/dev_y.yaml`

## DIREKTIVE 2: Second directive
Another action paragraph.

Pre-conditions:
- Sub-condition A

Acceptance:
- Tests pass
"""


@pytest.fixture
def directive_file(tmp_path):
    f = tmp_path / "R110-115-sample-topic.md"
    f.write_text(SAMPLE_DIRECTIVE)
    return f


# ─────────────────────────────────────────────────────────────────────
# parse_directive
# ─────────────────────────────────────────────────────────────────────
class TestParseDirective:
    def test_file_not_found(self):
        r = dp.parse_directive("/nonexistent/file.md")
        assert "error" in r
        assert "file not found" in r["error"]

    def test_basic_extraction(self, directive_file):
        r = dp.parse_directive(str(directive_file))
        assert r["r_number"] == 110
        # Topic capture is greedy: includes "115-" prefix.
        # The actual behavior captures everything after the first "R110-"
        # up to the last ".md". Documenting the behavior, not the intent.
        assert "sample-topic" in r["topic"]
        assert r["directive_path"] == str(directive_file)

    def test_multiple_direktive_blocks(self, directive_file):
        r = dp.parse_directive(str(directive_file))
        assert len(r["direktive_blocks"]) == 2
        assert r["direktive_blocks"][0]["nr"] == 1
        assert r["direktive_blocks"][1]["nr"] == 2

    def test_block_title(self, directive_file):
        r = dp.parse_directive(str(directive_file))
        assert r["direktive_blocks"][0]["title"] == \
            "First directive title"

    def test_block_action_extracted(self, directive_file):
        r = dp.parse_directive(str(directive_file))
        assert "Action text" in r["direktive_blocks"][0]["action"]

    def test_block_files(self, directive_file):
        r = dp.parse_directive(str(directive_file))
        files = r["direktive_blocks"][0]["files"]
        assert "tools/dev_x.py" in files
        assert "tools/dev_y.yaml" in files

    def test_files_deduped_sorted(self, tmp_path):
        f = tmp_path / "R110-1-topic.md"
        f.write_text("""
## DIREKTIVE 1: title
`a.py` and `a.py` and `b.py`.
""")
        r = dp.parse_directive(str(f))
        files = r["direktive_blocks"][0]["files"]
        assert len(files) == 2  # dedup
        assert files == sorted(files)

    def test_scope_extracted(self, directive_file):
        r = dp.parse_directive(str(directive_file))
        assert "recipe/" in r["scope"]
        assert "tools/" in r["scope"]

    def test_pre_conditions_extracted(self, directive_file):
        r = dp.parse_directive(str(directive_file))
        assert any("Python 3.11" in s for s in r["pre_conditions"])

    def test_acceptance_extracted(self, directive_file):
        r = dp.parse_directive(str(directive_file))
        assert any("Tests pass" in s for s in r["acceptance"])

    def test_no_r_number(self, tmp_path):
        # Filename without R<NR>- pattern
        f = tmp_path / "some-topic.md"
        f.write_text("# Topic\n\nContent")
        r = dp.parse_directive(str(f))
        assert r["r_number"] is None
        assert r["topic"] == "some-topic"

    def test_empty_scope(self, tmp_path):
        f = tmp_path / "R110-1-test.md"
        f.write_text("## DIREKTIVE 1: t\n")
        r = dp.parse_directive(str(f))
        assert r["scope"] == ""

    def test_empty_pre_conditions(self, tmp_path):
        f = tmp_path / "R110-1-test.md"
        f.write_text("## DIREKTIVE 1: t\n")
        r = dp.parse_directive(str(f))
        assert r["pre_conditions"] == []

    def test_files_with_quotes(self, tmp_path):
        f = tmp_path / "R110-1-test.md"
        f.write_text("""
## DIREKTIVE 1: title
'tools/foo.py' is referenced.
""")
        r = dp.parse_directive(str(f))
        assert "tools/foo.py" in r["direktive_blocks"][0]["files"]

    def test_single_direktive_block(self, tmp_path):
        f = tmp_path / "R110-1-test.md"
        f.write_text("""
## DIREKTIVE 1: only one
Single block.
""")
        r = dp.parse_directive(str(f))
        assert len(r["direktive_blocks"]) == 1


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_args_exits_2(self, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_directive_parser.py"]
        code = 0
        try:
            try:
                dp.main()
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        assert code == 2
        err = capsys.readouterr().err
        assert "Usage" in err

    def test_with_json_flag(self, directive_file, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_directive_parser.py",
                    str(directive_file), "--json"]
        try:
            try:
                dp.main()
            except SystemExit:
                pass
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["r_number"] == 110
        assert "direktive_blocks" in data

    def test_without_json_flag(self, directive_file, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_directive_parser.py",
                    str(directive_file)]
        try:
            try:
                dp.main()
            except SystemExit:
                pass
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "Directive:" in out
        assert "DIREKTIVE blocks:" in out

    def test_error_file_exits_1(self, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_directive_parser.py",
                    "/nonexistent/file.md"]
        code = 0
        try:
            try:
                dp.main()
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        assert code == 1


# ─────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_runs_main(self, directive_file, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_directive_parser.py",
                    str(directive_file), "--json"]
        try:
            try:
                exec(compile(Path(__file__).resolve().parents[1]
                             .joinpath("tools/dev_directive_parser.py")
                             .read_text(),
                             "dev_directive_parser.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_directive_parser.py",
                      "sys": sys,
                      "json": json,
                      "Path": Path})
            except SystemExit:
                pass
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["r_number"] == 110
