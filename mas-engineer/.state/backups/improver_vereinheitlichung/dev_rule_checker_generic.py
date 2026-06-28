#!/usr/bin/env python3
"""
dev_rule_checker_generic.py — Methode 9: Deterministischer Regel-Test (Generic)
Wird VOR jeder write/edit/shell Aktion aufgerufen.
Blockiert Aktionen bei Härte 5 ohne Bestätigung.
Exit-Code 0 = OK, Exit-Code 1 = BLOCKED

Generic: Keine MAS-Abhängigkeiten. Lädt User-Regeln aus .state/rules/regeln.yaml.
"""
import sys, os, yaml, time, json, argparse

REGEL_DATEI = ".state/rules/regeln.yaml"
BESTAETIGUNG_DATEI = ".state/.last_confirmation"

def load_regeln():
    if not os.path.exists(REGEL_DATEI):
        return []
    try:
        with open(REGEL_DATEI) as f:
            data = yaml.safe_load(f)
        return data.get("regeln", [])
    except: return []

def check_confirmation():
    if not os.path.exists(BESTAETIGUNG_DATEI):
        return False
    try:
        with open(BESTAETIGUNG_DATEI) as f:
            ts = int(f.read().strip())
        return int(time.time()) - ts < 300
    except: return False



def _check_tests(action):
    """Fuehrt pytest aus und blockiert wenn Tests fehlschlagen."""
    import subprocess as _sp, os as _os
    cwd = _os.getcwd()
    # Pruefe ob pytest existiert
    if not _os.path.exists(os.path.join(cwd, 'pytest.ini')) and not _os.path.exists(os.path.join(cwd, 'setup.cfg')) and not _os.path.exists(os.path.join(cwd, 'pyproject.toml')):
        # Kein pytest-Projekt -> Warnung aber erlauben
        return True, "kein pytest-Projekt"
    
    # Pruefe ob tests/ existiert
    if not _os.path.exists(os.path.join(cwd, 'tests')):
        return True, "kein tests/ Verzeichnis"
    
    try:
        r = _sp.run(['pytest', '--tb=short', '--quiet'], capture_output=True, text=True, timeout=10)
        if r.returncode > 0:
            # Extrahiere Fehler-Info
            errors = [l for l in r.stdout.split('\n') if 'failed' in l.lower() or 'error' in l.lower() or 'FAILED' in l]
            detail = errors[0][:80] if errors else "Tests fehlgeschlagen"
            return False, detail
        return True, "OK"
    except _sp.TimeoutExpired:
        return True, "Timeout (10s)"
    except FileNotFoundError:
        return True, "pytest nicht installiert"

def _get_project_profile(action=""):
    """Ermittelt Projekt-Profil (small/medium/large) anhand Datei-Anzahl."""
    import os as _os
    cwd = _os.getcwd()
    total = 0
    for root, dirs, files in _os.walk(cwd):
        if '.git' in dirs: dirs.remove('.git')
        if '__pycache__' in dirs: dirs.remove('__pycache__')
        total += len(files)
    
    if total < 20: return "small", total
    if total < 80: return "medium", total
    return "large", total


def _check_profile_rule(rule_id, haerte):
    """Prueft ob Regel fuer aktuelles Profil aktiv ist."""
    profile, total = _get_project_profile()
    # small: nur R01+R09
    if profile == "small":
        return rule_id in ["R01", "R09"]
    # medium: R01-R04+R09
    if profile == "medium":
        return rule_id in ["R01", "R02", "R03", "R04", "R09"]
    # large: alle
    return True

def check_rule(rule, aktion=""):
    name = rule.get("name", "")
    haerte = rule.get("haerte", 1)
    block = rule.get("block", False)
    rule_id = rule.get("id", "")
    akt = aktion.lower()
    
    # Scale-Profile: Nur aktive Regeln pruefen
    if not _check_profile_rule(rule_id, haerte):
        return {"verletzt": False, "regel": name, "haerte": haerte, "aktion": "SKIPPED (profil)"}
    
    # R01: BESTAETIGUNGSPFLICHT (Generic: immer wenn block=True)
    if rule_id == "R01" and block:
        if not check_confirmation():
            return {"verletzt": True, "regel": name, "haerte": haerte,
                    "detail": "Keine Bestaetigung in den letzten 5 Minuten", "aktion": "BLOCKED"}
    
    # R02: BESTAND_PRUFUNG  
    if rule_id == "R02":
        import os as _os, yaml as _yaml
        path = None
        for prefix in ["write ", "edit ", "cp ", "mv "]:
            if prefix in akt:
                path = akt.split(prefix)[-1].split()[0].strip()
                break
        
        if path and not path.startswith("/"):
            cwd = _os.getcwd()
            full_path = _os.path.join(cwd, path) if not _os.path.isabs(path) else path
            
            # Pruefe special_agents.yaml (User-Projekt)
            special_path = _os.path.join(cwd, ".state/agents/special_agents.yaml")
            if _os.path.exists(special_path):
                with open(special_path) as _f:
                    special = _yaml.safe_load(_f)
                if special and "agents" in special:
                    fname = _os.path.basename(path)
                    base_name = fname.replace(".yaml", "")
                    if base_name in special["agents"]:
                        return {"verletzt": False, "regel": name, "haerte": haerte,
                                "detail": f"Spezial-Agent: {base_name}", "aktion": "OK"}
            
            if _os.path.exists(full_path) and "force" not in akt:
                return {"verletzt": True, "regel": name, "haerte": haerte,
                        "detail": f"Ziel existiert bereits: {path}", "aktion": "BLOCKED"}
    regeln = load_regeln()
    ergebnisse = [check_rule(r, aktion) for r in regeln]
    blocked = [r for r in ergebnisse if r.get("aktion") == "BLOCKED"]
    print(f"=== ⛔ REGEL-CHECK (Generic) ===")
    print(f"Aktion: {aktion or '(keine)'}")
    print(f"Geprueft: {len(ergebnisse)} Regeln")
    for r in ergebnisse:
        if r.get("verletzt"):
            h = r.get("haerte", 1)
            sym = "⛔⛔⛔⛔⛔" if h >= 5 else "⛔⛔⛔" if h >= 4 else "⛔"
            print(f"{sym} {r['regel']}: {r['aktion']} — {r.get('detail','')}")
        else:
            print(f"  ✅ {r['regel']}: OK")
    if blocked:
        print(f"\n⛔ {len(blocked)} BLOCKED — Aktion gestoppt")
        return False
    print(f"\n✅ Alle Regeln eingehalten — Aktion freigegeben")
    return True


def cmd_health():
    """Checker-Health: JSON-Report ueber Checker-Zustand."""
    import json as _j, time as _t
    status = {"status": "healthy", "checks": [], "timestamp": _t.strftime("%Y-%m-%dT%H:%M:%S")}
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    reg_path = os.path.join(base, ".state/rules/regeln.yaml")
    if os.path.exists(reg_path):
        status["checks"].append({"name": "regeln_exists", "ok": True})
        try:
            yaml.safe_load(open(reg_path))
            status["checks"].append({"name": "regeln_valid", "ok": True})
        except:
            status["checks"].append({"name": "regeln_valid", "ok": False})
    else:
        status["checks"].append({"name": "regeln_exists", "ok": False})
    
    conf_path = os.path.join(base, ".state/.last_bestaetigung")
    if os.path.exists(conf_path):
        try:
            ts = int(open(conf_path).read().strip())
            status["checks"].append({"name": "confirmation_valid", "ok": (_t.time() - ts) < 300})
        except:
            status["checks"].append({"name": "confirmation_valid", "ok": False})
    else:
        status["checks"].append({"name": "confirmation_valid", "ok": False})
    
    ok_count = sum(1 for c in status["checks"] if c["ok"])
    status["score"] = round(ok_count / len(status["checks"]) * 10, 1) if status["checks"] else 0
    print(_j.dumps(status, indent=2))
    return 0


def _run_main_safe():
    """Graceful degradation bei Fehlern."""
    import sys, os, yaml, time, json, argparse
    action = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    try:
        if action:
            ok, msg = check_user_imports(action)
            if not ok:
                print(f"SAFE: {msg}")
                return
            ok, msg = check_domain_isolation_generic(action)
            if not ok:
                print(f"SAFE: {msg}")
                return
        print("SAFE: OK")
        sys.exit(0)
    except Exception as e:
        print(f"SAFE: {e} -> frei")
        sys.exit(0)



def cmd_undo_last_rule():
    """Entfernt die zuletzt generierte Regel aus regeln.yaml."""
    import json as _j, shutil as _sh, time as _t
    
    # Lese Strikes-Log
    strike_file = os.path.expanduser("~/.config/goose/.rule_strikes.json")
    if not os.path.exists(strike_file):
        print("❌ Keine generierten Regeln gefunden")
        return 1
    
    with open(strike_file) as f:
        strikes = _j.load(f)
    
    generated = strikes.get("generated_rules", [])
    if not generated:
        print("❌ Keine generierten Regeln im Log")
        return 1
    
    last = generated[-1]
    rid = last["id"]
    atype = last.get("action_type", "unbekannt")
    
    # Pruefe ob Backup existiert
    reg_path = ".state/rules/regeln.yaml"
    backup_path = reg_path + ".bak.auto"
    
    if os.path.exists(backup_path):
        # Stelle Backup wieder her
        _sh.copy2(backup_path, reg_path)
        os.remove(backup_path)
        print(f"🔄 Backup wiederhergestellt — {rid} entfernt")
    else:
        # Fallback: Lese regeln.yaml und entferne Regel manuell
        import yaml
        with open(reg_path) as f:
            data = yaml.safe_load(f) or {"version": "1.0.0", "regeln": []}
        
        data["regeln"] = [r for r in data["regeln"] if r.get("id") != rid]
        with open(reg_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"🔄 Regel {rid} aus regeln.yaml entfernt")
    
    # Entferne aus Log
    generated.pop()
    strikes["generated_rules"] = generated
    with open(strike_file, 'w') as f:
        _j.dump(strikes, f, indent=2)
    
    print(f"  Grund: {atype}")
    print(f"  Noch im Log: {len(generated)} Regeln")
    return 0

def main():
    import sys
    if '--require-tests-pass' in sys.argv and action:
        ok, msg = _check_tests(action)
        if not ok:
            print(f"\u26a0\ufe0f TESTS-FEHLER: {msg}")
            sys.exit(1)
    if '--undo-last-rule' in sys.argv:
        return cmd_undo_last_rule()
    if '--health' in sys.argv:
        return cmd_health()
    if '--safe' in sys.argv:
        try:
            return _run_main_safe()
        except Exception as e:
            print(f"SAFE: {e} -> frei")
            sys.exit(0)
    action = " ".join([a for a in sys.argv[1:] if not a.startswith('--')])
    if action and ('--action' in sys.argv or '--all' in sys.argv):
        ok, msg = check_user_imports(action)
        if not ok:
            print(f"⛔⛔⛔⛔⛔ R09-GEN: {msg}")
            sys.exit(1)
        ok, msg = check_domain_isolation_generic(action)
        if not ok:
            print(f"⛔⛔⛔⛔⛔ R09: {msg}")
            sys.exit(1)
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", help="Rule-ID")
    parser.add_argument("--action", default="", help="Geplante Aktion")
    parser.add_argument("--all", action="store_true", help="Alle Regeln")
    parser.add_argument("--confirm", action="store_true", help="Bestaetigung speichern")
    args = parser.parse_args()

    if args.confirm:
        with open(BESTAETIGUNG_DATEI, "w") as f:
            f.write(str(int(time.time())))
        print("✅ Bestaetigung gespeichert (5 Minuten gueltig)")
        sys.exit(0)

    if args.action:
        check_strikes(args.action)

    if args.check:
        for r in load_regeln():
            if r.get("id") == args.check:
                e = check_rule(r, args.action)
                if e.get("verletzt"):
                    print(f"⛔ {e['regel']}: {e['detail']}"); sys.exit(1)
                print(f"✅ {e['regel']}: OK"); sys.exit(0)
        print(f"❌ Regel '{args.check}' nicht gefunden"); sys.exit(1)

    ok = check_all(args.action)
    sys.exit(0 if ok else 1)




STRIKE_FILE = os.path.expanduser("~/.config/goose/.rule_strikes.json")

def check_strikes(action):
    """Zaehlt 3 gleiche Blockierungen -> automatische Regel."""
    if not os.path.exists(STRIKE_FILE):
        strikes = {}
        with open(STRIKE_FILE, 'w') as f:
            json.dump(strikes, f)
        return
    try:
        with open(STRIKE_FILE) as f:
            strikes = json.load(f)
    except:
        strikes = {}
    
    aktion_type = analyse_action_type(action)
    if not aktion_type:
        return
    
    strikes[aktion_type] = strikes.get(aktion_type, 0) + 1
    with open(STRIKE_FILE, 'w') as f:
        json.dump(strikes, f)
    
    if strikes[aktion_type] >= 3:
        generiere_regel(aktion_type)
        del strikes[aktion_type]
        with open(STRIKE_FILE, 'w') as f:
            json.dump(strikes, f)
        print(f"  ✅ Auto-Regel generiert fuer: {aktion_type}")

def analyse_action_type(action):
    act = action.lower()
    if "/etc/" in act and ("write" in act or "edit" in act):
        return "system_config"
    if "import os" in act or "import subprocess" in act:
        return "forbidden_import"
    if "import requests" in act or "import socket" in act:
        return "network_import"
    if "/tmp/" in act and ("write" in act or "edit" in act):
        return "temp_files"
    return None

def generiere_regel(aktion_type):
    # Rule-Snapshot: Backup vor Aenderung
    reg_path = ".state/rules/regeln.yaml"
    if os.path.exists(reg_path):
        import shutil as _sh
        _sh.copy2(reg_path, reg_path + ".bak.auto")
    
    rule_map = {
        "system_config": ("R-GEN-001", "System-Konfiguration blockiert", 5, "Schreibe NIEMALS in /etc/"),
        "forbidden_import": ("R-GEN-002", "Import-Kontrolle verschaerft", 5, "Importiere NIEMALS os/subprocess"),
        "network_import": ("R-GEN-003", "Netzwerk-Import blockiert", 5, "Keine Netzwerk-Imports erlaubt"),
        "temp_files": ("R-GEN-004", "Temp-Dateien blockiert", 4, "Temp-Dateien nur mit Bestaetigung"),
    }
    if aktion_type not in rule_map:
        return
    
    rid, name, haerte, text = rule_map[aktion_type]
    
    # Lese regeln.yaml
    reg_path = ".state/rules/regeln.yaml"
    if not os.path.exists(reg_path):
        return
    
    with open(reg_path) as f:
        data = yaml.safe_load(f) or {"version": "1.0.0", "regeln": []}
    
    # Pruefe ob Regel bereits existiert
    existing = [r for r in data.get("regeln", []) if r.get("id") == rid]
    if existing:
        # Erhoehe Haerte
        for r in data["regeln"]:
            if r["id"] == rid:
                r["haerte"] = min(r.get("haerte", 3) + 1, 5)
                break
        print(f"  ⬆️  {rid}: Haerte erhoeht auf {min(existing[0].get('haerte',3)+1,5)}")
    else:
        data["regeln"].append({
            "id": rid, "name": name, "haerte": haerte,
            "text": f"⛔⛔⛔⛔⛔ {name}",
            "prompt_text": text,
            "block": True,
            "check": f"python3 tools/dev_rule_checker_generic.py --check {rid} --action {{aktion}}"
        })
        print(f"  ➕ {rid}: {name} (H={haerte})")
    
    with open(reg_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

def check_user_imports(action):
    """Blockt gefaehrliche Imports fuer User-Framework."""
    allowed = ['json', 'yaml', 'datetime', 'os.path', 'typing', 're']
    blocked = ['os', 'subprocess', 'requests', 'socket', 'http',
               'shutil', 'glob', 'sys', 'multiprocessing', 'threading']
    
    if 'import ' not in action and 'from ' not in action:
        return True, 'KEIN IMPORT'
    
    for imp in blocked:
        if f'import {imp}' in action or f'from {imp}' in action:
            return False, f'IMPORT BLOCKED: {imp} ist nicht erlaubt'
    
    for w in allowed:
        if f'import {w}' in action or f'from {w}' in action:
            return True, f'IMPORT OK: {w}'
    
    for part in action.split():
        if part == 'import' or part == 'from':
            continue
        if part.startswith('import'):
            imp = part.replace('import', '').strip()
            if imp and imp not in allowed and imp not in blocked:
                return False, f'IMPORT NICHT IN WHITELIST: {imp}'
    
    return True, 'OK'

def check_domain_isolation_generic(aktion):
    """R09 für Generic: Prüft ob Aktion eine fremde Domain betrifft."""
    import os, yaml
    reg_path = os.path.expanduser("~/.config/goose/.active_domain")
    if not os.path.exists(reg_path):
        return True, "Keine active_domain"
    with open(reg_path) as f:
        active = f.read().strip()
    
    registry = os.path.join(os.path.abspath("."), "mas-engineer/.state/domains/registry.yaml")
    if not os.path.exists(registry):
        return True, "Keine registry"
    with open(registry) as f:
        reg = yaml.safe_load(f) or {}
    
    akt = aktion.lower()
    for dname, dconf in reg.get("domains", {}).items():
        if dname == active:
            continue
        dp = dconf.get("path", dname).rstrip("/").lower()
        if f"import {dname}" in akt or f"from {dname}" in akt:
            return False, f"Generic importiert {dname} — VERBOTEN!"
        if dp in akt and any(x in akt for x in ["write ", "edit ", "cp ", "mv ", "rm ", ">"]):
            return False, f"Generic schreibt in {dname} — VERBOTEN!"
    return True, "OK"


if __name__ == "__main__":
    main()
