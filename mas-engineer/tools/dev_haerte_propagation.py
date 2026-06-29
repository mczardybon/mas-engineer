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

def get_haerte_rulen(workspace, min_haerte=4):
    """Load Rulen ab determineser Hardening level"""
    rulen_file = os.path.join(workspace, "mas-engineer/.state/rules/harte_rulen.yaml")
    with open(rulen_file) as f:
        data = yaml.safe_load(f)
    
    leveln = data.get("haerte_leveln", {})
    rulen = data.get("rulen", [])
    
    result = []
    for r in rulen:
        if r["haerte"] >= min_haerte:
            h_name = "extrem_stark" if r["haerte"] >= 5 else "stark"
            level = leveln.get(h_name, {})
            symbol = level.get("symbol", "")
            haerte_icon = "⛔⛔⛔⛔⛔" if r["haerte"] >= 5 else "⛔⛔⛔"
            result.append({
                "id": r["id"],
                "text": f"{haerte_icon} {r['prompt_text']}",
                "block": r["block"],
                "haerte": r["haerte"]
            })
    
    return result

def format_for_intake(agent_name, original_intake, workspace):
    """Erzeuge den Intake-String mit geerbten Rulen"""
    rulen = get_haerte_rulen(workspace, min_haerte=4)
    
    lines = []
    lines.append("=== ⛔⛔⛔⛔⛔ GEERBTE RULES (Hardening: EXTREM-STARK + STARK) ===")
    lines.append(f"Geerbt von dev-mas-engineer for Sub-Agent: {agent_name}")
    lines.append("Diese Rulen have VORRANG vor alln eigenen Rulen.")
    lines.append("")
    
    for r in rulen:
        if r["block"]:
            lines.append(f"⛔⛔⛔⛔⛔ {r['text']}")
        else:
            lines.append(f"  {r['text']}")
    
    lines.append("")
    lines.append("=== END GEERBTE RULES ===")
    lines.append("")
    
    return "\n".join(lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hardening propagation in Sub-Agenten")
    parser.add_argument("--workspace", type=str, default=os.getcwd(),
                        help="MAS-Workspace-Directory (default: aktuelles Directory)")
    parser.add_argument("agent_name", type=str, nargs="?", default="sub_mas-unknown",
                        help="Name des Sub-Agenten")
    args = parser.parse_args()
    
    intake_block = format_for_intake(args.agent_name, {}, args.workspace)
    print(intake_block)