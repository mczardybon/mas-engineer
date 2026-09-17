"""
test_sub_mas_monitor_health.py — sanity tests for the monitor-health recipe.

Monitor-health is a thin wrapper around tools/dev_health_monitor.py (R85
Phase 2 refactor). Runs static checks: YAML-Integrity, Invariants,
Governance, Structure.

Run with:
    python3 -m pytest tests/test_sub_mas_monitor_health.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-monitor-health.yaml"
TOOL = REPO_ROOT / "tools" / "dev_health_monitor.py"


def test_monitor_health_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_monitor_health_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_monitor_health_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data


def test_monitor_health_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_monitor_health_delegates_to_script():
    """R85: recipe must delegate to tools/dev_health_monitor.py."""
    content = RECIPE.read_text()
    assert "dev_health_monitor.py" in content, \
        "Recipe must reference tools/dev_health_monitor.py (R85 Phase 2)"


def test_monitor_health_tool_script_exists():
    assert TOOL.exists(), f"Missing delegated tool: {TOOL}"


def test_monitor_health_tool_imports_correctly():
    """R10 CORONASHIELD: tool must be valid Python."""
    import py_compile
    try:
        py_compile.compile(str(TOOL), doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"Tool has Python syntax errors: {e}")


def test_monitor_health_tool_has_check_health_subcommand():
    """Tool must define CHECK_HEALTH subcommand."""
    content = TOOL.read_text()
    assert "CHECK_HEALTH" in content, "Tool must implement CHECK_HEALTH subcommand"


def test_monitor_health_returns_json():
    """Output must be JSON (per instructions)."""
    content = RECIPE.read_text()
    assert "JSON" in content, "Monitor-health must return JSON output"


def test_monitor_health_readonly():
    """Monitor-health is pure static-analysis, must not write."""
    content = RECIPE.read_text()
    assert "NO changes" in content or "ONLY Static" in content, \
        "Monitor-health must be read-only (R85)"
