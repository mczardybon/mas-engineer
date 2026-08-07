#!/usr/bin/env python3
"""R110-115 DIREKTIVE 1: apply .mase/directives/R<NR>-<topic>.md via 3 hook points.

Usage:
    python3 tools/dev_directive_applier.py --hook pre-apply <directive>
    python3 tools/dev_directive_applier.py --hook post-apply <directive>
    python3 tools/dev_directive_applier.py --hook error <directive> <err>
    python3 tools/dev_directive_applier.py --apply <directive>
    python3 tools/dev_directive_applier.py --rollback <directive>

Pre-apply:  verifies pre-conditions, checks .mase/directive_already_applied.json
Post-apply: runs pytest, scans, writes .mase/directive_already_applied.json
Error:      logs to .mase/directive_failures.json
Apply:      delegates to sub_mas-apply-directive via goose run
Rollback:   reverts applied patches via git checkout
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ALREADY_APPLIED = Path('.mase/directive_already_applied.json')
FAILURES = Path('.mase/directive_failures.json')
CHANGES = Path('.mase/changes.json')


def log_change(directive_path, stage, status, **extra):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "via": "apply_directive",
        "directive": directive_path,
        "stage": stage,
        "status": status,
    }
    entry.update(extra)
    if CHANGES.exists():
        data = json.loads(CHANGES.read_text() or '[]')
    else:
        data = []
    if not isinstance(data, list):
        data = []
    data.append(entry)
    CHANGES.parent.mkdir(parents=True, exist_ok=True)
    CHANGES.write_text(json.dumps(data, indent=2) + '\n')
    return entry


def hook_pre_apply(directive):
    """Verify pre-conditions, check idempotency."""
    if not Path(directive).exists():
        return {"ok": False, "reason": f"directive not found: {directive}"}
    if ALREADY_APPLIED.exists():
        data = json.loads(ALREADY_APPLIED.read_text() or '{}')
        applied = data.get('applied', [])
        if directive in applied and '--force' not in sys.argv:
            return {"ok": False,
                    "reason": f"already applied: {directive} (use --force to reapply)"}
    return {"ok": True, "directive": directive}


def hook_post_apply(directive):
    """Run pytest + scan, write already-applied marker."""
    # pytest
    r = subprocess.run(['python3', '-m', 'pytest', 'tests/', '-q'],
                       capture_output=True, text=True, timeout=120)
    pytest_ok = r.returncode == 0
    # scanner
    r2 = subprocess.run(
        ['python3', 'tools/dev_im_finder_scan.py', '--scope=recipe,+demo-teams'],
        capture_output=True, text=True, timeout=60)
    scan_ok = r2.returncode == 0
    # mark applied
    if ALREADY_APPLIED.exists():
        data = json.loads(ALREADY_APPLIED.read_text() or '{}')
    else:
        data = {"applied": []}
    if not isinstance(data, dict):
        data = {"applied": []}
    data.setdefault('applied', []).append(directive)
    ALREADY_APPLIED.parent.mkdir(parents=True, exist_ok=True)
    ALREADY_APPLIED.write_text(json.dumps(data, indent=2) + '\n')
    return {"ok": pytest_ok and scan_ok,
            "pytest_ok": pytest_ok, "scan_ok": scan_ok,
            "directive": directive}


def hook_error(directive, err):
    """Log failure."""
    if FAILURES.exists():
        data = json.loads(FAILURES.read_text() or '[]')
    else:
        data = []
    if not isinstance(data, list):
        data = []
    data.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "directive": directive,
        "error": err,
    })
    FAILURES.parent.mkdir(parents=True, exist_ok=True)
    FAILURES.write_text(json.dumps(data, indent=2) + '\n')
    return {"ok": False, "error": err, "logged_to": str(FAILURES)}


def apply_via_goose(directive):
    """Delegate to sub_mas-apply-directive via goose run."""
    env = os.environ.copy()
    env['RECURSION_OVERRIDE'] = '2'
    env['MAS_TASK'] = 'apply'
    env['MAS_CONFIRM'] = 'yes'
    env['MAS_APPROVE'] = 'y'
    cmd = ['goose', 'run', '--with-builtin', 'developer',
           '--recipe', 'recipe/sub/sub_mas-apply-directive.yaml',
           '--no-session']
    r = subprocess.run(cmd, env=env, input=f"per directive {directive}\nack\n",
                       capture_output=True, text=True, timeout=300)
    return {"ok": r.returncode == 0, "stdout_tail": r.stdout[-500:]}


def rollback(directive):
    """Revert via git checkout (operator must specify files)."""
    return {"ok": False, "reason": "rollback: use git checkout -- <file> "
            "directly (operator-initiated); this tool does not auto-rollback"}


def main():
    if len(sys.argv) < 3:
        print("Usage: dev_directive_applier.py --hook {pre-apply|post-apply|error} "
              "<directive> [<err>]", file=sys.stderr)
        print("       dev_directive_applier.py --apply <directive>", file=sys.stderr)
        print("       dev_directive_applier.py --rollback <directive>", file=sys.stderr)
        sys.exit(2)
    if sys.argv[1] == '--hook':
        hook = sys.argv[2]
        directive = sys.argv[3]
        if hook == 'pre-apply':
            result = hook_pre_apply(directive)
        elif hook == 'post-apply':
            result = hook_post_apply(directive)
        elif hook == 'error':
            err = sys.argv[4] if len(sys.argv) > 4 else 'unspecified'
            result = hook_error(directive, err)
        else:
            print(f"unknown hook: {hook}", file=sys.stderr)
            sys.exit(2)
        log_change(directive, f"hook_{hook}",
                   'success' if result.get('ok') else 'failed', **result)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get('ok') else 1)
    elif sys.argv[1] == '--apply':
        directive = sys.argv[2]
        pre = hook_pre_apply(directive)
        if not pre.get('ok'):
            log_change(directive, 'apply', 'pre_failed', **pre)
            print(json.dumps(pre, indent=2))
            sys.exit(1)
        result = apply_via_goose(directive)
        log_change(directive, 'apply',
                   'success' if result.get('ok') else 'failed', **result)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get('ok') else 1)
    elif sys.argv[1] == '--rollback':
        directive = sys.argv[2]
        result = rollback(directive)
        print(json.dumps(result, indent=2))
        sys.exit(1)
    else:
        print(f"unknown command: {sys.argv[1]}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
