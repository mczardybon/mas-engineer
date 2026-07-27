"""
test_sub_mas_dev_builder.py — sanity tests for dev-builder.

Dev-builder v1.0.0 is a single-role agent. ONLY creation — NO
direct analysis or testing. Creates agents, recipes, and framework
components. Capabilities: recipe-designer, template-generator,
intention-parser, team-packager, generic-init.

Run with:
    python3 -m pytest tests/test_sub_mas_dev_builder.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dev-builder.yaml"


def test_dev_builder_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dev_builder_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dev_builder_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_dev_builder_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_dev_builder_only_creation():
    """Spec: ONLY creation — NO direct analysis or testing."""
    content = RECIPE.read_text()
    assert "ONLY creation" in content, \
        "dev-builder must declare ONLY-creation rule"
    assert "NO direct analysis" in content, \
        "dev-builder must forbid direct analysis"
    assert "or testing" in content, \
        "dev-builder must forbid direct testing (or testing)"


def test_dev_builder_5_capabilities():
    """Spec: 5 sub-capabilities for creation."""
    content = RECIPE.read_text()
    for cap in ("sub_mas-recipe-designer", "dev_template_generator",
                "sub_mas-intention-parser", "sub_mas-team-packager",
                "sub_mas-generic-init"):
        assert cap in content, \
            f"dev-builder must list capability: {cap}"


def test_dev_builder_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "dev-builder must declare R01"
    assert "R09" in content, "dev-builder must declare R09"
    assert "R10" in content, "dev-builder must declare R10"
    assert "CORONASHIELD" in content, \
        "dev-builder must declare CORONASHIELD"


def test_dev_builder_receives_from_director():
    """Spec: receives specs from dev-director."""
    content = RECIPE.read_text()
    assert "dev-director" in content, \
        "dev-builder must receive specs from dev-director"


def test_dev_builder_no_sub_recipes():
    """Builder is a single-role leaf (capabilities listed but not sub_recipes)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "dev-builder must be a single-role leaf node"


def test_dev_builder_designs_recipes():
    """Spec: designs/creates/generates agents, recipes, framework components."""
    content = RECIPE.read_text()
    for verb in ("Design", "creat", "generat"):
        assert verb in content, \
            f"dev-builder must declare creation verb: {verb}"
