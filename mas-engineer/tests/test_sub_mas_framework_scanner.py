"""
test_sub_mas_framework_scanner.py — sanity tests for framework-scanner.

R110-137 (2026-08-06): The legacy `sub_mas-framework-scanner.yaml` was
removed because it was a byte-identical duplicate of
`sub_mas-framework-scanner-director.yaml` (R106 EVIDENCE, 1749==1749
bytes, MD5 bf425946). Keeping both created a 2-node dispatch cycle
(scanner-director -> scan-agent -> scanner). Tests now point to the
canonical scanner-director file.

Note: framework-scanner-director.yaml is the orchestrator that
delegates to 3 framework sub-agents: scan-agent, audit-agent, harden-agent.

Run with:
    python3 -m pytest tests/test_sub_mas_framework_scanner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-scanner-director.yaml"


def test_framework_scanner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_scanner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_scanner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_scanner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_scanner_orchestrator():
    """Spec: orchestrator — delegates to specialized sub-agents."""
    content = RECIPE.read_text()
    assert "Orchestrat" in content or "orchestrate" in content.lower(), \
        "framework-scanner must be an orchestrator"
    assert "Delegate" in content, \
        "framework-scanner must delegate to sub-agents"


def test_framework_scanner_only_orchestration():
    """Spec: ONLY orchestration — NO direct framework analysis."""
    content = RECIPE.read_text()
    assert "ONLY orchestration" in content, \
        "framework-scanner must declare ONLY-orchestration rule"
    assert "NO direct framework analysis" in content, \
        "framework-scanner must forbid direct framework analysis"


def test_framework_scanner_3_sub_agents():
    """Spec: 3 sub-agents — scan-agent, audit-agent, harden-agent."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-framework-scan-agent",
                "sub_mas-framework-audit-agent",
                "sub_mas-framework-harden-agent"):
        assert sub in content, \
            f"framework-scanner must delegate to: {sub}"


def test_framework_scanner_sub_recipes():
    """Orchestrator must have sub_recipes for the 3 agents."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-framework-scan-agent" in subs, \
        f"framework-scanner sub_recipes must include scan-agent. subs: {subs}"
    assert "sub_mas-framework-audit-agent" in subs, \
        f"framework-scanner sub_recipes must include audit-agent. subs: {subs}"
    assert "sub_mas-framework-harden-agent" in subs, \
        f"framework-scanner sub_recipes must include harden-agent. subs: {subs}"


def test_framework_scanner_delegation_map():
    """Spec: delegation map by task domain."""
    content = RECIPE.read_text()
    for task in ("scan/overview", "audit/analyze", "harden/check"):
        assert task in content, \
            f"framework-scanner must declare delegation for: {task}"


def test_framework_scanner_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "framework-scanner must declare R01"
    assert "R09" in content, "framework-scanner must declare R09"
    assert "R10" in content, "framework-scanner must declare R10"
    assert "CORONASHIELD" in content, \
        "framework-scanner must declare CORONASHIELD"
