"""
test_sub_mas_framework_hardener.py — sanity tests for framework-hardener.

framework-hardener v1.0.0 hardens and secures framework
configuration and structure. R01 confirmation required.
ONLY hardening and securing.

Per R101 EVIDENCE: framework-hardener has only R01 (no R04/R05/
R09/R10). It's the action-taker (vs harden-agent which only
checks).

Run with:
    python3 -m pytest tests/test_sub_mas_framework_hardener.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-hardener.yaml"


def test_framework_hardener_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_hardener_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_hardener_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_hardener_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_hardener_only_hardening():
    """Spec: ONLY framework hardening and securing."""
    content = RECIPE.read_text()
    assert "ONLY framework hardening" in content, \
        "framework-hardener must declare ONLY-hardening rule"
    assert "securing" in content or "secure" in content.lower(), \
        "framework-hardener must declare securing role"


def test_framework_hardener_r01_confirmation():
    """Spec: R01 confirmation required (action-taker)."""
    content = RECIPE.read_text()
    assert "R01" in content, "framework-hardener must declare R01"
    assert "confirmation" in content.lower(), \
        "framework-hardener must require confirmation"


def test_framework_hardener_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "framework-hardener must be single-role leaf"


def test_framework_hardener_settings():
    """Spec: standard settings (timeout=600, max_steps=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "framework-hardener must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "framework-hardener must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "framework-hardener must use deepseek model"


def test_framework_hardener_action_taker():
    """Spec: action-taker (vs harden-agent which only checks).
    Per R101 EVIDENCE: prompt says "Harden framework configs" (verb)
    and R01 confirmation (not just results).
    """
    content = RECIPE.read_text()
    assert "Harden framework configs" in content \
        or "harden framework" in content.lower(), \
        "framework-hardener must take hardening action (verb)"


def test_framework_hardener_no_coronashield():
    """Spec: framework-hardener has NO R10/CORONASHIELD
    (R10 is for pre-storage YAML validation, not for action agents).
    Per R101 EVIDENCE: R10/CORONASHIELD absent from this recipe.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") == 0, \
        "framework-hardener must NOT have R10 (action-taker, not storage)"
    assert flat.count("CORONASHIELD") == 0, \
        "framework-hardener must NOT have CORONASHIELD"
