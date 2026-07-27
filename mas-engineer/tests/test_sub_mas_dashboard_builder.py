"""
test_sub_mas_dashboard_builder.py — sanity tests for dashboard-builder.

Dashboard-builder v2.0.0 is a thin wrapper (R85 Phase 3) around
tools/dev_dashboard_refresh.py. ONLY dashboard building, NO data
collection.

Run with:
    python3 -m pytest tests/test_sub_mas_dashboard_builder.py -v
"""
import yaml
import py_compile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dashboard-builder.yaml"
TOOL = REPO_ROOT / "tools" / "dev_dashboard_refresh.py"


def test_dashboard_builder_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dashboard_builder_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dashboard_builder_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_dashboard_builder_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_dashboard_builder_v2_thin_wrapper():
    """R85 Phase 3: thin wrapper around dev_dashboard_refresh.py."""
    content = RECIPE.read_text()
    assert "dev_dashboard_refresh.py" in content, \
        "dashboard-builder must reference dev_dashboard_refresh.py (R85)"
    assert "v2.0.0" in content, "dashboard-builder must declare v2.0.0 (R85)"


def test_dashboard_builder_tool_exists():
    assert TOOL.exists(), f"Missing delegated tool: {TOOL}"


def test_dashboard_builder_tool_compiles():
    try:
        py_compile.compile(str(TOOL), doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"Tool has syntax errors: {e}")


def test_dashboard_builder_only_building():
    """Spec: ONLY dashboard building — NO data collection."""
    content = RECIPE.read_text()
    assert "ONLY dashboard building" in content, \
        "dashboard-builder must declare ONLY-building rule"
    assert "NO data collection" in content, \
        "dashboard-builder must forbid data collection"


def test_dashboard_builder_r01_r09():
    """R01 CONFIRMATION + R09 DOMAIN rules."""
    content = RECIPE.read_text()
    assert "R01" in content, "dashboard-builder must declare R01"
    assert "R09" in content, "dashboard-builder must declare R09"


def test_dashboard_builder_output_path():
    """Spec: writes to {workspace}/.mas/dashboards/project.json."""
    content = RECIPE.read_text()
    assert ".mas/dashboards" in content or "project.json" in content, \
        "dashboard-builder must declare output path"
