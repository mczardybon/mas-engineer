"""
test_sub_mas_framework_audit_agent.py — sanity tests for framework-audit-agent.

framework-audit-agent v1.0.0 audits framework structure and
architecture. ONLY auditing — NO scanning, NO hardening.
Single-role leaf.

Run with:
    python3 -m pytest tests/test_sub_mas_framework_audit_agent.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-audit-agent.yaml"


def test_framework_audit_agent_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_audit_agent_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_audit_agent_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_audit_agent_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_audit_agent_only_auditing():
    """Spec: ONLY framework auditing — NO scanning or hardening.
    Note: combined-list pattern "NO scanning or hardening".
    """
    content = RECIPE.read_text()
    assert "ONLY framework auditing" in content, \
        "framework-audit-agent must declare ONLY-auditing rule"
    assert "NO scanning" in content, \
        "framework-audit-agent must forbid scanning"
    assert "hardening" in content, \
        "framework-audit-agent must forbid hardening (combined-list)"


def test_framework_audit_agent_audit_role():
    """Spec: audits framework structure and architecture."""
    content = RECIPE.read_text()
    assert "framework" in content.lower(), \
        "framework-audit-agent must declare framework role"
    assert "audit" in content.lower() or "Audit" in content, \
        "framework-audit-agent must declare audit role"


def test_framework_audit_agent_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "framework-audit-agent must be single-role leaf"


def test_framework_audit_agent_settings():
    """Spec: standard settings (timeout=600, max_turns=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "framework-audit-agent must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "framework-audit-agent must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "framework-audit-agent must use deepseek model"


def test_framework_audit_agent_r01_r09_r10():
    """Spec: R01, R09, R10 (R04/R05 not in this recipe)."""
    content = RECIPE.read_text()
    assert "R01" in content, "framework-audit-agent must declare R01"
    assert "R09" in content, "framework-audit-agent must declare R09"
    assert "R10" in content, "framework-audit-agent must declare R10"
    assert "CORONASHIELD" in content, \
        "framework-audit-agent must declare CORONASHIELD"


def test_framework_audit_agent_architecture_and_structure():
    """Spec: audits framework structure and architecture.
    Per R101 EVIDENCE: this recipe focuses on architecture+structure
    analysis (not R04/R05 which are not declared).
    """
    content = RECIPE.read_text()
    assert "architecture" in content.lower(), \
        "framework-audit-agent must declare architecture focus"
    assert "structure" in content.lower(), \
        "framework-audit-agent must declare structure focus"
    assert "analysis" in content.lower(), \
        "framework-audit-agent must return analysis"
