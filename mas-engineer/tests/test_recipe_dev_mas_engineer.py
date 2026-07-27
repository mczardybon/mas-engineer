"""
test_recipe_dev_mas_engineer.py — sanity tests for dev-mas-engineer.yaml.

dev-mas-engineer v1.0.0 is the DEV ENTRY POINT for MAS-Engineer.
Fully autonomous, thin delegator that routes to sub_mas-dev-director.

Per R101 EVIDENCE: top-level thin delegator (sub_recipes=1).

Run with:
    python3 -m pytest tests/test_recipe_dev_mas_engineer.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "dev-mas-engineer.yaml"


def test_dev_mas_engineer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_dev_mas_engineer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_dev_mas_engineer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "description"):
        assert field in data, f"Missing required field: {field}"


def test_dev_mas_engineer_thin_delegator():
    """Spec: Fully autonomous. Thin delegator that routes to
    sub_mas-dev-director.
    """
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = data.get("sub_recipes", [])
    assert len(subs) == 1, \
        f"dev-mas-engineer must have exactly 1 sub_recipes, has {len(subs)}"
    assert subs[0].get("name") == "sub_mas-dev-director", \
        f"dev-mas-engineer must delegate to sub_mas-dev-director, " \
        f"got {subs[0].get('name')}"


def test_dev_mas_engineer_description():
    """Spec: v1.0.0 | Fully autonomous. Thin delegator that routes to
    sub_mas-dev-director.
    """
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    desc = data.get("description", "")
    assert "v1.0.0" in desc, "dev-mas-engineer must be v1.0.0"
    assert "thin delegator" in desc.lower() or "delegator" in desc.lower(), \
        "dev-mas-engineer must declare thin-delegator role"


def test_dev_mas_engineer_references_dev_director():
    with open(RECIPE) as f:
        content = f.read()
    assert "sub_mas-dev-director" in content, \
        "dev-mas-engineer must reference sub_mas-dev-director"
