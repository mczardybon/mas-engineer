"""Tests for tools/e2e_run_all.py — coverage gap closer (R110-589).

Covers the 0% coverage of e2e_run_all.py (241 stmts, 241 missed).
Strategy: exercise the pure helpers and module-level constants that
do not require running the full E2E suite (which needs goose + 20min
of subprocess work). Specifically:

- log() — prints with timestamp and level
- section() — prints bar + title
- find_all_recipes() — returns sorted glob of recipe/**/*.yaml
- REQUIRED_TOP_RECIPE_FIELDS / REQUIRED_SUB_RECIPE_FIELDS — non-empty
  lists containing the expected field names
"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import e2e_run_all as era  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_cwd_after_test():
    """CWD-robustness fixture (R110-589 follow-up).

    Other tests in the suite (notably
    tests/test_dev_dashboard_refresh_r110367.py) leave cwd at `/`
    in their `finally` blocks. Because `find_all_recipes()` uses
    RELATIVE globs (`glob.glob("recipe/*.yaml")`), our glob tests
    see cwd=/ and return [] → spurious failures.

    This autouse fixture saves cwd on entry and restores it on
    exit, then chdirs into REPO_ROOT for the duration of the
    test. After the test, REPO_ROOT is left intact for the NEXT
    test (which is what we want: subsequent tests also get a sane
    cwd even if they don't use this fixture).
    """
    _saved = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        yield
    finally:
        os.chdir(_saved)


def test_log_prints_with_timestamp_and_default_level(capsys):
    """Covers line 49-51: log() prints timestamp + default INFO level + msg."""
    era.log("hello world")
    captured = capsys.readouterr()
    assert "hello world" in captured.out
    assert "[INFO]" in captured.out
    # timestamp has HH:MM:SS format, always 8 chars between brackets
    assert "[INFO]" in captured.out


def test_log_with_custom_level(capsys):
    """Covers line 49-51: log() with non-default level argument."""
    era.log("warning msg", level="WARN")
    captured = capsys.readouterr()
    assert "[WARN]" in captured.out
    assert "warning msg" in captured.out


def test_log_format_includes_bracketed_timestamp(capsys):
    """Covers line 50: ts is bracketed, format '[HH:MM:SS] [LEVEL] msg'."""
    era.log("ts-check", level="DEBUG")
    captured = capsys.readouterr()
    out = captured.out
    # outer pattern: '... [HH:MM:SS] [DEBUG] ts-check\n'
    assert "] [DEBUG] ts-check" in out
    # bracketed timestamp is exactly 8 chars + brackets: '[HH:MM:SS]'
    import re

    m = re.search(r"\[(\d{2}:\d{2}:\d{2})\] \[DEBUG\]", out)
    assert m is not None, f"no bracketed timestamp found in: {out!r}"


def test_section_prints_title_and_bar(capsys):
    """Covers line 54-56: section() prints bar + title."""
    era.section("My Section Title")
    captured = capsys.readouterr().out
    assert "My Section Title" in captured
    # bar is 60 '=' chars
    assert "=" * 60 in captured


def test_section_indents_title(capsys):
    """Covers line 56: title is indented with two spaces."""
    era.section("Indented Title")
    captured = capsys.readouterr().out
    assert "  Indented Title" in captured


def test_find_all_recipes_returns_sorted_list():
    """Covers line 59-60: find_all_recipes() returns sorted glob result."""
    recipes = era.find_all_recipes()
    assert isinstance(recipes, list)
    assert len(recipes) > 0
    # result is sorted (sorted() applied to combined glob)
    assert recipes == sorted(recipes)
    # all paths end with .yaml
    assert all(r.endswith(".yaml") for r in recipes)


def test_find_all_recipes_includes_top_and_sub_dirs():
    """Covers line 60: find_all_recipes() combines recipe/ and recipe/sub/."""
    recipes = era.find_all_recipes()
    # at least one top-level recipe (no '/sub/' in path)
    assert any("/sub/" not in r for r in recipes)
    # at least one sub-recipe
    assert any("/sub/" in r for r in recipes)


def test_required_top_recipe_fields_is_nonempty_with_expected_keys():
    """Covers line 45: REQUIRED_TOP_RECIPE_FIELDS is a non-empty list."""
    fields = era.REQUIRED_TOP_RECIPE_FIELDS
    assert isinstance(fields, list)
    assert len(fields) > 0
    # minimal invariant: name + title + description should always be required
    for key in ("name", "title", "description"):
        assert key in fields, f"missing key {key!r} in REQUIRED_TOP_RECIPE_FIELDS"


def test_required_sub_recipe_fields_is_nonempty_with_expected_keys():
    """Covers line 46: REQUIRED_SUB_RECIPE_FIELDS is a non-empty list."""
    fields = era.REQUIRED_SUB_RECIPE_FIELDS
    assert isinstance(fields, list)
    assert len(fields) > 0
    # sub-recipes may NOT require 'version' (top-level does)
    for key in ("name", "title", "description"):
        assert key in fields, f"missing key {key!r} in REQUIRED_SUB_RECIPE_FIELDS"
