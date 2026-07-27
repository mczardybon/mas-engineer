"""
test_sub_mas_monitor_runtime.py — sanity tests for monitor-runtime (R85).

Monitor-runtime detects active/stale sessions, crashes, arch violations.
R85 Phase 2 refactor: thin wrapper around tools/dev_health_monitor.py
CHECK_RUNTIME subcommand.

Run with:
    python3 -m pytest tests/test_sub_mas_monitor_runtime.py -v
"""
import yaml
import py_compile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-monitor-runtime.yaml"
TOOL = REPO_ROOT / "tools" / "dev_health_monitor.py"


def test_monitor_runtime_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_monitor_runtime_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_monitor_runtime_recipe_has_required_fields():
    """monitor-runtime has inline-instructions (not external file)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_monitor_runtime_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_monitor_runtime_delegates_to_script():
    """R85 Phase 2: must reference dev_health_monitor.py CHECK_RUNTIME."""
    content = RECIPE.read_text()
    assert "dev_health_monitor.py" in content, \
        "Recipe must reference tools/dev_health_monitor.py (R85 Phase 2)"
    assert "CHECK_RUNTIME" in content, "Recipe must call CHECK_RUNTIME subcommand"


def test_monitor_runtime_tool_script_exists():
    assert TOOL.exists(), f"Missing delegated tool: {TOOL}"


def test_monitor_runtime_tool_imports_correctly():
    try:
        py_compile.compile(str(TOOL), doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"Tool has Python syntax errors: {e}")


def test_monitor_runtime_returns_json():
    """Spec: returns JSON with active_sessions, stale_sessions, crashes,
    arch_violations, signal."""
    content = RECIPE.read_text()
    for field in ("active_sessions", "stale_sessions", "crashes",
                  "arch_violations", "signal"):
        assert field in content, \
            f"monitor-runtime JSON output must include: {field}"


def test_monitor_runtime_r01_r09_compliance():
    """R01 CONFIRMATION + R09 DOMAIN rules must be declared."""
    content = RECIPE.read_text()
    assert "R01" in content, "monitor-runtime must declare R01 CONFIRMATION rule"
    assert "R09" in content, "monitor-runtime must declare R09 DOMAIN rule"


def test_monitor_runtime_readonly():
    """ONLY Runtime-Check — NO changes."""
    content = RECIPE.read_text()
    assert "NO changes" in content or "ONLY Runtime-Check" in content, \
        "monitor-runtime must declare read-only (R85)"
