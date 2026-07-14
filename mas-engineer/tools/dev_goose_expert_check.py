#!/usr/bin/env python3
"""
dev_goose_expert_check.py — Codifies L01 from lessons-learned.md

Purpose: Scan findings/patches for "missing mechanism" claims and verify
against Goose's known native capabilities. Catches the class of bug
where im-designer proposes reimplementing something Goose already provides.

Part of R11 GOOSE-EXPERT CONSULTATION (see master-constitution.yaml).

Usage:
    python3 dev_goose_expert_check.py --findings .state/pipeline/findings.yaml
    python3 dev_goose_expert_check.py --patches .state/pipeline/patches.yaml
    python3 dev_goose_expert_check.py --check-mechanism "load on demand for agents"
    python3 dev_goose_expert_check.py --list-known-mechanisms

Exit codes:
    0 = all clear (no Goose-already-provides-this conflicts)
    1 = conflicts found (must summon sub_mas-goose-expert for resolution)
    2 = usage error
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Knowledge base: Goose native mechanisms known as of 2026-07-14.
# Sourced from https://goose-docs.ai/ and verified against actual Goose behavior.
# This is a FALLBACK — the source of truth is sub_mas-goose-expert (see R11).
KNOWN_GOOSE_MECHANISMS = {
    "load on demand for agents": {
        "native": "summon extension (MCP)",
        "docs": "https://goose-docs.ai/docs/mcp/summon-mcp/",
        "alternative_keywords": ["lazy load", "on demand", "dynamic load", "load on demand"],
    },
    "load on demand for skills": {
        "native": "summon extension (MCP)",
        "docs": "https://goose-docs.ai/docs/mcp/summon-mcp/",
        "alternative_keywords": ["skill load", "skill on demand"],
    },
    "agent delegation": {
        "native": "summon extension (MCP)",
        "docs": "https://goose-docs.ai/docs/mcp/summon-mcp/",
        "alternative_keywords": ["delegate to agent", "sub-agent call", "spawn subagent"],
    },
    "load context on demand": {
        "native": "summon extension (MCP)",
        "docs": "https://goose-docs.ai/docs/mcp/summon-mcp/",
        "alternative_keywords": ["context load", "knowledge load"],
    },
    "config validation": {
        "native": "goose config validate (CLI)",
        "docs": "https://goose-docs.ai/docs/guides/config-file/",
        "alternative_keywords": ["validate config", "config check"],
    },
    "session management": {
        "native": "goose session (CLI subcommand)",
        "docs": "https://goose-docs.ai/docs/guides/sessions/",
        "alternative_keywords": ["session list", "session cleanup", "session rm"],
    },
    "recipe sharing across agents": {
        "native": "constitution: field (recipe inheritance)",
        "docs": "https://goose-docs.ai/docs/guides/recipe-constitution/",
        "alternative_keywords": ["shared rules", "common constitution"],
    },
    "automatic rollback": {
        "native": "no native mechanism — use git + checkpoint pattern",
        "docs": None,
        "alternative_keywords": ["undo", "revert", "restore"],
    },
    "recipe versioning": {
        "native": "version: field in recipe YAML + git",
        "docs": "https://goose-docs.ai/docs/guides/recipes/",
        "alternative_keywords": [],
    },
    "parallel agent execution": {
        "native": "goose run --parallel (limited) + delegate_task pattern",
        "docs": "https://goose-docs.ai/docs/guides/parallel-execution/",
        "alternative_keywords": ["concurrent agents", "multi-agent run"],
    },
}


def find_conflict(text: str) -> dict | None:
    """Check if the given text claims a 'missing mechanism' that Goose provides."""
    text_lower = text.lower()
    for mechanism, info in KNOWN_GOOSE_MECHANISMS.items():
        all_keywords = [mechanism] + info["alternative_keywords"]
        for kw in all_keywords:
            if kw in text_lower:
                # Check if the text implies the mechanism is MISSING
                missing_patterns = [
                    r"missing\s+" + re.escape(kw),
                    r"no\s+" + re.escape(kw),
                    r"add\s+" + re.escape(kw),
                    r"implement\s+" + re.escape(kw),
                    r"need\s+" + re.escape(kw),
                    r"requires?\s+" + re.escape(kw),
                ]
                for pat in missing_patterns:
                    if re.search(pat, text_lower):
                        return {
                            "claimed_missing": kw,
                            "goose_native": info["native"],
                            "docs": info["docs"],
                            "advice": f"Goose already provides '{info['native']}' for this. Use it instead of reimplementing.",
                        }
    return None


def scan_findings(findings_path: Path) -> tuple[int, list[dict]]:
    """Scan a findings.yaml file for Goose-already-provides-this conflicts."""
    if not findings_path.exists():
        print(f"WARN: {findings_path} does not exist, skipping")
        return 0, []

    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. pip install pyyaml", file=sys.stderr)
        return 2, []

    with open(findings_path) as f:
        data = yaml.safe_load(f)

    findings = data.get("data", {}).get("findings", [])
    conflicts = []
    for finding in findings:
        text = f"{finding.get('issue', '')} {finding.get('detail', '')} {finding.get('fix', '')}"
        conflict = find_conflict(text)
        if conflict:
            conflicts.append({
                "finding_id": finding.get("id"),
                "type": finding.get("type"),
                "file": finding.get("file"),
                **conflict,
            })
    return (1 if conflicts else 0), conflicts


def scan_patches(patches_path: Path) -> tuple[int, list[dict]]:
    """Scan a patches.yaml file for Goose-already-provides-this conflicts."""
    if not patches_path.exists():
        print(f"WARN: {patches_path} does not exist, skipping")
        return 0, []

    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. pip install pyyaml", file=sys.stderr)
        return 2, []

    with open(patches_path) as f:
        data = yaml.safe_load(f)

    patches = data.get("data", {}).get("patches", [])
    conflicts = []
    for patch in patches:
        text = f"{patch.get('reason', '')} {patch.get('to', '')}"
        conflict = find_conflict(text)
        if conflict:
            conflicts.append({
                "patch_file": patch.get("file"),
                "patch_field": patch.get("field"),
                **conflict,
            })
    return (1 if conflicts else 0), conflicts


def check_single_mechanism(claim: str) -> tuple[int, dict | None]:
    """Check a single claim string."""
    conflict = find_conflict(claim)
    if conflict:
        return 1, {"claim": claim, **conflict}
    return 0, {"claim": claim, "verdict": "CONFORM — no known Goose-native conflict"}


def list_known_mechanisms() -> None:
    """Print all known Goose native mechanisms."""
    print("Known Goose native mechanisms (last updated 2026-07-14):\n")
    for mechanism, info in KNOWN_GOOSE_MECHANISMS.items():
        print(f"  {mechanism}")
        print(f"    native: {info['native']}")
        if info["docs"]:
            print(f"    docs:   {info['docs']}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Codifies L01 — check findings/patches for Goose-already-provides-this conflicts"
    )
    parser.add_argument("--findings", type=Path, help="Path to findings.yaml to scan")
    parser.add_argument("--patches", type=Path, help="Path to patches.yaml to scan")
    parser.add_argument("--check-mechanism", type=str, help="Check a single mechanism claim")
    parser.add_argument(
        "--list-known-mechanisms",
        action="store_true",
        help="List all known Goose native mechanisms",
    )
    args = parser.parse_args()

    if args.list_known_mechanisms:
        list_known_mechanisms()
        return 0

    if args.check_mechanism:
        exit_code, result = check_single_mechanism(args.check_mechanism)
        print(json.dumps(result, indent=2))
        return exit_code

    if args.findings:
        exit_code, conflicts = scan_findings(args.findings)
        if conflicts:
            print(f"FOUND {len(conflicts)} Goose-already-provides-this conflicts in {args.findings}:")
            for c in conflicts:
                print(json.dumps(c, indent=2))
                print()
            print("ACTION: SUMMON sub_mas-goose-expert for each conflict (R11).")
        else:
            print(f"OK — no Goose-already-provides-this conflicts in {args.findings}")
        return exit_code

    if args.patches:
        exit_code, conflicts = scan_patches(args.patches)
        if conflicts:
            print(f"FOUND {len(conflicts)} Goose-already-provides-this conflicts in {args.patches}:")
            for c in conflicts:
                print(json.dumps(c, indent=2))
                print()
            print("ACTION: SUMMON sub_mas-goose-expert for each conflict (R11).")
        else:
            print(f"OK — no Goose-already-provides-this conflicts in {args.patches}")
        return exit_code

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
