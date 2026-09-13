"""Tests for tools/dev_gatekeeper.py — coverage gap closer.

Covers the 13% coverage of dev_gatekeeper.py (170 stmts, ~150 missed).
Strategy: exercise each top-level check function with mocked STATE_DIR
(monkeypatch the module-level constants):
- alog() — writes audit + lock on CRITICAL
- check_lock() — sys.exit(1) if lock exists, no-op otherwise
- check_r01() — no confirmation file, expired, valid
- check_r18() — empty audit, valid DELEGATE, non-DELEGATE
- check_r19() — write/edit/delete paths, .git/ forbidden, shell
- check_r20() — always True
- check_r10() — yaml validation success/failure
- check_r05() — no checkpoint dir, no recent checkpoint
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_gatekeeper as gk


@pytest.fixture
def isolated_state(monkeypatch, tmp_path):
    """Redirect gk.STATE_DIR, AUDIT_file, LOCK_file, CONFIRMATION_file to tmp_path."""
    state = tmp_path / ".mase"
    state.mkdir()
    monkeypatch.setattr(gk, "STATE_DIR", str(state))
    monkeypatch.setattr(gk, "AUDIT_file", str(state / "audit.log.jsonl"))
    monkeypatch.setattr(gk, "LOCK_file", str(state / ".disziplin_lock"))
    monkeypatch.setattr(gk, "CONFIRMATION_file", str(state / ".last_confirmation"))
    return state


def test_alog_writes_audit_entry(isolated_state):
    """Covers lines 24-30: alog() appends to AUDIT_file with all fields."""
    gk.alog("WRITE", "test-agent", "/path/to/file.py", "OK", rule="R01")
    audit_path = isolated_state / "audit.log.jsonl"
    assert audit_path.exists()
    lines = audit_path.read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action"] == "WRITE"
    assert entry["status"] == "OK"
    assert entry["rule"] == "R01"


def test_alog_critical_writes_lock_file(isolated_state):
    """Covers lines 31-33: alog() with status='CRITICAL' creates lock file."""
    gk.alog("WRITE", "test-agent", "/path", "CRITICAL", rule="R01")
    lock = isolated_state / ".disziplin_lock"
    assert lock.exists()
    assert "CRITICAL" in lock.read_text()


def test_check_lock_exits_when_lock_exists(isolated_state):
    """Covers lines 36-39: check_lock() sys.exit(1) when LOCK_file exists."""
    (isolated_state / ".disziplin_lock").write_text("frozen\n")
    with pytest.raises(SystemExit):
        gk.check_lock()


def test_check_lock_no_op_when_no_lock(isolated_state):
    """Covers line 35-39: no lock file → no exit, returns None."""
    result = gk.check_lock()
    assert result is None


def test_check_r01_no_confirmation(isolated_state):
    """Covers lines 42-43: no .last_confirmation → (False, 'No .last_confirmation')."""
    ok, reason = gk.check_r01()
    assert ok is False
    assert "No .last_confirmation" in reason


def test_check_r01_expired_confirmation(isolated_state):
    """Covers lines 46-47: timestamp > 300s old → (False, '>5 Min abgelaufen')."""
    old_ts = int(time.time()) - 600
    (isolated_state / ".last_confirmation").write_text(str(old_ts))
    ok, reason = gk.check_r01()
    assert ok is False
    assert ">5 Min" in reason


def test_check_r01_valid_confirmation(isolated_state):
    """Covers line 48: fresh timestamp → (True, '')."""
    fresh_ts = int(time.time()) - 60
    (isolated_state / ".last_confirmation").write_text(str(fresh_ts))
    ok, reason = gk.check_r01()
    assert ok is True


def test_check_r18_no_audit_log(isolated_state):
    """Covers lines 51-52: no AUDIT_file → (False, 'No Audit-Log')."""
    ok, reason = gk.check_r18("WRITE /path")
    assert ok is False
    assert "No Audit-Log" in reason


def test_check_r18_empty_audit_log(isolated_state):
    """Covers lines 54-56: empty audit → (False, 'Audit-Log empty')."""
    (isolated_state / "audit.log.jsonl").write_text("")
    ok, reason = gk.check_r18("WRITE /path")
    assert ok is False
    assert "Audit-Log empty" in reason


def test_check_r18_delegate_action_executor(isolated_state):
    """Covers lines 57-59: last action = DELEGATE to action-executor → (True, '')."""
    (isolated_state / "audit.log.jsonl").write_text(json.dumps({
        "action": "DELEGATE",
        "target": "sub_mas-action-executor"
    }) + "\n")
    ok, reason = gk.check_r18("WRITE /path")
    assert ok is True


def test_check_r18_non_delegate_action(isolated_state):
    """Covers line 60: last action ≠ DELEGATE → (False, ...)."""
    (isolated_state / "audit.log.jsonl").write_text(json.dumps({
        "action": "WRITE",
        "target": "/path"
    }) + "\n")
    ok, reason = gk.check_r18("WRITE /path")
    assert ok is False


def test_check_r19_write_outside_mas(isolated_state):
    """Covers lines 64-66: path starts with /home but not mas-engineer → blocked."""
    ok, reason = gk.check_r19("WRITE /home/user/other-project/file.py", "write")
    assert ok is False
    assert "outside MAS" in reason


def test_check_r19_write_to_git(isolated_state):
    """Covers lines 67-68: .git/ in path → blocked."""
    ok, reason = gk.check_r19("WRITE mas-engineer/.git/config", "write")
    assert ok is False
    assert ".git/ verboten" in reason


def test_check_r19_write_to_mas(isolated_state):
    """Covers line 69: valid path → (True, '')."""
    ok, reason = gk.check_r19("WRITE mas-engineer/tools/foo.py", "write")
    assert ok is True


def test_check_r19_shell_dev_build_allowed(isolated_state):
    """Covers lines 70-73: shell with dev_build/dev_install → allowed."""
    ok, reason = gk.check_r19("python3 mas-engineer/tools/dev_build.py", "shell")
    assert ok is True


def test_check_r19_shell_other_tool_blocked(isolated_state):
    """Covers lines 70-72: shell on tools/ without build/install → blocked."""
    ok, reason = gk.check_r19("python3 mas-engineer/tools/dev_other.py", "shell")
    assert ok is False
    assert "Source-Tool-Path" in reason


def test_check_r20_always_true():
    """Covers line 78: check_r20() always returns (True, '')."""
    ok, reason = gk.check_r20("write")
    assert ok is True


def test_check_r10_non_yaml_file_skipped():
    """Covers line 83: target doesn't end with .yaml/.yml → skipped."""
    ok, reason = gk.check_r10("write", "WRITE file.py", "content")
    assert ok is True


def test_check_r10_yaml_valid(isolated_state):
    """Covers line 86: valid yaml content → (True, '')."""
    ok, reason = gk.check_r10("write", "WRITE file.yaml", "name: test\n")
    assert ok is True


def test_check_r10_yaml_invalid(isolated_state):
    """Covers lines 87-88: invalid yaml content → (False, 'YAML-Error')."""
    ok, reason = gk.check_r10("write", "WRITE file.yaml", "invalid: yaml: [")
    assert ok is False
    assert "YAML-Error" in reason


def test_check_r05_non_write_action_skipped():
    """Covers line 91: at not in write/edit/delete → (True, '')."""
    ok, reason = gk.check_r05("read")
    assert ok is True


def test_check_r05_no_checkpoint_dir(isolated_state):
    """Covers lines 92-93: checkpoints/ dir missing → (False, 'No Checkpoint-Directory')."""
    ok, reason = gk.check_r05("write")
    assert ok is False
    assert "No Checkpoint" in reason


def test_check_r05_no_recent_checkpoint(isolated_state):
    """Covers lines 96-100: checkpoints exist but all > 30 min old."""
    cp_dir = isolated_state / "checkpoints"
    cp_dir.mkdir()
    # Old timestamp (1 hour ago)
    old_ts = int(time.time()) - 3600
    (cp_dir / f"cp_1_{old_ts}").write_text("")
    ok, reason = gk.check_r05("write")
    assert ok is False


def test_check_r05_recent_checkpoint_exists(isolated_state):
    """Covers line 99: checkpoint < 30 min old → (True, '')."""
    cp_dir = isolated_state / "checkpoints"
    cp_dir.mkdir()
    # Recent timestamp (5 min ago)
    recent_ts = int(time.time()) - 300
    (cp_dir / f"cp_1_{recent_ts}").write_text("")
    ok, reason = gk.check_r05("write")
    assert ok is True
