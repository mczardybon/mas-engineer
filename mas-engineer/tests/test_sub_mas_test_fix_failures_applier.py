"""
test_sub_mas_test_fix_failures_applier.py — sanity tests for test-fix-failures-applier.

test-fix-failures-applier v1.0.0 applies approved patches to
fix e2e test failures. ONLY apply — no design. Single-role leaf.

Per R101 EVIDENCE: has R04 (no general-improver.yaml changes),
no R10 (applier doesn't store YAML).

Run with:
    python3 -m pytest tests/test_sub_mas_test_fix_failures_applier.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-fix-failures-applier.yaml"


def test_applier_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_applier_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_applier_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_applier_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_applier_role():
    """Spec: Applies approved patches for test failures."""
    content = RECIPE.read_text()
    assert "Applies approved patches" in content \
        or "apply approved" in content.lower(), \
        "applier must declare apply-approved-patches role"
    assert "test failures" in content.lower(), \
        "applier must declare test-failures scope"


def test_applier_only_apply():
    """Spec: ONLY apply approved patches — no design."""
    content = RECIPE.read_text()
    assert "ONLY apply approved patches" in content, \
        "applier must declare ONLY-apply rule"
    assert "no design" in content, \
        "applier must forbid design (combined-list)"


def test_applier_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "applier must be single-role leaf"


def test_applier_settings():
    """Spec: sub-agent settings (timeout=300, max_steps=50, temperature=0.3)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 300, \
        "applier must have timeout=300 (sub-agent)"
    assert settings.get("max_steps") == 50, \
        "applier must have max_steps=50 (sub-agent)"
    assert settings.get("temperature") == 0.3, \
        "applier must have temperature=0.3"


def test_applier_r04_no_general_improver():
    """Spec: R04 — Never change general-improver.yaml."""
    content = RECIPE.read_text()
    assert "R04" in content, "applier must declare R04"
    assert "general-improver" in content or "general_improver" in content, \
        "applier must reference general-improver.yaml in R04 context"


def test_applier_safety_features():
    """Spec: backup before apply, validate YAML, rollback on failure."""
    content = RECIPE.read_text()
    assert "backup" in content.lower() or "Backup" in content, \
        "applier must declare backup before apply"
    assert "validate" in content.lower() or "Validate" in content, \
        "applier must declare validate YAML after change"
    assert "rollback" in content.lower() or "Rollback" in content, \
        "applier must declare rollback on failure"
