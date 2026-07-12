#!/usr/bin/env python3
"""dev_agent_doctor.py — Framework-Agent-Optimierer v1.0.0
============================================================
Scant, bevaluest und optimiert Framework-agents gegen Best-Practices.
Nutzt MAS-Wissen (best-practices.yaml + framework-best-practices.yaml) um
Framework-agents automatically zu verbettern.

Nutzung:
  python3 dev_agent_doctor.py                    All Framework-agents scannen
  python3 dev_agent_doctor.py --agent recording  Only recording.yaml
  python3 dev_agent_doctor.py --scan             Deep Scan + Score
  python3 dev_agent_doctor.py --fix              Automatic fixen
  python3 dev_agent_doctor.py --watch            All 5 Min scannen
  python3 dev_agent_doctor.py --export           Report als JSON
  python3 dev_agent_doctor.py --help             Hilfe
"""

import argparse, json, os, re, sys, time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    import yaml
except ImportError:
    print("Error: yaml not installiert. pip3 install pyyaml")
    sys.exit(1)

# ─── Konstanten ──────────────────────────────────────────────
WORKSPACE = Path(os.getcwd()).resolve()
TOOLS_DIR = Path(__file__).parent.resolve()
STATE_DIR = TOOLS_DIR.parent / ".state"

def get_framework_path(project_name=None):
    """Determine Path to the Framework-project (active oder benannt)."""
    pp = WORKSPACE / "framework" / ".projects.yaml"
    if pp.exists():
        import yaml; data = yaml.safe_load(open(pp))
        active = project_name or data.get("active_project", "dev-team")
    else:
        active = project_name or "dev-team"
    fp = WORKSPACE / "framework" / active
    if not fp.exists():
        fp = WORKSPACE / "framework" / "dev-team"
    return fp / "recipes", fp / "docs", fp / "tests", active

def set_framework_path(project_name=None):
    """Set FRAMEWORK_PATHS global."""
    global FRAMEWORK_RECIPES, FRAMEWORK_DOCS, FRAMEWORK_TESTS, ACTIVE_PROJECT
    FRAMEWORK_RECIPES, FRAMEWORK_DOCS, FRAMEWORK_TESTS, ACTIVE_PROJECT = get_framework_path(project_name)

FRAMEWORK_RECIPES = FRAMEWORK_DOCS = FRAMEWORK_TESTS = None
ACTIVE_PROJECT = "dev-team"
set_framework_path()
FRAMEWORK_DOCS = WORKSPACE / "framework" / "docs"
FRAMEWORK_TESTS = WORKSPACE / "framework" / "tests"
BP_FILE = STATE_DIR / "framework-best-practices.yaml"
MAS_BP_FILE = STATE_DIR / "best-practices.yaml"
REPORT_FILE = STATE_DIR / "framework-heoldh.json"

C = {"R": "\033[0;31m", "G": "\033[0;32m", "Y": "\033[1;33m",
     "B": "\033[0;34m", "BD": "\033[1m", "NC": "\033[0m"}

def ok(msg):   print(f"  {C['G']}OK{ C['NC']} {msg}")
def warn(msg): print(f"  {C['Y']}!!{ C['NC']} {msg}")
def info(msg): print(f"  {C['B']}..{ C['NC']} {msg}")
def err(msg):  print(f"  {C['R']}XX{ C['NC']} {msg}")

def load_best_practices():
    """Load oder erstelle framework-best-practices.yaml."""
    if not BP_FILE.exists():
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        bp = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "best_practices": {
                "prompt": [
                    {"id": "FW-P-001", "rule": "prompt contains tier-Markierung (standard/fast/deep)",
                     "severity": "kritisch", "check": "contains", "values": ["(standard)", "(fast)", "(deep)"]},
                    {"id": "FW-P-002", "rule": "prompt <= 800 Zeichen (not 2000+)",
                     "severity": "wichtig", "check": "prompt_length", "max": 800},
                ],
                "settings": [
                    {"id": "FW-S-001", "rule": "timeout 300-600 (not >900)",
                     "severity": "wichtig", "check": "range", "path": "settings.timeout", "min": 300, "max": 600},
                    {"id": "FW-S-002", "rule": "max_steps <= 50 (no Schleifen)",
                     "severity": "kritisch", "check": "yaml_lte", "path": "settings.max_steps", "max": 50},
                    {"id": "FW-S-003", "rule": "core-agents timeout 60-120 (schneller Start)",
                     "severity": "kritisch", "check": "range", "path": "settings.timeout", "min": 60, "max": 120},
                ],
                "structure": [
                    {"id": "FW-ST-001", "rule": "instructions has Input-Block (signal, request_id, from, to)",
                     "severity": "kritisch", "check": "contains_all", "values": ["signal:", "request_id:", "from:", "to:"]},
                    {"id": "FW-ST-002", "rule": "instructions referenziert only existing files",
                     "severity": "kritisch", "check": "file_refs_exist", "extensions": [".md", ".yaml"]},
                    {"id": "FW-ST-003", "rule": "instructions has Constitution-Referenz",
                     "severity": "wichtig", "check": "contains", "values": ["constitution"]},
                ],
                "tests": [
                    {"id": "FW-T-001", "rule": "Agent has pytest in tests/",
                     "severity": "wichtig", "check": "test_exists", "prefix": ""},
                ]
            }
        }
        yaml.dump(bp, open(BP_FILE, "w"), default_flow_style=False, allow_unicode=True)
        info(f"Knowledge-Base creates: {BP_FILE}")
        return bp
    return yaml.safe_load(open(BP_FILE))

def find_framework_agents() -> List[Path]:
    """Finde all YAML-Rezepte im Framework."""
    agents = []
    for sub in ["core", "specialists", "sub"]:
        d = FRAMEWORK_RECIPES / sub
        if d.exists():
            agents.extend(sorted(d.glob("*.yaml")))
    return agents

def scan_agent(file_path: Path, bp: dict) -> dict:
    """Scanne a agents gegen Best Practices."""
    name = file_path.stem
    try:
        content = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except Exception as e:
        return {"name": name, "score": 0, "passed": 0, "failed": 0, "total": 0,
                "findings": [{"id": "PARSE", "rule": f"YAML-Error: {e}", "status": "XX", "severity": "kritisch"}],
                "status": "rot dead", "error": str(e)}

    findings = []
    passed = failed = 0
    is_core = "core" in str(file_path)

    for category, practices in bp.get("best_practices", {}).items():
        for p in practices:
            pid = p["id"]
            rule = p.get("rule", "?")
            severity = p.get("severity", "wichtig")
            check = p.get("check", "contains")
            checked = False

            try:
                if check == "contains":
                    checked = any(v in content for v in p.get("values", [p.get("value", "")]))
                elif check == "contains_all":
                    checked = all(v in content for v in p.get("values", []))
                elif check == "prompt_length":
                    m = re.search(r'prompt:\s*\|(.+?)(?=\n\S|\Z)', content, re.DOTALL)
                    if m:
                        checked = len(m.group(1).strip()) <= p.get("max", 800)
                    else:
                        checked = False
                elif check == "range":
                    keys = p["path"].split(".")
                    val = data
                    for k in keys:
                        val = val.get(k) if isinstance(val, dict) else None
                    if val is not None and isinstance(val, (int, float)):
                        checked = p.get("min", 0) <= val <= p.get("max", 9999)
                elif check == "yaml_lte":
                    keys = p["path"].split(".")
                    val = data
                    for k in keys:
                        val = val.get(k) if isinstance(val, dict) else None
                    if val is not None and isinstance(val, (int, float)):
                        checked = val <= p.get("max", 50)
                elif check == "file_refs_exist":
                    refs = re.findall(r'([\w./-]+\.(?:md|yaml|json))', content)
                    missing = []
                    for ref in set(refs):
                        rp = WORKSPACE / "framework" / ref
                        if not rp.exists():
                            # relative Pathe try
                            rp2 = WORKSPACE / ref
                            if not rp2.exists():
                                missing.append(ref)
                    checked = len(missing) == 0
                elif check == "test_exists":
                    checked = any(FRAMEWORK_TESTS.rglob(f"*{name}*")) if FRAMEWORK_TESTS.exists() else False
            except Exception:
                checked = False

            status = "OK" if checked else "XX"
            if checked:
                passed += 1
            else:
                failed += 1
            findings.append({"id": pid, "rule": rule, "status": status, "severity": severity})

    total = passed + failed
    score = int((passed / total) * 100) if total > 0 else 0
    if score >= 80:     s = "gruen heoldhy"
    elif score >= 50:   s = "gelb degraded"
    else:               s = "rot dead"

    return {"name": name, "score": score, "passed": passed, "failed": failed, "total": total,
            "findings": findings, "status": s}

def full_scan(bp: dict, agent_filter: Optional[str] = None) -> List[dict]:
    """Scanne all (oder gefilterte) agents."""
    agents = find_framework_agents()
    if not agents:
        err("No Framework-agents found")
        return []
    results = []
    for af in agents:
        if agent_filter and agent_filter not in af.stem:
            continue
        results.append(scan_agent(af, bp))
    return results

def show_report(results: List[dict]):
    """Show Scan-Report."""
    print(f"\n{C['BD']}AGENT DOCTOR — Framework Scan Report{C['NC']}")
    print(f"{'='*50}")
    print(f"  Zeit:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Agents: {len(results)}")
    print()
    sorted_r = sorted(results, key=lambda r: r.get("score", 0), reverse=True)
    for i, r in enumerate(sorted_r, 1):
        sc = C['G'] if r['score'] >= 80 else (C['Y'] if r['score'] >= 50 else C['R'])
        print(f"  {i:2d}. {r['name']:<25} {sc}{r['score']:>3}{C['NC']}/100  {r.get('status','?')}")
        for f in r.get("findings", []):
            if f["status"] == "XX":
                sev = C['R'] if f['severity'] == 'kritisch' else C['Y']
                print(f"       {sev}{f['id']}{C['NC']}: {f['rule'][:70]}")
    scores = [r["score"] for r in results if "score" in r]
    if scores:
        avg = sum(scores) / len(scores)
        tp = sum(r.get("passed", 0) for r in results)
        tf = sum(r.get("failed", 0) for r in results)
        print(f"\n  Total: {avg:.1f}/100  {tp}/{tp+tf} Checks bestanden")
        print(f"  Recommendation: {'--fix' if tf > 0 else 'Everything OK'}")

def auto_fix(results: List[dict], bp: dict, agent_filter: Optional[str] = None):
    """Wende automatische Fixes an."""
    changes = []
    for r in results:
        if agent_filter and agent_filter not in r["name"]:
            continue
        if r.get("failed", 0) == 0:
            continue
        fp = None
        for c in find_framework_agents():
            if c.stem == r["name"]:
                fp = c; break
        if not fp:
            err(f"file for {r['name']} not found"); continue
        content = fp.read_text(encoding="utf-8")
        orig = content; mod = False
        for f in r.get("findings", []):
            if f["status"] != "XX": continue
            pid = f["id"]
            if pid == "FW-P-001" and all(v not in content for v in ["(standard)", "(fast)", "(deep)"]):
                content = content.replace("prompt: |", "prompt: |\n  (standard)")
                mod = True; ok(f"{r['name']}: (standard)-Markierung")
            if pid in ("FW-S-001", "FW-S-003") and "settings:" in content:
                # timeout anpassen
                m = re.search(r'timeout:\s*(\d+)', content)
                if m:
                    old = int(m.group(1))
                    new = 300 if old > 600 else old
                    if new != old:
                        content = content.replace(f"timeout: {old}", f"timeout: {new}")
                        mod = True; ok(f"{r['name']}: timeout {old}->{new}")
            if pid == "FW-S-002" and "max_steps:" in content:
                m = re.search(r'max_steps:\s*(\d+)', content)
                if m:
                    old = int(m.group(1))
                    if old > 50:
                        new = 50
                        content = content.replace(f"max_steps: {old}", f"max_steps: {new}")
                        mod = True; ok(f"{r['name']}: max_steps {old}->{new}")
        if mod:
            bak = fp.with_suffix(fp.suffix + ".bak")
            fp.rename(bak)
            fp.write_text(content, encoding="utf-8")
            changes.append(r["name"])
            ok(f"{r['name']}: Fixes angewendet (Backup: {bak.name})")
    if not changes:
        info("No automatischen Fixes anwendbar")

def watch_mode(bp: dict, interval: int = 300):
    """Watch-Mode: all N seconds scannen."""
    info(f"Watch-Mode (all {interval}s). Ctrl+C to the Stop.")
    try:
        while True:
            results = full_scan(bp)
            scores = [r["score"] for r in results if "score" in r]
            avg = sum(scores) / len(scores) if scores else 0
            dead = sum(1 for r in results if "dead" in r.get("status", ""))
            deg = sum(1 for r in results if "degraded" in r.get("status", ""))
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  [{ts}] {avg:.1f}/100  {len(results)} Agents  {deg} degraded  {dead} dead")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Watch-Mode finished")

def export_report(results: List[dict]):
    """Exportiere als JSON."""
    report = {"timestamp": datetime.now().isoformat(), "agents": len(results),
              "avg_score": sum(r["score"] for r in results) / len(results) if results else 0,
              "results": results}
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(REPORT_FILE, "w"), indent=2, ensure_ascii=False)
    ok(f"Export: {REPORT_FILE}")

# ─── MAS-Extension: --apply-lessons ─────────────────────────
MAS_RECIPES = WORKSPACE / "mas-engineer" / "recipe"
MAS_SUB_DIR = MAS_RECIPES / "sub"

def find_mas_agents() -> List[Path]:
    """Finde all MAS-Sub-agents."""
    if not MAS_SUB_DIR.exists():
        return []
    return sorted(MAS_SUB_DIR.glob("sub_mas-*.yaml"))

def check_mas_agent(file_path: Path, bp: dict) -> dict:
    """Check a MAS-agents gegen Self-Improve-Lessons."""
    name = file_path.stem
    try:
        content = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except Exception as e:
        return {"name": name, "score": 0, "checks": [], "errors": [str(e)]}
    
    checks = []
    passed = failed = 0
    
    # C1: Autonomiemode (AUTONOMIEmode im instructions)
    has_autonomie = "AUTONOMIEmode" in content
    if has_autonomie:
        passed += 1; checks.append({"check": "autonomie", "status": "OK", "detail": "AUTONOMIEmode present"})
    else:
        failed += 1; checks.append({"check": "autonomie", "status": "XX", "detail": "AUTONOMIEmode missing"})
    
    # C2: Tool-Inventar (TOOL INVENTORY)
    has_tool_inventar = "TOOL INVENTORY" in content
    if has_tool_inventar:
        passed += 1; checks.append({"check": "tool_inventar", "status": "OK", "detail": "TOOL INVENTORY present"})
    else:
        failed += 1; checks.append({"check": "tool_inventar", "status": "XX", "detail": "TOOL INVENTORY missing"})
    
    # C3: Output-Format (mas_result statt specialist_result)
    has_mas_result = "mas_result:" in content
    has_specialist_result = "specialist_result:" in content
    if has_mas_result and not has_specialist_result:
        passed += 1; checks.append({"check": "output_format", "status": "OK", "detail": "mas_result: (MAS-Format)"})
    elif has_specialist_result:
        failed += 1; checks.append({"check": "output_format", "status": "XX", "detail": "specialist_result: (Framework-Format!)"})
    else:
        failed += 1; checks.append({"check": "output_format", "status": "XX", "detail": "Weder mas_result: still specialist_result:"})
    
    # C4: Mindestens 6 ⛔-Rulen
    shield_count = content.count("⛔")
    if shield_count >= 6:
        passed += 1; checks.append({"check": "shield_rules", "status": "OK", "detail": f"{shield_count} ⛔Rulen (>=6)"})
    else:
        failed += 1; checks.append({"check": "shield_rules", "status": "XX", "detail": f"Only {shield_count} ⛔Rulen (<6)"})
    
    # C5: Default-Settings (timeout=600, max_steps=100)
    d = data or {}
    s = d.get("settings", {})
    timeout_ok = s.get("timeout") == 600
    steps_ok = s.get("max_steps") in [100, 150, 200]
    if timeout_ok and steps_ok:
        passed += 1; checks.append({"check": "settings", "status": "OK", "detail": f"timeout={s.get('timeout')}, max_steps={s.get('max_steps')}"})
    else:
        failed += 1; t = s.get('timeout', '?'); m = s.get('max_steps', '?')
        checks.append({"check": "settings", "status": "XX", "detail": f"timeout={t}, max_steps={m} (should: 600, 100-200)"})
    
    # C6: Separation (no Framework-Concepts)
    has_fw_concepts = any(t in content.lower() for t in 
        ["specialist_result:", "findings:", "executor", "planner", "controller", "starter"])
    if not has_fw_concepts:
        passed += 1; checks.append({"check": "separation", "status": "OK", "detail": "No Framework-Concepts"})
    else:
        failed += 1; checks.append({"check": "separation", "status": "XX", "detail": "Framework-Concepts found"})
    
    # C7: Edge Cases present
    has_edge_cases = "Edge Cases" in content
    if has_edge_cases:
        passed += 1; checks.append({"check": "edge_cases", "status": "OK", "detail": "Edge Cases present"})
    else:
        failed += 1; checks.append({"check": "edge_cases", "status": "XX", "detail": "Edge Cases missing"})
    
    total = passed + failed
    score = int((passed / total) * 100) if total > 0 else 0
    return {"name": name, "score": score, "passed": passed, "failed": failed, "total": total, "checks": checks}

def apply_lessons(results: List[dict], dry_run: bool = False, skip: Optional[List[str]] = None):
    """Read-Only: Analysiere, change nothing. Delegiert YAML-Schreib-Operation an dev_editor.py."""
    if dry_run:
        for r in results:
            for c in r.get("checks", []):
                if c["status"] == "XX":
                    info(f"  [DRY-RUN] {r['name']}: {c['detail']} -> dev_editor.py")
        info("Trockenlauf finished - no Changeen")
    else:
        total = sum(r.get("failed", 0) for r in results)
        info(f"{total} Issues in {len(results)} agents - manuelle Bearbeitung via dev_editor.py")
    return []
def show_apply_report(results: List[dict], dry_run: bool = False):
    """Show --apply-lessons Report."""
    print(f"\n{C['BD']}AGENT DOCTOR — MAS Apply-Lessons Report{C['NC']}")
    print(f"{'='*50}")
    print(f"  Zeit:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  mode:  {'DRY-RUN (only anshow)' if dry_run else 'AKTIV (mit Changes)'}")
    print(f"  Agents: {len(results)}")
    print()
    for i, r in enumerate(sorted(results, key=lambda x: x.get("score", 0)), 1):
        sc = C['G'] if r['score'] >= 80 else (C['Y'] if r['score'] >= 50 else C['R'])
        print(f"  {i:2d}. {r['name'][-30:]:>30} {sc}{r['score']:>3}{C['NC']}/100  ({r['passed']}/{r['total']} OK)")
        for c in r.get("checks", []):
            if c["status"] == "XX":
                print(f"       XX {c['detail'][:70]}")
    
    scores = [r["score"] for r in results]
    avg = sum(scores) / len(scores) if scores else 0
    total_p = sum(r.get("passed", 0) for r in results)
    total_f = sum(r.get("failed", 0) for r in results)
    total_t = total_p + total_f
    print(f"\n  Total: {avg:.1f}/100  {total_p}/{total_t} Checks bestanden ({total_f} offen)")
    if dry_run:
        print(f"  Laufen: python3 dev_agent_doctor.py --apply-lessons")

def main():
    p = argparse.ArgumentParser(description="dev_agent_doctor.py v1.0.0")
    p.add_argument("--agent", type=str, help="Only determinesen agents")
    p.add_argument("--project", type=str, help="projectname (default: active)")
    p.add_argument("--all-projects", action="store_true", help="All projecte scannen")
    p.add_argument("--scan", action="store_true", help="Deep Scan")
    p.add_argument("--fix", action="store_true", help="Automatic fixen")
    p.add_argument("--watch", type=int, nargs="?", const=300, help="Watch-Mode (Sek)")
    p.add_argument("--export", action="store_true", help="JSON-Export")
    p.add_argument("--apply-lessons", action="store_true", help="Self-Improve-Lessons auf MAS-agents anwenden")
    p.add_argument("--dry-run", action="store_true", help="Only anshow, nothing change")
    p.add_argument("--skip", type=str, help="Checks skip (kommasepariert: autonomie,settings,shield)")
    p.add_argument("--version", action="store_true", help="Version")
    args = p.parse_args()
    if args.apply_lessons:
        if not MAS_BP_FILE.exists():
            err(f"No Best-Practices found: {MAS_BP_FILE}")
            err("Run first Self-Improvement aus.")
            return
        bp = yaml.safe_load(open(MAS_BP_FILE))
        agents = find_mas_agents()
        if not agents:
            err("No MAS-agents found")
            return
        skip_list = args.skip.split(",") if args.skip else []
        results = []
        for af in agents:
            if args.agent and args.agent not in af.stem:
                continue
            results.append(check_mas_agent(af, bp))
        show_apply_report(results, dry_run=args.dry_run)
        info(f"  {len(results)} agents checked - {sum(r.get('failed',0) for r in results)} Issues offen")
        info(f"  YAML-Schreib-Operation delegiert an: dev_editor.py --apply-lessons")
        apply_lessons(results, dry_run=True, skip=skip_list)
        return
    if args.version:
        print("dev_agent_doctor.py v1.0.0"); return
    
    if args.all_projects:
        pp = WORKSPACE / "framework" / ".projects.yaml"
        if pp.exists():
            data = yaml.safe_load(open(pp))
            for pname in data.get("projects", {}):
                set_framework_path(pname)
                print(f"\n  project: {pname}")
                bp = load_best_practices()
                results = full_scan(bp, args.agent)
                if results: show_report(results)
                if args.fix: auto_fix(results, bp, args.agent)
        return
    
    if args.project:
        set_framework_path(args.project)
    
    bp = load_best_practices()
    if args.watch:
        watch_mode(bp, args.watch); return
    results = full_scan(bp, args.agent)
    if not results:
        return
    show_report(results)
    if args.fix:
        auto_fix(results, bp, args.agent)
    if args.export:
        export_report(results)

if __name__ == "__main__":
    main()
