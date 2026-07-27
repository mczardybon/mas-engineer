#!/usr/bin/env python3
"""
15x Demo-Team E2E (3 teams × 5 runs = 15 runs)

Reproduces the 2026-07-24 9/9 test but extended to 15/15.
Same 3 prompts, same setup, just N=5 per team instead of N=3.

Each run = fresh `goose run --no-session --instructions -` with the prompt
piped in. /tmp/<team> wiped before each run. PASS = real success
(file count + agent's own test suite ran).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

EVIDENCE = Path("/workspace/mas-engineer-src/e2e-results/2026-07-27-demo-team-15x/evidence")
EVIDENCE.mkdir(parents=True, exist_ok=True)

TEAMS = ['sales', 'marketing', 'translator']
TEAM_DIRS = {
    'sales': '/tmp/sales-team',
    'marketing': '/tmp/marketing-team',
    'translator': '/tmp/translator-team',
}

def run_one(team: str, run: int) -> dict:
    """One run = one fresh goose invocation."""
    prompt_path = EVIDENCE / f"run{run}-{team}-prompt.txt"
    if not prompt_path.exists():
        # Reuse run1 prompt
        shutil = __import__('shutil')
        src = Path("/workspace/mas-engineer-src/e2e-results/2026-07-24-demo-team-generation-rate/evidence") / f"run1-{team}-prompt.txt"
        if src.exists():
            shutil.copy(src, prompt_path)

    prompt = prompt_path.read_text()
    team_dir = TEAM_DIRS[team]

    # Wipe /tmp/<team>
    subprocess.run(["rm", "-rf", team_dir], check=False)
    subprocess.run(["mkdir", "-p", team_dir], check=False)

    # Env
    env = os.environ.copy()
    ds = os.environ.get('DEEPSEEK_API_KEY')
    if not ds:
        raise RuntimeError("DEEPSEEK_API_KEY not set — refusing to run without it (no hardcoded fallback for security)")
    env['DEEPSEEK_API_KEY'] = ds
    env['OPENAI_API_KEY'] = ds
    env['OPENAI_HOST'] = 'https://api.deepseek.com'
    env['OPENAI_MODEL'] = 'deepseek-chat'
    env['GOOSE_TELEMETRY_ENABLED'] = 'false'
    env['NO_COLOR'] = '1'
    env['TERM'] = 'dumb'
    env['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"

    log_path = EVIDENCE / f"run{run}-{team}-build.log"
    cmd = ['goose', 'run', '--no-session', '--instructions', '-']
    start = time.time()
    try:
        result = subprocess.run(
            cmd, input=prompt, env=env, capture_output=True, text=True,
            timeout=600,
        )
        duration = time.time() - start
        out = result.stdout + "\n--- STDERR ---\n" + result.stderr
        ANSI = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\r')
        log_path.write_text(ANSI.sub('', out))
        if result.returncode != 0:
            return {
                'team': team, 'run': run, 'pass': False,
                'duration_sec': round(duration, 1),
                'log_size': len(out), 'log_path': str(log_path),
                'error': f'exit {result.returncode}',
            }
    except subprocess.TimeoutExpired:
        return {
            'team': team, 'run': run, 'pass': False,
            'duration_sec': 600, 'log_size': 0,
            'log_path': str(log_path),
            'error': 'timeout 600s',
        }
    except Exception as e:
        return {
            'team': team, 'run': run, 'pass': False,
            'duration_sec': round(time.time() - start, 1),
            'log_size': 0, 'log_path': str(log_path),
            'error': f'crash: {e}',
        }

    # Eval
    eval_res = evaluate(team, team_dir, log_path)
    eval_res.update({
        'team': team, 'run': run,
        'duration_sec': round(duration, 1),
        'log_size': len(out), 'log_path': str(log_path),
    })
    return eval_res


def evaluate(team: str, team_dir: str, log_path: Path) -> dict:
    """Check files + agent's reported tests."""
    td = Path(team_dir)
    recipe_dir = td / 'recipe'
    sub_dir = recipe_dir / 'sub'
    n_files = len(list(recipe_dir.rglob('*.yaml'))) if recipe_dir.exists() else 0
    if n_files == 0:
        n_files = len(list(td.rglob('*.yaml')))

    # Agent reported its test results in the log
    log_text = log_path.read_text() if log_path.exists() else ''
    # Common success markers — capture N from "N of M PASSED", "N/N PASS", etc.
    # We want the LARGEST N that appears in a "passed" context.
    success_markers = [
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
    max_pass = 0
    for pat in success_markers:
        for m in re.finditer(pat, log_text, re.IGNORECASE):
            try:
                n = int(m.group(1))
                if n > max_pass:
                    max_pass = n
            except (ValueError, IndexError):
                pass

    # Failure indicators
    has_401 = bool(re.search(r'401|Authentication failed', log_text))
    has_crash = bool(re.search(r'panic|SIGSEGV|out of memory', log_text, re.IGNORECASE))

    # Pass criteria (same as 2026-07-24):
    #   - files created (>=4)
    #   - agent's own test suite ran and reported some PASS count
    #   - no auth failures
    pass_ok = (n_files >= 4) and (max_pass > 0) and not has_401 and not has_crash

    return {
        'pass': pass_ok,
        'n_files': n_files,
        'max_pass_reported': max_pass,
        'has_401': has_401,
        'has_crash': has_crash,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=5, help='runs per team')
    p.add_argument('--start', type=int, default=1)
    p.add_argument('--teams', nargs='+', default=TEAMS)
    p.add_argument('--sequential', action='store_true', help='one at a time (safer)')
    args = p.parse_args()

    total = args.n * len(args.teams)
    print(f"Demo-Team 15x E2E — {len(args.teams)} teams × {args.n} runs = {total} total")
    print(f"Evidence: {EVIDENCE}")
    print(f"Mode: {'sequential' if args.sequential else 'per-team-parallel'}")
    print("=" * 60)

    results = []
    pass_count = fail_count = 0

    for run in range(args.start, args.start + args.n):
        print(f"\n=== Round {run}/{args.start + args.n - 1} ===", flush=True)
        for team in args.teams:
            print(f"  -> {team} (run {run}) ...", flush=True)
            try:
                r = run_one(team, run)
                status = "PASS" if r.get('pass') else "FAIL"
                files = r.get('n_files', '?')
                pr = r.get('max_pass_reported', 0)
                dur = r.get('duration_sec', '?')
                print(f"     [{status}] {dur}s | {files} files | {pr} tests reported | {r.get('error','')}", flush=True)
                results.append(r)
                if r.get('pass'):
                    pass_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"     [CRASH] {e}", flush=True)
                results.append({'team': team, 'run': run, 'pass': False, 'error': str(e)})
                fail_count += 1
            save_summary(pass_count, fail_count, results)
        if run < args.start + args.n - 1:
            time.sleep(2)

    rate = pass_count / total * 100 if total else 0
    print(f"\n{'=' * 60}")
    print(f"FINAL: {pass_count} PASS / {fail_count} FAIL (n={total})")
    print(f"Success rate: {rate:.1f}%")
    print(f"Summary: {EVIDENCE}/SUMMARY.json")
    print(f"Pass per team:")
    for team in args.teams:
        team_results = [r for r in results if r.get('team') == team]
        team_pass = sum(1 for r in team_results if r.get('pass'))
        print(f"  {team}: {team_pass}/{len(team_results)}")
    if total > 0:
        import math
        pp = pass_count / total
        n = total
        z = 1.96
        denom = 1 + z**2/n
        center = (pp + z**2/(2*n)) / denom
        spread = z * math.sqrt(pp*(1-pp)/n + z**2/(4*n**2)) / denom
        print(f"Wilson 95% CI: [{max(0, center-spread)*100:.1f}%, {min(1, center+spread)*100:.1f}%]")


def save_summary(p, f, results):
    total = p + f
    rate = (p / total * 100) if total else 0
    summary = {
        'date': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'n_total': total, 'pass': p, 'fail': f,
        'success_rate_pct': round(rate, 1),
        'runs': results,
    }
    (EVIDENCE / 'SUMMARY.json').write_text(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
