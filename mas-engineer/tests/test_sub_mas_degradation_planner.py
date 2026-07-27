"""
test_sub_mas_degradation_planner.py — sanity tests for degradation-planner.

Degradation-planner v1.0.0 is a single-role agent. ONLY treatment
planning — NO analysis or report writing. Receives root cause
analysis from degradation-analyzer, returns treatment plan
(restart/reconfigure/rollback/escalate).

Run with:
    python3 -m pytest tests/test_sub_mas_degradation_planner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-degradation-planner.yaml"


def test_degradation_planner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_degradation_planner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_degradation_planner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_degradation_planner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_degradation_planner_single_role():
    """Spec: single role — design treatment plans."""
    content = RECIPE.read_text()
    assert "Single role" in content or "single-role" in content, \
        "degradation-planner must declare single role"


def test_degradation_planner_only_planning():
    """Spec: ONLY treatment planning — NO analysis or report writing."""
    content = RECIPE.read_text()
    assert "ONLY treatment planning" in content, \
        "degradation-planner must declare ONLY-planning rule"


def test_degradation_planner_forbids_analysis():
    """Spec: NEVER analyze degradation — delegate to analyzer."""
    content = RECIPE.read_text()
    assert "NEVER analyze" in content, \
        "degradation-planner must forbid degradation analysis"
    assert "degradation-analyzer" in content, \
        "degradation-planner must reference degradation-analyzer"


def test_degradation_planner_forbids_reports():
    """Spec: NEVER generate reports — delegate to reporter."""
    content = RECIPE.read_text()
    assert "NEVER generate reports" in content, \
        "degradation-planner must forbid report generation"
    assert "degradation-reporter" in content, \
        "degradation-planner must reference degradation-reporter"


def test_degradation_planner_treatment_steps():
    """Spec: treatment steps include restart, reconfigure, rollback, escalate."""
    content = RECIPE.read_text()
    for step in ("restart", "reconfigure", "rollback", "escalate"):
        assert step in content.lower(), \
            f"degradation-planner must list treatment step: {step}"


def test_degradation_planner_no_sub_recipes():
    """Planner is a single-role leaf node."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "degradation-planner must be a single-role leaf node"
