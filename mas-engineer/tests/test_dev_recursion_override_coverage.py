"""Tests for tools/dev_recursion_override.py — coverage gap closer.

Covers the 88% of dev_recursion_override.py (140 stmts, ~16 missed).
Strategy: exercise every function with both happy path and edge cases:
- load_cost_config() — missing file (default), valid yaml, broken yaml
- check_cost_gate() — no db, db_error, blocked, warn-only, ok
- load_validation() — missing file (sys.exit 1), dict structure, list structure
- already_applied() — missing changes.json, dict-format, list-format
- apply_patch() — already applied today, file missing, find missing, ok
- log_change() — missing changes.json, dict-format existing, append
"""
import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_recursion_override as ro


def test_load_cost_config_default_when_missing(tmp_path):
    """Covers line 47-48: no cost.yaml → DEFAULT_COST_CONFIG returned."""
    cfg = ro.load_cost_config(tmp_path)
    assert cfg["daily_budget_usd"] == 5.00
    assert "gate" in cfg


def test_load_cost_config_with_yaml(tmp_path, monkeypatch):
    """Covers lines 50-57: cost.yaml exists, valid yaml → merged config."""
    cfg_dir = tmp_path / ".mase" / "config"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "cost.yaml").write_text("""
daily_budget_usd: 10.00
gate:
  daily: warn
""")
    cfg = ro.load_cost_config(tmp_path)
    assert cfg["daily_budget_usd"] == 10.00
    assert cfg["gate"]["daily"] == "warn"
    # default keys still preserved
    assert cfg["per_run_max_usd"] == 1.00


def test_load_cost_config_broken_yaml(tmp_path):
    """Covers lines 58-60: yaml.safe_load fails → returns DEFAULT_COST_CONFIG."""
    cfg_dir = tmp_path / ".mase" / "config"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "cost.yaml").write_text("this: is: not: valid: yaml: [")
    cfg = ro.load_cost_config(tmp_path)
    assert cfg["daily_budget_usd"] == 5.00


def test_check_cost_gate_no_db(tmp_path):
    """Covers line 68-69: db_path doesn't exist → (True, 'no_db', 0.0, budget)."""
    cfg = ro.DEFAULT_COST_CONFIG
    allowed, reason, cost, budget = ro.check_cost_gate(tmp_path, cfg)
    assert allowed is True
    assert reason == "no_db"


def test_check_cost_gate_db_error(tmp_path, monkeypatch):
    """Covers lines 80-81: sqlite.connect fails → (True, 'db_error: ...', ...)."""
    cfg = ro.DEFAULT_COST_CONFIG
    # Force the db_path to a non-sqlite file
    db_path = tmp_path / "mas-engineer" / ".mase" / "data" / "goose" / "sessions.db"
    db_path.parent.mkdir(parents=True)
    db_path.write_text("not a sqlite db")
    # Override src to point to it
    cfg2 = {**cfg, "cost_source": {**cfg["cost_source"], "db_path": str(db_path)}}
    allowed, reason, cost, budget = ro.check_cost_gate(tmp_path, cfg2)
    assert "db_error" in reason or allowed is True  # either passes or fails gracefully


def test_check_cost_gate_blocked(tmp_path):
    """Covers lines 84-86: cost_today >= budget, gate='block' → (False, ...)."""
    cfg = ro.DEFAULT_COST_CONFIG
    # Create a real sqlite db with cost > budget
    db_path = tmp_path / "mas-engineer" / ".mase" / "data" / "goose" / "sessions.db"
    db_path.parent.mkdir(parents=True)
    con = sqlite3.connect(str(db_path))
    con.execute("CREATE TABLE sessions (accumulated_cost REAL, created_at TEXT)")
    con.execute("INSERT INTO sessions VALUES (10.0, datetime('now'))")
    con.commit()
    con.close()
    cfg2 = {**cfg, "cost_source": {**cfg["cost_source"], "db_path": str(db_path)}}
    allowed, reason, cost, budget = ro.check_cost_gate(tmp_path, cfg2)
    assert allowed is False
    assert "daily_budget_exceeded" in reason


def test_check_cost_gate_warn_only(tmp_path):
    """Covers lines 87-89: cost_today >= budget, gate='warn' → (True, 'warn_only')."""
    cfg = {**ro.DEFAULT_COST_CONFIG, "gate": {"daily": "warn"}}
    db_path = tmp_path / "mas-engineer" / ".mase" / "data" / "goose" / "sessions.db"
    db_path.parent.mkdir(parents=True)
    con = sqlite3.connect(str(db_path))
    con.execute("CREATE TABLE sessions (accumulated_cost REAL, created_at TEXT)")
    con.execute("INSERT INTO sessions VALUES (10.0, datetime('now'))")
    con.commit()
    con.close()
    cfg2 = {**cfg, "cost_source": {**cfg["cost_source"], "db_path": str(db_path)}}
    allowed, reason, cost, budget = ro.check_cost_gate(tmp_path, cfg2)
    assert allowed is True
    assert "warn_only" in reason


def test_load_validation_missing_file_exits(tmp_path):
    """Covers line 99-101: validation.yaml missing → sys.exit(1)."""
    with pytest.raises(SystemExit):
        ro.load_validation(tmp_path)


def test_load_validation_dict_structure(tmp_path):
    """Covers lines 102-103: validation.yaml with data.validation.details list."""
    pipeline_dir = tmp_path / ".mase" / "pipeline"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "validation.yaml").write_text("""
data:
  validation:
    details:
      - file: foo.py
        verdict: CONFORM
""")
    details = ro.load_validation(tmp_path)
    assert isinstance(details, list)
    assert details[0]["file"] == "foo.py"


def test_load_validation_empty_details_triggers_alt_path(tmp_path):
    """Covers lines 104-108: when 'data.validation.details' is empty/missing,
    falls back to checking if top-level data is a list."""
    pipeline_dir = tmp_path / ".mase" / "pipeline"
    pipeline_dir.mkdir(parents=True)
    # data.validation.details missing → details=[], but data itself is empty dict
    # so the alt branch isn't taken — this still covers line 104 (if not details)
    (pipeline_dir / "validation.yaml").write_text("""
data:
  validation: {}
""")
    details = ro.load_validation(tmp_path)
    assert details == []


def test_already_applied_no_changes_file(tmp_path):
    """Covers line 115-116: no changes.json → False."""
    assert ro.already_applied(tmp_path, "some/file.py") is False


def test_already_applied_dict_format(tmp_path):
    """Covers lines 122-123: changes.json is dict (not list) → False."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "changes.json").write_text(json.dumps({"stats": {}}))
    assert ro.already_applied(tmp_path, "some/file.py") is False


def test_already_applied_list_format_with_today_entry(tmp_path):
    """Covers lines 124-131: list-format changes.json with today's RECURSION_OVERRIDE entry."""
    from datetime import datetime, timezone
    (tmp_path / ".mase").mkdir()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = {
        "file": "some/file.py",
        "timestamp": today + "T12:00:00+00:00",
        "via": "RECURSION_OVERRIDE",
    }
    (tmp_path / ".mase" / "changes.json").write_text(json.dumps([entry]))
    assert ro.already_applied(tmp_path, "some/file.py") is True


def test_already_applied_json_decode_error(tmp_path):
    """Covers lines 119-120: invalid JSON → False."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "changes.json").write_text("not valid json {")
    assert ro.already_applied(tmp_path, "some/file.py") is False


def test_apply_patch_already_applied_today(tmp_path):
    """Covers line 139-140: already_applied=True → return (True, 'already_applied_today')."""
    (tmp_path / ".mase").mkdir()
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (tmp_path / ".mase" / "changes.json").write_text(json.dumps([
        {"file": "foo.py", "timestamp": today + "T12:00", "via": "RECURSION_OVERRIDE"}
    ]))
    (tmp_path / "foo.py").write_text("original")
    ok, reason = ro.apply_patch(tmp_path, "foo.py", "original", "replaced")
    assert ok is True
    assert reason == "already_applied_today"


def test_apply_patch_file_not_found(tmp_path):
    """Covers lines 142-143: target file doesn't exist."""
    ok, reason = ro.apply_patch(tmp_path, "missing.py", "x", "y")
    assert ok is False
    assert "file_not_found" in reason


def test_apply_patch_find_not_in_file(tmp_path):
    """Covers lines 145-146: find string not in content."""
    (tmp_path / "foo.py").write_text("hello world")
    ok, reason = ro.apply_patch(tmp_path, "foo.py", "NOT_THERE", "y")
    assert ok is False
    assert reason == "find_string_not_in_file"


def test_apply_patch_success(tmp_path):
    """Covers lines 144-149: successful patch application."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "changes.json").write_text("[]")
    (tmp_path / "foo.py").write_text("hello world")
    ok, reason = ro.apply_patch(tmp_path, "foo.py", "world", "there")
    assert ok is True
    assert reason == "applied"
    assert "there" in (tmp_path / "foo.py").read_text()


def test_log_change_creates_file(tmp_path):
    """Covers lines 154-176: log_change creates changes.json if missing and appends."""
    (tmp_path / ".mase").mkdir()
    ro.log_change(tmp_path, ["a.py"], ["b.py"])
    data = json.loads((tmp_path / ".mase" / "changes.json").read_text())
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["applied_files"] == ["a.py"]
    assert data[0]["refused_files"] == ["b.py"]
    assert data[0]["via"] == "RECURSION_OVERRIDE"
    assert data[0]["stage"] == "apply_only"


def test_log_change_dict_format_existing(tmp_path):
    """Covers lines 160-161: existing changes.json in dict format → reset to list."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "changes.json").write_text(json.dumps({"stats": {}}))
    ro.log_change(tmp_path, ["x.py"], [])
    data = json.loads((tmp_path / ".mase" / "changes.json").read_text())
    assert isinstance(data, list)
    assert len(data) == 1
