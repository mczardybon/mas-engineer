"""
test_sub_mas_degradation_analyzer.py — sanity tests for degradation-analyzer.

Degradation-analyzer v1.0.0 is a single-role agent. ONLY analysis
of degraded agent reports — NO treatment planning or report writing.
Delegates planning to degradation-planner, reporting to
degradation-reporter.

Run with:
    python3 -m pytest tests/test_sub_mas_degradation_analyzer.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-degradation-analyzer.yaml"


def test_degradation_analyzer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_degradation_analyzer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_degradation_analyzer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_degradation_analyzer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_degradation_analyzer_single_role():
    """Spec: single role — analyze degraded agent reports."""
    content = RECIPE.read_text()
    assert "Single role" in content or "single-role" in content, \
        "degradation-analyzer must declare single role"


def test_degradation_analyzer_only_analysis():
    """Spec: ONLY analysis — NO treatment planning or report writing."""
    content = RECIPE.read_text()
    assert "ONLY analysis" in content, \
        "degradation-analyzer must declare ONLY-analysis rule"


def test_degradation_analyzer_forbids_planning():
    """Spec: NEVER design treatment plans — delegate to planner."""
    content = RECIPE.read_text()
    assert "NEVER design treatment" in content, \
        "degradation-analyzer must forbid treatment planning"
    assert "degradation-planner" in content, \
        "degradation-analyzer must reference degradation-planner"


def test_degradation_analyzer_forbids_reports():
    """Spec: NEVER generate reports — delegate to reporter."""
    content = RECIPE.read_text()
    assert "NEVER generate reports" in content, \
        "degradation-analyzer must forbid report generation"
    assert "degradation-reporter" in content, \
        "degradation-analyzer must reference degradation-reporter"


def test_degradation_analyzer_root_cause_focus():
    """Spec: returns root cause analysis."""
    content = RECIPE.read_text()
    assert "root cause" in content.lower(), \
        "degradation-analyzer must focus on root cause analysis"


def test_degradation_analyzer_no_sub_recipes():
    """Analyzer is a single-role leaf node (delegation via instructions only)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "degradation-analyzer must be a single-role leaf node"
