"""Targeted coverage push for tools/dev_im_finder_scan_lib.py — R110-502.

Target: dev_im_finder_scan_lib.py (647 stmts, 11% covered → goal ~30%).
Per skill `mas-engineer-coverage-push-workflow` pitfall 9: module-level
side-effects (sys.argv parsing in _collect_scope_dirs, EXCLUDED_DIR_NAMES,
etc.) need monkeypatch.chdir(tmp_path) BEFORE import. We use INLINE
imports (not subprocess) so pytest-cov actually instruments the module.

This avoids the "subprocess coverage not measured" problem we hit on
R110-501 — inline imports are visible to coverage, subprocess imports
are not unless you set COVERAGE_PROCESS_START.

Per skill pitfall 8: Always MEASURE before setting +pp target. Pre-run
measure showed 11% (70/647 stmts covered). Goal: +15-20pp via pure-
helper tests for ~12 functions.

Coverage targets (functions currently uncovered):
- compute_issue_hash (delegates to dev_issue_db)
- compute_structural_pattern (delegates to dev_issue_db)
- _is_path_excluded (substring match in EXCLUDED_PATH_PATTERNS)
- _is_in_table_or_example (heuristic for markdown context)
- _is_in_code_block (fenced ``` counting)
- _is_in_docstring (triple-quote counting)
- _is_pycache_or_backup (path pattern check)
- _is_runtime_var_assert (regex-based runtime detection)
- _is_self_reference (assert `LITERAL in RHS` heuristic)
- _walk_count_literal (filesystem walker with early-exit at 3 hits)
- _is_common_value (cached filesystem walk)
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"


@pytest.fixture
def lib_module(tmp_path, monkeypatch):
    """Import dev_im_finder_scan_lib inline with chdir sandboxing.

    Per skill `mas-engineer-coverage-push-workflow` pitfall 9:
    chdir(tmp_path) BEFORE import so module-level code that
    reads SCAN_DIRS / EXCLUDED_PATH_PATTERNS / _collect_scope_dirs
    gets a clean slate. argv is neutralized so --include-external
    is not set.
    """
    monkeypatch.chdir(tmp_path)
    # Neutralize argv so --include-external-recipes is not detected
    monkeypatch.setattr(sys, "argv", ["dev_im_finder_scan_lib"])
    # Clear any cached env-var
    monkeypatch.delenv("MAS_INCLUDE_EXTERNAL_RECIPES", raising=False)

    # Now import (with tools.* prefix so coverage sees it)
    if "tools.dev_im_finder_scan_lib" in sys.modules:
        return sys.modules["tools.dev_im_finder_scan_lib"]

    # Add tools/ to path so the module is loadable as `tools.dev_im_finder_scan_lib`
    sys.path.insert(0, str(TOOLS_DIR))
    import tools.dev_im_finder_scan_lib as lib  # noqa: E402
    return lib


# ─────────────────────────────────────────────────────────
# compute_issue_hash + compute_structural_pattern
# ─────────────────────────────────────────────────────────

def test_compute_issue_hash_returns_string(lib_module):
    """compute_issue_hash delegates to dev_issue_db and returns a hash."""
    result = lib_module.compute_issue_hash("tools/foo.py", "stale_literal", "pat_xyz")
    assert isinstance(result, str)
    assert len(result) >= 8


def test_compute_structural_pattern_returns_string(lib_module):
    """compute_structural_pattern returns a structural pattern string."""
    result = lib_module.compute_structural_pattern("stale_literal", "tools/foo.py")
    assert isinstance(result, str)


# ─────────────────────────────────────────────────────────
# _is_path_excluded
# ─────────────────────────────────────────────────────────

def test_is_path_excluded_external_recipes(lib_module):
    """Path containing /.config/goose/recipes/ is excluded by default."""
    result = lib_module._is_path_excluded("/home/x/.config/goose/recipes/foo.yaml")
    assert result is True


def test_is_path_excluded_normal_path(lib_module):
    """Normal path is NOT excluded."""
    result = lib_module._is_path_excluded("/home/x/project/recipe/sub/foo.yaml")
    assert result is False


def test_is_path_excluded_original_yaml(lib_module):
    """-ORIGINAL.yaml files are excluded (R84 archival copies)."""
    result = lib_module._is_path_excluded("/home/x/project/recipe/sub/foo-ORIGINAL.yaml")
    assert result is True


# ─────────────────────────────────────────────────────────
# _is_in_table_or_example
# ─────────────────────────────────────────────────────────

def test_is_in_table_or_example_pipe_before(lib_module):
    """Previous line starts with | → True."""
    lines = ["normal text", "| col1 | col2 |", "  some_value  "]
    assert lib_module._is_in_table_or_example(lines, 2) is True


def test_is_in_table_or_example_pipe_after(lib_module):
    """Next line starts with | → True."""
    lines = ["  some_value  ", "| col1 | col2 |"]
    assert lib_module._is_in_table_or_example(lines, 0) is True


def test_is_in_table_or_example_block_next(lib_module):
    """Next line contains 'Example' → True (impl checks NEXT, not prev)."""
    lines = ["  some_value  ", "Example: foo bar"]
    assert lib_module._is_in_table_or_example(lines, 0) is True


def test_is_in_table_or_example_neither(lib_module):
    """No table/example context → False."""
    lines = ["intro paragraph", "  some_value  ", "outro paragraph"]
    assert lib_module._is_in_table_or_example(lines, 1) is False


# ─────────────────────────────────────────────────────────
# _is_in_code_block
# ─────────────────────────────────────────────────────────

def test_is_in_code_block_open(lib_module):
    """Inside ``` ... ``` → True (odd fence count)."""
    lines = ["```python", "x = 1", "y = 2", "```"]
    # Line 1: 1 fence before (line 0) → True
    assert lib_module._is_in_code_block(lines, 1) is True
    # Line 2: 1 fence before → True
    assert lib_module._is_in_code_block(lines, 2) is True


def test_is_in_code_block_closed(lib_module):
    """Outside ``` ... ``` → False (even fence count)."""
    lines = ["intro", "x = 1", "```", "y = 2"]
    # Line 1: 0 fences before → False
    assert lib_module._is_in_code_block(lines, 1) is False
    # Line 0: 0 fences before → False
    assert lib_module._is_in_code_block(lines, 0) is False


def test_is_in_code_block_at_fence(lib_module):
    """The fence line itself counts (starts with ```)."""
    lines = ["intro", "```", "y = 2"]
    # Line 1: 1 fence at line 1 → True
    assert lib_module._is_in_code_block(lines, 1) is True


# ─────────────────────────────────────────────────────────
# _is_in_docstring
# ─────────────────────────────────────────────────────────

def test_is_in_docstring_odd_quotes(lib_module):
    """Odd number of \"\"\" before line_idx → True (inside docstring)."""
    src_lines = ['"""', 'docstring line 1', 'docstring line 2', 'still inside', '"""']
    assert lib_module._is_in_docstring(src_lines, 2) is True


def test_is_in_docstring_even_quotes(lib_module):
    """Even number of \"\"\" → False (outside docstring)."""
    src_lines = ['"""', 'docstring line', '"""', 'regular code']
    assert lib_module._is_in_docstring(src_lines, 3) is False


# ─────────────────────────────────────────────────────────
# _is_pycache_or_backup
# ─────────────────────────────────────────────────────────

def test_is_pycache_or_backup_true_pycache(lib_module):
    """Path containing __pycache__ → True."""
    assert lib_module._is_pycache_or_backup("/x/__pycache__/foo.pyc") is True


def test_is_pycache_or_backup_true_pyc(lib_module):
    """Path ending in .pyc → True."""
    assert lib_module._is_pycache_or_backup("/x/foo.pyc") is True


def test_is_pycache_or_backup_true_llm_backup(lib_module):
    """Path containing /llm-backup/ → True."""
    assert lib_module._is_pycache_or_backup("/x/llm-backup/foo.py") is True


def test_is_pycache_or_backup_false(lib_module):
    """Normal path → False."""
    assert lib_module._is_pycache_or_backup("/x/project/foo.py") is False


# ─────────────────────────────────────────────────────────
# _is_self_reference
# ─────────────────────────────────────────────────────────

def test_is_self_reference_true(lib_module):
    """Literal in quoted RHS matching literal → True (self-reference)."""
    assert lib_module._is_self_reference('test_foo', 'assert "test_foo" in "test_foo"') is True


def test_is_self_reference_false_different(lib_module):
    """Literal differs from RHS → False."""
    assert lib_module._is_self_reference('test_foo', 'assert "test_foo" in real_var') is False


def test_is_self_reference_no_in_keyword(lib_module):
    """Line without `in` keyword → False."""
    assert lib_module._is_self_reference('test_foo', 'just some text') is False


# ─────────────────────────────────────────────────────────
# _is_runtime_var_assert
# ─────────────────────────────────────────────────────────

def test_is_runtime_var_assert_method_call(lib_module):
    """Line with method-call RHS (capsys.readouterr().out) → True."""
    line = 'assert "ERROR" in captured.out'
    assert lib_module._is_runtime_var_assert(line) is True


def test_is_runtime_var_assert_runtime_var_name(lib_module):
    """Plain var RHS matching runtime-var → True (rules is runtime-var)."""
    line = 'assert "key_value" in rules'
    assert lib_module._is_runtime_var_assert(line) is True


def test_is_runtime_var_assert_static_source(lib_module):
    """Reading from a static module var → False (not runtime)."""
    line = 'assert "ERROR" in SOURCE_LITERAL_CONST'
    assert lib_module._is_runtime_var_assert(line) is False


def test_is_runtime_var_assert_no_match(lib_module):
    """Line without `assert "x" in y` pattern → False."""
    line = 'assert x == y'
    assert lib_module._is_runtime_var_assert(line) is False


# ─────────────────────────────────────────────────────────
# _walk_count_literal
# ─────────────────────────────────────────────────────────

def test_walk_count_literal_zero_hits(lib_module, tmp_path):
    """Walk a dir with no matching files → 0 hits."""
    (tmp_path / "test.txt").write_text("no match here")
    hits = lib_module._walk_count_literal(str(tmp_path), "X_NONEXISTENT", 0)
    assert hits == 0


def test_walk_count_literal_with_match(lib_module, tmp_path):
    """Walk a dir with 1 matching file → 1 hit."""
    (tmp_path / "test.txt").write_text("contains MATCHED_LITERAL here")
    hits = lib_module._walk_count_literal(str(tmp_path), "MATCHED_LITERAL", 0)
    assert hits == 1


def test_walk_count_literal_early_exit(lib_module, tmp_path):
    """Walk many matching files, hits stop at 3 (early-exit)."""
    for i in range(10):
        (tmp_path / f"f{i}.txt").write_text("contains TARGET_LITERAL")
    hits = lib_module._walk_count_literal(str(tmp_path), "TARGET_LITERAL", 0)
    assert hits == 3


# ─────────────────────────────────────────────────────────
# _is_common_value
# ─────────────────────────────────────────────────────────

def test_is_common_value_rare_literal(lib_module, tmp_path):
    """Rare literal in 2 files → False (less than 3 hits)."""
    (tmp_path / "a.txt").write_text("RARE_LITERAL_xyz")
    (tmp_path / "b.txt").write_text("RARE_LITERAL_xyz")
    result = lib_module._is_common_value("RARE_LITERAL_xyz", [str(tmp_path)])
    assert result is False


def test_is_common_value_common_literal(lib_module, tmp_path):
    """Common literal in 3+ files → True (cache miss → walk → True)."""
    for i in range(3):
        (tmp_path / f"f{i}.txt").write_text("COMMON_LITERAL_abc")
    result = lib_module._is_common_value("COMMON_LITERAL_abc", [str(tmp_path)])
    assert result is True


def test_is_common_value_cache_hit(lib_module, tmp_path):
    """Second call with same args → cached True (no re-walk)."""
    key = ("CACHED_LITERAL", frozenset([str(tmp_path)]))
    lib_module._COMMON_VALUE_CACHE[key] = True
    result = lib_module._is_common_value("CACHED_LITERAL", [str(tmp_path)])
    assert result is True


def test_is_common_value_skips_nonexistent_dir(lib_module):
    """Non-existent search dir is skipped (no crash)."""
    result = lib_module._is_common_value("ANY_LITERAL", ["/nonexistent/path/xyz"])
    assert result is False


def test_is_common_value_prunes_mase_data_dirs(lib_module, tmp_path):
    """.mase subdirs in _SD_DATA_DIRS are pruned."""
    # Create .mase/mcp/foo.txt with literal — pruned
    mase_mcp = tmp_path / ".mase" / "mcp"
    mase_mcp.mkdir(parents=True)
    (mase_mcp / "foo.txt").write_text("PRUNED_LITERAL_xyz")
    # Create .mase/directives/ with only 1 file — NOT pruned but below threshold
    directives = tmp_path / ".mase" / "directives"
    directives.mkdir(parents=True)
    (directives / "a.txt").write_text("PRUNED_LITERAL_xyz")
    # Walk .mase — only directives has 1 file (mcp pruned), below 3
    result = lib_module._is_common_value("PRUNED_LITERAL_xyz", [str(tmp_path / ".mase")])
    assert result is False
