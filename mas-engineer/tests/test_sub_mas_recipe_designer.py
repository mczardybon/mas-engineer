"""
test_sub_mas_recipe_designer.py — sanity tests for recipe-designer.

recipe-designer v1.0.0 conceives, designs, and registers new
sub-agent recipes. Orchestrator + 3 sub-agents: scoper, generator,
registrar. R37 external instructions.

Note: this recipe has no 'settings' field.
Required-fields test adapted accordingly.

Run with:
    python3 -m pytest tests/test_sub_mas_recipe_designer.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-recipe-designer.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-recipe-designer.md"


def test_recipe_designer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_recipe_designer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_recipe_designer_recipe_has_required_fields():
    """Adapted: has description+instructions+prompt but no 'settings'."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_recipe_designer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_recipe_designer_external_instructions():
    """R37: uses external instructions file."""
    content = RECIPE.read_text()
    assert "sub_mas-recipe-designer.md" in content, \
        "recipe-designer must reference external instructions file (R37)"
    assert "Extended instructions" in content, \
        "recipe-designer must declare external instructions pattern"


def test_recipe_designer_instructions_file_exists():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_recipe_designer_orchestrator():
    """Spec: orchestrator + 3 sub-agents — scoper, generator, registrar."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-recipe-designer-scoper",
                "sub_mas-recipe-designer-generator",
                "sub_mas-recipe-designer-registrar"):
        assert sub in content, \
            f"recipe-designer must declare sub-agent: {sub}"


def test_recipe_designer_7_prohibitions():
    """Spec: 7 NEVER-X prohibition boundary rules."""
    content = RECIPE.read_text()
    for forbid in ("NEVER edit existing agent settings",
                   "NEVER modify sub_mas-general-improver.yaml",
                   "NEVER modify constitution files",
                   "NEVER modify tools/dev_workspace.py",
                   "NEVER save YAML without pre-validation",
                   "NEVER skip R01 confirmation",
                   "NEVER operate outside target workspace"):
        assert forbid in content, \
            f"recipe-designer must forbid: {forbid[:40]}..."


def test_recipe_designer_r04_no_recursion():
    """Spec: R04 — NEVER modify sub_mas-general-improver.yaml."""
    content = RECIPE.read_text()
    assert "R04" in content, \
        "recipe-designer must declare R04 (no recursion)"
    assert "general-improver" in content, \
        "recipe-designer must reference general-improver (R04 target)"


def test_recipe_designer_r10_coronashield():
    """Spec: R10 — pre-validation via sub_mas-recovery-immune CHECK_YAML."""
    content = RECIPE.read_text()
    assert "R10" in content, "recipe-designer must declare R10"
    assert "sub_mas-recovery-immune" in content, \
        "recipe-designer must use recovery-immune for YAML validation"
    assert "CHECK_YAML" in content, \
        "recipe-designer must call CHECK_YAML for pre-validation"
