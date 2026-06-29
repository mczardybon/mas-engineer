#!/usr/am/env python3
"""
dev_health_report.py — Health-Report + Trend for Generic-Projekte
Aufruf: python3 dev_health_report.py --target ~/my-project/
"""
import os, sys, json, time, yaml

def calculate_score(target):
    checks = []
    
    # 1. Rules-Aktivierung (R01-R09)
    reg_path = os.path.join(target, '.state/rules/rules.yaml')
    if os.path.exists(reg_path):
        try:
            data = yaml.safe_load(open(reg_path))
            rules = data.get('rules', [])
            total = len(rules)
            active = sum(1 for r in rules if r.get('block', False) and r.get('haerte', 0) >= 3)
            checks.append({"name": "rules_active", "ok": True, "detail": f"{active}/{total}"})
        except:
            checks.append({"name": "rules_active", "ok": False, "detail": "invalid yaml"})
    else:
        checks.append({"name": "rules_active", "ok": False, "detail": "not found"})
    
    # 2. Checker funktioniert?
    checker_path = os.path.join(target, 'tools/dev_rule_checker.py')
    if os.path.exists(checker_path):
        import subprocess
        r = subprocess.run(['python3', checker_path, '--health'], capture_output=True, text=True)
        if r.returncode == 0:
            try:
                h = json.loads(r.stdout)
                checks.append({"name": "checker_health", "ok": True, "detail": f"{h.get('score', 0)}/10"})
            except:
                checks.append({"name": "checker_health", "ok": True})
        else:
            checks.append({"name": "checker_health", "ok": False})
    else:
        checks.append({"name": "checker_health", "ok": False, "detail": "not found"})
    
    # 3. YAMLs valide?
    sub_dir = os.path.join(target, 'sub')
    if os.path.exists(sub_dir):
        ok = 0
        total = 0
        for f in os.listdir(sub_dir):
            if f.endswith('.yaml'):
                total += 1
                try: yaml.safe_load(open(os.path.join(sub_dir, f))); ok += 1
                except: pass
        checks.append({"name": "yaml_valid", "ok": ok == total, "detail": f"{ok}/{total}"})
    else:
        checks.append({"name": "yaml_valid", "ok": True, "detail": "no agents"})
    
    # 4. Letzter SI-RUN
    changes_path = os.path.join(target, '.state/changes.json')
    if os.path.exists(changes_path):
        try:
            changes = json.load(open(changes_path))
            si_runs = [c for c in changes if 'si-run' in c.get('action', '').lower() or 'improve' in c.get('action', '').lower()]
            days_since = round((time.time() - time.mktime(time.strptime(si_runs[-1]['timestamp'][:19], '%Y-%m-%dT%H:%M:%S'))) / 86400) if si_runs else None
            checks.append({"name": "last_si_run", "ok": days_since is not None and days_since < 7,
                          "detail": f"vor {days_since} Tag(en)" if days_since else "nie"})
        except:
            checks.append({"name": "last_si_run", "ok": False, "detail": "invalid"})
    else:
        checks.append({"name": "last_si_run", "ok": False, "detail": "not found"})
    
    # Score
    ok_count = sum(1 for c in checks if c['ok'])
    score = round(ok_count / max(len(checks), 1) * 10, 1)
    
    return {"checks": checks, "score": score, "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')}

def save_history(target, report):
    hist_path = os.path.join(target, '.state/health-history.json')
    history = []
    if os.path.exists(hist_path):
        try:
            history = json.load(open(hist_path))
        except: pass
    history.append({"timestamp": report["timestamp"], "score": report["score"]})
    # Only letzte 20 Eintraege keep
    history = history[-20:]
    json.dump(history, open(hist_path, 'w'), indent=2)
    return history

def show_trend(history):
    if len(history) < 2:
        return
    scores = [h['score'] for h in history]
    trend = scores[-1] - scores[0]
    arrow = "\u2191" if trend > 0 else ("\u2193" if trend < 0 else "\u2192")
    print(f"\n  Trend ({len(history)} Eintraege): {scores[0]} {arrow} {scores[-1]} ({'+' if trend > 0 else ''}{trend:.1f})")

def main():
    target = None
    for i, a in enumerate(sys.argv):
        if a == '--target' and i + 1 < len(sys.argv):
            target = sys.argv[i + 1]
    
    if not target:
        print("❌ --target required")
        sys.exit(1)
    
    target = os.path.abspath(target)
    report = calculate_score(target)
    history = save_history(target, report)
    
    print(f"\n{'='*50}")
    print(f"HEALTH-REPORT: {os.path.basename(target)}")
    print(f"{'='*50}")
    print(f"  Score: {report['score']}/10")
    for c in report['checks']:
        icon = '\u2705' if c['ok'] else '\u274c'
        print(f"  {icon} {c['name']}: {c.get('detail', '')}")
    
    show_trend(history)
    
    # Recommendation
    if report['score'] < 5:
        print(f"\n  Emfpehlung: Health-Score niedrig — SI-RUN recommended")
    elif report['score'] < 8:
        print(f"\n  Recommendation: Einige Checks verbetterungswuerdig")
    else:
        print(f"\n  Recommendation: System ist gesund")
    
    # Speichere Report
    json.dump(report, open(os.path.join(target, '.state/health-report.json'), 'w'), indent=2)
    print(f"\n  Report saved: .state/health-report.json")

if __name__ == "__main__":
    main()
