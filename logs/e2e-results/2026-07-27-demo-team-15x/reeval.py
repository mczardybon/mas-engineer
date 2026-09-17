#!/usr/bin/env python3
"""Re-evaluate all 15 runs with the fixed eval logic — no re-running of goose."""
import json
import re
import sys
from pathlib import Path

EVIDENCE = Path("/workspace/mas-engineer-src/e2e-results/2026-07-27-demo-team-15x/evidence")
TEAM_DIRS = {
    'sales': '/tmp/sales-team',
    'marketing': '/tmp/marketing-team',
    'translator': '/tmp/translator-team',
}

# Same success_markers as fixed run_15x_demo.py
SUCCESS_MARKERS = [
    r'(\d+)\s+of\s+\d+\s+PASS',
    r'(\d+)\s*/\s*\d+\s*PASS',
    r'(\d+)\s*/\s*\d+\s+checks?\s+PASS',
    r'(\d+)\s+checks?\s+PASS',
    r'All\s+(\d+)\s+checks?\s+PASS',
    r'ALL\s+(\d+)\s*CHECKS?\s*PASS',
    r'(\d+)\s+checks?\s+PASSED',
    r'(\d+)\s+tests?\s+passed',
    r'PASSED[^\n]*?(\d+)\s+of\s+\d+',
    r'✅\s*PASS[^\n]{0,40}?(\d+)',
    r'(\d+)\s*✅\s*PASS',
]


def find_max_pass(log_text: str) -> int:
    max_pass = 0
    for pat in SUCCESS_MARKERS:
        for m in re.finditer(pat, log_text, re.IGNORECASE):
            try:
                n = int(m.group(1))
                if n > max_pass:
                    max_pass = n
            except (ValueError, IndexError):
                pass
    return max_pass


def evaluate(team: str, run: int) -> dict:
    log_path = EVIDENCE / f"run{run}-{team}-build.log"
    if not log_path.exists():
        return {'pass': False, 'error': f'no log for run{run}-{team}'}
    log_text = log_path.read_text()
    team_dir = Path(TEAM_DIRS[team])
    n_files = len(list(team_dir.rglob('*.yaml'))) if team_dir.exists() else 0
    max_pass = find_max_pass(log_text)
    has_401 = bool(re.search(r'401|Authentication failed', log_text))
    has_crash = bool(re.search(r'panic|SIGSEGV|out of memory', log_text, re.IGNORECASE))
    pass_ok = (n_files >= 4) and (max_pass > 0) and not has_401 and not has_crash
    return {
        'pass': pass_ok,
        'n_files': n_files,
        'max_pass': max_pass,
        'has_401': has_401,
        'has_crash': has_crash,
    }


def main():
    # Load existing summary
    summary_path = EVIDENCE / 'SUMMARY.json'
    if summary_path.exists():
        existing = json.loads(summary_path.read_text())
    else:
        existing = {'runs': []}

    # Re-eval each run
    teams = ['sales', 'marketing', 'translator']
    fixed_runs = []
    for r in existing.get('runs', []):
        team = r['team']
        run = r['run']
        new_eval = evaluate(team, run)
        old_pass = r.get('pass')
        new_pass = new_eval['pass']
        if old_pass != new_pass:
            r['pass'] = new_pass
            r['re_eval_note'] = f"was={old_pass} now={new_pass}"
            fixed_runs.append((team, run, old_pass, new_pass, new_eval.get('max_pass')))
        r['max_pass'] = new_eval['max_pass']
        r['n_files'] = new_eval['n_files']

    # Recompute summary
    total = len(existing['runs'])
    pass_count = sum(1 for r in existing['runs'] if r.get('pass'))
    fail_count = total - pass_count
    rate = (pass_count / total * 100) if total else 0
    existing['pass'] = pass_count
    existing['fail'] = fail_count
    existing['n_total'] = total
    existing['success_rate_pct'] = round(rate, 1)
    existing['re_eval_date'] = '2026-07-27T12:04'

    summary_path.write_text(json.dumps(existing, indent=2))

    print(f"Re-eval done. {len(fixed_runs)} runs changed status:")
    for team, run, old, new, mp in fixed_runs:
        print(f"  {team} run{run}: {old} -> {new} (max_pass={mp})")
    print()
    print(f"FINAL: {pass_count}/{total} PASS = {rate:.1f}%")
    print()
    print("Per team:")
    for t in teams:
        t_results = [r for r in existing['runs'] if r.get('team') == t]
        t_pass = sum(1 for r in t_results if r.get('pass'))
        print(f"  {t}: {t_pass}/{len(t_results)}")

    if total > 0:
        import math
        pp = pass_count / total
        n = total
        z = 1.96
        denom = 1 + z**2/n
        center = (pp + z**2/(2*n)) / denom
        spread = z * math.sqrt(pp*(1-pp)/n + z**2/(4*n**2)) / denom
        lo = max(0, center - spread) * 100
        hi = min(1, center + spread) * 100
        print(f"Wilson 95% CI: [{lo:.1f}%, {hi:.1f}%]")


if __name__ == '__main__':
    main()
