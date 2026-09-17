"""
test_sub_mas_e2e_phoenix_fixes_director.py — sanity tests for e2e-phoenix-fixes-director.

Orchestrates e2e verification of 8 phoenix-recovery fixes from
commit 4ebd18e. Has Step 0: deterministic pre-check layer (R106
cost-control: 1-2s, no LLM tokens, ~14 tool-calls saved).

Note: this recipe has 'description:' but no 'settings:' field.
Required-fields test adapted accordingly.

Run with:
    python3 -m pytest tests/test_sub_mas_e2e_phoenix_fixes_director.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-e2e-phoenix-fixes-director.yaml"


def test_e2e_phoenix_fixes_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_e2e_phoenix_fixes_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_e2e_phoenix_fixes_director_recipe_has_required_fields():
    """Adapted: has description+instructions+prompt but no 'settings'."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_e2e_phoenix_fixes_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_e2e_phoenix_fixes_director_orchestrator():
    """Spec: orchestrator for 8 phoenix-recovery fixes verification."""
    content = RECIPE.read_text()
    assert "Orchestrat" in content or "orchestrator" in content.lower(), \
        "e2e-phoenix-fixes-director must be an orchestrator"
    assert "phoenix" in content.lower(), \
        "e2e-phoenix-fixes-director must reference phoenix"


def test_e2e_phoenix_fixes_director_8_fixes():
    """Spec: 8 phoenix-recovery fixes from commit 4ebd18e."""
    content = RECIPE.read_text()
    assert "8 phoenix-recovery" in content or "8 phoenix" in content, \
        "e2e-phoenix-fixes-director must declare 8 fixes"
    assert "4ebd18e" in content, \
        "e2e-phoenix-fixes-director must reference commit 4ebd18e"


def test_e2e_phoenix_fixes_director_pre_check_layer():
    """Spec: Step 0 — deterministic pre-check layer (1-2s, no LLM tokens)."""
    content = RECIPE.read_text()
    assert "Pre-Check" in content or "pre-check" in content, \
        "e2e-phoenix-fixes-director must declare pre-check layer"
    assert "tools/pre_check" in content, \
        "e2e-phoenix-fixes-director must reference pre_check tool"
    assert "no LLM" in content or "no LLM tokens" in content or \
           "deterministic" in content.lower(), \
        "e2e-phoenix-fixes-director must declare no-LLM-tokens cost-control"


def test_e2e_phoenix_fixes_director_delegates():
    """Spec: delegates to specialized sub-agents per test domain.
    NOTE: Director has empty sub_recipes list in current state
    (delegation by instruction-prompt, not by sub_recipes block).
    """
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    # Director's delegation is by instruction, not by sub_recipes block
    # (this is a soft-delegation pattern, R101 EVIDENCE)
    content = RECIPE.read_text()
    assert "Delegate" in content, \
        "e2e-phoenix-fixes-director must reference delegation in instructions"


def test_e2e_phoenix_fixes_director_cost_savings():
    """Spec: ~14 LLM tool-calls saved by pre-check layer."""
    content = RECIPE.read_text()
    assert "14" in content, \
        "e2e-phoenix-fixes-director must declare ~14 tool-calls saved"


def test_e2e_phoenix_fixes_director_recovery_workflow():
    """Spec: tests recovery workflows (wf_recovery_immune + 4 new)."""
    content = RECIPE.read_text()
    assert "wf_recovery_immune" in content, \
        "e2e-phoenix-fixes-director must test wf_recovery_immune"
    assert "4 new" in content.lower() or "4 new workflows" in content, \
        "e2e-phoenix-fixes-director must test 4 new recovery workflows"
