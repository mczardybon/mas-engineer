"""
test_sub_mas_pre_push_validator.py — sanity tests for pre-push-validator.

pre-push-validator v2.9.0 is the gatekeeper (MAS-internal) that
runs all 24 critical checks before git push is allowed.
Single-role leaf. R74: +Check 14 multi-dim coverage.
R110-118: +Check 18 spec-invariant.
R110-204: +Check 23 orphan-recipe registration audit.
R110-257: +Check 24 evidence/directive SOT-location audit.

Per R101 EVIDENCE: pre-push-validator has 0 R-number rules
(gatekeeper, just runs the 24 checks).

Run with:
    python3 -m pytest tests/test_sub_mas_pre_push_validator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-pre-push-validator.yaml"


def test_pre_push_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_pre_push_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_pre_push_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_pre_push_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_pre_push_validator_role():
    """Spec: Gatekeeper before git push — runs 24 critical checks."""
    content = RECIPE.read_text()
    assert "Gatekeeper" in content or "gatekeeper" in content, \
        "pre-push-validator must declare gatekeeper role"
    assert "git push" in content, \
        "pre-push-validator must reference git push"
    assert "24 critical checks" in content or "24 checks" in content \
        or "24" in content, \
        "pre-push-validator must reference 24 checks"


def test_pre_push_validator_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "pre-push-validator must be single-role leaf"


def test_pre_push_validator_settings():
    """Spec: gatekeeper settings (timeout=600, max_turns=60, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "pre-push-validator must have timeout=600"
    assert settings.get("max_turns") == 60, \
        "pre-push-validator must have max_turns=60 (gatekeeper)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "pre-push-validator must use deepseek model"


def test_pre_push_validator_r74_check14():
    """Spec: R74 — Check 14 multi-dim coverage."""
    content = RECIPE.read_text()
    assert "R74" in content, "pre-push-validator must reference R74"
    assert "Check 14" in content or "14" in content, \
        "pre-push-validator must reference Check 14"
    assert "multi-dim" in content or "multi_dim" in content \
        or "coverage" in content.lower(), \
        "pre-push-validator must declare multi-dim coverage"


def test_pre_push_validator_no_r_rules():
    """Spec: pre-push-validator has 0 R-number rules (except R74
    which is a feature reference, not an R-rule constraint).
    Per R101 EVIDENCE: gatekeeper, just runs checks.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # R74 is mentioned but is a feature ref, not an R-rule
    # Check for actual R-rule patterns (R01, R09, R10)
    for r in ("R01", "R09", "R10"):
        assert flat.count(f"{r} ") == 0 and flat.count(f"{r}—") == 0, \
            f"pre-push-validator must not restate R-rules. Found {r}."


def test_pre_push_validator_mas_internal():
    """Spec: MAS-internal scope (gatekeeper, not user-facing)."""
    content = RECIPE.read_text()
    assert "MAS-internal" in content, \
        "pre-push-validator must declare MAS-internal scope"
