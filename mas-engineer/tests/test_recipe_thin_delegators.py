"""
test_recipe_thin_delegators.py — sanity tests for thin-delegator master recipes.

There are 4 thin-delegator master recipes that follow the same pattern:
- e2e-verify-auto-repair.yaml → sub_mas-e2e-auto-repair-director
- e2e-verify-phoenix-fixes.yaml → sub_mas-e2e-phoenix-fixes-director
- test-fix-failures.yaml → sub_mas-test-fix-failures-director
- test-mas-user.yaml → sub_mas-test-director

Each is a thin delegator (sub_recipes=1) that routes to a director.

Per R101 EVIDENCE: thin delegator pattern (4 recipes as of R110-50;
e2e-verify-german-fixes removed in cleanup of obsoletes).

Run with:
    python3 -m pytest tests/test_recipe_thin_delegators.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()

# Map of (recipe_file, expected_director)
THIN_DELEGATORS = [
    ("e2e-verify-auto-repair.yaml", "sub_mas-e2e-auto-repair-director"),
    ("e2e-verify-phoenix-fixes.yaml", "sub_mas-e2e-phoenix-fixes-director"),
    ("test-fix-failures.yaml", "sub_mas-test-fix-failures-director"),
    ("test-mas-user.yaml", "sub_mas-test-director"),
]


def test_all_thin_delegators_exist():
    for fname, _ in THIN_DELEGATORS:
        path = REPO_ROOT / "recipe" / fname
        assert path.exists(), f"Missing thin-delegator: {path}"


def test_all_thin_delegators_are_valid_yaml():
    for fname, _ in THIN_DELEGATORS:
        path = REPO_ROOT / "recipe" / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{fname} is not a valid YAML dict"


def test_all_thin_delegators_have_one_sub_recipe():
    """Thin delegator = sub_recipes=1 (single director)."""
    for fname, expected_dir in THIN_DELEGATORS:
        path = REPO_ROOT / "recipe" / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        subs = data.get("sub_recipes", [])
        assert len(subs) == 1, \
            f"{fname} must have exactly 1 sub_recipes, has {len(subs)}"


def test_all_thin_delegators_route_to_director():
    """Each thin delegator must route to the expected director."""
    for fname, expected_dir in THIN_DELEGATORS:
        path = REPO_ROOT / "recipe" / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        subs = data.get("sub_recipes", [])
        assert subs[0].get("name") == expected_dir, \
            f"{fname} must delegate to {expected_dir}, " \
            f"got {subs[0].get('name')}"


def test_all_thin_delegators_have_version():
    """Thin delegators should have v1.0.0 in description."""
    for fname, _ in THIN_DELEGATORS:
        path = REPO_ROOT / "recipe" / fname
        with open(path) as f:
            content = f.read()
        assert "v1.0.0" in content or "v1" in content, \
            f"{fname} should declare version"


def test_thin_delegators_declare_thin_delegator():
    """Each thin delegator should declare 'thin delegator' in description."""
    matched = 0
    for fname, _ in THIN_DELEGATORS:
        path = REPO_ROOT / "recipe" / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        desc = data.get("description", "")
        if "thin delegator" in desc.lower() or "delegator" in desc.lower():
            matched += 1
    assert matched >= 3, \
        f"At least 3 thin delegators should declare 'thin delegator', " \
        f"matched {matched}"


def test_thin_delegator_count():
    """Spec: 4 thin-delegator master recipes (after R110-50 cleanup)."""
    assert len(THIN_DELEGATORS) == 4, \
        f"Expected 4 thin delegators, got {len(THIN_DELEGATORS)}"
