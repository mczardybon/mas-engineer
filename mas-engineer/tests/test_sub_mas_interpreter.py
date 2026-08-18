"""
test_sub_mas_interpreter.py — sanity tests for interpreter.

interpreter v1.0.0 is the result-interpreter (MAS-internal):
Interprets results. Tasks: INTERPRET, SUMMARIZE.
ONLY Interpreter — NO other changes.

Per R101 EVIDENCE: R01+R09+R10 (action-taker with YAML output).

Run with:
    python3 -m pytest tests/test_sub_mas_interpreter.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-interpreter.yaml"


def test_interpreter_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_interpreter_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_interpreter_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_interpreter_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_interpreter_role():
    """Spec: MAS-internal: Interprets results."""
    content = RECIPE.read_text()
    assert "interpret" in content.lower() or "Interpret" in content \
        or "interprets" in content.lower(), \
        "interpreter must declare interpret role"
    assert "result" in content.lower() or "results" in content.lower(), \
        "interpreter must declare result scope"


def test_interpreter_only_interpretation():
    """Spec: ONLY Interpreter — NO other changes."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY Interpreter" in flat or "only interpret" in flat.lower(), \
        "interpreter must declare ONLY-interpretation rule"
    assert "NO other changes" in flat or "no other changes" in flat.lower(), \
        "interpreter must forbid other changes (combined-list)"


def test_interpreter_tasks():
    """Spec: Tasks: INTERPRET, SUMMARIZE."""
    content = RECIPE.read_text()
    for task in ("INTERPRET", "SUMMARIZE"):
        assert task in content, \
            f"interpreter must reference task {task}"


def test_interpreter_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "interpreter must be single-role leaf"


def test_interpreter_settings():
    """Spec: sub-agent settings (timeout=600, max_turns=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "interpreter must have timeout=600"
    assert settings.get("max_turns") == 100, \
        "interpreter must have max_turns=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "interpreter must use deepseek model"


def test_interpreter_r01_r09_r10():
    """Spec: R01, R09, R10 (action-taker with YAML output)."""
    content = RECIPE.read_text()
    assert "R01" in content, "interpreter must declare R01"
    assert "R09" in content, "interpreter must declare R09"
    assert "R10" in content, "interpreter must declare R10"
    assert "CORONASHIELD" in content, \
        "interpreter must declare CORONASHIELD"
