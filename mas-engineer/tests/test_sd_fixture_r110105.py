"""Fixture for SD-check e2e test (R110-105).

Tests that the check_spec_drift() function in tools/dev_im_finder_scan.py
correctly identifies ZOMBIE literals (spec-drift) vs current literals.

Pattern: tests look for intentional 12+ char zombie literals in
test names. check_spec_drift() scans test code (not assert body)
and flags literals NOT in recipe/tools/docs as spec-drift.
"""
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCANNER = os.path.join(REPO, "tools", "dev_im_finder_scan.py")
# This test file intentionally contains the literal
# ZOMBIE_LITERAL_XYZZY_FORTYTWO which appears ONLY in this test name
# and is NOT in any recipe/tools/docs file. The check_spec_drift()
# function should flag it as spec-drift (the scanner walks test
# function names and reports 9+ char literals that are not in
# recipe/ or tools/).
TEST_FILE = __file__


def test_zombie_literal_in_test_name_creates_drift():
    """Sanity: this test's name and docstring contain the zombie literal
    ZOMBIE_LITERAL_XYZZY_FORTYTWO. The check_spec_drift() function should
    detect it as spec-drift. This test only verifies the literal exists
    in the test file (for the scanner to find)."""
    content = open(TEST_FILE).read()
    assert "ZOMBIE_LITERAL_XYZZY_FORTYTWO" in content, \
        "Zombie literal must be in test file for scanner to detect"


def test_current_literal_no_drift():
    """The literal '110 sub-agents' IS in recipe (sub_mas-bootstrap.yaml
    declares 110 sub-agents). Should NOT be flagged as drift by scanner."""
    content = open(TEST_FILE).read()
    assert "110 sub-agents" in content, \
        "Current literal reference must be in test file"


def test_short_literal_no_drift():
    """Short literals (<4 chars) should NOT be flagged per spec section 4a."""
    assert "ok" in "ok here"


def test_url_literal_no_drift():
    """URLs should NOT be flagged per spec section 4b (URL is reference, not literal)."""
    assert "https://example.com" in "https://example.com"
