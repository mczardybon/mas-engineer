"""
test_sub_mas_im_designer.py — sanity tests for im-designer (Stage 3).

IM-Designer converts findings into concrete YAML patch proposals.
Stage 3/5 of the IM-pipeline. Reads findings.yaml, outputs patch
proposals — no apply, no direct edit.

Run with:
    python3 -m pytest tests/test_sub_mas_im_designer.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-im-designer.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-im-designer.md"


def test_im_designer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_im_designer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_im_designer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_im_designer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_im_designer_instructions_exist():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_im_designer_is_stage_3():
    """IM-Designer is Stage 3/5 of the pipeline."""
    content = INSTRUCTIONS.read_text()
    assert "Stage 3" in content or "stage: 3" in content, \
        "im-designer must declare Stage 3 (R36+ pipeline contract)"


def test_im_designer_reads_findings_yaml():
    content = INSTRUCTIONS.read_text()
    assert "findings.yaml" in content, \
        "im-designer must read findings.yaml from im-finder/im-rank"


def test_im_designer_no_apply():
    """Spec: 'ONLY draft — no changes' — must declare this explicitly."""
    content = RECIPE.read_text()
    assert "no apply" in content.lower() or "no changes" in content.lower() or \
           "ONLY draft" in content, \
        "im-designer must declare 'no apply' rule (draft-only stage)"


def test_im_designer_summons_goose_expert():
    """R11: must summon sub_mas-goose-expert for patch design."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-goose-expert" in subs, \
        f"im-designer must summon sub_mas-goose-expert (R11). subs: {subs}"


def test_im_designer_uses_deepseek():
    """R36+: cost-control via deepseek-v4-flash."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    model = data.get("settings", {}).get("goose_model", "")
    assert "deepseek" in model, \
        f"im-designer should use deepseek (R36+ cost-control), got: {model}"
