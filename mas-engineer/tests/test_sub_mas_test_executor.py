"""
test_sub_mas_test_executor.py — sanity tests for test-executor.

test-executor v1.0.0 is the test executioner (MAS-internal):
executes tests and verifies results. Single-role leaf.

Per R101 EVIDENCE: test-executor has 0 R-number rules
(delegate-to-constitution pattern, like framework-auditor).

Run with:
    python3 -m pytest tests/test_sub_mas_test_executor.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-executor.yaml"


def test_executor_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_executor_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_executor_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_executor_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_executor_role():
    """Spec: Executes tests and verifies results (single role)."""
    content = RECIPE.read_text()
    assert "Executes tests" in content, \
        "test-executor must declare execution role"
    assert "verifies results" in content or "verify" in content.lower(), \
        "test-executor must declare verification role"
    assert "single role" in content.lower() or "Single role" in content, \
        "test-executor must declare single-role scope"


def test_executor_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "test-executor must be single-role leaf"


def test_executor_settings():
    """Spec: standard settings (timeout=600, max_turns=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "test-executor must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "test-executor must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "test-executor must use deepseek model"


def test_executor_only_execution():
    """Spec: ONLY executes tests (no other role)."""
    content = RECIPE.read_text()
    assert "ONLY" in content, \
        "test-executor must declare ONLY rule"
    # Check for negative rules (forbid other roles)
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("NO ") >= 1, \
        "test-executor must have at least one NO- rule"


def test_executor_no_r_rules():
    """Spec: test-executor has 0 R-number rules.
    Per R101 EVIDENCE: minimal recipe, delegates all rules
    to master-constitution.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R0") == 0, \
        f"test-executor must not restate R-rules. Found: {flat.count('R0')}"


def test_executor_mas_internal():
    """Spec: MAS-internal scope (not user-facing)."""
    content = RECIPE.read_text()
    assert "MAS-internal" in content, \
        "test-executor must declare MAS-internal scope"
