"""
test_sub_mas_test_agent.py — sanity tests for test-agent.

test-agent v1.0.0 is the test agent (MAS-internal): executes
tests and verifies results. Single-role leaf. R01+R09+R10.

Run with:
    python3 -m pytest tests/test_sub_mas_test_agent.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-agent.yaml"


def test_agent_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_agent_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_agent_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_agent_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_agent_role():
    """Spec: Executes tests and verifies results."""
    content = RECIPE.read_text()
    assert "Executes tests" in content, \
        "test-agent must declare execution role"
    assert "verifies results" in content or "verify" in content.lower(), \
        "test-agent must declare verification role"
    assert "MAS-internal" in content, \
        "test-agent must declare MAS-internal scope"


def test_agent_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "test-agent must be single-role leaf"


def test_agent_settings():
    """Spec: standard settings (timeout=600, max_turns=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "test-agent must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "test-agent must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "test-agent must use deepseek model"


def test_agent_only_execution():
    """Spec: ONLY executes tests (no other role)."""
    content = RECIPE.read_text()
    assert "ONLY" in content, \
        "test-agent must declare ONLY rule"
    # Check for negative rules (forbid other roles)
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("NO ") >= 1, \
        "test-agent must have at least one NO- rule"


def test_agent_r01_r09_r10():
    """Spec: R01, R09, R10 (per R101 EVIDENCE — full pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "test-agent must declare R01"
    assert "R09" in content, "test-agent must declare R09"
    assert "R10" in content, "test-agent must declare R10"
    assert "CORONASHIELD" in content, \
        "test-agent must declare CORONASHIELD"


def test_agent_differs_from_test_executor():
    """Spec: test-agent has R-rules, test-executor doesn't.
    Per R101 EVIDENCE: this distinguishes test-agent as
    R-rules-aware (vs test-executor's minimal recipe).
    """
    content = RECIPE.read_text()
    assert "R01" in content, \
        "test-agent must have R01 (differs from test-executor)"
    assert "R09" in content, \
        "test-agent must have R09 (differs from test-executor)"
