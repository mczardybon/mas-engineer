"""
test_sub_mas_recovery_timeline.py — sanity tests for recovery-timeline.

recovery-timeline v1.0.0 automatically finds the best checkpoint,
restores, analyzes damage. 4 operations:
FIND_BEST | RESTORE_BEST | SHOW_PATH | ANALYZE. R37 external
instructions. Settings declared in prompt, not as YAML key.

Run with:
    python3 -m pytest tests/test_sub_mas_recovery_timeline.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-recovery-timeline.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-recovery-timeline.md"


def test_recovery_timeline_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_recovery_timeline_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_recovery_timeline_recipe_has_required_fields():
    """Adapted: no 'settings' field."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_recovery_timeline_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_recovery_timeline_external_instructions():
    """R37: uses external instructions file."""
    content = RECIPE.read_text()
    assert "sub_mas-recovery-timeline.md" in content, \
        "recovery-timeline must reference external instructions file (R37)"
    assert "Extended instructions" in content, \
        "recovery-timeline must declare external instructions pattern"


def test_recovery_timeline_instructions_file_exists():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_recovery_timeline_best_point_search():
    """Spec: automatic best-point search."""
    content = RECIPE.read_text()
    assert "TIMELINE" in content, \
        "recovery-timeline must declare TIMELINE role"
    assert "Automatic" in content or "automatic" in content.lower(), \
        "recovery-timeline must declare automatic search"


def test_recovery_timeline_4_operations():
    """Spec: 4 operations — FIND_BEST | RESTORE_BEST | SHOW_PATH | ANALYZE."""
    content = RECIPE.read_text()
    for op in ("FIND_BEST", "RESTORE_BEST", "SHOW_PATH", "ANALYZE"):
        assert op in content, \
            f"recovery-timeline must declare operation: {op}"


def test_recovery_timeline_sot_workflow_check():
    """Spec: workflow boundaries via workflows.yaml + dev_rule_checker."""
    content = RECIPE.read_text()
    assert "workflows.yaml" in content, \
        "recovery-timeline must reference workflows.yaml (SOT)"
    assert "dev_rule_checker" in content, \
        "recovery-timeline must reference dev_rule_checker.py"


def test_recovery_timeline_r10_coronashield():
    """Spec: R10 — CORONASHIELD pre-validation."""
    content = RECIPE.read_text()
    assert "R10" in content, "recovery-timeline must declare R10"
    assert "CORONASHIELD" in content, \
        "recovery-timeline must declare CORONASHIELD"
    assert "sub_mas-recovery-immune" in content, \
        "recovery-timeline must reference recovery-immune for YAML validation"
