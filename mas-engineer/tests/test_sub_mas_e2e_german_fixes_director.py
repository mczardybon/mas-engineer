"""
test_sub_mas_e2e_german_fixes_director.py — sanity tests for german-fixes-director.

German-fixes-director orchestrates e2e verification of German descs +
placeholder fixes. Same pre-check pattern as the other e2e directors.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_german_fixes_director.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-german-fixes-director.yaml"


def test_german_fixes_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_german_fixes_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_german_fixes_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_german_fixes_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_german_fixes_director_orchestrator():
    """Spec: orchestrator — delegates to sub-agents."""
    content = RECIPE.read_text()
    assert "Orchestrator" in content or "orchestrate" in content.lower(), \
        "german-fixes-director must be an orchestrator"
    assert "Delegate" in content or "delegate" in content, \
        "german-fixes-director must delegate to sub-agents"


def test_german_fixes_director_pre_check():
    """Spec: Step 0 — pre-check (deterministic, ~0.5s, no LLM tokens)."""
    content = RECIPE.read_text()
    assert "pre_check" in content or "pre-check" in content, \
        "german-fixes-director must reference pre-check"
    assert "DETERMINISTIC" in content or "deterministic" in content, \
        "german-fixes-director must declare deterministic pre-check"


def test_german_fixes_director_2_pass_pre_check():
    """Spec: pre-check expects 2/2 PASS for T1-T2 mirror."""
    content = RECIPE.read_text()
    assert "2/2" in content, \
        "german-fixes-director pre-check must declare 2/2 PASS threshold"


def test_german_fixes_director_delegates_via_sub_recipes():
    """Spec: delegates T1-T2 to validator + T3 to runner via sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-e2e-german-fixes-validator" in subs, \
        f"german-fixes-director must delegate to validator. subs: {subs}"
    assert "sub_mas-e2e-german-fixes-runner" in subs, \
        f"german-fixes-director must delegate to runner. subs: {subs}"


def test_german_fixes_director_no_modifications():
    """Spec: orchestrator only — no direct file modifications."""
    content = RECIPE.read_text()
    assert "no direct" in content.lower() or "delegate" in content, \
        "german-fixes-director must not modify files directly"


def test_german_fixes_director_settings():
    """Spec: standard orchestrator settings (timeout, max_steps, temp)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert "timeout" in settings, "german-fixes-director must have timeout"
    assert "max_steps" in settings, "german-fixes-director must have max_steps"
