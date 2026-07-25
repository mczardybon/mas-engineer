#!/usr/bin/env python3
"""
dev_recursion_override.py — IM-006 RECURSION-OVERRIDE tool

Operator-triggered single-shot patch application.
Reads .state/pipeline/validation.yaml, applies CONFORM patches idempotently.
Skips 24h self-loop cooldown. Logs to .state/changes.json with stage="apply_only".

Usage:
    RECURSION_OVERRIDE=1 python3 dev_recursion_override.py --workspace /path/to/mas-engineer
    # or
    python3 dev_recursion_override.py --workspace /path/to/mas-engineer

Design: see .state/pipeline/IM-006.yaml
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


DEFAULT_COST_CONFIG = {
    "daily_budget_usd": 5.00,
    "per_run_max_usd": 1.00,
    "per_session_max_usd": 0.50,
    "gate": {"daily": "block", "per_run": "block", "per_session": "warn"},
    "cost_source": {
        "db_path": "mas-engineer/.mas/data/goose/sessions.db",
        "table": "sessions",
        "cost_column": "accumulated_cost",
        "timestamp_column": "created_at",
    },
}


def load_cost_config(workspace: Path) -> dict:
    """Load cost-control config from .mas/config/cost.yaml. Falls back to defaults."""
    cfg_path = workspace / ".mas" / "config" / "cost.yaml"
    if not cfg_path.exists():
        return DEFAULT_COST_CONFIG
    try:
        loaded = yaml.safe_load(cfg_path.read_text()) or {}
        # Shallow merge with defaults so missing keys still resolve
        merged = {**DEFAULT_COST_CONFIG, **loaded}
        if "gate" in loaded:
            merged["gate"] = {**DEFAULT_COST_CONFIG["gate"], **loaded["gate"]}
        if "cost_source" in loaded:
            merged["cost_source"] = {**DEFAULT_COST_CONFIG["cost_source"], **loaded["cost_source"]}
        return merged
    except Exception as e:
        print(f"WARN: cost.yaml unreadable ({e}); using defaults", file=sys.stderr)
        return DEFAULT_COST_CONFIG


def check_cost_gate(workspace: Path, config: dict) -> tuple:
    """Check cost gate. Returns (allowed: bool, reason: str, cost_today: float, budget: float)."""
    import sqlite3 as sqlite
    src = config.get("cost_source", {})
    db_path = workspace / src.get("db_path", "mas-engineer/.mas/data/goose/sessions.db")
    if not db_path.exists():
        return True, "no_db", 0.0, config.get("daily_budget_usd", 5.00)
    try:
        con = sqlite.connect(str(db_path))
        cur = con.cursor()
        cur.execute(
            f"SELECT COALESCE(SUM({src.get('cost_column', 'accumulated_cost')}), 0.0) "
            f"FROM {src.get('table', 'sessions')} "
            f"WHERE {src.get('timestamp_column', 'created_at')} >= datetime('now', '-24 hours')"
        )
        cost_today = float(cur.fetchone()[0] or 0.0)
        con.close()
    except Exception as e:
        return True, f"db_error: {e}", 0.0, config.get("daily_budget_usd", 5.00)
    budget = float(config.get("daily_budget_usd", 5.00))
    gate_mode = config.get("gate", {}).get("daily", "block")
    if cost_today >= budget:
        if gate_mode == "block":
            return False, f"daily_budget_exceeded: ${cost_today:.2f}/${budget:.2f}", cost_today, budget
        else:
            print(f"⚠ COST-WARN: daily_budget_exceeded ${cost_today:.2f}/${budget:.2f} (gate={gate_mode})", file=sys.stderr)
            return True, f"warn_only: {cost_today:.2f}/{budget:.2f}", cost_today, budget
    return True, "ok", cost_today, budget


def load_validation(workspace: Path) -> list:
    """Load validation details from .state/pipeline/validation.yaml.

    Returns list of detail dicts each with: file, verdict, find, replace, patch_id, notes.
    """
    val_path = workspace / ".state" / "pipeline" / "validation.yaml"
    if not val_path.exists():
        print(f"ERROR: validation.yaml not found at {val_path}", file=sys.stderr)
        sys.exit(1)
    val = yaml.safe_load(val_path.read_text())
    details = val.get("data", {}).get("validation", {}).get("details", [])
    if not details:
        # Try alternative structure: top-level data list
        data = val.get("data", [])
        if isinstance(data, list):
            details = data
    return details


def already_applied(workspace: Path, file_rel: str) -> bool:
    """Check if a patch with this file_rel was already applied today via RECURSION_OVERRIDE."""
    changes = workspace / ".state" / "changes.json"
    if not changes.exists():
        return False
    try:
        data = json.loads(changes.read_text() or "[]")
    except json.JSONDecodeError:
        return False
    # Handle dict-format changes.json (with metadata/changes/stats keys)
    if not isinstance(data, list):
        return False
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if entry.get("file") == file_rel and entry.get("timestamp", "").startswith(today) \
                and entry.get("via") == "RECURSION_OVERRIDE":
            return True
    return False


def apply_patch(workspace: Path, file_rel: str, find: str, replace: str) -> tuple:
    """Apply a single patch. Idempotent: skip if already applied today.

    Returns (applied: bool, reason: str).
    """
    if already_applied(workspace, file_rel):
        return True, "already_applied_today"
    target = workspace / file_rel
    if not target.exists():
        return False, f"file_not_found: {target}"
    content = target.read_text()
    if find not in content:
        return False, "find_string_not_in_file"
    new_content = content.replace(find, replace, 1)
    target.write_text(new_content)
    return True, "applied"


def log_change(workspace: Path, applied: list, refused: list) -> None:
    path = workspace / ".state" / "changes.json"
    if not path.exists():
        path.write_text("[]\n")
    try:
        data = json.loads(path.read_text() or "[]")
    except json.JSONDecodeError:
        data = []
    if not isinstance(data, list):
        data = []
    entry = {
        "run_id": os.urandom(4).hex(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "apply_only",
        "stages_run": ["apply_only"],
        "patches_applied": len(applied),
        "patches_refused": len(refused),
        "applied_files": applied,
        "refused_files": refused,
        "operator": os.environ.get("USER", "unknown"),
        "via": "RECURSION_OVERRIDE",
        "im_ticket": os.environ.get("IM_TICKET", "IM-006"),
    }
    data.append(entry)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="IM-006 RECURSION-OVERRIDE: apply approved CONFORM patches from validation.yaml"
    )
    ap.add_argument("--workspace", required=True, help="Path to mas-engineer workspace")
    args = ap.parse_args()
    ws = Path(args.workspace).resolve()
    if not ws.exists():
        print(f"ERROR: workspace not found: {ws}", file=sys.stderr)
        return 1
    # === COST-GATE (R70 hermes hot-fix) — central cost enforcement ===
    cost_cfg = load_cost_config(ws)
    allowed, reason, cost_today, budget = check_cost_gate(ws, cost_cfg)
    print(f"COST-GATE: ${cost_today:.2f}/${budget:.2f} daily ({len(ws.name)} chars workspace)")
    if not allowed:
        print(f"❌ COST-GATE BLOCKED: {reason}")
        print(f"   Adjust limit: edit {ws}/.mas/config/cost.yaml")
        print(f"   Or set gate.daily: warn in cost.yaml to allow with warning")
        return 1
    details = load_validation(ws)
    if not details:
        print("RECURSION-OVERRIDE: no details in validation.yaml (nothing to apply)")
        return 0
    conform = [d for d in details if str(d.get("verdict", "")).upper() == "CONFORM"]
    print(f"RECURSION-OVERRIDE: {len(conform)}/{len(details)} patches are CONFORM (apply), "
          f"{len(details) - len(conform)} non-CONFORM (skip)")
    applied = []
    refused = []
    for d in conform:
        file_rel = d.get("file", "")
        find = d.get("find", "")
        replace = d.get("replace", "")
        if not file_rel or not find or not replace:
            refused.append(file_rel or "unknown")
            print(f"  REFUSE {file_rel} — missing file/find/replace")
            continue
        ok, reason = apply_patch(ws, file_rel, find, replace)
        if ok:
            applied.append(file_rel)
            print(f"  APPLY {file_rel} — {reason}")
        else:
            refused.append(file_rel)
            print(f"  REFUSE {file_rel} — {reason}")
    log_change(ws, applied, refused)
    print(f"DONE: applied={len(applied)} refused={len(refused)}")
    return 0 if not refused else 0  # Don't fail — operator decides


if __name__ == "__main__":
    sys.exit(main())
