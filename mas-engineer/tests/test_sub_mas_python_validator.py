"""
test_sub_mas_python_validator.py — sanity tests for python-validator.

python-validator v1.0.0 is the Python code-validator (MAS-internal):
Python code validation and verification.
ONLY validation — NO analysis or fixing.

Per R101 EVIDENCE: R01+R09+R10 (action-taker, single-role).
Part of python-repair 3-way split (analyzer+fixer+validator).

Run with:
    python3 -m pytest tests/test_sub_mas_python_validator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-python-validator.yaml"


def test_python_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_python_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_python_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_python_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_python_validator_role():
    """Spec: MAS-internal: Python code validation and verification."""
    content = RECIPE.read_text()
    assert "Python" in content, \
        "python-validator must reference Python"
    assert "validation" in content.lower() or "Verification" in content \
        or "VALIDATION" in content.upper() \
        or "verify" in content.lower(), \
        "python-validator must declare validation role"


def test_python_validator_only_validation():
    """Spec: ONLY validation — NO analysis or fixing."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY validation" in flat or "only validation" in flat.lower(), \
        "python-validator must declare ONLY-validation rule"
    assert "NO analysis" in flat or "no analysis" in flat.lower(), \
        "python-validator must forbid analysis (combined-list)"
    assert "fix" in flat.lower() and "NO" in flat, \
        "python-validator must forbid fixing (combined-list)"


def test_python_validator_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "python-validator must be single-role leaf"


def test_python_validator_settings():
    """Spec: sub-agent settings (timeout=300, max_turns=30, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 300, \
        "python-validator must have timeout=300"
    assert settings.get("max_turns") == 30, \
        "python-validator must have max_turns=30"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "python-validator must use deepseek model"


def test_python_validator_r01_r09_r10():
    """Spec: R01, R09, R10 (action-taker)."""
    content = RECIPE.read_text()
    assert "R01" in content, "python-validator must declare R01"
    assert "R09" in content, "python-validator must declare R09"
    assert "R10" in content, "python-validator must declare R10"
    assert "CORONASHIELD" in content, \
        "python-validator must declare CORONASHIELD"


def test_python_validator_part_of_python_repair():
    """Spec: python-validator is one of 3 python-repair sub-agents.
    Per R101 EVIDENCE: NN1 split (analyzer+fixer+validator).
    """
    content = RECIPE.read_text()
    assert "validate" in content.lower() or "VALIDATE" in content \
        or "validation" in content.lower(), \
        "python-validator must declare validation scope"
