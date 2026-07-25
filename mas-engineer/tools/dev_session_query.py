#!/usr/bin/env python3
"""
dev_session_query.py — Session-DB Reader (v1.0.0)

R89 Phase 7: Script-replacement for sub_mas-im-session-reader.yaml.
Reads Goose session database with 3-level project filter.

Commands:
  ANALYZE <workspace> [N] [--include-messages]
  FILTER_LEVEL <workspace>           — Just check which filter level matches + count
  SHOW_DB_INFO                      — Info about session-DB (path, size, mtime)
  STALE [days=30]                   — Find stale sessions

3-Level Project Filter:
  Level 1: GOOSE_SESSION_TAG from {workspace}/.goosehints (exact match in name)
  Level 2: working_dir LIKE '{workspace}%'
  Level 3: Fallback — last N non-MAS sessions (recipe_json NOT LIKE '%DEV-MAS-ENGINEER%')

Edge cases (per Coronashield spec):
  - DB not found       → empty result, status='no_db' (no abort)
  - DB locked          → try copy, fall back to raw
  - sqlite3 missing    → status='no_sqlite' (no abort)
  - 0 sessions in all  → status='no_sessions' (no abort)
  - .goosehints missing → skip Level 1
  - include_messages + no messages-table → skip chat extraction
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_DB = os.path.expanduser("~/.local/share/goose/sessions/sessions.db")


def get_db_path() -> str:
    return os.environ.get("GOOSE_DB", DEFAULT_DB)


def get_copy_path() -> str:
    """Get a writable copy of the DB (Goose can lock).

    Always creates a fresh copy via timestamped filename to avoid stale data.
    """
    db = get_db_path()
    if not os.path.isfile(db):
        return None

    # Always fresh — timestamped path
    import time
    copy = f"/tmp/im_session_copy_{int(time.time())}.db"

    # Try sqlite3 .clone first (atomic copy under lock)
    try:
        r = subprocess.run(
            ["sqlite3", db, f".clone {copy}"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and os.path.isfile(copy):
            # Cleanup old copies
            try:
                import glob
                for old in glob.glob("/tmp/im_session_copy_*.db"):
                    if old != copy and os.path.isfile(old):
                        os.unlink(old)
            except Exception:
                pass
            return copy
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: plain cp
    try:
        shutil.copy2(db, copy)
        return copy
    except Exception:
        return None


def read_goosehints_tag(workspace: str) -> str:
    """Read GOOSE_SESSION_TAG from {workspace}/.goosehints (Level 1)."""
    hints = os.path.join(workspace, ".goosehints")
    if not os.path.isfile(hints):
        return ""
    try:
        with open(hints) as f:
            for line in f:
                m = re.match(r"^\s*GOOSE_SESSION_TAG\s*=\s*(\S+)", line)
                if m:
                    return m.group(1).strip().strip("'\"")
    except Exception:
        pass
    return ""


def query_sessions(db: str, where: str, limit: int) -> list[dict[str, Any]]:
    """Run SELECT against sessions table with given WHERE clause."""
    sql = f"""
        SELECT id, name, session_type, total_tokens, accumulated_cost,
               created_at, working_dir, recipe_json
        FROM sessions
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT {int(limit)}
    """
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return [{"_error": str(e)}]


def has_messages_table(db: str) -> bool:
    """Check if 'messages' table exists (only true in newer goose versions)."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
        r = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        ).fetchone()
        conn.close()
        return r is not None
    except Exception:
        return False


def extract_messages_patterns(db: str, session_ids: list[str]) -> dict[str, Any]:
    """Extract chat patterns from messages table (corrections, confusions, etc)."""
    if not session_ids or not has_messages_table(db):
        return {"available": False, "reason": "no messages table"}

    placeholders = ",".join("?" * len(session_ids))
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT session_id, role, content, created_at
            FROM messages
            WHERE session_id IN ({placeholders})
            ORDER BY session_id, created_at ASC
            """,
            session_ids,
        ).fetchall()
        conn.close()
    except Exception as e:
        return {"available": False, "error": str(e)}

    patterns = {
        "available": True,
        "corrections": [],
        "confusions": [],
        "praises": [],
        "abandoned_sessions": [],
        "feature_requests": [],
    }
    re_correction = re.compile(r"(?i)(no|false|correct|not so|not right)")
    re_confusion = re.compile(r"(?i)(what\?|like\?|why\?|explain|don't understand)")
    re_praise = re.compile(r"(?i)(good|perfect|thanks|exactly|great|works)")
    re_feature = re.compile(r"(?i)(can you|add|do this|would need)")

    # Group by session
    by_session: dict[str, list] = {}
    for r in rows:
        by_session.setdefault(r["session_id"], []).append(dict(r))

    for sid, msgs in by_session.items():
        corr = [m for m in msgs if m["role"] == "user"
                and re_correction.search(m["content"] or "")]
        conf = [m for m in msgs if m["role"] == "user"
                and re_confusion.search(m["content"] or "")]
        pra = [m for m in msgs if m["role"] == "user"
               and re_praise.search(m["content"] or "")]
        feat = [m for m in msgs if m["role"] == "user"
                and re_feature.search(m["content"] or "")]

        if corr:
            patterns["corrections"].append({
                "session_id": sid,
                "count": len(corr),
                "examples": [(m["content"] or "")[:150] for m in corr[:3]],
            })
        if conf:
            patterns["confusions"].append({
                "session_id": sid,
                "count": len(conf),
                "questions": [(m["content"] or "")[:150] for m in conf[:3]],
            })
        if pra:
            patterns["praises"].append({"session_id": sid, "count": len(pra)})
        if feat:
            patterns["feature_requests"].append({
                "session_id": sid,
                "requests": [(m["content"] or "")[:150] for m in feat[:3]],
            })

        # Abandoned: <5 msgs + last is from user
        if len(msgs) < 5 and msgs and msgs[-1]["role"] == "user":
            patterns["abandoned_sessions"].append({
                "session_id": sid,
                "messages_count": len(msgs),
                "last_message_preview": (msgs[-1]["content"] or "")[:150],
            })

    return patterns


def aggregate_metrics(sessions: list[dict]) -> dict[str, Any]:
    """Total tokens, cost, top-cost session.

    Accepts both raw ('total_tokens', 'accumulated_cost') and cleaned
    ('tokens', 'cost') session shapes.
    """
    if not sessions:
        return {"sessions": 0, "tokens": 0, "cost": 0.0, "top_cost_session": None}

    def get(s, k1, k2):
        v = s.get(k1)
        if v is None:
            v = s.get(k2)
        return v

    total_tokens = sum(get(s, "tokens", "total_tokens") or 0 for s in sessions)
    total_cost = sum(get(s, "cost", "accumulated_cost") or 0.0 for s in sessions)

    def cost_key(s):
        v = get(s, "cost", "accumulated_cost")
        return v if v is not None else 0.0

    top = max(sessions, key=cost_key)
    top_cost = cost_key(top)

    return {
        "sessions": len(sessions),
        "tokens": total_tokens,
        "cost": round(total_cost, 6),
        "top_cost_session": {
            "id": top.get("id"),
            "name": top.get("name"),
            "cost": top_cost,
        } if top_cost else None,
    }


def find_stale_sessions(db: str, days: int = 30) -> list[dict]:
    """Find sessions older than N days (via created_at)."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT id, name, session_type, total_tokens, accumulated_cost, created_at
            FROM sessions
            WHERE julianday('now') - julianday(created_at) > {int(days)}
            ORDER BY created_at DESC
            LIMIT 50
            """
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return [{"_error": str(e)}]


def analyze(workspace: str, limit: int = 20, include_messages: bool = False) -> dict[str, Any]:
    """Main ANALYZE command. 3-level filter + optional messages + aggregates."""
    result: dict[str, Any] = {
        "workspace": workspace,
        "filter_level": None,
        "tag": None,
        "sessions": [],
        "totals": {"sessions": 0, "tokens": 0, "cost": 0.0},
        "stale": [],
        "messages": {"available": False},
    }

    # Check DB exists
    db = get_db_path()
    if not os.path.isfile(db):
        result["status"] = "no_db"
        result["warning"] = f"No Session-DB found at {db}"
        return result

    # Get writable copy
    copy = get_copy_path()
    if not copy:
        result["status"] = "db_locked"
        result["warning"] = "DB copy failed — session data not available"
        return result

    # === Level 1: TAG ===
    tag = read_goosehints_tag(workspace)
    sessions: list[dict] = []
    if tag:
        sessions = query_sessions(
            copy,
            f"name LIKE '%' || ? || '%'",
            limit,
        )
        # Filter with param (sqlite3 doesn't always bind correctly with WHERE-clause concat)
        # Re-run with bound param if first attempt returned rows check failed
        try:
            conn = sqlite3.connect(f"file:{copy}?mode=ro", uri=True, timeout=10)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, name, session_type, total_tokens, accumulated_cost,
                          created_at, working_dir, recipe_json
                   FROM sessions
                   WHERE name LIKE '%' || ? || '%'
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (tag, limit),
            ).fetchall()
            conn.close()
            sessions = [dict(r) for r in rows]
        except Exception as e:
            sessions = []

        if sessions:
            result["filter_level"] = "tag"
            result["tag"] = tag

    # === Level 2: working_dir ===
    if not sessions:
        try:
            conn = sqlite3.connect(f"file:{copy}?mode=ro", uri=True, timeout=10)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, name, session_type, total_tokens, accumulated_cost,
                          created_at, working_dir, recipe_json
                   FROM sessions
                   WHERE working_dir LIKE ? || '%'
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (workspace, limit),
            ).fetchall()
            conn.close()
            sessions = [dict(r) for r in rows]
            if sessions:
                result["filter_level"] = "working_dir"
        except Exception as e:
            sessions = []

    # === Level 3: Fallback (last N non-MAS) ===
    if not sessions:
        try:
            conn = sqlite3.connect(f"file:{copy}?mode=ro", uri=True, timeout=10)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, name, session_type, total_tokens, accumulated_cost,
                          created_at, working_dir, recipe_json
                   FROM sessions
                   WHERE recipe_json IS NULL
                      OR recipe_json = ''
                      OR recipe_json NOT LIKE '%DEV-MAS-ENGINEER%'
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            conn.close()
            sessions = [dict(r) for r in rows]
            if sessions:
                result["filter_level"] = "fallback"
        except Exception as e:
            sessions = []

    if not sessions:
        result["status"] = "no_sessions"
        result["warning"] = "No Sessions for this project"
        return result

    # Strip recipe_json (large, internal)
    clean_sessions = []
    for s in sessions:
        clean_sessions.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "type": s.get("session_type"),
            "tokens": s.get("total_tokens"),
            "cost": s.get("accumulated_cost"),
            "created": s.get("created_at"),
            "working_dir": s.get("working_dir"),
        })
    result["sessions"] = clean_sessions
    result["totals"] = aggregate_metrics(clean_sessions)

    # Stale (always)
    result["stale"] = find_stale_sessions(copy, days=30)

    # Optional messages
    if include_messages:
        ids = [s["id"] for s in clean_sessions if s.get("id")]
        result["messages"] = extract_messages_patterns(copy, ids)

    result["status"] = "success"
    return result


def show_db_info() -> dict[str, Any]:
    """Info about session-DB."""
    db = get_db_path()
    info: dict[str, Any] = {
        "path": db,
        "exists": False,
        "size_bytes": 0,
        "mtime": None,
        "session_count": 0,
        "has_messages_table": False,
    }
    if not os.path.isfile(db):
        return info
    info["exists"] = True
    info["size_bytes"] = os.path.getsize(db)
    info["mtime"] = os.path.getmtime(db)

    copy = get_copy_path()
    if copy:
        info["has_messages_table"] = has_messages_table(copy)
        try:
            conn = sqlite3.connect(f"file:{copy}?mode=ro", uri=True, timeout=10)
            r = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
            conn.close()
            info["session_count"] = r[0] if r else 0
        except Exception:
            pass
    return info


def find_stale(workspace: str, days: int = 30) -> list[dict]:
    """Standalone STALE command."""
    db = get_db_path()
    if not os.path.isfile(db):
        return []
    copy = get_copy_path()
    if not copy:
        return []
    return find_stale_sessions(copy, days)


def print_usage() -> None:
    print(__doc__)


def main() -> int:
    if len(sys.argv) < 2:
        print_usage()
        return 2

    cmd = sys.argv[1].upper()

    if cmd == "ANALYZE":
        if len(sys.argv) < 3:
            print("Usage: ANALYZE <workspace> [N=20] [--include-messages]",
                  file=sys.stderr)
            return 2
        workspace = sys.argv[2]
        limit = 20
        include_messages = False
        for arg in sys.argv[3:]:
            if arg == "--include-messages":
                include_messages = True
            elif arg.isdigit():
                limit = int(arg)
        result = analyze(workspace, limit, include_messages)
    elif cmd == "FILTER_LEVEL":
        if len(sys.argv) < 3:
            print("Usage: FILTER_LEVEL <workspace>", file=sys.stderr)
            return 2
        workspace = sys.argv[2]
        result = {"workspace": workspace}
        tag = read_goosehints_tag(workspace)
        if tag:
            result["level1_tag"] = tag
            result["filter_level"] = "tag"
        else:
            result["level1_tag"] = None
            result["filter_level"] = "fallback_needed"
    elif cmd == "SHOW_DB_INFO":
        result = show_db_info()
    elif cmd == "STALE":
        days = 30
        workspace = sys.argv[2] if len(sys.argv) > 2 else "."
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            days = int(sys.argv[2])
            workspace = sys.argv[3] if len(sys.argv) > 3 else "."
        result = {"workspace": workspace, "days": days,
                  "stale": find_stale(workspace, days)}
    elif cmd in ("-h", "--help", "HELP"):
        print_usage()
        return 0
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print_usage()
        return 2

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
