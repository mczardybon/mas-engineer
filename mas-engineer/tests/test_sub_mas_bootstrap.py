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
    """Spec: orchestrator settings (timeout=600, max_turns=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "bootstrap must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "bootstrap must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "bootstrap must use deepseek model"


def test_bootstrap_r10_coronashield():
    """Spec: R10 CORONASHIELD — bootstrap must ensure valid YAML."""
    content = RECIPE.read_text()
    assert "R10" in content, "bootstrap must declare R10"
    assert "Coronashield" in content or "CORONASHIELD" in content, \
        "bootstrap must reference Coronashield/CORONASHIELD"


def test_bootstrap_python_shell_yaml():
    """Spec: bootstrap must include tools (composition breakdown dropped
    in R110-71: '50 Python + 6 Shell + 1 YAML' was too brittle and changed
    on every tools/ commit). The current spec is just 'N tools' aggregate,
    so this test now only checks the file is reachable and parseable — the
    detailed Python/Shell/YAML breakdown is verified at the file-system
    level in mas-engineer/tests/test_tools_count.py instead."""
    # R110-71 dropped composition breakdown from sub_mas-bootstrap.yaml
    # because it drifted every commit. The aggregate count ('77 tools')
    # is what bootstrap now declares. Detailed tool-type breakdown
    # belongs to test_tools_count.py, not to a recipe-content test.
    content = RECIPE.read_text()
    assert "tools" in content.lower(), \
        "bootstrap must reference tools aggregate"


def test_bootstrap_distributes_110_subagents():
    """Spec: bootstrap distributes 110 sub-agents (R110-71 snapshot).

    R110-71 (commit f6f2f46) corrected the stale '96 sub-agents' count
    to '110 sub-agents', verified at that time via
    `ls recipe/sub/sub_mas-*.yaml | grep -v llm-backup | wc -l`. Recipe
    body now declares 110; this test verifies the spec matches the
    recipe, not the other way around.
    """
    content = RECIPE.read_text()
    assert "110 sub-agents" in content, \
        "bootstrap must declare 110 sub-agents distribution (R110-71)"
