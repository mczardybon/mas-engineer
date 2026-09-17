"""
test_sub_mas_prompt_engineer.py — sanity tests for prompt-engineer.

prompt-engineer v1.0.0 is the prompt-optimizer (MAS-internal):
Analyzes & optimizes agent prompts based on 10 Goose criteria.
NEVER changes prompts itself — only generates suggestions.
ALWAYS consults goose-docs.ai BEFORE each evaluation.

Per R101 EVIDENCE: R10 only (2x) (read-only optimizer, generates
suggestions but does NOT modify).

Run with:
    python3 -m pytest tests/test_sub_mas_prompt_engineer.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-prompt-engineer.yaml"


def test_prompt_engineer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_prompt_engineer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_prompt_engineer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_prompt_engineer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_prompt_engineer_role():
    """Spec: MAS-internal: Analyzes & optimizes agent prompts."""
    content = RECIPE.read_text()
    assert "prompt" in content.lower(), \
        "prompt-engineer must reference prompt"
    assert "optim" in content.lower() or "Optim" in content \
        or "ANALYSIS" in content.upper() \
        or "Analyzes" in content, \
        "prompt-engineer must declare optimization role"


def test_prompt_engineer_10_goose_criteria():
    """Spec: 10 Goose criteria for prompt analysis."""
    content = RECIPE.read_text()
    assert "10 Goose" in content or "10 goose" in content.lower() \
        or "10" in content and "Goose" in content, \
        "prompt-engineer must reference 10 Goose criteria"


def test_prompt_engineer_only_suggestions():
    """Spec: NEVER change prompts — only generate suggestions."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "NEVER" in flat or "never" in flat.lower(), \
        "prompt-engineer must have NEVER rule (read-only)"
    assert "suggestion" in flat.lower() or "suggest" in flat.lower(), \
        "prompt-engineer must generate suggestions only"


def test_prompt_engineer_consults_goose_docs():
    """Spec: ALWAYS consult goose-docs.ai BEFORE each evaluation."""
    content = RECIPE.read_text()
    assert "goose-docs" in content or "goose-docs.ai" in content, \
        "prompt-engineer must consult goose-docs.ai"
    assert "BEFORE" in content or "before" in content.lower(), \
        "prompt-engineer must consult goose-docs.ai BEFORE evaluation"


def test_prompt_engineer_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "prompt-engineer must be single-role leaf"


def test_prompt_engineer_settings():
    """Spec: sub-agent settings (timeout=600, max_turns=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "prompt-engineer must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "prompt-engineer must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "prompt-engineer must use deepseek model"


def test_prompt_engineer_r10_x2_no_r01_r09():
    """Spec: R10 (2x) only — no R01, no R09.
    Per R101 EVIDENCE: read-only optimizer, generates
    suggestions but does NOT modify YAMLs.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") >= 2, \
        f"prompt-engineer must declare R10 2x. Found: {flat.count('R10')}"
    assert flat.count("CORONASHIELD") >= 2, \
        f"prompt-engineer must declare CORONASHIELD 2x. " \
        f"Found: {flat.count('CORONASHIELD')}"
    assert "R01" not in flat, \
        "prompt-engineer must NOT have R01 (read-only optimizer)"
    assert "R09" not in flat, \
        "prompt-engineer must NOT have R09 (read-only optimizer)"
