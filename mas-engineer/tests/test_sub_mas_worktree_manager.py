"""
test_sub_mas_worktree_manager.py — sanity tests for worktree-manager.

worktree-manager v1.0.0 is the Git-Worktree manager (MAS-internal):
Manages git worktrees — INIT, LIST, SWITCH, CLEANUP tasks.
ONLY Worktree — NO other changes.

Per R101 EVIDENCE: R01+R09+R10 (action-taker with YAML output).

Run with:
    python3 -m pytest tests/test_sub_mas_worktree_manager.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-worktree-manager.yaml"


def test_worktree_manager_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_worktree_manager_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_worktree_manager_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_worktree_manager_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_worktree_manager_role():
    """Spec: MAS-internal: Manages Git-Worktrees."""
    content = RECIPE.read_text()
    assert "Worktree" in content or "worktree" in content.lower(), \
        "worktree-manager must reference worktree"
    assert "manage" in content.lower() or "Manage" in content, \
        "worktree-manager must declare manage-role"
    assert "Git" in content or "git" in content.lower(), \
        "worktree-manager must reference Git"


def test_worktree_manager_only_worktree():
    """Spec: ONLY Worktree — NO other changes."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY Worktree" in flat or "only worktree" in flat.lower(), \
        "worktree-manager must declare ONLY-worktree rule"
    assert "NO other changes" in flat or "no other changes" in flat.lower(), \
        "worktree-manager must forbid other changes (combined-list)"


def test_worktree_manager_tasks():
    """Spec: Tasks: INIT, LIST, SWITCH, CLEANUP."""
    content = RECIPE.read_text()
    for task in ("INIT", "LIST", "SWITCH", "CLEANUP"):
        assert task in content, \
            f"worktree-manager must reference task {task}"


def test_worktree_manager_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "worktree-manager must be single-role leaf"


def test_worktree_manager_settings():
    """Spec: sub-agent settings (timeout=600, max_turns=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "worktree-manager must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "worktree-manager must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "worktree-manager must use deepseek model"


def test_worktree_manager_r01_r09_r10():
    """Spec: R01, R09, R10 (action-taker with YAML output)."""
    content = RECIPE.read_text()
    assert "R01" in content, "worktree-manager must declare R01"
    assert "R09" in content, "worktree-manager must declare R09"
    assert "R10" in content, "worktree-manager must declare R10"
    assert "CORONASHIELD" in content, \
        "worktree-manager must declare CORONASHIELD"
