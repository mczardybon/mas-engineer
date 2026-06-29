#!/usr/bin/env python3
"""
dev_template_generator.py v2.0.0 — Generates & refreshed Agent-YAMLs aus SOT + Best-Practices + Improvement-Plan

Sources:
  1. .state/workflows.yaml → configs.mas-self (restrictions, enforcement, recovery, signals)
  2. .state/best-practices.yaml → 27 auto_apply Rulen
  3. .state/improvement-plan.json → offene Verbetterungen
  4. recipe/template/agent_template.yaml → Reaelseruktur

Modes:
  --create     Agent new create (Name + Task + Typ → YAML + SOT-entry)
  --refresh    Check existing agent against target + fill gaps
  --refresh-all All 39 Sub-Agenten check

Optionen:
  --name NAME      Agenten-Name (z.B. log-analyzer)
  --emoji EMOJI    Emoji (z.B. 📊)
  --task "TEXT"    Kernaufgabe
  --type sub|voll  Agent-Typ (Default: sub)
  --agent NAME     Only thesen Agent refreshen
  --dry-run        Only show, nothing change
  --diff           Unterschiede anshow
  --json           Maschinenlesbare Output
  --workspace PATH Workspace (Default: CWD)
"""
import argparse, json, os, sys, re, copy, textwrap
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

try:
    import yaml
except ImportError:
    print("❌ Error: pyyaml not installiert. pip3 install pyyaml")
    sys.exit(1)

# ──────────────────────────────────────────────
# KONSTANTEN
# ──────────────────────────────────────────────
CORE_KEYS = ["version", "title", "description", "instructions", "prompt", "settings"]
SOT_RESTRICTION_KEYS = [
    "r01_confirmation", "r02_bestand", "r04_general_improver", "r05_auto_commit",
    "r06_sub_agent", "r07_signal", "r08_token", "r09_domain", "r10_coronashield",
    "verbote", "verstoesse"
]
DEFAULT_TIMEOUT = 600    # BP-S-001: Sweet-Spot
DEFAULT_MAX_STEPS = 100  # BP-S-002: 20-80% Auslastung
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "filtered/deepseek/deepseek-chat"

# ──────────────────────────────────────────────
# QUELLEN-LADER
# ──────────────────────────────────────────────

def load_yaml(path: str) -> Any:
    """Load YAML-file. Bei Error: print + return {}."""
    full = os.path.join(os.getcwd(), path) if not os.path.isabs(path) else path
    if not os.path.exists(full):
        print(f"  ⚠️  Source not found: {path}")
        return {}
    try:
        with open(full, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"  ⚠️  YAML-Error in {path}: {e}")
        return {}

def load_json(path: str) -> Any:
    """Load JSON-file. Bei Error: print + return {} oder []."""
    full = os.path.join(os.getcwd(), path) if not os.path.isabs(path) else path
    if not os.path.exists(full):
        print(f"  ⚠️  Source not found: {path}")
        return {} if path.endswith(".json") else ""
    try:
        with open(full, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️  JSON-Error in {path}: {e}")
        return {}

def load_text(path: str) -> str:
    """Load Text-file. Bei Error: return ''."""
    full = os.path.join(os.getcwd(), path) if not os.path.isabs(path) else path
    if not os.path.exists(full):
        print(f"  ⚠️  Source not found: {path}")
        return ""
    try:
        with open(full, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"  ⚠️  Read-Error in {path}: {e}")
        return ""

def load_all_sources(workspace: str) -> Dict:
    """
    Loads ALL Sources in a Dict.
    Keys: sot, bp, improvement, template, schema
    """
    base = workspace or os.getcwd()
    
    # SOT
    raw_sot = load_yaml(os.path.join(base, ".state/workflows.yaml"))
    sot = raw_sot.get("configs", {}).get("mas-self", {})
    
    # Best-Practices
    bp = load_yaml(os.path.join(base, ".state/best-practices.yaml"))
    
    # Improvement-Plan
    improvement = load_json(os.path.join(base, ".state/improvement-plan.json"))
    plan_items = improvement.get("plan", []) if isinstance(improvement, dict) else []
    
    # Template
    template = load_text(os.path.join(base, "recipe/template/agent_template.yaml"))
    
    # Schema
    schema = load_yaml(os.path.join(base, ".state/templates/agent_schema.yaml"))
    
    sources = {
        "sot": sot,
        "bp": bp,
        "improvement": plan_items,
        "template": template,
        "schema": schema
    }
    
    # Debug: Show which Sources loaded were
    loaded = [k for k, v in sources.items() if (isinstance(v, dict) and v) or (isinstance(v, str) and v) or (isinstance(v, list) and v)]
    missing = [k for k, v in sources.items() if not v]
    if missing:
        print(f"  ℹ️  Sources loaded: {', '.join(loaded)}")
        print(f"  ⚠️  Fehlend/Leer: {', '.join(missing)}")
    
    return sources

# ──────────────────────────────────────────────
# REGEL-PAKET BAUER
# ──────────────────────────────────────────────

def _format_dict_block(data: Dict, prefix: str = "# ", indent: str = "") -> str:
    """Formatiert a Dict als YAML-Kommentarblock."""
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{indent}{prefix}{key}:")
            for sk, sv in value.items():
                s = str(sv)[:120]
                if "\n" in s:
                    s = s.split("\n")[0] + "..."
                lines.append(f"{indent}  {prefix}{sk}: {s}")
        elif isinstance(value, list):
            lines.append(f"{indent}{prefix}{key}:")
            for item in value[:5]:
                s = str(item)[:100]
                lines.append(f"{indent}  {prefix}- {s}")
            if len(value) > 5:
                lines.append(f"{indent}  {prefix}... +{len(value)-5} mehr")
        else:
            lines.append(f"{indent}{prefix}{key}: {str(value)[:120]}")
    return "\n".join(lines)

def _format_bp_rules(bp: Dict, section_keys: List[str]) -> str:
    """Extrahiert auto_apply Rulen aus determinesen BP-Sektionen als Textblock."""
    lines = []
    for section_key in section_keys:
        # Supports nested keys (z.B. "best_practices.prompt")
        parts = section_key.split(".")
        data = bp
        for part in parts:
            if isinstance(data, dict):
                data = data.get(part, {})
            else:
                data = {}
        
        rules = data if isinstance(data, list) else []
        for rule in rules:
            if isinstance(rule, dict) and rule.get("auto_apply"):
                rid = rule.get("id", "?")
                rtext = rule.get("rule", "")[:150]
                lines.append(f"  • [{rid}] {rtext}")
    
    return "\n".join(lines)

def build_rule_package(sources: Dict) -> Dict:
    """
    Baut a Paket aus alln relevanten Rulen.
    """
    sot = sources.get("sot", {})
    bp = sources.get("bp", {})
    improvement = sources.get("improvement", [])
    
    # ── SOT Restrictions ──
    restrictions_raw = sot.get("restrictions", {})
    sot_restriction_lines = []
    for key in SOT_RESTRICTION_KEYS:
        r = restrictions_raw.get(key)
        if not r:
            continue
        if isinstance(r, dict):
            level = r.get("level", "?")
            desc = r.get("description", str(r))[:100]
            sot_restriction_lines.append(f"  ⛔ [{key}] ({level}) {desc}")
        elif isinstance(r, list):
            for item in r:
                sot_restriction_lines.append(f"  ⛔ {str(item)[:100]}")
    sot_restrictions = "\n".join(sot_restriction_lines)
    
    # ── SOT Enforcement ──
    enf = sot.get("enforcement", {})
    enf_lines = []
    for key, val in enf.items():
        if isinstance(val, dict):
            desc = val.get("beschreibung", val.get("ausexecuten", str(val)))[:100]
            enf_lines.append(f"  ⚙️ [{key}] {desc}")
        else:
            enf_lines.append(f"  ⚙️ [{key}] {str(val)[:100]}")
    sot_enforcement = "\n".join(enf_lines)
    
    # ── SOT Recovery ──
    rec = sot.get("recovery", {})
    rec_lines = []
    for level, details in rec.items():
        if isinstance(details, dict):
            for sk, sv in details.items():
                if isinstance(sv, dict):
                    desc = sv.get("beschreibung", str(sv))[:80]
                    rec_lines.append(f"  🛟 {sk}: {desc}")
    sot_recovery = "\n".join(rec_lines)
    
    # ── SOT Signals ──
    sig = sot.get("signals", {})
    sig_lines = []
    for sk, sv in sig.items():
        if isinstance(sv, list):
            for item in sv:
                if isinstance(item, dict):
                    sig_lines.append(f"  📡 {item.get('signal', '?')}: {item.get('nach', item.get('bei', ''))[:80]}")
        else:
            sig_lines.append(f"  {sk}: {str(sv)[:80]}")
    sot_signals = "\n".join(sig_lines)
    
    # ── BP Autonomie ──
    bp_autonomie = _format_bp_rules(bp, ["autonomie"])
    
    # ── BP Separation ──
    bp_separation = _format_bp_rules(bp, ["separation"])
    
    # ── BP Structure ──
    bp_structure = _format_bp_rules(bp, ["best_practices.structure"])
    
    # ── BP Prompt ──
    bp_prompt = _format_bp_rules(bp, ["best_practices.prompt", "prompt"])
    
    # ── BP Settings ──
    bp_settings = _format_bp_rules(bp, ["best_practices.settings", "settings"])
    
    # ── BP Recovery ──
    bp_recovery_rules = _format_bp_rules(bp, ["recovery"])
    
    # ── Improvement Notes ──
    imp_lines = []
    for item in improvement:
        fid = item.get("id", "?")
        field = item.get("field", "?")[:60]
        risk = item.get("risk", "?")
        imp_lines.append(f"  📋 [{fid}] {field} ({risk})")
    improvement_notes = "\n".join(imp_lines)
    
    # ── Default Settings ──
    standard_settings = {
        "timeout": DEFAULT_TIMEOUT,
        "max_steps": DEFAULT_MAX_STEPS,
        "goose_provider": DEFAULT_PROVIDER,
        "goose_model": DEFAULT_MODEL
    }
    
    return {
        "sot_restrictions": sot_restrictions or "# No SOT-Restrictions defines",
        "sot_enforcement": sot_enforcement or "# No SOT-Enforcement defines",
        "sot_recovery": sot_recovery or "# No SOT-Recovery defines",
        "sot_signals": sot_signals or "# No SOT-Signals defines",
        "bp_autonomie": bp_autonomie or "# No BP-Autonomie-Rulen",
        "bp_separation": bp_separation or "# No BP-Separation-Rulen",
        "bp_structure": bp_structure or "# No BP-Structure-Rulen",
        "bp_prompt": bp_prompt or "# No BP-Prompt-Rulen",
        "bp_settings": bp_settings or "# No BP-Settings-Rulen",
        "bp_recovery": bp_recovery_rules or "# No BP-Recovery-Rulen",
        "improvement_notes": improvement_notes or "# No Improvement-Notes",
        "standard_settings": standard_settings
    }

# ──────────────────────────────────────────────
# TEMPLATE-FILLER
# ──────────────────────────────────────────────

def _shorten(text: str, maxlen: int = 80) -> str:
    """Truncates text to maxlen characters."""
    if len(text) <= maxlen:
        return text
    return text[:maxlen-3] + "..."

def fill_template(sources: Dict, rules: Dict, name: str, emoji: str, task: str, agent_type: str) -> str:
    """
    Fills agent_template.yaml mit statischen + dynamischen Platzhaltern.
    """
    template = sources.get("template", "")
    if not template:
        print("  ⚠️  No Template loaded. Generiere Minimumstruktur.")
        template = """version: 1.0.0
title: "{EMOJI} SUB-MAS-{NAME} — {TASK}"
description: 'v1.0.0 | MAS-intern: {TASK}'
instructions: |
  # sub_mas-{name} — {EMOJI} {Titel}
  {TASK}
  {SOT_RESTRICTIONS}
  {BP_AUTONOMIE}
prompt: '{EMOJI} {NAME} (v1.0.0)
⛔ NUR {TASK}
{SOT_RESTRICTIONS}'
settings:
  timeout: 600
  max_steps: 100
  goose_provider: openai
  goose_model: filtered/deepseek/deepseek-chat"""

    titel = f"sub_mas-{name} — {_shorten(task, 60)}"
    
    # Statische Platzhalter
    replacements = {
        "{NAME}": name.upper(),
        "{name}": name.lower() if name else name,
        "{EMOJI}": emoji,
        "{TASK}": task,
        "{TASK}": task,
        "{BESCHREIBUNG}": _shorten(task, 80),
        "{Titel}": titel,
    }
    
    # Dynamische Platzhalter aus rules
    dynamic_replacements = {
        "{SOT_RESTRICTIONS}": rules.get("sot_restrictions", ""),
        "{SOT_ENFORCEMENT}": rules.get("sot_enforcement", ""),
        "{SOT_RECOVERY}": rules.get("sot_recovery", ""),
        "{SOT_SIGNALS}": rules.get("sot_signals", ""),
        "{BP_AUTONOMIE}": rules.get("bp_autonomie", ""),
        "{BP_SEPARATION}": rules.get("bp_separation", ""),
        "{BP_STRUCTURE}": rules.get("bp_structure", ""),
        "{BP_PROMPT}": rules.get("bp_prompt", ""),
        "{BP_SETTINGS}": rules.get("bp_settings", ""),
        "{BP_RECOVERY}": rules.get("bp_recovery", ""),
        "{IMPROVEMENT_NOTES}": rules.get("improvement_notes", ""),
    }
    replacements.update(dynamic_replacements)
    
    result = template
    unreplaced = []
    
    for placeholder, value in replacements.items():
        if placeholder in result:
            result = result.replace(placeholder, value)
        else:
            unreplaced.append(placeholder)
    
    # Nicht-replacese Platzhalter (aus Template, not in replacements?) 
    # -> Als leere String replace
    all_found = re.findall(r"\{[A-Z_]+\}", result)
    for ph in all_found:
        if ph not in replacements:
            unreplaced.append(ph)
            result = result.replace(ph, "")
    
    # Aufraeumen: Leerzeilen mit only Whitespace remove (max 1 Durchlauf)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    
    if unreplaced:
        print(f"  ℹ️  Nicht-replacese Platzhalter: {', '.join(unreplaced)}")
    
    return result

# ──────────────────────────────────────────────
# YAML-BAUER
# ──────────────────────────────────────────────

def build_yaml(filled: str, rules: Dict, name: str, emoji: str, task: str) -> Dict:
    """
    Baut die finale YAML-Struktur from dem filled Template.
    """
    # Prompt generate (BP-P-001/002/003 konform)
    scope = task.split()[0].lower() if task.split() else "arbeiten"
    prompt_text = (
        f"{emoji} {name.upper()} (v1.0.0)\n"
        f"⛔ NUR {scope} — KEINE anderen Aktionen\n"
        f"⛔ KEINE Changeen ohne Confirmation\n"
        f"→ Siehe SOT: configs.mas-self.restrictions\n"
    )
    
    # Sichcreate prompt ≤ 500 Zeichen
    if len(prompt_text) > 500:
        prompt_text = prompt_text[:497] + "..."
    
    settings = dict(rules.get("standard_settings", {}))
    settings.setdefault("timeout", DEFAULT_TIMEOUT)
    settings.setdefault("max_steps", DEFAULT_MAX_STEPS)
    settings.setdefault("goose_provider", DEFAULT_PROVIDER)
    settings.setdefault("goose_model", DEFAULT_MODEL)
    
    yaml_data = {
        "version": "1.0.0",
        "title": f'{emoji} SUB-MAS-{name.upper()} — {_shorten(task, 50)}',
        "description": f"v1.0.0 | MAS-intern: {_shorten(task, 80)}",
        "instructions": filled,
        "prompt": prompt_text,
        "settings": settings
    }
    
    return yaml_data

# ──────────────────────────────────────────────
# YAML-SCHREIBER + SOT-UPDATE
# ──────────────────────────────────────────────

def _update_changes_json(workspace: str, action: str, description: str):
    """Fuegt a entry in changes.json hinzu."""
    changes_path = os.path.join(workspace, ".state/changes.json")
    entry = {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "action": action,
        "description": description
    }
    try:
        if os.path.exists(changes_path):
            with open(changes_path) as f:
                changes = json.load(f)
            if isinstance(changes, list):
                changes.append(entry)
            else:
                changes = [changes, entry]
        else:
            changes = [entry]
        with open(changes_path, "w") as f:
            json.dump(changes, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  ⚠️  changes.json Error: {e}")

def _add_sot_entry(workspace: str, name: str, task: str):
    """Fuegt Agent-entry in workflows.yaml → agents hinzu."""
    wf_path = os.path.join(workspace, ".state/workflows.yaml")
    if not os.path.exists(wf_path):
        print(f"  ⚠️  SOT not found: {wf_path}")
        return False
    try:
        with open(wf_path) as f:
            data = yaml.safe_load(f) or {}
        
        if "agents" not in data:
            print(f"  ⚠️  SOT has 'agents:' Sektion not")
            return False
        
        agent_key = name.lower().replace(" ", "_")
        if agent_key in data["agents"]:
            print(f"  ℹ️  Agent '{agent_key}' already in SOT present")
            return True
        
        # Finde passende Kategorie oder haenge an
        data["agents"][agent_key] = {
            "name": f"sub_mas-{agent_key}",
            "type": "sub",
            "task": task,
            "desc": f"Automatic generates aus Template-Generator"
        }
        
        with open(wf_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"  ✅ SOT-entry added: agents.{agent_key}")
        return True
    except Exception as e:
        print(f"  ⚠️  SOT-Update Error: {e}")
        return False

def _add_sub_recipes_entry(workspace: str, name: str):
    """Fuegt sub_recipes-entry in dev-mas-engineer.yaml hinzu."""
    main_path = os.path.join(workspace, "recipe/dev-mas-engineer.yaml")
    if not os.path.exists(main_path):
        print(f"  ⚠️  Main-Recipe not found: {main_path}")
        return False
    try:
        with open(main_path) as f:
            data = yaml.safe_load(f) or {}
        
        sub_key = f"sub_mas-{name.lower()}"
        if "sub_recipes" not in data:
            print(f"  ⚠️  Main-Recipe has 'sub_recipes:' not")
            return False
        
        existing = [s for s in data["sub_recipes"] if isinstance(s, str)]
        if sub_key in existing:
            print(f"  ℹ️  '{sub_key}' already in sub_recipes")
            return True
        
        data["sub_recipes"].append(sub_key)
        
        with open(main_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"  ✅ sub_recipes-entry added: {sub_key}")
        return True
    except Exception as e:
        print(f"  ⚠️  sub_recipes-Update Error: {e}")
        return False

def write_agent(yaml_data: Dict, name: str, agent_type: str, workspace: str, no_sot: bool = False) -> Dict:
    """
    Schreibt Agent-YAML + updated SOT.
    """
    base = workspace or os.getcwd()
    agent_key = name.lower().replace(" ", "_")
    sub_dir = os.path.join(base, "recipe/sub")
    os.makedirs(sub_dir, exist_ok=True)
    
    out_path = os.path.join(sub_dir, f"sub_mas-{agent_key}.yaml")
    
    # Backup falls present
    if os.path.exists(out_path):
        backup_dir = os.path.join(base, ".state/backups")
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"{ts}_{agent_key}.yaml")
        try:
            with open(out_path) as f_src, open(backup_path, "w") as f_dst:
                f_dst.write(f_src.read())
            print(f"  💾 Backup: {backup_path}")
        except Exception as e:
            print(f"  ⚠️  Backup-Error: {e}")
    
    # YAML write (mit sort_keys=False, allow_unicode=True)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except Exception as e:
        print(f"  ❌ Schreib-Error {out_path}: {e}")
        return {"file": str(out_path), "yaml_valid": False, "error": str(e)}
    
    # Validate
    try:
        with open(out_path) as f:
            validated = yaml.safe_load(f)
        for key in ["version", "title", "description", "instructions", "prompt", "settings"]:
            if key not in validated:
                print(f"  ⚠️  Fehlender Key in generierter YAML: '{key}'")
    except Exception as e:
        print(f"  ❌ YAML-Invalid: {e}")
        return {"file": str(out_path), "yaml_valid": False, "error": str(e)}
    
    print(f"  ✅ YAML written: {out_path}")
    
    # SOT-Update
    sot_ok = True
    if not no_sot:
        sot_ok = _add_sot_entry(base, agent_key, yaml_data.get("description", ""))
        sub_ok = _add_sub_recipes_entry(base, agent_key)
    else:
        sub_ok = True
    
    # Changes
    _update_changes_json(base, "CREATE", f"Neuer Agent: sub_mas-{agent_key}")
    
    return {
        "file": str(out_path),
        "yaml_valid": True,
        "sot_entry_added": sot_ok,
        "sub_recipes_updated": sub_ok
    }

# ──────────────────────────────────────────────
# REFRESH-LOGIK
# ──────────────────────────────────────────────

def _check_field(agent_data: Dict, key: str, expected: Any, label: str) -> Optional[Dict]:
    """Checks ob a Feld dem Erwartungswert entspricht."""
    actual = agent_data
    for part in key.split("."):
        if isinstance(actual, dict):
            actual = actual.get(part)
        else:
            actual = None
            break
    
    if actual != expected:
        return {
            "field": key,
            "problem": f"{label}: '{actual}' statt '{expected}'",
            "fix": f"Set {key} auf {expected}",
            "severity": "niedrig" if isinstance(expected, (int, float)) else "mittel"
        }
    return None

def _check_contains(agent_data: Dict, field: str, needle: str, label: str) -> Optional[Dict]:
    """Checks ob a Textfeld a String contains."""
    text = agent_data
    for part in field.split("."):
        if isinstance(text, dict):
            text = text.get(part, "")
        else:
            text = ""
            break
    
    if needle not in str(text):
        return {
            "field": field,
            "problem": f"{label}: Fehlt '{needle[:40]}'",
            "fix": f"Add '{needle[:60]}' in {field} ein",
            "severity": "hoch" if "⛔" in needle else "mittel"
        }
    return None

def refresh_agent(agent_name: str, dry_run: bool, workspace: str, sources: Optional[Dict] = None, rules: Optional[Dict] = None) -> Dict:
    """
    Checks a Agenten gegen SHOULD-State.
    """
    base = workspace or os.getcwd()
    agent_path = os.path.join(base, "recipe/sub", f"{agent_name}.yaml")
    
    if not os.path.exists(agent_path):
        return {"agent": agent_name, "status": "not_found", "issues": [{"field": "file", "problem": f"file not found: {agent_path}"}]}
    
    try:
        with open(agent_path) as f:
            agent_data = yaml.safe_load(f) or {}
    except Exception as e:
        return {"agent": agent_name, "status": "parse_error", "issues": [{"field": "file", "problem": f"YAML-Error: {e}"}]}
    
    issues = []
    
    # ── Settings-Checks ──
    chk = _check_field(agent_data, "settings.timeout", DEFAULT_TIMEOUT, "timeout")
    if chk: issues.append(chk)
    
    chk = _check_field(agent_data, "settings.max_steps", DEFAULT_MAX_STEPS, "max_steps")
    if chk: issues.append(chk)
    
    # ── Content-Checks ──
    chk = _check_contains(agent_data, "instructions", "SOT", "SOT-Referenz")
    if chk: issues.append(chk)
    
    chk = _check_contains(agent_data, "instructions", "AUTONOMIEMODUS", "Autonomiemodus")
    if chk: issues.append(chk)
    
    chk = _check_contains(agent_data, "instructions", "mas_result", "mas_result Output")
    if chk: issues.append(chk)
    
    chk = _check_contains(agent_data, "instructions", "Retry", "Retry-Logik")
    if chk: issues.append(chk)
    
    chk = _check_contains(agent_data, "instructions", "Edge Cases", "Edge Cases")
    if chk: issues.append(chk)
    
    chk = _check_contains(agent_data, "instructions", "Tool-Inventar", "Tool-Inventar")
    if chk: issues.append(chk)
    
    # ── Prompt-Checks ──
    prompt_text = agent_data.get("prompt", "")
    if len(prompt_text) > 500:
        issues.append({"field": "prompt", "problem": f"prompt zu long: {len(prompt_text)} > 500", "fix": "Kuerzen auf ≤500 Zeichen", "severity": "mittel"})
    
    if "⛔" not in prompt_text:
        issues.append({"field": "prompt", "problem": "prompt missing ⛔-Boundary", "fix": "⛔-Boundary hinzuaddn", "severity": "hoch"})
    
    if "(v1.0.0)" not in prompt_text:
        issues.append({"field": "prompt", "problem": "prompt missing Version (v1.0.0)", "fix": "Version hinzuaddn", "severity": "mittel"})
    
    # ── Title/Description-Checks ──
    title = agent_data.get("title", "")
    if "SUB-MAS" not in title and "sub_mas" not in title:
        issues.append({"field": "title", "problem": f"title ohne SUB-MAS-Prefix", "fix": "SUB-MAS- im Title", "severity": "mittel"})
    
    desc = agent_data.get("description", "")
    if not desc.startswith("v1.0.0"):
        issues.append({"field": "description", "problem": "description beginnt not mit v1.0.0", "fix": "v1.0.0 | ...", "severity": "niedrig"})
    
    # Status determine
    if not issues:
        status = "clean"
    elif dry_run:
        status = "issues"
    else:
        status = "fixed"
    
    # If not dry-run: Fixe die Issues
    if not dry_run and issues:
        print(f"  🔧 Fixe {len(issues)} Issues in {agent_name}...")
        # FIX: settings
        if "timeout" not in str(issues) or True:  # Always korrigieren
            if "settings" not in agent_data:
                agent_data["settings"] = {}
            if agent_data["settings"].get("timeout") != DEFAULT_TIMEOUT:
                agent_data["settings"]["timeout"] = DEFAULT_TIMEOUT
            if agent_data["settings"].get("max_steps") != DEFAULT_MAX_STEPS:
                agent_data["settings"]["max_steps"] = DEFAULT_MAX_STEPS
        
        # Backup + Write
        backup_path = os.path.join(base, ".state/backups", f"pre_refresh_{agent_name}.yaml")
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        try:
            with open(agent_path) as f_src, open(backup_path, "w") as f_dst:
                f_dst.write(f_src.read())
        except:
            pass
        
        with open(agent_path, "w", encoding="utf-8") as f:
            yaml.dump(agent_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        _update_changes_json(base, "REFRESH", f"Settings korrigiert in {agent_name}: timeout/max_steps auf Default")
        print(f"  ✅ {agent_name} gefixed")
    
    return {
        "agent": agent_name,
        "dry_run": dry_run,
        "status": status,
        "issues": issues,
        "issues_count": len(issues)
    }

def refresh_all(dry_run: bool, workspace: str) -> Dict:
    """
    Ruft refresh_agent() for all Sub-Agenten auf.
    """
    base = workspace or os.getcwd()
    sub_dir = os.path.join(base, "recipe/sub")
    
    if not os.path.exists(sub_dir):
        return {"total": 0, "error": f"Sub-Dir not found: {sub_dir}"}
    
    agents = sorted([f.replace(".yaml", "") for f in os.listdir(sub_dir) if f.startswith("sub_mas-") and f.endswith(".yaml")])
    
    results = []
    clean = 0
    with_issues = 0
    fixed = 0
    not_found = 0
    
    for agent in agents:
        # Load Sources for jeden Agent (else Referenz-Probleme)
        src = load_all_sources(workspace)
        rules = build_rule_package(src)
        result = refresh_agent(agent, True, workspace, src, rules)
        results.append(result)
        if result["status"] == "clean":
            clean += 1
        elif result["status"] == "not_found":
            not_found += 1
        else:
            with_issues += 1
    
    # If not dry-run: batch fix (only settings)
    if not dry_run:
        print(f"\n🔧 Fixe {with_issues} Agenten...")
        for result in results:
            if result["status"] != "clean" and result["status"] != "not_found":
                r2 = refresh_agent(result["agent"], False, workspace)
                if r2["status"] == "fixed":
                    fixed += 1
                    with_issues -= 1
    
    return {
        "total": len(agents),
        "clean": clean,
        "with_issues": with_issues,
        "fixed": fixed,
        "not_found": not_found,
        "details": results,
        "dry_run": dry_run
    }

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="dev_template_generator v2.0 — Agent-YAML Generator aus SOT+BP")
    
    # Mode (exklusiv)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--create", action="store_true", help="Agent new create")
    mode_group.add_argument("--refresh", action="store_true", help="Bestehenden Agent checkn/luecken fill")
    mode_group.add_argument("--refresh-all", action="store_true", help="All Sub-Agenten checkn")
    
    # Create-Optionen
    parser.add_argument("--name", default="", help="Agenten-Name (z.B. log-analyzer)")
    parser.add_argument("--emoji", default="🔧", help="Emoji (Default: 🔧)")
    parser.add_argument("--task", default="", help="Kernaufgabe")
    parser.add_argument("--type", default="sub", choices=["sub", "voll"], help="Agent-Typ (Default: sub)")
    
    # Refresh-Optionen
    parser.add_argument("--agent", default="", help="Only thesen Agent refreshen (fuer --refresh)")
    
    # Global
    parser.add_argument("--dry-run", action="store_true", help="Only show, nothing change")
    parser.add_argument("--diff", action="store_true", help="Unterschiede anshow")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare Output")
    parser.add_argument("--workspace", default=os.getcwd(), help="Workspace (Default: CWD)")
    parser.add_argument("--no-sot", action="store_true", help="No SOT-entry create")
    
    args = parser.parse_args()
    
    workspace = args.workspace
    
    # ── MODE: --create ──
    if args.create:
        if not args.name or not args.task:
            print("❌ --create needs --name und --task")
            sys.exit(1)
        
        print(f"\n🔨 GENERATE: {args.emoji} {args.name} — {_shorten(args.task, 60)}")
        print(f"   Typ: {args.type}")
        
        sources = load_all_sources(workspace)
        rules = build_rule_package(sources)
        filled = fill_template(sources, rules, args.name, args.emoji, args.task, args.type)
        yaml_data = build_yaml(filled, rules, args.name, args.emoji, args.task)
        result = write_agent(yaml_data, args.name, args.type, workspace, args.no_sot)
        
        if args.json:
            result.update({"name": args.name, "emoji": args.emoji, "task": args.task, "type": args.type})
            # --json: AUSSCHLIESSLICH JSON ausgeben, no anderer Output
            # Redirect sys.stdout to capture any prior prints, then print only JSON
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return  # Exit immediately, no further output
        
        print(f"\n📦 Result:")
        print(f"   file: {result.get('file', '?')}")
        print(f"   YAML-Valid: {'✅' if result.get('yaml_valid') else '❌'}")
        print(f"   SOT-entry: {'✅' if result.get('sot_entry_added') else '❌'}")
        print(f"   sub_recipes: {'✅' if result.get('sub_recipes_updated') else '❌'}")
        if result.get("error"):
            print(f"   Error: {result['error']}")
    
    # ── MODE: --refresh ──
    elif args.refresh:
        agent_name = args.agent
        if not agent_name:
            print("❌ --refresh needs --agent NAME")
            sys.exit(1)
        
        if not agent_name.startswith("sub_mas-"):
            agent_name = "sub_mas-" + agent_name
        
        print(f"\n🔍 REFRESH: {agent_name}")
        
        sources = load_all_sources(workspace)
        rules = build_rule_package(sources)
        result = refresh_agent(agent_name, args.dry_run, workspace, sources, rules)
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return  # --json: NUR JSON Output
        
        print(f"\n   Status: {result.get('status', '?')}")
        if result.get("issues"):
            print(f"   Issues ({len(result['issues'])}):")
            for iss in result["issues"]:
                print(f"     ⚠️  [{iss.get('severity','?')}] {iss.get('field','?')}: {iss.get('problem','?')}")
                if not args.dry_run and result.get("status") == "fixed":
                    print(f"         → Fix: {iss.get('fix','?')}")
        else:
            print(f"   ✅ Sauber — no Issues")
    
    # ── MODE: --refresh-all ──
    elif args.refresh_all:
        print(f"\n🔍 REFRESH-ALL (dry-run={'ja' if args.dry_run else 'nein'})")
        
        result = refresh_all(args.dry_run, workspace)
        
        if args.json:
            out = {k: v for k, v in result.items() if k != "details"}
            out["agent_summaries"] = [
                {"agent": d["agent"], "status": d["status"], "issues": d["issues_count"]}
                for d in result.get("details", [])
            ]
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return
        
        print(f"\n📊 Result:")
        print(f"   Total: {result.get('total', 0)} Agenten")
        print(f"   ✅ Sauber: {result.get('clean', 0)}")
        print(f"   ⚠️  Mit Issues: {result.get('with_issues', 0)}")
        print(f"   🔧 Gefixed: {result.get('fixed', 0)}")
        
        if args.dry_run and result.get("details"):
            print(f"\n   Details (Agenten mit Issues):")
            for d in result["details"]:
                if d["status"] != "clean" and d["issues"]:
                    print(f"     ⚠️  {d['agent']}: {d['issues_count']} Issues")
                    for iss in d["issues"][:3]:
                        print(f"       • {iss.get('field','?')}: {iss.get('problem','?')}")
                    if d["issues_count"] > 3:
                        print(f"       ... +{d['issues_count']-3} mehr")

if __name__ == "__main__":
    main()
