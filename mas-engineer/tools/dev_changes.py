#!/usr/bin/env python3
"""
dev_changes.py — 📝 Das Memory des dev-mas-engineer
========================================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Dokumentiert JEDE Change am agent/ framework.
Enables rollback. Zeigt Historie.

VERWENDUNG:
    python3 dev_changes.py --status                  # Currentn status show
    python3 dev_changes.py --history                 # All Changes show
    python3 dev_changes.py --add <json>              # Change add
    python3 dev_changes.py --get <id>                # Eine determinese Change
    python3 dev_changes.py --rollback <id>           # rollback-Command generate
    python3 dev_changes.py --help                    # This help anshow

NO framework dependency. Pure standard library.
"""

import json, sys, os
from pathlib import Path
from datetime import datetime, timezone

def resolve_state_dir():
    """Ermittelt STATE_DIR — mit --workspace Support."""
    for i, arg in enumerate(sys.argv):
        if arg == "--workspace" and i + 1 < len(sys.argv):
            ws = Path(sys.argv[i + 1]).resolve()
            return ws / ".state"
    return (Path(__file__).parent.parent / ".state").resolve()

STATE_DIR = resolve_state_dir()
CHANGES_FILE = STATE_DIR / "changes.json"


def init_state():
    """Create empty changes.json falls not present."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not CHANGES_FILE.exists():
        default = {
            "metadata": {
                "agent": "dev-mas-engineer",
                "version": "1.0.0",
                "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_changes": 0
            },
            "changes": [],
            "stats": {
                "harden": 0, "evolve": 0, "patch": 0, "other": 0,
                "rolled_back": 0, "last_24h": 0
            }
        }
        with open(CHANGES_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default
    return load()


def load():
    """Load changes.json."""
    if not CHANGES_FILE.exists():
        return init_state()
    with open(CHANGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data):
    """memorye changes.json."""
    data["metadata"]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["metadata"]["total_changes"] = len(data["changes"])
    with open(CHANGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_change(change_data):
    """Add a change."""
    data = load()
    
    # Find metadata block (first item with "changes" key)
    if isinstance(data, list):
        meta = next((d for d in data if "changes" in d), {"changes": [], "stats": {}})
    else:
        meta = data
    
    # ID generate
    next_id = max((c.get("id", 0) for c in meta["changes"]), default=0) + 1
    change_id = f"ch_{next_id:03d}"
    
    # Default-Felder
    entry = {
        "id": change_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user": change_data.get("user", "Marius"),
        "user_approved": change_data.get("user_approved", True),
        "user_comment": change_data.get("user_comment", ""),
        "file": change_data.get("file", ""),
        "type": change_data.get("type", "edit"),
        "von": change_data.get("von", ""),
        "nach": change_data.get("nach", ""),
        "grund": change_data.get("grund", ""),
        "art": change_data.get("art", "other"),
        "risk": change_data.get("risk", "niedrig"),
        "validated_before": change_data.get("validated_before", True),
        "validated_after": change_data.get("validated_after", True),
        "tests_passed": change_data.get("tests_passed", None),
        "backup": change_data.get("backup", ""),
        "rolled_back": False,
        "rolled_back_at": None,
        "rolled_back_reason": None
    }
    
    data["changes"].append(entry)
    
    # Stats update
    art = change_data.get("art", "other")
    if art in data["stats"]:
        data["stats"][art] += 1
    else:
        data["stats"]["other"] += 1
    
    # last_24h: all Changes der letzten 24h count
    now = datetime.now(timezone.utc)
    yesterday = now.timestamp() - 86400
    data["stats"]["last_24h"] = sum(
        1 for c in data["changes"]
        if datetime.fromisoformat(c["timestamp"].replace("Z", "+00:00")).timestamp() > yesterday
    )
    
    save(data)
    return entry


def show_status():
    """Show status an."""
    data = load()
    output = []
    output.append("📝 CHANGE status")
    output.append("━" * 40)
    output.append(f"  Total: {data['metadata']['total_changes']}")
    output.append(f"  Last 24h: {data['stats']['last_24h']}")
    output.append(f"  Last Update: {data['metadata']['last_updated']}")
    output.append("")
    output.append("  After Art:")
    for art, count in data['stats'].items():
        if art != "last_24h":
            output.append(f"    {art}: {count}")
    output.append("")
    
    if data['changes']:
        last = data['changes'][-1]
        output.append("  Last Change:")
        output.append(f"    #{last['id']}: {last['file']}")
        output.append(f"    {last['von']} → {last['nach']}")
        output.append(f"    User: {last['user']} ({'✅' if last['user_approved'] else '❌'})")
    else:
        output.append("  No changes yet.")
    
    return "\n".join(output)


def show_history(limit=10):
    """Show die letzten n Changes."""
    data = load()
    changes = data["changes"][-limit:]
    changes.reverse()
    
    output = []
    output.append("📝 LAST CHANGES")
    output.append("━" * 40)
    
    if not changes:
        output.append("  No changes yet.")
        return "\n".join(output)
    
    for c in changes:
        status = "✅" if not c["rolled_back"] else "🔙"
        ts = c["timestamp"][:19].replace("T", " ")
        output.append(f"  #{c['id']} {status} {ts}")
        output.append(f"      {c['file']}")
        output.append(f"      {c['von']} → {c['nach']}")
        output.append(f"      Reason: {c['grund']}")
        if c['user_comment']:
            output.append(f"      User: {c['user_comment']}")
        output.append("")
    
    return "\n".join(output)


def show_change(change_id):
    """Show Details a determinesen Change."""
    data = load()
    for c in data["changes"]:
        if c["id"] == change_id:
            output = []
            output.append(f"📝 CHANGE #{change_id}")
            output.append("━" * 40)
            for key, value in c.items():
                output.append(f"  {key}: {value}")
            return "\n".join(output)
    return f"❌ Change #{change_id} not found."


def generate_rollback(change_id):
    """Generiere rollback-Command for eine Change."""
    data = load()
    for c in data["changes"]:
        if c["id"] == change_id:
            if not c["backup"]:
                return f"❌ No Backup for #{change_id} available."
            output = []
            output.append(f"🔄 ROLLBACK for #{change_id}")
            output.append("━" * 40)
            output.append(f"  file: {c['file']}")
            output.append(f"  Change: {c['von']} → {c['nach']}")
            output.append(f"  Backup: {c['backup']}")
            output.append("")
            output.append("  Command:")
            output.append(f"    cp {c['backup']}/{Path(c['file']).name} ../agent/{c['file']}")
            output.append("")
            output.append("  After Execution: dev_changes.py markieren")
            return "\n".join(output)
    return f"❌ Change #{change_id} not found."


def mark_rolled_back(change_id, reason=""):
    """Markiere eine Change als undo gemacht."""
    data = load()
    for c in data["changes"]:
        if c["id"] == change_id:
            c["rolled_back"] = True
            c["rolled_back_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            c["rolled_back_reason"] = reason
            data["stats"]["rolled_back"] += 1
            save(data)
            return f"✅ #{change_id} als rolled_back markiert."
    return f"❌ Change #{change_id} not found."


def add_cli():
    """CLI for --add: Liest JSON von stdin oder als argument."""
    if len(sys.argv) > 2 and sys.argv[2]:
        try:
            data = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            data = {"file": sys.argv[2], "von": "", "nach": "", "grund": "CLI-call", "user": "Marius"}
    else:
        data = json.loads(sys.stdin.read())
    
    entry = add_change(data)
    return f"✅ #{entry['id']} documented: {entry['file']}"


def main():
    if len(sys.argv) < 2:
        print("dev_changes.py — Change management")
        print("")
        print("Usage:")
        print("  --status              status anshow")
        print("  --history [n]         Last n Changes (Default: 10)")
        print("  --add <json>          Change entryen (JSON mit file, von, nach, grund)")
        print("  --get <id>            Details a Change")
        print("  --rollback <id>       rollback-Command generate")
        print("  --mark-rolled <id>    Als rolled_back markieren")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "--status":
        print(show_status())
    elif cmd == "--history":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(show_history(limit))
    elif cmd == "--add":
        print(add_cli())
    elif cmd == "--get":
        print(show_change(sys.argv[2]))
    elif cmd == "--rollback":
        print(generate_rollback(sys.argv[2]))
    elif cmd == "--mark-rolled":
        reason = sys.argv[3] if len(sys.argv) > 3 else ""
        print(mark_rolled_back(sys.argv[2], reason))
    else:
        print(f"❌ Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
