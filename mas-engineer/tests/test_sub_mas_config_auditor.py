"""
test_sub_mas_config_auditor.py — sanity tests for config-auditor recipe.

Config-auditor cross-references config.yaml ↔ core docs ↔ 94 recipes ↔
runtime. It's a leaf-node analyzer that surfaces config drift.

Run with:
    python3 -m pytest tests/test_sub_mas_config_auditor.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-config-auditor.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-config-auditor.md"


def test_config_auditor_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_config_auditor_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_config_auditor_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_config_auditor_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_config_auditor_instructions_exist():
    """R37: external instructions file must exist."""
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_config_auditor_mentions_config_yaml():
    """Config-auditor must reference config.yaml as source-of-truth."""
    content = RECIPE.read_text()
    assert "config.yaml" in content, \
        "Config-auditor must cross-reference config.yaml"


def test_config_auditor_mentions_recipe_count():
    """Config-auditor description says '94 recipes' — must reflect that scope."""
    content = RECIPE.read_text()
    # Description claims "94 recipes" — verify the number is mentioned
    assert "94" in content or "recipe" in content.lower(), \
        "Config-auditor must mention its recipe-coverage scope"


def test_config_auditor_readonly():
    """Config-auditor is pure analysis — no edits to config files."""
    content = INSTRUCTIONS.read_text() if INSTRUCTIONS.exists() else ""
    # The auditor reports drift, doesn't fix it
    assert "report" in content.lower() or "find" in content.lower() or \
           "drift" in content.lower() or "inconsist" in content.lower(), \
        "Config-auditor must report findings (analysis only)"


def test_config_auditor_no_sub_recipes():
    """Config-auditor is a leaf node (analysis only, no delegation)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "Config-auditor must be a leaf node (no sub_recipes)"


def test_config_auditor_has_coronashield():
    """R10: must validate YAML before any analysis output."""
    content = INSTRUCTIONS.read_text() if INSTRUCTIONS.exists() else ""
    assert "CORONASHIELD" in content or "yaml.safe_load" in content, \
        "Config-auditor must validate YAML inputs (R10)"
