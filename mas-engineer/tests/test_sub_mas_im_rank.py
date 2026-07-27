"""
test_sub_mas_im_rank.py — sanity tests for im-rank (Stage 2 of IM-pipeline).

IM-Rank prioritizes and filters findings. Reads findings.yaml from
im-finder, writes ranked_findings.yaml for im-designer. Applies the
duckling-constitution Art.1-6 check (R36+ v2).

Run with:
    python3 -m pytest tests/test_sub_mas_im_rank.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-im-rank.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-im-rank.md"


def test_im_rank_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_im_rank_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_im_rank_recipe_has_required_fields():
    """im-rank has BOTH prompt-field and external-instructions-file (R37)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_im_rank_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_im_rank_instructions_exist():
    """R37: external instructions file must exist."""
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_im_rank_is_stage_2():
    """IM-Rank is Stage 2 of the 5-stage IM pipeline."""
    content = INSTRUCTIONS.read_text()
    assert "Stage 2" in content or "stage: 2" in content, \
        "im-rank must declare Stage 2 (R36+ pipeline contract)"


def test_im_rank_reads_findings_yaml():
    """Input: .state/pipeline/findings.yaml (from im-finder)."""
    content = INSTRUCTIONS.read_text()
    assert "findings.yaml" in content, \
        "im-rank must read findings.yaml input from im-finder"
    assert ".state/pipeline/" in content, \
        "im-rank must reference the .state/pipeline/ directory"


def test_im_rank_writes_ranked_findings():
    """Output: .state/pipeline/ranked_findings.yaml (for im-designer)."""
    content = INSTRUCTIONS.read_text()
    assert "ranked_findings.yaml" in content, \
        "im-rank must write ranked_findings.yaml output for im-designer"


def test_im_rank_art_1_6_check():
    """R36+: applies the duckling-constitution Art.1-6 check (priority filter)."""
    content = INSTRUCTIONS.read_text()
    # Must reference the 6-article filter
    assert "Art" in content or "article" in content.lower() or "1-6" in content, \
        "im-rank must apply the Art.1-6 duckling-constitution check"


def test_im_rank_coronashield():
    """R10: prompt must declare CORONASHIELD YAML validation rule."""
    content = RECIPE.read_text()
    assert "CORONASHIELD" in content, \
        "im-rank must declare R10 CORONASHIELD YAML validation"


def test_im_rank_uses_deepseek():
    """R36+: uses deepseek-v4-flash model for cost-efficiency."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    model = data.get("settings", {}).get("goose_model", "")
    assert "deepseek" in model, \
        f"im-rank should use deepseek model (R36+ cost-control), got: {model}"


def test_im_rank_selective_goose_summon():
    """im-rank summons goose-expert ONLY conditionally (R36+ v2 — more
    selective than im-finder, relies on duckling-constitution)."""
    content = INSTRUCTIONS.read_text()
    # Should mention "conditional" or "ONLY" in context of goose-summon
    assert "conditional" in content.lower() or "ONLY" in content, \
        "im-rank must declare conditional goose-expert summon (R36+ v2)"


def test_im_rank_uses_workflow_control():
    """SOT: must reference workflows.yaml → agents.im-rank → .task_workflows.RANK."""
    content = INSTRUCTIONS.read_text()
    assert "workflows.yaml" in content, \
        "im-rank must reference workflows.yaml as SOT (R36+ v2)"
    assert "RANK" in content, "im-rank must reference .task_workflows.RANK"
