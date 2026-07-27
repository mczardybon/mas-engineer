"""
test_sub_mas_e2e_german_fixes_runner.py — sanity tests for german-fixes-runner.

German-fixes-runner runs T3: workflow invocation test for all 5
wf_recovery_* workflows via dev_workflow_runner.py.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_german_fixes_runner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-german-fixes-runner.yaml"


def test_german_fixes_runner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_german_fixes_runner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_german_fixes_runner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_german_fixes_runner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_german_fixes_runner_is_t3():
    """Spec: T3 (workflow invocation test)."""
    content = RECIPE.read_text()
    assert "T3" in content, "german-fixes-runner must declare T3"


def test_german_fixes_runner_5_workflows():
    """Spec: 5 wf_recovery_* workflows tested."""
    content = RECIPE.read_text()
    assert "5 recovery workflows" in content or "5 wf_recovery" in content, \
        "german-fixes-runner must declare 5-workflow scope"
    assert "wf_recovery_" in content, \
        "german-fixes-runner must reference wf_recovery_ prefix"


def test_german_fixes_runner_uses_dev_workflow_runner():
    """Spec: invokes via tools/dev_workflow_runner.py."""
    content = RECIPE.read_text()
    assert "dev_workflow_runner.py" in content, \
        "german-fixes-runner must invoke tools/dev_workflow_runner.py"


def test_german_fixes_runner_allowed_skipped():
    """Spec: steps can be 'skipped' if dependencies failed (allowed)."""
    content = RECIPE.read_text()
    assert "skipped" in content or "skip" in content.lower(), \
        "german-fixes-runner must allow skipped steps"


def test_german_fixes_runner_structured_output():
    """Spec: returns {t3: {passed, details, per_workflow: {}}}."""
    content = RECIPE.read_text()
    assert "structured" in content.lower() or "per_workflow" in content, \
        "german-fixes-runner must declare structured output"


def test_german_fixes_runner_no_sub_recipes():
    """Runner is a leaf node."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "german-fixes-runner must be a leaf node"
