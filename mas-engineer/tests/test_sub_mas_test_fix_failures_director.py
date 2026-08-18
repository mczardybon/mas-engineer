"""
test_sub_mas_test_fix_failures_director.py — sanity tests for test-fix-failures-director.

test-fix-failures-director v1.0.0 is the orchestrator (MAS-internal)
for fixing 2 e2e test failures. ONLY orchestration — no direct fixes.
Delegates to 5 specialized sub-agents.

Per R101 EVIDENCE: director has 0 R-number rules (minimal recipe,
all rules delegated to specialized sub-agents + constitution).

Run with:
    python3 -m pytest tests/test_sub_mas_test_fix_failures_director.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-fix-failures-director.yaml"


def test_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_director_orchestrator_role():
    """Spec: MAS-internal orchestrator for fixing 2 e2e test failures."""
    content = RECIPE.read_text()
    assert "Orchestrates" in content or "orchestrat" in content.lower(), \
        "director must declare orchestrator role"
    assert "test failures" in content.lower(), \
        "director must declare test-failures scope"
    assert "2 e2e" in content or "two e2e" in content.lower(), \
        "director must declare 2-e2e scope"


def test_director_only_orchestration():
    """Spec: ONLY orchestration — no direct fixes."""
    content = RECIPE.read_text()
    assert "ONLY orchestration" in content, \
        "director must declare ONLY-orchestration rule"
    assert "no direct fixes" in content, \
        "director must forbid direct fixes (combined-list)"


def test_director_delegation_map():
    """Spec: 5-way delegation map (full pipeline)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-test-fix-failures-finder",
                "sub_mas-test-fix-failures-ranker",
                "sub_mas-test-fix-failures-designer",
                "sub_mas-test-fix-failures-validator-director",
                "sub_mas-test-fix-failures-applier"):
        assert sub in content, \
            f"director must reference {sub} in delegation map"


def test_director_5_sub_recipes():
    """Spec: exactly 5 sub_recipes (full pipeline)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 5, \
        f"director must have 5 sub_recipes, got {len(subs)}: {subs}"


def test_director_settings():
    """Spec: orchestrator settings (timeout=600, max_turns=100, temperature=0.3)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "director must have timeout=600 (orchestrator)"
    assert settings.get("max_turns") == 100, \
        "director must have max_turns=100 (orchestrator)"
    assert settings.get("temperature") == 0.3, \
        "director must have temperature=0.3"


def test_director_no_r_rules():
    """Spec: director has 0 R-number rules.
    Per R101 EVIDENCE: minimal recipe, delegates all rules
    to specialized sub-agents + master-constitution.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R0") == 0, \
        f"director must not restate R-rules. Found: {flat.count('R0')}"


def test_director_workflow_order():
    """Spec: 5-step workflow (find → rank → design → validate → apply)."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Check order of delegation stages
    pos_find = flat.lower().find("finder")
    pos_rank = flat.lower().find("ranker")
    pos_design = flat.lower().find("designer")
    pos_validate = flat.lower().find("validator")
    pos_apply = flat.lower().find("applier")
    assert pos_find > 0 and pos_rank > pos_find \
        and pos_design > pos_rank and pos_validate > pos_design \
        and pos_apply > pos_validate, \
        "director must order: find → rank → design → validate → apply"
