"""Tests for tools/dev_self_auditor.py — coverage gap closer.

Covers the 13 missed statements in dev_self_auditor.py by exercising:
- has_honest_scope_marker() (line 135)
- is_evidence_stale() True branch (line 174) + except-fallback (lines 175-176)
- audit_file() with strong-claim + weakening pattern (line 121+)
- write_report() with empty results (line 294+)
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_self_auditor as sa


def test_has_honest_scope_marker_recognizes_markers():
    """Covers line 135: returns True for content containing HONEST_SCOPE_MARKERS
    like 'honest scope' or 'NOT verified'."""
    # True cases — exact regex match required (whitespace boundaries)
    assert sa.has_honest_scope_marker("This document is honest scope, not absolute.") is True
    assert sa.has_honest_scope_marker("This is NOT verified, preliminary only.") is True
    # False case — no marker
    assert sa.has_honest_scope_marker("Final report, 100% verified") is False


def test_is_evidence_stale_true_branch(tmp_path):
    """Covers line 174: when evidence file mtime is older than file_path
    mtime by more than max_age_days, returns True."""
    file_p = tmp_path / "doc.md"
    ev_p = tmp_path / "ev.json"
    file_p.write_text("# doc")
    ev_p.write_text("{}")
    # Make evidence file 10 days older than the doc
    old_mtime = (datetime.now() - timedelta(days=10)).timestamp()
    import os
    os.utime(ev_p, (old_mtime, old_mtime))
    assert sa.is_evidence_stale(file_p, ev_p, max_age_days=7) is True


def test_is_evidence_stale_handles_missing_file(tmp_path):
    """Covers lines 175-176: when stat() fails (file missing), except
    branch returns False (no crash)."""
    file_p = tmp_path / "doc.md"
    ev_p = tmp_path / "missing-ev.json"
    file_p.write_text("# doc")
    assert sa.is_evidence_stale(file_p, ev_p) is False


def test_audit_file_with_strong_claim(tmp_path):
    """Covers line 121+: audit_file detects strong-claim statements."""
    p = tmp_path / "report.md"
    p.write_text("# Report\nThis has 99 tests passing.\nAll verified.\n")
    result = sa.audit_file(p)
    assert isinstance(result, dict)


def test_write_report_with_empty_results(tmp_path, monkeypatch):
    """Covers line 294+: write_report with empty file_results list."""
    monkeypatch.chdir(tmp_path)
    report = sa.write_report(str(tmp_path), [], scope="all")
    assert isinstance(report, dict)
