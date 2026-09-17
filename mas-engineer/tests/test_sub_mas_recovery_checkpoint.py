"""
test_sub_mas_recovery_checkpoint.py — sanity tests for recovery-checkpoint.

recovery-checkpoint v1.0.0 creates Git-like workspace snapshots
before each change. Enables precision restore from N steps back.
R37 external instructions.

Run with:
    python3 -m pytest tests/test_sub_mas_recovery_checkpoint.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-recovery-checkpoint.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-recovery-checkpoint.md"


def test_recovery_checkpoint_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_recovery_checkpoint_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_recovery_checkpoint_recipe_has_required_fields():
    """Adapted: no 'settings' field."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_recovery_checkpoint_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_recovery_checkpoint_external_instructions():
    """R37: uses external instructions file."""
    content = RECIPE.read_text()
    assert "sub_mas-recovery-checkpoint.md" in content, \
        "recovery-checkpoint must reference external instructions file (R37)"
    assert "Extended instructions" in content, \
        "recovery-checkpoint must declare external instructions pattern"


def test_recovery_checkpoint_instructions_file_exists():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_recovery_checkpoint_snapshot_role():
    """Spec: Git-like workspace snapshots before each change."""
    content = RECIPE.read_text()
    assert "snapshot" in content.lower() or "Snapshot" in content, \
        "recovery-checkpoint must declare snapshot role"
    assert "before each change" in content or "before" in content.lower(), \
        "recovery-checkpoint must declare pre-change snapshot pattern"


def test_recovery_checkpoint_restore_capability():
    """Spec: precision restore from N steps back."""
    content = RECIPE.read_text()
    assert "restore" in content.lower(), \
        "recovery-checkpoint must declare restore capability"
    assert "N steps" in content or "steps back" in content or "precision" in content.lower(), \
        "recovery-checkpoint must declare N-step restore"


def test_recovery_checkpoint_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "recovery-checkpoint must be single-role leaf"


def test_recovery_checkpoint_r10_coronashield():
    """Spec: R10 — CORONASHIELD pre-validation (R01/R09 not in this recipe)."""
    content = RECIPE.read_text()
    assert "R10" in content, "recovery-checkpoint must declare R10"
    assert "CORONASHIELD" in content, \
        "recovery-checkpoint must declare CORONASHIELD"
    assert "sub_mas-recovery-immune" in content, \
        "recovery-checkpoint must reference recovery-immune for YAML validation"
