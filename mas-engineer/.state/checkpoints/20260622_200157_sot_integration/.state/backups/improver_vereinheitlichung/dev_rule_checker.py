#!/usr/bin/env python3
"""
dev_rule_checker.py — Methode 9: Deterministischer Regel-Test
Wird VOR jeder write/edit/shell-Aktion aufgerufen.
Blockiert Aktionen die gegen harte Regeln verstossen.
"""

import sys
import os
import json
import yaml
import subprocess
import time

BASE_DIR = os.path.abspath(".")

REGEL_DATEI = os.path.join(BASE_DIR, ".state/rules/regeln_5_extrem.yaml")
REGEL_4_DATEI = os.path.join(BASE_DIR, ".state/rules/regeln_4_stark.yaml")
MODE_DATEI = os.path.join(BASE_DIR, ".mas-mode")
BESTAETIGUNG_DATEI = os.path.join(BASE_DIR, ".state/.last_bestaetigung")

def load_rules(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("regeln", [])

def check_mode():
    if not os.path.exists(MODE_DATEI):
        return "unbekannt"
    with open(MODE_DATEI) as f:
        return f.read().strip()

def check_bestaetigung():
    """Prüft ob User-Bestätigung in den letzten 5 Minuten vorliegt"""
    if not os.path.exists(BESTAETIGUNG_DATEI):
        return False
    with open(BESTAETIGUNG_DATEI) as f:
        ts = int(f.read().strip())
    return int(time.time()) - ts < 300

def check_rule(rule_id, aktion=""):
    rules = load_rules(REGEL_DATEI)
    for rule in rules:
        if rule["id"] != rule_id:
            continue
        
        if rule_id == "R01":
            hat = check_bestaetigung()
            if not hat:
                return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                        "detail": "Keine Bestaetigung in den letzten 5 Minuten", "aktion": "BLOCKED"}
        
        if rule_id == "R09":
            """MODUS-DOMAENEN-KOPPLUNG: Modus bestimmt die erlaubte Domain.
            
            Pruefungen:
            1. Logischer Import (from/import andere Domain) -> BLOCKED
            2. Modus-Konflikt (Ziel-Domaene != .mas-mode) -> BLOCKED  
            3. Domain-Konflikt (Ziel-Domaene != .active_domain) -> BLOCKED
               Ausnahme: Lesender Zugriff (read/cat/ls) in andere Domain = OK
               Ausnahme: Framework analysieren von MAS aus = OK (nur lesen)
            """
            import os, yaml
            
            # Lese Konfiguration
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            reg_path = os.path.join(base, ".state/domains/registry.yaml")
            mode_file = os.path.expanduser("~/.config/goose/.mas-mode")
            domain_file = os.path.expanduser("~/.config/goose/.active_domain")
            
            # Lese registry
            domains = {}
            if os.path.exists(reg_path):
                with open(reg_path) as f:
                    reg = yaml.safe_load(f) or {}
                domains = reg.get("domains", {})
            
            # Lese aktuellen Modus
            mode = check_mode() if os.path.exists(MODE_DATEI) else "unbekannt"
            
            # Lese active_domain
            active_domain = None
            if os.path.exists(domain_file):
                with open(domain_file) as f:
                    active_domain = f.read().strip()
            
            akt = aktion.lower()
            
            # PRUEFUNG 1: Logische Imports (import/from andere Domain)
            for dname, dconf in domains.items():
                if dname == active_domain:
                    continue
                dp = dconf["path"].rstrip("/").lower() if "path" in dconf else dname.lower()
                if f"import {dname}" in akt or f"from {dname}" in akt:
                    return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                            "detail": f"{active_domain} importiert {dname} — Logischer Import VERBOTEN!", "aktion": "BLOCKED"}
                if f"import {dp}" in akt or f"from {dp}" in akt:
                    return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                            "detail": f"{active_domain} importiert {dname} ({dp}) — Logischer Import VERBOTEN!", "aktion": "BLOCKED"}
            
            # PRUEFUNG 2: Modus-Konflikt (nur bei write/edit/shell)
            is_write = any(x in akt for x in ["write ", "edit ", "delete ", "mv ", "cp ", "rm ", ">", "sed "])
            if is_write and active_domain and domains:
                target_domain = None
                for dname, dconf in domains.items():
                    dp = dconf["path"].rstrip("/").lower() if "path" in dconf else dname.lower()
                    if dp in akt:
                        target_domain = dname
                        break
                
                if target_domain and target_domain != active_domain:
                    # Modus-Prüfung: Darf active_domain in target_domain schreiben?
                    target_mode = domains.get(target_domain, {}).get("mode", None)
                    if target_mode and mode != target_mode:
                        return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                                "detail": f"{active_domain} schreibt in {target_domain} (mode={target_mode}) bei eigenem mode={mode} — MODUS-KONFLIKT!", "aktion": "BLOCKED"}
                    
                    # Domain-Prüfung: Schreibzugriff auf fremde Domain
                    return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                            "detail": f"{active_domain} schreibt in {target_domain} — DOMAENEN-KONFLIKT! Nur lesender Zugriff erlaubt.", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}

        if rule_id == "R02":
            """BESTAND_PRUFUNG: Prueft ob Datei existiert + special_agents Registry"""
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
                            return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"],
                                    "detail": f"Spezial-Agent: {base_name} (special_agents.yaml)", "aktion": "OK"}
                
                if _os.path.exists(full_path) and "force" not in akt and "--force" not in akt:
                    return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                            "detail": f"Ziel existiert bereits: {path}", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R05":
            """AUTO_COMMIT: Prueft ob git commit + checkpoint + changes.json nach Aenderung"""
            import os as _os, json as _json, subprocess as _sp
            
            akt = aktion.lower()
            is_modify = any(x in akt for x in ["write ", "edit ", "mv ", "cp ", "delete ", "rm "])
            
            if is_modify:
                # Pruefe ob direkt ein commit/checkpoint folgt
                has_commit = "git commit" in akt or "git add" in akt
                has_checkpoint = "checkpoint" in akt
                
                if not has_commit and not has_checkpoint:
                    return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                            "detail": "Aenderung ohne git commit/checkpoint — AUTO-COMMIT erforderlich!", "aktion": "WARN"}
            
            return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R06":
            """SUB_AGENT_CONTAINMENT: Sub-Agent = NUR Analyse, Shell selbst ausfuehren"""
            akt = aktion.lower()
            
            # Pruefe ob delegate() eine shell-Aktion enthaelt
            if "delegate" in akt and ("write" in akt or "edit" in akt or "rm " in akt or "mv " in akt):
                return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                        "detail": "Sub-Agent delegiert write/edit — Sub-Agent NUR fuer Analyse, Shell selbst ausfuehren!", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R07":
            """SIGNAL_CP_DONE: CP_DONE Signal nach Checkpoint erforderlich"""
            akt = aktion.lower()
            
            if "checkpoint" in akt and "cp_done" not in akt and "CP_DONE" not in akt:
                return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                        "detail": "Checkpoint ohne CP_DONE Signal — CP_DONE muss nach Checkpoint gesendet werden!", "aktion": "WARN"}
            
            return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        if rule_id == "R08":
            """TOKEN_BUDGET: Self-Improver max 50K Tokens"""
            akt = aktion.lower()
            
            if "self-improver" in akt or "self_improver" in akt or "si-run" in akt:
                extrahiere_token = False
                # Einfache Token-Schaetzung: Anzahl Woerter * 1.3
                token_est = len(akt.split()) * 1.3
                
                if token_est > 50000:
                    return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                            "detail": f"Token-Budget ueberschritten (ca. {token_est:.0f} > 50000) — User fragen ob Fortsetzung erlaubt", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
        
        
        if rule_id == "R04":
            if "self-improver" in aktion.lower() and ("edit" in aktion.lower() or "write" in aktion.lower()):
                return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                        "detail": "self-improver.yaml darf nicht editiert werden", "aktion": "BLOCKED"}
        
        if rule_id == "R10":
            """CORONASHIELD: Jede YAML wird vor Speicherung validiert"""
            import os as _os
            akt = aktion.lower()
            
            # Nur bei write/edit von .yaml/.yml Dateien prüfen
            is_yaml_write = any(x in akt for x in [".yaml", ".yml"]) and ("write " in akt or "edit " in akt)
            
            if is_yaml_write:
                # Prüfe ob immune-check im Befehl ist
                has_immune = "immune" in akt or "CHECK_YAML" in akt or "corona" in akt
                if not has_immune:
                    return {"verletzt": True, "regel": rule["name"], "haerte": rule["haerte"],
                            "detail": "YAML-Edit ohne CORONASHIELD-Check — sub_mas-recovery-immune CHECK_YAML erforderlich!", "aktion": "BLOCKED"}
            
            return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}

        return {"verletzt": False, "regel": rule["name"], "haerte": rule["haerte"], "aktion": "OK"}
    
    return {"verletzt": False, "regel": "unbekannt", "aktion": "OK"}

def format_output(ergebnisse, action_typ=""):
    blocked = [r for r in ergebnisse if r.get("aktion") == "BLOCKED"]
    
    lines = []
    lines.append("=== ⛔ REGEL-CHECK ===")
    lines.append(f"Aktion: {action_typ}")
    lines.append(f"Geprueft: {len(ergebnisse)} Regeln")
    
    for r in ergebnisse:
        if r["haerte"] >= 5:
            lines.append(f"⛔⛔⛔⛔⛔ {r['regel']}: {r['aktion']} — {r.get('detail', 'ok')}")
        elif r["haerte"] >= 4:
            lines.append(f"⛔⛔⛔ {r['regel']}: {r['aktion']} — {r.get('detail', 'ok')}")
        else:
            lines.append(f"⛔ {r['regel']}: {r['aktion']} — {r.get('detail', 'ok')}")
    
    if blocked:
        lines.append(f"\n⛔⛔⛔⛔⛔ {len(blocked)} EXTREM-STARK VERSTOESSE!")
        lines.append("AKTION WURDE BLOCKIERT — User informieren")
        for b in blocked:
            lines.append(f"  → {b['regel']}: {b['detail']}")
        return "\n".join(lines), False
    else:
        lines.append("\n✅ Alle Regeln eingehalten — Aktion freigegeben")
        return "\n".join(lines), True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Regel-Check vor Aktionen")
    parser.add_argument("--check", help="Regel-ID (R01-R09)")
    parser.add_argument("--file", default=None, help="Betroffene Datei (fuer R09)")
    parser.add_argument("--action", default="", help="Geplante Aktion (z.B. 'edit file.yaml')")
    parser.add_argument("--mode", default="mas", help="Aktueller Modus")
    parser.add_argument("--all", action="store_true", help="Alle Regeln prüfen")
    parser.add_argument("--action-type", default="unbekannt", help="Typ der Aktion: write|edit|delegate|shell")
    
    args = parser.parse_args()
    
    action_info = f"{args.action_type}: {args.action}" if args.action else args.action_type
    
    if args.all:
        rules_5 = load_rules(REGEL_DATEI)
        # R09 IMMER ZUERST pruefen (oberste Regel)
        r09_result = check_rule("R09", args.action or "")
        if r09_result.get("verletzt"):
            ergebnisse = [r09_result]
        else:
            ergebnisse = [check_rule(r["id"], args.action or "") for r in rules_5]
        output, ok = format_output(ergebnisse, action_info)
        print(output)
        sys.exit(0 if ok else 1)
    elif args.check:
        ergebnis = check_rule(args.check, args.action or "")
        if ergebnis.get("verletzt"):
            print(f"⛔⛔⛔⛔⛔ REGEL-VERSTOSS: {ergebnis['regel']}")
            print(f"  Detail: {ergebnis['detail']}")
            print(f"  Aktion: {ergebnis['aktion']}")
            sys.exit(1)
        else:
            print(f"✅ {ergebnis['regel']}: OK")
            sys.exit(0)
    else:
        # Standard: alle EXTREM-STARK Regeln prüfen
        rules_5 = load_rules(REGEL_DATEI)
        ergebnisse = [check_rule(r["id"], args.action or "") for r in rules_5]
        output, ok = format_output(ergebnisse, action_info)
        print(output)
        sys.exit(0 if ok else 1)
