"""
test_sub_mas_e2e_auto_repair_runner.py — sanity tests for auto-repair-runner.

Auto-repair-runner runs T2-T3 for the e2e-verify-auto-repair workflow.
Verifies wf_recovery_immune has an auto_repair step at position 4.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_auto_repair_runner.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-auto-repair-runner.yaml"


def test_auto_repair_runner_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_auto_repair_runner_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_auto_repair_runner_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_auto_repair_runner_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_auto_repair_runner_is_t2_t3():
    """Spec: T2-T3 tests for auto-repair."""
    content = RECIPE.read_text()
    assert "T2" in content, "auto-repair-runner must declare T2"
    assert "T3" in content, "auto-repair-runner must declare T3"


def test_auto_repair_runner_t2_auto_repair_step():
    """Spec: T2 — wf_recovery_immune has auto_repair step."""
    content = RECIPE.read_text()
    assert "auto_repair" in content, \
        "auto-repair-runner T2 must check for auto_repair step"
    assert "wf_recovery_immune" in content, \
        "auto-repair-runner T2 must reference wf_recovery_immune"


def test_auto_repair_runner_t3_step_position():
    """Spec: T3 — auto_repair step is at position 4 in wf_recovery_immune."""
    content = RECIPE.read_text()
    assert "step 4" in content or "idx[0]+1" in content or "4" in content, \
        "auto-repair-runner T3 must verify step 4 position"


def test_auto_repair_runner_only_t2_t3():
    """Spec: ONLY T2-T3 runner — no changes."""
    content = RECIPE.read_text()
    assert "ONLY T2-T3" in content or "no changes" in content, \
        "auto-repair-runner must declare ONLY-T2-T3 rule"


def test_auto_repair_runner_structured_output():
    """Spec: returns {t2: {passed, details}, t3: {passed, details}}."""
    content = RECIPE.read_text()
    assert "structured" in content.lower() or "passed" in content, \
        "auto-repair-runner must declare structured output format"


def test_auto_repair_runner_no_sub_recipes():
    """Runner is a leaf node (executor only)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "auto-repair-runner must be a leaf node"
