"""R110-272: Unit tests for dev_issue_db.py mark-fixed CLI.

R110-271 had to use mark-wontfix as a workaround for fixed issues
(polluting the wontfix stats). R110-272 restores the proper
mark-fixed CLI surface and adds tests for it.

Coverage:
  - mark_fixed from open -> fixed (True)
  - mark_fixed from already-fixed (False, idempotent)
  - mark_fixed appends past_validation_outcomes
  - mark-fixed CLI integration (subprocess)
  - mark-fixed rejects empty --commit-sha
  - mark-fixed persists to disk (db.save() works)

Total: 8 tests.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
ISSUE_DB_TOOL = REPO_ROOT / "tools" / "dev_issue_db.py"


@pytest.fixture
def tmp_issue_db(tmp_path):
    """Fresh issue-db in tmp_path; each test gets a clean one.

    We create the file with the proper schema, then tests add issues
    by writing JSON directly. Tests load the db in-process via importlib
    AFTER writing the seed JSON, so IssueDB() reads our test data.
    """
    db_path = tmp_path / "issue_db.json"
    # Schema-only init (no issues yet)
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
    db_path.write_text(json.dumps(initial, indent=2))
    return db_path


def _register_sample_issue(db_path: Path, issue_hash: str) -> None:
    """Insert a sample open issue directly into the db (avoids needing scanner)."""
    db = json.loads(db_path.read_text())
    db["issues"][issue_hash] = {
        "hash": issue_hash,
        "type": "A2",
        "severity": "low",
        "file": "recipe/test.yaml",
        "structural_pattern": "max_turns_too_low:10",
        "instances": [],
        "status": "open",
        "first_seen": "2026-08-28T00:00:00Z",
        "last_seen": "2026-08-28T00:00:00Z",
        "past_designs": [],
        "past_validation_outcomes": [],
        "wontfix_reason": None,
        "wontfix_marked_at": None,
        "wontfix_marked_by": None,
    }
    db_path.write_text(json.dumps(db, indent=2))


# ============================================================
# 1. mark_fixed() library function (4 tests)
# ============================================================

def _load_issue_db_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dev_issue_db_mod", str(ISSUE_DB_TOOL))
    _mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_mod)
    return _mod


def test_mark_fixed_open_to_fixed(tmp_issue_db):
    """mark_fixed() on an open issue returns True and transitions to fixed."""
    h = "sha256:" + "a" * 64
    _register_sample_issue(tmp_issue_db, h)
    mod = _load_issue_db_module()
    db = mod.IssueDB(str(tmp_issue_db))

    changed = db.mark_fixed(h, "deadbeef" * 8, validated_by="im-validator")
    assert changed is True
    issue = db.get(h)
    assert issue["status"] == "fixed"
    assert len(issue["past_validation_outcomes"]) == 1
    out = issue["past_validation_outcomes"][0]
    assert out["commit_sha"] == "deadbeef" * 8
    assert out["verdict"] == "APPROVED"


def test_mark_fixed_already_fixed_returns_false(tmp_issue_db):
    """mark_fixed() on an already-fixed issue returns False (idempotent)."""
    h = "sha256:" + "b" * 64
    _register_sample_issue(tmp_issue_db, h)
    mod = _load_issue_db_module()
    db = mod.IssueDB(str(tmp_issue_db))

    db.mark_fixed(h, "abc123" * 13)
    changed_2nd = db.mark_fixed(h, "def456" * 13)
    assert changed_2nd is False
    # past_validation_outcomes should have 1 entry (NOT 2 — no double-log)
    issue = db.get(h)
    assert len(issue["past_validation_outcomes"]) == 1


def test_mark_fixed_unknown_hash_returns_false(tmp_issue_db):
    """mark_fixed() on a hash that doesn't exist returns False (no crash)."""
    mod = _load_issue_db_module()
    db = mod.IssueDB(str(tmp_issue_db))
    changed = db.mark_fixed("sha256:" + "0" * 64, "cafebabe" * 8)
    assert changed is False


def test_mark_fixed_validated_by_override(tmp_issue_db):
    """mark_fixed() honors validated_by override (not just default)."""
    h = "sha256:" + "c" * 64
    _register_sample_issue(tmp_issue_db, h)
    mod = _load_issue_db_module()
    db = mod.IssueDB(str(tmp_issue_db))

    db.mark_fixed(h, "12345678" * 8, validated_by="R110-272-test")
    out = db.get(h)["past_validation_outcomes"][0]
    assert out["validated_by"] == "R110-272-test"


# ============================================================
# 2. mark-fixed CLI subcommand (4 tests)
# ============================================================

def test_cli_mark_fixed_basic(tmp_issue_db):
    """mark-fixed CLI: open -> fixed, exit 0, prints changed=True."""
    h = "sha256:" + "d" * 64
    _register_sample_issue(tmp_issue_db, h)

    result = subprocess.run(
        [sys.executable, str(ISSUE_DB_TOOL), "--db", str(tmp_issue_db),
         "mark-fixed", h, "--commit-sha", "abc1234" * 8],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "changed=True" in result.stdout

    db = json.loads(tmp_issue_db.read_text())
    assert db["issues"][h]["status"] == "fixed"


def test_cli_mark_fixed_empty_commit_sha_rejected(tmp_issue_db):
    """mark-fixed CLI: empty --commit-sha exits 1 with error message."""
    h = "sha256:" + "e" * 64
    _register_sample_issue(tmp_issue_db, h)

    result = subprocess.run(
        [sys.executable, str(ISSUE_DB_TOOL), "--db", str(tmp_issue_db),
         "mark-fixed", h, "--commit-sha", ""],
        capture_output=True, text=True,
    )
    # argparse with required arg + empty string: argparse rejects empty
    # because we check `not args.commit_sha.strip()`. Either way exit 1.
    assert result.returncode == 1
    assert "ERROR" in result.stderr or "error" in result.stderr.lower()


def test_cli_mark_fixed_validated_by_flag(tmp_issue_db):
    """mark-fixed CLI: --validated-by is recorded in past_validation_outcomes."""
    h = "sha256:" + "f" * 64
    _register_sample_issue(tmp_issue_db, h)

    subprocess.run(
        [sys.executable, str(ISSUE_DB_TOOL), "--db", str(tmp_issue_db),
         "mark-fixed", h, "--commit-sha", "87654321" * 8,
         "--validated-by", "R110-272-cli-test"],
        check=True, capture_output=True,
    )
    db = json.loads(tmp_issue_db.read_text())
    out = db["issues"][h]["past_validation_outcomes"][0]
    assert out["validated_by"] == "R110-272-cli-test"


def test_cli_mark_fixed_help_shows_arguments():
    """mark-fixed CLI: --help shows --commit-sha and --validated-by."""
    result = subprocess.run(
        [sys.executable, str(ISSUE_DB_TOOL), "mark-fixed", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--commit-sha" in result.stdout
    assert "--validated-by" in result.stdout
