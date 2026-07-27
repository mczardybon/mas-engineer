"""
test_sub_mas_dev_analyzer.py — sanity tests for dev-analyzer.

Dev-analyzer v1.0.0 is a single-role agent. ONLY analysis — NO
direct changes. Reports findings to dev-director. Capabilities
list 5 sub-domains: scanner, config-auditor, session-analyst,
goose-expert, prompt-engineer.

Run with:
    python3 -m pytest tests/test_sub_mas_dev_analyzer.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dev-analyzer.yaml"


def test_dev_analyzer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dev_analyzer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dev_analyzer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_dev_analyzer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_dev_analyzer_only_analysis():
    """Spec: ONLY analysis — NO direct changes."""
    content = RECIPE.read_text()
    assert "ONLY analysis" in content, \
        "dev-analyzer must declare ONLY-analysis rule"
    assert "NO direct changes" in content, \
        "dev-analyzer must forbid direct changes"


def test_dev_analyzer_5_capabilities():
    """Spec: 5 sub-capabilities for analysis."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-framework-scanner", "sub_mas-config-auditor",
                "sub_mas-session-analyst", "sub_mas-goose-expert",
                "sub_mas-prompt-engineer"):
        assert sub in content, \
            f"dev-analyzer must list capability: {sub}"


def test_dev_analyzer_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "dev-analyzer must declare R01"
    assert "R09" in content, "dev-analyzer must declare R09"
    assert "R10" in content, "dev-analyzer must declare R10"
    assert "CORONASHIELD" in content, \
        "dev-analyzer must declare CORONASHIELD"


def test_dev_analyzer_reports_to_director():
    """Spec: reports findings to dev-director."""
    content = RECIPE.read_text()
    assert "dev-director" in content, \
        "dev-analyzer must report to dev-director"


def test_dev_analyzer_no_sub_recipes():
    """Analyzer is a single-role leaf (capabilities listed but not sub_recipes)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "dev-analyzer must be a single-role leaf node"


def test_dev_analyzer_single_role():
    """Spec: single role — analyze/audit/scan framework components."""
    content = RECIPE.read_text()
    assert "Analyze, audit" in content or "analyze" in content.lower(), \
        "dev-analyzer must declare analysis role"
