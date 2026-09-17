"""
test_sub_mas_degradation_reporter.py — sanity tests for degradation-reporter.

Degradation-reporter v1.0.0 is a single-role agent. ONLY report
writing — NO analysis or treatment planning. Receives treatment
plan from degradation-planner, returns structured report.

Run with:
    python3 -m pytest tests/test_sub_mas_degradation_reporter.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-degradation-reporter.yaml"


def test_degradation_reporter_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_degradation_reporter_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_degradation_reporter_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_degradation_reporter_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_degradation_reporter_single_role():
    """Spec: single role — generate treatment reports."""
    content = RECIPE.read_text()
    assert "Single role" in content or "single-role" in content, \
        "degradation-reporter must declare single role"


def test_degradation_reporter_only_reporting():
    """Spec: ONLY report writing — NO analysis or treatment planning."""
    content = RECIPE.read_text()
    assert "ONLY report writing" in content, \
        "degradation-reporter must declare ONLY-reporting rule"


def test_degradation_reporter_forbids_analysis():
    """Spec: NEVER analyze degradation — delegate to analyzer."""
    content = RECIPE.read_text()
    assert "NEVER analyze" in content, \
        "degradation-reporter must forbid degradation analysis"
    assert "degradation-analyzer" in content, \
        "degradation-reporter must reference degradation-analyzer"


def test_degradation_reporter_forbids_planning():
    """Spec: NEVER design treatments — delegate to planner."""
    content = RECIPE.read_text()
    assert "NEVER design" in content, \
        "degradation-reporter must forbid treatment design"
    assert "degradation-planner" in content, \
        "degradation-reporter must reference degradation-planner"


def test_degradation_reporter_structured_output():
    """Spec: structured report with status, actions, recommendations."""
    content = RECIPE.read_text()
    for field in ("status", "actions", "recommendations"):
        assert field in content.lower(), \
            f"degradation-reporter report must include: {field}"


def test_degradation_reporter_no_sub_recipes():
    """Reporter is a single-role leaf node."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "degradation-reporter must be a single-role leaf node"
