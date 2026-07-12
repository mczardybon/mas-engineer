#!/usr/bin/env python3
"""
dev_recipe_manager.py — Rezept-Manager for Goose GUI
====================================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Manages which Framework-Components in Goose sichtbar are.
Installiert / deinstalliert Rezepte getargett in:
  {RECIPES_DIR}/             — sichtbare Rezepte (Starter, MAS-Engineer)
  {RECIPES_DIR}/_framework/  — unsichtbare Rezepte (for Delegation)

VERWENDUNG:
    python3 dev_recipe_manager.py --install <spec>     # Installieren
    python3 dev_recipe_manager.py --uninstall <spec>   # Deinstallieren
    python3 dev_recipe_manager.py --list               # status
    python3 dev_recipe_manager.py --cleanup-hidden     # Old .yaml-files clean

<spec> can be:
    minimal      — starter + mas-engineer + core (5 files)
    core         — planner + executor + controller (3 files)
    specialists  — all 47 Specialists
    sub-agents   — all 43 Sub-agents
    all          — ALLES (95 files)
    <filename>   — Einzelne file (z.B. specialist_security.yaml)
    a,b,c        — Komma-separated (z.B. starter,mas-engineer,core)
"""

import sys, shutil, re
from pathlib import Path

# ─── PFADE ───
GOOSE_RECIPES = Path.home() / ".config" / "goose" / "recipes"
GOOSE_FRAMEWORK_DIR = Path.home() / ".local" / "share" / "goose" / "_framework"
FRAMEWORK_DIR = GOOSE_FRAMEWORK_DIR
AGENT_REPO = Path(__file__).parent.parent.parent.resolve()

def _discover_framework_root(base: Path) -> Path:
    for candidate in [base] + [d for d in sorted(base.iterdir()) if d.is_dir() and (d / "recipes").exists()]:
        if (candidate / "recipes").exists():
            return candidate
    return base

FW_ROOT = _discover_framework_root(AGENT_REPO)
REPO_MAIN = FW_ROOT / "recipes"
REPO_SPECIALISTS = REPO_MAIN / "specialists"
MAS_RECIPE_DIR = FW_ROOT / "mas-engineer" / "recipe"

KEEP_SLASH = {"framework-starter.yaml", "dev-mas-engineer.yaml"}
VISIBLE_RECIPES = {"framework-starter.yaml", "dev-mas-engineer.yaml"}


# ─── KATEGORIEN ───
CATEGORIES = {
    "starter": {
        "files": ["framework-starter.yaml"],
        "visible": True,
    },
    "mas-engineer": {
        "files": ["dev-mas-engineer.yaml"],
        "visible": True,
    },
    "planner": {
        "files": ["planner.yaml"],
        "visible": False,
    },
    "executor": {
        "files": ["executor.yaml"],
        "visible": False,
    },
    "controller": {
        "files": ["framework-controller.yaml"],
        "visible": False,
    },
    "core": {
        "files": ["planner.yaml", "executor.yaml", "framework-controller.yaml"],
        "visible": False,
    },
    "specialists": {
        "files": [
            "specialist_accessibility.yaml", "specialist_ai_engineer.yaml",
            "specialist_api_designer.yaml", "specialist_api_gateway.yaml",
            "specialist_auth.yaml", "specialist_backend.yaml",
            "specialist_chaos_engineer.yaml", "specialist_cloud_architect.yaml",
            "specialist_cost_optimizer.yaml", "specialist_data_engineer.yaml",
            "specialist_data_governance.yaml", "specialist_data_scientist.yaml",
            "specialist_database.yaml", "specialist_ddd_architect.yaml",
            "specialist_dependency_manager.yaml", "specialist_devops.yaml",
            "specialist_devsecops.yaml", "specialist_event_driven.yaml",
            "specialist_frontend.yaml", "specialist_i18n.yaml",
            "specialist_incident_response.yaml", "specialist_legal_compliance.yaml",
            "specialist_migration.yaml", "specialist_ml_engineer.yaml",
            "specialist_mobile.yaml", "specialist_mobile_ci.yaml",
            "specialist_multi_tenant.yaml", "specialist_observability.yaml",
            "specialist_onboarding.yaml", "specialist_performance.yaml",
            "specialist_platform_engineer.yaml", "specialist_quality_manager.yaml",
            "specialist_reoldime_engineer.yaml", "specialist_refactoring.yaml",
            "specialist_release_manager.yaml", "specialist_requirements_engineer.yaml",
            "specialist_reviewer.yaml", "specialist_search_engineer.yaml",
            "specialist_security.yaml", "specialist_software_architekt.yaml",
            "specialist_software_engineer.yaml", "specialist_sre.yaml",
            "specialist_system_architekt.yaml", "specialist_technical_writer.yaml",
            "specialist_test_engineer.yaml", "specialist_ux_designer.yaml",
            "specialist_workflow_engineer.yaml",
        ],
        "visible": False,
    },
    "sub-agents": {
        "files": [
            "sub_agent-selector.yaml",
            "sub_analyst-accessibility.yaml", "sub_analyst-auth.yaml",
            "sub_analyst-backend.yaml", "sub_analyst-code.yaml",
            "sub_analyst-deps.yaml", "sub_analyst-devops.yaml",
            "sub_analyst-docs.yaml", "sub_analyst-i18n.yaml",
            "sub_analyst-infra.yaml", "sub_analyst-migration.yaml",
            "sub_analyst-observability.yaml", "sub_analyst-performance.yaml",
            "sub_analyst-quality.yaml", "sub_analyst-refactoring.yaml",
            "sub_analyst-requirements.yaml", "sub_analyst-security.yaml",
            "sub_analyst-sre.yaml", "sub_analyst-tests.yaml",
            "sub_analyst-ux.yaml", "sub_analyst.yaml",
            "sub_context-preparer.yaml", "sub_degradation-handler.yaml",
            "sub_dispatcher.yaml",
            "sub_fw-monitor-comms.yaml", "sub_fw-monitor-debug.yaml",
            "sub_fw-monitor-heoldh.yaml", "sub_fw-monitor-memory.yaml",
            "sub_fw-monitor-recovery.yaml", "sub_fw-monitor-runtime.yaml",
            "sub_fw-monitor-session.yaml",
            "sub_interpreter.yaml", "sub_memory-writer.yaml",
            "sub_mode-selector.yaml", "sub_orchestrator.yaml",
            "sub_plan-validator.yaml", "sub_session-init.yaml",
            "sub_signal-generator.yaml", "sub_starter-launch.yaml",
            "sub_status-tracker.yaml", "sub_summarizer.yaml",
            "sub_verification-runner.yaml", "sub_worktree-manager.yaml",
        ],
        "visible": False,
    },
}


# ─── HILFSFUNKTIONEN ───

def find_recipe_file(filename, main_dir=None, specialists_dir=None):
    """Findet eine Recipe-file in den Quell-Verzeichnissen."""
    if main_dir is None:
        main_dir = REPO_MAIN
    if specialists_dir is None:
        specialists_dir = REPO_SPECIALISTS

    for candidate in [
        main_dir / filename,
        specialists_dir / filename,
        MAS_RECIPE_DIR / filename,
    ]:
        if candidate.exists():
            return candidate
    return None


def resolve_spec(spec):
    """Resolves a specification into a list of filenames."""
    filenames = []
    warnings = []

    if spec == "minimal":
        for cat in ["starter", "mas-engineer", "core"]:
            filenames.extend(CATEGORIES[cat]["files"])
    elif spec == "all":
        for cat in CATEGORIES:
            if CATEGORIES[cat].get("files"):
                filenames.extend(CATEGORIES[cat]["files"])
    elif spec in CATEGORIES and CATEGORIES[spec].get("files"):
        filenames.extend(CATEGORIES[spec]["files"])
    elif "," in spec:
        for part in spec.split(","):
            sub, subw = resolve_spec(part.strip())
            filenames.extend(sub)
            warnings.extend(subw)
    elif spec.endswith(".yaml"):
        filenames.append(spec)
    else:
        warnings.append(f"Unbekannte Spezifikation: {spec}")

    seen = set()
    unique = []
    for f in filenames:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return unique, warnings


def is_visible(filename):
    """True if Recipe im Top-Level landen should."""
    return filename in VISIBLE_RECIPES


# ─── BEFEHLE ───

def cmd_install(spec):
    """Installiert Recipes in die Goose-Installation."""
    filenames, warnings = resolve_spec(spec)
    for w in warnings:
        print(f"⚠️  {w}")

    if not filenames:
        print("❌ No files to the Installieren.")
        print("   Available: minimal, core, specialists, sub-agents, all, <file>")
        sys.exit(1)

    n_ok, n_upd, n_skip = 0, 0, 0

    for filename in filenames:
        src = find_recipe_file(filename)
        if not src:
            print(f"❌ {filename}: Source not found")
            n_skip += 1
            continue

        visible = is_visible(filename)
        dest_dir = GOOSE_RECIPES if visible else FRAMEWORK_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)
        dst = dest_dir / filename
        existed = dst.exists()

        shutil.copy2(src, dst)

        if filename not in KEEP_SLASH:
            text = dst.read_text()
            new_text = re.sub(r"^slash_command:.*\n", "", text, flags=re.MULTILINE)
            if new_text != text:
                dst.write_text(new_text)

        loc = "recipes/" if visible else "recipes/_framework/"
        if existed:
            print(f"↻  {filename} → {loc} (updated)")
            n_upd += 1
        else:
            print(f"✅ {filename} → {loc}")
            n_ok += 1

    print(f"\n📦 {n_ok} installiert, {n_upd} updated, {n_skip} skipped")


def cmd_uninstall(spec):
    """Removed Recipes from der Goose-Installation."""
    filenames, _ = resolve_spec(spec)
    n_ok, n_nf = 0, 0

    for filename in filenames:
        found = False
        for search in [GOOSE_RECIPES, FRAMEWORK_DIR]:
            tgt = search / filename
            if tgt.exists():
                tgt.unlink()
                print(f"🗑️  {filename}")
                n_ok += 1
                found = True
                break
        if not found:
            print(f"⚠️  {filename}: not installiert")
            n_nf += 1

    print(f"\n📦 {n_ok} removed, {n_nf} not found")


def cmd_list():
    """Zeigt all installierten Recipes."""
    vis = sorted(GOOSE_RECIPES.glob("*.yaml"))
    hid = sorted(FRAMEWORK_DIR.glob("*.yaml")) if FRAMEWORK_DIR.exists() else []

    print("\n📋 SICHTBARE REZEPTE (recipes/):")
    if vis:
        for f in vis:
            try:
                sc = re.search(r"^slash_command:\s*(\S+)", f.read_text(), re.MULTILINE)
                sl = sc.group(1) if sc else "—"
            except:
                sl = "?"
            print(f"  {f.name:<45} slash: {sl}")
    else:
        print("  (no)")

    print(f"\n📋 FRAMEWORK-REZEPTE (recipes/_framework/):")
    if hid:
        for f in hid:
            print(f"  {f.name}")
        print(f"\n  → {len(hid)} Rezepte")
    else:
        print("  (no)")

    print(f"\n📊 Total: {len(vis)} sichtbar + {len(hid)} Framework = {len(vis) + len(hid)} installiert")


def cmd_cleanup_hidden():
    """Removed ALL .yaml-files aus beforeigem install_framework.py Lauf."""
    n = 0
    for f in sorted(GOOSE_RECIPES.glob(".*.yaml")):
        f.unlink()
        print(f"🧹 {f.name} → deleted")
        n += 1
    if n == 0:
        print("🧹 No .yaml-files found.")
    else:
        print(f"\n🧹 {n} old .yaml-files cleaned")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    spec = sys.argv[2] if len(sys.argv) > 2 else ""

    if cmd == "--install":
        if not spec:
            print("❌ No Spezifikation. z.B. --install minimal")
            sys.exit(1)
        cmd_install(spec)
    elif cmd == "--uninstall":
        if not spec:
            print("❌ No Spezifikation.")
            sys.exit(1)
        cmd_uninstall(spec)
    elif cmd == "--list":
        cmd_list()
    elif cmd == "--cleanup-hidden":
        cmd_cleanup_hidden()
    else:
        print(f"❌ Unbekannt: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
