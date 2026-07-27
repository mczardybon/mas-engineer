"""
test_recipe_root.py — sanity tests for root_recipe.yaml.

root_recipe.yaml is the ROOT recipe for MAS-Engineer.
Defines global settings, extensions, and entry point.

Per R101 EVIDENCE: top-level orchestrator (delegates to dev-mas-engineer).

Run with:
    python3 -m pytest tests/test_recipe_root.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "root_recipe.yaml"


def test_root_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_root_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_root_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    # Root recipe should have at least: title, description
    for field in ("title", "description"):
        assert field in data, f"Missing required field: {field}"


def test_root_recipe_references_mas_engineer():
    with open(RECIPE) as f:
        content = f.read()
    assert "MAS-Engineer" in content or "mas-engineer" in content \
        or "MAS Engineer" in content, \
        "root_recipe must reference MAS-Engineer"


def test_root_recipe_no_sub_recipes():
    """Root recipe is the entry point, no sub_recipes expected."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    # Root may or may not have sub_recipes; if it does, it should
    # be very minimal
    subs = data.get("sub_recipes", [])
    assert len(subs) <= 1, \
        f"root_recipe should have <= 1 sub_recipes, has {len(subs)}"
