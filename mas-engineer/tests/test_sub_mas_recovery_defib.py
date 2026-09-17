"""
test_sub_mas_recovery_defib.py — sanity tests for recovery-defib.

recovery-defib v1.0.0 is the LAST-RESORT emergency revival at total
failure. Minimal config + DEFIB-RESURRECT-DIAGNOSE. R37 external
instructions. Settings declared in prompt, not as YAML key.

Run with:
    python3 -m pytest tests/test_sub_mas_recovery_defib.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-recovery-defib.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-recovery-defib.md"


def test_recovery_defib_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_recovery_defib_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_recovery_defib_recipe_has_required_fields():
    """Adapted: no 'settings' field — required-fields based on actual recipe."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_recovery_defib_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_recovery_defib_external_instructions():
    """R37: uses external instructions file."""
    content = RECIPE.read_text()
    assert "sub_mas-recovery-defib.md" in content, \
        "recovery-defib must reference external instructions file (R37)"
    assert "Extended instructions" in content, \
        "recovery-defib must declare external instructions pattern"


def test_recovery_defib_instructions_file_exists():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_recovery_defib_last_resort_role():
    """Spec: last resort at total failure."""
    content = RECIPE.read_text()
    assert "last resort" in content, \
        "recovery-defib must declare last-resort role"
    assert "EMERGENCY" in content or "emergency" in content.lower(), \
        "recovery-defib must declare EMERGENCY context"


def test_recovery_defib_3_operations():
    """Spec: DEFIB | RESURRECT | DIAGNOSE."""
    content = RECIPE.read_text()
    for op in ("DEFIB", "RESURRECT", "DIAGNOSE"):
        assert op in content, \
            f"recovery-defib must declare operation: {op}"


def test_recovery_defib_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "recovery-defib must be single-role leaf"


def test_recovery_defib_r10_coronashield():
    """Spec: R10 — CORONASHIELD pre-validation."""
    content = RECIPE.read_text()
    assert "R10" in content, "recovery-defib must declare R10"
    assert "CORONASHIELD" in content, \
        "recovery-defib must declare CORONASHIELD"
    assert "sub_mas-recovery-immune" in content, \
        "recovery-defib must reference recovery-immune for YAML validation"
