"""
test_sub_mas_python_analyzer.py — sanity tests for python-analyzer.

python-analyzer v1.0.0 is the Python code-analyzer (MAS-internal):
Python code syntax check and structure analysis.
ONLY analysis — NO fixing or validation.

Per R101 EVIDENCE: R01+R09+R10 (action-taker, single-role).

Run with:
    python3 -m pytest tests/test_sub_mas_python_analyzer.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-python-analyzer.yaml"


def test_python_analyzer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_python_analyzer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_python_analyzer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_python_analyzer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_python_analyzer_role():
    """Spec: MAS-internal: Python code syntax check and structure analysis."""
    content = RECIPE.read_text()
    assert "Python" in content, \
        "python-analyzer must reference Python"
    assert "syntax" in content.lower() or "analysis" in content.lower() \
        or "ANALYSIS" in content.upper(), \
        "python-analyzer must declare analysis role"
    assert "structure" in content.lower() or "Structure" in content \
        or "STRUCTURE" in content.upper(), \
        "python-analyzer must declare structure scope"


def test_python_analyzer_only_analysis():
    """Spec: ONLY analysis — NO fixing or validation."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY Python code analysis" in flat \
        or "only python code analysis" in flat.lower() \
        or "ONLY analysis" in flat \
        or "ONLY Analysis" in flat, \
        "python-analyzer must declare ONLY-analysis rule"
    assert "NO fixing" in flat or "no fixing" in flat.lower(), \
        "python-analyzer must forbid fixing (combined-list)"
    assert "validation" in flat.lower() or "NO validation" in flat \
        or "no validation" in flat.lower(), \
        "python-analyzer must forbid validation (combined-list)"


def test_python_analyzer_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "python-analyzer must be single-role leaf"


def test_python_analyzer_settings():
    """Spec: sub-agent settings (timeout=300, max_turns=30, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 300, \
        "python-analyzer must have timeout=300"
    assert settings.get("max_turns") == 30, \
        "python-analyzer must have max_turns=30"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "python-analyzer must use deepseek model"


def test_python_analyzer_r01_r09_r10():
    """Spec: R01, R09, R10 (action-taker)."""
    content = RECIPE.read_text()
    assert "R01" in content, "python-analyzer must declare R01"
    assert "R09" in content, "python-analyzer must declare R09"
    assert "R10" in content, "python-analyzer must declare R10"
    assert "CORONASHIELD" in content, \
        "python-analyzer must declare CORONASHIELD"


def test_python_analyzer_returns_results():
    """Spec: Returns results — doesn't modify Python files."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "return results" in flat.lower() \
        or "return" in flat.lower() and "result" in flat.lower(), \
        "python-analyzer must declare return-results behavior"
