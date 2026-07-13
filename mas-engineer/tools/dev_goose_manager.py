#!/usr/bin/env python3
"""
dev_goose_manager.py — 🖥️ Goose-Management
==========================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Manages Goose components that do NOT belong to the framework:
Skills, Sessions, History, Logs, Scheduler, MCP-Apps.

NOE framework-files (recipes/, docs/, config.yaml) will angetastet.

VERWENDUNG:
    python3 dev_goose_manager.py --status
    python3 dev_goose_manager.py --clear-skills [--force]
    python3 dev_goose_manager.py --clear-sessions [--force]
    python3 dev_goose_manager.py --clear-history [--force]
    python3 dev_goose_manager.py --clear-logs [--force]
    python3 dev_goose_manager.py --clear-schedule [--force]
    python3 dev_goose_manager.py --clear-all [--force]
"""

import sys, shutil, re, json
from pathlib import Path

GOOSE_CONFIG_DIR = Path.home() / ".config" / "goose"
GOOSE_CONFIG = GOOSE_CONFIG_DIR / "config.yaml"
GOOSE_SHARE = Path.home() / ".local" / "share" / "goose"
GOOSE_STATE = Path.home() / ".local" / "state" / "goose"

SKILLS_DIR      = GOOSE_CONFIG_DIR / "skills"
MCP_APPS_DIR    = GOOSE_CONFIG_DIR / "mcp-apps-cache"
MCP_HERMIT_DIR  = GOOSE_CONFIG_DIR / "mcp-hermit"
CUSTOM_PROV_DIR = GOOSE_CONFIG_DIR / "custom_providers"
SESSIONS_DIR    = GOOSE_SHARE / "sessions"
SCHEDULE_FILE   = GOOSE_SHARE / "schedule.json"
SCHEDULED_DIR   = GOOSE_SHARE / "scheduled_recipes"
PROJECTS_FILE   = GOOSE_SHARE / "projects.json"
HISTORY_FILE    = GOOSE_STATE / "history.txt"
LOGS_DIR        = GOOSE_STATE / "logs"
MODELS_DIR      = GOOSE_SHARE / "models"


# ─── HILFSFUNKTIONEN ───

def fmt_size(path: Path) -> str:
    """Lesbare size (B/KB/MB/GB)."""
    if not path.exists():
        return "—"
    try:
        if path.is_file():
            size = path.stat().st_size
        elif path.is_dir():
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        else:
            return "—"
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"
    except:
        return "?"


def count_files(path: Path, pattern: str = "*") -> int:
    """Counts files (0 if path does not exist)."""
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    return len(list(path.glob(pattern)))


def ask(msg: str, force: bool) -> bool:
    """Asks um Confirmation. Bei --force always True."""
    if force:
        return True
    answer = input(f"{msg} (j/N): ").strip().lower()
    return answer in ("j", "yes", "y", "yes")


def safe_delete(path: Path, label: str, force: bool) -> int:
    """Sicheres Delete mit sizes-Anshow + Confirmation."""
    if not path.exists():
        print(f"  ⏭️  {label}: not present")
        return 0

    size = fmt_size(path)
    cnt = count_files(path)

    if not ask(f"  {label} ({cnt} files, {size}) delete?", force):
        print(f"  ⏭️  {label}: skipped")
        return 0

    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  ✅ {label}: deleted ({size})")
        return cnt
    except Exception as e:
        print(f"  ❌ {label}: Error — {e}")
        return 0


# ─── BEFEHLE ───

def cmd_status():
    """Complete Goose-status."""
    print("\n📊 GOOSE status")
    print("=" * 60)

    # 1. Provider
    provider, model = "?", "?"
    if GOOSE_CONFIG.exists():
        try:
            text = GOOSE_CONFIG.read_text()
            m = re.search(r"^active_provider:\s*(.+)", text, re.MULTILINE)
            provider = m.group(1).strip() if m else "?"
            m = re.search(r"^GOOSE_MODEL:\s*(.+)", text, re.MULTILINE)
            model = m.group(1).strip() if m else "?"
        except:
            pass
    print(f"  🔌 Provider:  {provider} / {model}")

    # 2. Recipes
    recipes_dir = GOOSE_CONFIG_DIR / "recipes"
    vis = count_files(recipes_dir, "*.yaml")
    fw_dir = recipes_dir / "_framework"
    fw = count_files(fw_dir, "*.yaml")
    print(f"  🍳 Recipes:   {vis} sichtbar + {fw} in _framework/ = {vis + fw} total ({fmt_size(recipes_dir)})")

    # 3. Docs
    docs_dir = GOOSE_CONFIG_DIR / "docs"
    print(f"  📚 Docs:      {count_files(docs_dir)} files ({fmt_size(docs_dir)})")

    # 4. Skills
    print(f"  🎯 Skills:    {count_files(SKILLS_DIR)} files ({fmt_size(SKILLS_DIR)})")

    # 5. Extensions
    exts = []
    if GOOSE_CONFIG.exists():
        try:
            text = GOOSE_CONFIG.read_text()
            in_ext = False
            for line in text.split("\n"):
                if line.startswith("extensions:"):
                    in_ext = True
                    continue
                if in_ext and line.strip() and not line.startswith(" "):
                    break
                if in_ext and "enabled:" in line:
                    name = line.strip().split(":")[0].strip()
                    status = "✅" if "true" in line.lower() else "❌"
                    exts.append(f"{name}({status})")
        except:
            pass
    print(f"  🔌 Extensions: {', '.join(exts) if exts else '—'}")

    # 6-7. MCP
    print(f"  📱 MCP Apps:   {count_files(MCP_APPS_DIR)} gecached ({fmt_size(MCP_APPS_DIR)})")
    print(f"  📱 MCP Hermit: {fmt_size(MCP_HERMIT_DIR)}")

    # 8. Custom Provider
    print(f"  🔧 Custom Prov: {count_files(CUSTOM_PROV_DIR)} ({fmt_size(CUSTOM_PROV_DIR)})")

    # 9. Scheduler
    sch_jobs = 0
    if SCHEDULE_FILE.exists():
        try:
            data = json.loads(SCHEDULE_FILE.read_text())
            sch_jobs = len(data.get("jobs", [])) if isinstance(data, dict) else 0
        except:
            pass
    print(f"  📅 Scheduler:  {sch_jobs} Job(s), {count_files(SCHEDULED_DIR)} scheduled ({fmt_size(SCHEDULE_FILE)})")

    # 10. History
    print(f"  📋 History:    {fmt_size(HISTORY_FILE)}")
    if HISTORY_FILE.exists():
        try:
            lines = len(HISTORY_FILE.read_text().split("\n"))
            print(f"                → {lines} lines")
        except:
            pass

    # 11-13
    print(f"  💬 Sessions:   {count_files(SESSIONS_DIR)} ({fmt_size(SESSIONS_DIR)})")
    print(f"  📜 LLM-Logs:   {count_files(LOGS_DIR)} ({fmt_size(LOGS_DIR)})")
    print(f"  📁 Projects:   {fmt_size(PROJECTS_FILE)}")
    print(f"  🧠 Model-cache:{fmt_size(MODELS_DIR)}")

    # 14. TLS
    tls_dir = GOOSE_CONFIG_DIR / "tls"
    print(f"  🔒 TLS:       {count_files(tls_dir)} files ({fmt_size(tls_dir)})")

    # 15. Apps
    apps_dir = GOOSE_SHARE / "apps"
    apps_cnt = count_files(apps_dir)
    if apps_cnt > 0:
        apps_list = [f.name for f in apps_dir.iterdir() if f.is_file()]
        print(f"  📱 Apps:      {apps_cnt} ({', '.join(apps_list[:3])})")
    else:
        print(f"  📱 Apps:      0")

    # 16. Goose-Hints
    hints_file = GOOSE_CONFIG_DIR / ".goosehints"
    print(f"  💡 .goosehints: {fmt_size(hints_file)}", end="")
    if hints_file.exists():
        lines = len(hints_file.read_text().split("\n"))
        print(f" ({lines} lines)")
    else:
        print(" (not present)")

    # 17. Tool-Permissions
    perm_file = GOOSE_CONFIG_DIR / "permissions" / "tool_permissions.json"
    print(f"  🔐 Permissions: {fmt_size(perm_file)}", end="")
    if perm_file.exists():
        try:
            data = json.loads(perm_file.read_text())
            entries = len(data) if isinstance(data, (dict, list)) else 0
            print(f" ({entries} entries)")
        except:
            print(f" (JSON-Error)")
    else:
        print(" (not present)")

    # 18. Config-Backups
    bak_count = len(list(GOOSE_CONFIG_DIR.glob("config.yaml.bak-*")))
    print(f"  💾 Backups:   {bak_count} Config-Backups")

    print("=" * 60)


def cmd_clear(what: str, force: bool):
    """Runs eine Clear-Operation aus."""
    targets = {
        "skills":   (SKILLS_DIR,   "Skills"),
        "sessions": (SESSIONS_DIR, "Chat-Sessions"),
        "history":  (HISTORY_FILE, "Chat-History"),
        "logs":     (LOGS_DIR,     "LLM-Logs"),
        "schedule": (SCHEDULE_FILE,"Scheduler"),
    }

    if what == "all":
        print(f"\n🧹 GOOSE CLEANUP (framework remains untouched)")
        print("=" * 60)
        total = 0
        for key, (path, label) in targets.items():
            total += safe_delete(path, label, force)
        total += safe_delete(SCHEDULED_DIR, "Scheduled Recipes", force)
        total += safe_delete(MCP_APPS_DIR, "MCP Apps cache", force)
        total += safe_delete(MCP_HERMIT_DIR, "MCP Hermit cache", force)
        print(f"\n✅ {total} Elements deleted — framework untouched")
        return

    if what not in targets:
        print(f"❌ Unknown: {what}")
        sys.exit(1)

    path, label = targets[what]
    print(f"\n🧹 {label}")
    print("=" * 60)
    safe_delete(path, label, force)
    if what == "schedule":
        safe_delete(SCHEDULED_DIR, "Scheduled Recipes", force)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    force = "--force" in sys.argv

    if cmd == "--status":
        cmd_status()
    elif cmd.startswith("--clear-"):
        what = cmd.replace("--clear-", "")
        cmd_clear(what, force)
    else:
        print(f"❌ Unbekannt: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
