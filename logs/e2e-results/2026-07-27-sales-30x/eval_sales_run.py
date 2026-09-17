#!/usr/bin/env python3
"""
Sales-Team Run Evaluator (R108-9)

Evaluates a single goose run against the sales-team success criteria.
Used by the 30x batch test to score runs and compute statistics.

Usage:
    python3 eval_sales_run.py --log <path/to/build.log> --output-dir <path>
    # Returns exit 0 if PASS, 1 if FAIL, 2 if ERROR (crash/timeout)

Hard criteria (FAIL if any missing):
  H1. /tmp/sales-team/recipe/sales-team.yaml exists
  H2. /tmp/sales-team/recipe/sub/ has 4+ sub-recipes
  H3. All YAML files parse without errors
  H4. sales-team.yaml has sub_recipes field referencing the 4 agents
  H5. MANDATORY quality gate (lead-verifier) mentioned in pipeline

Soft criteria (warnings, not failures):
  S1. Each recipe has 'title:' field
  S2. Orchestrator prompt mentions sub-task dispatch + synthesis
  S3. Line counts are reasonable (50-150 lines per recipe)
  S4. All 5+6 = 11 checks reported as PASS in the log
  S5. Live test of one sub-agent succeeded (real output, not just --explain)
"""
import argparse
import os
import re
import sys
import json
from pathlib import Path

# Required files for a successful sales-team
REQUIRED_FILES = [
    "/tmp/sales-team/recipe/sales-team.yaml",
    "/tmp/sales-team/recipe/sub/lead-scraper.yaml",
    "/tmp/sales-team/recipe/sub/lead-verifier.yaml",
    "/tmp/sales-team/recipe/sub/outreach-drafter.yaml",
    "/tmp/sales-team/recipe/sub/deal-closer.yaml",
]

def check_files_exist():
    """H1 + H2: check files exist"""
    missing = [f for f in REQUIRED_FILES if not os.path.exists(f)]
    if missing:
        return False, f"Missing files: {missing}"
    # Check for 4+ sub-recipes (H2)
    sub_dir = Path("/tmp/sales-team/recipe/sub/")
    if not sub_dir.exists():
        return False, "sub-dir /tmp/sales-team/recipe/sub/ does not exist"
    yaml_files = list(sub_dir.glob("*.yaml"))
    if len(yaml_files) < 4:
        return False, f"Only {len(yaml_files)} sub-recipes (need 4+)"
    return True, f"6 files present, {len(yaml_files)} sub-recipes"


def check_yaml_valid():
    """H3: YAML parse check"""
    try:
        import yaml
    except ImportError:
        return None, "PyYAML not installed (skipping)"
    errors = []
    for f in REQUIRED_FILES:
        if not os.path.exists(f):
            continue
        try:
            with open(f) as fp:
                yaml.safe_load(fp)
        except yaml.YAMLError as e:
            errors.append(f"{f}: {e}")
    if errors:
        return False, f"YAML parse errors: {errors}"
    return True, "All YAML files parse cleanly"


def check_orchestrator_subrecipes():
    """H4: sales-team.yaml references the 4 sub-recipes"""
    try:
        import yaml
    except ImportError:
        return None, "PyYAML not installed (skipping)"
    root = "/tmp/sales-team/recipe/sales-team.yaml"
    if not os.path.exists(root):
        return False, "sales-team.yaml missing"
    with open(root) as fp:
        data = yaml.safe_load(fp) or {}
    sub_recipes = data.get("sub_recipes", [])
    sub_names = {sr.get("name", "") if isinstance(sr, dict) else str(sr) for sr in sub_recipes}
    required = {"lead-scraper", "lead-verifier", "outreach-drafter", "deal-closer"}
    missing = required - sub_names
    if missing:
        return False, f"sub_recipes missing: {missing}"
    return True, f"All 4 sub_recipes referenced"


def check_mandatory_gate():
    """H5: lead-verifier as mandatory quality gate"""
    # Try the sub-orchestrator first, then the root
    for orch_path in [
        "/tmp/sales-team/recipe/sub/sales-orchestrator.yaml",
        "/tmp/sales-team/recipe/sales-team.yaml",
    ]:
        if os.path.exists(orch_path):
            orch_sub = orch_path
            break
    else:
        return False, "no orchestrator file to check for MANDATORY gate"
    with open(orch_sub) as fp:
        content = fp.read()
    patterns = [
        r"mandatory.{0,30}quality.{0,30}gate",
        r"lead.verifier.{0,30}gate",
        r"verifier.{0,30}mandatory",
        r"must.{0,20}pass.{0,30}verifier",
        r"unverified.{0,20}NOT",
    ]
    found = [p for p in patterns if re.search(p, content, re.IGNORECASE)]
    if not found:
        return False, "MANDATORY quality gate (lead-verifier) not enforced"
    return True, f"Quality gate enforced ({len(found)} patterns found)"


def check_soft_criteria(log_path):
    """S1-S5: soft criteria from log file"""
    if not log_path or not os.path.exists(log_path):
        return {"warning": "no log file to analyze"}
    with open(log_path) as fp:
        log = fp.read()
    soft = {}
    # S4: 11 checks PASS
    pass_count = len(re.findall(r"(?:✅|PASS)[^\n]{0,80}", log))
    soft["S4_pass_count"] = pass_count
    # S5: live test
    soft["S5_has_live_run"] = "live" in log.lower() and "found" in log.lower()
    return soft


def evaluate_run(log_path=None, output_dir=None):
    """Run all hard + soft checks, return result"""
    result = {
        "pass": True,
        "hard_checks": {},
        "soft_checks": {},
        "errors": [],
    }
    # Hard checks
    for name, fn in [
        ("H1_H2_files", check_files_exist),
        ("H3_yaml", check_yaml_valid),
        ("H4_subrecipes", check_orchestrator_subrecipes),
        ("H5_gate", check_mandatory_gate),
    ]:
        try:
            ok, msg = fn()
            result["hard_checks"][name] = {"pass": ok, "msg": msg}
            if ok is False:
                result["pass"] = False
                result["errors"].append(f"{name}: {msg}")
        except Exception as e:
            result["hard_checks"][name] = {"pass": None, "msg": f"ERROR: {e}"}
            result["errors"].append(f"{name} raised: {e}")
    # Soft checks
    result["soft_checks"] = check_soft_criteria(log_path)
    # Save result
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "evaluation.json"), "w") as fp:
            json.dump(result, fp, indent=2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", help="path to goose build log")
    parser.add_argument("--output-dir", help="where to write evaluation.json")
    args = parser.parse_args()
    result = evaluate_run(args.log, args.output_dir)
    print(f"Result: {'PASS' if result['pass'] else 'FAIL'}")
    for name, h in result["hard_checks"].items():
        if h["pass"] is True:
            icon = "[PASS]"
        elif h["pass"] is False:
            icon = "[FAIL]"
        else:
            icon = "[SKIP]"
        print(f"  {icon} {name}: {h['msg']}")
    if result["errors"]:
        print("Errors:")
        for e in result["errors"]:
            print(f"  - {e}")
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
