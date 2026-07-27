"""
test_sub_mas_summarizer.py — sanity tests for summarizer.

summarizer v1.0.0 is the result-summarizer (MAS-internal):
Summarizes results. Single role: SUMMARIZE, CONDENSE.

Per R101 EVIDENCE: R01+R09+R10 (action-taker leaf).

Run with:
    python3 -m pytest tests/test_sub_mas_summarizer.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-summarizer.yaml"


def test_summarizer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_summarizer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_summarizer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_summarizer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_summarizer_role():
    """Spec: MAS-internal: Summarizes results."""
    content = RECIPE.read_text()
    assert "Summariz" in content or "summariz" in content \
        or "SUMMARIZE" in content or "Summary" in content, \
        "summarizer must declare summarizer role"
    assert "result" in content.lower() or "Result" in content \
        or "RESULTS" in content, \
        "summarizer must reference results to summarize"


def test_summarizer_only_summarizing():
    """Spec: ONLY Summarize — NO other changes."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY Summariz" in flat or "ONLY summariz" in flat \
        or "ONLY SUMMARIZE" in flat, \
        "summarizer must declare ONLY-summarize rule"
    assert "NO other changes" in flat or "no other changes" in flat.lower(), \
        "summarizer must forbid other changes (combined-list)"


def test_summarizer_tasks():
    """Spec: Tasks: SUMMARIZE, CONDENSE."""
    content = RECIPE.read_text()
    assert "SUMMARIZE" in content, "summarizer must reference SUMMARIZE task"
    assert "CONDENSE" in content, "summarizer must reference CONDENSE task"


def test_summarizer_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "summarizer must be single-role leaf"


def test_summarizer_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "summarizer must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "summarizer must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "summarizer must use deepseek model"


def test_summarizer_r01_r09_r10():
    """Spec: R01, R09, R10 (action-taker leaf).
    Per R101 EVIDENCE: standard action-taker pattern.
    """
    content = RECIPE.read_text()
    assert "R01" in content, "summarizer must declare R01"
    assert "R09" in content, "summarizer must declare R09"
    assert "R10" in content, "summarizer must declare R10"
    assert "CORONASHIELD" in content, \
        "summarizer must declare CORONASHIELD"
