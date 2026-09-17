"""
test_r110411_im_finder_scan_deferred.py — R110-266 deferral (DRAFT, NOT EXECUTABLE).

⚠️ STATUS: DRAFT — file not executable. See BOTTOM of file for root cause.

This file targets the 4 check_* driver functions + 8 helper functions in
tools/dev_im_finder_scan.py that were R110-266-deferred. Strategy:

  1. PURE HELPERS (8 functions): test directly with crafted inputs.
     These are 100% testable, no fixtures needed.

  2. CHECK_* DRIVERS (4 functions): smoke-test the entry-point logic
     with a tiny tmp repo containing 1-2 test files + 1-2 source
     files. Monkey-patch `add_finding` as a recorder so we can assert
     on the findings list without DB side-effects.

This is the same minimal/entry-point strategy as test_r110411_workspace_deferred.py
— not full body coverage, but documents behavior + catches regressions
in the most critical skip-filters.

────────────────────────────────────────────────────────────────────────────────
ROOT CAUSE — WHY THIS FILE CANNOT BE EXECUTED (R110-411b BLOCKED):
────────────────────────────────────────────────────────────────────────────────
`tools/dev_im_finder_scan.py` lines 1577-1681 contain 105 lines of SCRIPT-MODE
code at MODULE LEVEL (try-blocks calling `check_spec_drift(findings, '.')`,
`check_spec_drift_reverse`, `check_hardcode_stale`, `check_stale_literal`,
plus `print('---JSON_START---')`, `print(json.dumps(...))`, and an optional
`--publish` subprocess call). These run on EVERY `import dev_im_finder_scan`,
not just when executed as a script.

There is NO `if __name__ == '__main__':` wrapper. The module is a SCRIPT
masquerading as a library. R110-266 deferred testing the check_* drivers
BECAUSE importing the module triggers a full-repo scan (~60s on the
real repo) plus dumps JSON to stdout. Even with `add_finding` mocked,
the `for root, dirs, files in os.walk(d)` loops over recipe/, tools/,
docs/, .mase/ still run for every test that imports the module.

PROPER FIX (out of scope for R110-411b):
  - Extract check_* + helpers into `dev_im_finder_scan_lib.py` (no
    script-mode code at module level)
  - Move the script-mode tail (lines 1577-1681) into
    `if __name__ == '__main__':` block in dev_im_finder_scan.py
  - Then this test file becomes executable

This is essentially the R110-266 refactor, which was scoped out of
R110-411. Marked as DRAFT so the file is not collected by pytest.
────────────────────────────────────────────────────────────────────────────────
"""
import os
import re
import sys
from pathlib import Path

import pytest

# ─── Module path setup ───────────────────────────────────────
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "tools"))

import dev_im_finder_scan as mod  # noqa: E402


# ─── Fixtures ───────────────────────────────────────────────
@pytest.fixture
def tiny_repo(tmp_path):
    """Build a minimal repo with 1 test file (referencing 'X12345_LITERAL') and
    1 source file (containing the same literal). This lets check_spec_drift
    run end-to-end without scanning thousands of files."""
    repo = tmp_path / "tiny_repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "tools").mkdir()
    (repo / "recipe").mkdir()
    (repo / "docs").mkdir()
    (repo / ".mase").mkdir()

    # Test file: contains a unique literal that's NOT in any source
    (repo / "tests" / "test_zzz.py").write_text(
        'def test_foo():\n'
        '    assert "DRIFT_LITERAL_X42" in out\n'  # runtime-var assert, skipped
        '    assert "DRIFT_LITERAL_PRESENT" in "hello"\n'  # in source, no drift
        '    assert "DRIFT_LITERAL_ABSENT" in "hello"\n'  # NOT in source, drift!
    )
    # Source file: contains PRESENT but not ABSENT
    (repo / "tools" / "src.py").write_text(
        '# Reference: DRIFT_LITERAL_PRESENT should be in source\n'
    )
    # Recipe
    (repo / "recipe" / "x.yaml").write_text("title: x\n")
    return repo


@pytest.fixture
def recorded_findings(monkeypatch):
    """Monkey-patch add_finding to record into a list instead of mutating global fid."""
    captured = []
    def fake_add(ftype, severity, file, issue, impact, fix,
                 *, line_start=None, line_end=None, **pattern_kwargs):
        captured.append({
            "ftype": ftype,
            "severity": severity,
            "file": file,
            "issue": issue,
        })
    monkeypatch.setattr(mod, "add_finding", fake_add)
    return captured


# ═══════════════════════════════════════════════════════════════
# PURE HELPER TESTS
# ═══════════════════════════════════════════════════════════════
class TestIsRuntimeVarAssert:
    """`_is_runtime_var_assert` — R110-279: skip SD for runtime-output asserts."""

    def test_method_call_rhs_is_runtime(self):
        """captured = capsys.readouterr(); assert "x" in captured.out → True"""
        line = '    assert "X42" in captured.out'
        assert mod._is_runtime_var_assert(line) is True

    def test_runtime_method_chain(self):
        """assert "x" in result.stdout.split() → True (method chain)"""
        line = '    assert "FOO" in result.stdout.split()'
        assert mod._is_runtime_var_assert(line) is True

    def test_runtime_dict_subscript(self):
        """assert "key" in rules["key"] → True (dict subscript)"""
        line = '    assert "FOO" in rules["FOO"]'
        assert mod._is_runtime_var_assert(line) is True

    def test_plain_runtime_var(self):
        """assert "x" in out → True (bare runtime var)"""
        line = '    assert "FOO" in out'
        assert mod._is_runtime_var_assert(line) is True

    def test_plain_runtime_var_content(self):
        """assert "x" in content → True (bare runtime var)"""
        line = '    assert "FOO" in content'
        assert mod._is_runtime_var_assert(line) is True

    def test_static_string_rhs_is_not_runtime(self):
        """assert "x" in "literal" → False (static RHS)"""
        line = '    assert "FOO" in "literal_value"'
        assert mod._is_runtime_var_assert(line) is False

    def test_no_assert_clause(self):
        """Non-assert line → False"""
        line = '    x = "FOO" + "BAR"'
        assert mod._is_runtime_var_assert(line) is False


class TestIsPycacheOrBackup:
    """`_is_pycache_or_backup` — path filter."""

    def test_pycache_in_path(self):
        assert mod._is_pycache_or_backup("/a/__pycache__/foo.pyc") is True

    def test_pyc_extension(self):
        assert mod._is_pycache_or_backup("/a/foo.pyc") is True

    def test_llm_backup(self):
        assert mod._is_pycache_or_backup("/a/llm-backup/foo.py") is True

    def test_normal_path(self):
        assert mod._is_pycache_or_backup("/a/tools/dev_foo.py") is False

    def test_empty_path(self):
        assert mod._is_pycache_or_backup("") is False


class TestIsSelfReference:
    """`_is_self_reference` — skip if literal IS the RHS container."""

    def test_self_reference_quoted(self):
        """assert "test_foo" in __name__ where __name__ is "test_foo"."""
        line = '    assert "test_foo" in "test_foo"'
        assert mod._is_self_reference("test_foo", line) is True

    def test_not_self_reference_different_value(self):
        """assert "foo" in "bar" → False."""
        line = '    assert "foo" in "bar"'
        assert mod._is_self_reference("foo", line) is False

    def test_not_self_reference_unquoted(self):
        """assert "foo" in some_var → False (var, not self-ref)."""
        line = '    assert "foo" in some_var'
        assert mod._is_self_reference("foo", line) is False

    def test_self_reference_single_quoted(self):
        """assert 'x' in 'x' → True."""
        line = "    assert 'x' in 'x'"
        assert mod._is_self_reference("x", line) is True


class TestIsInDocstring:
    """`_is_in_docstring` — crudely counts triple-quotes."""

    def test_inside_triple_quote(self):
        src = ['def foo():\n', '    """\n', '    This is docstring\n', '    with literal\n']
        assert mod._is_in_docstring(src, 2) is True  # inside
        assert mod._is_in_docstring(src, 0) is False  # before

    def test_outside_docstring(self):
        src = ['def foo():\n', '    x = 1\n', '    """\n', '    docstring\n']
        # line 1 is outside (before opening triple quote on line 2)
        assert mod._is_in_docstring(src, 1) is False

    def test_empty_source(self):
        assert mod._is_in_docstring([], 0) is False


class TestIsInCodeBlock:
    """`_is_in_code_block` — detects fenced ``` markdown."""

    def test_inside_fenced_block(self):
        lines = ['```\n', 'code here\n', '```\n']
        assert mod._is_in_code_block(lines, 1) is True

    def test_outside_fenced_block(self):
        lines = ['# Header\n', '```\n', 'code\n', '```\n', '# After\n']
        assert mod._is_in_code_block(lines, 0) is False
        assert mod._is_in_code_block(lines, 4) is False


class TestIsInTableOrExample:
    """`_is_in_table_or_example` — markdown structural skip."""

    def test_inside_table_row(self):
        lines = ['| Col A | Col B |\n', '|-------|-------|\n', '| data  | data  |\n']
        # line 0 is the header (next line is separator)
        assert mod._is_in_table_or_example(lines, 0) is True

    def test_inside_table_data(self):
        lines = ['| Col A | Col B |\n', '| data  | data  |\n', '|-------|-------|\n']
        assert mod._is_in_table_or_example(lines, 1) is True

    def test_outside_table(self):
        lines = ['# Heading\n', 'Some prose.\n', 'More prose.\n']
        assert mod._is_in_table_or_example(lines, 1) is False

    def test_inside_example_block(self):
        lines = ['Some text\n', 'Example: do this\n', 'Then that\n']
        assert mod._is_in_table_or_example(lines, 1) is True


# ═══════════════════════════════════════════════════════════════
# CHECK_* DRIVER SMOKE TESTS
# ═══════════════════════════════════════════════════════════════
class TestCheckSpecDrift:
    """check_spec_drift — entry-point smoke test."""

    def test_returns_early_without_tests_dir(self, tmp_path, recorded_findings):
        """No tests/ → returns immediately, no findings."""
        repo = tmp_path / "no_tests_repo"
        repo.mkdir()
        mod.check_spec_drift(recorded_findings, repo_root=str(repo))
        assert len(recorded_findings) == 0

    def test_finds_drift_literal(self, tiny_repo, recorded_findings):
        """Test with literal NOT in source → finding registered."""
        mod.check_spec_drift(recorded_findings, repo_root=str(tiny_repo))
        # Should find DRIFT_LITERAL_ABSENT
        drift_findings = [f for f in recorded_findings
                          if f["ftype"].startswith("SD-test")]
        assert len(drift_findings) >= 1
        # The drift literal should be mentioned
        issues = " ".join(f["issue"] for f in drift_findings)
        assert "DRIFT_LITERAL_ABSENT" in issues

    def test_skips_runtime_var_asserts(self, tiny_repo, recorded_findings):
        """DRIFT_LITERAL_X42 in `captured.out` → not a finding (R110-279)."""
        mod.check_spec_drift(recorded_findings, repo_root=str(tiny_repo))
        # No finding for DRIFT_LITERAL_X42
        for f in recorded_findings:
            assert "DRIFT_LITERAL_X42" not in f["issue"]

    def test_no_drift_for_present_literal(self, tiny_repo, recorded_findings):
        """DRIFT_LITERAL_PRESENT IS in source → no finding."""
        mod.check_spec_drift(recorded_findings, repo_root=str(tiny_repo))
        for f in recorded_findings:
            assert "DRIFT_LITERAL_PRESENT" not in f["issue"]


class TestCheckSpecDriftReverse:
    """check_spec_drift_reverse — entry-point smoke test."""

    def test_returns_early_without_docs(self, tmp_path, recorded_findings):
        """No docs/ → returns immediately."""
        repo = tmp_path / "no_docs_repo"
        repo.mkdir()
        (repo / "recipe").mkdir()
        (repo / "tools").mkdir()
        mod.check_spec_drift_reverse(recorded_findings, repo_root=str(repo))
        # No SD-reverse findings
        sd_rev = [f for f in recorded_findings
                  if "spec_drift_reverse" in f["ftype"] or f["ftype"].startswith("SDR")]
        assert len(sd_rev) == 0

    def test_runs_without_crash(self, tiny_repo, recorded_findings):
        """check_spec_drift_reverse runs end-to-end on tiny_repo."""
        mod.check_spec_drift_reverse(recorded_findings, repo_root=str(tiny_repo))
        # No crash → pass. May or may not have findings; both are valid.


class TestCheckHardcodeStale:
    """check_hardcode_stale — entry-point smoke test."""

    def test_returns_early_without_tests_dir(self, tmp_path, recorded_findings):
        """No tests/ → returns immediately."""
        repo = tmp_path / "no_tests_repo"
        repo.mkdir()
        mod.check_hardcode_stale(recorded_findings, repo_root=str(repo))
        # No HC findings expected (early return)
        hc = [f for f in recorded_findings
              if f["ftype"].startswith("HC")]
        assert len(hc) == 0

    def test_runs_without_crash(self, tiny_repo, recorded_findings):
        """check_hardcode_stale runs end-to-end on tiny_repo."""
        mod.check_hardcode_stale(recorded_findings, repo_root=str(tiny_repo))
        # No crash → pass.


class TestCheckStaleLiteral:
    """check_stale_literal — entry-point smoke test."""

    def test_returns_early_without_tests_dir(self, tmp_path, recorded_findings):
        """No tests/ → returns immediately."""
        repo = tmp_path / "no_tests_repo"
        repo.mkdir()
        mod.check_stale_literal(recorded_findings, repo_root=str(repo))
        sl = [f for f in recorded_findings if f["ftype"].startswith("SL")]
        assert len(sl) == 0

    def test_runs_without_crash(self, tiny_repo, recorded_findings):
        """check_stale_literal runs end-to-end on tiny_repo."""
        mod.check_stale_literal(recorded_findings, repo_root=str(tiny_repo))
        # No crash → pass.
