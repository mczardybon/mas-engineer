#!/usr/bin/env python3
"""
dev_workspace.py — 📁 Workspace-Manager des dev-mas-engineer
===========================================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Creates und manages a Arbeitsordner for the framework-Development.
Der Workspace contains eine copy des installierten frameworks — der
MAS-Engineer arbeitet daran und installiert Changes back.

VERWENDUNG:
    python3 dev_workspace.py --init <workspace_dir>      # Workspace create
    python3 dev_workspace.py --install <workspace_dir>    # framework aus Workspace installieren
    python3 dev_workspace.py --uninstall                   # framework deinstallieren (MAS bleibt)
    python3 dev_workspace.py --install-mas <workspace>    # Only MAS aus Workspace installieren
    python3 dev_workspace.py --uninstall-mas              # Only MAS deinstallieren (framework bleibt)
    python3 dev_workspace.py --clean <workspace_dir>      # Workspace delete
    python3 dev_workspace.py --status <workspace_dir>     # status anshow
    python3 dev_workspace.py --rollback <workspace>  # Git-Log + rollback
    python3 dev_workspace.py --add-recipe <ws> <recipe>   # Ein Recipe aus Workspace installieren
    python3 dev_workspace.py --remove-recipe <recipe>     # Ein Recipe aus Goose remove
    python3 dev_workspace.py --help                        # This help anshow
"""

import sys, os, shutil, re, json
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("Error: yaml not installed. pip3 install pyyaml")
    sys.exit(1)


GOOSE_RECIPES = Path.home() / ".config" / "goose" / "recipes"
GOOSE_FRAMEWORK_DIR = Path.home() / ".local" / "share" / "goose" / "_framework"
GOOSE_DOCS = Path.home() / ".config" / "goose" / "docs"
GOOSE_CONFIG = Path.home() / ".config" / "goose" / "config.yaml"
TOOLS_DIR = GOOSE_RECIPES / "mas-engineer-tools"

# Source-Repo for Python scripts, tests, project files
AGENT_REPO = Path.home() / ".config" / "goose" / "recipes"

# Was will NICHT in den Workspace copyrt
EXCLUDE_RECIPES = {"dev-mas-engineer.yaml"}
EXCLUDE_DOCS = {"mas-engineer"}


def log(msg):
    print(msg)


def info(msg):
    print(f"📢 {msg}")


def ok(msg):
    print(f"✅ {msg}")


def warn(msg):
    print(f"⚠️  {msg}")


def error(msg):
    print(f"❌ {msg}")


def count_files(d: Path, pattern="*") -> int:
    if not d.exists():
        return 0
    return len(list(d.glob(pattern)))


def cmd_init_recovery(ws_dir):
    """Add Phoenix-Recovery-structure in new framework ein."""
    import shutil
    mas_dir = Path(ws_dir).resolve() / "mas-engineer"
    template_recovery = Path(__file__).parent.parent / "recipe" / "template" / "recovery"

    if not template_recovery.exists():
        warn("Recovery-Template not found")
        return

    target_sub = mas_dir / "recipe" / "sub"
    target_checkpoints = mas_dir / ".state" / "checkpoints"

    recoveries = ["immune", "checkpoint", "safezone", "timeline", "defib"]
    for name in recoveries:
        src = template_recovery / f"{name}.yaml"
        dst = target_sub / f"sub_mas-recovery-{name}.yaml"
        if src.exists() and not dst.exists():
            shutil.copy2(str(src), str(dst))
            ok(f"recovery: sub_mas-recovery-{name}.yaml")

    target_checkpoints.mkdir(parents=True, exist_ok=True)

    main_recipe = mas_dir / "recipe" / "dev-mas-engineer.yaml"
    if main_recipe.exists():
        with open(main_recipe) as f:
            d = yaml.safe_load(f)
        existing = {s["name"] for s in d.get("sub_recipes", [])}

        recovery_agents = [
            {"name": "sub_mas-recovery-immune", "path": "./sub/sub_mas-recovery-immune.yaml",
             "description": "YAML-Praevention & Syntax-Schutz"},
            {"name": "sub_mas-recovery-checkpoint", "path": "./sub/sub_mas-recovery-checkpoint.yaml",
             "description": "Git-similare Snapshots"},
            {"name": "sub_mas-recovery-safezone", "path": "./sub/sub_mas-recovery-safezone.yaml",
             "description": "Paralller Fork-Workspace"},
            {"name": "sub_mas-recovery-timeline", "path": "./sub/sub_mas-recovery-timeline.yaml",
             "description": "Automatische Best point-Suche"},
            {"name": "sub_mas-recovery-defib", "path": "./sub/sub_mas-recovery-defib.yaml",
             "description": "Emergency-Resuscitation"},
        ]
        for agent in recovery_agents:
            if agent["name"] not in existing:
                d.setdefault("sub_recipes", []).append(agent)

        with open(main_recipe, "w") as f:
            yaml.dump(d, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    ok("Phoenix-Recovery: immune, checkpoint, safezone, timeline, defib")
    ok("checkpoints/.state/ created")

def cmd_init(ws_dir: str):
    """Workspace mit copy des installierten frameworks create."""
    ws = Path(ws_dir).resolve()

    # Dev-mode? (zweites argument = "dev" → inkl. MAS-Tools + Docs)
    dev_mode = len(sys.argv) > 3 and sys.argv[3] == "dev"

    mode_label = "framework + MAS-Engineer" if dev_mode else "framework"
    log(f"\n📁 Workspace: {ws} ({mode_label})")
    log("=" * 60)

    # directory create
    fw = ws / "framework"
    (fw / "recipes").mkdir(parents=True, exist_ok=True)
    (fw / "docs").mkdir(parents=True, exist_ok=True)

    n_recipes = 0
    n_docs = 0

    # ── FRAMEWORK: Recipes copyren (Top-Level + _framework/) ──
    if GOOSE_RECIPES.exists():
        for src_dir in [GOOSE_RECIPES, GOOSE_FRAMEWORK_DIR]:
            if not src_dir.exists():
                continue
            for f in sorted(src_dir.iterdir()):
                if not f.name.endswith(".yaml"):
                    continue
                name = f.name.lstrip(".")
                if name in EXCLUDE_RECIPES:
                    continue  # dev-mas-engineer.yaml → MAS-Territorium
                if name.startswith("sub_mas-"):
                    continue  # MAS-Sub-agents → mas-engineer/recipe/sub/
                dest_path = fw / "recipes" / name
                if not dest_path.exists():
                    shutil.copy2(f, dest_path)
                    n_recipes += 1

    # ── MAS-ENGINEER: Recipe + Tools + Docs (NUR Dev-mode) ──
    if dev_mode:
        mas_recipe_dir = ws / "mas-engineer" / "recipe"
        mas_recipe_dir.mkdir(parents=True, exist_ok=True)
        mas_tools_dir = ws / "mas-engineer" / "tools"
        mas_docs_dir = ws / "mas-engineer" / "docs"

        # MAS-Rezept copyren
        mas_yaml = GOOSE_RECIPES / "dev-mas-engineer.yaml"
        if mas_yaml.exists():
            shutil.copy2(mas_yaml, mas_recipe_dir / "dev-mas-engineer.yaml")
            n_recipes += 1

        # MAS-Sub-agents copyren (aus GOOSE_RECIPES/)
        sub_src = GOOSE_RECIPES
        sub_dst = mas_recipe_dir / "sub"
        sub_dst.mkdir(exist_ok=True)
        mas_sub_count = 0
        if sub_src.exists():
            for f in sorted(sub_src.iterdir()):
                if f.name.startswith("sub_mas-"):
                    shutil.copy2(f, sub_dst / f.name)
                    mas_sub_count += 1
            if mas_sub_count > 0:
                ok(f"MAS-Sub-agents: {mas_sub_count} → mas-engineer/recipe/sub/")
                n_recipes += mas_sub_count

        # MAS-Tools copyren (aus mas-engineer-tools/)
        tools_src = GOOSE_RECIPES / "mas-engineer-tools"
        if tools_src.exists():
            if mas_tools_dir.exists():
                shutil.rmtree(mas_tools_dir)
            shutil.copytree(tools_src, mas_tools_dir)
            n_tools = count_files(mas_tools_dir, "*.py")
            ok(f"MAS-Tools: {n_tools} files → mas-engineer/tools/")
            n_recipes += n_tools

        # MAS-Docs copyren
        mas_docs_src = GOOSE_DOCS / "mas-engineer"
        if mas_docs_src.exists():
            if mas_docs_dir.exists():
                shutil.rmtree(mas_docs_dir)
            shutil.copytree(mas_docs_src, mas_docs_dir)
            n_mas_docs = count_files(mas_docs_dir, "*.md")
            ok(f"MAS-Docs: {n_mas_docs} files → mas-engineer/docs/")
            n_docs += n_mas_docs

    ok(f"Recipes: {n_recipes} files")

    # Docs copyren (mas-engineer/ separat in Dev-mode behandelt)
    if GOOSE_DOCS.exists():
        for item in sorted(GOOSE_DOCS.iterdir()):
            if item.name in EXCLUDE_DOCS:
                continue  # mas-engineer/ separat copyrt in Dev-mode oben
            dst = fw / "docs" / item.name
            if item.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
                n_docs += count_files(dst, "*.md")
            else:
                shutil.copy2(item, dst)
                n_docs += 1

    ok(f"Docs: {n_docs} files")

    # Config copyren
    if GOOSE_CONFIG.exists():
        shutil.copy2(GOOSE_CONFIG, fw / "config.yaml")

    # ── Python-Skripte copyren (NUR im Dev-mode) ──
    if dev_mode:
        python_dir = fw / "python"
        python_dir.mkdir(exist_ok=True)
        py_copied = 0
        for py_file in sorted(AGENT_REPO.glob("*.py")):
            if py_file.name.startswith("__") or py_file.name.endswith("_gui.py"):
                continue
            shutil.copy2(py_file, python_dir / py_file.name)
            py_copied += 1
        if py_copied > 0:
            ok(f"Python-Skripte: {py_copied} files → framework/python/")

    # ── Tests copyren ──
    tests_src = AGENT_REPO / "tests"
    if tests_src.exists():
        tests_dir = fw / "tests"
        tests_dir.mkdir(exist_ok=True)
        tc = 0
        for f in sorted(tests_src.glob("test_*.py")):
            shutil.copy2(f, tests_dir / f.name)
            tc += 1
        # __init__.py
        init = tests_src / "__init__.py"
        if init.exists():
            shutil.copy2(init, tests_dir / "__init__.py")
        ok(f"Tests: {tc} files → framework/tests/")

    # ── project-files copyren ──
    for proj_file in ["pyproject.toml", ".gitignore"]:
        src = AGENT_REPO / proj_file
        if src.exists():
            shutil.copy2(src, ws / proj_file)
    # Workspace .gitignore add
    gi = ws / ".gitignore"
    if gi.exists():
        gi.write_text(gi.read_text() + "\n# Workspace runtime\n.state/\n.backups/\n")
    ok("project-files: pyproject.toml, .gitignore")

    # ── README.md create ──
    readme = ws / "README.md"
    if dev_mode:
        readme.write_text(f"""# framework Workspace (Dev)

> Creates: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
> mode: framework + MAS-Engineer (Dev)

## structure

```
├── framework/          ← 🔒 framework (Rezepte, Docs, Tests, Config)
│   ├── recipes/        ← 94 YAML-Rezepte
│   ├── docs/           ← framework-Documentation
│   ├── config.yaml     ← framework-Configuration
│   ├── tests/          ← Test-files (pytest)
│   └── python/         ← Admin-Skripte
├── mas-engineer/       ← 🔒 MAS-Engineer (Rezept, Tools, Docs)
│   ├── recipe/         ← dev-mas-engineer.yaml + Sub-agents
│   ├── tools/          ← Python-Developer-Tools
│   └── docs/           ← MAS-Documentation
├── .git/               ← Git-Repository
├── .state/             ← Change-Historie
├── .backups/           ← Backups
└── start-sessions.sh   ← 🆕 Zwei Goose-Sessions start

## framework installieren

```bash
cd {ws} && python3 framework/python/install_framework.py install --source framework --no-launcher
```

## Tests execute

```bash
cd {ws} && python3 -m pytest framework/tests/ -q
```

## Dev-Sessions start

```bash
bash start-sessions.sh
```
""")
    else:
        readme.write_text(f"""# framework Workspace

> Creates: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
> mode: framework

## structure

```
├── framework/          ← framework (Rezepte, Docs, Tests, Config)
│   ├── recipes/        ← 94 YAML-Rezepte
│   ├── docs/           ← framework-Documentation
│   ├── config.yaml     ← framework-Configuration
│   ├── tests/          ← Test-files (pytest)
│   └── python/         ← Admin-Skripte
├── .git/               ← Git-Repository
├── .state/             ← Change-Historie
├── .backups/           ← Backups
└── pyproject.toml

## framework installieren

```bash
python3 {TOOLS_DIR}/dev_recipe_manager.py --install all
```

## Tests execute

```bash
cd {ws} && python3 -m pytest framework/tests/ -q
```
""")
    ok(f"README.md creates")

    # .state + .backups
    (ws / ".state").mkdir(exist_ok=True)
    (ws / ".backups").mkdir(exist_ok=True)

    # ── start-sessions.sh (only Dev-mode) ──
    if dev_mode:
        _write_start_sessions_script(ws)

    # ── Git-Repository initialize ──
    import subprocess as _sp
    if _sp.run(["git", "--version"], capture_output=True).returncode == 0:
        ws_str = str(ws)
        _sp.run(["git", "-C", ws_str, "init"], capture_output=True)
        _sp.run(["git", "-C", ws_str, "add", "-A"], capture_output=True)
        r = _sp.run(["git", "-C", ws_str, "commit", "-m", "initial workspace"],
                     capture_output=True, text=True)
        if r.returncode == 0:
            ok("Git-Repository initialized + initial commit")
        else:
            warn("Git: no commit (evtl. no Changes)")
    else:
        warn("Git not available — Workspace without version control")

    log("")
    cmd_init_recovery(ws_dir)
    ok(f"Workspace ready: {ws}")
    log(f"  📁 framework/    ← {n_recipes} Recipes, {n_docs} Docs, 1 Config, {tc if 'tc' in dir() else 0} Tests")
    if dev_mode:
        log(f"  📁 mas-engineer/  ← MAS-Rezept, Sub-agents, Tools, Docs")
        log(f"")
        log(f"  🚀 Zwei Goose-Sessions start:")
        log(f"     bash start-sessions.sh")


def _write_start_sessions_script(ws: Path):
    """Creates start-sessions.sh for zwei parallle Goose-Sessions."""
    script = ws / "start-sessions.sh"
    fw_recipes = ws / "framework" / "recipes"
    mas_recipes = ws / "mas-engineer" / "recipe"

    content = f'''#!/bin/bash
# ══════════════════════════════════════════════════
#  Dual-Session-Starter — framework + MAS-Engineer
# ══════════════════════════════════════════════════

set -e

WS="$(cd "$(dirname "$0")" && pwd)"
FW_RECIPES="$WS/framework/recipes"
MAS_RECIPES="$WS/mas-engineer/recipe"

if [ ! -d "$FW_RECIPES" ]; then
    echo "❌ framework-Recipes not found: $FW_RECIPES"
    exit 1
fi
if [ ! -f "$MAS_RECIPES/dev-mas-engineer.yaml" ]; then
    echo "❌ MAS-Rezept not found: $MAS_RECIPES/dev-mas-engineer.yaml"
    exit 1
fi

echo "╔══════════════════════════════════════════╗"
echo "║  🚀 framework Dev-Sessions              ║"
echo "╠══════════════════════════════════════════╣"
echo "║  🛠️  framework-Development               ║"
echo "║      RECIPE_PATH=$FW_RECIPES"
echo "║      Policy: Goose-First"
echo "║                                         ║"
echo "║  🔧 MAS-Engineer                        ║"
echo "║      RECIPE_PATH=$MAS_RECIPES"
echo "║      Policy: Python-First"
echo "╚══════════════════════════════════════════╝"

echo ""
echo "▶️  Starte 🛠️  framework-Development..."
GOOSE_RECIPE_PATH="$FW_RECIPES" goose session -n "🛠️ framework-Development" &
FW_PID=$!

sleep 1

echo "▶️  Starte 🔧 MAS-Engineer..."
GOOSE_RECIPE_PATH="$MAS_RECIPES" goose session -n "🔧 MAS-Engineer" &
MAS_PID=$!

sleep 1

echo ""
echo "✅ Beide Sessions started:"
echo "   🛠️  framework (PID $FW_PID)"
echo "      RECIPE_PATH=$FW_RECIPES"
echo "      Policy: Goose-First"
echo ""
echo "   🔧 MAS (PID $MAS_PID)"
echo "      RECIPE_PATH=$MAS_RECIPES"
echo "      Policy: Python-First"
echo ""
echo "Zum Stop: kill $FW_PID $MAS_PID"

wait
'''
    script.write_text(content)
    script.chmod(0o755)
    ok("start-sessions.sh creates (chmod +x)")


def cmd_install(ws_dir: str):
    """framework AUS DEM WORKSPACE via install_framework.py installieren."""
    ws = Path(ws_dir).resolve()
    import subprocess

    if not (ws / "framework" / "recipes").exists():
        error(f"No valid Workspace: {ws}")
        sys.exit(1)

    installr = ws / "framework" / "python" / "install_framework.py"
    if not installr.exists():
        error(f"Installr not im Workspace: {installr}")
        error("Nutze --init <path> dev for Workspace mit Python-Skripten")
        sys.exit(1)

    # Safety Pre-Check: MAS exists before?
    mas_yaml = GOOSE_RECIPES / "dev-mas-engineer.yaml"
    mas_tools = GOOSE_RECIPES / "mas-engineer-tools"
    mas_ok_before = mas_yaml.exists() and mas_tools.exists()
    if not mas_ok_before:
        warn("MAS-Engineer missing vor framework-Installation — will danach nachinstalliert")

    log(f"\n📦 Installiere framework aus: {ws}")
    log("=" * 60)

    result = subprocess.run(
        [sys.executable, str(installr), "install", "--source", str(ws / "framework"), "--no-launcher"]
    )

    if result.returncode != 0:
        error(f"framework-Installation failed (Exit {result.returncode})")
        sys.exit(1)

    # Safety Post-Check: MAS still da?
    mas_ok_after = mas_yaml.exists() and mas_tools.exists()
    if mas_ok_before and not mas_ok_after:
        warn("MAS after framework-Install verschwunden — will againhergestellt")
        _install_mas_from_workspace(ws)
    elif not mas_ok_after:
        warn("MAS-Engineer missing — will nachinstalliert")
        _install_mas_from_workspace(ws)

    ok(f"framework aus Workspace installiert ✓")


def _install_mas_from_workspace(ws: Path):
    """Hilfsfunction: MAS-files aus Workspace copyren."""
    # Recipe
    src = ws / "mas-engineer" / "recipe" / "dev-mas-engineer.yaml"
    if src.exists():
        shutil.copy2(src, GOOSE_RECIPES / "dev-mas-engineer.yaml")

    # Tools
    tools_src = ws / "mas-engineer" / "tools"
    if tools_src.exists():
        tools_dst = GOOSE_RECIPES / "mas-engineer-tools"
        if tools_dst.exists():
            shutil.rmtree(tools_dst)
        shutil.copytree(tools_src, tools_dst)

    # Docs
    docs_src = ws / "mas-engineer" / "docs"
    if docs_src.exists():
        docs_dst = GOOSE_DOCS / "mas-engineer"
        if docs_dst.exists():
            shutil.rmtree(docs_dst)
        shutil.copytree(docs_src, docs_dst)

    # Sub-agents (nach GOOSE_RECIPES/ for delegate()-Access)
    subs_src = ws / "mas-engineer" / "recipe" / "sub"
    if subs_src.exists():
        for f in subs_src.glob("sub_mas-*.yaml"):
            shutil.copy2(f, GOOSE_RECIPES / f.name)


def cmd_install_mas(ws_dir: str):
    """NUR MAS-Engineer from dem Workspace installieren."""
    ws = Path(ws_dir).resolve()

    if not (ws / "mas-engineer" / "recipe" / "dev-mas-engineer.yaml").exists():
        error(f"dev-mas-engineer.yaml not im Workspace: {ws}")
        error("Nutze --init <path> dev for Workspace mit MAS-Rezept")
        sys.exit(1)

    log(f"\n🔧 Installiere MAS-Engineer aus: {ws}")
    log("=" * 60)
    _install_mas_from_workspace(ws)

    mas_yaml = GOOSE_RECIPES / "dev-mas-engineer.yaml"
    mas_tools = GOOSE_RECIPES / "mas-engineer-tools"
    if mas_yaml.exists() and mas_tools.exists():
        ok("MAS-Engineer installiert ✓")
    else:
        error("MAS-Installation failed — files missing")


def cmd_uninstall():
    """framework deinstallieren — MAS bleibt keep."""
    # Safety Check
    mas_yaml = GOOSE_RECIPES / "dev-mas-engineer.yaml"
    if not mas_yaml.exists():
        error("⛔ MAS-Engineer missing — framework-Deinstallation verweigert")
        sys.exit(1)

    log(f"\n🗑️  Deinstalliere framework (MAS bleibt)")
    log("=" * 60)

    n = 0
    # Top-level YAMLs (EXCEPT dev-mas-engineer.yaml)
    for f in list(GOOSE_RECIPES.glob("*.yaml")):
        if f.name == "dev-mas-engineer.yaml":
            continue
        f.unlink()
        n += 1

    # _framework/ Directory
    fw_dir = GOOSE_RECIPES / "_framework"
    if fw_dir.exists():
        shutil.rmtree(fw_dir)
        n += 1

    # Docs (EXCEPT mas-engineer/)
    if GOOSE_DOCS.exists():
        for item in list(GOOSE_DOCS.iterdir()):
            if item.name == "mas-engineer":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            n += 1

    ok(f"framework deinstalliert ({n} Elements) — MAS bleibt ✓")


def cmd_uninstall_mas():
    """NUR MAS-Engineer deinstallieren — framework bleibt."""
    fw_yaml = GOOSE_RECIPES / "framework-starter.yaml"
    fw_dir = GOOSE_RECIPES / "_framework"

    if not fw_yaml.exists() or not fw_dir.exists():
        error("⛔ framework missing — MAS-Deinstallation verweigert")
        sys.exit(1)

    log(f"\n🗑️  Deinstalliere MAS-Engineer (framework bleibt)")
    log("=" * 60)

    n = 0
    for item in [
        GOOSE_RECIPES / "dev-mas-engineer.yaml",
        GOOSE_RECIPES / "mas-engineer-tools",
        GOOSE_DOCS / "mas-engineer",
    ]:
        if item.exists():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            n += 1

    # Sub-agents aus GOOSE_RECIPES delete
    for f in GOOSE_RECIPES.glob("sub_mas-*.yaml"):
        f.unlink()
        n += 1

    ok(f"MAS-Engineer deinstalliert ({n} Components) — framework bleibt ✓")


def cmd_rollback(ws_dir: str):
    """Git-Log show und rollback enable."""
    import subprocess
    ws_str = str(Path(ws_dir).resolve())

    if not (Path(ws_str) / ".git").exists():
        error("No Git-Repository im Workspace")
        sys.exit(1)

    n = 10
    for i, arg in enumerate(sys.argv):
        if arg == "--last" and i + 1 < len(sys.argv):
            try: n = int(sys.argv[i + 1])
            except: pass

    log(f"\n📜 GIT-LOG (letzte {n} commits)")
    log("=" * 60)
    subprocess.run(["git", "-C", ws_str, "log", "--oneline", f"-{n}"])

    print("\nrollback zu commit? (Hash oder Enter=cancel): ", end="")
    commit = input().strip()
    if commit:
        r = subprocess.run(
            ["git", "-C", ws_str, "reset", "--hard", commit],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            ok(f"rollback zu {commit[:8]}")
            subprocess.run(["git", "-C", ws_str, "log", "--oneline", "-3"])
        else:
            error(f"rollback failed: {r.stderr.strip()}")


def cmd_add_recipe(ws_dir: str, recipe_name: str):
    """Einzelnes Recipe from dem Workspace in Goose installieren."""
    ws = Path(ws_dir).resolve()
    src = ws / "framework" / "recipes" / recipe_name

    if not src.exists():
        error(f"Recipe not found: {src}")
        sys.exit(1)

    dst = GOOSE_RECIPES / recipe_name

    # Backup falls already present
    if dst.exists():
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        bak = GOOSE_RECIPES / f"{recipe_name}.bak-{ts}"
        shutil.copy2(dst, bak)
        ok(f"Backup: {bak}")

    shutil.copy2(src, dst)

    # slash_command remove (only dev-mas-engineer keeps it)
    if recipe_name != "dev-mas-engineer.yaml":
        text = dst.read_text()
        text = re.sub(r"^slash_command:.*\n", "", text, flags=re.MULTILINE)
        dst.write_text(text)

    # Verstecken if not sichtbar → _framework/
    if recipe_name not in {"framework-starter.yaml", "dev-mas-engineer.yaml"}:
        fw_dir = GOOSE_RECIPES / "_framework"
        fw_dir.mkdir(parents=True, exist_ok=True)
        fw_dst = fw_dir / recipe_name
        if fw_dst.exists():
            fw_dst.unlink()
        shutil.move(str(dst), str(fw_dst))

    ok(f"Recipe installiert: {recipe_name}")


def cmd_remove_recipe(recipe_name: str):
    """Einzelnes Recipe aus Goose remove (recipes/ + _framework/)."""
    found = False
    for search_dir in [GOOSE_RECIPES, GOOSE_RECIPES / "_framework"]:
        tgt = search_dir / recipe_name
        if tgt.exists():
            tgt.unlink()
            print(f"🗑️  {recipe_name}")
            found = True
            break
    if not found:
        warn(f"Recipe not found: {recipe_name}")


def cmd_clean(ws_dir: str):
    """Workspace delete."""
    ws = Path(ws_dir).resolve()
    if not ws.exists():
        warn(f"Workspace exists not: {ws}")
        return

    log(f"\n🗑️  Delete Workspace: {ws}")
    shutil.rmtree(ws)
    ok(f"Workspace deleted")


def cmd_status(ws_dir: str):
    """Workspace-status anshow."""
    ws = Path(ws_dir).resolve()

    log(f"\n📊 Workspace: {ws}")
    log("=" * 60)

    if not ws.exists():
        warn("Workspace exists not.")
        return

    n_yaml = count_files(ws / "framework" / "recipes", "*.yaml")
    n_py = count_files(ws / "mas-engineer" / "tools", "*.py")
    n_core = count_files(ws / "framework" / "docs" / "core", "*.md")
    n_exec = count_files(ws / "framework" / "docs" / "executor", "*.md")
    n_plan = count_files(ws / "framework" / "docs" / "planner", "*.md")
    n_other = count_files(ws / "framework" / "docs", "*.md")
    n_config = 1 if (ws / "framework" / "config.yaml").exists() else 0

    log(f"  📄 Recipes:  {n_yaml} YAML + {n_py} Tools")
    log(f"  📋 Docs:     {n_core} core + {n_exec} executor + {n_plan} planner + {n_other} other")
    log(f"  ⚙️  Config:   {n_config}")

    # Changes (via changes.json)
    changes_file = ws / ".state" / "changes.json"
    if changes_file.exists():
        import json
        try:
            data = json.loads(changes_file.read_text())
            total = data.get("stats", {}).get("total_changes", 0)
            log(f"  📝 Changes: {total}")
        except:
            pass


# ─── Scaffold: Agent-Generator ─────────────────────────────

MAS_TEMPLATE = Path(__file__).parent.parent / "recipe" / "template" / "agent_template.yaml"


def _ask_type():
    """Interaktive type-selection: mas, specialist oder sub."""
    print("\n📋 AGENT-GENERATOR v1.0.0")
    print("━" * 50)
    print("What type of agent would you like to create?")
    print()
    print("  1) MAS — Sub-Agent (mas-engineer/recipe/sub/)")
    print("  2) framework — Specialist (framework/recipes/specialists/)")
    print("  3) framework — Sub-Agent (framework/recipes/sub/)")
    print()

    while True:
        try:
            choice = input("  Selection (1-3): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  ❌ Abgebrochen")
            return None, None, None
        if choice == "1":
            return "mas_sub", "mas-engineer/recipe/sub/", "agent_template.yaml"
        elif choice == "2":
            return "fw_specialist", "framework/recipes/specialists/", None
        elif choice == "3":
            return "fw_sub", "framework/recipes/sub/", None
        print("  ❌ Invalid — bitte 1, 2 oder 3 enter")


def _ask_name(agent_type):
    """Interaktive Namensquery mit validation."""
    import re
    print()
    if agent_type == "mas_sub":
        hint = "Name (z.B. 'database-cleaner' → sub_mas-database-cleaner.yaml)"
    elif agent_type == "fw_specialist":
        hint = "Name (z.B. 'deploy' → deploy.yaml)"
    else:
        hint = "Name (z.B. 'config-writer' → sub_config-writer.yaml)"
    print(f"  {hint}")
    while True:
        try:
            name = input("  > ").strip().lower().replace(" ", "-")
        except (EOFError, KeyboardInterrupt):
            print("\n  ❌ Abgebrochen")
            return None
        if not name:
            print("  ❌ Name may not empty be")
            continue
        if not re.match(r'^[a-z0-9-]+$', name):
            print("  ❌ Only smallbuchstaben, Zahlen und Bindestriche erlaubt")
            continue
        return name


def _ask_description():
    """Interaktive query from Description und Emoji."""
    print()
    try:
        desc = input("  Description (z.B. 'Database-Cleanup'): ").strip()
        emoji = input("  Emoji (z.B. 🛡️, 🧪, 🖥️): ").strip() or "🤖"
    except (EOFError, KeyboardInterrupt):
        print("\n  ❌ Abgebrochen")
        return None, None
    return desc or name.replace("-", " ").title(), emoji


def _generate_agent(agent_type, name, description, emoji, workspace):
    """copyrt Template und replaces Platzholder. generated bei framework a minimum-YAML."""
    import shutil

    ws = Path(workspace)

    if agent_type == "mas_sub":
        dst_dir = ws / "mas-engineer" / "recipe" / "sub"
        filename = f"sub_mas-{name}.yaml"
        if not MAS_TEMPLATE.exists():
            print(f"  ❌ Template not found: {MAS_TEMPLATE}")
            return None
    elif agent_type == "fw_specialist":
        dst_dir = ws / "framework" / "recipes" / "specialists"
        filename = f"{name}.yaml"
    else:
        dst_dir = ws / "framework" / "recipes" / "sub"
        filename = f"sub_{name}.yaml"

    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / filename

    if dst.exists():
        try:
            overwrite = input(f"  ⚠️ {filename} exists already. Overwrite? (j/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  ❌ Abgebrochen")
            return None
        if overwrite != "j":
            print("  ❌ Skip")
            return None

    if agent_type == "mas_sub" and MAS_TEMPLATE.exists():
        content = MAS_TEMPLATE.read_text()
        content = content.replace("{NAME}", name.upper().replace("-", " "))
        content = content.replace("{name}", name.lower())
        content = content.replace("{name}", name.lower())
        content = content.replace("{EMOJI}", emoji)
        content = content.replace("{BESCHREIBUNG}", description)
        content = content.replace("{TASK}", description)
        content = content.replace("{Titel}", description)
        dst.write_text(content)
    else:
        # minimum-YAML for framework
        display_name = name.upper().replace("-", " ")
        content = f"""version: 1.0.0
title: "{display_name} — {description}"
description: 'v1.0.0 | framework: {description}'

prompt: |
  {emoji} {display_name} (v1.0.0)
  ⛔ Reasonrulen:
     1. NOTHING automatically applied
     2. framework-governance.md noten
  🎯 {description}

settings:
  timeout: 600
  max_steps: 100
  provider: openai
  model: filtered/deepseek/deepseek-chat
"""
        dst.write_text(content)

    rel = dst.relative_to(ws)
    print(f"  ✅ Creates: {rel}")
    return dst


def _validate_agent(yaml_path, agent_type):
    """Validated gegen Best Practices (MAS) oder YAML (framework)."""
    import subprocess, yaml

    print()
    print(f"  🔍 Validiere {yaml_path.name}...")

    if agent_type == "mas_sub":
        editor = Path(__file__).parent / "dev_editor.py"
        if not editor.exists():
            print("  ℹ️ dev_editor.py not found — skip validation")
            return

        result = subprocess.run(
            ["python3", str(editor), "--validate", str(yaml_path)],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        print(result.stdout)
        if result.returncode == 0:
            print("  ✅ validation: INVENTORYEN")
        else:
            print("  ⚠️ validation: FAILED — Agent nevertheless creates")
    else:
        try:
            with open(yaml_path) as fh:
                yaml.safe_load(fh)
            print("  ✅ YAML-Syntax: OK")
            print("  ℹ️ framework: No MAS-Best-Practices available — manuelle Check recommended")
        except yaml.YAMLError as e:
            print(f"  ❌ YAML-Syntax-Error: {e}")


def _register_agent(name, description, emoji, workspace):
    """Readyet sub_recipes-Registrierung vor (zeigt Anleitung)."""
    print()
    try:
        register = input("  Agent als sub_recipes in dev-mas-engineer.yaml registrieren? (j/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("  ℹ️ Skipped")
        return

    if register != "j":
        print("  ℹ️ Nicht registriert.")
        return

    name_lower = name.lower()
    safe_name = f"sub_mas-{name_lower}"
    safe_path = f"./sub/sub_mas-{name_lower}.yaml"
    safe_desc = f"{emoji} {description}"

    # Check ob already present
    main_path = Path(workspace) / "mas-engineer" / "recipe" / "dev-mas-engineer.yaml"
    if main_path.exists():
        with open(main_path) as fh:
            content = fh.read()
        if safe_name in content:
            print(f"  ⚠️ {safe_name} already in dev-mas-engineer.yaml registriert!")
            return

    print(f"""
  ✅ Registrierungs-Data:

  Add to recipe/dev-mas-engineer.yaml (into matching group):

    - name: \"{safe_name}\"
      path: \"{safe_path}\"
      description: \"{safe_desc}\"

  Run then aus: update.sh --mas
""")


def _show_summary(agent_type, name, description, emoji, yaml_path):
    """Abclosede Togetherfassung."""
    ws = Path(os.getcwd())

    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │  ✅ AGENT ERSTELLT                            │")
    print("  ├─────────────────────────────────────────────┤")
    type_label = {"mas_sub": "MAS Sub-Agent",
                  "fw_specialist": "framework Specialist",
                  "fw_sub": "framework Sub-Agent"}.get(agent_type, agent_type)
    print(f"  │  type:    {type_label:<22}{'│':>10}")
    print(f"  │  Name:   {name:<22}{'│':>10}")
    print(f"  │  Emoji:  {emoji:<22}{'│':>10}")
    print(f"  │  Path:   {str(yaml_path.relative_to(ws)):<22}{'│':>2}")
    print("  ├─────────────────────────────────────────────┤")

    if agent_type == "mas_sub":
        steps = [
            "1. dev_editor.py --validate <path> (bei Changeen)",
            "2. sub_recipes-entry in dev-mas-engineer.yaml",
            "3. update.sh --mas",
        ]
    else:
        steps = [
            "1. file manuell anpassen (prompt, instructions)",
            "2. framework-Dependencyen checkn",
        ]
    for s in steps:
        print(f"  │  {s:<39}{'│':>1}")
    print("  └─────────────────────────────────────────────┘")


# ─── Multi-project-Management ───────────────────────────────

PROJECTS_FILE = "framework/.projects.yaml"

def _load_projects():
    """Load .projects.yaml. Create if not present."""
    pp = Path(PROJECTS_FILE)
    if not pp.exists():
        pp.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0.0", "last_updated": datetime.now().isoformat(),
            "active_project": "dev-team",
            "projects": {"dev-team": {"label": "DEV-TEAM", "created": "2026-06-13",
                         "type": "multi_agent_system", "agents": 0, "tests": 0,
                         "config": "dev-team/config.yaml", "status": "stable"}}
        }
        yaml.dump(data, open(pp, "w"), default_flow_style=False, allow_unicode=True)
    return yaml.safe_load(open(pp))

def _save_projects(data):
    """memorye .projects.yaml."""
    data["last_updated"] = datetime.now().isoformat()
    yaml.dump(data, open(PROJECTS_FILE, "w"), default_flow_style=False, allow_unicode=True)

def _active_project_path():
    """Give Path to the aktiven project back."""
    data = _load_projects()
    active = data.get("active_project", "dev-team")
    return Path("framework") / active, active

def cmd_project_list():
    """--project list: All projecte anshow."""
    data = _load_projects()
    active = data.get("active_project", "")
    print(f"\n  framework-projecte")
    print(f"  {'='*50}")
    for name, p in data.get("projects", {}).items():
        marker = "  <- active" if name == active else ""
        status_icon = {"stable": "gruen", "draft": "gelb", "archived": "rot"}.get(p.get("status", ""), "weiss")
        print(f"  {status_icon} {name:<20} {p.get('agents', 0):>3} Agents  {p.get('tests', 0):>3} Tests  {p.get('status', '?')}{marker}")
    print(f"  {'='*50}")
    print(f"  Total: {len(data.get('projects', {}))} projecte")

def cmd_project_create(name, copy_from=None):
    """--project create <name> [--copy <old>]: New project."""
    data = _load_projects()
    if name in data.get("projects", {}):
        print(f"  project '{name}' exists already")
        return
    
    pp = Path("framework") / name
    if copy_from:
        src = Path("framework") / copy_from
        if not src.exists():
            print(f"  Quell-project '{copy_from}' not found")
            return
        import shutil
        shutil.copytree(src, pp)
        print(f"  copyrt von '{copy_from}' after '{name}'")
    else:
        pp.mkdir(parents=True, exist_ok=True)
        (pp / "recipes" / "core").mkdir(parents=True)
        (pp / "recipes" / "sub").mkdir(parents=True)
        (pp / "docs").mkdir(parents=True)
        (pp / "tests").mkdir(parents=True)
        
        # config.yaml
        cfg = {"version": "1.0.0", "project_name": name,
               "project_type": "multi_agent_system", "created": datetime.now().strftime("%Y-%m-%d")}
        yaml.dump(cfg, open(pp / "config.yaml", "w"), default_flow_style=False, allow_unicode=True)
        
        print(f"  Ordnerstructure creates: framework/{name}/")
    
    # .projects.yaml update
    if "projects" not in data:
        data["projects"] = {}
    data["projects"][name] = {
        "label": name.upper(), "created": datetime.now().strftime("%Y-%m-%d"),
        "type": "multi_agent_system", "agents": 0, "tests": 0,
        "config": f"{name}/config.yaml", "status": "draft"
    }
    data["active_project"] = name
    _save_projects(data)
    
    # Symlink update
    symlink = Path("framework/current")
    if symlink.exists() or symlink.is_symlink():
        symlink.unlink()
    symlink.symlink_to(name)
    
    print(f"  Aktives project: {name}")

def cmd_project_switch(name):
    """--project switch <name>: Aktives project wechseln."""
    data = _load_projects()
    if name not in data.get("projects", {}):
        print(f"  project '{name}' not found")
        cmd_project_list()
        return
    
    data["active_project"] = name
    _save_projects(data)
    
    # Symlink update
    symlink = Path("framework/current")
    if symlink.exists() or symlink.is_symlink():
        symlink.unlink()
    symlink.symlink_to(name)
    
    p = data["projects"][name]
    print(f"  Aktives project: {name} ({p.get('agents', 0)} Agents, {p.get('tests', 0)} Tests)")

def cmd_project_show(name):
    """--project show <name>: Details anshow."""
    data = _load_projects()
    if name not in data.get("projects", {}):
        print(f"  project '{name}' not found"); return
    p = data["projects"][name]
    print(f"\n  project: {name}")
    print(f"  Label:   {p.get('label', '?')}")
    print(f"  type:     {p.get('type', '?')}")
    print(f"  Agents:  {p.get('agents', 0)}")
    print(f"  Tests:   {p.get('tests', 0)}")
    print(f"  status:  {p.get('status', '?')}")

def cmd_project_delete(name):
    """--project delete <name>: project delete (mit Backup)."""
    if name == "dev-team":
        print("  dev-team can not deleted will (Basis-project)"); return
    
    data = _load_projects()
    if name not in data.get("projects", {}):
        print(f"  project '{name}' not found"); return
    
    import shutil
    pp = Path("framework") / name
    backup = Path("framework/.trash") / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if pp.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(pp), str(backup))
        print(f"  Backup: {backup}")
    
    del data["projects"][name]
    if data.get("active_project") == name:
        data["active_project"] = "dev-team"
        symlink = Path("framework/current")
        if symlink.exists() or symlink.is_symlink():
            symlink.unlink()
        symlink.symlink_to("dev-team")
    _save_projects(data)
    print(f"  project '{name}' deleted (Backup in .trash/)")

def cmd_project_rename(old, new):
    """--project rename <old> <new>: project umbenennen."""
    data = _load_projects()
    if old not in data.get("projects", {}):
        print(f"  project '{old}' not found"); return
    if new in data.get("projects", {}):
        print(f"  project '{new}' exists already"); return
    
    import shutil
    src = Path("framework") / old
    dst = Path("framework") / new
    if src.exists():
        src.rename(dst)
    
    data["projects"][new] = data["projects"].pop(old)
    data["projects"][new]["config"] = f"{new}/config.yaml"
    if data.get("active_project") == old:
        data["active_project"] = new
        symlink = Path("framework/current")
        if symlink.exists() or symlink.is_symlink():
            symlink.unlink()
        symlink.symlink_to(new)
    _save_projects(data)
    print(f"  '{old}' -> '{new}'")

def cmd_project(args):
    """Dispatch for --project Commands."""
    cmd = args[0] if args else "list"
    if cmd in ("list", "ls", "l"):
        cmd_project_list()
    elif cmd in ("create", "new", "c"):
        name = args[1] if len(args) > 1 else input("  projectname: ").strip()
        copy_from = None
        if "--copy" in args:
            ci = args.index("--copy")
            copy_from = args[ci+1] if ci+1 < len(args) else None
        if name:
            cmd_project_create(name, copy_from)
    elif cmd in ("switch", "sw", "s"):
        name = args[1] if len(args) > 1 else input("  projectname: ").strip()
        if name:
            cmd_project_switch(name)
    elif cmd in ("show", "info", "i"):
        name = args[1] if len(args) > 1 else input("  projectname: ").strip()
        if name:
            cmd_project_show(name)
    elif cmd in ("delete", "del", "rm", "d"):
        name = args[1] if len(args) > 1 else input("  projectname: ").strip()
        if name:
            cmd = input(f"  project '{name}' wirklich delete? (j/N): ").strip().lower()
            if cmd == "j":
                cmd_project_delete(name)
    elif cmd in ("rename", "mv", "r"):
        old = args[1] if len(args) > 1 else input("  older Name: ").strip()
        new = args[2] if len(args) > 2 else input("  newer Name: ").strip()
        if old and new:
            cmd_project_rename(old, new)
def cmd_doctor_init(target_path):
    """Creates new framework-project mit MAS-Integration."""
    from pathlib import Path
    import json
    from datetime import datetime

    target = Path(target_path).resolve()

    if target.exists():
        overwrite = input(f"  Target {target} exists. Aboutwrite? (j/N): ").strip().lower()
        if overwrite != "j":
            print("  Abgebrochen")
            return

    # Reaelseruktur
    (target / "recipes" / "specialists").mkdir(parents=True, exist_ok=True)
    (target / "recipes" / "core").mkdir(parents=True, exist_ok=True)
    (target / "recipes" / "sub").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / "tests").mkdir(parents=True, exist_ok=True)

    # .doctor Directory (MAS-Integration)
    doctor_dir = target / ".doctor"
    doctor_dir.mkdir(parents=True, exist_ok=True)

    # Knowledge-Base
    bp = {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "best_practices": {"prompt": [], "settings": [], "structure": [], "tests": []}
    }
    import yaml
    yaml.dump(bp, open(doctor_dir / "best-practices.yaml", "w"),
              default_flow_style=False, allow_unicode=True)

    # MAS-Registrierung
    config = {
        "mas_managed": True,
        "framework_path": str(target),
        "registered": datetime.now().isoformat()
    }
    json.dump(config, open(doctor_dir / "config.json", "w"), indent=2)

    print(f"""
  framework-project creates: {target}

  recipes/
    core/          Core-agents (starter, planner, executor)
    specialists/   Spezialisierte agents
    sub/           Sub-agents
  docs/            Documentation
  tests/           pytest-Tests
  .doctor/         MAS-Integration
    config.json    MAS-Registrierung
    best-practices.yaml   Knowledge-Base

  Jetzt: dev_agent_doctor.py --scan
""")


def cmd_scaffold(args):
    """Hauptfunction for --scaffold."""
    # Phase 1: type
    agent_type, rel_dir, _ = _ask_type()
    if not agent_type:
        return

    # Phase 2: Name
    name = args.name if getattr(args, 'name', None) else _ask_name(agent_type)
    if not name:
        return

    # Phase 3: Description + Emoji
    if getattr(args, 'quiet', False):
        desc, emoji = name.replace("-", " ").title(), "🤖"
    else:
        desc, emoji = _ask_description()
        if not desc:
            return

    # Phase 4: Generate
    workspace = os.getcwd()
    yaml_path = _generate_agent(agent_type, name, desc, emoji, workspace)
    if not yaml_path:
        return

    # Phase 5: Validate
    if not getattr(args, 'no_validate', False):
        _validate_agent(yaml_path, agent_type)

    # Phase 6: Registrieren (only MAS)
    if agent_type == "mas_sub":
        _register_agent(name, desc, emoji, workspace)

    # Phase 7: Togetherfassung
    _show_summary(agent_type, name, desc, emoji, yaml_path)


def cmd_install_check(ws_dir):
    """Check ob MAS after newinstallation functionieren would."""
    mas_dir = Path(ws_dir) / "mas-engineer"
    if not mas_dir.exists():
        error(f"No MAS-Directory: {mas_dir}")
        return

    checks = []
    ok("=== INSTALL-CHECK ===")

    # C1: YAML-validation
    yaml_ok = yaml_total = 0
    for f in mas_dir.rglob("*.yaml"):
        if ".backups" in str(f): continue
        yaml_total += 1
        try:
            import yaml as _y
            _y.safe_load(f.read_text())
            yaml_ok += 1
        except: pass

    if yaml_ok == yaml_total:
        ok(f"YAML: {yaml_ok}/{yaml_total} gueltig")
    else:
        warn(f"YAML: {yaml_ok}/{yaml_total} gueltig")
    checks.append(("yaml", yaml_ok == yaml_total, f"{yaml_ok}/{yaml_total}"))

    # C2: Hardcodierte Pathe
    hardcoded = 0
    for f in mas_dir.rglob("*"):
        if f.is_file() and f.suffix in (".yaml", ".py", ".md", ".sh"):
            if ".bak" in f.name or ".backups" in str(f): continue
            try:
                text = f.read_text()
                for p in [os.path.expanduser("~") + "/"]:
                    if p in text: hardcoded += 1
            except: pass

    if hardcoded == 0:
        ok(f"Pathe: sauber ({hardcoded} hardcodiert)")
    else:
        warn(f"Pathe: {hardcoded} hardcodiert")
    checks.append(("paths", hardcoded == 0, str(hardcoded)))

    # C3: framework-Undependentkeit
    has_main = (mas_dir / "recipe" / "dev-mas-engineer.yaml").exists()
    has_sub = (mas_dir / "recipe" / "sub").exists()
    has_tools = (mas_dir / "tools").exists() and len(list((mas_dir / "tools").glob("dev_*.py"))) >= 8
    fw_ok = has_main and has_sub and has_tools
    if fw_ok:
        ok(f"Standalone: Main-Recipe + Sub + {len(list((mas_dir / 'tools').glob('dev_*.py')))} Tools")
    else:
        warn(f"Standalone: missing Components")
    checks.append(("standalone", fw_ok, ""))

    # C4: Paralllitaet
    main_r = (mas_dir / "recipe" / "dev-mas-engineer.yaml").read_text()
    has_par = "PARALLEL-POOL" in main_r
    ok(f"Paralll: {'yes' if has_par else 'no'}")
    checks.append(("paralll", has_par, ""))

    # C5: Backups
    bdir = mas_dir / ".backups"
    has_bak = bdir.exists()
    ok(f"Backups: {'present' if has_bak else 'no'}")
    checks.append(("backups", has_bak, ""))

    passed = sum(1 for c in checks if c[1])
    total = len(checks)
    score = int(passed / total * 100) if total else 0
    ok(f"Score: {score}/100 ({passed}/{total} bestanden)")
    return checks

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    ws_dir = sys.argv[2] if len(sys.argv) > 2 else ""

    if cmd == "--scaffold":
        class ScaffoldArgs:
            name = None
            no_validate = False
            quiet = False
        # Parse optionale arguments after --scaffold
        extra = sys.argv[2:]
        for i, a in enumerate(extra):
            if a == "--name" and i + 1 < len(extra):
                ScaffoldArgs.name = extra[i + 1]
            elif a == "--no-validate":
                ScaffoldArgs.no_validate = True
            elif a == "--quiet":
                ScaffoldArgs.quiet = True
        cmd_scaffold(ScaffoldArgs)
    elif cmd == "--init" and ws_dir:
        cmd_init(ws_dir)
    elif cmd == "--install" and ws_dir:
        cmd_install(ws_dir)
    elif cmd == "--uninstall":
        cmd_uninstall()
    elif cmd == "--install-check" and ws_dir:
        cmd_install_check(ws_dir)
    elif cmd == "--install-mas" and ws_dir:
        cmd_install_mas(ws_dir)
    elif cmd == "--uninstall-mas":
        cmd_uninstall_mas()
    elif cmd == "--clean" and ws_dir:
        cmd_clean(ws_dir)
    elif cmd == "--status" and ws_dir:
        cmd_status(ws_dir)
    elif cmd == "--add-recipe" and ws_dir:
        recipe = sys.argv[3] if len(sys.argv) > 3 else ""
        if recipe:
            cmd_add_recipe(ws_dir, recipe)
        else:
            info("No Recipe-Name specified")
    elif cmd == "--rollback" and ws_dir:
        cmd_rollback(ws_dir)
    elif cmd == "--project":
        cmd_project(sys.argv[2:] if len(sys.argv) > 2 else ["list"])
    elif cmd == "--doctor-init" and ws_dir:
        cmd_doctor_init(ws_dir)
    elif cmd == "--remove-recipe":
        recipe = sys.argv[2] if len(sys.argv) > 2 else ""
        if recipe:
            cmd_remove_recipe(recipe)
        else:
            info("No Recipe-Name specified")
    else:
        print(f"❌ Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
