#!/usr/bin/env python3
"""
dev_architecture_checker.py — Checks whether a change affects the MAS architecture (R15).
Will be called FROM dev_rule_checker.py at --check-architecture.

Architecture changes (require user approval):
  1. New agent/tool create (CREATE)
  2. SOT-rules change (R01-R18)
  3. Constitution change (Articles 1-11)
  4. workflows.yaml structure change (new task_workflows section)
  5. master-constitution.yaml change
  6. dev-mas-engineer.yaml sub_recipes-list change
"""

import sys, os, re, json, yaml

# Files that count as "architecture"
ARCHITEKTUR_DATEIEN = [
    ".state/workflows.yaml",
    ".state/domains/registry.yaml",
    "recipe/dev-mas-engineer.yaml",
    "recipe/sub/sub_mas-master-constitution.yaml",
    "recipe/template/agent_template.yaml",
]

# Allowed changes (NOT architecture)
ALLOWED_PATTERNS = [
    r"recipe/sub/sub_mas-\w+\.yaml$",  # Sub-agent edit (not CREATE)
    r"tools/dev_\w+\.py$",              # Tool edit (not CREATE)
    r"\.state/knowledge/.*\.md",        # Knowledge files
    r"\.state/changes\.json",           # Changes log
    r"docs/.*\.md",                     # Documentation
    r"user_info/.*",                    # User info
    r"\.backups/.*",                    # Backups
    r"\.state/checkpoints/.*",         # Checkpoints
]

def ist_architektur_change(action, file=""):
    """Checks whether an action is an architecture change."""
    akt = action.lower()
    d = file.lower() if file else akt

    # 1. NEW file create (CREATE)
    if any(x in akt for x in ["create", "new", "new agent", "new tool", "clone"]):
        # Check whether it is a sub-agent or tool (then architecture)
        if any(x in d for x in ["sub_mas-", "dev_"]):
            return True, "New agent/tool create — architecture change"
        # Check whether it is only a regular file
        if ".md" in d or "changes.json" in d or ".bak" in d:
            return False, ""
        return True, "New file of unknown type — architecture check"

    # 2. SOT-rules change
    if "workflows.yaml" in d:
        if any(x in akt for x in ["edit", "write", "add", "remove", "delete"]):
            return True, "workflows.yaml change — SOT architecture"

    # 3. Constitution change
    if "master-constitution.yaml" in d:
        if any(x in akt for x in ["edit", "write"]):
            return True, "master-constitution.yaml change — constitution"

    # 4. ARCHITEKTUR_DATEIEN (specially protected)
    for ad in ARCHITEKTUR_DATEIEN:
        if ad in d:
            if any(x in akt for x in ["edit", "write", "delete", "add"]):
                return True, f"{ad} change — protected architecture file"

    # 5. Allowed changes (NOT architecture)
    for pat in ALLOWED_PATTERNS:
        if re.search(pat, d):
            return False, ""

    # 6. sub_recipes-list in dev-mas-engineer.yaml
    if "dev-mas-engineer.yaml" in d and any(x in akt for x in ["sub_recipes", "add sub", "remove sub"]):
        return True, "sub_recipes-list change — agent architecture"

    return False, ""


def check_architecture(action, file=""):
    """Main check: returns result as dict."""
    ist_arch, grund = ist_architektur_change(action, file)

    if ist_arch:
        return {
            "architektur_change": True,
            "grund": grund,
            "action": "ABSEGNEN",
            "detail": f"Architecture change detected: {grund}. User must approve."
        }
    else:
        return {
            "architektur_change": False,
            "grund": "",
            "action": "OK",
            "detail": "No architecture change"
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Architecture check (R15)")
    parser.add_argument("--action", default="", help="Planned action")
    parser.add_argument("--file", default="", help="Affected file")
    args = parser.parse_args()

    result = check_architecture(args.action, args.file)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["architektur_change"]:
        sys.exit(1)
    else:
        sys.exit(0)
