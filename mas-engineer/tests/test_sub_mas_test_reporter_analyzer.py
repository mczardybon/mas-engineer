"""
test_sub_mas_test_reporter_analyzer.py — sanity tests for test-reporter-analyzer.

test-reporter-analyzer v1.0.0 is the analyzer (MAS-internal):
analyzes test results and identifies root causes and patterns.
Single-role leaf.

Per R101 EVIDENCE: test-reporter-analyzer has 0 R-number rules
(delegate-to-constitution pattern, like test-executor and
framework-auditor).

Run with:
    python3 -m pytest tests/test_sub_mas_test_reporter_analyzer.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-reporter-analyzer.yaml"


def test_reporter_analyzer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_reporter_analyzer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_reporter_analyzer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_reporter_analyzer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_reporter_analyzer_role():
    """Spec: Analyzes test results, identifies root causes and patterns."""
    content = RECIPE.read_text()
    assert "Analyzes" in content or "analyzes" in content, \
        "test-reporter-analyzer must declare analysis role"
    assert "root cause" in content.lower() or "root-cause" in content.lower(), \
        "test-reporter-analyzer must declare root-cause identification"
    assert "pattern" in content.lower(), \
        "test-reporter-analyzer must declare pattern identification"
    assert "single role" in content.lower() or "Single role" in content, \
        "test-reporter-analyzer must declare single-role scope"


def test_reporter_analyzer_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "test-reporter-analyzer must be single-role leaf"


def test_reporter_analyzer_settings():
    """Spec: standard settings (timeout=600, max_turns=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "test-reporter-analyzer must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "test-reporter-analyzer must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "test-reporter-analyzer must use deepseek model"


def test_reporter_analyzer_only_analysis():
    """Spec: ONLY analyzes (no other role)."""
    content = RECIPE.read_text()
    assert "ONLY" in content, \
        "test-reporter-analyzer must declare ONLY rule"
    # Check for negative rules (forbid other roles)
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("NO ") >= 1, \
        "test-reporter-analyzer must have at least one NO- rule"


def test_reporter_analyzer_no_r_rules():
    """Spec: test-reporter-analyzer has 0 R-number rules.
    Per R101 EVIDENCE: minimal recipe, delegates all rules
    to master-constitution.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R0") == 0, \
        f"test-reporter-analyzer must not restate R-rules. Found: {flat.count('R0')}"


def test_reporter_analyzer_mas_internal():
    """Spec: MAS-internal scope (not user-facing)."""
    content = RECIPE.read_text()
    assert "MAS-internal" in content, \
        "test-reporter-analyzer must declare MAS-internal scope"
