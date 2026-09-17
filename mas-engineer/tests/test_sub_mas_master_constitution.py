"""
test_sub_mas_master_constitution.py — sanity tests for master-constitution.

Master-constitution v1.0.0 defines the 11 Articles for all MAS agents.
ONLY define rules — NO changes. Uses R37 external instructions.

Run with:
    python3 -m pytest tests/test_sub_mas_master_constitution.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-master-constitution.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-master-constitution.md"


def test_master_constitution_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_master_constitution_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_master_constitution_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_master_constitution_references_self():
    """Self-references: it IS the master-constitution."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_master_constitution_external_instructions():
    """R37: uses external instructions file."""
    content = RECIPE.read_text()
    assert "sub_mas-master-constitution.md" in content, \
        "master-constitution must reference external instructions file (R37)"


def test_master_constitution_instructions_file_exists():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_master_constitution_only_define_rules():
    """Spec: ONLY define rules — NO changes."""
    content = RECIPE.read_text()
    assert "ONLY define rules" in content, \
        "master-constitution must declare ONLY-define-rules rule"
    assert "NO changes" in content, \
        "master-constitution must forbid changes"


def test_master_constitution_11_articles():
    """Spec: 11 Articles for all Agents."""
    content = RECIPE.read_text()
    assert "11 Articles" in content, \
        "master-constitution must declare 11 Articles"
    # Check at least 5 of 11 articles are listed
    articles = ["Info", "Tool", "Delegation", "Context", "Error", "Quality",
                "Error Handling", "Stability", "Transparency", "Performance",
                "Security"]
    found = sum(1 for a in articles if a in content)
    assert found >= 5, \
        f"master-constitution must list ≥5 articles. found: {found}"


def test_master_constitution_r01_r09_r10():
    """Spec: R01 (no changes w/o user), R09 (domain), R10 (CORONASHIELD)."""
    content = RECIPE.read_text()
    assert "R01" in content, "master-constitution must declare R01"
    assert "R09" in content, "master-constitution must declare R09"
    assert "R10" in content or "CORONASHIELD" in content, \
        "master-constitution must declare R10 CORONASHIELD"


def test_master_constitution_r11_goose_expert():
    """Spec: R11 mandatory goose-expert consultation for governance questions."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-goose-expert" in subs, \
        f"master-constitution must delegate R11 governance to goose-expert. subs: {subs}"
