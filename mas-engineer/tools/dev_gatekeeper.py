#!/usr/bin/env python3
"""
dev_gatekeeper.py — Pre-Execute-Hook (R01 + R18 + R19 + R20 + R10 + R05 + Matrix)
Will VOR jeder write/edit/shell/delete-Aktion aufgerufen.
BLOCKED if eine Rule verletzt ist.

Aufruf: python3 dev_gatekeeper.py --write path --content "..."
        python3 dev_gatekeeper.py --edit path --before "X" --after "Y"
        python3 dev_gatekeeper.py --shell "befehl"
        python3 dev_gatekeeper.py --delete path
        python3 dev_gatekeeper.py --check-lock   # Lock-Status check
        python3 dev_gatekeeper.py --check-matrix   # Matrix-Check
          [--action shell] [--file path] [--cmd "befehl"]
"""

import sys, os, json, subprocess, time, datetime

MAS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(MAS_DIR, ".state")
CONFIRMATION_DATEI = os.path.join(STATE_DIR, ".last_confirmation")
AUDIT_DATEI = os.path.join(STATE_DIR, "audit.log.jsonl")
LOCK_DATEI = os.path.join(STATE_DIR, ".disziplin_lock")

def alog(aktion, agent, ziel, status, rule=""):
    """Audit-Log entry (JSON-Lines)"""
    os.makedirs(STATE_DIR, exist_ok=True)
    e = {"ts": datetime.datetime.now().isoformat(), "aktion": aktion,
         "agent": agent, "ziel": str(ziel)[:200], "status": status, "rule": rule}
    with open(AUDIT_DATEI, 'a') as f:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')
    if status == "CRITICAL":
        with open(LOCK_DATEI, 'w') as f:
            f.write(f"CRITICAL: {rule} - {aktion} um {e['ts']}\n")

def check_lock():
    if os.path.exists(LOCK_DATEI):
        print(f"🔴 MAS GEFRIERT: {open(LOCK_DATEI).read().strip()}")
        sys.exit(1)

def check_r01():
    if not os.path.exists(CONFIRMATION_DATEI):
        return (False, "No .last_confirmation")
    with open(CONFIRMATION_DATEI) as f:
        ts = int(f.read().strip())
    if int(time.time()) - ts > 300:
        return (False, "Confirmation >5 Min abgelaufen")
    return (True, "")

def check_r18(aktion_str):
    if not os.path.exists(AUDIT_DATEI):
        return (False, "No Audit-Log")
    with open(AUDIT_DATEI) as f:
        zeilen = [z for z in f.read().strip().split('\n') if z.strip()]
    if not zeilen:
        return (False, "Audit-Log empty")
    letzter = json.loads(zeilen[-1])
    if letzter.get("aktion") == "DELEGATE" and "action-executor" in letzter.get("ziel",""):
        return (True, "")
    return (False, f"Letzte Aktion: {letzter.get('aktion')}, not DELEGATE")

def check_r19(aktion_str, at):
    if at in ("write","edit","delete"):
        path = aktion_str.split()[-1]
        if path.startswith("/home") and "mas-engineer" not in path:
            return (False, f"Target outside MAS: {path}")
        if ".git/" in path:
            return (False, ".git/ verboten")
        return (True, "")
    if at == "shell":
        if "mas-engineer/tools/" in aktion_str and "dev_build" not in aktion_str and "dev_install" not in aktion_str:
            return (False, "Source-Tool-Path — no Build/Install")
        return (True, "")
    return (True, "")

def check_r20(at):
    # Gatekeeper selbst may always (er ist System)
    return (True, "")

def check_r10(at, aktion_str, inhalt=""):
    if at not in ("write","edit"): return (True, "")
    ziel = aktion_str.split()[-1] if aktion_str else ""
    if not ziel.endswith(('.yaml','.yml')): return (True, "")
    if not inhalt: return (True, "")
    try:
        import yaml; yaml.safe_load(inhalt); return (True, "")
    except Exception as e:
        return (False, f"YAML-Error: {e}")

def check_r05(at):
    if at not in ("write","edit","delete"): return (True, "")
    cp_dir = os.path.join(STATE_DIR, "checkpoints")
    if not os.path.exists(cp_dir): return (False, "No Checkpoint-Directory")
    cps = os.listdir(cp_dir)
    if not cps: return (False, "No Checkpoints")
    jetzt = time.time()
    for cp in sorted(cps, reverse=True)[:3]:
        ts = int(cp.split('_')[-1]) if '_' in cp else 0
        if ts and jetzt - ts < 1800: return (True, "")
    return (False, "No Checkpoint <30 Min")

def check_responsibility_matrix(action_type, filepath=None, cmd=None):
    """
    Checks ob eine Aktion durch die Responsibility-Matrix abgedeckt ist.
    
    Returns:
        (status, agent_name, task)
        - ("delegate", "sub_mas-xxx", "TASK") → an thesen Agenten delegate
        - ("self", None, None) → selbst execute (read_exception)
        - ("blocked", None, None) → no Sub-Agent responsible
    """
    import yaml
    
    # Matrix-Pathe: current Workspace > Install
    matrix_path = os.path.join(os.getcwd(), "mas-engineer", ".state", "rules", "responsibility_matrix.yaml")
    if not os.path.exists(matrix_path):
        matrix_path = os.path.expanduser("~/.config/goose/recipes/../mas-engineer/.state/rules/responsibility_matrix.yaml")
    
    if not os.path.exists(matrix_path):
        return ("error", None, f"Matrix not found: {matrix_path}")
    
    with open(matrix_path) as f:
        matrix = yaml.safe_load(f)
    
    # 1. Check read_exceptions
    if action_type == "shell" and cmd:
        cmd_base = cmd.split()[0] if cmd else ""
        for exc in matrix.get("read_exceptions", []):
            if exc.get("action") == "shell" and cmd_base in exc.get("cmds", []):
                return ("self", None, None)
    
    if action_type in ["load", "delegate"]:
        return ("self", None, None)
    
    # 2. Check file_map (Path-basiert)
    if filepath:
        for pattern, mapping in matrix.get("file_map", {}).items():
            if pattern in filepath or (filepath and filepath.endswith(pattern.replace("*", ""))):
                agent = mapping.get(action_type)
                if agent:
                    return ("delegate", agent, None)
    
    # 3. Check action_map
    entry = matrix.get("action_map", {}).get(action_type)
    if entry:
        agent = entry.get("agent")
        if agent is None:
            return ("self", None, None)
        return ("delegate", agent, entry.get("task"))
    
    # 4. Nothing found
    return ("blocked", None, f"No Sub-Agent for Aktion '{action_type}'")

PRUEF_MATRIX = {
    "write": ["R01","R18","R19","R20","R10","R05"],
    "edit":  ["R01","R18","R19","R20","R10","R05"],
    "shell": ["R01","R18","R19","R20","R05"],
    "delete":["R01","R18","R19","R20","R05"],
}

def main():
    check_lock()
    
    # --check-lock Modus
    if "--check-lock" in sys.argv:
        print("✅ Lock-Check: MAS not gefroren")
        sys.exit(0)
    
    # --check-matrix Modus
    if "--check-matrix" in sys.argv:
        cmd_args = {}
        for i, a in enumerate(sys.argv[1:], 1):
            if a.startswith("--") and "=" in a:
                key, val = a.lstrip('-').split("=", 1)
                cmd_args[key] = val
            elif a.startswith("--") and not a.startswith("--check") and i+1 < len(sys.argv):
                nxt = sys.argv[i+1]
                if not nxt.startswith("--"):
                    cmd_args[a.lstrip('-')] = nxt
        action = cmd_args.get("action", "shell")
        filepath = cmd_args.get("file", None)
        cmd_val = cmd_args.get("cmd", None)
        status, agent, task = check_responsibility_matrix(action, filepath, cmd_val)
        print(json.dumps({"status": status, "agent": agent, "task": str(task)}))
        sys.exit(0)

    if len(sys.argv) < 3:
        print("❌ Aufruf: dev_gatekeeper.py --write|--edit|--shell|--delete path [--content ...]")
        sys.exit(1)

    at = sys.argv[1].lstrip('-')
    if at not in ("write","edit","shell","delete"):
        print(f"❌ Unbekannte Aktion: {at}"); sys.exit(1)

    global aktion_str; aktion_str = " ".join(sys.argv[2:])
    inhalt = ""
    if "--content" in sys.argv:
        idx = sys.argv.index("--content"); inhalt = sys.argv[idx+1]
    elif "--stdin" in sys.argv:
        inhalt = sys.stdin.read()

    error = []
    for rule in PRUEF_MATRIX.get(at, []):
        if rule == "R01": ok, det = check_r01()
        elif rule == "R18": ok, det = check_r18(aktion_str)
        elif rule == "R19": ok, det = check_r19(aktion_str, at)
        elif rule == "R20": ok, det = check_r20(at)
        elif rule == "R10": ok, det = check_r10(at, aktion_str, inhalt)
        elif rule == "R05": ok, det = check_r05(at)
        else: ok, det = True, ""
        if not ok:
            error.append(f"{rule}: {det}")
            alog("BLOCKED", "gatekeeper", aktion_str, "BLOCKED", rule)

    if error:
        print(f"❌❌❌ GATEKEEPER BLOCKED: {len(error)} Violations")
        for f in error: print(f"  ⛔ {f}")
        sys.exit(1)

    print(f"✅ Gatekeeper: {len(PRUEF_MATRIX.get(at,[]))} Rulen bestanden")
    alog(at.upper(), "gatekeeper", aktion_str, "OK", "")

    if at == "shell":
        result = subprocess.run(sys.argv[2:], capture_output=True, text=True)
        print(result.stdout, end="")
        if result.stderr: print(result.stderr, end="", file=sys.stderr)
        sys.exit(result.returncode)
    elif at == "write":
        path = sys.argv[2]
        with open(path, 'w') as f: f.write(inhalt)
        print(f"✅ {path} written ({len(inhalt)} bytes)")
    elif at == "edit":
        path = sys.argv[2]
        if "--before" in sys.argv and "--after" in sys.argv:
            ib = sys.argv.index("--before"); ia = sys.argv.index("--after")
            before, after = sys.argv[ib+1], sys.argv[ia+1]
            with open(path) as f: c = f.read()
            if before not in c:
                print(f"❌ 'before' not found in {path}"); sys.exit(1)
            c = c.replace(before, after, 1)
            with open(path, 'w') as f: f.write(c)
            print(f"✅ {path} edited")
        else:
            print("❌ --before und --after required"); sys.exit(1)
    elif at == "delete":
        os.remove(sys.argv[2]); print(f"✅ {sys.argv[2]} deleted")

if __name__ == "__main__":
    main()
