"""
test_sub_mas_framework_finder.py — sanity tests for framework-finder.

Framework-finder is a single-role agent: find framework files and
structures. Delegates scanning/auditing/hardening to other agents.

Run with:
    python3 -m pytest tests/test_sub_mas_framework_finder.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-finder.yaml"


def test_framework_finder_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_finder_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_finder_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_finder_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_finder_only_finding():
    """Spec: ONLY finding — NO scanning, auditing, or hardening."""
    content = RECIPE.read_text()
    assert "ONLY finding" in content or "ONLY framework finding" in content, \
        "framework-finder must declare single-role (only finding) rule"


def test_framework_finder_forbidden_actions():
    """Spec: NEVER scan/audit/harden/edit — delegate to other agents."""
    content = RECIPE.read_text()
    for action in ("NEVER scan", "NEVER audit", "NEVER harden", "NEVER edit"):
        assert action in content, \
            f"framework-finder must forbid: {action}"


def test_framework_finder_delegates_to_others():
    """Must explicitly delegate to framework-scanner, framework-auditor,
    framework-hardener."""
    content = RECIPE.read_text()
    for agent in ("framework-scanner", "framework-auditor", "framework-hardener"):
        assert agent in content, \
            f"framework-finder must delegate to: {agent}"


def test_framework_finder_no_sub_recipes():
    """framework-finder is a leaf node (delegation via instructions, not sub_recipes)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "framework-finder must be a leaf node"


def test_framework_finder_returns_paths():
    """Procedure FIND: return file paths and context."""
    content = RECIPE.read_text()
    # Should mention return format
    assert "return" in content.lower() or "Return" in content, \
        "framework-finder must define return-format"
    assert "file path" in content.lower() or "file_path" in content or \
           "path" in content.lower(), \
        "framework-finder must return file paths"


def test_framework_finder_deepseek():
    """R36+: cost-control via deepseek-v4-flash."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    model = data.get("settings", {}).get("goose_model", "")
    assert "deepseek" in model, \
        f"framework-finder should use deepseek (R36+ cost-control), got: {model}"
