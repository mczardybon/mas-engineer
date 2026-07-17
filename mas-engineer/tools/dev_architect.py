#!/usr/bin/env python3
"""
dev_architect.py — 🧠 The brain of the dev-mas-engineer
=====================================================
Version: 1.0.0
Author: dev-mas-engineer (autonomous)

Detects patterns, relationships and gaps in the framework.
Uses raw data from dev_observer.py (or scans itself).
Adds NO framework knowledge (no SOTs, protocols, constitutions).

ONLY uses structural observations:
  - Which files exist?
  - What names do they have?
  - What slash-commands do they have?
  - How are they arranged?

USAGE:
    python3 dev_architect.py --analyze         # Complete architecture analysis
    python3 dev_architect.py --quick            # Only core knowledge
    python3 dev_architect.py --suggest          # Generate improvement suggestions
    python3 dev_architect.py --impact <change> # Impact analysis for a change
"""

import sys
from pathlib import Path

# Use dev_observer for raw data
OBSERVER_DIR = Path(__file__).parent / "dev_observer.py"
sys.path.insert(0, str(Path(__file__).parent))

import importlib.util
spec = importlib.util.spec_from_file_location("dev_observer", OBSERVER_DIR)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


# ─────────────────────────────────────────────────────────
# CORE ANALYSIS
# ─────────────────────────────────────────────────────────

def analyze(scanner: "observer.Scanner") -> str:
    """Complete architecture analysis."""
    scanner._collect()
    
    out = []
    out.append("#" * 60)
    out.append("🧠 ARCHITECTURE ANALYSIS")
    out.append(f"🕐 {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out.append("#" * 60)
    out.append("")
    
    # 1. agents-LANDSCAPE
    out.append("👥 agents-LANDSCAPE")
    out.append("━" * 60)
    
    with_slash = sorted([y for y in scanner.yamls if y.has_slash], key=lambda x: x.slash_cmd)
    without_slash = [y for y in scanner.yamls if not y.has_slash]
    specialists = [y for y in scanner.yamls if "specialist_" in y.rel_path]
    subs = [y for y in scanner.yamls if y.rel_path.startswith("sub_") or "/sub_" in y.rel_path]
    
    out.append(f"  Total: {len(scanner.yamls)} YAML-agents")
    out.append("")
    out.append(f"  🎯 Mit Slash-Command ({len(with_slash)}):")
    for y in with_slash:
        out.append(f"     /{y.slash_cmd:20s} → {Path(y.rel_path).name}")
    
    out.append("")
    out.append(f"  🔹 Ohne Slash-Command ({len(without_slash)}):")
    out.append(f"     → Werden von anderen agents dispatcht (no direkter call)")
    out.append(f"     → {len(specialists)} Spezialistn, {len(subs)} Sub-agents")
    out.append("")
    
    # 2. LAYER-structure (aus Namen und Anordnung abgeleitet)
    out.append("📐 LAYER-structure (abgeleitet)")
    out.append("━" * 60)
    
    # Find Hauptagents
    starter = [y for y in with_slash if "starter" in y.rel_path.lower()]
    planner = [y for y in with_slash if "planner" in y.rel_path.lower() and "sub_" not in y.rel_path]
    executor = [y for y in with_slash if "executor" in y.rel_path.lower() and "sub_" not in y.rel_path]
    controller = [y for y in with_slash if "controller" in y.rel_path.lower()]
    remainder_slash = [y for y in with_slash if y not in starter + planner + executor + controller]
    
    if starter:
        out.append(f"  🟢 Layer Interface:     /{starter[0].slash_cmd}  ({Path(starter[0].rel_path).name})")
        out.append("       Einziger User-Kontakt. Delegiert alls.")
    if planner:
        out.append(f"  🔵 Layer Planung:       /{planner[0].slash_cmd}  ({Path(planner[0].rel_path).name})")
        out.append("       Interne Planung. No User-Kontakt.")
    if executor:
        out.append(f"  🟣 Layer Execution:    /{executor[0].slash_cmd}  ({Path(executor[0].rel_path).name})")
        out.append("       Runs Tasks aus. Dispatched Spezialistn.")
    if controller:
        out.append(f"  🔴 Layer monitoring:   /{controller[0].slash_cmd}  ({Path(controller[0].rel_path).name})")
        out.append("       Beobachtet the framework. Runs in loop.")
    if remainder_slash:
        out.append(f"  ⚪ Weitere:             {', '.join('/' + y.slash_cmd for y in remainder_slash)}")
    
    # Kommunikationskette ableiten
    names_lower = [y.rel_path.lower() for y in with_slash]
    chain_parts = []
    if any("starter" in n for n in names_lower):
        chain_parts.append("User")
        chain_parts.append("Starter")
    if any("planner" in n for n in names_lower):
        chain_parts.append("Planner")
    if any("executor" in n for n in names_lower):
        chain_parts.append("Executor")
    if specialists:
        chain_parts.append(f"{len(specialists)} Specialists")
    
    out.append("")
    out.append(f"  🔗 Kommunikationskette (abgeleitet):")
    out.append(f"     {' → '.join(chain_parts)}")
    out.append("")
    
    # 3. KATEGORIEN (aus Filenamen abgeleitet)
    out.append("📂 KATEGORIEN (aus Namen)")
    out.append("━" * 60)
    
    cats = {
        "A: Core Dev": [], "B: Architecture": [], "C: Security": [],
        "D: Data & AI": [], "E: Ops & Infra": [], "F: Spezial": [],
        "Sub-agents": [], "Other": []
    }
    
    # Only Spezialistn categorize
    for y in specialists:
        name = Path(y.rel_path).stem.replace("specialist_", "")
        # Grobe Categorization basierend auf Name (NO framework-Wissen)
        if name in ("backend", "frontend", "test_engineer", "reviewer", "quality_manager", "refactoring", "software_engineer"):
            cats["A: Core Dev"].append(name)
        elif name in ("software_architekt", "system_architekt", "ddd_architect", "api_designer", "api_gateway", "ux_designer", "event_driven"):
            cats["B: Architecture"].append(name)
        elif name in ("security", "auth", "devsecops", "legal_compliance"):
            cats["C: Security"].append(name)
        elif name in ("database", "data_engineer", "data_governance", "data_scientist", "ai_engineer", "ml_engineer", "search_engineer"):
            cats["D: Data & AI"].append(name)
        elif name in ("devops", "cloud_architect", "observability", "sre", "platform_engineer", "cost_optimizer", "chaos_engineer", "incident_response", "mobile_ci", "dependency_manager", "release_manager", "migration"):
            cats["E: Ops & Infra"].append(name)
        else:
            cats["F: Spezial"].append(name)
    
    for cat, names in cats.items():
        if names:
            out.append(f"  {cat}  ({len(names)})")
            for n in sorted(names):
                out.append(f"    - {n}")
    out.append("")
    
    # 4. EINSTIEGSPUNKTE
    out.append("🚪 EINSTIEGSPUNKTE (User)")
    out.append("━" * 60)
    for y in with_slash:
        out.append(f"  /{y.slash_cmd:20s} → {y.rel_path}")
    out.append("")
    
    # 5. TESTS
    test_files = [f for f in scanner.files if "test" in f.rel_path.lower() and f.is_py]
    if test_files:
        out.append(f"🧪 TESTS ({len(test_files)})")
        out.append("━" * 60)
        for f in sorted(test_files, key=lambda x: x.rel_path):
            out.append(f"  {f.rel_path} ({f.lines} Tests)")
        out.append("")
    
    # 6. CONFIGURATION
    configs = [f for f in scanner.files if f.name in ("config.yaml", "pyproject.toml")]
    if configs:
        out.append("⚙️ CONFIGURATION")
        out.append("━" * 60)
        for f in configs:
            out.append(f"  {f.rel_path} ({f.lines} lines)")
        out.append("")
    
    # 7. BEOBWARNINGEN (only structureell!)
    out.append("🔍 BEOBWARNINGEN")
    out.append("━" * 60)
    
    observations = []
    
    # Einstiegs-Punkt
    if starter:
        observations.append(f"  • Einstieg ist /{starter[0].slash_cmd} → alls andere will dispatcht")
    
    # Number Spezialistn
    if specialists:
        observations.append(f"  • {len(specialists)} Spezialistn decken many Domains ab")
    
    # Controller runs long
    for y in controller:
        observations.append(f"  • /{y.slash_cmd} runs in loop (6000 max_steps)")
    
    # agents ohne / (dispatcht)
    observations.append(f"  • {len(without_slash)} agents ohne Slash-Command (will dispatcht)")
    
    # Tests
    if not test_files:
        observations.append("  • No Test-files found")
    
    # settings
    ohne_settings = [y for y in scanner.yamls if not y.has_settings]
    if ohne_settings:
        observations.append(f"  • {len(ohne_settings)} YAMLs ohne settings-Block")
    
    for obs in observations:
        out.append(obs)
    out.append("")
    
    return "\n".join(out)


def quick_analyze(scanner: "observer.Scanner") -> str:
    """Only Kern-Erknowledgese."""
    scanner._collect()
    
    with_slash = len([y for y in scanner.yamls if y.has_slash])
    specialists = len([y for y in scanner.yamls if "specialist_" in y.rel_path])
    subs = len([y for y in scanner.yamls if y.rel_path.startswith("sub_") or "/sub_" in y.rel_path])
    
    out = []
    out.append("🧠 KERN-ERKENNTNISSE")
    out.append("━" * 40)
    out.append(f"  {len(scanner.yamls)} agents: {with_slash} Main- + {specialists} Spezialistn + {subs} Sub")
    out.append(f"  {len(scanner.files)} files total")
    out.append(f"  Communication: User → Starter → Planner → Executor → Specialists")
    out.append(f"  Controller monitors the framework in loop")
    
    return "\n".join(out)


def suggest(scanner: "observer.Scanner") -> str:
    """Improvement suggestions generate (NUR aus structure)."""
    scanner._collect()
    
    out = []
    out.append("💡 IMPROVEMENT SUGGESTIONS")
    out.append("━" * 60)
    out.append("  (Basieren NUR auf structureellen Beobachtungen)")
    out.append("")
    
    suggestions = []
    
    # 1. max_steps compare (main agents)
    main_yamls = [y for y in scanner.yamls if ("planner" in y.rel_path.lower() or "executor" in y.rel_path.lower() or "starter" in y.rel_path.lower() or "controller" in y.rel_path.lower()) and "sub_" not in y.rel_path]
    
    # We cannot read max_steps directly (no YAML parsing in architect)
    # Stattdessen: lineszahlen als Indikator
    for y in main_yamls:
        name = Path(y.rel_path).stem
        if y.lines_total > 500:
            suggestions.append(f"  • {name}.yaml: {y.lines_total} lines (large)")
    
    # 2. Spezialistn ohne settings
    for y in scanner.yamls:
        if "specialist_" in y.rel_path and not y.has_settings:
            suggestions.append(f"  • {Path(y.rel_path).name}: no settings-Block")
    
    # 3. agents mit very shorten Instructions
    for y in scanner.yamls:
        if y.instr_lines > 0 and y.instr_lines < 10:
            suggestions.append(f"  • {Path(y.rel_path).name}: only {y.instr_lines} Instructions-lines")
    
    # 4. Very large Instructions
    for y in scanner.yamls:
        if y.instr_lines > 500:
            suggestions.append(f"  • {Path(y.rel_path).name}: {y.instr_lines} Instructions-lines (very large)")
    
    if not suggestions:
        suggestions.append("  • No offensichtlichen Anomalies.")
    
    out.extend(suggestions)
    out.append("")
    
    return "\n".join(out)


def impact_analysis(scanner: "observer.Scanner", change_desc: str) -> str:
    """Impact analysis: What would be affected by a change?"""
    scanner._collect()
    
    out = []
    out.append(f"📐 IMPACT-ANALYSE")
    out.append("━" * 60)
    out.append(f"  Change: {change_desc}")
    out.append("")
    
    # Simple Analyse basierend auf Stichworten
    keywords = change_desc.lower().split()
    
    relevant = []
    for y in scanner.yamls:
        rel = y.rel_path.lower()
        for kw in keywords:
            if kw in rel and len(kw) > 3:
                relevant.append(y)
                break
    
    if relevant:
        out.append(f"  Possibly affected ({len(relevant)}):")
        for y in sorted(relevant, key=lambda x: x.rel_path):
            out.append(f"    • {y.rel_path}")
    else:
        out.append("  (No direkten files erkannt)")
    out.append("")
    
    out.append("  Note: Only structureelle Analyse. Der User entscheidet.")
    
    return "\n".join(out)


def generate_blueprint(feature_name):
    """Generates a blueprint for a newen Sub-agents mit Best-Practice-Integration."""
    import yaml, re
    
    name = feature_name.upper().replace(" ", "-")
    name_lower = name.lower()
    description = feature_name
    emoji = "🤖"
    
    # Best Practices load (if present)
    bp_path = Path(__file__).parent.parent / ".state" / "best-practices.yaml"
    bp = {}
    if bp_path.exists():
        try:
            with open(bp_path) as f:
                bp = yaml.safe_load(f) or {}
        except Exception:
            bp = {}
    
    prompt_note = "Default"
    timeout_note = "600"
    steps_note = "100"
    bp_number = "no"
    
    if bp and "best_practices" in bp:
        bp_number = str(sum(len(items) for items in bp["best_practices"].values()))
        for cat, practices in bp["best_practices"].items():
            for p in practices:
                if p["id"] == "BP-P-001":
                    prompt_note = "✅ (v1.0.0) + ⛔ automatically"
                elif p["id"] == "BP-S-001":
                    timeout_note = f"✅ {p['check_value']} (Sweet-Spot)"
                elif p["id"] == "BP-S-002":
                    steps_note = f"✅ {p['check_value']} (Sweet-Spot)"
    
    blueprint = f"""
╔══════════════════════════════════════════════════════════════╗
║  BAUPPLAN: newer Sub-Agent — {name}                        ║
║  Generates aus {bp_number} Best-Practices                 ║
╚══════════════════════════════════════════════════════════════╝

📋 BESCHREIBUNG: {description}

=== PHASE 1 — template copyren ===
  mkdir -p recipe/sub/
  cp recipe/template/agent_template.yaml recipe/sub/sub_mas-{name_lower}.yaml

=== PHASE 2 — Platzholder replace ===
  sed -i 's/{{{{NAME}}}}/{name}/g' recipe/sub/sub_mas-{name_lower}.yaml
  sed -i 's/{{{{name}}}}/{name_lower}/g' recipe/sub/sub_mas-{name_lower}.yaml
  sed -i 's/{{{{EMOJI}}}}/{emoji}/g' recipe/sub/sub_mas-{name_lower}.yaml
  sed -i 's/{{{{BESCHREIBUNG}}}}/{description}/g' recipe/sub/sub_mas-{name_lower}.yaml
  sed -i 's/{{{{TASK}}}}/{description}/g' recipe/sub/sub_mas-{name_lower}.yaml

=== PHASE 3 — Best-Practice-Optimierung ===
  prompt:     {prompt_note}
  timeout:    {timeout_note}
  max_steps:  {steps_note}
  ⛔ NOE hardcodierten Pathe (BP-T-001)
  ⛔ str.replace() mit count=1 (BP-T-002)
  ⛔ Backup vor erster Change (BP-R-003)

=== PHASE 4 — validation ===
  python3 tools/dev_editor.py \\
    --validate recipe/sub/sub_mas-{name_lower}.yaml
  
  Expected: ✅ 25/25 bestanden, 0 ❌

=== PHASE 5 — Registration ===
  sub_recipes-entry in recipe/dev-mas-engineer.yaml add:
  
    - name: \"sub_mas-{name_lower}\"
      path: \"./sub/sub_mas-{name_lower}.yaml\"
      description: \"{emoji} {description}\"
  
  update.sh --mas → Installation in Goose

=== RISIKO-EVALUATION ===
  Template + Best Practices → Niedriges Risiko
  Estimated Duration: ~5 Minuten
"""
    return blueprint


def main():
    import argparse
    parser = argparse.ArgumentParser(description="dev_architect.py — Architecture-Analyse")
    parser.add_argument("--analyze", action="store_true", help="Komplette Analyse")
    parser.add_argument("--quick", action="store_true", help="Only Kern-Erknowledgese")
    parser.add_argument("--suggest", action="store_true", help="Improvement suggestions")
    parser.add_argument("--impact", type=str, help="Impact-Analyse for Change")
    parser.add_argument("--blueprint", type=str, help="blueprint for newen agents generate")
    parser.add_argument("--apply-best-practices", action="store_true", help="Best Practices anwenden")
    parser.add_argument("--agent-path", type=str, default=str(observer.AGENT_DIR))
    
    args = parser.parse_known_args()[0]
    
    agent_path = Path(args.agent_path).resolve()
    scanner = observer.Scanner(agent_path)
    
    if args.quick:
        print(quick_analyze(scanner))
    elif args.suggest:
        print(suggest(scanner))
    elif args.impact:
        print(impact_analysis(scanner, args.impact))
    elif args.blueprint:
        feature = args.blueprint
        if args.apply_best_practices:
            print(generate_blueprint(feature))
        else:
            print(generate_blueprint(feature))
    else:
        print(analyze(scanner))


if __name__ == "__main__":
    main()
