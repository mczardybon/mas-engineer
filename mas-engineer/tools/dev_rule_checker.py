#!/usr/am/env python3
"""
dev_rule_checker.py — Methode 9: Deterministischer Rule-Test
Will VOR jeder write/edit/shell-Aktion aufgerufen.
Blocked Aktionen die gegen harte Rulen verstossen.
"""

import sys
import os
import json
import yaml
import subprocess
import time

BASE_DIR = os.path.abspath(".")
MAS_DIR = os.path.join(BASE_DIR, "mas-engineer") if os.path.isdir(os.path.join(BASE_DIR, "mas-engineer")) else BASE_DIR
# MAS-Rulen liegen in mas-engineer/.state/rules/ (not in .state/rules/)
MAS_DIR = os.path.join(BASE_DIR, "mas-engineer") if os.path.isdir(os.path.join(BASE_DIR, "mas-engineer")) else BASE_DIR

# --mode generic: User-Projekt (rulen.yaml)
# --mode mas (default): MAS-eigene Rulen (rulen_5_extrem.yaml + harte_rulen.yaml)
REGEL_DATEI = os.path.join(MAS_DIR, ".state/rules/rulen_5_extrem.yaml")
REGEL_4_DATEI = os.path.join(MAS_DIR, ".state/rules/rulen_4_stark.yaml")
REGEL_GENERIC_DATEI = os.path.join(BASE_DIR, ".state/rules/rulen.yaml")
HARTE_REGEL_DATEI = os.path.join(MAS_DIR, ".state/rules/harte_rulen.yaml")
MODE_DATEI = os.path.join(BASE_DIR, ".mas-mode")
WORKFLOWS_DATEI = os.path.join(MAS_DIR, ".state/workflows.yaml")
CONFIRMATION_DATEI = os.path.join(MAS_DIR, ".state/.last_confirmation")

def load_rules(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("rulen", [])

def get_rules(mode=None):
    """Load Rulen basierend auf Mode. --mode generic = rulen.yaml, mas = harte_rulen.yaml + workflows.yaml"""
    m = mode or "mas"
    if m == "generic":
        if os.path.exists(REGEL_GENERIC_DATEI):
            with open(REGEL_GENERIC_DATEI) as f:
                data = yaml.safe_load(f)
            return data.get("rulen", data.get("rules", []))
        return []
    else:
        # Load aus alten files + workflows.yaml
        rules = load_rules(REGEL_DATEI) + load_rules(REGEL_4_DATEI) + load_rules(HARTE_REGEL_DATEI)
        # Load additionally aus workflows.yaml (R12-R18)
        WORKFLOWS_DATEI
        if os.path.exists(WORKFLOWS_DATEI):
            with open(WORKFLOWS_DATEI) as f:
                wf = yaml.safe_load(f)
            restrictions = wf.get("configs", {}).get("mas-self", {}).get("restrictions", {})
            for key, val in restrictions.items():
                if key.startswith("r") and isinstance(val, dict):
                    # Normierte ID: R19 aus r19_path_hierarchie, R01 aus r01_confirmation usw.
                    norm_id = key.split("_")[0].upper()
                    rules.append({
                        "id": norm_id,
                        "name": val.get("description", val.get("type", key)),
                        "haerte": 5 if val.get("level") == "extrem" else (4 if val.get("level") == "stark" else 3)
                    })
        return rules

def check_mode():
    if not os.path.exists(MODE_DATEI):
        return "unbekannt"
    with open(MODE_DATEI) as f:
        return f.read().strip()

def check_confirmation():
    """Checks ob User-Confirmation in den letzten 5 Minuten vorliegt"""
    if not os.path.exists(CONFIRMATION_DATEI):
        return False
    with open(CONFIRMATION_DATEI) as f:
        ts = int(f.read().strip())
    return int(time.time()) - ts < 300

def check_rule(rule_id, aktion=""):
    rules = load_rules(REGEL_DATEI)
    # Load auch aus workflows.yaml (R12-R19)
    import os as _wf_os
    if _wf_os.path.exists(WORKFLOWS_DATEI):
        try:
            with open(WORKFLOWS_DATEI) as f:
                wf = yaml.safe_load(f)
            restrictions = wf.get("configs", {}).get("mas-self", {}).get("restrictions", {})
            for key, val in restrictions.items():
                if key.startswith("r") and isinstance(val, dict):
                    norm_id = key.split("_")[0].upper()
                    rules.append({
                        "id": norm_id,
                        "name": val.get("description", key),
                        "haerte": 5 if val.get("level") == "extrem" else (4 if val.get("level") == "stark" else 3)
                    })
        except:
            pass
    for rule in rules:
        if rule["id"] != rule_id:
            continue
        
        if rule_id == "R01":
            has = check_confirmation()
            if not has:
                return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "No Confirmation in den letzten 5 Minuten", "aktion": "BLOCKED"}
        
        if rule_id == "R09":
            """MODUS-DOMAENEN-KOPPLUNG: Modus determines die erlaubte Domain.
            
            Checken:
            1. Logischer Import (from/import andere Domain) -> BLOCKED
            2. Modus-Konflikt (Target-Domaene != .mas-mode) -> BLOCKED  
            3. Domain-Konflikt (Target-Domaene != .active_domain) -> BLOCKED
               Exception: Readder Access (read/cat/ls) in andere Domain = OK
               Exception: Framework analysieren from MAS aus = OK (only read)
            """
            import os as _os9, yaml as _yaml9
            
            # Read Configuration
            base = _os9.path.dirname(_os9.path.dirname(_os9.path.abspath(__file__)))
            reg_path = _os9.path.join(base, ".state/domains/registry.yaml")
            mode_file = _os9.path.expanduser("~/.config/goose/.mas-mode")
            domain_file = _os9.path.expanduser("~/.config/goose/.active_domain")
            
            # Read registry
            domains = {}
            if _os9.path.exists(reg_path):
                with open(reg_path) as f:
                    reg = _yaml9.safe_load(f) or {}
                domains = reg.get("domains", {})
            
            # Read aktuellen Modus
            mode = check_mode() if _os9.path.exists(MODE_DATEI) else "unbekannt"
            
            # Read active_domain
            active_domain = None
            if _os9.path.exists(domain_file):
                with open(domain_file) as f:
                    active_domain = f.read().strip()
            
            akt = aktion.lower()
            
            # PRUEFUNG 1: Logische Imports (import/from andere Domain)
            for dname, dconf in domains.items():
                if dname == active_domain:
                    continue
                dp = dconf["path"].rstrip("/").lower() if "path" in dconf else dname.lower()
                if f"import {dname}" in akt or f"from {dname}" in akt:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": f"{active_domain} importiert {dname} — Logischer Import FORBIDDEN!", "aktion": "BLOCKED"}
                if f"import {dp}" in akt or f"from {dp}" in akt:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": f"{active_domain} importiert {dname} ({dp}) — Logischer Import FORBIDDEN!", "aktion": "BLOCKED"}
            
            # PRUEFUNG 2: Modus-Konflikt (only bei write/edit/shell)
            is_write = any(x in akt for x in ["write ", "edit ", "delete ", "mv ", "cp ", "rm ", ">", "sed "])
            if is_write and active_domain and domains:
                target_domain = None
                for dname, dconf in domains.items():
                    dp = dconf["path"].rstrip("/").lower() if "path" in dconf else dname.lower()
                    if dp in akt:
                        target_domain = dname
                        break
                
                if target_domain and target_domain != active_domain:
                    # Modus-Check: May active_domain in target_domain write?
                    target_mode = domains.get(target_domain, {}).get("mode", None)
                    if target_mode and mode != target_mode:
                        return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                                "detail": f"{active_domain} schreibt in {target_domain} (mode={target_mode}) bei eigenem mode={mode} — MODUS-KONFLIKT!", "aktion": "BLOCKED"}
                    
                    # Domain-Check: Schreibzugriff auf fremde Domain
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": f"{active_domain} schreibt in {target_domain} — DOMAENEN-KONFLIKT! Only readder Access erlaubt.", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}

        if rule_id == "R02":
            """BESTAND_PRUFUNG: Checks ob file exists + special_agents Registry"""
            import os as _os, yaml as _yaml
            
            akt = aktion.lower()
            path = None
            for prefix in ["write ", "edit ", "cp ", "mv "]:
                if prefix in akt:
                    path = akt.split(prefix)[-1].split()[0].strip()
                    break
            
            if path and not path.startswith("/"):
                cwd = _os.getcwd()
                full_path = _os.path.join(cwd, path) if not _os.path.isabs(path) else path
                
                special_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), ".state/agents/special_agents.yaml")
                if _os.path.exists(special_path):
                    with open(special_path) as _f:
                        special = _yaml.safe_load(_f)
                    if special and "agents" in special:
                        fname = _os.path.basename(path)
                        base_name = fname.replace(".yaml", "")
                        if base_name in special["agents"]:
                            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                                    "detail": f"Spezial-Agent: {base_name} (special_agents.yaml)", "aktion": "OK"}
                
                if _os.path.exists(full_path) and "force" not in akt and "--force" not in akt:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": f"Target exists already: {path}", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R05":
            """AUTO_COMMIT: 1. Checkpoint VOR Change → 2. Change → 3. Commit"""
            akt = aktion.lower()
            is_modify = any(x in akt for x in ["write ", "edit ", "mv ", "cp ", "delete ", "rm "])
            
            if is_modify:
                # Check Reihenfolge: Checkpoint MUST vor Change kommen
                has_checkpoint = "checkpoint" in akt
                has_change = any(x in akt for x in ["edit ", "write ", "mv ", "cp "])
                has_commit = "git commit" in akt or "git add" in akt
                
                # Check ob ORDER eingehalten will
                if "checkpoint" in akt:
                    # Checkpoint VOR Change ist OK
                    return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": "Checkpoint VOR Change — korrekte Reihenfolge", "aktion": "OK"}
                
                if has_change and not has_checkpoint and not has_commit:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": "Change OHNE beforeigen Checkpoint! Reihenfolge: 1. Checkpoint → 2. Change → 3. Commit", "aktion": "BLOCKED"}
                
                if has_change and not has_checkpoint and has_commit and "git commit" in akt:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": "Commit OHNE beforeigen Checkpoint! ORDER VERLETZT — Rollback recommended", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R06":
            """SUB_AGENT_CONTAINMENT: Sub-Agent = NUR Analyse, Shell selbst ausexecuten"""
            akt = aktion.lower()
            
            # Check ob delegate() eine shell-Aktion contains
            if "delegate" in akt and ("write" in akt or "edit" in akt or "rm " in akt or "mv " in akt):
                return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "Sub-Agent delegiert write/edit — Sub-Agent NUR for Analyse, Shell selbst ausexecuten!", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R07":
            """SIGNAL_CP_DONE: CP_DONE Signal after Checkpoint required"""
            akt = aktion.lower()
            
            if "checkpoint" in akt and "cp_done" not in akt and "CP_DONE" not in akt:
                return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "Checkpoint ohne CP_DONE Signal — CP_DONE must after Checkpoint gesendet will!", "aktion": "WARNING"}
            
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R08":
            """TOKEN_BUDGET: General-Improver max 50K Tokens"""
            akt = aktion.lower()
            
            if "general-improver" in akt or "general_improver" in akt or "si-run" in akt:
                extrahiere_token = False
                # Einfache Token-Schaetzung: Number Woerter * 1.3
                token_est = len(akt.split()) * 1.3
                
                if token_est > 50000:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": f"Token-Budget aboutstepsn (ca. {token_est:.0f} > 50000) — User ask ob Fortsetzung erlaubt", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        
        if rule_id == "R04":
            if "general-improver" in aktion.lower() and ("edit" in aktion.lower() or "write" in aktion.lower()):
                return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "general-improver.yaml may not edited will", "aktion": "BLOCKED"}
        
        if rule_id == "R10":
            """CORONASHIELD: Jede YAML will vor Speicherung validated"""
            import os as _os
            akt = aktion.lower()
            
            # Only bei write/edit von .yaml/.yml files check
            is_yaml_write = any(x in akt for x in [".yaml", ".yml"]) and ("write " in akt or "edit " in akt)
            
            if is_yaml_write:
                # Check ob immune-check im Command ist
                has_immune = "immune" in akt or "CHECK_YAML" in akt or "corona" in akt
                if not has_immune:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": "YAML-Edit ohne CORONASHIELD-Check — sub_mas-recovery-immune CHECK_YAML required!", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}

        if rule_id == "R12":
            """WORK_MAS_ENTKOPPLUNG: MAS lebt in ~/.config/goose/.state/mas/"""
            akt = aktion.lower()
            if any(x in akt for x in [".state/", "checkpoints/", ".backups/"]) and "checkpoint" not in akt:
                return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "MAS-State in work/ erkannt! State gehoert after ~/.config/goose/.state/mas/", "aktion": "WARNING"}
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R13":
            """NEUES_PROJEKT_IGNORE: Bei leerem Directory MAS-Config ignorieren"""
            # Will in prompt_1 checked — hier only Enforcement-Check
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                    "detail": "R13 will in prompt_1 checked", "aktion": "OK"}
        
        if rule_id == "R14":
            """WORK_ON_MODUS: work_on = mas | <projekt>"""
            mode_file = os.path.expanduser("~/.config/goose/.mas-mode")
            if not os.path.exists(mode_file):
                return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "No .mas-mode found — work_on-Modus not bestimmbar", "aktion": "BLOCKED"}
            with open(mode_file) as _f:
                mode = _f.read().strip()
            akt = aktion.lower()
            if mode != "mas":
                # Im Projekt-Modus: KEINE MAS-Operationen erlaubt
                if any(x in akt for x in ["sub_mas-", "mas-engineer", "workflows.yaml"]):
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": f"work_on='{mode}' — MAS-Operationen im Projekt-Modus not erlaubt", "aktion": "BLOCKED"}
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R15":
            """ARCHITEKTUR_GENEHMIGUNG: Nutzt dev_architecture_checker.py"""
            import subprocess as _sp
            try:
                result = _sp.run(
                    ["python3", "tools/dev_architecture_checker.py", "--action", aktion, "--file", ""],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 1:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": result.stdout.strip(), "aktion": "BLOCKED"}
            except Exception:
                return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "dev_architecture_checker.py not found", "aktion": "WARNING"}
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R16":
            """TOOL_VOR_EXPERTE: Checks ob Tool exists bevor Expert delegiert will"""
            akt = aktion.lower()
            if "delegate" in akt:
                # Extract agent_name aus delegate()
                import re as _re
                m = _re.search(r"sub_mas-(\w+)", akt)
                if m:
                    agent_name = m.group(1)
                    # Check ob a Tool exists das den Job macht
                    tool_match = False
                    for tool_cat in ["analyse", "build", "harden", "dashboard"]:
                        tool_check = f"dev_{tool_cat}" in akt or tool_cat in agent_name
                        if tool_check:
                            tool_match = True
                            break
                    if not tool_match:
                        return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                                "detail": f"Delegate an {agent_name} ohne beforeigen Tool-Check! Reihenfolge: 1. Tool → 2. Expert → 3. Neuer Agent", "aktion": "WARNING"}
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R17":
            """IMPROVEMENT_PUSH: Verbetterungen an User pushen"""
            # Will in general-improver checked — hier only Note
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                    "detail": "R17 will in general-improver Step 8 checked", "aktion": "OK"}

        if rule_id == "R19":
            """PFAD-HIERARCHIE: NUR installierte Tools execute — NEVER Source-Tools"""
            akt = aktion.lower()
            # CHECK 1: Build/Install exception (BEFORE source check)
            if "dev_build.sh" in akt or "dev_install.sh" in akt:
                return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "Build/Install-Exception — Source-Access erlaubt", "aktion": "OK"}
            # CHECK 2: Install path (correct)
            install_patterns = ["mas-engineer-tools/", "MAS_TOOLS_DIR"]
            for pattern in install_patterns:
                if pattern in akt:
                    return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": "Install-Path verwendet — korrekt", "aktion": "OK"}
            # CHECK 3: Source path (BLOCKED)
            source_patterns = ["mas-engineer/tools/", "mas-engineer/tools/dev_"]
            for pattern in source_patterns:
                if pattern in akt:
                    return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                            "detail": f"Source-Path erkannt ('{pattern}')! Nutze $MAS_TOOLS_DIR (Install-Path) statt Source",
                            "aktion": "BLOCKED"}
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                    "detail": "No Tool-Aufruf erkannt — R19 not anwendbar", "aktion": "OK"}

        if rule_id == "R18":
            """DELEGATION DUTY: NEVER selbst shell/write/edit if Sub-Agent exists"""
            akt = aktion.lower()
            # Check ob es sich um eine shell/write/edit Aktion handelt
            ist_selbst_mach = any(x in akt for x in ["shell", "write", "edit"])
            if not ist_selbst_mach:
                return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": "No shell/write/edit Aktion — R18 not anwendbar", "aktion": "OK"}

            # Check ob a passender Sub-Agent exists
            wf_path = os.path.join(BASE_DIR, ".state/workflows.yaml")
            sub_agent_gefunden = False
            if os.path.exists(wf_path):
                with open(WORKFLOWS_DATEI) as f:
                    wf = yaml.safe_load(f)
                sub_agents = wf.get("configs", {}).get("mas-self", {}).get("sub_agents", {})
                all_sub_agent_names = []
                for cat, agents in sub_agents.items():
                    all_sub_agent_names.extend(agents)

                for agent in all_sub_agent_names:
                    agent_clean = agent.replace("sub_mas-", "").replace("_", "-").lower()
                    if agent_clean in akt or any(word in akt for word in agent_clean.split("-")):
                        sub_agent_gefunden = True
                        gefundener_agent = agent
                        break

            if sub_agent_gefunden:
                return {"verletzt": True, "rule": rule["name"], "haerte": rule["haerte"],
                        "detail": f"Sub-Agent {gefundener_agent} exists for these Task — delegiere() statt do it yourself!",
                        "aktion": "BLOCKED"}
            return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"],
                    "detail": "No passender Sub-Agent found — do it yourself erlaubt", "aktion": "OK"}
        
        return {"verletzt": False, "rule": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
    
    return {"verletzt": False, "rule": "unbekannt", "haerte": 2, "aktion": "OK"}

def format_output(ergebnisse, action_typ=""):
    blocked = [r for r in ergebnisse if r.get("aktion") == "BLOCKED"]
    
    lines = []
    lines.append("=== ⛔ REGEL-CHECK ===")
    lines.append(f"Aktion: {action_typ}")
    lines.append(f"Gechecks: {len(ergebnisse)} Rulen")
    
    for r in ergebnisse:
        if r.get("haerte", 0) >= 5:
            lines.append(f"⛔⛔⛔⛔⛔ {r['rule']}: {r['aktion']} — {r.get('detail', 'ok')}")
        elif r.get("haerte", 0) >= 4:
            lines.append(f"⛔⛔⛔ {r['rule']}: {r['aktion']} — {r.get('detail', 'ok')}")
        else:
            lines.append(f"⛔ {r['rule']}: {r['aktion']} — {r.get('detail', 'ok')}")
    
    if blocked:
        lines.append(f"\n⛔⛔⛔⛔⛔ {len(blocked)} EXTREM-STARK VERSTOESSE!")
        lines.append("AKTION WAS BLOCKIERT — User informieren")
        for b in blocked:
            lines.append(f"  → {b['rule']}: {b['detail']}")
        return "\n".join(lines), False
    else:
        lines.append("\n✅ All Rulen eingehalten — Aktion approved")
        return "\n".join(lines), True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rule-Check vor Aktionen")
    parser.add_argument("--check", help="Rule-ID (R01-R19)")
    parser.add_argument("--file", default=None, help="Betroffene file (fuer R09)")
    parser.add_argument("--action", default="", help="Geplante Aktion (z.B. 'edit file.yaml')")
    parser.add_argument("--mode", default="mas", help="Aktueller Modus")
    parser.add_argument("--all", action="store_true", help="All Rulen check")
    parser.add_argument("--action-type", default="unbekannt", help="Typ der Aktion: write|edit|delegate|shell")
    
    args = parser.parse_args()
    global CURRENT_MODE
    CURRENT_MODE = args.mode or "mas"
    
    action_info = f"{args.action_type}: {args.action}" if args.action else args.action_type
    
    if args.all:
        active_rules = get_rules(args.mode)
        # R09 ALWAYS FIRST checkn (oberste Rule) — only im MAS-Mode
        if args.mode == "mas":
            r09_result = check_rule("R09", args.action or "")
            ergebnisse = [r09_result]
            # ALL anderen Rulen (ohne Duplikate via ID)
            gesehene_ids = {"R09", "R19"}
            for idx, r in enumerate(active_rules):
                rid = r.get("id", f"G{idx:02d}")
                if rid not in gesehene_ids:
                    gesehene_ids.add(rid)
                    ergebnisse.append(check_rule(rid, args.action or ""))
        else:
            ergebnisse = [check_rule(r.get("id", f"G{i:02d}"), args.action or "") for i, r in enumerate(active_rules)]
        output, ok = format_output(ergebnisse, action_info)
        print(output)
        sys.exit(0 if ok else 1)
    elif args.check:
        ergebnis = check_rule(args.check, args.action or "")
        if ergebnis.get("verletzt"):
            print(f"⛔⛔⛔⛔⛔ REGEL-VERSTOSS: {ergebnis['rule']}")
            print(f"  Detail: {ergebnis['detail']}")
            print(f"  Aktion: {ergebnis['aktion']}")
            sys.exit(1)
        else:
            print(f"✅ {ergebnis['rule']}: OK")
            sys.exit(0)
    else:
        # Default: all Rulen des aktiven Mode check
        active_rules = get_rules(args.mode)
        if args.mode == "mas":
            ergebnisse = [check_rule(r["id"], args.action or "") for r in active_rules if isinstance(r, dict)]
        else:
            ergebnisse = [{"rule": r.get("name", r.get("id", "?")), "haerte": r.get("haerte", 3),
                          "aktion": "WARNING" if r.get("block") else "OK",
                          "detail": r.get("prompt_text", str(r)[:100])}
                         for r in active_rules if isinstance(r, dict)]
        output, ok = format_output(ergebnisse, action_info)
        print(output)
        sys.exit(0 if ok else 1)
