"""
test_sub_mas_bootstrap.py — sanity tests for MAS Bootstrap.

MAS Bootstrap v1.0.0 creates standalone MAS-Engineer distribution
with all sub-agents + tools (Python + Shell + YAML). For deployment,
not framework development.

Per R101 EVIDENCE: has R10 (CORONASHIELD) — bootstrap creates
distribution, must ensure valid YAML.

Run with:
    python3 -m pytest tests/test_sub_mas_bootstrap.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-bootstrap.yaml"


def test_bootstrap_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_bootstrap_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_bootstrap_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_bootstrap_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_bootstrap_role():
    """Spec: Creates standalone MAS-Engineer distribution."""
    content = RECIPE.read_text()
    assert "distribution" in content.lower(), \
        "bootstrap must declare distribution role"
    assert "deployment" in content.lower(), \
        "bootstrap must declare deployment scope"
    assert "sub-agents" in content.lower() or "sub_agents" in content.lower(), \
        "bootstrap must reference sub-agents"


def test_bootstrap_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "bootstrap must be single-role leaf"


def test_bootstrap_settings():
    """Spec: orchestrator settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "bootstrap must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "bootstrap must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "bootstrap must use deepseek model"


def test_bootstrap_r10_coronashield():
    """Spec: R10 CORONASHIELD — bootstrap must ensure valid YAML."""
    content = RECIPE.read_text()
    assert "R10" in content, "bootstrap must declare R10"
    assert "Coronashield" in content or "CORONASHIELD" in content, \
        "bootstrap must reference Coronashield/CORONASHIELD"


def test_bootstrap_python_shell_yaml():
    """Spec: bootstrap includes Python + Shell + YAML tools."""
    content = RECIPE.read_text()
    assert "Python" in content, \
        "bootstrap must reference Python tools"
    assert "Shell" in content, \
        "bootstrap must reference Shell tools"
    assert "YAML" in content, \
        "bootstrap must reference YAML tools"


def test_bootstrap_distributes_96_subagents():
    """Spec: bootstrap distributes 96 sub-agents (snapshot count)."""
    content = RECIPE.read_text()
    assert "96 sub-agents" in content, \
        "bootstrap must declare 96 sub-agents distribution"
