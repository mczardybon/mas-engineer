"""
test_sub_mas_git_operator.py — sanity tests for git-operator.

git-operator v2.0.0 is the Git-command executor (MAS-internal):
git init, add, commit, push, status, log, diff.
CLEAN-COMMIT mode by default — no backup-dir pollution,
no monolithic commits.

Per R101 EVIDENCE: R01 (6x!) + R09 (2x) + R10 (3x) — heavily
R01-enforced (every write/edit/shell requires explicit user
confirmation, SHOWN PLAN BEFORE COMMIT).

Run with:
    python3 -m pytest tests/test_sub_mas_git_operator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-git-operator.yaml"


def test_git_operator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_git_operator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_git_operator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_git_operator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_git_operator_role():
    """Spec: MAS-internal: git init, add, commit, push, status, log, diff."""
    content = RECIPE.read_text()
    for cmd in ("init", "add", "commit", "push", "status", "log", "diff"):
        assert cmd in content, \
            f"git-operator must reference git command {cmd}"


def test_git_operator_clean_commit_mode():
    """Spec: CLEAN-COMMIT mode by default."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "CLEAN-COMMIT" in flat or "CLEAN_COMMIT" in flat \
        or "clean-commit" in flat.lower(), \
        "git-operator must declare CLEAN-COMMIT mode"
    # No backup-dir pollution
    assert "no backup" in flat.lower() or "backup-dir" in flat.lower(), \
        "git-operator must forbid backup-dir pollution"
    # No monolithic commits
    assert "no monolithic" in flat.lower() or "monolithic" in flat.lower(), \
        "git-operator must forbid monolithic commits"


def test_git_operator_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "git-operator must be single-role leaf"


def test_git_operator_settings():
    """Spec: git-operator settings (timeout=180, max_steps=30, deepseek,
    temperature=0.2).
    """
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 180, \
        "git-operator must have timeout=180"
    assert settings.get("max_steps") == 30, \
        "git-operator must have max_steps=30"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "git-operator must use deepseek model"
    assert settings.get("temperature") == 0.2, \
        "git-operator must have temperature=0.2 (deterministic git)"


def test_git_operator_r01_x6_r09_x2_r10_x3():
    """Spec: R01 (6x) + R09 (2x) + R10 (3x) — heavily R01-enforced.

    Per R101 EVIDENCE: git-operator has the most R01 rules
    because every git operation needs explicit user confirmation
    (SHOWN PLAN BEFORE COMMIT).
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R01") >= 6, \
        f"git-operator must declare R01 6x. Found: {flat.count('R01')}"
    assert flat.count("R09") >= 2, \
        f"git-operator must declare R09 2x. Found: {flat.count('R09')}"
    assert flat.count("R10") >= 3, \
        f"git-operator must declare R10 3x. Found: {flat.count('R10')}"
    assert "CORONASHIELD" in flat, \
        "git-operator must declare CORONASHIELD"


def test_git_operator_uses_recovery_immune():
    """Spec: R10 CORONASHIELD delegates YAML validation to
    sub_mas-recovery-immune.
    """
    content = RECIPE.read_text()
    assert "sub_mas-recovery-immune" in content, \
        "git-operator must reference sub_mas-recovery-immune"


def test_git_operator_shown_plan_before_commit():
    """Spec: R01 — SHOWN PLAN BEFORE COMMIT (every commit)."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "SHOWN PLAN BEFORE COMMIT" in flat \
        or "shown plan before commit" in flat.lower(), \
        "git-operator must show plan before commit"
