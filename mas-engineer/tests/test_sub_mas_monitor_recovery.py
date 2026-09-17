"""
test_sub_mas_monitor_recovery.py — sanity tests for monitor-recovery.

Monitor-recovery restarts dead/looping agents, max 3 attempts, then
escalates. Thin wrapper around tools/dev_health_monitor.py RECOVER
(R85 Phase 2).

Run with:
    python3 -m pytest tests/test_sub_mas_monitor_recovery.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-monitor-recovery.yaml"
TOOL = REPO_ROOT / "tools" / "dev_health_monitor.py"


def test_monitor_recovery_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_monitor_recovery_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_monitor_recovery_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data


def test_monitor_recovery_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_monitor_recovery_delegates_to_script():
    """R85 Phase 2: must reference dev_health_monitor.py RECOVER."""
    content = RECIPE.read_text()
    assert "dev_health_monitor.py" in content, \
        "Recipe must reference tools/dev_health_monitor.py (R85 Phase 2)"
    assert "RECOVER" in content, "Recipe must call RECOVER subcommand"


def test_monitor_recovery_max_attempts_3():
    """Spec: max 3 attempts before ESCALATE signal."""
    content = RECIPE.read_text()
    assert "3" in content and "max" in content.lower(), \
        "Monitor-recovery must enforce max 3 attempts"


def test_monitor_recovery_escalate_signal():
    """After max attempts, must signal ESCALATE."""
    content = RECIPE.read_text()
    assert "ESCALATE" in content, "Must define ESCALATE signal after max attempts"


def test_monitor_recovery_no_general_improver_recursion():
    """R04: NEVER edit general-improver.yaml (no recursion)."""
    content = RECIPE.read_text()
    assert "R04" in content or "NEVER edit general-improver" in content, \
        "Monitor-recovery must declare R04 general-improver no-recursion rule"


def test_monitor_recovery_no_schema_edits():
    """Recovery is action-only, no schema/config edits."""
    content = RECIPE.read_text()
    assert "NO schema" in content or "ONLY Recovery" in content, \
        "Monitor-recovery must be action-only (no schema edits)"


def test_monitor_recovery_tool_has_recover_subcommand():
    """The delegated tool must implement RECOVER subcommand."""
    content = TOOL.read_text()
    assert "RECOVER" in content, "Tool must implement RECOVER subcommand"
