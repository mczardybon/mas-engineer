#!/usr/bin/env python3
"""R110-43 tool-syntax-check: AST + hard-coded path scan for tools/*.py

Lightweight equivalent of R10 CORONASHIELD for Python tool files.
Catches:
  - Syntax errors (ast.parse)
  - Hard-coded absolute paths (HARDCODED_PATH_RE, same as test_no_hard_coded_absolute_paths_in_tools)

Usage:
  python3 scripts/r11043-tool-syntax-check.py tools/              # scan a dir
  python3 scripts/r11043-tool-syntax-check.py tools/foo.py        # scan one file
  python3 scripts/r11043-tool-syntax-check.py tools/ --allow tools/dev_im_finder_scan.py

R110-43 established this; previously the 7 hard-coded absolute paths in tools/
were only caught by a pytest test that runs at e2e time, not at pre-commit/pre-push.
This script can run in <1s and is suitable for pre-commit hooks.
"""

import argparse
import ast
import re
import sys
from pathlib import Path

HARDCODED_PATH_RE = re.compile(
    r"""(?P<path>["'](/root/|/home/(?!\\.)|/Users/(?!\\.)|/opt/(?!\\.))(?:[^"'\\s]*)["'])""",
    re.MULTILINE,
)

DEFAULT_ALLOWLIST = {
    "tools/cleanup_repo_v1.sh",
    "tools/dev_im_finder_scan.py",
}


def check_file(path: Path, allowlist: set) -> list[str]:
    errors = []
    rel = str(path)
    if rel in allowlist:
        return errors

    try:
        content = path.read_text()
    except Exception as e:
        return [f"read error: {e}"]

    # AST syntax check
    try:
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"line {e.lineno}: SyntaxError: {e.msg}")

    # Hard-coded absolute paths
    for i, line in enumerate(content.splitlines(), 1):
        for m in HARDCODED_PATH_RE.finditer(line):
            errors.append(f"line {i}: hard-coded path: {m.group('path')}")

    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="File or directory to scan")
    ap.add_argument("--allow", action="append", default=[], help="Add path to allowlist")
    args = ap.parse_args()

    allowlist = DEFAULT_ALLOWLIST | set(args.allow)

    target = Path(args.target)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.rglob("*.py"))
    else:
        print(f"FATAL: {target} is not a file or directory", file=sys.stderr)
        sys.exit(2)

    print(f"=== R110-43 tool-syntax-check: {target} ({len(files)} files) ===")
    total_errors = 0
    for f in files:
        errs = check_file(f, allowlist)
        if errs:
            total_errors += len(errs)
            print(f"\n  ❌ {f}")
            for e in errs:
                print(f"      - {e}")

    print()
    if total_errors == 0:
        print(f"=== R110-43 RESULT: 0 errors in {len(files)} files ===")
        sys.exit(0)
    else:
        print(f"=== R110-43 RESULT: {total_errors} errors ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
