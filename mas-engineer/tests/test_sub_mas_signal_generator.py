"""
test_sub_mas_signal_generator.py — sanity tests for signal-generator.

signal-generator v1.0.0 is the SOT signal-emitter (MAS-internal):
Generates CP_DONE, ERROR, SESSION_END signals.
Called after each action from MAS-Engineer.

Per R101 EVIDENCE: R01+R09+R10 (action-taker leaf).

Run with:
    python3 -m pytest tests/test_sub_mas_signal_generator.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-signal-generator.yaml"


def test_signal_generator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_signal_generator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_signal_generator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_signal_generator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_signal_generator_role():
    """Spec: MAS-internal: Generates CP_DONE, ERROR, SESSION_END signals.
    Called after each action from MAS-Engineer.
    """
    content = RECIPE.read_text()
    assert "CP_DONE" in content, \
        "signal-generator must reference CP_DONE signal"
    assert "ERROR" in content, \
        "signal-generator must reference ERROR signal"
    assert "SESSION_END" in content, \
        "signal-generator must reference SESSION_END signal"


def test_signal_generator_workflow_control():
    """Spec: SOT WORKFLOW CONTROL — workflows.yaml → agents.signal-generator
    .task_workflows.CP_DONE.
    """
    content = RECIPE.read_text()
    assert "workflows.yaml" in content or "WORKFLOW CONTROL" in content, \
        "signal-generator must reference workflows.yaml SOT"
    assert "task_workflows" in content, \
        "signal-generator must reference task_workflows"


def test_signal_generator_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "signal-generator must be single-role leaf"


def test_signal_generator_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "signal-generator must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "signal-generator must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "signal-generator must use deepseek model"


def test_signal_generator_r01_r09_r10():
    """Spec: R01, R09, R10 (action-taker leaf).
    Per R101 EVIDENCE: standard action-taker pattern.
    """
    content = RECIPE.read_text()
    assert "R01" in content, "signal-generator must declare R01"
    assert "R09" in content, "signal-generator must declare R09"
    assert "R10" in content, "signal-generator must declare R10"
    assert "CORONASHIELD" in content, \
        "signal-generator must declare CORONASHIELD"
