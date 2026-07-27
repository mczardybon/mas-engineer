"""
test_sub_mas_e2e_phoenix_fixes_validator.py — sanity tests for phoenix-fixes-validator.

Phoenix-fixes-validator runs T1-T5 and T7 tests for the
e2e-verify-phoenix-fixes workflow. Each test inspects a specific
recovery workflow in .state/workflows.yaml.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_phoenix_fixes_validator.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-phoenix-fixes-validator.yaml"


def test_phoenix_fixes_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_phoenix_fixes_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_phoenix_fixes_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_phoenix_fixes_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_phoenix_fixes_validator_t1_immune():
    """Spec: T1 — wf_recovery_immune exists in .state/workflows.yaml."""
    content = RECIPE.read_text()
    assert "T1" in content, "phoenix-fixes-validator must declare T1"
    assert "wf_recovery_immune" in content, \
        "phoenix-fixes-validator T1 must reference wf_recovery_immune"


def test_phoenix_fixes_validator_t2_5_workflows():
    """Spec: T2 — 4 new recovery workflows exist (total 5 with immune)."""
    content = RECIPE.read_text()
    assert "T2" in content, "phoenix-fixes-validator must declare T2"
    assert "5" in content, "phoenix-fixes-validator T2 must expect 5 workflows"
    for wf in ("checkpoint", "defib", "safezone", "timeline"):
        assert wf in content, \
            f"phoenix-fixes-validator T2 must reference wf: {wf}"


def test_phoenix_fixes_validator_t3_checkpoint_restore():
    """Spec: T3 — recovery_checkpoint has restore-step."""
    content = RECIPE.read_text()
    assert "T3" in content, "phoenix-fixes-validator must declare T3"
    assert "restore" in content.lower(), \
        "phoenix-fixes-validator T3 must check for restore-step"


def test_phoenix_fixes_validator_t4_defib():
    """Spec: T4 — recovery_defib has defibrillate-step."""
    content = RECIPE.read_text()
    assert "T4" in content, "phoenix-fixes-validator must declare T4"
    assert "defib" in content.lower(), \
        "phoenix-fixes-validator T4 must check for defibrillate-step"


def test_phoenix_fixes_validator_t5_safezone():
    """Spec: T5 — recovery_safezone has safezone-step."""
    content = RECIPE.read_text()
    assert "T5" in content, "phoenix-fixes-validator must declare T5"
    assert "safezone" in content.lower(), \
        "phoenix-fixes-validator T5 must check for safezone-step"


def test_phoenix_fixes_validator_reads_workflows_yaml():
    """Spec: reads .state/workflows.yaml SOT (consistent with T6 runner)."""
    content = RECIPE.read_text()
    assert "workflows.yaml" in content, \
        "phoenix-fixes-validator must read .state/workflows.yaml"
