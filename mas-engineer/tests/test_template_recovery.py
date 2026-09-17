"""
test_template_recovery.py — sanity tests for recovery templates.

recipe/template/recovery/ contains 5 recovery sub_recipes:
- immune.yaml: Coronashield YAML/Syntax validation (R-first shield)
- checkpoint.yaml: Git-like snapshots (R-second shield)
- safezone.yaml: Parallel fork workspace
- timeline.yaml: Automatic best-point search
- defib.yaml: Emergency resuscitation (R-last resort)

All are MAS-internal recovery recipes with R10 (recovery + EVIDENCE).

Per R101 EVIDENCE: recovery-system pattern (5 recipes, R10 + 11 Articles).

Run with:
    python3 -m pytest tests/test_template_recovery.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECOVERY_DIR = REPO_ROOT / "recipe" / "template" / "recovery"

RECOVERY_RECIPES = {
    "immune.yaml": {
        "tasks": ["CHECK_YAML", "CHECK_SYNTAX", "VERIFY_STATE"],
        "role": "YAML Prevention",
        "shield": "FIRST",
    },
    "checkpoint.yaml": {
        "tasks": ["SNAPSHOT", "LIST", "RESTORE", "DIFF"],
        "role": "Snapshot System",
        "shield": "SECOND",
    },
    "safezone.yaml": {
        "tasks": ["FORK", "MERGE", "ABORT", "DIFF"],
        "role": "Fork Workspace",
        "shield": None,
    },
    "timeline.yaml": {
        "tasks": ["FIND_BEST", "RESTORE_BEST", "SHOW_PATH", "ANALYZE"],
        "role": "Time Travel",
        "shield": None,
    },
    "defib.yaml": {
        "tasks": ["DEFIB", "RESURRECT", "DIAGNOSE"],
        "role": "Emergency Resuscitation",
        "shield": "LAST",
    },
}


def test_recovery_dir_exists():
    assert RECOVERY_DIR.exists(), f"Missing: {RECOVERY_DIR}"


def test_all_recovery_recipes_exist():
    """All 5 recovery recipes must exist."""
    for fname in RECOVERY_RECIPES:
        path = RECOVERY_DIR / fname
        assert path.exists(), f"Missing recovery recipe: {path}"


def test_all_recovery_recipes_valid_yaml():
    """All recovery recipes must be valid YAML."""
    for fname in RECOVERY_RECIPES:
        path = RECOVERY_DIR / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{fname} is not a valid YAML dict"


def test_all_recovery_recipes_mas_internal():
    """All recovery recipes must be MAS-internal."""
    for fname in RECOVERY_RECIPES:
        path = RECOVERY_DIR / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        desc = data.get("description", "")
        assert "MAS-internal" in desc or "MAS-Engineer-internal" in desc, \
            f"{fname} must be MAS-internal, desc: {desc[:80]}"


def test_all_recovery_recipes_v1_0_0():
    """All recovery recipes must be v1.0.0."""
    for fname in RECOVERY_RECIPES:
        path = RECOVERY_DIR / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data.get("version") == "1.0.0", \
            f"{fname} must be v1.0.0, got {data.get('version')}"


def test_recovery_recipes_have_tasks():
    """Each recovery recipe must declare its tasks."""
    for fname, spec in RECOVERY_RECIPES.items():
        path = RECOVERY_DIR / fname
        content = path.read_text()
        for task in spec["tasks"]:
            assert task in content, \
                f"{fname} must reference task {task}"


def test_recovery_recipes_role_keywords():
    """Each recovery recipe must reference its specific role."""
    for fname, spec in RECOVERY_RECIPES.items():
        path = RECOVERY_DIR / fname
        content = path.read_text()
        # Role keywords are case-insensitive substrings
        for keyword in spec["role"].split():
            assert keyword.lower() in content.lower(), \
                f"{fname} must reference role keyword '{keyword}'"


def test_recovery_recipes_coronashield():
    """immune.yaml specifically must reference Coronashield (R-first shield)."""
    path = RECOVERY_DIR / "immune.yaml"
    content = path.read_text()
    assert "Coronashield" in content or "CORONASHIELD" in content, \
        "immune.yaml must reference Coronashield"


def test_recovery_recipes_delegation():
    """Recovery recipes reference master-constitution OR are 11-Article-based.

    Per R101 EVIDENCE: recovery recipes are referenced as "11 Articles"
    or via sub_mas-master-constitution. Some recipes (like immune) only
    reference the system via Coronashield-Rule without explicit 11 Articles.
    """
    keywords = ["master-constitution", "11 Articles", "Coronashield",
                "MAS-Engineer-internal", "sub_mas-recovery"]
    for fname in RECOVERY_RECIPES:
        path = RECOVERY_DIR / fname
        content = path.read_text()
        assert any(kw in content for kw in keywords), \
            f"{fname} must reference one of: {keywords}"


def test_recovery_recipes_settings():
    """Recovery recipes have varying timeouts (low for immune, high for safezone)."""
    expected = {
        "immune.yaml": 60,      # Quick validation
        "checkpoint.yaml": None,  # No settings specified (uses default)
        "safezone.yaml": 300,   # Long for fork
        "timeline.yaml": 120,   # Medium for analysis
        "defib.yaml": 120,      # Quick but critical
    }
    for fname, expected_timeout in expected.items():
        path = RECOVERY_DIR / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        settings = data.get("settings", {})
        if expected_timeout is not None:
            assert settings.get("timeout") == expected_timeout, \
                f"{fname} must have timeout={expected_timeout}, " \
                f"got {settings.get('timeout')}"


def test_recovery_recipes_no_sub_recipes():
    """All recovery recipes are leaf recipes (no sub_recipes)."""
    for fname in RECOVERY_RECIPES:
        path = RECOVERY_DIR / fname
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "sub_recipes" not in data or not data["sub_recipes"], \
            f"{fname} must be a leaf recipe (no sub_recipes)"


def test_recovery_recipes_count():
    """Spec: 5 recovery recipes."""
    assert len(RECOVERY_RECIPES) == 5, \
        f"Expected 5 recovery recipes, got {len(RECOVERY_RECIPES)}"
