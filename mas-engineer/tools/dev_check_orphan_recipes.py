#!/usr/bin/env python3
"""dev_check_orphan_recipes.py — R110-204: block orphan-recipe commits.

DETECTION -> CORRECTION -> PREVENTION cycle (R110-195 / R110-203 / R110-204):

  R110-195 (DETECTION)    added recipe/sub/sub_mas-design-patches.yaml but
                          never registered it in workflows.yaml
                          configs.mas-self.sub_agents -> the recipe was an
                          orphan, undispatchable from any workflow.
  R110-203 (CORRECTION)   fixed the registry manually (1 line), Check 17
                          caught it after the fact.
  R110-204 (PREVENTION)   THIS tool + pre-push Check 23: any commit that
                          adds a DOMAIN 1 recipe without registering it is
                          BLOCKED at push time, before the orphan lands.

The script is the SOURCE OF TRUTH for what "registered" means — both
tests/test_dev_check_orphan_recipes.py and pre-push-validator Check 23
call it (R110-31 hard rule: "All DOMAIN 1 sub-agents MUST be registered
in configs.mas-self.sub_agents").

Algorithm (mirrors test_recipe_registry_consistency.py):
  - glob recipe/sub/*.yaml (skip ORIGINAL_*)
  - classify each file's DOMAIN (mas-self / mas-generated / demo-team /
    unknown) using the R110-39 stem + description heuristics
  - load .mase/workflows.yaml configs.mas-self.sub_agents (dict-of-lists)
    and flatten all values to a set of registered names
  - orphans = DOMAIN 1 (mas-self) recipe stems - registered names
  - orphans -> print table + exit 1; else "OK" + exit 0

CLI:
    python3 tools/dev_check_orphan_recipes.py [--json] [--repo-root PATH]
    exit 0 = clean, 1 = orphan(s) found, 2 = config/parse error
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required (pip install pyyaml)\n")
    sys.exit(2)

TYPE_MIN_LEN = 2  # unused here; kept for parity with sibling scanners

# R110-43 / R110-30 domain classification tokens (mirror
# tests/test_recipe_registry_consistency.py exactly).
DOMAIN1_PREFIXES = (
    "sub_mas-monitor-",            # CONTROLLER-internal
    "sub_mas-im-",                 # IM-pipeline sub-agents
    "sub_mas-test-fix-failures-",  # test-fix-failures director chain
)
DOMAIN1_DESC = (
    "MAS-internal",
    "MAS-Engineer-internal",
    "CONTROLLER-internal",
    "Code-Review-Team",
)
DOMAIN2_TOKENS = (
    "sub_mas-team-packager",
    "sub_mas-generic-init",
)
DOMAIN3_TOKENS = (
    "social-media-manager",
    "email-campaign-manager",
    "seo-researcher",
    "content-writer",
    "analytics-reporter",
)
MARKETING_KEYWORDS = (
    "marketing", "social media", "campaign", "seo", "blog",
)


def classify_domain(stem: str, data: dict) -> str:
    """Return 'mas-self', 'mas-generated', 'demo-team' or 'unknown'.

    Heuristic mirror of tests/test_recipe_registry_consistency.py
    classify_domain() for recipe/sub/*.yaml (path-based decisions are
    not needed: this tool only scans recipe/sub/ directly).
    """
    desc = (data.get("description") or "")
    if any(stem.startswith(t) for t in DOMAIN2_TOKENS):
        return "mas-generated"
    if any(t in stem for t in DOMAIN3_TOKENS):
        return "demo-team"
    if any(sig in desc for sig in DOMAIN1_DESC):
        return "mas-self"
    if any(stem.startswith(p) for p in DOMAIN1_PREFIXES):
        return "mas-self"
    if re.match(r"v\d+\.\d+\.\d+\s*\|", desc) and not any(
        kw in desc.lower() for kw in MARKETING_KEYWORDS
    ):
        return "mas-self"
    return "unknown"


def load_registered(repo_root: Path):
    """Return the set of registered sub-agent names from workflows.yaml.

    None if workflows.yaml is missing or has no configs.mas-self.sub_agents.
    """
    wf = repo_root / ".mase" / "workflows.yaml"
    if not wf.exists():
        return None
    try:
        data = yaml.safe_load(wf.read_text(errors="ignore"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    sub = ((data.get("configs") or {}).get("mas-self") or {}).get(
        "sub_agents") or {}
    registered = set()
    if isinstance(sub, dict):
        for v in sub.values():
            if isinstance(v, list):
                registered.update(x for x in v if isinstance(x, str))
    return registered


def scan_recipe_sub(repo_root: Path):
    """Yield (stem, domain) for each recipe/sub/*.yaml (skip ORIGINAL_*)."""
    sub_dir = repo_root / "recipe" / "sub"
    if not sub_dir.is_dir():
        return
    for f in sorted(sub_dir.glob("*.yaml")):
        if f.name.startswith("ORIGINAL_"):
            continue
        try:
            data = yaml.safe_load(f.read_text(errors="ignore"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        yield f.stem, classify_domain(f.stem, data)


def find_orphans(repo_root: Path):
    """Return (orphans, mas_self_total, registered).

    orphans: list of {"name": stem, "recipe_file": str}
    registered: set of registered names (or None when registry missing)
    """
    registered = load_registered(repo_root)
    mas_self = []
    for stem, domain in scan_recipe_sub(repo_root):
        if domain == "mas-self":
            mas_self.append(stem)
    orphans = []
    if registered is not None:
        for stem in mas_self:
            if stem not in registered:
                orphans.append({
                    "name": stem,
                    "recipe_file": f"recipe/sub/{stem}.yaml",
                })
    return orphans, len(mas_self), registered


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="R110-204: detect DOMAIN 1 recipes not registered in "
                    "workflows.yaml configs.mas-self.sub_agents")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable output for CI")
    ap.add_argument("--repo-root", type=Path, default=Path("."),
                    help="repository root (default: .)")
    args = ap.parse_args(argv)

    repo_root = args.repo_root
    orphans, mas_self_total, registered = find_orphans(repo_root)

    if registered is None:
        if args.json:
            print(json.dumps({
                "ok": False, "error": "registry missing/unreadable",
                "orphans": [], "total": mas_self_total,
            }))
        else:
            print("ERROR: workflows.yaml configs.mas-self.sub_agents "
                  "missing/unreadable — cannot validate registration")
        return 2

    ok = not orphans
    if args.json:
        print(json.dumps({
            "ok": ok,
            "orphans": orphans,
            "total_mas_self": mas_self_total,
            "registered": len(registered),
        }, indent=2))
    else:
        if orphans:
            print(f"ORPHAN: {len(orphans)}/{mas_self_total} DOMAIN 1 "
                  f"(mas-self) recipes NOT registered in "
                  f"workflows.yaml configs.mas-self.sub_agents "
                  f"(R110-31 violation — undispatchable from workflow):")
            for o in orphans:
                print(f"  ❌ {o['name']:<50} {o['recipe_file']}")
            print("Fix: add the recipe to configs.mas-self.sub_agents in "
                  ".mase/workflows.yaml (design the right category, then "
                  "re-run this tool).")
        else:
            print(f"OK: {mas_self_total}/{mas_self_total} DOMAIN 1 (mas-self) "
                  f"recipes registered "
                  f"({len(registered)} total in registry)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
