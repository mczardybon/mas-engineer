"""
test_sub_mas_yaml_editor.py — sanity tests for yaml-editor (sub-agent).

Yaml-editor is the safe-YAML-edit sub-agent: Backup → Edit → Validate →
rollback. Used by general-improver's R-Application stage.

Run with:
    python3 -m pytest tests/test_sub_mas_yaml_editor.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-yaml-editor.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-yaml-editor.md"


def test_yaml_editor_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_yaml_editor_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_yaml_editor_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_yaml_editor_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_yaml_editor_instructions_exist():
    """R37: external instructions file must exist."""
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_yaml_editor_has_backup_step():
    """Spec: Backup → Edit → Validate → rollback. First step must be backup."""
    content = INSTRUCTIONS.read_text()
    # Backup must be mentioned explicitly
    assert "Backup" in content or "backup" in content, \
        "Yaml-editor must define backup step (first in pipeline)"


def test_yaml_editor_has_rollback_step():
    """Spec includes rollback if validation fails."""
    content = INSTRUCTIONS.read_text()
    assert "rollback" in content.lower() or "Rollback" in content, \
        "Yaml-editor must define rollback step (if validation fails)"


def test_yaml_editor_has_validate_step():
    """Spec: must validate YAML before considering edit complete (R10 CORONASHIELD)."""
    content = INSTRUCTIONS.read_text()
    assert "Validate" in content or "validate" in content or "CORONASHIELD" in content, \
        "Yaml-editor must validate after edit (R10)"


def test_yaml_editor_uses_external_instructions():
    """Recipe must reference the external instructions file (R37)."""
    content = RECIPE.read_text()
    assert "sub_mas-yaml-editor.md" in content, \
        "Recipe must reference external instructions file (R37)"


def test_yaml_editor_no_sub_recipes():
    """Yaml-editor is a leaf node (no further delegation)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "Yaml-editor must be a leaf node (no sub_recipes)"
