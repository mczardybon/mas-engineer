"""
test_sub_mas_dashboard_generator.py — sanity tests for dashboard-generator.

dashboard-generator v2.0.0 is a script-wrapper recipe:
Generates and renders the project dashboard. Delegates to
tools/dev_dashboard_refresh.py. This recipe is a thin wrapper.

Per R101 EVIDENCE: R01+R09+R10 (script-wrapper with YAML output).

Run with:
    python3 -m pytest tests/test_sub_mas_dashboard_generator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dashboard-generator.yaml"


def test_generator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_generator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_generator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_generator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_generator_role():
    """Spec: MAS-internal: Generates and renders the project dashboard."""
    content = RECIPE.read_text()
    assert "Generates" in content or "GENERATION" in content.upper() \
        or "generation" in content.lower(), \
        "generator must declare generation role"
    assert "dashboard" in content.lower(), \
        "generator must declare dashboard scope"
    assert "renders" in content.lower() or "render" in content.lower(), \
        "generator must declare render capability"


def test_generator_only_generation():
    """Spec: ONLY generation — NO data collection or editing."""
    content = RECIPE.read_text()
    assert "ONLY generation" in content, \
        "generator must declare ONLY-generation rule"
    assert "NO data collection" in content \
        or "no data collection" in content.lower(), \
        "generator must forbid data collection (combined-list)"
    assert "editing" in content.lower() or "NO editing" in content, \
        "generator must forbid editing (combined-list)"


def test_generator_delegates_to_dev_dashboard_refresh():
    """Spec: delegates to tools/dev_dashboard_refresh.py."""
    content = RECIPE.read_text()
    assert "dev_dashboard_refresh" in content, \
        "generator must reference dev_dashboard_refresh tool"


def test_generator_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "generator must be single-role leaf"


def test_generator_settings():
    """Spec: code-review settings (timeout=120, max_steps=15, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "generator must have timeout=120 (script-wrapper)"
    assert settings.get("max_steps") == 15, \
        "generator must have max_steps=15 (script-wrapper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "generator must use deepseek model"


def test_generator_r01_r09_r10():
    """Spec: R01, R09, R10 (script-wrapper with YAML output)."""
    content = RECIPE.read_text()
    assert "R01" in content, "generator must declare R01"
    assert "R09" in content, "generator must declare R09"
    assert "R10" in content, "generator must declare R10"
    assert "CORONASHIELD" in content, \
        "generator must declare CORONASHIELD"


def test_generator_differs_from_data_reader():
    """Spec: generator and data-reader are both script-wrappers
    but generator uses dev_dashboard_refresh while data-reader
    uses dev_dashboard_data.
    Per R101 EVIDENCE: this distinguishes them.
    """
    content = RECIPE.read_text()
    assert "dev_dashboard_refresh" in content, \
        "generator must use dev_dashboard_refresh (NOT data)"
    assert "dev_dashboard_data" not in content, \
        "generator must NOT use dev_dashboard_data (data-reader's tool)"
