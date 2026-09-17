"""
R110-369 regression tests for dev_spec_invariant.extract_count_assertions_from_tests.

Bug: the test-r110322 meta-tests (which test the extractor itself) contain
fixtures like '5 ab' / '7 cd' in pseudo-assert strings. The extractor's
regex correctly identifies them but treating them as real test assertions
caused false-positive INVARIANT-ab / -cd BLOCKERs in dev_self_audit
(R110-119 test-debt). Additionally, test_r110351 had a substring check
where a digit and a file-extension label ('YAML') appeared in one string
but were semantically unrelated.

Fix: META_TEST_FILE_PREFIXES exemption + heuristic to skip
'in captured.out' assertions for the 'yaml' type.

This test pins both fixes so they don't regress in future refactors.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from dev_spec_invariant import extract_count_assertions_from_tests  # noqa: E402


def test_meta_test_files_excluded(tmp_path):
    """R110-369: test_r110322_* meta-tests are skipped (META_TEST_FILE_PREFIXES)."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    # Simulate a meta-test file with a fixture
    (tests_dir / "test_r110322_dummy.py").write_text(
        '''
def test_xxx():
    assert "5 ab" in "5 ab"
    assert "7 cd" in "7 cd"
'''
    )
    result = extract_count_assertions_from_tests(tests_dir)
    # The "5 ab" and "7 cd" from the meta-test must NOT be in the result
    assert "ab" not in result, f"meta-test fixture leaked into result: {result}"
    assert "cd" not in result, f"meta-test fixture leaked into result: {result}"


def test_yaml_in_captured_out_excluded(tmp_path):
    """R110-369: substring-check on stdout is not a yaml count assertion."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_dummy.py").write_text(
        '''
def test_xxx(captured):
    # Simulates test_r110351 pattern: substring check on stdout
    assert "2 YAML" in captured.out
'''
    )
    result = extract_count_assertions_from_tests(tests_dir)
    # "yaml" should not appear in the result (was a false positive)
    assert "yaml" not in result, f"false positive: {result}"


def test_real_yaml_assertion_still_kept(tmp_path):
    """R110-369: legitimate yaml count assertions are still detected."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_real.py").write_text(
        '''
def test_xxx():
    # Real assertion about yaml files (not a captured.out substring check)
    assert "3 yaml" in "we have 3 yaml files"
'''
    )
    result = extract_count_assertions_from_tests(tests_dir)
    # The legitimate "3 yaml" must be in the result
    assert result.get("yaml") == {3}, f"legitimate yaml count missed: {result}"
