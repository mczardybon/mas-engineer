"""
test_sub_mas_e2e_phoenix_fixes_validator.py — sanity tests for e2e-phoenix-fixes-validator.

Validates phoenix-recovery fix state — runs T1-T5 and T7 tests for
e2e-verify-phoenix-fixes workflow. 5 sub-checks against
.state/workflows.yaml.

Note: this recipe has 'description:' but no 'settings:' field.
Required-fields test adapted accordingly.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_phoenix_fixes_validator.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-phoenix-fixes-validator.yaml"


def test_e2e_phoenix_fixes_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_e2e_phoenix_fixes_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_e2e_phoenix_fixes_validator_recipe_has_required_fields():
    """Adapted: has description+instructions+prompt but no 'settings'."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_e2e_phoenix_fixes_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_e2e_phoenix_fixes_validator_t1_t5_t7():
    """Spec: T1-T5 and T7 — 6 sub-checks total."""
    content = RECIPE.read_text()
    for t in ("T1:", "T2:", "T3:", "T4:", "T5:", "T7:"):
        assert t in content, \
            f"e2e-phoenix-fixes-validator must declare {t}"


def test_e2e_phoenix_fixes_validator_t1_wf_recovery_immune():
    """Spec: T1 — wf_recovery_immune exists."""
    content = RECIPE.read_text()
    assert "wf_recovery_immune" in content, \
        "e2e-phoenix-fixes-validator T1 must check wf_recovery_immune"


def test_e2e_phoenix_fixes_validator_t2_4_new_workflows():
    """Spec: T2 — 4 new recovery workflows exist."""
    content = RECIPE.read_text()
    assert "4 new recovery" in content or "4 new" in content.lower(), \
        "e2e-phoenix-fixes-validator T2 must check 4 new workflows"
    # The 4 new workflows (immune is the 5th baseline)
    for wf in ("recovery_checkpoint", "recovery_defib",
               "recovery_safezone", "recovery_timeline"):
        assert wf in content, \
            f"e2e-phoenix-fixes-validator T2 must check {wf}"


def test_e2e_phoenix_fixes_validator_t3_restore_step():
    """Spec: T3 — recovery_checkpoint has restore-step."""
    content = RECIPE.read_text()
    assert "restore" in content.lower(), \
        "e2e-phoenix-fixes-validator T3 must check restore step"


def test_e2e_phoenix_fixes_validator_t5_t7_safezone():
    """Spec: T5/T7 — recovery_safezone has safezone-step."""
    content = RECIPE.read_text()
    assert "safezone" in content, \
        "e2e-phoenix-fixes-validator T5 must check safezone step"


def test_e2e_phoenix_fixes_validator_no_sub_recipes():
    """Validator is a single-role test validator (no sub_recipes)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "e2e-phoenix-fixes-validator must be a single-role validator"
