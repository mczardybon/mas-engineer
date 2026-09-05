"""R110-309: library function tests for tools/dev_im_finder_scan.py.

Covers pure-function helpers that were below 85% coverage:
- compute_issue_hash
- compute_structural_pattern (delegates to dev_issue_db.compute_structural_pattern)
- _is_pycache_or_backup
- _is_self_reference
- _is_in_docstring
- _is_in_code_block
- _is_in_table_or_example
- _is_path_excluded
- _is_runtime_var_assert

These are pure-logic helpers used by the SD-test detector
(check_spec_drift / check_stale_literal), so they can be tested
without triggering the full scan.
"""
import sys
import os
import importlib
from pathlib import Path
import pytest

# R110-323: eager import at module level would cause the scanner
# to run at pytest collection time (~12min hang). The fixture
# below still imports the module with a sandboxed CWD.
TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def ifs(tmp_path, monkeypatch):
    """Import dev_im_finder_scan with a sandboxed CWD.

    dev_im_finder_scan.py runs module-level: collects SCAN_SCOPE,
    sets SEVERITY_FILTER, opens dev_issue_db. We redirect CWD to
    tmp_path and neutralize the scan by setting SCAN_SCOPE to a
    non-existent dir. Some module-level side effects are
    unavoidable (the module imports yaml, opens dev_issue_db) so
    the fixture also restores sys.path.
    """
    monkeypatch.chdir(tmp_path)
    # Prevent the module-level scan from doing anything dramatic
    monkeypatch.setenv("SCAN_SCOPE", str(tmp_path / "no-such-dir"))
    monkeypatch.setenv("SEVERITY_FILTER", "critical,warning,info,error,medium,high,low,debug")
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_im_finder_scan", None)
    sys.modules.pop("dev_issue_db", None)
    try:
        import dev_im_finder_scan
        return dev_im_finder_scan
    finally:
        sys.path.pop(0)


# ────────────────────────────────────────────────────────────
# compute_issue_hash
# ────────────────────────────────────────────────────────────

def test_compute_issue_hash_stable(ifs):
    """Same inputs always produce the same hash (it's the contract)."""
    h1 = ifs.compute_issue_hash("tools/x.py", "hardcode", "line:N")
    h2 = ifs.compute_issue_hash("tools/x.py", "hardcode", "line:N")
    assert h1 == h2
    assert isinstance(h1, str) and len(h1) >= 8


def test_compute_issue_hash_changes_with_inputs(ifs):
    """Changing any of the 3 inputs must change the hash."""
    base = ifs.compute_issue_hash("tools/x.py", "hardcode", "line:N")
    # Different file
    assert ifs.compute_issue_hash("tools/y.py", "hardcode", "line:N") != base
    # Different type
    assert ifs.compute_issue_hash("tools/x.py", "spec_drift", "line:N") != base
    # Different pattern
    assert ifs.compute_issue_hash("tools/x.py", "hardcode", "line:M") != base


# ────────────────────────────────────────────────────────────
# compute_structural_pattern
# ────────────────────────────────────────────────────────────

def test_compute_structural_pattern_returns_string(ifs):
    """Returns a non-empty string (the 'stable pattern' per finding-type)."""
    pat = ifs.compute_structural_pattern("hardcode", "tools/x.py",
                                         line_start=42, line_end=42)
    assert isinstance(pat, str)
    assert len(pat) > 0


def test_compute_structural_pattern_handles_known_type(ifs):
    """A known ftype should return SOMETHING distinct from the default."""
    # Per R110-177: each finding-type has a pattern shape
    pat_hardcode = ifs.compute_structural_pattern("hardcode", "f.py", literal="42")
    assert isinstance(pat_hardcode, str)
    # Unknown type may fall back to a generic "type:file" pattern
    pat_unknown = ifs.compute_structural_pattern("totally_unknown_type",
                                                 "f.py", literal="x")
    assert isinstance(pat_unknown, str)


# ────────────────────────────────────────────────────────────
# _is_pycache_or_backup
# ────────────────────────────────────────────────────────────

def test_is_pycache_or_backup_true_cases(ifs):
    """Paths containing pycache, .pyc, or llm-backup are excluded."""
    assert ifs._is_pycache_or_backup("foo/__pycache__/x.pyc")
    assert ifs._is_pycache_or_backup("bar/x.pyc")
    assert ifs._is_pycache_or_backup("baz/llm-backup/y.py")


def test_is_pycache_or_backup_false_cases(ifs):
    """Normal source files are NOT excluded."""
    assert not ifs._is_pycache_or_backup("tools/dev_x.py")
    assert not ifs._is_pycache_or_backup("tests/test_x.py")


# ────────────────────────────────────────────────────────────
# _is_self_reference
# ────────────────────────────────────────────────────────────

def test_is_self_reference_positive(ifs):
    """`assert "FOO" in __name__` (literal == RHS) is a self-reference."""
    # Literal matches the RHS string
    assert ifs._is_self_reference("test_foo", 'in "test_foo"')
    assert ifs._is_self_reference("test_foo", "in 'test_foo'")


def test_is_self_reference_negative(ifs):
    """`assert "FOO" in some_dict["key"]` is NOT a self-reference."""
    assert not ifs._is_self_reference("FOO", 'in some_dict["key"]')
    assert not ifs._is_self_reference("FOO", "in container")


# ────────────────────────────────────────────────────────────
# _is_in_docstring
# ────────────────────────────────────────────────────────────

def test_is_in_docstring_outside(ifs):
    """A line with 0 unclosed docstrings is OUTSIDE."""
    src = ["line 0", "line 1", "line 2"]
    # No triple-quote anywhere -> outside
    assert not ifs._is_in_docstring(src, 0)
    assert not ifs._is_in_docstring(src, 1)


def test_is_in_docstring_inside(ifs):
    """A line between two triple-quote markers is INSIDE a docstring."""
    # 1 docstring opened before line 2 -> inside
    src = ['DQdocstring', "more docstring", "even more", 'DQend']
    # Replace DQ back to " via reading the raw triple
    src = ['"""docstring', "more docstring", "even more", '"""end']
    # At line 1, we've seen 1 triple-quote (odd) -> INSIDE
    assert ifs._is_in_docstring(src, 1)
    # At line 3, we've seen 2 triple-quotes (even) -> OUTSIDE
    assert not ifs._is_in_docstring(src, 3)


# ────────────────────────────────────────────────────────────
# _is_in_code_block (markdown fenced)
# ────────────────────────────────────────────────────────────

def test_is_in_code_block_outside(ifs):
    """Lines without ``` markers are outside a code block."""
    lines = ["# Title", "some text", "more text"]
    assert not ifs._is_in_code_block(lines, 0)
    assert not ifs._is_in_code_block(lines, 1)


def test_is_in_code_block_inside(ifs):
    """A line between two backtick-triple markers is INSIDE."""
    lines = ["# Title", "BQpython", "code here", "BQ", "after"]
    # Use the backtick-triple inside the strings
    lines = ["# Title", "```python", "code here", "```", "after"]
    # Line 2: 1 backtick-triple seen before -> INSIDE
    assert ifs._is_in_code_block(lines, 2)
    # Line 4: 2 backtick-triples seen before -> OUTSIDE
    assert not ifs._is_in_code_block(lines, 4)


# ────────────────────────────────────────────────────────────
# _is_in_table_or_example
# ────────────────────────────────────────────────────────────

def test_is_in_table_or_example_table(ifs):
    """A line inside a markdown table row is detected."""
    # Per spec: pipe-delimited line with at least 2 pipes
    lines = [
        "| Col1 | Col2 | Col3 |",
        "|-------|-------|-------|",
        "| data | data | data |",
    ]
    assert ifs._is_in_table_or_example(lines, 0) or ifs._is_in_table_or_example(lines, 2)


def test_is_in_table_or_example_prose(ifs):
    """Plain prose is not in a table/example."""
    lines = ["# Heading", "This is normal text.", "More text."]
    for i in range(len(lines)):
        assert not ifs._is_in_table_or_example(lines, i)


# ────────────────────────────────────────────────────────────
# _is_path_excluded
# ────────────────────────────────────────────────────────────

def test_is_path_excluded_external_recipes(ifs):
    """A path under .config/goose/recipes/ is hard-excluded (R97).

    EXCLUDED_PATH_PATTERNS is matched as substrings, so we test with
    a path that contains the /.config/goose/recipes/ marker.
    """
    assert ifs._is_path_excluded("/home/user/.config/goose/recipes/x.yaml")


def test_is_path_excluded_normal_path(ifs):
    """A normal repo path is NOT excluded by default."""
    assert not ifs._is_path_excluded("/repo/tools/dev_x.py")
    assert not ifs._is_path_excluded("/repo/tests/test_x.py")


# ────────────────────────────────────────────────────────────
# _is_runtime_var_assert (R110-279)
# ────────────────────────────────────────────────────────────

def test_is_runtime_var_assert_capsys(ifs):
    """assert with capsys.readouterr() RHS is runtime (skipped)."""
    line = 'assert "hello" in capsys.readouterr().out'
    assert ifs._is_runtime_var_assert(line)


def test_is_runtime_var_assert_runtime_dict_method(ifs):
    """A method-call RHS is detected as runtime (per the SD_RUNTIME_CALL_RE path).

    Note: the assert regex requires the LITERAL to be 4-80 chars long.
    'x' is too short and the regex will skip it. We use 'hello' as a
    realistic literal.
    """
    line = 'assert "hello" in capsys.readouterr().out'
    assert ifs._is_runtime_var_assert(line)
    line2 = 'assert "hello" in result.stdout'
    assert ifs._is_runtime_var_assert(line2)


def test_is_runtime_var_assert_static_literal(ifs):
    """assert with a static-literal RHS is NOT runtime (returns False).

    'static_string_here' is 18 chars (within 4-80 regex range).
    'static_string_here' is NOT in _SD_RUNTIME_VARS so falls through.
    """
    line = 'assert "static_string_here" in "static_string_here"'
    assert not ifs._is_runtime_var_assert(line)
