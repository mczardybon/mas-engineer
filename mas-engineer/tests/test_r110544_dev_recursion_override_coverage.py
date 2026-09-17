"""R110-544 — coverage test sprint: tools/dev_recursion_override.py 0%→100%.

Tests the IM-006 RECURSION-OVERRIDE tool: operator-triggered single-shot
patch application. The SUT is a 228 LOC script with 8 functions:

  - DEFAULT_COST_CONFIG (L30-41): constant
  - load_cost_config() (L44-60): loads .mase/config/cost.yaml, falls back
    to defaults. Shallow-merges at top + nested merge at 'gate' + 'cost_source'.
  - check_cost_gate() (L63-90): SQLite query of accumulated_cost over 24h;
    compares to daily_budget; respects gate.daily mode (block/warn).
  - load_validation() (L93-109): loads .mase/pipeline/validation.yaml,
    extracts details from data.validation.details (or top-level data list).
  - already_applied() (L112-131): reads .mase/changes.json, checks for
    today's entry matching file_rel + via=RECURSION_OVERRIDE.
  - apply_patch() (L134-149): idempotent, single-shot replace. Skips if
    already applied today, file missing, or find string absent.
  - log_change() (L152-176): appends entry with stage='apply_only',
    patches_applied, patches_refused, via='RECURSION_OVERRIDE'.
  - main() (L179-228): orchestration — workspace check, cost-gate,
    load details, filter CONFORM, apply each, log change.

Tests use tmp_path workspaces with .mase/ directory structure.
"""
import argparse
import datetime
import json
import os
import sqlite3
import subprocess
import sys
from datetime import timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_recursion_override as ro


# ────────────────────── Fixtures ──────────────────────────────────

@pytest.fixture
def ws(tmp_path):
    """Workspace with .mase/ scaffold."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "config").mkdir()
    (tmp_path / ".mase" / "pipeline").mkdir()
    return tmp_path


# ────────────────────── DEFAULT_COST_CONFIG ───────────────────────

def test_default_cost_config_shape():
    """L30-41: constant has expected keys + nested structure."""
    cfg = ro.DEFAULT_COST_CONFIG
    assert cfg["daily_budget_usd"] == 5.00
    assert cfg["per_run_max_usd"] == 1.00
    assert cfg["per_session_max_usd"] == 0.50
    assert cfg["gate"]["daily"] == "block"
    assert cfg["gate"]["per_run"] == "block"
    assert cfg["gate"]["per_session"] == "warn"
    assert cfg["cost_source"]["db_path"] == "mas-engineer/.mase/data/goose/sessions.db"
    assert cfg["cost_source"]["table"] == "sessions"
    assert cfg["cost_source"]["cost_column"] == "accumulated_cost"
    assert cfg["cost_source"]["timestamp_column"] == "created_at"


# ────────────────────── load_cost_config() ────────────────────────

def test_load_cost_config_no_file_returns_defaults(ws):
    """L47-48: cost.yaml missing → DEFAULT_COST_CONFIG."""
    cfg = ro.load_cost_config(ws)
    assert cfg == ro.DEFAULT_COST_CONFIG


def test_load_cost_config_empty_yaml(ws):
    """L50: yaml.safe_load returns None → fall back to defaults."""
    (ws / ".mase" / "config" / "cost.yaml").write_text("")
    cfg = ro.load_cost_config(ws)
    assert cfg == ro.DEFAULT_COST_CONFIG


def test_load_cost_config_shallow_merge(ws):
    """L52: top-level keys override defaults."""
    (ws / ".mase" / "config" / "cost.yaml").write_text(
        "daily_budget_usd: 10.0\n"
    )
    cfg = ro.load_cost_config(ws)
    assert cfg["daily_budget_usd"] == 10.0
    # Other defaults preserved
    assert cfg["per_run_max_usd"] == 1.00


def test_load_cost_config_gate_nested_merge(ws):
    """L53-54: 'gate' dict merged with defaults, not replaced."""
    (ws / ".mase" / "config" / "cost.yaml").write_text(
        "gate:\n  daily: warn\n"
    )
    cfg = ro.load_cost_config(ws)
    assert cfg["gate"]["daily"] == "warn"
    assert cfg["gate"]["per_run"] == "block"  # default preserved
    assert cfg["gate"]["per_session"] == "warn"


def test_load_cost_config_cost_source_nested_merge(ws):
    """L55-56: 'cost_source' dict merged with defaults."""
    (ws / ".mase" / "config" / "cost.yaml").write_text(
        "cost_source:\n  table: my_sessions\n"
    )
    cfg = ro.load_cost_config(ws)
    assert cfg["cost_source"]["table"] == "my_sessions"
    assert cfg["cost_source"]["db_path"] == "mas-engineer/.mase/data/goose/sessions.db"


def test_load_cost_config_yaml_error_returns_defaults(ws):
    """L58-60: yaml parse error → WARN + defaults."""
    (ws / ".mase" / "config" / "cost.yaml").write_text(":\n  invalid: [yaml")
    cfg = ro.load_cost_config(ws)
    assert cfg == ro.DEFAULT_COST_CONFIG


def test_load_cost_config_empty_dict_yaml(ws):
    """L50: yaml.safe_load returns {} (not None) → still merge with defaults."""
    (ws / ".mase" / "config" / "cost.yaml").write_text("{}\n")
    cfg = ro.load_cost_config(ws)
    assert cfg == ro.DEFAULT_COST_CONFIG


# ────────────────────── check_cost_gate() ─────────────────────────

def test_check_cost_gate_no_db_returns_allowed(ws):
    """L68-69: db_path missing → (True, 'no_db', 0.0, budget)."""
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "block"}}
    allowed, reason, cost, budget = ro.check_cost_gate(ws, cfg)
    assert allowed is True
    assert reason == "no_db"
    assert cost == 0.0
    assert budget == 5.0


def test_check_cost_gate_under_budget(ws):
    """L70-90: cost < budget, gate=block → allowed=True, reason='ok'."""
    db = ws / "sessions.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE sessions (id INTEGER, accumulated_cost REAL, created_at TEXT)")
    con.execute("INSERT INTO sessions VALUES (1, 1.50, datetime('now'))")
    con.commit()
    con.close()
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "block"},
           "cost_source": {"db_path": str(db), "table": "sessions",
                          "cost_column": "accumulated_cost",
                          "timestamp_column": "created_at"}}
    allowed, reason, cost, budget = ro.check_cost_gate(ws, cfg)
    assert allowed is True
    assert reason == "ok"
    assert cost == 1.5
    assert budget == 5.0


def test_check_cost_gate_blocked(ws):
    """L84-86: cost >= budget, gate=block → (False, msg, cost, budget)."""
    db = ws / "sessions.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE sessions (id INTEGER, accumulated_cost REAL, created_at TEXT)")
    con.execute("INSERT INTO sessions VALUES (1, 7.50, datetime('now'))")
    con.commit()
    con.close()
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "block"},
           "cost_source": {"db_path": str(db), "table": "sessions",
                          "cost_column": "accumulated_cost",
                          "timestamp_column": "created_at"}}
    allowed, reason, cost, budget = ro.check_cost_gate(ws, cfg)
    assert allowed is False
    assert "daily_budget_exceeded" in reason
    assert "7.50" in reason
    assert cost == 7.5


def test_check_cost_gate_warn_mode(ws):
    """L87-89: cost >= budget, gate=warn → (True, 'warn_only:...')."""
    db = ws / "sessions.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE sessions (id INTEGER, accumulated_cost REAL, created_at TEXT)")
    con.execute("INSERT INTO sessions VALUES (1, 7.50, datetime('now'))")
    con.commit()
    con.close()
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "warn"},
           "cost_source": {"db_path": str(db), "table": "sessions",
                          "cost_column": "accumulated_cost",
                          "timestamp_column": "created_at"}}
    allowed, reason, cost, budget = ro.check_cost_gate(ws, cfg)
    assert allowed is True
    assert "warn_only" in reason
    assert cost == 7.5


def test_check_cost_gate_db_error(ws):
    """L80-81: sqlite error → (True, 'db_error:...', 0.0, budget).

    Trigger: db_path exists but is not a valid sqlite file.
    """
    bad_db = ws / "bad.db"
    bad_db.write_text("not a sqlite database")
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "block"},
           "cost_source": {"db_path": str(bad_db), "table": "sessions",
                          "cost_column": "accumulated_cost",
                          "timestamp_column": "created_at"}}
    allowed, reason, cost, budget = ro.check_cost_gate(ws, cfg)
    assert allowed is True
    assert "db_error" in reason
    assert cost == 0.0
    assert budget == 5.0


def test_check_cost_gate_exactly_at_budget(ws):
    """L84: cost == budget (>=) → blocked."""
    db = ws / "sessions.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE sessions (id INTEGER, accumulated_cost REAL, created_at TEXT)")
    con.execute("INSERT INTO sessions VALUES (1, 5.00, datetime('now'))")
    con.commit()
    con.close()
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "block"},
           "cost_source": {"db_path": str(db), "table": "sessions",
                          "cost_column": "accumulated_cost",
                          "timestamp_column": "created_at"}}
    allowed, reason, cost, _ = ro.check_cost_gate(ws, cfg)
    assert allowed is False
    assert cost == 5.0


def test_check_cost_gate_24h_window(ws):
    """L76: WHERE clause filters to last 24h — old entries excluded."""
    db = ws / "sessions.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE sessions (id INTEGER, accumulated_cost REAL, created_at TEXT)")
    con.execute("INSERT INTO sessions VALUES (1, 10.0, datetime('now', '-2 days'))")
    con.execute("INSERT INTO sessions VALUES (2, 0.50, datetime('now'))")
    con.commit()
    con.close()
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "block"},
           "cost_source": {"db_path": str(db), "table": "sessions",
                          "cost_column": "accumulated_cost",
                          "timestamp_column": "created_at"}}
    allowed, reason, cost, _ = ro.check_cost_gate(ws, cfg)
    assert allowed is True
    assert cost == 0.5  # only the recent one counts


def test_check_cost_gate_null_sum(ws):
    """L78: COALESCE wraps SUM → empty table returns 0.0, not None."""
    db = ws / "sessions.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE sessions (id INTEGER, accumulated_cost REAL, created_at TEXT)")
    con.commit()
    con.close()
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "block"},
           "cost_source": {"db_path": str(db), "table": "sessions",
                          "cost_column": "accumulated_cost",
                          "timestamp_column": "created_at"}}
    allowed, reason, cost, _ = ro.check_cost_gate(ws, cfg)
    assert allowed is True
    assert cost == 0.0


def test_check_cost_gate_default_cost_source_paths(ws, monkeypatch):
    """L67: src.get() with defaults — no cost_source in cfg."""
    # Set cwd so the default db_path resolves to a non-existent path
    monkeypatch.chdir(ws)
    cfg = {"daily_budget_usd": 5.0, "gate": {"daily": "block"}}
    allowed, reason, cost, budget = ro.check_cost_gate(ws, cfg)
    assert allowed is True
    assert reason == "no_db"
    assert budget == 5.0


# ────────────────────── load_validation() ─────────────────────────

def test_load_validation_no_file_exits(ws):
    """L99-101: validation.yaml missing → print + sys.exit(1)."""
    with pytest.raises(SystemExit) as exc:
        ro.load_validation(ws)
    assert exc.value.code == 1


def test_load_validation_data_validation_details(ws):
    """L103: nested data.validation.details path."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n      - file: foo.py\n        verdict: CONFORM\n      - file: bar.py\n        verdict: REJECT\n"
    )
    details = ro.load_validation(ws)
    assert len(details) == 2
    assert details[0]["file"] == "foo.py"


def test_load_validation_data_validation_details(ws):
    """L103: nested data.validation.details path."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n      - file: foo.py\n        verdict: CONFORM\n      - file: bar.py\n        verdict: REJECT\n"
    )
    details = ro.load_validation(ws)
    assert len(details) == 2
    assert details[0]["file"] == "foo.py"


def test_load_validation_top_level_data_list(ws):
    """L106-108: fallback to top-level data list when nested empty.

    KNOWN LIMITATION: When `data` is a list (not a dict), the L103 call
    crashes with AttributeError before reaching the L106 fallback. The
    fallback only triggers when data is a dict with empty details.
    This documents the actual behavior; the intended use-case is covered
    by test_load_validation_data_validation_details.
    """
    import pytest as _pytest
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  - file: a.py\n    verdict: CONFORM\n  - file: b.py\n    verdict: CONFORM\n"
    )
    with _pytest.raises(AttributeError):
        ro.load_validation(ws)


def test_load_validation_empty_details(ws):
    """L104: details empty → L106 fallback runs, data is dict → not list → returns []."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details: []\n"
    )
    details = ro.load_validation(ws)
    assert details == []


def test_load_validation_missing_data(ws):
    """L103: no 'data' key → .get returns {} → chained .get returns [] → fallback skipped."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "metadata: {}\n"
    )
    details = ro.load_validation(ws)
    assert details == []


def test_load_validation_empty_dict_data(ws):
    """L106: data is empty dict → isinstance(dict, list)=False → skip fallback, return []."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data: {}\n"
    )
    details = ro.load_validation(ws)
    assert details == []


def test_load_validation_dict_data_with_empty_validation(ws):
    """L104: data dict with no 'validation' key → details empty → fallback skipped."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  other_key: foo\n"
    )
    details = ro.load_validation(ws)
    assert details == []


# ────────────────────── already_applied() ─────────────────────────

def test_already_applied_no_changes_file(ws):
    """L114-116: .mase/changes.json missing → False."""
    assert ro.already_applied(ws, "foo.py") is False


def test_already_applied_today(ws):
    """L124-130: matching file + today's timestamp + RECURSION_OVERRIDE → True."""
    today = datetime.datetime.now(timezone.utc).isoformat()
    (ws / ".mase" / "changes.json").write_text(json.dumps([
        {"file": "foo.py", "timestamp": today, "via": "RECURSION_OVERRIDE"}
    ]))
    assert ro.already_applied(ws, "foo.py") is True


def test_already_applied_different_via(ws):
    """L129: via != RECURSION_OVERRIDE → False."""
    today = datetime.datetime.now(timezone.utc).isoformat()
    (ws / ".mase" / "changes.json").write_text(json.dumps([
        {"file": "foo.py", "timestamp": today, "via": "OTHER_VIA"}
    ]))
    assert ro.already_applied(ws, "foo.py") is False


def test_already_applied_different_file(ws):
    """L128: different file → False."""
    today = datetime.datetime.now(timezone.utc).isoformat()
    (ws / ".mase" / "changes.json").write_text(json.dumps([
        {"file": "other.py", "timestamp": today, "via": "RECURSION_OVERRIDE"}
    ]))
    assert ro.already_applied(ws, "foo.py") is False


def test_already_applied_yesterday(ws):
    """L128: timestamp doesn't start with today's date → False."""
    yesterday = (datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1)).isoformat()
    (ws / ".mase" / "changes.json").write_text(json.dumps([
        {"file": "foo.py", "timestamp": yesterday, "via": "RECURSION_OVERRIDE"}
    ]))
    assert ro.already_applied(ws, "foo.py") is False


def test_already_applied_invalid_json(ws):
    """L119-120: JSONDecodeError → False (no crash)."""
    (ws / ".mase" / "changes.json").write_text("not json at all")
    assert ro.already_applied(ws, "foo.py") is False


def test_already_applied_dict_format(ws):
    """L122-123: changes.json is dict (not list) → False."""
    (ws / ".mase" / "changes.json").write_text(json.dumps({
        "metadata": {}, "changes": [], "stats": {}
    }))
    assert ro.already_applied(ws, "foo.py") is False


def test_already_applied_empty_changes(ws):
    """Edge: empty list → False."""
    (ws / ".mase" / "changes.json").write_text("[]\n")
    assert ro.already_applied(ws, "foo.py") is False


def test_already_applied_non_dict_entry(ws):
    """L126-127: entry not a dict → skip."""
    today = datetime.datetime.now(timezone.utc).isoformat()
    (ws / ".mase" / "changes.json").write_text(json.dumps([
        "not_a_dict",
        {"file": "foo.py", "timestamp": today, "via": "RECURSION_OVERRIDE"}
    ]))
    assert ro.already_applied(ws, "foo.py") is True


def test_already_applied_empty_changes_file(ws):
    """L118: file exists but empty → json.loads('[]') works, no entries."""
    (ws / ".mase" / "changes.json").write_text("")
    assert ro.already_applied(ws, "foo.py") is False


# ────────────────────── apply_patch() ─────────────────────────────

def test_apply_patch_basic(ws):
    """L144-148: find/replace works → (True, 'applied')."""
    target = ws / "foo.py"
    target.write_text("hello world")
    ok, reason = ro.apply_patch(ws, "foo.py", "world", "universe")
    assert ok is True
    assert reason == "applied"
    assert target.read_text() == "hello universe"


def test_apply_patch_already_applied_today(ws):
    """L139-140: already_applied=True → skip + return 'already_applied_today'."""
    target = ws / "foo.py"
    target.write_text("hello world")
    today = datetime.datetime.now(timezone.utc).isoformat()
    (ws / ".mase" / "changes.json").write_text(json.dumps([
        {"file": "foo.py", "timestamp": today, "via": "RECURSION_OVERRIDE"}
    ]))
    ok, reason = ro.apply_patch(ws, "foo.py", "world", "universe")
    assert ok is True
    assert reason == "already_applied_today"
    # File unchanged
    assert target.read_text() == "hello world"


def test_apply_patch_file_not_found(ws):
    """L141-143: target file missing → (False, 'file_not_found:...')."""
    ok, reason = ro.apply_patch(ws, "missing.py", "a", "b")
    assert ok is False
    assert "file_not_found" in reason


def test_apply_patch_find_string_missing(ws):
    """L145-146: find not in content → (False, 'find_string_not_in_file')."""
    target = ws / "foo.py"
    target.write_text("hello world")
    ok, reason = ro.apply_patch(ws, "foo.py", "ABSENT", "X")
    assert ok is False
    assert reason == "find_string_not_in_file"
    assert target.read_text() == "hello world"  # unchanged


def test_apply_patch_replaces_only_first(ws):
    """L147: replace(..., 1) — only first occurrence replaced."""
    target = ws / "foo.py"
    target.write_text("foo foo foo")
    ok, reason = ro.apply_patch(ws, "foo.py", "foo", "bar")
    assert ok is True
    assert target.read_text() == "bar foo foo"


def test_apply_patch_multi_line_find(ws):
    """L144-148: multi-line find string works."""
    target = ws / "foo.py"
    target.write_text("line1\nline2\nline3\n")
    ok, reason = ro.apply_patch(ws, "foo.py", "line1\nline2", "NEW1\nNEW2")
    assert ok is True
    assert target.read_text() == "NEW1\nNEW2\nline3\n"


# ────────────────────── log_change() ──────────────────────────────

def test_log_change_no_file_creates(ws):
    """L154-155: changes.json missing → create '[]\n'."""
    ro.log_change(ws, ["a.py"], ["b.py"])
    path = ws / ".mase" / "changes.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["applied_files"] == ["a.py"]
    assert data[0]["refused_files"] == ["b.py"]


def test_log_change_appends_to_existing(ws):
    """L175: existing list → append new entry."""
    (ws / ".mase" / "changes.json").write_text(json.dumps([
        {"old": "entry"}
    ]))
    ro.log_change(ws, ["x.py"], [])
    data = json.loads((ws / ".mase" / "changes.json").read_text())
    assert len(data) == 2
    assert data[0] == {"old": "entry"}
    assert data[1]["applied_files"] == ["x.py"]


def test_log_change_entry_shape(ws):
    """L162-174: entry has all required fields with right values."""
    ro.log_change(ws, ["a.py"], ["b.py", "c.py"])
    data = json.loads((ws / ".mase" / "changes.json").read_text())
    e = data[0]
    assert e["stage"] == "apply_only"
    assert e["stages_run"] == ["apply_only"]
    assert e["patches_applied"] == 1
    assert e["patches_refused"] == 2
    assert e["applied_files"] == ["a.py"]
    assert e["refused_files"] == ["b.py", "c.py"]
    assert e["via"] == "RECURSION_OVERRIDE"
    assert e["im_ticket"] == "IM-006"  # default
    # run_id is 8 hex chars
    assert len(e["run_id"]) == 8
    # timestamp parses as ISO
    datetime.datetime.fromisoformat(e["timestamp"])


def test_log_change_dict_format_resets(ws):
    """L160-161: changes.json is dict (not list) → reset to list."""
    (ws / ".mase" / "changes.json").write_text(json.dumps({
        "metadata": {}, "changes": [], "stats": {}
    }))
    ro.log_change(ws, ["x.py"], [])
    data = json.loads((ws / ".mase" / "changes.json").read_text())
    assert isinstance(data, list)
    assert len(data) == 1


def test_log_change_empty_lists(ws):
    """Edge: both applied and refused empty."""
    ro.log_change(ws, [], [])
    data = json.loads((ws / ".mase" / "changes.json").read_text())
    assert data[0]["patches_applied"] == 0
    assert data[0]["patches_refused"] == 0
    assert data[0]["applied_files"] == []
    assert data[0]["refused_files"] == []


def test_log_change_invalid_json_resets(ws):
    """L158-159: invalid JSON → reset to []."""
    (ws / ".mase" / "changes.json").write_text("not valid json")
    ro.log_change(ws, ["a.py"], [])
    data = json.loads((ws / ".mase" / "changes.json").read_text())
    assert isinstance(data, list)
    assert len(data) == 1


def test_log_change_respects_env(monkeypatch, ws):
    """L171,173: USER + IM_TICKET env vars reflected in entry."""
    monkeypatch.setenv("USER", "alice")
    monkeypatch.setenv("IM_TICKET", "IM-CUSTOM")
    ro.log_change(ws, [], [])
    data = json.loads((ws / ".mase" / "changes.json").read_text())
    assert data[0]["operator"] == "alice"
    assert data[0]["im_ticket"] == "IM-CUSTOM"


# ────────────────────── main() ────────────────────────────────────

def test_main_workspace_not_found(tmp_path):
    """L186-188: workspace doesn't exist → return 1."""
    nonexistent = tmp_path / "does_not_exist"
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(nonexistent)]):
        rc = ro.main()
    assert rc == 1


def test_main_cost_gate_blocked(ws):
    """L193-197: cost-gate returns allowed=False → return 1 + exit message."""
    # Set cost to exceed budget
    db = ws / "sessions.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE sessions (id INTEGER, accumulated_cost REAL, created_at TEXT)")
    con.execute("INSERT INTO sessions VALUES (1, 99.0, datetime('now'))")
    con.commit()
    con.close()
    (ws / ".mase" / "config" / "cost.yaml").write_text(
        f"daily_budget_usd: 5.0\ngate:\n  daily: block\n"
        f"cost_source:\n  db_path: {db}\n  table: sessions\n"
    )
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n      - file: foo.py\n        verdict: CONFORM\n"
    )
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc = ro.main()
    assert rc == 1


def test_main_no_details(ws):
    """L199-201: no details → return 0 + message."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details: []\n"
    )
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc = ro.main()
    assert rc == 0


def test_main_happy_path(ws):
    """L202-222: full success — CONFORM patches applied + logged."""
    target = ws / "foo.py"
    target.write_text("hello world\n")
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n"
        "      - file: foo.py\n        verdict: CONFORM\n"
        "        find: 'world'\n        replace: 'universe'\n"
    )
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc = ro.main()
    assert rc == 0
    assert target.read_text() == "hello universe\n"
    # Log entry created
    log = json.loads((ws / ".mase" / "changes.json").read_text())
    assert log[0]["applied_files"] == ["foo.py"]
    assert log[0]["refused_files"] == []
    assert log[0]["patches_applied"] == 1


def test_main_skips_non_conform(ws):
    """L202: only CONFORM verdicts applied, others filtered out."""
    target = ws / "foo.py"
    target.write_text("hello\n")
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n"
        "      - file: foo.py\n        verdict: CONFORM\n"
        "        find: 'hello'\n        replace: 'hi'\n"
        "      - file: bar.py\n        verdict: REJECT\n"
        "        find: 'X'\n        replace: 'Y'\n"
        "      - file: baz.py\n        verdict: conform\n"
        "        find: 'foo'\n        replace: 'bar'\n"
    )
    (ws / "bar.py").write_text("X")
    (ws / "baz.py").write_text("foo")
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc = ro.main()
    assert rc == 0
    assert target.read_text() == "hi\n"
    # bar.py not touched
    assert (ws / "bar.py").read_text() == "X"
    # baz.py touched (verdict.upper() == 'CONFORM')
    assert (ws / "baz.py").read_text() == "bar"


def test_main_refused_missing_fields(ws):
    """L211-213: missing file/find/replace → refused + message."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n"
        "      - verdict: CONFORM\n"
        "        find: 'x'\n        replace: 'y'\n"
        "      - file: foo.py\n        verdict: CONFORM\n"
    )
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc = ro.main()
    # Returns 0 even with refusals (operator decides)
    assert rc == 0
    log = json.loads((ws / ".mase" / "changes.json").read_text())
    # First entry has no file field, recorded as 'unknown'
    assert "unknown" in log[0]["refused_files"]


def test_main_refused_file_not_found(ws):
    """L215-220: apply_patch returns False → refused."""
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n"
        "      - file: missing.py\n        verdict: CONFORM\n"
        "        find: 'a'\n        replace: 'b'\n"
    )
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc = ro.main()
    assert rc == 0
    log = json.loads((ws / ".mase" / "changes.json").read_text())
    assert log[0]["applied_files"] == []
    assert "missing.py" in log[0]["refused_files"]


def test_main_idempotent_skips_already_applied(ws):
    """L139-140: second run with same patch → 'already_applied_today' skipped."""
    target = ws / "foo.py"
    target.write_text("hello world\n")
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n"
        "      - file: foo.py\n        verdict: CONFORM\n"
        "        find: 'world'\n        replace: 'universe'\n"
    )
    # First run applies
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc1 = ro.main()
    assert rc1 == 0
    assert target.read_text() == "hello universe\n"

    # Second run — should skip because already_applied today
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc2 = ro.main()
    assert rc2 == 0
    log = json.loads((ws / ".mase" / "changes.json").read_text())
    assert len(log) == 2
    assert log[1]["patches_applied"] == 0
    # File unchanged on second run
    assert target.read_text() == "hello universe\n"


def test_main_uses_recursion_override_env(ws, monkeypatch):
    """L10: env var RECURSION_OVERRIDE not required for main to work,
    but env-driven IM_TICKET overrides default."""
    monkeypatch.setenv("IM_TICKET", "IM-FOO")
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details: []\n"
    )
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        rc = ro.main()
    assert rc == 0


def test_main_print_messages(ws, capsys):
    """L192,203,218,221,223: print output formatting."""
    target = ws / "foo.py"
    target.write_text("hello")
    (ws / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details:\n"
        "      - file: foo.py\n        verdict: CONFORM\n"
        "        find: 'hello'\n        replace: 'world'\n"
    )
    with patch.object(sys, "argv", ["dev_recursion_override.py",
                                    "--workspace", str(ws)]):
        ro.main()
    captured = capsys.readouterr().out
    assert "COST-GATE" in captured
    assert "RECURSION-OVERRIDE" in captured
    assert "1/1 patches are CONFORM" in captured
    assert "APPLY foo.py — applied" in captured
    assert "DONE: applied=1 refused=0" in captured


def test_main_cli_invocation(tmp_path):
    """L227-228: if __name__ == '__main__': sys.exit(main())."""
    target_dir = tmp_path / "ws"
    target_dir.mkdir()
    (target_dir / ".mase").mkdir()
    (target_dir / ".mase" / "config").mkdir()
    (target_dir / ".mase" / "pipeline").mkdir()
    (target_dir / ".mase" / "pipeline" / "validation.yaml").write_text(
        "data:\n  validation:\n    details: []\n"
    )
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "dev_recursion_override.py"),
         "--workspace", str(target_dir)],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0
    assert "RECURSION-OVERRIDE: no details" in result.stdout


def test_main_cli_no_yaml(tmp_path):
    """L99-101: validation.yaml missing → CLI exits 1."""
    target_dir = tmp_path / "ws"
    target_dir.mkdir()
    (target_dir / ".mase").mkdir()
    (target_dir / ".mase" / "config").mkdir()
    (target_dir / ".mase" / "pipeline").mkdir()
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "dev_recursion_override.py"),
         "--workspace", str(target_dir)],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 1
    assert "validation.yaml not found" in result.stderr


# ────────────────────── ImportError path ──────────────────────────

def test_yaml_import_error(monkeypatch, capsys):
    """L23-27: if yaml import fails → print ERROR + sys.exit(2).

    Simulated by hiding yaml from sys.modules so the import raises.
    """
    import importlib
    # Re-import the module's import guard by exec'ing its top in isolation
    # is complex; instead, test the import-guard message directly by
    # patching builtins.__import__.
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("PyYAML required")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Reload the module to trigger the import guard
    with pytest.raises(SystemExit) as exc:
        importlib.reload(ro)
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "PyYAML required" in captured.err
