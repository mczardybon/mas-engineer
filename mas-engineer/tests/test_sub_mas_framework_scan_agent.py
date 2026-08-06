"""
test_sub_mas_framework_scan_agent.py — sanity tests for framework-scan-agent.

Note: framework-scan-agent.yaml is the FRAMEWORK-DIRECTOR (different
name in title) — the master orchestrator for framework operations.
Delegates to 4 framework sub-agents: scanner, auditor, finder, hardener.

Run with:
    python3 -m pytest tests/test_sub_mas_framework_scan_agent.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-scan-agent.yaml"


def test_framework_scan_agent_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_scan_agent_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_scan_agent_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_scan_agent_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_scan_agent_orchestrator():
    """Spec: FRAMEWORK-DIRECTOR — orchestrator for framework operations."""
    content = RECIPE.read_text()
    assert "Orchestrat" in content or "orchestrate" in content.lower(), \
        "framework-scan-agent must be an orchestrator"
    assert "Delegate" in content, \
        "framework-scan-agent must delegate to sub-agents"


def test_framework_scan_agent_3_sub_recipes():
    """R110-137 (2026-08-06): The legacy `sub_mas-framework-scanner` was
    removed (byte-identical duplicate of scanner-director per R106 EVIDENCE,
    caused 2-node dispatch cycle). scan-agent now has 3 sub-recipes
    (auditor, finder, hardener). The scanner-director is referenced in
    the delegation map but NOT as a sub-recipe (it's a peer director).
    """
    content = RECIPE.read_text()
    for sub in ("sub_mas-framework-auditor",
                "sub_mas-framework-finder",
                "sub_mas-framework-hardener"):
        assert sub in content, \
            f"framework-scan-agent must delegate to: {sub}"


def test_framework_scan_agent_sub_recipes():
    """Orchestrator must have sub_recipes for the 3 leaf agents (NOT scanner-director)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    for sub in ("sub_mas-framework-auditor",
                "sub_mas-framework-finder",
                "sub_mas-framework-hardener"):
        assert sub in subs, \
            f"framework-scan-agent sub_recipes must include: {sub}. subs: {subs}"
    # R110-137: scanner-director MUST NOT be a sub-recipe of scan-agent
    # (would create 2-node cycle: scanner-director -> scan-agent -> scanner-director)
    assert "sub_mas-framework-scanner-director" not in subs, \
        f"framework-scan-agent sub_recipes must NOT include scanner-director (cycle per R110-137). subs: {subs}"
    # R110-137: legacy scanner MUST NOT be a sub-recipe
    assert "sub_mas-framework-scanner" not in subs, \
        f"framework-scan-agent sub_recipes must NOT include legacy scanner (removed per R110-137). subs: {subs}"


def test_framework_scan_agent_4_prohibitions():
    """Spec: 4 NEVER-X prohibitions (scan, audit, find, harden)."""
    content = RECIPE.read_text()
    for forbid in ("NEVER scan directly", "NEVER audit directly",
                   "NEVER find directly", "NEVER harden directly"):
        assert forbid in content, \
            f"framework-scan-agent must forbid: {forbid}"


def test_framework_scan_agent_delegation_map():
    """Spec: delegation map by task domain."""
    content = RECIPE.read_text()
    for task in ("scan/inventory", "audit/validate",
                 "find/search", "harden/secure"):
        assert task in content, \
            f"framework-scan-agent must declare delegation for: {task}"


def test_framework_scan_agent_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "framework-scan-agent must declare R01"
    assert "R09" in content, "framework-scan-agent must declare R09"
    assert "R10" in content, "framework-scan-agent must declare R10"
    assert "CORONASHIELD" in content, \
        "framework-scan-agent must declare CORONASHIELD"
