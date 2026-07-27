"""
test_sub_mas_generic_init.py — sanity tests for generic-init.

Generic-init is the project-bootstrap agent: symlink + guidelines +
remote analysis. v3.0.0 (NO agent copies, R88 cleanup philosophy).

Run with:
    python3 -m pytest tests/test_sub_mas_generic_init.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-generic-init.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-generic-init.md"


def test_generic_init_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_generic_init_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_generic_init_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_generic_init_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_generic_init_instructions_exist():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_generic_init_v3_symlink_approach():
    """v3.0.0: NO agent copies — symlink + guidelines + remote analysis."""
    content = RECIPE.read_text()
    assert "symlink" in content.lower(), \
        "generic-init v3.0.0 must use symlink approach (R88)"
    assert "NO agent copies" in content or "no copies" in content.lower(), \
        "generic-init v3.0.0 must declare NO-agent-copies rule"


def test_generic_init_subrecipes():
    """Spec: summons sub_mas-web-researcher + sub_mas-recipe-designer."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-web-researcher" in subs, \
        f"generic-init must summon web-researcher. subs: {subs}"
    assert "sub_mas-recipe-designer" in subs, \
        f"generic-init must summon recipe-designer. subs: {subs}"


def test_generic_init_only_initialize():
    """Spec: Only initialize — NO changes to existing projects."""
    content = RECIPE.read_text()
    assert "Only initialize" in content or "ONLY initialize" in content, \
        "generic-init must declare Only-initialize rule"


def test_generic_init_uses_master_constitution():
    """Spec: See MASTER-CONSTITUTION Art. 1-6."""
    content = RECIPE.read_text()
    assert "MASTER-CONSTITUTION" in content or "master-constitution" in content, \
        "generic-init must reference MASTER-CONSTITUTION"


def test_generic_init_external_instructions_ref():
    """Recipe must reference the external instructions file (R37)."""
    content = RECIPE.read_text()
    assert "sub_mas-generic-init.md" in content, \
        "Recipe must reference external instructions file (R37)"
