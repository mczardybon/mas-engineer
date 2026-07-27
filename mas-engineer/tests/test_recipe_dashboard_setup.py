"""
test_recipe_dashboard_setup.py — sanity tests for setup-dashboard.yaml
and dashboard-data-refresh.yaml.

setup-dashboard.yaml: Sets up the MCP App Dashboard. Execute once
after init: npm install, Extension, etc.
dashboard-data-refresh.yaml: Updated all 5 Minuten die Dashboard-Data.
Liest guardian.yaml, changes.json, etc.

These are setup/data-refresh recipes, NOT thin delegators.

Per R101 EVIDENCE: setup recipes (no sub_recipes, no R-rules needed).

Run with:
    python3 -m pytest tests/test_recipe_dashboard_setup.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()

SETUP_RECIPES = [
    "setup-dashboard.yaml",
    "dashboard-data-refresh.yaml",
]


def test_all_setup_recipes_exist():
    for fname in SETUP_RECIPES:
        path = REPO_ROOT / "recipe" / fname
        assert path.exists(), f"Missing setup recipe: {path}"


def test_all_setup_recipes_valid_yaml():
    for fname in SETUP_RECIPES:
        path = REPO_ROOT / "recipe" / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{fname} is not a valid YAML dict"


def test_setup_dashboard_role():
    """Spec: Sets up the MCP App Dashboard. Execute once after init:
    npm install, Extension, etc.
    """
    path = REPO_ROOT / "recipe" / "setup-dashboard.yaml"
    content = path.read_text()
    assert "Dashboard" in content or "dashboard" in content, \
        "setup-dashboard must reference Dashboard"
    assert "init" in content.lower() or "Init" in content \
        or "setup" in content.lower() or "Setup" in content, \
        "setup-dashboard must declare setup/init role"
    # Should mention npm install OR extension
    assert "npm" in content.lower() or "install" in content.lower() \
        or "Extension" in content, \
        "setup-dashboard must mention install steps"


def test_dashboard_data_refresh_role():
    """Spec: Updated all 5 Minuten die Dashboard-Data. Liest guardian.yaml,
    changes.json.
    """
    path = REPO_ROOT / "recipe" / "dashboard-data-refresh.yaml"
    content = path.read_text()
    assert "Dashboard" in content or "dashboard" in content, \
        "dashboard-data-refresh must reference Dashboard"
    assert "5 Min" in content or "5 min" in content \
        or "5min" in content or "5minut" in content.lower() \
        or "interval" in content.lower() \
        or "Interval" in content, \
        "dashboard-data-refresh must declare 5-minute interval"
    assert "guardian" in content.lower() or "Guardian" in content, \
        "dashboard-data-refresh must reference guardian.yaml"


def test_setup_recipes_no_thin_delegator_sub_recipes():
    """Setup recipes should not be thin delegators (sub_recipes=0)."""
    for fname in SETUP_RECIPES:
        path = REPO_ROOT / "recipe" / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        subs = data.get("sub_recipes", [])
        # Either no subs, or subs > 1 (not a thin delegator)
        assert len(subs) != 1, \
            f"{fname} should not be a thin delegator (1 sub_recipes)"


def test_setup_recipes_have_description():
    """Setup recipes should have description."""
    for fname in SETUP_RECIPES:
        path = REPO_ROOT / "recipe" / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "description" in data, \
            f"{fname} must have description"
