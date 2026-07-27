"""
test_sub_mas_dashboard_director.py — sanity tests for dashboard-director.

Dashboard-director is the orchestrator for dashboard operations.
Delegates to data-reader (collection) and generator (building).
Has explicit NEVER-collect/NEVER-generate prohibitions.

Run with:
    python3 -m pytest tests/test_sub_mas_dashboard_director.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dashboard-director.yaml"


def test_dashboard_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dashboard_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dashboard_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_dashboard_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_dashboard_director_orchestrator():
    """Spec: orchestrator — delegates to specialized sub-agents."""
    content = RECIPE.read_text()
    assert "Orchestrator" in content or "orchestrate" in content.lower(), \
        "dashboard-director must be an orchestrator"
    assert "Delegate" in content or "delegate" in content, \
        "dashboard-director must delegate to sub-agents"


def test_dashboard_director_delegation_map():
    """Spec: read/collect → data-reader, generate/build → generator."""
    content = RECIPE.read_text()
    assert "sub_mas-dashboard-data-reader" in content, \
        "dashboard-director must delegate to data-reader"
    assert "sub_mas-dashboard-generator" in content, \
        "dashboard-director must delegate to generator"


def test_dashboard_director_prohibitions():
    """Spec: NEVER collect data directly, NEVER generate dashboard directly."""
    content = RECIPE.read_text()
    assert "NEVER collect" in content, \
        "dashboard-director must forbid direct data collection"
    assert "NEVER generate" in content, \
        "dashboard-director must forbid direct dashboard generation"


def test_dashboard_director_sub_recipes():
    """Director must have sub_recipes for data-reader + generator."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-dashboard-data-reader" in subs, \
        f"dashboard-director sub_recipes must include data-reader. subs: {subs}"
    assert "sub_mas-dashboard-generator" in subs, \
        f"dashboard-director sub_recipes must include generator. subs: {subs}"


def test_dashboard_director_uses_deepseek():
    """R36+: cost-control via deepseek."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    model = data.get("settings", {}).get("goose_model", "")
    assert "deepseek" in model, \
        f"dashboard-director should use deepseek (R36+), got: {model}"


def test_dashboard_director_no_data_collection():
    """Spec: only delegate, no direct I/O."""
    content = RECIPE.read_text()
    # Verify prohibitions appear as declarative rules, not permissive
    assert "PROHIBITIONS" in content or "PROHIBITION" in content, \
        "dashboard-director must declare PROHIBITIONS section"
