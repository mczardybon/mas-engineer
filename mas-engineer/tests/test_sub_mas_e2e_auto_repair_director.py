"""
test_sub_mas_e2e_auto_repair_director.py — sanity tests for auto-repair-director.

Auto-repair-director orchestrates verification of the auto_repair step
(step 4) added to 4 recovery workflows. Same pre-check pattern as
phoenix-fixes-director.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_auto_repair_director.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-auto-repair-director.yaml"


def test_auto_repair_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_auto_repair_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_auto_repair_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_auto_repair_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_auto_repair_director_orchestrator():
    """Spec: orchestrator — delegates to validator."""
    content = RECIPE.read_text()
    assert "Orchestrator" in content or "orchestrate" in content.lower(), \
        "auto-repair-director must be an orchestrator"
    assert "sub_mas-e2e-auto-repair-validator" in content, \
        "auto-repair-director must delegate to sub_mas-e2e-auto-repair-validator"


def test_auto_repair_director_pre_check():
    """Spec: Step 0 — pre-check (deterministic, ~0.3s, no LLM tokens)."""
    content = RECIPE.read_text()
    assert "pre_check" in content, \
        "auto-repair-director must reference pre-check"
    assert "DETERMINISTIC" in content or "deterministic" in content, \
        "auto-repair-director must declare deterministic pre-check"


def test_auto_repair_director_delegates_to_subs():
    """Spec: director delegates to validator + runner via sub_recipes.

    Unlike phoenix-fixes-director (which uses workflow steps), the
    auto-repair-director uses explicit sub_recipes for delegation.
    """
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-e2e-auto-repair-validator" in subs, \
        f"auto-repair-director must delegate to validator. subs: {subs}"
    assert "sub_mas-e2e-auto-repair-runner" in subs, \
        f"auto-repair-director must delegate to runner. subs: {subs}"


def test_auto_repair_director_pre_check_8_pass():
    """Spec: pre-check reports 8/8 PASS when auto_repair steps are correct."""
    content = RECIPE.read_text()
    assert "8/8" in content, \
        "auto-repair-director pre-check must declare 8/8 PASS threshold"


def test_auto_repair_director_has_sub_recipes():
    """Spec: director delegates via sub_recipes (not workflow steps).

    Contrasts with phoenix-fixes-director which delegates via workflow
    steps (no sub_recipes). Both are valid orchestrator patterns.
    """
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = data.get("sub_recipes", [])
    assert subs, "auto-repair-director must have sub_recipes (validator + runner)"


def test_auto_repair_director_step_4_target():
    """Spec: auto_repair is at step 4 across all recovery workflows."""
    content = RECIPE.read_text()
    assert "step 4" in content or "Step 4" in content, \
        "auto-repair-director must declare step 4 as target position"
