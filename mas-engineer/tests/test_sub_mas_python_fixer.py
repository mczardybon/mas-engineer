"""
test_sub_mas_python_fixer.py — sanity tests for python-fixer.

python-fixer v1.0.0 is the Python code-fixer (MAS-internal):
Python code repair and patching.
ONLY fixing — NO analysis or validation.

Per R101 EVIDENCE: R01+R09+R10 (action-taker, single-role).
Part of python-repair 3-way split (analyzer+fixer+validator).

Run with:
    python3 -m pytest tests/test_sub_mas_python_fixer.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-python-fixer.yaml"


def test_python_fixer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_python_fixer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_python_fixer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_python_fixer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_python_fixer_role():
    """Spec: MAS-internal: Python code repair and patching."""
    content = RECIPE.read_text()
    assert "Python" in content, \
        "python-fixer must reference Python"
    assert "repair" in content.lower() or "fix" in content.lower() \
        or "FIX" in content or "REPAIR" in content \
        or "PATCH" in content or "patch" in content.lower(), \
        "python-fixer must declare fix role"


def test_python_fixer_only_fixing():
    """Spec: ONLY fixing — NO analysis or validation."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY fix" in flat or "only fix" in flat.lower() \
        or "ONLY fixing" in flat, \
        "python-fixer must declare ONLY-fixing rule"
    assert "NO analysis" in flat or "no analysis" in flat.lower(), \
        "python-fixer must forbid analysis (combined-list)"
    assert "validation" in flat.lower() and "NO" in flat, \
        "python-fixer must forbid validation (combined-list)"


def test_python_fixer_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "python-fixer must be single-role leaf"


def test_python_fixer_settings():
    """Spec: sub-agent settings (timeout=300, max_steps=30, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 300, \
        "python-fixer must have timeout=300"
    assert settings.get("max_steps") == 30, \
        "python-fixer must have max_steps=30"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "python-fixer must use deepseek model"


def test_python_fixer_r01_r09_r10():
    """Spec: R01, R09, R10 (action-taker)."""
    content = RECIPE.read_text()
    assert "R01" in content, "python-fixer must declare R01"
    assert "R09" in content, "python-fixer must declare R09"
    assert "R10" in content, "python-fixer must declare R10"
    assert "CORONASHIELD" in content, \
        "python-fixer must declare CORONASHIELD"


def test_python_fixer_part_of_python_repair():
    """Spec: python-fixer is one of 3 python-repair sub-agents.
    Per R101 EVIDENCE: NN1 split (analyzer+fixer+validator).
    """
    content = RECIPE.read_text()
    assert "fix" in content.lower() or "FIX" in content \
        or "REPAIR" in content, \
        "python-fixer must declare fix scope"
