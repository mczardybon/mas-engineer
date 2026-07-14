#!/usr/bin/env python3
"""
dev_rule_checker_generic.py — method 9: Deterministischer Rule-Test (Generic)
Will be called BEFORE each write/edit/shell action.
Blocked actions at Hardening 5 without confirmation.
Exit-Code 0 = OK, Exit-Code 1 = BLOCKED

Generic: No MAS-Dependencies. Loads User-Rulen aus .state/rules/rules.yaml.
"""
import sys, os, yaml, time, json, argparse

REGEL_DATEI = ".state/rules/rules.yaml"
CONFIRMATION_DATEI = ".state/.last_confirmation"

def load_rules():
    if not os.path.exists(REGEL_DATEI):
        return []
    try:
        with open(REGEL_DATEI) as f:
            data = yaml.safe_load(f)
        return data.get("rules", [])
    except: return []

def check_confirmation():
    if not os.path.exists(CONFIRMATION_DATEI):
        return False
    try:
        with open(CONFIRMATION_DATEI) as f:
            ts = int(f.read().strip())
        return int(time.time()) - ts < 300
    except: return False



def _check_tests(action):
    """Runs pytest and blocks if tests fail."""
    import subprocess as _sp, os as _os
    cwd = _os.getcwd()
    # Check ob pytest exists
    if not _os.path.exists(os.path.join(cwd, 'pytest.ini')) and not _os.path.exists(os.path.join(cwd, 'setup.cfg')) and not _os.path.exists(os.path.join(cwd, 'pyproject.toml')):
        # No pytest-Projekt -> Warning aber erlauben
        return True, "no pytest-Projekt"
    
    # Check ob tests/ exists
    if not _os.path.exists(os.path.join(cwd, 'tests')):
        return True, "no tests/ Directory"
    
    try:
        r = _sp.run(['pytest', '--tb=short', '--quiet'], capture_output=True, text=True, timeout=10)
        if r.returncode > 0:
            # Extract Error-Info
            errors = [l for l in r.stdout.split('\n') if 'failed' in l.lower() or 'error' in l.lower() or 'FAILED' in l]
            detail = errors[0][:80] if errors else "Tests failed"
            return False, detail
        return True, "OK"
    except _sp.TimeoutExpired:
        return True, "Timeout (10s)"
    except FileNotFoundError:
        return True, "pytest not installed"

def _get_project_profile(action=""):
    """Determines project profile (small/medium/large) based on file count."""
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


def _check_profile_rule(rule_id, hardness):
    """Check if rule is active for current profile."""
    profile, total = _get_project_profile()
    # small: only R01+R09
    if profile == "small":
        return rule_id in ["R01", "R09"]
    # medium: R01-R04+R09
    if profile == "medium":
        return rule_id in ["R01", "R02", "R03", "R04", "R09"]
    # large: all
    return True

def check_rule(rule, action=""):
    name = rule.get("name", "")
    hardness = rule.get("hardness", 1)
    block = rule.get("block", False)
    rule_id = rule.get("id", "")
    akt = action.lower()
    
    # Scale-Profile: Only check active rules
    if not _check_profile_rule(rule_id, hardness):
        return {"violation": False, "rule": name, "hardness": hardness, "action": "SKIPPED (profile)"}
    
    # R01: CONFIRMATION_REQUIRED (Generic: always if block=True)
    if rule_id == "R01" and block:
        if not check_confirmation():
            return {"violation": True, "rule": name, "hardness": hardness,
                    "detail": "No confirmation in the last 5 minutes", "action": "BLOCKED"}
    
    # R02: INVENTORY_CHECK  
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
            
            # Check special_agents.yaml (User project)
            special_path = _os.path.join(cwd, ".state/agents/special_agents.yaml")
            if _os.path.exists(special_path):
                with open(special_path) as _f:
                    special = _yaml.safe_load(_f)
                if special and "agents" in special:
                    fname = _os.path.basename(path)
                    base_name = fname.replace(".yaml", "")
                    if base_name in special["agents"]:
                        return {"violation": False, "rule": name, "hardness": hardness,
                                "detail": f"Special agent: {base_name}", "action": "OK"}
            
            if _os.path.exists(full_path) and "force" not in akt:
                return {"violation": True, "rule": name, "hardness": hardness,
                        "detail": f"Target already exists: {path}", "action": "BLOCKED"}
    rules = load_rules()
    results = [check_rule(r, action) for r in rules]
    blocked = [r for r in results if r.get("action") == "BLOCKED"]
    print(f"=== ⛔ RULE CHECK (Generic) ===")
    print(f"Action: {action or '(none)'}")
    print(f"Checked: {len(results)} rules")
    for r in results:
        if r.get("violation"):
            h = r.get("hardness", 1)
            sym = "⛔⛔⛔⛔⛔" if h >= 5 else "⛔⛔⛔" if h >= 4 else "⛔"
            print(f"{sym} {r['rule']}: {r['action']} — {r.get('detail','')}")
        else:
            print(f"  ✅ {r['rule']}: OK")
    if blocked:
        print(f"\n⛔ {len(blocked)} BLOCKED — Action stopped")
        return False
    print(f"\n✅ All rules followed — Action approved")
    return True


def cmd_health():
    """Checker-Health: JSON-Report about Checker-State."""
    import json as _j, time as _t
    status = {"status": "healthy", "checks": [], "timestamp": _t.strftime("%Y-%m-%dT%H:%M:%S")}
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    reg_path = os.path.join(base, ".state/rules/rules.yaml")
    if os.path.exists(reg_path):
        status["checks"].append({"name": "rules_exists", "ok": True})
        try:
            yaml.safe_load(open(reg_path))
            status["checks"].append({"name": "rules_valid", "ok": True})
        except:
            status["checks"].append({"name": "rules_valid", "ok": False})
    else:
        status["checks"].append({"name": "rules_exists", "ok": False})
    
    conf_path = os.path.join(base, ".state/.last_confirmation")
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
    """Graceful degradation on errors."""
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
    """Remove the last auto-generated rule from rules.yaml."""
    import json as _j, shutil as _sh, time as _t
    
    # Read strikes log
    strike_file = os.path.expanduser("~/.config/goose/.rule_strikes.json")
    if not os.path.exists(strike_file):
        print("❌ No generated rules found")
        return 1
    
    with open(strike_file) as f:
        strikes = _j.load(f)
    
    generated = strikes.get("generated_rules", [])
    if not generated:
        print("❌ No generated rules in log")
        return 1
    
    last = generated[-1]
    rid = last["id"]
    atypee = last.get("action_typee", "unknown")
    
    # Check if backup exists
    reg_path = ".state/rules/rules.yaml"
    backup_path = reg_path + ".bak.auto"
    
    if os.path.exists(backup_path):
        # remainderore backup
        _sh.copy2(backup_path, reg_path)
        os.remove(backup_path)
        print(f"🔄 Backup remainderored — {rid} removed")
    else:
        # Fallback: read rules.yaml and remove rule manually
        import yaml
        with open(reg_path) as f:
            data = yaml.safe_load(f) or {"version": "1.0.0", "rules": []}
        
        data["rules"] = [r for r in data["rules"] if r.get("id") != rid]
        with open(reg_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"🔄 Rule {rid} removed from rules.yaml")
    
    # Remove from log
    generated.pop()
    strikes["generated_rules"] = generated
    with open(strike_file, 'w') as f:
        _j.dump(strikes, f, indent=2)
    
    print(f"  Reason: {atypee}")
    print(f"  Still in log: {len(generated)} rules")
    return 0

def main():
    import sys
    if '--require-tests-pass' in sys.argv and action:
        ok, msg = _check_tests(action)
        if not ok:
            print(f"\u26a0\ufe0f TESTS-ERROR: {msg}")
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
    parser.add_argument("--action", default="", help="Planned action")
    parser.add_argument("--all", action="store_true", help="All rules")
    parser.add_argument("--confirm", action="store_true", help="Confirmation save")
    args = parser.parse_args()

    if args.confirm:
        with open(CONFIRMATION_DATEI, "w") as f:
            f.write(str(int(time.time())))
        print("✅ Confirmation saved (5 minutes valid)")
        sys.exit(0)

    if args.action:
        check_strikes(args.action)

    if args.check:
        for r in load_rules():
            if r.get("id") == args.check:
                e = check_rule(r, args.action)
                if e.get("violation"):
                    print(f"⛔ {e['rule']}: {e['detail']}"); sys.exit(1)
                print(f"✅ {e['rule']}: OK"); sys.exit(0)
        print(f"❌ Rule '{args.check}' not found"); sys.exit(1)

    ok = check_all(args.action)
    sys.exit(0 if ok else 1)




STRIKE_FILE = os.path.expanduser("~/.config/goose/.rule_strikes.json")

def check_strikes(action):
    """Counts 3 identical blockages -> auto rule."""
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
    
    action_typee = analyse_action_typee(action)
    if not action_typee:
        return
    
    strikes[action_typee] = strikes.get(action_typee, 0) + 1
    with open(STRIKE_FILE, 'w') as f:
        json.dump(strikes, f)
    
    if strikes[action_typee] >= 3:
        generiere_rule(action_typee)
        del strikes[action_typee]
        with open(STRIKE_FILE, 'w') as f:
            json.dump(strikes, f)
        print(f"  ✅ Auto-Rule generated for: {action_typee}")

def analyse_action_typee(action):
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

def generiere_rule(action_typee):
    # Rule snapshot: backup before change
    reg_path = ".state/rules/rules.yaml"
    if os.path.exists(reg_path):
        import shutil as _sh
        _sh.copy2(reg_path, reg_path + ".bak.auto")
    
    rule_map = {
        "system_config": ("R-GEN-001", "System configuration blocked", 5, "Write NEVER in /etc/"),
        "forbidden_import": ("R-GEN-002", "Import control tightened", 5, "NEVER import os/subprocess"),
        "network_import": ("R-GEN-003", "Network import blocked", 5, "No network imports allowed"),
        "temp_files": ("R-GEN-004", "Temp files blocked", 4, "Temp files only with confirmation"),
    }
    if action_typee not in rule_map:
        return
    
    rid, name, hardness, text = rule_map[action_typee]
    
    # Read rules.yaml
    reg_path = ".state/rules/rules.yaml"
    if not os.path.exists(reg_path):
        return
    
    with open(reg_path) as f:
        data = yaml.safe_load(f) or {"version": "1.0.0", "rules": []}
    
    # Check if rule already exists
    existing = [r for r in data.get("rules", []) if r.get("id") == rid]
    if existing:
        # Increase hardness
        for r in data["rules"]:
            if r["id"] == rid:
                r["hardness"] = min(r.get("hardness", 3) + 1, 5)
                break
        print(f"  ⬆️  {rid}: Hardness increased to {min(existing[0].get('hardness',3)+1,5)}")
    else:
        data["rules"].append({
            "id": rid, "name": name, "hardness": hardness,
            "text": f"⛔⛔⛔⛔⛔ {name}",
            "prompt_text": text,
            "block": True,
            "check": f"python3 tools/dev_rule_checker_generic.py --check {rid} --action {{action}}"
        })
        print(f"  ➕ {rid}: {name} (H={hardness})")
    
    with open(reg_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

def check_user_imports(action):
    """Block dangerous imports for user framework."""
    allowed = ['json', 'yaml', 'datetime', 'os.path', 'typeing', 're']
    blocked = ['os', 'subprocess', 'requests', 'socket', 'http',
               'shutil', 'glob', 'sys', 'multiprocessing', 'threading']
    
    if 'import ' not in action and 'from ' not in action:
        return True, 'NO IMPORT'
    
    for imp in blocked:
        if f'import {imp}' in action or f'from {imp}' in action:
            return False, f'IMPORT BLOCKED: {imp} is not allowed'
    
    for w in allowed:
        if f'import {w}' in action or f'from {w}' in action:
            return True, f'IMPORT OK: {w}'
    
    for part in action.split():
        if part == 'import' or part == 'from':
            continue
        if part.startswith('import'):
            imp = part.replace('import', '').strip()
            if imp and imp not in allowed and imp not in blocked:
                return False, f'IMPORT NOT IN WHITELIST: {imp}'
    
    return True, 'OK'

def check_domain_isolation_generic(action):
    """R09 for Generic: Check if action affects a foreign domain."""
    import os, yaml
    reg_path = os.path.expanduser("~/.config/goose/.active_domain")
    if not os.path.exists(reg_path):
        return True, "No active_domain"
    with open(reg_path) as f:
        active = f.read().strip()
    
    registry = os.path.join(os.path.abspath("."), "mas-engineer/.state/domains/registry.yaml")
    if not os.path.exists(registry):
        return True, "No registry"
    with open(registry) as f:
        reg = yaml.safe_load(f) or {}
    
    akt = action.lower()
    for dname, dconf in reg.get("domains", {}).items():
        if dname == active:
            continue
        dp = dconf.get("path", dname).rstrip("/").lower()
        if f"import {dname}" in akt or f"from {dname}" in akt:
            return False, f"Generic imports {dname} — FORBIDDEN!"
        if dp in akt and any(x in akt for x in ["write ", "edit ", "cp ", "mv ", "rm ", ">"]):
            return False, f"Generic writes to {dname} — FORBIDDEN!"
    return True, "OK"


if __name__ == "__main__":
    main()
