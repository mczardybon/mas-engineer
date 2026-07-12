#!/usr/bin/env python3
"""
dev_architecture_checker.py — Checks ob eine Change die MAS-Architektur betrifft (R15).
Will von dev_rule_checker.py bei --check-architecture aufgerufen.

Architektur-Changes (must User absegnen):
  1. Neuen Agent/Tool create (CREATE)
  2. SOT-Rulen change (R01-R18)
  3. Constitution change (Artikel 1-11)
  4. workflows.yaml Struktur change (new task_workflows-Sektion)
  5. master-constitution.yaml change
  6. dev-mas-engineer.yaml sub_recipes-list change
"""

import sys, os, re, json, yaml

# files die als "Architektur" gelten
ARCHITEKTUR_DATEIEN = [
    ".state/workflows.yaml",
    ".state/domains/registry.yaml",
    "recipe/dev-mas-engineer.yaml",
    "recipe/sub/sub_mas-master-constitution.yaml",
    "recipe/template/agent_template.yaml",
]

# Allowed Changes (NOE Architektur)
ERLAUBTE_PATTERNS = [
    r"recipe/sub/sub_mas-\w+\.yaml$",  # Sub-Agent-Edit (not CREATE)
    r"tools/dev_\w+\.py$",              # Tool-Edit (not CREATE)
    r"\.state/knowledge/.*\.md",        # Wissen-files
    r"\.state/changes\.json",           # Changes-Log
    r"docs/.*\.md",                     # Documentation
    r"user_info/.*",                    # User-Info
    r"\.backups/.*",                    # Backups
    r"\.state/checkpoints/.*",         # Checkpoints
]

def ist_architektur_change(action, file=""):
    """Checks ob eine action eine Architektur-Change ist."""
    akt = action.lower()
    d = file.lower() if file else akt
    
    # 1. NEUE file create (CREATE)
    if any(x in akt for x in ["create", "new", "new agent", "new tool", "clone"]):
        # Check ob es a Sub-Agent oder Tool ist (then Architektur)
        if any(x in d for x in ["sub_mas-", "dev_"]):
            return True, "Neuen Agent/Tool create — Architektur-Change"
        # Check ob es only eine normale file ist
        if ".md" in d or "changes.json" in d or ".bak" in d:
            return False, ""
        return True, "New file unbekannten typees — Architektur check"
    
    # 2. SOT-Rulen change
    if "workflows.yaml" in d:
        if any(x in akt for x in ["edit", "write", "add", "remove", "delete"]):
            return True, "workflows.yaml change — SOT-Architektur"
    
    # 3. Constitution change
    if "master-constitution.yaml" in d:
        if any(x in akt for x in ["edit", "write"]):
            return True, "master-constitution.yaml change — Constitution"
    
    # 4. ARCHITEKTUR_DATEIEN (speziell protected)
    for ad in ARCHITEKTUR_DATEIEN:
        if ad in d:
            if any(x in akt for x in ["edit", "write", "delete", "add"]):
                return True, f"{ad} change — protected Architektur-file"
    
    # 5. Allowed Changes (NOE Architektur)
    for pat in ERLAUBTE_PATTERNS:
        if re.search(pat, d):
            return False, ""
    
    # 6. sub_recipes-list in dev-mas-engineer.yaml
    if "dev-mas-engineer.yaml" in d and any(x in akt for x in ["sub_recipes", "add sub", "remove sub"]):
        return True, "sub_recipes-list change — Agenten-Architektur"
    
    return False, ""

def check_architecture(action, file=""):
    """Main check: Returns result as dict."""
    ist_arch, grund = ist_architektur_change(action, file)
    
    if ist_arch:
        return {
            "architektur_change": True,
            "grund": grund,
            "action": "ABSEGNEN",
            "detail": f"Architektur-Change erkannt: {grund}. User must zustimmen."
        }
    else:
        return {
            "architektur_change": False,
            "grund": "",
            "action": "OK",
            "detail": "No Architektur-Change"
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.argumentParser(description="Architektur-Check (R15)")
    parser.add_argument("--action", default="", help="Geplante action")
    parser.add_argument("--file", default="", help="Betroffene file")
    args = parser.parse_args()
    
    result = check_architecture(args.action, args.file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result["architektur_change"]:
        sys.exit(1)
    else:
        sys.exit(0)
