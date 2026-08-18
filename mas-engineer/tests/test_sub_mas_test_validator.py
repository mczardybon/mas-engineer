"""
test_sub_mas_test_validator.py — sanity tests for test-validator.

test-validator v1.0.0 is a SINGLE-ROLE validator. ONLY validates
test configs and results — NO execution, analysis, or scanning.
Delegates those to specialized test-* sub-agents.

Run with:
    python3 -m pytest tests/test_sub_mas_test_validator.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-validator.yaml"


def test_test_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_test_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_test_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_test_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_test_validator_only_validation():
    """Spec: ONLY validation — NO execution, analysis, or scanning.
    Note: combined-list pattern with em-dash separator.
    """
    content = RECIPE.read_text()
    assert "ONLY validation" in content, \
        "test-validator must declare ONLY-validation rule"
    # Combined-list: "NO execution, analysis, or scanning"
    assert "NO execution" in content and "analysis" in content \
        and "scanning" in content, \
        "test-validator must forbid execution+analysis+scanning"


def test_test_validator_single_role():
    """Spec: SINGLE role — validation only."""
    content = RECIPE.read_text()
    assert "Single role" in content or "single-role" in content, \
        "test-validator must declare single-role pattern"


def test_test_validator_procedure():
    """Spec: 3-step validation procedure."""
    content = RECIPE.read_text()
    for step in ("Receive test config", "Validate against schema",
                 "Return validation"):
        assert step in content, \
            f"test-validator must declare procedure step: {step}"


def test_test_validator_3_forbidden_actions():
    """Spec: 3 forbidden actions — execute, analyze, scan."""
    content = RECIPE.read_text()
    for forbid in ("NEVER execute", "NEVER analyze", "NEVER scan"):
        assert forbid in content, \
            f"test-validator must forbid: {forbid}"


def test_test_validator_no_sub_recipes():
    """Single-role validator — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "test-validator must be a single-role validator (no sub_recipes)"


def test_test_validator_settings():
    """Spec: has settings (timeout, max_turns, goose_provider, model)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert "timeout" in settings, "test-validator must have timeout setting"
    assert "max_turns" in settings, \
        "test-validator must have max_turns setting"
    assert "goose_model" in settings, \
        "test-validator must declare goose_model"
