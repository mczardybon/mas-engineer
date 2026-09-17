"""
test_sub_mas_im_validator.py — sanity tests for im-validator (Stage 4).

IM-Validator reviews proposed patches and recommends rollback. Stage
4/5 of the IM-pipeline. ONLY Analysis — no Changes.

Run with:
    python3 -m pytest tests/test_sub_mas_im_validator.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-im-validator.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-im-validator.md"


def test_im_validator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_im_validator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_im_validator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_im_validator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_im_validator_instructions_exist():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_im_validator_is_stage_4():
    """IM-Validator is Stage 4/5 of the pipeline."""
    content = INSTRUCTIONS.read_text()
    assert "Stage 4" in content or "stage: 4" in content, \
        "im-validator must declare Stage 4 (R36+ pipeline contract)"


def test_im_validator_only_analysis():
    """Spec: 'ONLY Analysis - no Changes' — must declare this explicitly."""
    content = RECIPE.read_text()
    assert "ONLY Analysis" in content or "no Changes" in content, \
        "im-validator must declare 'ONLY Analysis - no Changes' rule"


def test_im_validator_recommends_rollback():
    """Spec: validator can recommend rollback on risky patches."""
    content = INSTRUCTIONS.read_text() if INSTRUCTIONS.exists() else ""
    assert "rollback" in content.lower() or "ROLLBACK" in content, \
        "im-validator must define rollback recommendation logic"


def test_im_validator_summons_goose_expert():
    """R11: must summon sub_mas-goose-expert for patch validation."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-goose-expert" in subs, \
        f"im-validator must summon sub_mas-goose-expert (R11). subs: {subs}"


def test_im_validator_uses_deepseek():
    """R36+: cost-control via deepseek-v4-flash."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    model = data.get("settings", {}).get("goose_model", "")
    assert "deepseek" in model, \
        f"im-validator should use deepseek (R36+ cost-control), got: {model}"
