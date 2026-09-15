"""
R110-562 regression tests for dev_spec_invariant._docstring_or_comment_mask.

Bug: _is_docstring_or_comment(lines, idx) was O(N^2) per call (it scanned
all lines from 0..idx to count triple-quote tokens). With N test files
each containing ~500 lines, extract_count_assertions_from_tests took
6.4 seconds for 388 files.

Fix: _docstring_or_comment_mask(lines) precomputes the per-line docstring/
comment bit in a single O(N) pass per file. extract_count_assertions_from_tests
now reads the mask instead of calling _is_docstring_or_comment per line.

These tests pin:
  1) Output parity with the old per-line function (bit-for-bit identical
     on a representative sample of real test files plus constructed cases).
  2) Perf bound: extract_count_assertions_from_tests on the real test
     dir finishes in well under the 6.4s pre-fix baseline (we assert
     <2.0s to be robust against CI variance while still catching a
     10x regression).
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
TESTS_DIR = REPO / "tests"


def _import_module():
    sys.path.insert(0, str(TOOLS))
    try:
        import dev_spec_invariant
    finally:
        sys.path.pop(0)
    return dev_spec_invariant


def _build_representative_text():
    """Hand-constructed snippet exercising all docstring/comment shapes."""
    return (
        '"""Module docstring."""\n'             # 0: opens
        "import os\n"                            # 1: in docstring
        "# trailing comment\n"                   # 2: in docstring
        '"""end of docstring"""\n'               # 3: closes
        "x = 1  # inline comment\n"              # 4: code (not masked)
        'def f():\n'                             # 5: code
        '    """nested docstring."""\n'          # 6: opens nested
        '    assert "12 tests" in s\n'           # 7: in nested
        '    return s\n'                         # 8: in nested
        '"""multi\n'                             # 9: opens new
        'line\n'                                 # 10: in
        'docstring\n'                            # 11: in
        'spans.\n'                               # 12: in
        '"""\n'                                  # 13: closes
        "y = 2\n"                                # 14: code
    )


class TestMaskParity:
    """The new mask must match the old per-line function exactly."""

    def test_representative_text(self):
        dev_spec_invariant = _import_module()
        lines = _build_representative_text().splitlines()
        old = [dev_spec_invariant._is_docstring_or_comment(lines, i)
               for i in range(len(lines))]
        new = dev_spec_invariant._docstring_or_comment_mask(lines)
        assert old == new, (
            f"Mask parity broken:\n  old={old}\n  new={new}")

    def test_empty_file(self):
        dev_spec_invariant = _import_module()
        assert dev_spec_invariant._docstring_or_comment_mask([]) == []

    def test_single_line_no_docstring(self):
        dev_spec_invariant = _import_module()
        lines = ["x = 1"]
        assert dev_spec_invariant._docstring_or_comment_mask(lines) == [False]

    def test_comment_only(self):
        dev_spec_invariant = _import_module()
        lines = ["# only", "# comments"]
        assert dev_spec_invariant._docstring_or_comment_mask(lines) == [True, True]

    def test_single_line_docstring(self):
        dev_spec_invariant = _import_module()
        lines = ['"""one-liner"""', "x = 1"]
        old = [dev_spec_invariant._is_docstring_or_comment(lines, i)
               for i in range(len(lines))]
        new = dev_spec_invariant._docstring_or_comment_mask(lines)
        assert old == new

    def test_random_real_files(self, monkeypatch):
        """Bit-for-bit parity on a sample of real test files."""
        dev_spec_invariant = _import_module()
        import random
        random.seed(42)
        real_files = sorted(TESTS_DIR.glob("test_*.py"))
        sample = random.sample(real_files, min(15, len(real_files)))
        for path in sample:
            lines = path.read_text(errors="ignore").splitlines()
            old = [dev_spec_invariant._is_docstring_or_comment(lines, i)
                   for i in range(len(lines))]
            new = dev_spec_invariant._docstring_or_comment_mask(lines)
            assert old == new, (
                f"Parity broken on {path.name}: "
                f"first diff at idx {next(i for i,(o,n) in enumerate(zip(old,new)) if o != n)}")


class TestExtractPerf:
    """extract_count_assertions_from_tests must finish well under 6.4s."""

    def test_under_two_seconds_on_real_repo(self):
        dev_spec_invariant = _import_module()
        t0 = time.time()
        result = dev_spec_invariant.extract_count_assertions_from_tests(TESTS_DIR)
        elapsed = time.time() - t0
        # Pre-fix: 6.4s for 388 files. Threshold 2.0s = 3x headroom,
        # catches 10x regressions on slower CI.
        assert elapsed < 2.0, (
            f"extract_count_assertions_from_tests too slow: {elapsed:.2f}s "
            f"(R110-562 fix target was <1s, baseline was 6.4s)")
        assert isinstance(result, dict)


class TestSelfAuditPerf:
    """R110-562: run_self_audit must finish under 10s (was 44s pre-fix).

    Pre-fix: each of 95 instruction files rebuilt a 95x724=68k-file
    repo-wide index (95 redundant glob walks + reads).
    Post-fix: index built once, ~1.5s on this dev box.
    """

    def test_run_self_audit_under_ten_seconds(self):
        sys.path.insert(0, str(TOOLS))
        try:
            import dev_self_audit
        finally:
            sys.path.pop(0)
        repo_root = REPO
        scope = repo_root / "recipe" / "instructions"
        t0 = time.time()
        result = dev_self_audit.run_self_audit(scope=scope, repo_root=repo_root)
        elapsed = time.time() - t0
        assert elapsed < 10.0, (
            f"run_self_audit too slow: {elapsed:.2f}s "
            f"(baseline was 44s, R110-562 target was <2s)")
        # Sanity: result is a real audit, not an empty shim.
        assert hasattr(result, "findings")

    def test_build_repo_literal_index_called_once(self, monkeypatch):
        """R110-562 regression guard: _scan_pattern_b must NOT call
        _build_repo_literal_index internally (the old per-file call was
        the source of the 95x redundant glob walks)."""
        sys.path.insert(0, str(TOOLS))
        try:
            import dev_self_audit
        finally:
            sys.path.pop(0)
        # Spy on the function
        call_count = {"n": 0}
        original = dev_self_audit._build_repo_literal_index
        def spy(repo_root):
            call_count["n"] += 1
            return original(repo_root)
        monkeypatch.setattr(dev_self_audit, "_build_repo_literal_index", spy)
        # Also need to swap the reference inside the module's run_self_audit
        # closure: easiest is to patch the run_self_audit function's globals.
        repo_root = REPO
        scope = repo_root / "recipe" / "instructions"
        dev_self_audit.run_self_audit(scope=scope, repo_root=repo_root)
        # Should be called exactly once, not once per instruction file.
        assert call_count["n"] == 1, (
            f"_build_repo_literal_index called {call_count['n']} times "
            f"(expected 1; R110-562 fix removed the per-instruction-file call)")
