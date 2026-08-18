"""
test_sub_mas_test_fix_failures_designer.py — sanity tests for test-fix-failures-designer.

test-fix-failures-designer v1.0.0 designs YAML patches to
fix e2e test failures. ONLY design — no changes. Single-role leaf.

Per R101 EVIDENCE: has R10 (CORONASHIELD), no R04 (designer
creates new content, doesn't modify general-improver).

Run with:
    python3 -m pytest tests/test_sub_mas_test_fix_failures_designer.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-test-fix-failures-designer.yaml"


def test_designer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_designer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_designer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_designer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_designer_role():
    """Spec: Designs patches for test failures."""
    content = RECIPE.read_text()
    assert "Designs patches" in content or "design patches" in content.lower(), \
        "designer must declare design-patches role"
    assert "test failures" in content.lower(), \
        "designer must declare test-failures scope"


def test_designer_only_design():
    """Spec: ONLY design — no changes."""
    content = RECIPE.read_text()
    assert "ONLY design" in content, \
        "designer must declare ONLY-design rule"
    assert "no changes" in content, \
        "designer must forbid changes (combined-list)"


def test_designer_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "designer must be single-role leaf"


def test_designer_settings():
    """Spec: sub-agent settings (timeout=300, max_turns=50, temperature=0.3)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 300, \
        "designer must have timeout=300 (sub-agent)"
    assert settings.get("max_turns") == 50, \
        "designer must have max_turns=50 (sub-agent)"
    assert settings.get("temperature") == 0.3, \
        "designer must have temperature=0.3"


def test_designer_r10_coronashield():
    """Spec: R10 CORONASHIELD — Ensure each patch is valid YAML."""
    content = RECIPE.read_text()
    assert "R10" in content, "designer must declare R10"
    assert "Coronashield" in content or "CORONASHIELD" in content, \
        "designer must reference Coronashield/CORONASHIELD"
    assert "valid YAML" in content, \
        "designer must declare valid-YAML rule"


def test_designer_goose_verdict():
    """Spec: Each patch must include goose_verdict: CONFORM."""
    content = RECIPE.read_text()
    assert "goose_verdict" in content, \
        "designer must declare goose_verdict output"
    assert "CONFORM" in content, \
        "designer must declare CONFORM verdict value"


def test_designer_no_r04():
    """Spec: designer has NO R04 (designer creates new content,
    doesn't modify general-improver.yaml).
    Per R101 EVIDENCE: applier has R04, designer doesn't.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R04") == 0, \
        "designer must NOT have R04 (R04 belongs to applier)"
