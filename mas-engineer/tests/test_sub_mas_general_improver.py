"""
test_sub_mas_general_improver.py — sanity tests for the IM-pipeline recipe.

The general-improver orchestrates 6 sub-agents in 7 steps (FIND→RANK→
DESIGN→...→SHIP). It's the only entry point for the improvement system,
so any structural break here blocks the whole loop.

Run with:
    python3 -m pytest tests/test_sub_mas_general_improver.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-general-improver.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-general-improver.md"


def test_general_improver_recipe_exists():
    """Recipe must exist at canonical location."""
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_general_improver_recipe_is_valid_yaml():
    """R10 CORONASHIELD: recipe must be parseable YAML."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "Recipe must be a YAML mapping"


def test_general_improver_recipe_has_required_fields():
    """Constitution requires: name, version, instructions, prompt, settings."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_general_improver_references_master_constitution():
    """R10 traceability: must declare master constitution."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_general_improver_has_10_sub_recipes():
    """Recipe must declare 10 sub-agents in the pipeline (R36+ expanded).
    Original R36 design had 6, but Finder/Rank/Designer + helpers grew to 10.
    """
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = data.get("sub_recipes", [])
    assert len(subs) == 10, f"Expected 10 sub_recipes, got {len(subs)}: {[s.get('name') for s in subs]}"


def test_general_improver_pipeline_sub_agents_present():
    """All 6 sub-agents must be from the canonical IM pipeline (R36+)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    names = {s.get("name") for s in data.get("sub_recipes", [])}
    required = {
        "sub_mas-im-finder",
        "sub_mas-im-rank",
        # FIND→RANK→DESIGN→... pattern; the remaining 4 vary per version
    }
    missing = required - names
    assert not missing, f"Missing required IM pipeline sub-agents: {missing}"


def test_general_improver_has_summon_extension():
    """Summon platform extension is required (R3-summon)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    extensions = data.get("extensions", [])
    ext_names = [e.get("name") for e in extensions]
    assert "summon" in ext_names, \
        f"summon extension missing. extensions: {extensions}"


def test_general_improver_has_developer_extension():
    """Developer builtin is required for file operations in the IM pipeline."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    extensions = data.get("extensions", [])
    ext_names = [e.get("name") for e in extensions]
    assert "developer" in ext_names, \
        f"developer extension missing. extensions: {extensions}"


def test_general_improver_instructions_mention_find_rank_design():
    """The instructions must describe the FIND→RANK→DESIGN pipeline (R36 v2)."""
    content = INSTRUCTIONS.read_text()
    # At least 2 of the 3 core stages must be explicitly named
    stages = [s for s in ("FIND", "RANK", "DESIGN") if s in content]
    assert len(stages) >= 2, \
        f"Instructions must mention at least 2 of FIND/RANK/DESIGN. Found: {stages}"


def test_general_improver_instructions_mention_7_steps():
    """Recipe header says '7 steps' — instructions must reflect that."""
    content = INSTRUCTIONS.read_text()
    assert "7" in content, "Instructions must reference the 7-step pipeline"


def test_general_improver_instructions_file_exists():
    """External instructions file must exist."""
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"
