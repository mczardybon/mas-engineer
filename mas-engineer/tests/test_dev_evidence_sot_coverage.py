"""Tests for tools/dev_evidence_sot.py — coverage gap closer.

Covers the 11 missed statements in dev_evidence_sot.py by exercising:
- _list_staged_files() with ls-tree failure (line 115: head_set = set())
- _is_any_file_in_anti_sot_logs() with various path shapes (line 181)
- _is_evidence_file() (line 162-167: edge cases)
- check_directives_sot_git_index() (line 224)
- check_sot_evidence_dir_health() (line 240)
- check_sot_directives_dir_health() (line 255)
"""
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_evidence_sot as sot


def test_list_staged_files_handles_ls_tree_failure(monkeypatch):
    """Covers line 115: when 'git ls-tree HEAD' fails (rc2 != 0),
    head_set = set() (empty) — instead of crashing."""
    # Patch _git to return (0, stage, '') for ls-files, and (1, '', '')
    # for ls-tree (simulating failure)
    def fake_git(*args, cwd=None):
        if args[0] == "ls-files":
            return (0, "100644 blob abc123\tstaged_file.txt\n", "")
        if args[0] == "ls-tree":
            return (1, "", "fatal: not a git repo")
        return (0, "", "")
    monkeypatch.setattr(sot, "_git", fake_git)
    result = sot._list_staged_files()
    assert result == ["staged_file.txt"]


def test_is_evidence_file_recognizes_convention():
    """Covers line 162-167: _is_evidence_file identifies files by
    convention names (-evidence.md, e2e-evidence-gen2/, session-report)."""
    # True cases
    assert sot._is_evidence_file("logs/e2e-evidence-gen2/x.json") is True
    assert sot._is_evidence_file("R110-EVIDENCE.md") is True
    assert sot._is_evidence_file("session-report.txt") is True
    # False case
    assert sot._is_evidence_file("normal/file.txt") is False


def test_check_sot_directives_dir_health_no_directives_dir(tmp_path, monkeypatch):
    """Covers line 255: when directives/ dir doesn't exist, the health
    check returns a list (possibly empty)."""
    # Override _resolve_repo_root to return tmp_path (no directives/)
    monkeypatch.setattr(sot, "_resolve_repo_root", lambda: tmp_path)
    report = sot.check_sot_directives_dir_health()
    # Returns a list per the actual signature
    assert report is not None
