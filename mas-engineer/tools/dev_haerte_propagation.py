#!/usr/am/env python3
"""
dev_haerte_propagation.py — Methode 6: Hardening propagation in Sub-Agenten
Will bei JEDEM delegate()-Aufruf executed.
Adds hard rules into the sub-agent intake.

Usage:
    python3 dev_haerte_propagation.py [--workspace /path] <agent_name>
"""

import sys
import os
import argparse
import yaml

def get_hard_rules(workspace, min_hardness=4):
    """Load rules above certain hardness level"""
    rules_file = os.path.join(workspace, "mas-engineer/.state/rules/hard_rules.yaml")
    with open(rules_file) as f:
        data = yaml.safe_load(f)
    
    levels = data.get("hardness_levels", {})
    rules = data.get("rules", [])
    
    result = []
    for r in rules:
        if r["hardness"] >= min_hardness:
            h_name = "extreme" if r["hardness"] >= 5 else "strong"
            level = levels.get(h_name, {})
            symbol = level.get("symbol", "")
            hardness_icon = "⛔⛔⛔⛔⛔" if r["hardness"] >= 5 else "⛔⛔⛔"
            result.append({
                "id": r["id"],
                "text": f"{hardness_icon} {r['prompt_text']}",
                "block": r["block"],
                "hardness": r["hardness"]
            })
    
    return result

def format_for_intake(agent_name, original_intake, workspace):
    """Generate intake string with inherited rules"""
    rules = get_hard_rules(workspace, min_hardness=4)
    
    lines = []
    lines.append("=== ⛔⛔⛔⛔⛔ INHERITED RULES (Hardening: EXTREME + STRONG) ===")
    lines.append(f"Inherited from dev-mas-engineer for Sub-Agent: {agent_name}")
    lines.append("These rules take PRIORITY over all own rules.")
    lines.append("")
    
    for r in rules:
        if r["block"]:
            lines.append(f"⛔⛔⛔⛔⛔ {r['text']}")
        else:
            lines.append(f"  {r['text']}")
    
    lines.append("")
    lines.append("=== END INHERITED RULES ===")
    lines.append("")
    
    return "\n".join(lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hardening propagation in sub-agents")
    parser.add_argument("--workspace", type=str, default=os.getcwd(),
                        help="MAS workspace directory (default: current directory)")
    parser.add_argument("agent_name", type=str, nargs="?", default="sub_mas-unknown",
                        help="Name of the sub-agent")
    args = parser.parse_args()
    
    intake_block = format_for_intake(args.agent_name, {}, args.workspace)
    print(intake_block)