#!/usr/bin/env python3
"""
dev_rule_checker.py — Method 9: Deterministic rule test
Called BEFORE every write/edit/shell action.
Blocks actions that violate hard rules.
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

# --mode generic: User-Projekt (rules.yaml)
# --mode mas (default): MAS-eigene Rulen (rules_5_extreme.yaml + hard_rules.yaml)
REGEL_DATEI = os.path.join(MAS_DIR, ".state/rules/rules_5_extreme.yaml")
REGEL_4_DATEI = os.path.join(MAS_DIR, ".state/rules/rules_4_strong.yaml")
REGEL_GENERIC_DATEI = os.path.join(BASE_DIR, ".state/rules/rules.yaml")
HARTE_REGEL_DATEI = os.path.join(MAS_DIR, ".state/rules/hard_rules.yaml")
MODE_DATEI = os.path.join(BASE_DIR, ".mas-mode")
WORKFLOWS_DATEI = os.path.join(MAS_DIR, ".state/workflows.yaml")
CONFIRMATION_DATEI = os.path.join(MAS_DIR, ".state/.last_confirmation")

def load_rules(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("rules", [])

def get_rules(mode=None):
    """Load rules based on mode. --mode generic = rules.yaml, mas = hard_rules.yaml + workflows.yaml"""
    m = mode or "mas"
    if m == "generic":
        if os.path.exists(REGEL_GENERIC_DATEI):
            with open(REGEL_GENERIC_DATEI) as f:
                data = yaml.safe_load(f)
            return data.get("rules", data.get("rules", []))
        return []
    else:
        # Load from old files + workflows.yaml
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
                        "hardness": 5 if val.get("level") == "extreme" else (4 if val.get("level") == "strong" else 3)
                    })
        return rules

def check_mode():
    if not os.path.exists(MODE_DATEI):
        return "unbekannt"
    with open(MODE_DATEI) as f:
        return f.read().strip()

def check_confirmation():
    """Checks if user confirmation exists within the last 5 minutes"""
    if not os.path.exists(CONFIRMATION_DATEI):
        return False
    with open(CONFIRMATION_DATEI) as f:
        ts = int(f.read().strip())
    return int(time.time()) - ts < 300

def check_rule(rule_id, action=""):
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
                        "hardness": 5 if val.get("level") == "extreme" else (4 if val.get("level") == "strong" else 3)
                    })
        except:
            pass
    for rule in rules:
        if rule["id"] != rule_id:
            continue
        
        if rule_id == "R01":
            has = check_confirmation()
            if not has:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "No confirmation in the last 5 minutes", "action": "BLOCKED"}
        
        if rule_id == "R09":
            """MODE-DOMAIN-COUPLING: Mode determines the allowed domain.
            
            Checken:
            1. Logischer Import (from/import andere Domain) -> BLOCKED
            2. Mode conflict (Target-Domain != .mas-mode) -> BLOCKED  
            3. Domain-Konflikt (Target-Domaene != .active_domain) -> BLOCKED
               Exception: Readder Access (read/cat/ls) in andere Domain = OK
               Exception: framework analyzen from MAS aus = OK (only read)
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
            
            # Read current mode
            mode = check_mode() if _os9.path.exists(MODE_DATEI) else "unbekannt"
            
            # Read active_domain
            active_domain = None
            if _os9.path.exists(domain_file):
                with open(domain_file) as f:
                    active_domain = f.read().strip()
            
            akt = action.lower()
            
            # PRUEFUNG 1: Logische Imports (import/from andere Domain)
            for dname, dconf in domains.items():
                if dname == active_domain:
                    continue
                dp = dconf["path"].rstrip("/").lower() if "path" in dconf else dname.lower()
                if f"import {dname}" in akt or f"from {dname}" in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"{active_domain} imports {dname} — Logical import FORBIDDEN!", "action": "BLOCKED"}
                if f"import {dp}" in akt or f"from {dp}" in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"{active_domain} importiert {dname} ({dp}) — Logischer Import FORBIDDEN!", "action": "BLOCKED"}
            
            # CHECK 2: Mode conflict (only for write/edit/shell)
            is_write = any(x in akt for x in ["write ", "edit ", "delete ", "mv ", "cp ", "rm ", ">", "sed "])
            if is_write and active_domain and domains:
                target_domain = None
                for dname, dconf in domains.items():
                    dp = dconf["path"].rstrip("/").lower() if "path" in dconf else dname.lower()
                    if dp in akt:
                        target_domain = dname
                        break
                
                if target_domain and target_domain != active_domain:
                    # Mode check: May active_domain write in target_domain?
                    target_mode = domains.get(target_domain, {}).get("mode", None)
                    if target_mode and mode != target_mode:
                        return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                                "detail": f"{active_domain} writes to {target_domain} (mode={target_mode}) with own mode={mode} — MODE CONFLICT!", "action": "BLOCKED"}
                    
                    # Domain-Check: Schreibzugriff auf fremde Domain
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"{active_domain} writes to {target_domain} — DOMAIN CONFLICT! Only read access allowed.", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}

        if rule_id == "R02":
            """INVENTORY_CHECK: Checks if file exists + special_agents registry"""
            import os as _os, yaml as _yaml
            
            akt = action.lower()
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
                            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                                    "detail": f"Special agent: {base_name} (special_agents.yaml)", "action": "OK"}
                
                if _os.path.exists(full_path) and "force" not in akt and "--force" not in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"Target exists already: {path}", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R05":
            """AUTO_COMMIT: 1. Checkpoint BEFORE change → 2. Change → 3. commit"""
            akt = action.lower()
            is_modify = any(x in akt for x in ["write ", "edit ", "mv ", "cp ", "delete ", "rm "])
            
            if is_modify:
                # Check order: Checkpoint MUST come before change
                has_checkpoint = "checkpoint" in akt
                has_change = any(x in akt for x in ["edit ", "write ", "mv ", "cp "])
                has_commit = "git commit" in akt or "git add" in akt
                
                # Check ob ORDER eingehalten will
                if "checkpoint" in akt:
                    # Checkpoint VOR Change ist OK
                    return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "Checkpoint BEFORE change — correct order", "action": "OK"}
                
                if has_change and not has_checkpoint and not has_commit:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "Change WITHOUT prior checkpoint! Order: 1. Checkpoint → 2. Change → 3. commit", "action": "BLOCKED"}
                
                if has_change and not has_checkpoint and has_commit and "git commit" in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "commit WITHOUT prior checkpoint! ORDER VIOLATED — rollback recommended", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R06":
            """SUB_AGENT_CONTAINMENT: Sub-Agent = NUR Analyse, Shell selbst ausexecuten"""
            akt = action.lower()
            
            # Check ob delegate() eine shell-action contains
            if "delegate" in akt and ("write" in akt or "edit" in akt or "rm " in akt or "mv " in akt):
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "Sub-agent delegated write/edit — Sub-agent ONLY for analysis, execute shell yourself!", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R07":
            """SIGNAL_CP_DONE: CP_DONE signal required after checkpoint"""
            akt = action.lower()
            
            if "checkpoint" in akt and "cp_done" not in akt and "CP_DONE" not in akt:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "Checkpoint without CP_DONE signal — CP_DONE must be sent after checkpoint!", "action": "WARNING"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R08":
            """TOKEN_BUDGET: General improver max 50K tokens"""
            akt = action.lower()
            
            if "general-improver" in akt or "general_improver" in akt or "si-run" in akt:
                extrahiere_token = False
                # Einfache Token-Schaetzung: Number Woerter * 1.3
                token_est = len(akt.split()) * 1.3
                
                if token_est > 50000:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"Token budget exceeded (approx. {token_est:.0f} > 50000) — Ask user if continuation is allowed", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        
        if rule_id == "R04":
            if "general-improver" in action.lower() and ("edit" in action.lower() or "write" in action.lower()):
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "general-improver.yaml may not be edited", "action": "BLOCKED"}
        
        if rule_id == "R10":
            """CORONASHIELD: Every YAML must be validated before saving"""
            import os as _os
            akt = action.lower()
            
            # Only bei write/edit von .yaml/.yml files check
            is_yaml_write = any(x in akt for x in [".yaml", ".yml"]) and ("write " in akt or "edit " in akt)
            
            if is_yaml_write:
                # Check ob immune-check im Command ist
                has_immune = "immune" in akt or "CHECK_YAML" in akt or "corona" in akt
                if not has_immune:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "YAML edit without CORONASHIELD check — sub_mas-recovery-immune CHECK_YAML required!", "action": "BLOCKED"}
            
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}

        if rule_id == "R12":
            """WORK_MAS_DECOUPLING: MAS lebt in ~/.config/goose/.state/mas/"""
            akt = action.lower()
            if any(x in akt for x in [".state/", "checkpoints/", ".backups/"]) and "checkpoint" not in akt:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "MAS state in work/ detected! State belongs in ~/.config/goose/.state/mas/", "action": "WARNING"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R13":
            """NEW_PROJECT_IGNORE: Bei emptym Directory MAS-Config ignorieren"""
            # Will in prompt_1 checked — hier only Enforcement-Check
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": "R13 is checked in prompt_1", "action": "OK"}
        
        if rule_id == "R14":
            """WORK_ON_MODE: work_on = mas | <projekt>"""
            mode_file = os.path.expanduser("~/.config/goose/.mas-mode")
            if not os.path.exists(mode_file):
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "No .mas-mode found — work_on mode not determinable", "action": "BLOCKED"}
            with open(mode_file) as _f:
                mode = _f.read().strip()
            akt = action.lower()
            if mode != "mas":
                # Im Projekt-Mode: NOE MAS-Operationen erlaubt
                if any(x in akt for x in ["sub_mas-", "mas-engineer", "workflows.yaml"]):
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"work_on='{mode}' — MAS operations in project mode not allowed", "action": "BLOCKED"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R15":
            """ARCHITECTURE_APPROVAL: Nutzt dev_architecture_checker.py"""
            import subprocess as _sp
            try:
                result = _sp.run(
                    ["python3", "tools/dev_architecture_checker.py", "--action", action, "--file", ""],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 1:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": result.stdout.strip(), "action": "BLOCKED"}
            except Exception:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "dev_architecture_checker.py not found", "action": "WARNING"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R16":
            """TOOL_BEFORE_EXPERT: Checks if tool exists before delegating to expert"""
            akt = action.lower()
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
                        return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                                "detail": f"Delegate to {agent_name} without prior tool check! Order: 1. Tool → 2. Expert → 3. New agent", "action": "WARNING"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
        
        if rule_id == "R17":
            """IMPROVEMENT_PUSH: Push improvements to user"""
            # Will in general-improver checked — hier only Note
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": "R17 will in general-improver Step 8 checked", "action": "OK"}

        if rule_id == "R19":
            """PATH-HIERARCHY: ONLY execute installed tools — NEVER source tools"""
            akt = action.lower()
            # CHECK 1: Build/Install exception (BEFORE source check)
            if "dev_build.sh" in akt or "dev_install.sh" in akt:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "Build/install exception — source access allowed", "action": "OK"}
            # CHECK 2: Install path (correct)
            install_patterns = ["mas-engineer-tools/", "MAS_TOOLS_DIR"]
            for pattern in install_patterns:
                if pattern in akt:
                    return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": "Install path used — correct", "action": "OK"}
            # CHECK 3: Source path (BLOCKED)
            source_patterns = ["mas-engineer/tools/", "mas-engineer/tools/dev_"]
            for pattern in source_patterns:
                if pattern in akt:
                    return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                            "detail": f"Source-Path erkannt ('{pattern}')! Nutze $MAS_TOOLS_DIR (Install-Path) statt Source",
                            "action": "BLOCKED"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": "No tool-call detected — R19 not applicable", "action": "OK"}

        if rule_id == "R18":
            """DELEGATION DUTY: NEVER shell/write/edit yourself if sub-agent exists"""
            akt = action.lower()
            # Check ob es sich um eine shell/write/edit action handelt
            ist_selbst_mach = any(x in akt for x in ["shell", "write", "edit"])
            if not ist_selbst_mach:
                return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": "No shell/write/edit action — R18 not applicable", "action": "OK"}

            # Check ob a passender Sub-Agent exists
            wf_path = os.path.join(BASE_DIR, ".state/workflows.yaml")
            sub_agent_found = False
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
                        sub_agent_found = True
                        founder_agent = agent
                        break

            if sub_agent_found:
                return {"violation": True, "rule": rule["name"], "hardness": rule["hardness"],
                        "detail": f"Sub-Agent {founder_agent} exists for these Task — delegiere() statt do it yourself!",
                        "action": "BLOCKED"}
            return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"],
                    "detail": "No matching sub-agent found — doing it yourself allowed", "action": "OK"}
        
        return {"violation": False, "rule": rule["name"], "hardness": rule["hardness"], "action": "OK"}
    
    return {"violation": False, "rule": "unbekannt", "hardness": 2, "action": "OK"}

def format_output(resultse, action_type=""):
    blocked = [r for r in resultse if r.get("action") == "BLOCKED"]
    
    lines = []
    lines.append("=== ⛔ REGEL-CHECK ===")
    lines.append(f"action: {action_type}")
    lines.append(f"Gechecks: {len(resultse)} Rulen")
    
    for r in resultse:
        if r.get("hardness", 0) >= 5:
            lines.append(f"⛔⛔⛔⛔⛔ {r['rule']}: {r['action']} — {r.get('detail', 'ok')}")
        elif r.get("hardness", 0) >= 4:
            lines.append(f"⛔⛔⛔ {r['rule']}: {r['action']} — {r.get('detail', 'ok')}")
        else:
            lines.append(f"⛔ {r['rule']}: {r['action']} — {r.get('detail', 'ok')}")
    
    if blocked:
        lines.append(f"\n⛔⛔⛔⛔⛔ {len(blocked)} EXTREME-STRONG VERSTOESSE!")
        lines.append("AKTION WAS BLOCKIERT — User informieren")
        for b in blocked:
            lines.append(f"  → {b['rule']}: {b['detail']}")
        return "\n".join(lines), False
    else:
        lines.append("\n✅ All Rulen eingehalten — action approved")
        return "\n".join(lines), True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rule check before actions")
    parser.add_argument("--check", help="Rule-ID (R01-R19)")
    parser.add_argument("--file", default=None, help="Betroffene file (for R09)")
    parser.add_argument("--action", default="", help="Geplante action (z.B. 'edit file.yaml')")
    parser.add_argument("--mode", default="mas", help="Current mode")
    parser.add_argument("--all", action="store_true", help="All Rulen check")
    parser.add_argument("--action-type", default="unbekannt", help="type of action: write|edit|delegate|shell")
    
    args = parser.parse_args()
    global CURRENT_MODE
    CURRENT_MODE = args.mode or "mas"
    
    action_info = f"{args.action_type}: {args.action}" if args.action else args.action_type
    
    if args.all:
        active_rules = get_rules(args.mode)
        # R09 ALWAYS FIRST checkn (oberste Rule) — only im MAS-Mode
        if args.mode == "mas":
            r09_result = check_rule("R09", args.action or "")
            resultse = [r09_result]
            # ALL other rules (without duplicates via ID)
            gesehene_ids = {"R09", "R19"}
            for idx, r in enumerate(active_rules):
                rid = r.get("id", f"G{idx:02d}")
                if rid not in gesehene_ids:
                    gesehene_ids.add(rid)
                    resultse.append(check_rule(rid, args.action or ""))
        else:
            resultse = [check_rule(r.get("id", f"G{i:02d}"), args.action or "") for i, r in enumerate(active_rules)]
        output, ok = format_output(resultse, action_info)
        print(output)
        sys.exit(0 if ok else 1)
    elif args.check:
        result = check_rule(args.check, args.action or "")
        if result.get("violation"):
            print(f"⛔⛔⛔⛔⛔ REGEL-VERSTOSS: {result['rule']}")
            print(f"  Detail: {result['detail']}")
            print(f"  action: {result['action']}")
            sys.exit(1)
        else:
            print(f"✅ {result['rule']}: OK")
            sys.exit(0)
    else:
        # Default: all Rulen des activeen Mode check
        active_rules = get_rules(args.mode)
        if args.mode == "mas":
            resultse = [check_rule(r["id"], args.action or "") for r in active_rules if isinstance(r, dict)]
        else:
            resultse = [{"rule": r.get("name", r.get("id", "?")), "hardness": r.get("hardness", 3),
                          "action": "WARNING" if r.get("block") else "OK",
                          "detail": r.get("prompt_text", str(r)[:100])}
                         for r in active_rules if isinstance(r, dict)]
        output, ok = format_output(resultse, action_info)
        print(output)
        sys.exit(0 if ok else 1)
