"""
test_sub_mas_recovery_safezone.py — sanity tests for recovery-safezone.

recovery-safezone v1.0.0 works in FORK, merges only after complete
validation. Main workspace untouched. 4 operations:
FORK | MERGE | ABORT | DIFF. R37 external instructions.

Run with:
    python3 -m pytest tests/test_sub_mas_recovery_safezone.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-recovery-safezone.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-recovery-safezone.md"


def test_recovery_safezone_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_recovery_safezone_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_recovery_safezone_recipe_has_required_fields():
    """Adapted: no 'settings' field."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_recovery_safezone_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_recovery_safezone_external_instructions():
    """R37: uses external instructions file."""
    content = RECIPE.read_text()
    assert "sub_mas-recovery-safezone.md" in content, \
        "recovery-safezone must reference external instructions file (R37)"
    assert "Extended instructions" in content, \
        "recovery-safezone must declare external instructions pattern"


def test_recovery_safezone_instructions_file_exists():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_recovery_safezone_fork_role():
    """Spec: works in fork — main workspace untouched."""
    content = RECIPE.read_text()
    assert "FORK" in content or "fork" in content.lower(), \
        "recovery-safezone must declare fork role"
    assert "Main untouched" in content or "untouched" in content.lower(), \
        "recovery-safezone must declare main-workspace-untouched pattern"


def test_recovery_safezone_4_operations():
    """Spec: 4 operations — FORK | MERGE | ABORT | DIFF."""
    content = RECIPE.read_text()
    for op in ("FORK", "MERGE", "ABORT", "DIFF"):
        assert op in content, \
            f"recovery-safezone must declare operation: {op}"


def test_recovery_safezone_sot_workflow_check():
    """Spec: workflow boundaries checked via workflows.yaml + dev_rule_checker."""
    content = RECIPE.read_text()
    assert "workflows.yaml" in content, \
        "recovery-safezone must reference workflows.yaml (SOT)"
    assert "dev_rule_checker" in content, \
        "recovery-safezone must reference dev_rule_checker.py"


def test_recovery_safezone_r01_r09_r10():
    """Spec: R01 (Confirmation), R09 (no domain-overreach), R10."""
    content = RECIPE.read_text()
    assert "Confirmation" in content or "confirmation" in content.lower(), \
        "recovery-safezone must declare R01 Confirmation"
    assert "domain-overreach" in content, \
        "recovery-safezone must declare R09 domain-overreach"
    assert "R10" in content, "recovery-safezone must declare R10"
    assert "CORONASHIELD" in content, \
        "recovery-safezone must declare CORONASHIELD"
