#!/usr/bin/env python3
"""
dev_goose_db.py — 📊 Goose SQLite-Database-Analyse
===================================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Analyzed die Goose-interne SQLite-Database:
  ~/.local/share/goose/sessions/sessions.db

Hilft dem MAS-Engineer the framework-Behavior zu verstehen:
Token-Verbrauch, Kosten, Stale-Sessions, Message-Historie.

Database can gesperrt be if Goose runs.
→ Automatische copy after /tmp/ vor Analyse.

VERWENDUNG:
    python3 dev_goose_db.py --sessions         # All Sessions mit Metadaten
    python3 dev_goose_db.py --session <id>     # Session-Details + Messages
    python3 dev_goose_db.py --stale [min]      # Stale-Sessions (>30min idle)
    python3 dev_goose_db.py --costs            # Kosten-Overview
    python3 dev_goose_db.py --models           # Available Modelle
    python3 dev_goose_db.py --activity         # Activitys-Timeline
"""

import sys, os, shutil, sqlite3, json, tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

GOOSE_DB = Path.home() / ".local" / "share" / "goose" / "sessions" / "sessions.db"
TMP_DB = Path(tempfile.gettempdir()) / f"goose_sessions_{os.getpid()}.db"


# ─── HILFSFUNKTIONEN ───

def open_db(read_only: bool = True):
    """Opens a COPY of the database (bypasses SQLITE_BUSY)."""
    if TMP_DB.exists():
        TMP_DB.unlink()
    try:
        shutil.copy2(str(GOOSE_DB), str(TMP_DB))
    except (PermissionError, OSError) as e:
        print(f"❌ Database not lesbar: {e}")
        sys.exit(1)

    uri = f"file:{TMP_DB}?mode=ro" if read_only else str(TMP_DB)
    try:
        conn = sqlite3.connect(uri, uri=True if read_only else False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"❌ Database-Error: {e}")
        sys.exit(1)


def close_db(conn):
    """Closes the DB and deletes the temp copy."""
    conn.close()
    if TMP_DB.exists():
        TMP_DB.unlink()


def fmt_tokens(n: int) -> str:
    if n and n > 0:
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1000:
            return f"{n/1000:.0f}K"
        return str(n)
    return "—"


def fmt_cost(c: float) -> str:
    if c and c > 0:
        return f"${c:.2f}"
    return "—"


def fmt_dt(ts: str) -> str:
    """Formatiert Timestamp lesbar."""
    if not ts:
        return "—"
    try:
        return ts.replace("T", " ")[:19]
    except:
        return ts[:19] if len(ts) > 19 else ts


def idle_minutes(updated_at: str) -> float:
    """Berechnet wie long eine Session idle ist."""
    if not updated_at:
        return 0
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 60
    except:
        return 0


# ─── BEFEHLE ───

def cmd_sessions():
    """All Sessions mit Metadaten."""
    conn = open_db()
    rows = conn.execute("""
        SELECT id, name, description, session_typee, working_dir,
               total_tokens, accumulated_cost, created_at, updated_at,
               provider_name, goose_mode, recipe_json
        FROM sessions
        WHERE archived_at IS NULL
        ORDER BY created_at DESC
    """).fetchall()
    close_db(conn)

    if not rows:
        print("📊 No Sessions in der Database.")
        return

    print(f"\n📊 GOOSE SESSIONS ({len(rows)} active)")
    print("=" * 100)
    print(f"{'ID':<12} {'Name':<28} {'typee':<12} {'Tokens':>10} {'Kosten':>8} {'Mode':<16} {'Creates':<20}")
    print("-" * 100)

    total_tokens = 0
    total_cost = 0.0
    for r in rows:
        total_tokens += (r["total_tokens"] or 0)
        total_cost += (r["accumulated_cost"] or 0)
        print(f"{r['id'][:12]:<12} {(r['name'] or '?')[:28]:<28} "
              f"{(r['session_typee'] or '—'):<12} {fmt_tokens(r['total_tokens']):>10} "
              f"{fmt_cost(r['accumulated_cost']):>8} {(r['goose_mode'] or '—'):<16} "
              f"{fmt_dt(r['created_at']):<20}")

    print("-" * 100)
    print(f"  Total: {len(rows)} Sessions · {fmt_tokens(total_tokens)} Tokens · ${total_cost:.2f}")


def cmd_session(session_id: str):
    """Details a Session + Messages."""
    conn = open_db()

    # Session
    s = conn.execute(
        "SELECT * FROM sessions WHERE id LIKE ?", (f"%{session_id}%",)
    ).fetchone()

    if not s:
        print(f"❌ Session not found: {session_id}")
        close_db(conn)
        sys.exit(1)

    # Messages
    msgs = conn.execute(
        "SELECT role, tokens, content_json, created_timestamp FROM messages WHERE session_id = ? ORDER BY created_timestamp",
        (s["id"],)
    ).fetchall()
    close_db(conn)

    print(f"\n📊 SESSION: {s['name'] or '?'} ({s['id'][:12]})")
    print("=" * 80)
    print(f"  Mode:      {s['goose_mode'] or '—'}")
    print(f"  typee:       {s['session_typee'] or '—'}")
    print(f"  Provider:  {s['provider_name'] or '—'}")
    print(f"  Tokens:    {fmt_tokens(s['total_tokens'])} (in: {fmt_tokens(s['input_tokens'])}, out: {fmt_tokens(s['output_tokens'])})")
    print(f"  Kosten:    {fmt_cost(s['accumulated_cost'] or 0)}")
    print(f"  Creates:  {fmt_dt(s['created_at'])}")
    print(f"  Updated:   {fmt_dt(s['updated_at'])}")
    idle = idle_minutes(s["updated_at"])
    if idle > 0:
        print(f"  Idle:      {idle:.0f}min")
    print(f"  Messages:  {len(msgs)}")
    if s["working_dir"]:
        print(f"  directory:    {s['working_dir']}")
    if s["description"]:
        print(f"  Info:      {s['description'][:80]}")

    if msgs:
        print(f"\n  MESSAGES ({len(msgs)}):")
        for i, m in enumerate(msgs[:20]):
            role_icon = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(m["role"], "❓")
            try:
                content = json.loads(m["content_json"] or "{}")
                if isinstance(content, list):
                    preview = str(content)[:100]
                elif isinstance(content, dict):
                    preview = content.get("text", str(content))[:100]
                else:
                    preview = str(content)[:100]
            except:
                preview = (m["content_json"] or "")[:100]
            print(f"  {i+1:>2}. {role_icon} {m['role']:<10} {fmt_tokens(m['tokens']):>8} | {preview}")


def cmd_stale(minutes: int = 30):
    """Sessions idle for more than N minutes."""
    conn = open_db()
    rows = conn.execute(
        "SELECT id, name, total_tokens, accumulated_cost, updated_at, session_typee FROM sessions WHERE archived_at IS NULL"
    ).fetchall()
    close_db(conn)

    stale = []
    for r in rows:
        im = idle_minutes(r["updated_at"])
        if im >= minutes:
            stale.append((im, r))

    if not stale:
        print(f"✅ No Stale-Sessions (>{minutes}min idle)")
        return

    print(f"\n⚠️  STALE SESSIONS (>{minutes}min idle)")
    print("=" * 80)
    for im, r in sorted(stale, reverse=True):
        print(f"  {r['name'] or '?'[:30]:<30} {r['id'][:12]:<12} "
              f"idle: {im:.0f}min · {fmt_tokens(r['total_tokens'])} · {fmt_cost(r['accumulated_cost'])}")
    print(f"\n  → {len(stale)} Stale-Sessions found")


def cmd_costs():
    """Kosten-Overview."""
    conn = open_db()
    rows = conn.execute(
        "SELECT name, accumulated_cost, total_tokens, goose_mode, created_at FROM sessions WHERE accumulated_cost > 0 ORDER BY accumulated_cost DESC"
    ).fetchall()
    close_db(conn)

    if not rows:
        print("📊 No Kosten-Data.")
        return

    total = sum(r["accumulated_cost"] or 0 for r in rows)
    print(f"\n💰 KOSTEN-OVERVIEW (Total: ${total:.2f})")
    print("=" * 60)
    for r in rows:
        pct = (r["accumulated_cost"] / total * 100) if total > 0 else 0
        print(f"  {r['name'] or '?'[:30]:<30} {fmt_cost(r['accumulated_cost']):>8} "
              f"({pct:4.1f}%) · {fmt_tokens(r['total_tokens'])}")


def cmd_models():
    """Available Modelle."""
    conn = open_db()
    rows = conn.execute(
        "SELECT model_id, name, family, context_limit, reasoning, recommended FROM provider_inventory_models ORDER BY ordinal"
    ).fetchall()
    close_db(conn)

    if not rows:
        print("📊 No Model-Data.")
        return

    print(f"\n🧠 AVAILABLE MODELLE ({len(rows)})")
    print("=" * 80)
    for r in rows:
        flags = []
        if r["reasoning"]:
            flags.append("🧠")
        if r["recommended"]:
            flags.append("⭐")
        print(f"  {r['model_id']:<40} {r['name'] or '?'[:20]:<20} "
              f"ctx: {fmt_tokens(r['context_limit']):>6} {' '.join(flags)}")
    print(f"\n  → Family: {rows[0]['family'] if rows else '—'}")


def cmd_activity():
    """Activitys-Timeline."""
    conn = open_db()
    rows = conn.execute(
        "SELECT name, created_at, updated_at, total_tokens, session_typee FROM sessions WHERE archived_at IS NULL ORDER BY created_at"
    ).fetchall()
    close_db(conn)

    if not rows:
        print("📊 No Activitys-Data.")
        return

    print(f"\n📈 ACTIVITY TIMELINE ({len(rows)} Sessions)")
    print("=" * 80)
    for r in rows:
        created = fmt_dt(r["created_at"])
        updated = fmt_dt(r["updated_at"])
        name = (r["name"] or "?")[:25]
        print(f"  {created} → {updated} | {name:<25} | {fmt_tokens(r['total_tokens']):>8} | {r['session_typee'] or '—'}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__.strip())
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "--sessions":
        cmd_sessions()
    elif cmd == "--session":
        sid = sys.argv[2] if len(sys.argv) > 2 else ""
        if not sid:
            print("❌ Session-ID required")
            sys.exit(1)
        cmd_session(sid)
    elif cmd == "--stale":
        minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        cmd_stale(minutes)
    elif cmd == "--costs":
        cmd_costs()
    elif cmd == "--models":
        cmd_models()
    elif cmd == "--activity":
        cmd_activity()
    else:
        print(f"❌ Unknown: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
