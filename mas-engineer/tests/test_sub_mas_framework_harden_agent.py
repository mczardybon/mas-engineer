"""
test_sub_mas_framework_harden_agent.py — sanity tests for framework-harden-agent.

framework-harden-agent v1.0.0 checks framework hardening and
security. ONLY hardening checks — NO scanning or auditing.
Single-role leaf.

Per R101 EVIDENCE: framework-harden-agent has R01+R09+R10 (not
R04/R05 like I initially assumed).

Run with:
    python3 -m pytest tests/test_sub_mas_framework_harden_agent.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-harden-agent.yaml"


def test_framework_harden_agent_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_harden_agent_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_harden_agent_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_harden_agent_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_harden_agent_only_hardening():
    """Spec: ONLY framework hardening checks — NO scanning or auditing.
    Note: combined-list pattern "NO scanning or auditing".
    """
    content = RECIPE.read_text()
    assert "ONLY framework hardening" in content, \
        "framework-harden-agent must declare ONLY-hardening rule"
    assert "NO scanning" in content, \
        "framework-harden-agent must forbid scanning (combined-list)"
    assert "auditing" in content, \
        "framework-harden-agent must forbid auditing (combined-list)"


def test_framework_harden_agent_security_role():
    """Spec: checks framework hardening and security."""
    content = RECIPE.read_text()
    assert "hardening" in content.lower() or "Hardening" in content, \
        "framework-harden-agent must declare hardening role"
    assert "security" in content.lower(), \
        "framework-harden-agent must declare security check"
    assert "check" in content.lower() or "Check" in content, \
        "framework-harden-agent must declare check verb"


def test_framework_harden_agent_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "framework-harden-agent must be single-role leaf"


def test_framework_harden_agent_settings():
    """Spec: standard settings (timeout=600, max_turns=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "framework-harden-agent must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "framework-harden-agent must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "framework-harden-agent must use deepseek model"


def test_framework_harden_agent_r01_r09_r10():
    """Spec: R01, R09, R10 (per R101 EVIDENCE — not R04/R05)."""
    content = RECIPE.read_text()
    assert "R01" in content, "framework-harden-agent must declare R01"
    assert "R09" in content, "framework-harden-agent must declare R09"
    assert "R10" in content, "framework-harden-agent must declare R10"
    assert "CORONASHIELD" in content, \
        "framework-harden-agent must declare CORONASHIELD"


def test_framework_harden_agent_returns_results():
    """Spec: returns hardening check results (not validation report).
    Per R101 EVIDENCE: prompt says "Check framework hardening and
    return results" (vs framework-auditor which returns
    validation report).
    """
    content = RECIPE.read_text()
    assert "return results" in content, \
        "framework-harden-agent must return results (not validation report)"
