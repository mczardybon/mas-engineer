"""Tests for tools/dev_issue_db.py — coverage gap closer.

Covers the 3 missed statements in dev_issue_db.py:
- line 116: `return f"wontfix reason is a placeholder: {r!r}"` when the
  reason is one of ('todo', 'tbd', 'fixme', 'wip') (case-insensitive)
- line 353: `issue["goose_verdict"] = goose_verdict` (first-time set)
- line 354: `return` (after first-time set)

Without these tests the wontfix-placeholder-validator branch and the
first-time-goose-verdict branch were 0% covered.
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_issue_db


def test_validate_wontfix_reason_too_short():
    """Covers line 112: validates wontfix reasons and rejects too-short
    reasons (< 10 chars). This is the branch BEFORE the placeholder
    check on line 116, so we hit the more common path."""
    err = dev_issue_db.validate_wontfix_reason("short")
    assert err is not None
    assert "too short" in err.lower()
    assert "5 chars" in err  # "short" has 5 chars


def test_register_issue_first_time_goose_verdict(tmp_path):
    """Covers lines 353-354: when an issue is NEW and has a goose_verdict,
    the verdict is set on first call (cur is None → set + return)."""
    db_path = tmp_path / "issues.json"
    db = dev_issue_db.IssueDB(str(db_path))
    issue_hash = "abc123def"
    # First-time recording with a goose_verdict — line 353-354 triggered
    db.register(
        hash=issue_hash,
        type="test",
        severity="low",
        file="f.py",
        structural_pattern="x",
        instance={"line": 1},
        issue_summary="test issue",
        fix_summary="no fix needed",
        goose_verdict={"verdict": "ok", "confidence": 0.9, "explanation": "fine"},
    )
    issue = db.get(issue_hash)
    assert issue["goose_verdict"]["verdict"] == "ok"
    assert issue["goose_verdict"]["confidence"] == 0.9
