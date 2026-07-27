"""
test_sub_mas_degradation_director.py — sanity tests for degradation-director.

Degradation-director orchestrates degradation handling. Delegates to
analyzer (analysis/diagnose) and reporter (report/document). The
planner is a downstream single-role agent (treatment planning),
NOT a director's sub_recipe.

Run with:
    python3 -m pytest tests/test_sub_mas_degradation_director.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-degradation-director.yaml"


def test_degradation_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_degradation_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_degradation_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_degradation_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_degradation_director_orchestrator():
    """Spec: orchestrator — delegates to specialized sub-agents."""
    content = RECIPE.read_text()
    assert "Orchestrator" in content or "orchestrate" in content.lower(), \
        "degradation-director must be an orchestrator"
    assert "Delegate" in content or "delegate" in content, \
        "degradation-director must delegate to sub-agents"


def test_degradation_director_delegation_map():
    """Spec: analyze/diagnose → analyzer, report/document → reporter."""
    content = RECIPE.read_text()
    assert "sub_mas-degradation-analyzer" in content, \
        "degradation-director must delegate to analyzer"
    assert "sub_mas-degradation-reporter" in content, \
        "degradation-director must delegate to reporter"


def test_degradation_director_prohibitions():
    """Spec: NEVER analyze directly, NEVER generate reports directly."""
    content = RECIPE.read_text()
    assert "NEVER analyze" in content, \
        "degradation-director must forbid direct analysis"
    assert "NEVER generate" in content, \
        "degradation-director must forbid direct report generation"


def test_degradation_director_sub_recipes():
    """Director must have sub_recipes for analyzer + reporter."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-degradation-analyzer" in subs, \
        f"degradation-director sub_recipes must include analyzer. subs: {subs}"
    assert "sub_mas-degradation-reporter" in subs, \
        f"degradation-director sub_recipes must include reporter. subs: {subs}"


def test_degradation_director_uses_deepseek():
    """R36+: cost-control via deepseek."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    model = data.get("settings", {}).get("goose_model", "")
    assert "deepseek" in model, \
        f"degradation-director should use deepseek (R36+), got: {model}"


def test_degradation_director_prohibitions_section():
    """Spec: must declare PROHIBITIONS section."""
    content = RECIPE.read_text()
    assert "PROHIBITIONS" in content or "PROHIBITION" in content, \
        "degradation-director must declare PROHIBITIONS section"
