"""
test_sub_mas_monitor_session.py — sanity tests for monitor-session (R85).

Monitor-session writes cycle logs to .mase/logs/cycle-{YYYY-MM-DD}.log.
R85 Phase 2 refactor: thin wrapper around tools/dev_health_monitor.py
LOG_SESSION subcommand.

Run with:
    python3 -m pytest tests/test_sub_mas_monitor_session.py -v
"""
import yaml
import py_compile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-monitor-session.yaml"
TOOL = REPO_ROOT / "tools" / "dev_health_monitor.py"


def test_monitor_session_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_monitor_session_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_monitor_session_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_monitor_session_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_monitor_session_delegates_to_script():
    """R85 Phase 2: must reference dev_health_monitor.py LOG_SESSION."""
    content = RECIPE.read_text()
    assert "dev_health_monitor.py" in content, \
        "Recipe must reference tools/dev_health_monitor.py (R85 Phase 2)"
    assert "LOG_SESSION" in content, "Recipe must call LOG_SESSION subcommand"


def test_monitor_session_tool_script_exists():
    assert TOOL.exists(), f"Missing delegated tool: {TOOL}"


def test_monitor_session_tool_imports_correctly():
    try:
        py_compile.compile(str(TOOL), doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"Tool has Python syntax errors: {e}")


def test_monitor_session_writes_cycle_log():
    """Spec: appends JSON line to .mase/logs/cycle-{YYYY-MM-DD}.log."""
    content = RECIPE.read_text()
    assert ".mase/logs/" in content, \
        "monitor-session must write to .mase/logs/ directory"
    assert "cycle-" in content, "monitor-session must use cycle-{date}.log naming"
    assert "JSON" in content, "monitor-session must write JSON lines"


def test_monitor_session_r01_r09_compliance():
    """R01 CONFIRMATION + R09 DOMAIN rules must be declared."""
    content = RECIPE.read_text()
    assert "R01" in content, "monitor-session must declare R01 CONFIRMATION rule"
    assert "R09" in content, "monitor-session must declare R09 DOMAIN rule"


def test_monitor_session_no_domain_overreach():
    """R09: NO cross-domain writes. R88 cleanup-rule compatibility."""
    content = RECIPE.read_text()
    assert "NO cross-domain" in content or "Stay within" in content, \
        "monitor-session must declare no-domain-overreach rule"
