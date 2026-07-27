"""
test_sub_mas_e2e_phoenix_fixes_runner.py — sanity tests for phoenix-fixes-runner.

Phoenix-fixes-runner is T6 of the e2e-verify-phoenix-fixes workflow:
verifies all 5 recovery workflows (wf_recovery_*) can be loaded and
have the right step structure.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_phoenix_fixes_runner.py -v
"""
import yaml
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-phoenix-fixes-runner.yaml"


def test_phoenix_fixes_runner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_phoenix_fixes_runner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_phoenix_fixes_runner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    # This is a runner — no prompt field, only instructions
    for field in ("name", "version", "instructions", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_phoenix_fixes_runner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_phoenix_fixes_runner_is_t6():
    """Spec: T6 (workflow invocation test)."""
    content = RECIPE.read_text()
    assert "T6" in content, "phoenix-fixes-runner must declare T6 test"


def test_phoenix_fixes_runner_test_5_workflows():
    """Spec: T6 verifies all 5 recovery workflows can be loaded."""
    content = RECIPE.read_text()
    assert "5 recovery workflows" in content, \
        "phoenix-fixes-runner must declare 5-workflow check"
    assert "wf_recovery_" in content, \
        "phoenix-fixes-runner must reference wf_recovery_ workflow prefix"


def test_phoenix_fixes_runner_step_count():
    """Spec: prints number of steps per workflow."""
    content = RECIPE.read_text()
    assert "steps" in content, \
        "phoenix-fixes-runner must inspect step counts"


def test_phoenix_fixes_runner_reads_workflows_yaml():
    """Spec: reads .state/workflows.yaml (SOT)."""
    content = RECIPE.read_text()
    assert "workflows.yaml" in content, \
        "phoenix-fixes-runner must read .state/workflows.yaml"


def test_phoenix_fixes_runner_no_sub_recipes():
    """Runner is a leaf node (executor only)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "phoenix-fixes-runner must be a leaf node"


def test_phoenix_fixes_runner_python_executable():
    """Runner embeds a Python check (load + inspect)."""
    content = RECIPE.read_text()
    assert "python3" in content or "yaml.safe_load" in content, \
        "phoenix-fixes-runner must use Python to inspect workflows"
