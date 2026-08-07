#!/usr/bin/env python3
"""
R10 CORONASHIELD validator for mas-engineer recipe wrappers.

Per R10 (from sub_mas-yaml-editor.md workflow):
  "⛔ BEFORE: python3 -c 'import yaml; yaml.safe_load(open(...))' → invalid? ABORT"
  "⛔ AFTER:  python3 -c 'import yaml; yaml.safe_load(open(...))' → invalid? ROLLBACK"

This script enforces R10 on a directory of recipe-wrappers BEFORE we run them
with `goose run`. It performs:
  1. YAML parse check (safe_load)
  2. safe_dump → safe_load round-trip check
  3. Sub-recipe path resolution check (paths must exist on disk)
  4. Required-fields check (name, version, prompt, sub_recipes)

"""
import sys
import os
import yaml
import argparse


def validate_wrapper(path: str, strict: bool = False) -> tuple[bool, list[str]]:
    """Validate one wrapper-recipe. Returns (ok, errors)."""
    errors = []
    # 1. safe_load (R10 step 1: BEFORE check)
    try:
        with open(path) as f:
            content = f.read()
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {e}"]

    if not isinstance(parsed, dict):
        return False, [f"Root must be a dict, got {type(parsed).__name__}"]

    # 2. safe_dump → safe_load round-trip (R10 step 3: AFTER check)
    try:
        re_dumped = yaml.safe_dump(parsed, default_flow_style=False, sort_keys=False, width=200)
        re_parsed = yaml.safe_load(re_dumped)
        if parsed != re_parsed:
            errors.append("Round-trip mismatch: safe_dump → safe_load lost data")
    except yaml.YAMLError as e:
        errors.append(f"Round-trip YAML error: {e}")

    # 3. Sub-recipe paths (the BUG-1 from R110-28)
    if 'sub_recipes' in parsed:
        for sr in parsed['sub_recipes']:
            if not isinstance(sr, dict):
                errors.append(f"sub_recipes entry is not a dict: {sr}")
                continue
            sub_path = sr.get('path', '')
            if not sub_path:
                errors.append(f"sub_recipe missing 'path' field: {sr}")
            else:
                # gotcha #11: relative paths resolve from recipe's own dir, NOT cwd
                # Per R10 comment: "relative paths resolve from recipe's own dir"
                # Bug: previously resolved from cwd (False-positive for ./sub_mas-*.yaml)
                # Fix: if path is relative (no leading /), prepend recipe's own dir.
                if not os.path.isabs(sub_path):
                    recipe_dir = os.path.dirname(os.path.abspath(path))
                    candidate = os.path.join(recipe_dir, sub_path)
                    if os.path.exists(candidate):
                        pass  # OK, path resolves correctly
                    else:
                        errors.append(
                            f"sub_recipe path does not exist: {sub_path} "
                            f"(gotcha #11: tried {candidate}, neither cwd-relative nor "
                            f"recipe-dir-relative resolves)"
                        )
                elif not os.path.exists(sub_path):
                    errors.append(
                        f"sub_recipe path does not exist: {sub_path} "
                        f"(gotcha #11: absolute path, but file not found)"
                    )

    # 4. Required fields
    for field in ('name', 'version', 'prompt'):
        if field not in parsed:
            errors.append(f"Missing required field: '{field}'")
        elif field == 'prompt' and len(str(parsed[field])) < 20:
            errors.append(f"prompt is too short ({len(parsed[field])} chars, min 20)")

    if strict:
        # Strict mode: also check title/description
        for field in ('title', 'description'):
            if field not in parsed:
                errors.append(f"[strict] Missing recommended field: '{field}'")

    return (len(errors) == 0), errors


def main():
    parser = argparse.ArgumentParser(description="R10 CORONASHIELD validator for recipe wrappers")
    parser.add_argument("wrapper_dir", help="Directory containing wrapper-*.yaml files")
    parser.add_argument("--strict", action="store_true", help="Also check title/description")
    args = parser.parse_args()

    if not os.path.isdir(args.wrapper_dir):
        print(f"FATAL: not a directory: {args.wrapper_dir}", file=sys.stderr)
        return 2

    yaml_files = sorted(f for f in os.listdir(args.wrapper_dir) if f.endswith('.yaml'))
    if not yaml_files:
        print(f"FATAL: no .yaml files in {args.wrapper_dir}", file=sys.stderr)
        return 2

    n_pass = 0
    n_fail = 0
    print(f"=== R10 CORONASHIELD validate: {args.wrapper_dir} ({len(yaml_files)} files) ===")
    print()
    for fname in yaml_files:
        path = f"{args.wrapper_dir}/{fname}"
        ok, errors = validate_wrapper(path, strict=args.strict)
        if ok:
            print(f"  ✓ {fname:50s} R10-conform")
            n_pass += 1
        else:
            print(f"  ❌ {fname:50s}")
            for e in errors:
                print(f"      - {e}")
            n_fail += 1

    print()
    print(f"=== R10 RESULT: {n_pass} pass, {n_fail} fail ===")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
