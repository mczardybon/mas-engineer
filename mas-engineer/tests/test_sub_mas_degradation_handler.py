"""
test_sub_mas_degradation_handler.py — sanity tests for degradation-handler.

NOTE: degradation-handler is the orchestrator (NN1 split from
degradation-director). It delegates to ALL THREE sub-agents
(analyzer, planner, reporter) and includes the SOT workflow
control reference.

Run with:
    python3 -m pytest tests/test_sub_mas_degradation_handler.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-degradation-handler.yaml"


def test_degradation_handler_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_degradation_handler_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_degradation_handler_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_degradation_handler_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_degradation_handler_orchestrator():
    """Spec: orchestrator — delegates to specialized sub-agents."""
    content = RECIPE.read_text()
    assert "Orchestrat" in content or "orchestrate" in content.lower(), \
        "degradation-handler must be an orchestrator"
    assert "Delegate" in content or "delegate" in content, \
        "degradation-handler must delegate to sub-agents"


def test_degradation_handler_only_orchestration():
    """Spec: ONLY orchestration — NO direct handling."""
    content = RECIPE.read_text()
    assert "ONLY orchestration" in content, \
        "degradation-handler must declare ONLY-orchestration rule"
    assert "NO direct handling" in content, \
        "degradation-handler must forbid direct handling"


def test_degradation_handler_sot_workflow_control():
    """Spec: SOT workflow control via .state/workflows.yaml."""
    content = RECIPE.read_text()
    assert "workflows.yaml" in content, \
        "degradation-handler must reference workflows.yaml SOT"
    assert "SOT" in content or "SOT WORKFLOW" in content, \
        "degradation-handler must declare SOT WORKFLOW CONTROL"
    assert "DEGRADATION" in content, \
        "degradation-handler must reference DEGRADATION workflow"


def test_degradation_handler_4_prohibitions():
    """Spec: 4 NEVER-X prohibitions (analyze, plan, report, + direct)."""
    content = RECIPE.read_text()
    for forbid in ("NEVER analyze", "NEVER design", "NEVER write reports",
                   "NO direct handling"):
        assert forbid in content, \
            f"degradation-handler must forbid: {forbid}"


def test_degradation_handler_delegates_to_all_3():
    """Spec: delegates to analyzer, planner, reporter."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-degradation-analyzer", "sub_mas-degradation-planner",
                "sub_mas-degradation-reporter"):
        assert sub in content, \
            f"degradation-handler must delegate to: {sub}"


def test_degradation_handler_sub_recipes():
    """Handler must have sub_recipes for all 3 sub-agents."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-degradation-analyzer" in subs, \
        f"degradation-handler sub_recipes must include analyzer. subs: {subs}"
    assert "sub_mas-degradation-planner" in subs, \
        f"degradation-handler sub_recipes must include planner. subs: {subs}"
    assert "sub_mas-degradation-reporter" in subs, \
        f"degradation-handler sub_recipes must include reporter. subs: {subs}"
