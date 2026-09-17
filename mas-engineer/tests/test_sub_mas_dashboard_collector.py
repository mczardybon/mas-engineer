"""
test_sub_mas_dashboard_collector.py — sanity tests for dashboard-collector.

Dashboard-collector v2.0.0 is a thin wrapper (R85 Phase 3) around
tools/dev_dashboard_data.py. ONLY data collection, NO dashboard building.

Run with:
    python3 -m pytest tests/test_sub_mas_dashboard_collector.py -v
"""
import yaml
import py_compile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dashboard-collector.yaml"
TOOL = REPO_ROOT / "tools" / "dev_dashboard_data.py"


def test_dashboard_collector_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dashboard_collector_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dashboard_collector_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_dashboard_collector_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_dashboard_collector_v2_thin_wrapper():
    """R85 Phase 3: thin wrapper around dev_dashboard_data.py."""
    content = RECIPE.read_text()
    assert "dev_dashboard_data.py" in content, \
        "dashboard-collector must reference dev_dashboard_data.py (R85)"
    assert "v2.0.0" in content, "dashboard-collector must declare v2.0.0 (R85)"


def test_dashboard_collector_tool_exists():
    assert TOOL.exists(), f"Missing delegated tool: {TOOL}"


def test_dashboard_collector_tool_compiles():
    try:
        py_compile.compile(str(TOOL), doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"Tool has syntax errors: {e}")


def test_dashboard_collector_only_collection():
    """Spec: ONLY data collection — NO dashboard building."""
    content = RECIPE.read_text()
    assert "ONLY data collection" in content, \
        "dashboard-collector must declare ONLY-collection rule"
    assert "NO dashboard building" in content, \
        "dashboard-collector must forbid dashboard building"


def test_dashboard_collector_r01_r09_r10():
    """R01 CONFIRMATION + R09 DOMAIN + R10 CORONASHIELD rules."""
    content = RECIPE.read_text()
    assert "R01" in content, "dashboard-collector must declare R01"
    assert "R09" in content, "dashboard-collector must declare R09"
    assert "R10" in content, "dashboard-collector must declare R10"
    assert "CORONASHIELD" in content, \
        "dashboard-collector must declare CORONASHIELD"


def test_dashboard_collector_output_path():
    """Spec: writes to {workspace}/.mase/dashboards/data.json."""
    content = RECIPE.read_text()
    assert ".mase/dashboards" in content or "data.json" in content, \
        "dashboard-collector must declare output path"
