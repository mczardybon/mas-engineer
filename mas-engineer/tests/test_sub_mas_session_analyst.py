"""
test_sub_mas_session_analyst.py — sanity tests for session-analyst.

session-analyst v1.0.0 is the session-analyzer (MAS-internal):
Correlates Goose sessions with framework changes and test results.
Read-only analyzer — produces correlation report.

Per R101 EVIDENCE: R10 (1x) only (read-only analyzer, no R01/R09).

Run with:
    python3 -m pytest tests/test_sub_mas_session_analyst.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-session-analyst.yaml"


def test_session_analyst_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_session_analyst_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_session_analyst_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_session_analyst_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_session_analyst_role():
    """Spec: MAS-internal: Correlates Goose sessions with framework changes
    and test results.
    """
    content = RECIPE.read_text()
    assert "session" in content.lower() or "Session" in content \
        or "SESSION" in content, \
        "session-analyst must reference session"
    assert "correlation" in content.lower() or "correlate" in content.lower() \
        or "Correlate" in content or "CORRELATE" in content, \
        "session-analyst must declare correlation role"
    # Should mention at least one of: changes, test results
    assert ("change" in content.lower() or "Change" in content) \
        or ("test" in content.lower() and "result" in content.lower()), \
        "session-analyst must reference changes or test results"


def test_session_analyst_read_only():
    """Spec: Read-only analyzer — produces correlation report.

    Note: the recipe delegates to .md file which has:
    L20: "⛔ Only read — no Sessions delete or modify"
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Recipe delegates to external .md file — check the .md file
    md_path = REPO_ROOT / "recipe" / "instructions" / "sub_mas-session-analyst.md"
    if md_path.exists():
        md_content = md_path.read_text()
        md_flat = re.sub(r"\s+", " ", md_content)
        assert "Only read" in md_flat \
            or "only read" in md_flat.lower() \
            or "no Sessions delete" in md_flat \
            or "no modify" in md_flat.lower(), \
            "session-analyst .md must declare 'Only read' or 'no Sessions delete'"


def test_session_analyst_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "session-analyst must be single-role leaf"


def test_session_analyst_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "session-analyst must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "session-analyst must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "session-analyst must use deepseek model"


def test_session_analyst_r10_only():
    """Spec: R10 (1x) only — no R01, no R09.
    Per R101 EVIDENCE: read-only analyzer, doesn't modify YAMLs.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") >= 1, \
        f"session-analyst must declare R10. Found: {flat.count('R10')}"
    assert "CORONASHIELD" in flat, \
        "session-analyst must declare CORONASHIELD"
    assert "R01" not in flat, \
        "session-analyst must NOT have R01 (read-only analyzer)"
    assert "R09" not in flat, \
        "session-analyst must NOT have R09 (read-only analyzer)"


def test_session_analyst_uses_recovery_immune():
    """Spec: R10 CORONASHIELD delegates YAML validation to
    sub_mas-recovery-immune.
    """
    content = RECIPE.read_text()
    assert "sub_mas-recovery-immune" in content, \
        "session-analyst must reference sub_mas-recovery-immune"
