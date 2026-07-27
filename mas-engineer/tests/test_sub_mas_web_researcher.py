"""
test_sub_mas_web_researcher.py — sanity tests for web-researcher.

web-researcher v1.0.0 is the web-research sub-agent (MAS-internal):
Searches web for MAS techniques, MCP servers, Goose features,
Python tools. ONLY research — no changes.
Returns structured findings.

Per R101 EVIDENCE: R10 (2x) only (read-only researcher,
delegates to web search tool).

Run with:
    python3 -m pytest tests/test_sub_mas_web_researcher.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-web-researcher.yaml"


def test_web_researcher_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_web_researcher_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_web_researcher_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_web_researcher_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_web_researcher_role():
    """Spec: MAS-internal: Searches web for MAS techniques, MCP servers,
    Goose features, Python tools.
    """
    content = RECIPE.read_text()
    assert "web" in content.lower() or "Web" in content, \
        "web-researcher must reference web"
    assert "research" in content.lower() or "Research" in content, \
        "web-researcher must declare research role"
    # Should mention at least one domain
    domains = ["MAS", "MCP", "Goose", "Python"]
    assert any(d in content for d in domains), \
        f"web-researcher must mention at least one of {domains}"


def test_web_researcher_only_research():
    """Spec: ONLY research — no changes."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY research" in flat or "only research" in flat.lower(), \
        "web-researcher must declare ONLY-research rule"
    assert "no changes" in flat.lower(), \
        "web-researcher must forbid changes"


def test_web_researcher_returns_structured_findings():
    """Spec: Returns structured findings."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "structured findings" in flat.lower() \
        or "return" in flat.lower() and "findings" in flat.lower(), \
        "web-researcher must return structured findings"


def test_web_researcher_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "web-researcher must be single-role leaf"


def test_web_researcher_settings():
    """Spec: sub-agent settings (timeout=120, max_steps=30, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "web-researcher must have timeout=120"
    assert settings.get("max_steps") == 30, \
        "web-researcher must have max_steps=30"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "web-researcher must use deepseek model"


def test_web_researcher_r10_x2_no_r01_r09():
    """Spec: R10 (2x) only — no R01, no R09.
    Per R101 EVIDENCE: read-only researcher, doesn't modify YAMLs.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") >= 2, \
        f"web-researcher must declare R10 2x. Found: {flat.count('R10')}"
    assert flat.count("CORONASHIELD") >= 2, \
        f"web-researcher must declare CORONASHIELD 2x. " \
        f"Found: {flat.count('CORONASHIELD')}"
    assert "R01" not in flat, \
        "web-researcher must NOT have R01 (read-only researcher)"
    assert "R09" not in flat, \
        "web-researcher must NOT have R09 (read-only researcher)"


def test_web_researcher_uses_recovery_immune():
    """Spec: R10 CORONASHIELD delegates YAML validation to
    sub_mas-recovery-immune.
    """
    content = RECIPE.read_text()
    assert "sub_mas-recovery-immune" in content, \
        "web-researcher must reference sub_mas-recovery-immune"
