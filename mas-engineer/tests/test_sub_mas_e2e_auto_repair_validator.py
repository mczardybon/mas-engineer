"""
test_sub_mas_e2e_auto_repair_validator.py — sanity tests for auto-repair-validator.

Auto-repair-validator runs T1, T4-T10 for the e2e-verify-auto-repair
workflow. Each test verifies auto_repair step is in a specific
recovery workflow.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_auto_repair_validator.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-auto-repair-validator.yaml"


def test_auto_repair_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_auto_repair_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_auto_repair_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_auto_repair_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_auto_repair_validator_t1_t4_to_t10():
    """Spec: T1, T4-T10 (8 tests)."""
    content = RECIPE.read_text()
    for t in ("T1", "T4", "T5", "T6", "T7", "T8", "T9", "T10"):
        assert t in content, f"auto-repair-validator must declare test: {t}"


def test_auto_repair_validator_4_workflows():
    """Spec: T1, T4-T6 — auto_repair in 4 workflows (checkpoint, defib,
    safezone, timeline)."""
    content = RECIPE.read_text()
    for wf in ("wf_recovery_checkpoint", "wf_recovery_defib",
               "wf_recovery_safezone", "wf_recovery_timeline"):
        assert wf in content, \
            f"auto-repair-validator must reference: {wf}"


def test_auto_repair_validator_step_4_position():
    """Spec: T7 — auto_repair is at step 4 in all workflows."""
    content = RECIPE.read_text()
    assert "step 4" in content or "Step 4" in content, \
        "auto-repair-validator T7 must check step 4 position"


def test_auto_repair_validator_reads_workflows_yaml():
    """Spec: reads .state/workflows.yaml SOT."""
    content = RECIPE.read_text()
    assert "workflows.yaml" in content, \
        "auto-repair-validator must read .state/workflows.yaml"


def test_auto_repair_validator_python_check():
    """Spec: uses python3 yaml.safe_load for inspection."""
    content = RECIPE.read_text()
    assert "python3" in content or "yaml.safe_load" in content, \
        "auto-repair-validator must use Python yaml inspection"


def test_auto_repair_validator_auto_repair_id():
    """Spec: looks for 'auto_repair' substring in step.id."""
    content = RECIPE.read_text()
    assert "auto_repair" in content, \
        "auto-repair-validator must check for auto_repair in step id"
