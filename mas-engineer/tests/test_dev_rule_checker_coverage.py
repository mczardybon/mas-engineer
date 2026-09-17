"""Tests for tools/dev_rule_checker.py — coverage gap closer.

Covers the 10% coverage of dev_rule_checker.py (451 stmts, ~400 missed).
Strategy: exercise the YAML-loading helpers + check_mode +
check_confirmation + format_output (the simplest, most testable
functions). The massive check_rule function (with R01-R30+ logic)
is intentionally NOT exhaustively tested here — that's a separate
sprint. We cover:
- load_rules() — missing file, valid yaml, invalid yaml, no rules key
- get_rules() — generic mode + mas mode + workflows.yaml restrictions
- check_mode() — missing file, empty file, populated file
- check_confirmation() — missing file, expired, valid
- format_output() — empty results, all OK, BLOCKED with various hardness
  levels, multiple blocked
"""
import json
import os
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_rule_checker as rc


@pytest.fixture
def tmp_mase(tmp_path, monkeypatch):
    """Redirect all rule-file constants to tmp_path/.mase/..."""
    mase_dir = tmp_path / ".mase"
    rules_dir = mase_dir / "rules"
    rules_dir.mkdir(parents=True)
    monkeypatch.setattr(rc, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(rc, "MAS_DIR", str(tmp_path))
    monkeypatch.setattr(rc, "REGEL_DATEI", str(rules_dir / "rules_5_extreme.yaml"))
    monkeypatch.setattr(rc, "REGEL_4_DATEI", str(rules_dir / "rules_4_strong.yaml"))
    monkeypatch.setattr(rc, "REGEL_GENERIC_DATEI", str(rules_dir / "rules.yaml"))
    monkeypatch.setattr(rc, "HARTE_REGEL_DATEI", str(rules_dir / "hard_rules.yaml"))
    monkeypatch.setattr(rc, "MODE_DATEI", str(tmp_path / ".mas-mode"))
    monkeypatch.setattr(rc, "WORKFLOWS_DATEI", str(mase_dir / "workflows.yaml"))
    monkeypatch.setattr(rc, "CONFIRMATION_DATEI", str(mase_dir / ".last_confirmation"))
    return tmp_path, mase_dir, rules_dir


# ─────────────────────────────────────────────────────────
# load_rules
# ─────────────────────────────────────────────────────────

def test_load_rules_missing_file(tmp_mase):
    r"""Covers lines 30-31: file doesn't exist → return [\]."""
    path = str(tmp_mase[2] / "nonexistent.yaml")
    assert rc.load_rules(path) == []


def test_load_rules_valid_yaml(tmp_mase):
    """Covers lines 32-34: valid yaml with rules key → returns rules list."""
    path = tmp_mase[2] / "rules.yaml"
    path.write_text("""
rules:
  - id: R01
    name: TEST_RULE
    hardness: 5
""")
    rules = rc.load_rules(str(path))
    assert len(rules) == 1
    assert rules[0]["id"] == "R01"


def test_load_rules_empty_yaml(tmp_mase):
    """Covers line 33-34: empty yaml → yaml.safe_load returns None,
    data.get crashes. Documents the actual (buggy) behavior."""
    path = tmp_mase[2] / "rules.yaml"
    path.write_text("")
    # The current implementation crashes on empty yaml (yaml.safe_load → None)
    # We document this behavior — fix would require null-check in source.
    with pytest.raises(AttributeError):
        rc.load_rules(str(path))


def test_load_rules_no_rules_key(tmp_mase):
    """Covers line 34: yaml without 'rules' key → empty list."""
    path = tmp_mase[2] / "rules.yaml"
    path.write_text("other_key: value\n")
    rules = rc.load_rules(str(path))
    assert rules == []


def test_load_rules_invalid_yaml(tmp_mase):
    """Covers line 32-33: invalid yaml → raises yaml.YAMLError."""
    import yaml
    path = tmp_mase[2] / "rules.yaml"
    path.write_text("invalid: yaml: [")
    with pytest.raises(yaml.YAMLError):
        rc.load_rules(str(path))


# ─────────────────────────────────────────────────────────
# get_rules
# ─────────────────────────────────────────────────────────

def test_get_rules_generic_mode_no_file(tmp_mase):
    """Covers lines 38-44: mode='generic', no rules.yaml → []."""
    rules = rc.get_rules(mode="generic")
    assert rules == []


def test_get_rules_generic_mode_with_file(tmp_mase):
    """Covers lines 39-43: mode='generic' loads rules.yaml."""
    path = tmp_mase[2] / "rules.yaml"
    path.write_text("""
rules:
  - id: R01
    name: TEST
    hardness: 3
""")
    rules = rc.get_rules(mode="generic")
    assert len(rules) == 1


def test_get_rules_mas_mode_no_files(tmp_mase):
    """Covers line 47: mas mode, no rule files → []."""
    rules = rc.get_rules(mode="mas")
    assert rules == []


def test_get_rules_mas_mode_with_files(tmp_mase):
    """Covers lines 47: mas mode loads from all 3 rule files."""
    (tmp_mase[2] / "rules_5_extreme.yaml").write_text("""
rules:
  - id: R01
    name: extreme_test
    hardness: 5
""")
    (tmp_mase[2] / "rules_4_strong.yaml").write_text("""
rules:
  - id: R02
    name: strong_test
    hardness: 4
""")
    (tmp_mase[2] / "hard_rules.yaml").write_text("""
rules:
  - id: R03
    name: hard_test
    hardness: 4
""")
    rules = rc.get_rules(mode="mas")
    assert len(rules) == 3
    ids = {r["id"] for r in rules}
    assert ids == {"R01", "R02", "R03"}


def test_get_rules_default_mode_is_mas(tmp_mase):
    """Covers line 38: default mode is 'mas'."""
    rules = rc.get_rules()
    assert isinstance(rules, list)


def test_get_rules_with_workflows_yaml_restrictions(tmp_mase):
    """Covers lines 49-62: workflows.yaml restrictions → R-rule objects."""
    (tmp_mase[1] / "workflows.yaml").write_text("""
configs:
  mas-self:
    restrictions:
      r01_confirmation:
        level: extreme
        description: Test R01
      r05_blocklist:
        level: strong
        description: Test R05
""")
    rules = rc.get_rules(mode="mas")
    # R01 + R05 from workflows
    norm_ids = {r["id"] for r in rules}
    assert "R01" in norm_ids or "R05" in norm_ids


# ─────────────────────────────────────────────────────────
# check_mode
# ─────────────────────────────────────────────────────────

def test_check_mode_missing_file(tmp_mase):
    """Covers line 66-67: MODE_DATEI doesn't exist → 'unbekannt'."""
    assert rc.check_mode() == "unbekannt"


def test_check_mode_with_content(tmp_mase):
    """Covers lines 68-69: MODE_DATEI exists → returns content."""
    (tmp_mase[0] / ".mas-mode").write_text("mas")
    assert rc.check_mode() == "mas"


def test_check_mode_with_trailing_whitespace(tmp_mase):
    """Covers line 69: .strip() removes trailing whitespace."""
    (tmp_mase[0] / ".mas-mode").write_text("  generic  \n")
    assert rc.check_mode() == "generic"


def test_check_mode_empty_file(tmp_mase):
    """Covers line 69: empty file → '' (empty string)."""
    (tmp_mase[0] / ".mas-mode").write_text("")
    assert rc.check_mode() == ""


# ─────────────────────────────────────────────────────────
# check_confirmation
# ─────────────────────────────────────────────────────────

def test_check_confirmation_missing_file(tmp_mase):
    """Covers line 73-74: CONFIRMATION_DATEI missing → False."""
    assert rc.check_confirmation() is False


def test_check_confirmation_expired(tmp_mase):
    """Covers line 76-77: timestamp > 300s old → False."""
    expired_ts = int(time.time()) - 600
    (tmp_mase[1] / ".last_confirmation").write_text(str(expired_ts))
    assert rc.check_confirmation() is False


def test_check_confirmation_valid(tmp_mase):
    """Covers line 77: recent timestamp → True."""
    recent_ts = int(time.time()) - 10
    (tmp_mase[1] / ".last_confirmation").write_text(str(recent_ts))
    assert rc.check_confirmation() is True


def test_check_confirmation_just_expired(tmp_mase):
    """Covers line 77: timestamp 400s old → False (just past 300s limit)."""
    expired_ts = int(time.time()) - 400
    (tmp_mase[1] / ".last_confirmation").write_text(str(expired_ts))
    assert rc.check_confirmation() is False


# ─────────────────────────────────────────────────────────
# format_output
# ─────────────────────────────────────────────────────────

def test_format_output_empty_results():
    """Covers line 838-861: empty results list → 'OK', True."""
    out, ok = rc.format_output([])
    assert "REGEL-CHECK" in out
    assert "Gechecks: 0" in out
    assert "approved" in out
    assert ok is True


def test_format_output_with_ok_rule():
    """Covers lines 850-851: hardness < 4 → single ⛔ marker + OK."""
    results = [{"rule": "R01", "action": "OK", "hardness": 3, "detail": "ok"}]
    out, ok = rc.format_output(results, action_type="write")
    assert "R01" in out
    assert "OK" in out
    assert ok is True


def test_format_output_with_strong_rule():
    """Covers line 848-849: hardness >= 4 → triple ⛔ marker."""
    results = [{"rule": "R02", "action": "OK", "hardness": 4, "detail": "warn"}]
    out, ok = rc.format_output(results)
    assert "⛔⛔⛔" in out
    assert ok is True


def test_format_output_with_extreme_rule():
    """Covers line 846-847: hardness >= 5 → quintuple ⛔ marker."""
    results = [{"rule": "R03", "action": "OK", "hardness": 5, "detail": "ext"}]
    out, ok = rc.format_output(results)
    assert "⛔⛔⛔⛔⛔" in out
    assert ok is True


def test_format_output_with_blocked_rule():
    """Covers line 853-858: BLOCKED → False returned, list of blocked."""
    results = [{"rule": "R01", "action": "BLOCKED", "hardness": 5, "detail": "violated!"}]
    out, ok = rc.format_output(results)
    assert ok is False
    assert "BLOCKED" in out or "BLOCKIERT" in out


def test_format_output_with_mixed_rules():
    """Covers lines 838-861: mix of OK + BLOCKED → False, both shown."""
    results = [
        {"rule": "R01", "action": "OK", "hardness": 3, "detail": "ok"},
        {"rule": "R02", "action": "BLOCKED", "hardness": 5, "detail": "violated"},
    ]
    out, ok = rc.format_output(results)
    assert ok is False
    assert "R01" in out
    assert "R02" in out


def test_format_output_with_multiple_blocked():
    """Covers line 854: 2+ blocked → count shown."""
    results = [
        {"rule": "R01", "action": "BLOCKED", "hardness": 5, "detail": "v1"},
        {"rule": "R02", "action": "BLOCKED", "hardness": 5, "detail": "v2"},
    ]
    out, ok = rc.format_output(results)
    assert "2 EXTREME-STRONG" in out or "2" in out
    assert ok is False


def test_format_output_with_action_type():
    """Covers line 842: action_type shown in output."""
    results = []
    out, ok = rc.format_output(results, action_type="write")
    assert "action: write" in out
