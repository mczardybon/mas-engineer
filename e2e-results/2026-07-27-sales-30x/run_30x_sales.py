#!/usr/bin/env python3
"""
30x Sales-Team E2E Orchestrator (R108-9, simple non-interactive)

Runs the sales-team prompt N times with `goose run -t "PROMPT" --no-session`,
evaluates each run against hard + soft criteria, aggregates results.

Each run is a FRESH session (--no-session) so it's a true independent
generation attempt with full LLM variance.

Usage:
    python3 run_30x_sales.py [--n 30] [--start 1] [--evidence-dir PATH]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ANSI = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\r')

def clean(text: str) -> str:
    return ANSI.sub('', text)

def run_one(idx: int, prompt: str, evidence_dir: Path, timeout_sec: int = 600) -> dict:
    """Run one sales-team generation via `goose run -t --no-session`."""
    log_path = evidence_dir / f"run{idx}-sales-build.log"
    eval_path = evidence_dir / f"run{idx}-eval"
    eval_path.mkdir(parents=True, exist_ok=True)
    team_dir = Path("/tmp/sales-team")

    # Cleanup
    subprocess.run(["rm", "-rf", str(team_dir)], check=False)
    team_dir.mkdir(parents=True, exist_ok=True)

    # Build env — prefer os.environ, fallback to known-working deepseek key
    env = os.environ.copy()
    ds_key = os.environ.get('DEEPSEEK_API_KEY') or '<REDACTED-DEEPSEEK-KEY>'
    env['DEEPSEEK_API_KEY'] = ds_key
    env['OPENAI_API_KEY'] = ds_key
    env['OPENAI_HOST'] = 'https://api.deepseek.com'
    env['OPENAI_MODEL'] = 'deepseek-chat'
    env['GOOSE_TELEMETRY_ENABLED'] = 'false'
    env['PATH'] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"

    cmd = ['goose', 'run', '-t', prompt, '--no-session']
    start = time.time()
    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True,
            timeout=timeout_sec,
        )
        duration = time.time() - start
        out = result.stdout + "\n--- STDERR ---\n" + result.stderr
        log_path.write_text(clean(out))
        if result.returncode != 0:
            return {
                'pass': False, 'duration_sec': round(duration, 1),
                'log_path': str(log_path), 'log_size': len(out),
                'error': f'goose exit {result.returncode}',
            }
    except subprocess.TimeoutExpired as e:
        return {
            'pass': False, 'duration_sec': round(time.time() - start, 1),
            'log_path': str(log_path), 'log_size': 0,
            'error': f'timeout after {timeout_sec}s',
        }
    except Exception as e:
        return {
            'pass': False, 'duration_sec': round(time.time() - start, 1),
            'log_path': str(log_path), 'log_size': 0,
            'error': f'crash: {e}',
        }

    # Evaluate
    eval_result = evaluate(team_dir, log_path)
    eval_result['duration_sec'] = round(duration, 1)
    eval_result['log_path'] = str(log_path)
    eval_result['log_size'] = len(out)
    (eval_path / 'evaluation.json').write_text(json.dumps(eval_result, indent=2))
    return eval_result


def evaluate(team_dir: Path, log_path: Path) -> dict:
    """Evaluate one run against hard + soft criteria."""
    try:
        import yaml
    except ImportError:
        yaml = None
    result = {'pass': True, 'hard_checks': {}, 'errors': []}

    required = [
        team_dir / 'recipe/sales-team.yaml',
        team_dir / 'recipe/sub/lead-scraper.yaml',
        team_dir / 'recipe/sub/lead-verifier.yaml',
        team_dir / 'recipe/sub/outreach-drafter.yaml',
        team_dir / 'recipe/sub/deal-closer.yaml',
    ]
    missing = [str(f) for f in required if not f.exists()]
    if missing:
        result['hard_checks']['H1_files'] = {'pass': False, 'msg': f'missing: {len(missing)} files'}
        result['pass'] = False
    else:
        result['hard_checks']['H1_files'] = {'pass': True, 'msg': '5/5 required files'}

    sub_dir = team_dir / 'recipe/sub'
    if sub_dir.exists():
        n_sub = len(list(sub_dir.glob('*.yaml')))
        if n_sub < 4:
            result['hard_checks']['H2_subcount'] = {'pass': False, 'msg': f'only {n_sub} sub-recipes'}
            result['pass'] = False
        else:
            result['hard_checks']['H2_subcount'] = {'pass': True, 'msg': f'{n_sub} sub-recipes'}

    if yaml:
        yerrors = []
        for f in required:
            if not f.exists(): continue
            try: yaml.safe_load(f.read_text())
            except yaml.YAMLError as e: yerrors.append(f'{f.name}: {e}')
        if yerrors:
            result['hard_checks']['H3_yaml'] = {'pass': False, 'msg': f'{len(yerrors)} YAML errors'}
            result['pass'] = False
        else:
            result['hard_checks']['H3_yaml'] = {'pass': True, 'msg': 'all YAML valid'}

    root = team_dir / 'recipe/sales-team.yaml'
    if yaml and root.exists():
        try:
            d = yaml.safe_load(root.read_text()) or {}
            subs = d.get('sub_recipes', [])
            names = {s.get('name', '') if isinstance(s, dict) else str(s) for s in subs}
            needed = {'lead-scraper', 'lead-verifier', 'outreach-drafter', 'deal-closer'}
            miss = needed - names
            if miss:
                result['hard_checks']['H4_subrecipes'] = {'pass': False, 'msg': f'missing: {miss}'}
                result['pass'] = False
            else:
                result['hard_checks']['H4_subrecipes'] = {'pass': True, 'msg': 'all 4 referenced'}
        except Exception as e:
            result['hard_checks']['H4_subrecipes'] = {'pass': False, 'msg': str(e)[:60]}
            result['pass'] = False

    # H5: MANDATORY quality gate
    gate_patterns = [
        r'mandatory.{0,30}quality.{0,30}gate',
        r'lead.?verifier.{0,30}gate',
        r'verifier.{0,30}mandatory',
        r'must.{0,20}pass.{0,30}verifier',
        r'unverified.{0,20}NOT',
    ]
    gate_found = False
    for op in [team_dir / 'recipe/sub/sales-orchestrator.yaml', root]:
        if op.exists():
            content = op.read_text()
            for p in gate_patterns:
                if re.search(p, content, re.IGNORECASE):
                    gate_found = True
                    break
            if gate_found: break
    if not gate_found:
        result['hard_checks']['H5_gate'] = {'pass': False, 'msg': 'no MANDATORY gate in prompts'}
        result['pass'] = False
    else:
        result['hard_checks']['H5_gate'] = {'pass': True, 'msg': 'gate enforced'}

    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=30)
    p.add_argument('--start', type=int, default=1)
    p.add_argument('--evidence-dir', default='e2e-results/2026-07-27-sales-30x/evidence')
    p.add_argument('--prompt', default='e2e-results/2026-07-27-sales-30x/prompt.txt')
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--per-run-sleep', type=int, default=2)
    args = p.parse_args()

    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    prompt = Path(args.prompt).read_text()

    print(f"30x Sales-Team E2E — runs {args.start} to {args.start + args.n - 1} (n={args.n})")
    print(f"Evidence: {evidence_dir}")
    print(f"Timeout per run: {args.timeout}s")
    print("=" * 60)

    results = []
    pass_count = fail_count = err_count = 0

    for i in range(args.start, args.start + args.n):
        print(f"\n=== Run {i}/{args.start + args.n - 1} ===", flush=True)
        try:
            r = run_one(i, prompt, evidence_dir, timeout_sec=args.timeout)
            status = "PASS" if r.get('pass') else "FAIL"
            print(f"  [{status}] in {r.get('duration_sec', '?')}s | log={r.get('log_size', '?')}B", flush=True)
            for k, h in r.get('hard_checks', {}).items():
                icon = "[OK]" if h['pass'] is True else "[NO]" if h['pass'] is False else "[??]"
                print(f"    {icon} {k}: {h['msg']}", flush=True)
            if r.get('error'):
                print(f"    [ERROR] {r['error']}", flush=True)
            results.append({'run': i, **r})
            if r.get('pass'):
                pass_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  [CRASH] {e}", flush=True)
            import traceback; traceback.print_exc()
            results.append({'run': i, 'pass': False, 'error': str(e)})
            err_count += 1
        # Save summary after each run (in case we crash)
        save_summary(evidence_dir, pass_count, fail_count, err_count, results)
        if i < args.start + args.n - 1:
            time.sleep(args.per_run_sleep)

    # Final summary
    total = pass_count + fail_count + err_count
    rate = (pass_count / total * 100) if total else 0
    print(f"\n{'=' * 60}")
    print(f"FINAL: {pass_count} PASS / {fail_count} FAIL / {err_count} ERROR (n={total})")
    print(f"Success rate: {rate:.1f}%")
    if total > 0:
        import math
        pp = pass_count / total
        n = total
        z = 1.96
        denom = 1 + z**2/n
        center = (pp + z**2/(2*n)) / denom
        spread = z * math.sqrt(pp*(1-pp)/n + z**2/(4*n**2)) / denom
        print(f"Wilson 95% CI: [{max(0, center-spread)*100:.1f}%, {min(1, center+spread)*100:.1f}%]")
    print(f"Summary: {evidence_dir}/SUMMARY.json")


def save_summary(evidence_dir, p, f, e, results):
    total = p + f + e
    rate = (p / total * 100) if total else 0
    summary = {
        'date': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'n_total': total, 'pass': p, 'fail': f, 'error': e,
        'success_rate_pct': round(rate, 1),
        'runs': results,
    }
    (evidence_dir / 'SUMMARY.json').write_text(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
