#!/usr/am/env python3
"""
dev_audit.py — Audit-Log-System + Lock + Pre-Commit-Check
Aufruf: dev_audit.py --log --aktion WRITE --agent gatekeeper --ziel path --status OK
        dev_audit.py --check              # Pre-Commit-Check
        dev_audit.py --status              # MAS-Status anshow
        dev_audit.py --unlock --force      # MAS entsperren
        dev_audit.py --violations          # Letzte Violations show
"""

import sys, os, json, datetime

MAS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(MAS_DIR, ".state")
AUDIT_FILE = os.path.join(STATE_DIR, "audit.log.jsonl")
LOCK_FILE = os.path.join(STATE_DIR, ".disziplin_lock")

def _load():
    if not os.path.exists(AUDIT_FILE): return []
    with open(AUDIT_FILE) as f:
        return [json.loads(z) for z in f.read().strip().split('\n') if z.strip()]

def log(aktion, agent, ziel, status, rule=""):
    os.makedirs(STATE_DIR, exist_ok=True)
    e = {"ts": datetime.datetime.now().isoformat(),
         "session": os.environ.get("GOOSE_SESSION_TAG",""),
         "aktion": aktion, "agent": agent,
         "ziel": str(ziel)[:200], "status": status, "rule": rule}
    with open(AUDIT_FILE, 'a') as f:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')
    if status == "CRITICAL":
        with open(LOCK_FILE, 'w') as f:
            f.write(f"CRITICAL: {rule} - {aktion} um {e['ts']}")
        print("🔴 CRITICAL — MAS GEFRIERT!")

def check():
    """Pre-Commit: Checks ob Violations exist"""
    print("=== DEV-AUDIT: Pre-Commit-Check ===")
    if os.path.exists(LOCK_FILE):
        print(f"❌ COMMIT BLOCKIERT: MAS gefroren!")
        print(f"   {open(LOCK_FILE).read().strip()}")
        sys.exit(1)
    eintraege = _load()
    verstoesse = [e for e in eintraege if e.get('status') in ('BLOCKED','CRITICAL')]
    if verstoesse:
        print(f"❌ COMMIT BLOCKIERT: {len(verstoesse)} Violations")
        for v in verstoesse[-3:]:
            print(f"   {v['ts'][:19]} | {v['status']} | {v['rule']} | {v['ziel'][:60]}")
        sys.exit(1)
    if eintraege and eintraege[-1].get('status') != 'OK':
        print(f"❌ Letzte Aktion not OK: {eintraege[-1]['status']}")
        sys.exit(1)
    print("✅ Pre-Commit bestanden")
    sys.exit(0)

def status():
    eintraege = _load()
    if not eintraege:
        print("📝 Audit-Log: Leer (no Aktionen)"); return
    g, ok, bl, cr = len(eintraege), 0, 0, 0
    for e in eintraege:
        if e['status'] == 'OK': ok += 1
        elif e['status'] == 'BLOCKED': bl += 1
        elif e['status'] == 'CRITICAL': cr += 1
    print(f"📊 AUDIT: {g} total | ✅ {ok} | ⛔ {bl} | 🔴 {cr}")
    if bl+cr > 0:
        print("Letzte Violations:")
        for e in eintraege[-5:]:
            if e.get('status') in ('BLOCKED','CRITICAL'):
                print(f"   {e['ts'][:19]} | {e['status']} | {e['rule']} | {e['ziel'][:60]}")
    if os.path.exists(LOCK_FILE):
        print(f"🔴 MAS GEFRIERT: {open(LOCK_FILE).read().strip()}")

def unlock():
    if not os.path.exists(LOCK_FILE):
        print("🔓 MAS not gefroren"); return
    if "--force" not in sys.argv:
        print("❌ --force to the Confirmation required")
        print(f"   Lock: {open(LOCK_FILE).read().strip()}"); sys.exit(1)
    grund = open(LOCK_FILE).read().strip()
    os.remove(LOCK_FILE)
    log("UNLOCK", "audit", f"MAS entriegelt (war: {grund})", "OK", "")
    print(f"✅ MAS entriegelt (war: {grund})")

def violations():
    eintraege = _load()
    v = [e for e in eintraege if e.get('status') in ('BLOCKED','CRITICAL')]
    if not v: print("✅ No Violations"); return
    print(f"⛔ {len(v)} Violations:")
    for e in v[-10:]:
        print(f"   {e['ts'][:19]} | {e['rule']} | {e['aktion']} | {e['ziel'][:60]}")

def main():
    if len(sys.argv) < 2:
        print("dev_audit.py --log|--check|--status|--unlock|--violations"); sys.exit(1)
    m = sys.argv[1]
    if m == "--log":
        p = {}
        for i in range(2, len(sys.argv)-1):
            if sys.argv[i].startswith('--'): p[sys.argv[i].lstrip('-')] = sys.argv[i+1]
        log(p.get("aktion","?"), p.get("agent","?"), p.get("ziel","?"),
            p.get("status","OK"), p.get("rule",""))
        print(f"✅ Audit: {p.get('aktion','?')} | {p.get('status','OK')}")
    elif m == "--check": check()
    elif m == "--status": status()
    elif m == "--unlock": unlock()
    elif m == "--violations": violations()
    else: print(f"❌ Unbekannt: {m}"); sys.exit(1)

if __name__ == "__main__":
    main()
