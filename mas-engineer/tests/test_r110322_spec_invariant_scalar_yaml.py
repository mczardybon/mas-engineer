"""
R110-322 regression tests for dev_spec_invariant.extract_count_from_recipes.

Bug: top-level string scalars (e.g. `5 ab here`) in a yaml recipe were
silently dropped by `if not isinstance(data, (dict, list)): continue`.
A top-level string is exactly the kind of single-line scalar value the
docstring promises to scan, so a recipe whose entire body is a one-liner
count-declaration was being skipped — a real spec-drift false negative.

Fix: now any node that walk() can handle is walked; only None
(empty yaml / parse-to-null) is treated as "no data".

These tests pin the fixed behavior AND the unchanged behavior
(non-str top-level scalars like int, float, bool are still ignored).

Subprocess pattern (R110-310/R110-311): spawn `python3 tools/dev_spec_invariant.py`
from the repo root so that the conftest's sitecustomize.py +
COVERAGE_PROCESS_START instruments the subprocess for coverage tracking.
This is what gets dev_spec_invariant.py out of the 0%-cov bucket — R110-322
moves the file toward 100% just by running real CLI invocations.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "dev_spec_invariant.py"


def _run_repo(args, tmp_repo, timeout=20):
    """Run `python3 tools/dev_spec_invariant.py <args>` against tmp_repo."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args, "--repo-root", str(tmp_repo)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture
def tmp_repo(tmp_path):
    """A fresh repo-root with tests/ and recipe/sub/ subdirs."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "recipe" / "sub").mkdir(parents=True)
    (tmp_path / "recipe" / "instructions").mkdir(parents=True)
    return tmp_path


def _write(path, content):
    path.write_text(content)
    return path


class TestTopLevelScalar:
    """Top-level string scalar with a count-declaration IS scanned."""

    def test_top_level_quoted_string_with_count_produces_no_finding_when_match(
        self, tmp_repo
    ):
        """End-to-end via CLI: test asserts '5 ab', recipe is top-level
        string '5 ab here' — must match (exit 0, no finding)."""
        _write(
            tmp_repo / "tests" / "test_t.py",
            'def test_t():\n    assert "5 ab" in "5 ab"\n',
        )
        _write(tmp_repo / "recipe" / "sub" / "r.yaml", '"we have 5 ab here"\n')
        rc, out, err = _run_repo([], tmp_repo)
        assert rc == 0, f"expected match (rc=0), got rc={rc} out={out!r} err={err!r}"
        # No INVARIANT- finding in output
        assert "INVARIANT-" not in out, f"unexpected finding: {out}"

    def test_top_level_unquoted_string_with_count_produces_no_finding_when_match(
        self, tmp_repo
    ):
        """Same as above but unquoted scalar: yaml parses to string too."""
        _write(
            tmp_repo / "tests" / "test_t.py",
            'def test_t():\n    assert "5 ab" in "5 ab"\n',
        )
        _write(tmp_repo / "recipe" / "sub" / "r.yaml", "5 ab here\n")
        rc, out, err = _run_repo([], tmp_repo)
        assert rc == 0, f"expected match (rc=0), got rc={rc} out={out!r} err={err!r}"
        assert "INVARIANT-" not in out, f"unexpected finding: {out}"

    def test_top_level_string_with_mismatched_count_emits_finding(self, tmp_repo):
        """End-to-end: test asserts '5 ab' but recipe is top-level '7 ab' →
        INVARIANT-ab BLOCKER finding (was silently MISSING before R110-322)."""
        _write(
            tmp_repo / "tests" / "test_t.py",
            'def test_t():\n    assert "5 ab" in "5 ab"\n',
        )
        _write(tmp_repo / "recipe" / "sub" / "r.yaml", '"we have 7 ab"\n')
        rc, out, err = _run_repo([], tmp_repo)
        assert rc == 1, f"expected mismatch (rc=1), got rc={rc} out={out!r}"
        assert "INVARIANT-ab" in out, (
            "R110-322 fix must trigger INVARIANT-ab on top-level scalar "
            f"recipe with contradicting count; got: {out!r}"
        )
        # The description should mention both 5 (test) and 7 (recipe)
        assert "5" in out and "7" in out, (
            f"finding should show the 5 vs 7 divergence; got: {out!r}"
        )

    def test_top_level_string_with_blacklisted_type_still_skipped(self, tmp_repo):
        """TYPE_BLACKLIST (e.g. 'tests') is still honored at the top level."""
        _write(
            tmp_repo / "tests" / "test_t.py",
            'def test_t():\n    assert "5 ab" in "5 ab"\n',
        )
        # Recipe has '5 tests' which is blacklisted; should not appear
        _write(tmp_repo / "recipe" / "sub" / "r.yaml", '"5 tests here"\n')
        rc, out, err = _run_repo([], tmp_repo)
        # The test asserts '5 ab'; recipe has '5 tests' (blacklisted) →
        # no 'ab' recipe entry → INVARIANT-ab finding
        assert "INVARIANT-ab" in out, (
            "tests/5-ab vs recipe/no-ab should produce INVARIANT-ab finding; "
            f"got: {out!r}"
        )


class TestTopLevelNonString:
    """Top-level non-string scalars (int, float, bool) are still ignored."""

    def test_top_level_int_in_recipe_does_not_match_count(self, tmp_repo):
        """Regression: top-level int must not be scanned (walk() only walks
        str/dict/list). So '5 ab' assertion finds no recipe entry → finding."""
        _write(
            tmp_repo / "tests" / "test_t.py",
            'def test_t():\n    assert "5 ab" in "5 ab"\n',
        )
        _write(tmp_repo / "recipe" / "sub" / "r.yaml", "42\n")
        rc, out, err = _run_repo([], tmp_repo)
        assert rc == 1, f"expected mismatch (rc=1), got rc={rc}"
        assert "INVARIANT-ab" in out, (
            "top-level int recipe should not extract '5 ab' (still skipped); "
            f"got: {out!r}"
        )

    def test_empty_recipe_yaml_does_not_crash(self, tmp_repo):
        """Regression: empty yaml parses to None and must be skipped cleanly."""
        _write(
            tmp_repo / "tests" / "test_t.py",
            'def test_t():\n    assert "5 ab" in "5 ab"\n',
        )
        _write(tmp_repo / "recipe" / "sub" / "r.yaml", "")
        rc, out, err = _run_repo([], tmp_repo)
        # Should not crash; finding expected (no recipe entry for 'ab')
        assert "Traceback" not in err, f"empty yaml caused crash: {err!r}"
        assert "INVARIANT-ab" in out


class TestTopLevelScalarNoRegression:
    """Existing dict/list walks still work (no regression)."""

    def test_dict_with_nested_string_still_matches(self, tmp_repo):
        """Pre-existing dict-walk behavior unchanged."""
        _write(
            tmp_repo / "tests" / "test_t.py",
            'def test_t():\n    assert "5 ab" in "5 ab"\n',
        )
        _write(
            tmp_repo / "recipe" / "sub" / "r.yaml",
            "a:\n  b:\n    c: \"5 ab\"\n",
        )
        rc, out, err = _run_repo([], tmp_repo)
        assert rc == 0, f"expected match (rc=0), got rc={rc} out={out!r}"
        assert "INVARIANT-" not in out

    def test_list_of_strings_still_matches(self, tmp_repo):
        """Pre-existing list-walk behavior unchanged."""
        _write(
            tmp_repo / "tests" / "test_t.py",
            'def test_t():\n    assert "5 ab" in "5 ab"\n    assert "7 cd" in "7 cd"\n',
        )
        _write(
            tmp_repo / "recipe" / "sub" / "r.yaml",
            '- "5 ab step 1"\n- "7 cd step 2"\n',
        )
        rc, out, err = _run_repo([], tmp_repo)
        assert rc == 0, f"expected match (rc=0), got rc={rc} out={out!r}"
        assert "INVARIANT-" not in out
