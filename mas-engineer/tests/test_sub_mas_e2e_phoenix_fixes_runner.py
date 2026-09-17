"""
test_sub_mas_e2e_phoenix_fixes_runner.py — sanity tests for e2e-phoenix-fixes-runner.

Runs T6 (workflow invocation test) for the e2e-verify-phoenix-fixes
workflow. Loads .mase/workflows.yaml and checks recovery workflows.

Note: this recipe has 'description:' but no 'settings:' field.
Required-fields test adapted accordingly.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_phoenix_fixes_runner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-phoenix-fixes-runner.yaml"


def test_e2e_phoenix_fixes_runner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_e2e_phoenix_fixes_runner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_e2e_phoenix_fixes_runner_recipe_has_required_fields():
    """Adapted: has description+instructions+prompt but no 'settings'."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_e2e_phoenix_fixes_runner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_e2e_phoenix_fixes_runner_t6_role():
    """Spec: T6 — workflow invocation test."""
    content = RECIPE.read_text()
    assert "T6" in content, \
        "e2e-phoenix-fixes-runner must declare T6 role"
    assert "workflow" in content.lower(), \
        "e2e-phoenix-fixes-runner must reference workflows"


def test_e2e_phoenix_fixes_runner_loads_workflows_yaml():
    """Spec: loads .mase/workflows.yaml via yaml.safe_load."""
    content = RECIPE.read_text()
    assert ".mase/workflows.yaml" in content, \
        "e2e-phoenix-fixes-runner must reference .mase/workflows.yaml"
    assert "yaml.safe_load" in content, \
        "e2e-phoenix-fixes-runner must use yaml.safe_load"


def test_e2e_phoenix_fixes_runner_5_recovery_workflows():
    """Spec: checks for 5 recovery workflows (wf_recovery_*)."""
    content = RECIPE.read_text()
    assert "wf_recovery_" in content, \
        "e2e-phoenix-fixes-runner must check wf_recovery_ workflows"
    assert "5" in content, \
        "e2e-phoenix-fixes-runner must expect 5 recovery workflows"


def test_e2e_phoenix_fixes_runner_e2e_verify():
    """Spec: tests e2e-verify-phoenix-fixes workflow."""
    content = RECIPE.read_text()
    assert "e2e-verify-phoenix-fixes" in content, \
        "e2e-phoenix-fixes-runner must test e2e-verify-phoenix-fixes"


def test_e2e_phoenix_fixes_runner_steps_inspection():
    """Spec: iterates over steps and prints step details."""
    content = RECIPE.read_text()
    assert "steps" in content, \
        "e2e-phoenix-fixes-runner must inspect workflow steps"


def test_e2e_phoenix_fixes_runner_no_sub_recipes():
    """Runner is a single-role test executor (no sub_recipes)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "e2e-phoenix-fixes-runner must be a single-role test executor"
