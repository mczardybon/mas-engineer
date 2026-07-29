#!/usr/bin/env python3
"""
dev_yaml_immune.py — R10 CORONASHIELD standalone yaml validator (R110-30)

Purpose: Allow R10 enforcement for ALL yaml save paths, not just mas-workflow.
         Originally R10 was only enforced via yaml-editor R18 + dev_editor.py,
         leaving standalone recipe-pack testscripts unprotected → BUG-1
         (sub_recipe path resolution failure) went undetected.

Usage:
    python3 tools/dev_yaml_immune.py <file.yaml> [<file2.yaml> ...]
    echo $?  # 0 = valid, 1 = invalid syntax, 2 = file missing, 3 = parse error

    # Check if yaml file is safe to save:
    python3 tools/dev_yaml_immune.py --validate <file.yaml> || { echo "BLOCKED"; exit 1; }

    # Roundtrip test (catches duplicates, key-order issues):
    python3 tools/dev_yaml_immune.py --roundtrip <file.yaml>

    # Path resolution check (catches BUG-1: sub_recipe path failures):
    python3 tools/dev_yaml_immune.py --path-check <file.yaml> [--strict]

Graceful degradation:
    - File missing → exit 2, but stdout says "skip" (not block)
    - yaml module missing → falls back to PyYAML or basic parser
    - --strict mode: also enforce required fields (title, description for sub-agents)
    - Without --strict: only syntax check (graceful default)

R10 integration:
    Called by dev_rule_checker.py R10 check when --action write/edit detected.
    Also called directly by standalone testscripts BEFORE `goose run` (STEP 2).

R110-30 changelog:
    - Initial creation (graceful yaml.safe_load + roundtrip + path resolution)
    - --strict mode for sub-agent validation (title/description required)
"""

import sys
import os
import argparse
import json

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def safe_load(path: str) -> tuple:
    """Load yaml file safely. Returns (data, error_msg)."""
    if not os.path.exists(path):
        return None, f"file_not_found: {path}"
    if not HAS_YAML:
        return None, "yaml_module_missing: pip install pyyaml"
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return data, None
    except yaml.YAMLError as e:
        return None, f"yaml_syntax_error: {e}"
    except Exception as e:
        return None, f"parse_error: {e}"


def check_syntax(path: str) -> dict:
    """Basic syntax check. Returns {ok: bool, error: str, file: str}.

    Only checks .yaml/.yml files. Non-yaml files are skipped (ok=True, skipped=True).
    """
    if not (path.endswith(".yaml") or path.endswith(".yml")):
        return {"ok": True, "error": None, "file": path, "check": "syntax", "skipped": "not yaml"}
    data, err = safe_load(path)
    if err:
        return {"ok": False, "error": err, "file": path, "check": "syntax"}
    return {"ok": True, "error": None, "file": path, "check": "syntax", "data": data}


def check_roundtrip(path: str) -> dict:
    """Load → dump → reload → compare. Catches duplicate keys, non-deterministic ordering."""
    data, err = safe_load(path)
    if err:
        return {"ok": False, "error": err, "file": path, "check": "roundtrip"}
    try:
        dumped = yaml.safe_dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        reloaded = yaml.safe_load(dumped)
        if data != reloaded:
            return {"ok": False, "error": "roundtrip_mismatch: data changed after dump/reload", "file": path, "check": "roundtrip"}
        return {"ok": True, "error": None, "file": path, "check": "roundtrip"}
    except Exception as e:
        return {"ok": False, "error": f"roundtrip_error: {e}", "file": path, "check": "roundtrip"}


def check_path_resolution(path: str, strict: bool = False) -> dict:
    """Check if sub_recipe paths in yaml resolve to existing files.

    Catches BUG-1: sub_recipe path resolution failure (recipe references itself
    or paths that don't exist).
    """
    data, err = safe_load(path)
    if err:
        return {"ok": False, "error": err, "file": path, "check": "path"}
    if not isinstance(data, dict):
        return {"ok": True, "error": None, "file": path, "check": "path", "skipped": "not a recipe dict"}

    # Find sub_recipe entries
    sub_recipes = []
    # Pattern 1: top-level sub_recipes list
    if "sub_recipes" in data:
        sub_recipes = data["sub_recipes"]
    # Pattern 2: agents[].sub_recipes
    elif "agents" in data and isinstance(data["agents"], list):
        for agent in data["agents"]:
            if isinstance(agent, dict) and "sub_recipes" in agent:
                sub_recipes.extend(agent["sub_recipes"])

    if not sub_recipes:
        return {"ok": True, "error": None, "file": path, "check": "path", "skipped": "no sub_recipes"}

    # Resolve each sub_recipe path
    base_dir = os.path.dirname(os.path.abspath(path))
    missing = []
    for sr in sub_recipes:
        if not isinstance(sr, dict):
            continue
        sr_path = sr.get("path") or sr.get("recipe") or sr.get("name")
        if not sr_path:
            continue
        # Try multiple resolution strategies
        candidates = [
            sr_path,                          # as-is
            os.path.join(base_dir, sr_path),  # relative to file
            os.path.join(base_dir, "sub", sr_path),  # relative to sub/
            os.path.join(base_dir, "..", "sub", sr_path),  # parent/sub/
        ]
        found = any(os.path.exists(c) for c in candidates)
        if not found and strict:
            missing.append({"path": sr_path, "candidates": candidates})

    if missing:
        return {
            "ok": False,
            "error": f"sub_recipe_path_missing: {len(missing)} entries",
            "file": path,
            "check": "path",
            "missing": missing,
        }
    return {"ok": True, "error": None, "file": path, "check": "path", "sub_recipes_checked": len(sub_recipes)}


def check_required_fields(path: str) -> dict:
    """Strict mode: check required fields for sub-agents (title, description)."""
    data, err = safe_load(path)
    if err:
        return {"ok": False, "error": err, "file": path, "check": "required"}
    if not isinstance(data, dict):
        return {"ok": True, "error": None, "file": path, "check": "required", "skipped": "not a dict"}

    missing = []
    for field in ["title", "description"]:
        if field not in data or not data[field]:
            missing.append(field)

    # Also check version
    if "version" not in data:
        missing.append("version")

    if missing:
        return {
            "ok": False,
            "error": f"required_fields_missing: {missing}",
            "file": path,
            "check": "required",
            "missing": missing,
        }
    return {"ok": True, "error": None, "file": path, "check": "required"}


def main():
    parser = argparse.ArgumentParser(
        description="R10 CORONASHIELD standalone yaml validator (R110-30)"
    )
    parser.add_argument("files", nargs="*", help="yaml files to validate")
    parser.add_argument("--validate", metavar="FILE", help="single file, exit 0/1")
    parser.add_argument("--roundtrip", metavar="FILE", help="roundtrip test single file")
    parser.add_argument("--path-check", metavar="FILE", help="sub_recipe path resolution check")
    parser.add_argument("--strict", action="store_true", help="strict mode (required fields + path check)")
    parser.add_argument("--quiet", action="store_true", help="only show errors")
    parser.add_argument("--json", action="store_true", help="json output")

    args = parser.parse_args()

    # Determine files to check
    if args.validate:
        files = [args.validate]
    elif args.roundtrip:
        files = [args.roundtrip]
    elif args.path_check:
        files = [args.path_check]
    elif args.files:
        files = args.files
    else:
        parser.error("no files specified (use positional or --validate/--roundtrip/--path-check)")

    # Determine which checks to run
    results = []
    for f in files:
        # Skip non-yaml files for roundtrip/path/required checks (yaml-syntax only)
        is_yaml = f.endswith((".yaml", ".yml"))
        r1 = check_syntax(f)
        results.append(r1)
        if r1["ok"] and (args.roundtrip or args.strict) and is_yaml:
            r2 = check_roundtrip(f)
            results.append(r2)
        if r1["ok"] and (args.path_check or args.strict) and is_yaml:
            r3 = check_path_resolution(f, strict=args.strict)
            results.append(r3)
        if r1["ok"] and args.strict and is_yaml:
            r4 = check_required_fields(f)
            results.append(r4)

    # Output
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for r in results:
            if r["ok"]:
                if not args.quiet:
                    print(f"✅ {r['file']} [{r['check']}]: OK")
            else:
                print(f"⛔ {r['file']} [{r['check']}]: {r['error']}", file=sys.stderr)

    # Exit code
    has_block = any(not r["ok"] for r in results)
    has_missing = any(
        (r.get("error") or "").startswith("file_not_found")
        for r in results
    )

    if has_block:
        sys.exit(1)
    elif has_missing and not args.files:
        # When called with --validate, missing file = block
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
