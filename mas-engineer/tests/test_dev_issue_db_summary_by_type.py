"""R110-273: Unit tests for dev_issue_db._compute_summary status-filtered fields.

R110-271 noticed the `by_type` field in the stats output counts ALL
issues by type, not just open. R110-273 adds `by_type_open`,
`by_type_fixed`, `by_type_wontfix`, `by_type_false_positive` fields
so dashboards can show "currently broken by type" without filtering
client-side.

Coverage:
  - by_type_open counts only open-status issues
  - by_type_fixed counts only fixed-status issues
  - by_type_wontfix counts only wontfix-status issues
  - by_type_false_positive counts only false_positive-status issues
  - legacy by_type still counts all (backward compat)
  - mixed-status db: each field is independent
  - empty db: all 5 dicts are empty
  - by_status totals are unaffected by the new fields

Total: 8 tests.
"""
import json
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
ISSUE_DB_TOOL = REPO_ROOT / "tools" / "dev_issue_db.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "dev_issue_db_mod", str(ISSUE_DB_TOOL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_issue(status: str, type_: str = "A2",
                hash_prefix: str = "a") -> dict:
    h = "sha256:" + hash_prefix * 64
    return {
        "hash": h,
        "type": type_,
        "severity": "low",
        "file": "recipe/test.yaml",
        "structural_pattern": "x",
        "instances": [],
        "status": status,
        "first_seen": "2026-08-28T00:00:00Z",
        "last_seen": "2026-08-28T00:00:00Z",
        "past_designs": [],
        "past_validation_outcomes": [],
        "wontfix_reason": None,
        "wontfix_marked_at": None,
        "wontfix_marked_by": None,
    }


@pytest.fixture
def empty_db(tmp_path):
    return tmp_path / "issue_db.json"


@pytest.fixture
def empty_issue_db(empty_db):
    """Fresh empty db, schema-only."""
    initial = {
        "schema_version": "1.0.0",
        "issues": {},
        "summary": {
            "total_issues": 0,
            "by_status": {"open": 0, "fixed": 0, "wontfix": 0,
                          "false_positive": 0},
            "by_type": {},
        },
    }
    empty_db.write_text(json.dumps(initial, indent=2))
    return empty_db


# ============================================================
# Tests for status-filtered by_type fields
# ============================================================

def test_compute_summary_empty_db_has_empty_type_dicts(empty_issue_db):
    """Empty db: all 5 type-dicts are empty (not None, not missing)."""
    mod = _load_module()
    db = mod.IssueDB(str(empty_issue_db))
    summary = db._compute_summary()
    assert summary["by_type"] == {}
    assert summary["by_type_open"] == {}
    assert summary["by_type_fixed"] == {}
    assert summary["by_type_wontfix"] == {}
    assert summary["by_type_false_positive"] == {}


def test_compute_summary_by_type_open_only_counts_open(empty_issue_db):
    """by_type_open counts ONLY open-status issues (not fixed)."""
    empty_issue_db.write_text(json.dumps({
        "schema_version": "1.0.0",
        "issues": {
            "sha256:" + "1" * 64: _make_issue("open", "A2", "1"),
            "sha256:" + "2" * 64: _make_issue("open", "A2", "2"),
            "sha256:" + "3" * 64: _make_issue("open", "NN1", "3"),
            "sha256:" + "4" * 64: _make_issue("fixed", "A2", "4"),
        },
        "summary": {},
    }, indent=2))
    mod = _load_module()
    db = mod.IssueDB(str(empty_issue_db))
    summary = db._compute_summary()
    assert summary["by_type_open"] == {"A2": 2, "NN1": 1}
    # A2 appears 1 time fixed, so by_type_fixed has 1
    assert summary["by_type_fixed"] == {"A2": 1}
    # NN1 has 0 fixed, so NN1 is not in by_type_fixed
    assert "NN1" not in summary["by_type_fixed"]


def test_compute_summary_by_type_fixed_only_counts_fixed(empty_issue_db):
    """by_type_fixed counts ONLY fixed-status issues."""
    empty_issue_db.write_text(json.dumps({
        "schema_version": "1.0.0",
        "issues": {
            "sha256:" + "a" * 64: _make_issue("fixed", "A2", "a"),
            "sha256:" + "b" * 64: _make_issue("fixed", "Q4c", "b"),
            "sha256:" + "c" * 64: _make_issue("open", "Q4c", "c"),
        },
        "summary": {},
    }, indent=2))
    mod = _load_module()
    db = mod.IssueDB(str(empty_issue_db))
    summary = db._compute_summary()
    assert summary["by_type_fixed"] == {"A2": 1, "Q4c": 1}
    assert summary["by_type_open"] == {"Q4c": 1}


def test_compute_summary_by_type_wontfix(empty_issue_db):
    """by_type_wontfix counts ONLY wontfix-status issues."""
    empty_issue_db.write_text(json.dumps({
        "schema_version": "1.0.0",
        "issues": {
            "sha256:" + "a" * 64: _make_issue("wontfix", "Q4c", "a"),
            "sha256:" + "b" * 64: _make_issue("wontfix", "Q4c", "b"),
            "sha256:" + "c" * 64: _make_issue("open", "A2", "c"),
        },
        "summary": {},
    }, indent=2))
    mod = _load_module()
    db = mod.IssueDB(str(empty_issue_db))
    summary = db._compute_summary()
    assert summary["by_type_wontfix"] == {"Q4c": 2}
    assert "Q4c" not in summary["by_type_open"]


def test_compute_summary_by_type_false_positive(empty_issue_db):
    """by_type_false_positive counts ONLY false_positive-status issues."""
    empty_issue_db.write_text(json.dumps({
        "schema_version": "1.0.0",
        "issues": {
            "sha256:" + "a" * 64: _make_issue("false_positive", "NN1", "a"),
        },
        "summary": {},
    }, indent=2))
    mod = _load_module()
    db = mod.IssueDB(str(empty_issue_db))
    summary = db._compute_summary()
    assert summary["by_type_false_positive"] == {"NN1": 1}
    assert "NN1" not in summary["by_type_open"]


def test_compute_summary_legacy_by_type_counts_all(empty_issue_db):
    """by_type (legacy) still counts ALL issues (mixed status)."""
    empty_issue_db.write_text(json.dumps({
        "schema_version": "1.0.0",
        "issues": {
            "sha256:" + "1" * 64: _make_issue("open", "A2", "1"),
            "sha256:" + "2" * 64: _make_issue("fixed", "A2", "2"),
            "sha256:" + "3" * 64: _make_issue("wontfix", "A2", "3"),
            "sha256:" + "4" * 64: _make_issue("open", "NN1", "4"),
        },
        "summary": {},
    }, indent=2))
    mod = _load_module()
    db = mod.IssueDB(str(empty_issue_db))
    summary = db._compute_summary()
    # A2 appears 3 times total (1 open + 1 fixed + 1 wontfix)
    assert summary["by_type"]["A2"] == 3
    assert summary["by_type"]["NN1"] == 1


def test_compute_summary_by_status_totals_unchanged(empty_issue_db):
    """R110-273 added 4 new fields but by_status totals must not change."""
    empty_issue_db.write_text(json.dumps({
        "schema_version": "1.0.0",
        "issues": {
            "sha256:" + "1" * 64: _make_issue("open", "A2", "1"),
            "sha256:" + "2" * 64: _make_issue("fixed", "A2", "2"),
            "sha256:" + "3" * 64: _make_issue("wontfix", "Q4c", "3"),
            "sha256:" + "4" * 64: _make_issue("false_positive", "NN1", "4"),
        },
        "summary": {},
    }, indent=2))
    mod = _load_module()
    db = mod.IssueDB(str(empty_issue_db))
    summary = db._compute_summary()
    assert summary["by_status"] == {
        "open": 1, "fixed": 1, "wontfix": 1, "false_positive": 1,
    }
    assert summary["total_issues"] == 4


def test_compute_summary_mixed_status_independence(empty_issue_db):
    """A type appearing in multiple status dicts is independently counted."""
    empty_issue_db.write_text(json.dumps({
        "schema_version": "1.0.0",
        "issues": {
            # 2 open A2
            "sha256:" + "1" * 64: _make_issue("open", "A2", "1"),
            "sha256:" + "2" * 64: _make_issue("open", "A2", "2"),
            # 1 fixed A2
            "sha256:" + "3" * 64: _make_issue("fixed", "A2", "3"),
            # 1 wontfix A2
            "sha256:" + "4" * 64: _make_issue("wontfix", "A2", "4"),
        },
        "summary": {},
    }, indent=2))
    mod = _load_module()
    db = mod.IssueDB(str(empty_issue_db))
    summary = db._compute_summary()
    assert summary["by_type_open"]["A2"] == 2
    assert summary["by_type_fixed"]["A2"] == 1
    assert summary["by_type_wontfix"]["A2"] == 1
    assert summary["by_type"]["A2"] == 4  # legacy: all
