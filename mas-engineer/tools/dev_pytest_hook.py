#!/usr/bin/env python3
"""
dev_pytest_hook.py — Checker-Hook for pytest
Aktiviert: pytest --checker-hook
Checks vor/nach Test-Lauf die Rule-Compliance.
"""
import sys, subprocess, json
from pathlib import Path

# R110-303: Anchor all tool paths to this module's directory so the
# checks are CWD-robust. Without this, a test that calls os.chdir
# without restoring (e.g. one of the r110298 / r110261 / r110287
# test files) makes os.path.exists('tools/dev_rule_checker.py')
# return False from a different cwd, suppressing the
# post-test "failed" recommendation line and breaking
# test_run_post_test_checks_fail_prints_recommendation in the
# full-suite run. See tests/conftest.py:14-17 which already flagged
# this as a CWD-fragility bug (R110-129).
_HERE = Path(__file__).resolve().parent
_CHECKER = _HERE / "dev_rule_checker.py"
_AUDIT_DEPS = _HERE / "dev_audit_deps.py"

def run_pre_test_checks():
    """Checks Checker-status vor Test-Lauf."""
    if not _CHECKER.exists():
        print("DEV-CHECKER: not found (no Generic-Improver)")
        return True

    r = subprocess.run([sys.executable, str(_CHECKER), '--mode', 'generic', '--health'], capture_output=True, text=True)
    if r.returncode != 0:
        print("⚠️ DEV-CHECKER: Health-Check failed")
        try:
            data = json.loads(r.stdout)
            if data.get('score', 10) < 5:
                print(f"  Score: {data['score']}/10 — Rule-system ist schwach")
        except:
            pass
        return True  # Only warnen, not blocken

    print("✅ DEV-CHECKER: Heoldh OK")
    return True

def run_post_test_checks(pytest_exit_code):
    """Checks whether tests need new rules (post-test phase).

    Spec (R110-77-follow-up): when tests fail, the output must contain
    the keyword 'failed' as an explicit signal — not buried inside a
    sentence like 'Tests failed' which only matches by substring. The
    test_tools_framework test_run_post_test_checks_fail_prints_recommendation
    test currently passes by substring match; making the keyword
    explicit and uppercase-prefixed makes the log greppable and the
    contract obvious.
    """
    if pytest_exit_code > 0:
        # Tests failed -> Check whether rule-adjustment needed
        # R110-303: use the CWD-anchored _CHECKER (see _HERE above)
        if _CHECKER.exists():
            print("\n[failed] post-test checks flagging rule-adjustment needed")
            print("DEV-CHECKER: Recommendation:")
            print(f"  python3 {_AUDIT_DEPS} --target .")
    return True

def main():
    if '--checker-hook' not in sys.argv:
        print("Usage: pytest --checker-hook")
        sys.exit(1)

    run_pre_test_checks()
    # pytest exit code aboutgeben if available
    exit_code = int(sys.argv[-1]) if len(sys.argv) > 2 and sys.argv[-1].isdigit() else 0
    run_post_test_checks(exit_code)

if __name__ == "__main__":
    main()
