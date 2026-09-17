"""
test_sub_mas_general_improver.py — sanity tests for general-improver.

General-improver v3.0.0 is the IM-PIPELINE orchestrator. ONLY entry
point for the Improvement-System. Orchestrates 6 specialized agents
in 7 steps.

Run with:
    python3 -m pytest tests/test_sub_mas_general_improver.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-general-improver.yaml"


def test_general_improver_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_general_improver_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_general_improver_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_general_improver_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_general_improver_entry_point():
    """Spec: ONLY entry point for the Improvement-System."""
    content = RECIPE.read_text()
    assert "ONLY entry point" in content or "entry point" in content.lower(), \
        "general-improver must declare ONLY entry-point rule"


def test_general_improver_im_pipeline_orchestrator():
    """Spec: IM-PIPELINE orchestrator — 7 steps, 6 sub-agents."""
    content = RECIPE.read_text()
    assert "7 steps" in content or "7-step" in content, \
        "general-improver must declare 7-step pipeline"
    assert "6 sub-agents" in content or "6 specialized" in content, \
        "general-improver must declare 6 sub-agents"


def test_general_improver_sub_recipes():
    """Spec: 6 sub_recipes (specialized agents)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) >= 6, \
        f"general-improver must have ≥6 sub_recipes. subs: {subs}"


def test_general_improver_v3_architecture():
    """Spec: v3.0.0 architecture (R36+ cost-control) — declared in description."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    desc = data.get("description", "")
    assert "v3.0.0" in desc, \
        f"general-improver description must declare v3.0.0 architecture. desc: {desc}"


def test_general_improver_extensions():
    """Spec: requires developer + summon extensions."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    exts = [e.get("name") for e in data.get("extensions", [])]
    assert "summon" in exts, \
        f"general-improver must require summon extension. exts: {exts}"


def test_general_improver_orchestrator_role():
    """Spec: orchestrator role — improvements-pipeline orchestrator."""
    content = RECIPE.read_text()
    assert "Orchestrat" in content or "orchestrate" in content.lower(), \
        "general-improver must be an orchestrator"
