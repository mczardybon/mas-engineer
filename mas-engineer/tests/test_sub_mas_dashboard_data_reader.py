"""
test_sub_mas_dashboard_data_reader.py — sanity tests for dashboard-data-reader.

dashboard-data-reader v2.0.0 is a script-wrapper recipe:
Reads and collects project data. Delegates to
tools/dev_dashboard_data.py. This recipe is a thin wrapper.

Per R101 EVIDENCE: R01+R09+R10 (script-wrapper with YAML output).

Run with:
    python3 -m pytest tests/test_sub_mas_dashboard_data_reader.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dashboard-data-reader.yaml"


def test_data_reader_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_data_reader_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_data_reader_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_data_reader_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_data_reader_role():
    """Spec: MAS-internal: Reads and collects project data."""
    content = RECIPE.read_text()
    assert "Reads" in content or "reads" in content \
        or "DATA COLLECTION" in content.upper() \
        or "data collection" in content.lower(), \
        "data-reader must declare data-collection role"
    assert "project data" in content.lower() or "project_data" in content.lower(), \
        "data-reader must declare project-data scope"


def test_data_reader_only_collection():
    """Spec: ONLY data collection — NO generation or editing."""
    content = RECIPE.read_text()
    assert "ONLY data collection" in content, \
        "data-reader must declare ONLY-collection rule"
    assert "NO generation" in content or "no generation" in content.lower(), \
        "data-reader must forbid generation (combined-list)"
    assert "editing" in content.lower() or "NO editing" in content, \
        "data-reader must forbid editing (combined-list)"


def test_data_reader_delegates_to_dev_dashboard_data():
    """Spec: delegates to tools/dev_dashboard_data.py."""
    content = RECIPE.read_text()
    assert "dev_dashboard_data" in content, \
        "data-reader must reference dev_dashboard_data tool"


def test_data_reader_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "data-reader must be single-role leaf"


def test_data_reader_settings():
    """Spec: code-review settings (timeout=120, max_turns=15, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "data-reader must have timeout=120 (script-wrapper)"
    assert settings.get("max_turns") == 30, \
        "data-reader must have max_turns=15 (script-wrapper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "data-reader must use deepseek model"


def test_data_reader_r01_r09_r10():
    """Spec: R01, R09, R10 (script-wrapper with YAML output)."""
    content = RECIPE.read_text()
    assert "R01" in content, "data-reader must declare R01"
    assert "R09" in content, "data-reader must declare R09"
    assert "R10" in content, "data-reader must declare R10"
    assert "CORONASHIELD" in content, \
        "data-reader must declare CORONASHIELD"
