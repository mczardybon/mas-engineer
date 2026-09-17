"""R110-535 coverage tests for tools/dev_directive_parser.py.

Module: 107 LOC, 43 stmts, 1 main function + main() CLI, 0% covered.

Functions tested:
  - parse_directive(path)         lines 29-84
  - main()                        lines 87-103

Coverage strategy:
  - parse_directive: pure function, easy to test with crafted .md files
  - main: subprocess tests with --json flag and text fallback

Edge cases to cover:
  - File not found (line 31-32)
  - R-number extraction (line 35-36)
  - Topic extraction (line 38-39)
  - DIREKTIVE blocks parsing (lines 41-64)
  - Scope / pre-conditions / acceptance extraction (66-75)
  - main no args (88-91)
  - main --json flag (94-95)
  - main text fallback (96-102)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.dev_directive_parser as dp  # noqa: E402


# ====================== helpers ==================================

SAMPLE_DIRECTIVE = """\
# R110-115 Sub-MAS Apply Directive Spec

## DIREKTIVE 1: parse .mase/directives/

Parse each directive markdown file and emit structured JSON.

The action block describes what should be done.

Files: `tools/dev_directive_parser.py`, `tests/test_directive.py`

## DIREKTIVE 2: apply directive

Apply the parsed directive to the codebase.

Files: `tools/dev_directive_applier.py`
"""

SAMPLE_WITH_SCOPE = """\
# R110-200 My Topic

Scope: recipe/,tools/,docs/

## DIREKTIVE 1: title here

First action paragraph.

Pre-conditions: must have clean working tree.

Acceptance: all tests pass.
"""


def _write_directive(tmp_path, content=SAMPLE_DIRECTIVE, name="R110-115-sub-topic.md"):
    p = tmp_path / name
    p.write_text(content)
    return p


# ====================== parse_directive ==========================

def test_parse_directive_file_not_found(tmp_path):
    """Covers lines 31-32: file not found → error dict."""
    result = dp.parse_directive(tmp_path / "does_not_exist.md")
    assert "error" in result
    assert "file not found" in result["error"]


def test_parse_directive_extracts_r_number(tmp_path):
    """Covers lines 35-36: R<NR>- in filename."""
    p = _write_directive(tmp_path)
    result = dp.parse_directive(p)
    assert result["r_number"] == 110


def test_parse_directive_no_r_number(tmp_path):
    """Covers line 36 False: no R<NR>- in filename."""
    p = tmp_path / "random_file.md"
    p.write_text(SAMPLE_DIRECTIVE)
    result = dp.parse_directive(p)
    assert result["r_number"] is None


def test_parse_directive_extracts_topic(tmp_path):
    """Covers lines 38-39: topic from filename R<NR>-<topic>.md."""
    p = _write_directive(tmp_path, name="R110-sub-topic.md")
    result = dp.parse_directive(p)
    assert result["topic"] == "sub-topic"


def test_parse_directive_topic_fallback_to_stem(tmp_path):
    """Covers line 39 False: no match → p.stem."""
    p = tmp_path / "notamatch.md"
    p.write_text(SAMPLE_DIRECTIVE)
    result = dp.parse_directive(p)
    assert result["topic"] == "notamatch"


def test_parse_directive_single_block(tmp_path):
    """Covers lines 41-64: parse single DIREKTIVE block."""
    p = _write_directive(tmp_path, SAMPLE_DIRECTIVE)
    result = dp.parse_directive(p)
    assert len(result["direktive_blocks"]) == 2
    assert result["direktive_blocks"][0]["nr"] == 1
    assert "parse" in result["direktive_blocks"][0]["title"]


def test_parse_directive_block_action(tmp_path):
    """Covers lines 52-54: action = first paragraph."""
    p = _write_directive(tmp_path, SAMPLE_DIRECTIVE)
    result = dp.parse_directive(p)
    assert "Parse each directive" in result["direktive_blocks"][0]["action"]


def test_parse_directive_block_files_extracted(tmp_path):
    """Covers lines 56-58: files mentioned via `path.ext` heuristic."""
    p = _write_directive(tmp_path, SAMPLE_DIRECTIVE)
    result = dp.parse_directive(p)
    files = result["direktive_blocks"][0]["files"]
    assert "tools/dev_directive_parser.py" in files
    assert "tests/test_directive.py" in files


def test_parse_directive_block_files_unique(tmp_path):
    """Covers line 63: sorted(set(files))."""
    p = _write_directive(tmp_path, SAMPLE_DIRECTIVE)
    result = dp.parse_directive(p)
    files = result["direktive_blocks"][0]["files"]
    # Should be sorted and unique
    assert files == sorted(set(files))


def test_parse_directive_block_title_fallback(tmp_path):
    """Covers lines 49-50: title from '## DIREKTIVE N: <title>' first non-empty line."""
    p = tmp_path / "R110-001.md"
    # Format: "## DIREKTIVE 5" followed by line that becomes title
    p.write_text("## DIREKTIVE 5\nsome-title-here\n\nbody text\n")
    result = dp.parse_directive(p)
    block = result["direktive_blocks"][0]
    # Regex `##\s*DIREKTIVE\s+\d+[:#]?\s*([^\n]+)` captures first non-empty line
    assert block["title"] == "some-title-here"


def test_parse_directive_scope_extraction(tmp_path):
    """Covers lines 66-67: 'Scope:' in text."""
    p = _write_directive(tmp_path, SAMPLE_WITH_SCOPE)
    result = dp.parse_directive(p)
    assert "recipe/" in result["scope"]
    assert "tools/" in result["scope"]


def test_parse_directive_scope_missing(tmp_path):
    """Covers line 67 False: no scope match → empty string."""
    p = _write_directive(tmp_path, SAMPLE_DIRECTIVE)  # no Scope: line
    result = dp.parse_directive(p)
    assert result["scope"] == ""


def test_parse_directive_pre_conditions(tmp_path):
    """Covers lines 69-71: pre-conditions extraction."""
    p = _write_directive(tmp_path, SAMPLE_WITH_SCOPE)
    result = dp.parse_directive(p)
    assert len(result["pre_conditions"]) == 1
    assert "clean working tree" in result["pre_conditions"][0]


def test_parse_directive_acceptance(tmp_path):
    """Covers lines 73-75: acceptance extraction."""
    p = _write_directive(tmp_path, SAMPLE_WITH_SCOPE)
    result = dp.parse_directive(p)
    assert len(result["acceptance"]) == 1
    assert "tests pass" in result["acceptance"][0]


def test_parse_directive_no_direktive_blocks(tmp_path):
    """Covers regex path with no DIREKTIVE blocks → empty blocks."""
    p = tmp_path / "R110-001.md"
    p.write_text("# Just a title\n\nNo DIREKTIVE sections here.\n")
    result = dp.parse_directive(p)
    assert result["direktive_blocks"] == []


# ====================== main / CLI ===============================

def _run_cli(*args):
    cmd = [sys.executable, str(REPO_ROOT / "tools" / "dev_directive_parser.py")] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def test_cli_no_args():
    """Covers lines 88-91: no path → exit 2, usage to stderr."""
    code, out, err = _run_cli()
    assert code == 2
    assert "Usage:" in err


def test_cli_json_output(tmp_path):
    """Covers lines 94-95: --json flag → JSON dump to stdout."""
    p = _write_directive(tmp_path)
    code, out, _ = _run_cli(str(p), "--json")
    assert code == 0
    parsed = json.loads(out)
    assert parsed["r_number"] == 110
    assert "topic" in parsed


def test_cli_text_output(tmp_path):
    """Covers lines 96-102: text fallback output."""
    p = _write_directive(tmp_path)
    code, out, _ = _run_cli(str(p))
    assert code == 0
    assert "Directive:" in out
    assert "Scope:" in out
    assert "DIREKTIVE blocks:" in out


def test_cli_exit_1_on_error(tmp_path):
    """Covers line 103: error in result → exit 1."""
    code, _, _ = _run_cli(str(tmp_path / "missing.md"))
    assert code == 1
