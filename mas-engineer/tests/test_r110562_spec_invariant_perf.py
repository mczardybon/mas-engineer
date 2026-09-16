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


class TestR110578CommentTripleQuoteParity:
    """R110-578: a triple-quote token that lives INSIDE a `#` comment must
    NOT advance the docstring-region counter in EITHER the old per-line
    helper OR the new precomputed mask. Before the fix, the OLD function
    counted a triple-quote inside a comment (opening a phantom docstring
    region), while the NEW mask correctly skipped comments — so the
    parity test silently broke when the validator's random sample
    happened to include tests/test_dev_im_finder_scan_lib.py (whose
    line 203 contains a triple-quote token inside a `#` comment).

    These tests pin the correct behaviour so neither function regresses.
    """

    def _helper(self):
        sys.path.insert(0, str(TOOLS))
        import dev_spec_invariant  # noqa: WPS433
        return dev_spec_invariant

    def test_comment_with_triple_quote_in_middle_does_not_open_region(self):
        """The validator-F-2 scenario: a real test file with a `#`
        comment that contains a triple-quote literal.

        Asserts:
        1. OLD and NEW agree on every line (parity holds).
        2. The comment line itself (idx 203) is masked True (because it
           is a `#` comment, regardless of the docstring-region rule).
        3. The first divergence that the OLD logic had — at idx 204, a
           real `assert` statement — must NOT be introduced by the
           comment's triple-quote token. Concretely: if we strip the
           triple-quote token from the comment text, the mask at idx 204
           must be unchanged. Before the fix, the OLD function counted
           the triple-quote in the comment (advancing the counter),
           so removing it would have FLIPPED the mask. After the fix,
           the comment is skipped entirely, so removing it has no
           effect."""
        dev_spec_invariant = self._helper()
        from pathlib import Path
        target = TESTS_DIR / "test_dev_im_finder_scan_lib.py"
        if not target.exists():
            pytest.skip(f"{target} not present in this checkout")
        lines = target.read_text(errors="ignore").splitlines()
        # OLD and NEW must agree on every line.
        old = [dev_spec_invariant._is_docstring_or_comment(lines, i)
               for i in range(len(lines))]
        new = dev_spec_invariant._docstring_or_comment_mask(lines)
        assert old == new, (
            f"Parity broken on {target.name}"
        )
        # Line 203 is a `#` comment → masked True.
        assert new[203] is True, (
            f"Line 203 is a `#` comment, must be masked True. "
            f"Got {new[203]}"
        )

        # Stronger invariant: rebuild the file with the `"""` token
        # REMOVED from the comment, and verify new[204] is unchanged.
        # Before the fix, the OLD function counted `"""` in the comment
        # (advancing the counter by 1), so removing the token would
        # decrement the count by 1, FLIPPING new[204] from True to
        # False. After the fix, the comment is skipped entirely, so
        # removing the token has no effect on new[204].
        tq = chr(34) * 3
        assert tq in lines[203], "Test premise: idx 203 must contain triple-quote"
        lines_stripped = list(lines)
        lines_stripped[203] = lines_stripped[203].replace(tq, "")
        new_stripped = dev_spec_invariant._docstring_or_comment_mask(lines_stripped)
        assert new_stripped[204] == new[204], (
            f"Stripping triple-quote from idx 203 changed mask at idx 204 "
            f"({new[204]} → {new_stripped[204]}). The comment must not "
            f"influence the docstring-region counter."
        )

    def test_handcrafted_comment_with_triple_quote(self):
        """Construct a minimal snippet where a comment line in the middle
        contains a triple-quote token, and verify both OLD and NEW treat
        it correctly."""
        dev_spec_invariant = self._helper()
        lines = [
            "x = 1\n",
            '    # literal tq marker here\n',  # placeholder; we splice below
            "y = 2\n",
        ]
        # Splice in a real triple-quote inside the comment.
        tq = chr(34) * 3
        lines[1] = '    # count of ' + tq + ' before is 0 (even)\n'
        old = [dev_spec_invariant._is_docstring_or_comment(lines, i)
               for i in range(len(lines))]
        new = dev_spec_invariant._docstring_or_comment_mask(lines)
        assert old == new
        assert old == [False, True, False], (
            f"Expected [False, True, False], got old={old} new={new}"
        )

    def test_real_docstring_open_still_detected(self):
        """Sanity: a single-line triple-quoted docstring token toggles the
        counter to odd, and BOTH functions agree on the resulting mask.

        Note: the OLD counter is a coarse line-count heuristic (one
        triple-quote token per line toggles once), so a docstring whose
        opening and closing triple-quote sit on the same line yields
        mask=[True, True] for both lines. That is the existing
        convention used by all parity tests in this file, so the new
        test must respect it to assert parity."""
        dev_spec_invariant = self._helper()
        lines = [
            '"""docstring"""\n',
            "x = 1\n",
        ]
        old = [dev_spec_invariant._is_docstring_or_comment(lines, i)
               for i in range(len(lines))]
        new = dev_spec_invariant._docstring_or_comment_mask(lines)
        assert old == [True, True]
        assert new == [True, True]


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
