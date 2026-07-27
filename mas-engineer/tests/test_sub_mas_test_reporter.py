"""
test_sub_mas_test_reporter.py — sanity tests for test-reporter.

test-reporter v1.0.0 is the test reporter (MAS-internal):
analyzes test results and generates reports. Single-role
leaf. R01+R09+R10.

Run with:
    python3 -m pytest tests/test_sub_mas_test_reporter.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-reporter.yaml"


def test_reporter_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_reporter_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_reporter_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_reporter_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_reporter_role():
    """Spec: Analyzes test results and generates reports."""
    content = RECIPE.read_text()
    assert "Analyzes" in content or "analyzes" in content, \
        "test-reporter must declare analysis role"
    assert "generates reports" in content or "generates" in content.lower() \
        or "report" in content.lower(), \
        "test-reporter must declare report generation"
    assert "MAS-internal" in content, \
        "test-reporter must declare MAS-internal scope"


def test_reporter_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "test-reporter must be single-role leaf"


def test_reporter_settings():
    """Spec: standard settings (timeout=600, max_steps=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "test-reporter must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "test-reporter must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "test-reporter must use deepseek model"


def test_reporter_only_reporting():
    """Spec: ONLY reports (no other role)."""
    content = RECIPE.read_text()
    assert "ONLY" in content, \
        "test-reporter must declare ONLY rule"
    # Check for negative rules (forbid other roles)
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("NO ") >= 1, \
        "test-reporter must have at least one NO- rule"


def test_reporter_r01_r09_r10():
    """Spec: R01, R09, R10 (per R101 EVIDENCE — full pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "test-reporter must declare R01"
    assert "R09" in content, "test-reporter must declare R09"
    assert "R10" in content, "test-reporter must declare R10"
    assert "CORONASHIELD" in content, \
        "test-reporter must declare CORONASHIELD"


def test_reporter_no_test_execution():
    """Spec: test-reporter does NOT execute tests (only analyzes)."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Should forbid direct execution
    assert "NO direct test execution" in flat \
        or "NO test execution" in flat, \
        "test-reporter must forbid direct test execution"
