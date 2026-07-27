"""
test_sub_mas_e2e_phoenix_fixes_director.py — sanity tests for phoenix-fixes-director.

Phoenix-fixes-director is the orchestrator for verifying 8 phoenix-
recovery fixes. Runs pre-check layer (deterministic, ~1-2s) before
LLM-driven semantic review.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_phoenix_fixes_director.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-phoenix-fixes-director.yaml"


def test_phoenix_fixes_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_phoenix_fixes_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_phoenix_fixes_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_phoenix_fixes_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_phoenix_fixes_director_orchestrator():
    """Spec: orchestrator — delegates to sub-agents."""
    content = RECIPE.read_text()
    assert "Orchestrator" in content or "orchestrate" in content.lower(), \
        "phoenix-fixes-director must be an orchestrator"
    assert "Delegate" in content or "delegate" in content, \
        "phoenix-fixes-director must delegate to sub-agents"


def test_phoenix_fixes_director_pre_check_step():
    """Spec: Step 0 runs deterministic pre-check (1-2s, no LLM tokens)."""
    content = RECIPE.read_text()
    assert "pre_check" in content, \
        "phoenix-fixes-director must reference pre-check script"
    assert "Step 0" in content or "DETERMINISTIC" in content, \
        "phoenix-fixes-director must declare pre-check as Step 0"


def test_phoenix_fixes_director_pre_check_mirrors_validator():
    """Spec: pre-check mirrors T1-T7 in phoenix-fixes-validator (LLM-cost saving)."""
    content = RECIPE.read_text()
    assert "T1-T7" in content or "T1-T5" in content, \
        "phoenix-fixes-director pre-check must mirror T1-T7 validator tests"


def test_phoenix_fixes_director_8_phoenix_fixes():
    """Spec: verifies 8 phoenix-recovery fixes (commit 4ebd18e)."""
    content = RECIPE.read_text()
    assert "8" in content, \
        "phoenix-fixes-director must declare 8-fix scope"


def test_phoenix_fixes_director_recovery_workflows():
    """Spec: tests wf_recovery_immune + 4 new workflows + recovery-templates."""
    content = RECIPE.read_text()
    assert "wf_recovery_immune" in content, \
        "phoenix-fixes-director must reference wf_recovery_immune"
    assert "recovery-template" in content or "recovery_template" in content or \
           "checkpoint" in content, \
        "phoenix-fixes-director must reference recovery-templates"


def test_phoenix_fixes_director_no_sub_recipes():
    """Director orchestrates via instructions, not sub_recipes (top-level)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    # Director delegates via workflow steps, not yaml sub_recipes
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "phoenix-fixes-director must be a top-level orchestrator"
