#!/usr/bin/env python3
"""
dev_pytest_hook.py — Checker-Hook for pytest
Aktiviert: pytest --checker-hook
Checks vor/nach Test-Lauf die Rule-Compliance.
"""
import os, sys, subprocess, json

def run_pre_test_checks():
    """Checks Checker-Status vor Test-Lauf."""
    checker_path = 'tools/dev_rule_checker.py'
    if not os.path.exists(checker_path):
        print("DEV-CHECKER: not found (no Generic-Improver)")
        return True
    
    r = subprocess.run(['python3', checker_path, '--mode', 'generic', '--health'], capture_output=True, text=True)
    if r.returncode != 0:
        print("\u26a0\ufe0f DEV-CHECKER: Health-Check failed")
        try:
            data = json.loads(r.stdout)
            if data.get('score', 10) < 5:
                print(f"  Score: {data['score']}/10 — Rule-System ist schwach")
        except:
            pass
        return True  # Only warnen, not blocken
    
    print("\u2705 DEV-CHECKER: Health OK")
    return True

def run_post_test_checks(pytest_exit_code):
    """Checks ob Tests new Rulen need."""
    if pytest_exit_code > 0:
        # Tests failed -> Check ob Rule-Anpassung notig
        checker_path = 'tools/dev_rule_checker.py'
        if os.path.exists(checker_path):
            print("\nDEV-CHECKER: Tests failed — Recommendation:")
            print("  python3 tools/dev_audit_deps.py --target .")
    return True

def main():
    if '--checker-hook' not in sys.argv:
        print("Nutzung: pytest --checker-hook")
        sys.exit(1)
    
    run_pre_test_checks()
    # pytest exit code aboutgeben if available
    exit_code = int(sys.argv[-1]) if len(sys.argv) > 2 and sys.argv[-1].isdigit() else 0
    run_post_test_checks(exit_code)

if __name__ == "__main__":
    main()
