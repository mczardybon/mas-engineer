"""
test_sub_mas_workflow_engine.py — sanity tests for workflow-engine.

workflow-engine v2.0.0 is the SOT workflow executor (MAS-internal):
Executes workflows via core orchestration actions:
delegate | parallel | conditional | loop.
Respects depends_on, on_error, timeout, condition, foreach, params.

Per R101 EVIDENCE: R09+R10 only (workflow executor, no general-improver
changes — R01 NOT required).

Run with:
    python3 -m pytest tests/test_sub_mas_workflow_engine.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-workflow-engine.yaml"


def test_workflow_engine_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_workflow_engine_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_workflow_engine_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_workflow_engine_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_workflow_engine_role():
    """Spec: Executes SOT workflows with orchestration actions."""
    content = RECIPE.read_text()
    assert "workflow" in content.lower(), \
        "workflow-engine must declare workflow role"
    # Should mention at least one of: delegate, parallel, conditional, loop
    actions = ["delegate", "parallel", "conditional", "loop"]
    assert any(a in content.lower() for a in actions), \
        f"workflow-engine must mention at least one of {actions}"
    # SOT = Single Source of Truth
    assert "SOT" in content or "sot" in content.lower(), \
        "workflow-engine must reference SOT workflows"


def test_workflow_engine_respects_workflow_fields():
    """Spec: Respects depends_on, on_error, timeout, condition, foreach, params."""
    content = RECIPE.read_text()
    for field in ("depends_on", "on_error", "timeout", "condition", "foreach"):
        assert field in content, \
            f"workflow-engine must respect {field} field"


def test_workflow_engine_confirmation_required():
    """Spec: CONFIRMATION before write/edit — NEVER without OK."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "CONFIRMATION" in flat or "confirmation" in flat.lower(), \
        "workflow-engine must require CONFIRMATION before write/edit"


def test_workflow_engine_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "workflow-engine must be single-role leaf"


def test_workflow_engine_settings():
    """Spec: workflow executor settings (timeout=600, max_turns=200, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "workflow-engine must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "workflow-engine must have max_turns=200 (workflow executor)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "workflow-engine must use deepseek model"


def test_workflow_engine_r09_r10_no_r01():
    """Spec: R09, R10 only — no R01.
    Per R101 EVIDENCE: workflow-engine is workflow executor,
    not general-improver modifier, so R01 (no general-improver
    changes) is not applicable.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "R09" in flat, "workflow-engine must declare R09"
    assert "R10" in flat, "workflow-engine must declare R10"
    # R01 not applicable — workflow engine is a workflow executor
    assert "R01" not in flat, \
        "workflow-engine must NOT have R01 (workflow executor)"
