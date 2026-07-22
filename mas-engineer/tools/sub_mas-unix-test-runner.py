#!/usr/bin/env python3
"""
sub_mas-unix-test-runner.py — Manual implementation of sub_mas-unix-test-runner.

This runs the SAME checks the sub_mas-unix-test-runner recipe would perform when
called by the mas-engineer. It uses the POSIX `test` builtin via subprocess.

Usage:
    python3 tools/sub_mas-unix-test-runner.py [--scope all|recipe|sub|docs|tests]
"""
import subprocess
import os
import sys
import json
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()


def run_test(check_args: str) -> bool:
    """Run a POSIX `test` expression. Returns True if check passes."""
    r = subprocess.run(["test"] + check_args.split(), capture_output=True, text=True)
    return r.returncode == 0


def get_checks(scope: str) -> list:
    """Return the list of (name, test_args) checks for the given scope."""
    checks = []

    # Universal checks (always run)
    checks.append(("workspace is a directory", f"-d {REPO_ROOT}"))

    if scope in ("all", "recipe"):
        # Recipe structure
        checks.append(("recipe/sub/ exists", f"-d {REPO_ROOT}/recipe/sub"))
        checks.append(("recipe/instructions/ exists", f"-d {REPO_ROOT}/recipe/instructions"))
        checks.append(("recipe/sub_mas-general-improver.yaml exists",
                      f"-f {REPO_ROOT}/recipe/sub/sub_mas-general-improver.yaml"))
        checks.append(("recipe/sub_mas-master-constitution.yaml exists",
                      f"-f {REPO_ROOT}/recipe/sub/sub_mas-master-constitution.yaml"))

        # All sub-recipe files are non-empty
        for f in sorted((REPO_ROOT / "recipe" / "sub").glob("*.yaml")):
            rel = f.relative_to(REPO_ROOT)
            checks.append((f"recipe/{rel} is non-empty", f"-s {f}"))

        # All sub-recipe files have .yaml extension (sanity)
        for f in sorted((REPO_ROOT / "recipe" / "sub").iterdir()):
            if f.is_file():
                expected_ext = ".yaml"
                actual_ext = f.suffix
                checks.append((f"recipe/{f.name} has .yaml extension",
                              f'"{actual_ext}" = "{expected_ext}"'))

    if scope in ("all", "tests"):
        checks.append(("tests/ exists", f"-d {REPO_ROOT}/tests"))
        checks.append(("tests/__init__.py exists", f"-f {REPO_ROOT}/tests/__init__.py"))
        checks.append(("tests/conftest.py exists", f"-f {REPO_ROOT}/tests/conftest.py"))

    if scope in ("all", "docs"):
        checks.append(("docs/ exists", f"-d {REPO_ROOT}/docs"))
        checks.append(("docs/manifest.md exists", f"-f {REPO_ROOT}/docs/manifest.md"))
        checks.append(("docs/procedures.md exists", f"-f {REPO_ROOT}/docs/procedures.md"))

    if scope in ("all", "tools"):
        checks.append(("tools/ exists", f"-d {REPO_ROOT}/tools"))
        # All .py files in tools/ are non-empty
        for f in sorted((REPO_ROOT / "tools").glob("*.py")):
            checks.append((f"tools/{f.name} is non-empty", f"-s {f}"))

    return checks


def main():
    parser = argparse.ArgumentParser(description="sub_mas-unix-test-runner (POSIX test builtin)")
    parser.add_argument("--scope", default="all", choices=["all", "recipe", "tests", "docs", "tools"])
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    checks = get_checks(args.scope)
    passed = 0
    failed = 0
    failures = []

    print(f"🔧 sub_mas-unix-test-runner — scope={args.scope}")
    print(f"   Running {len(checks)} POSIX `test` checks...\n")

    for name, test_args in checks:
        ok = run_test(test_args)
        status = "✓" if ok else "✗"
        if args.json:
            pass
        else:
            print(f"  {status} {name}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append({"name": name, "test": test_args})

    total = len(checks)
    score = (passed * 100 // total) if total > 0 else 0

    if args.json:
        result = {
            "scope": args.scope,
            "total": total,
            "passed": passed,
            "failed": failed,
            "score_pct": score,
            "failures": failures,
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  Total: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print(f"  Score: {score}%")
        if score == 100:
            print(f"  Status: ✅ PASS")
        elif score >= 90:
            print(f"  Status: ⚠️  DEGRADED")
        else:
            print(f"  Status: ❌ FAIL")
        print(f"{'='*60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
