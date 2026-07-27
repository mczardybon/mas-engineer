"""
test_sub_mas_python_repair.py — sanity tests for python-repair.

python-repair v1.0.0 is the orchestrator (MAS-internal) for the
Python repair pipeline. Delegates to 3 specialized sub-agents
(NN1 split):
- sub_mas-python-analyzer
- sub_mas-python-fixer
- sub_mas-python-validator

ONLY orchestration — NO direct Python repair.

Per R101 EVIDENCE: R01+R09+R10 (full controller pattern).

Note: There is BOTH sub_mas-python-repair (this, orchestrator) AND
sub_mas-python-repair-director. This is a naming inconsistency.
Per R101 EVIDENCE: both exist as separate recipes. This test
covers sub_mas-python-repair (the orchestrator).

Run with:
    python3 -m pytest tests/test_sub_mas_python_repair.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-python-repair.yaml"


def test_python_repair_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_python_repair_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_python_repair_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_python_repair_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_python_repair_orchestrator_role():
    """Spec: MAS-internal orchestrator for Python repair pipeline."""
    content = RECIPE.read_text()
    assert "Orchestrates" in content or "orchestrat" in content.lower() \
        or "DIRECTOR" in content.upper() or "Director" in content, \
        "python-repair must declare orchestrator role"
    assert "Python repair" in content or "python repair" in content.lower() \
        or "Python-repair" in content, \
        "python-repair must declare Python-repair scope"


def test_python_repair_only_orchestration():
    """Spec: ONLY orchestration — NO direct Python repair."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY orchestration" in flat, \
        "python-repair must declare ONLY-orchestration rule"
    assert "NO direct Python" in flat or "no direct python" in flat.lower(), \
        "python-repair must forbid direct Python repair (combined-list)"


def test_python_repair_delegation_map():
    """Spec: 3-way delegation map (analyzer+fixer+validator)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-python-analyzer",
                "sub_mas-python-fixer",
                "sub_mas-python-validator"):
        assert sub in content, \
            f"python-repair must reference {sub} in delegation map"


def test_python_repair_3_sub_recipes():
    """Spec: exactly 3 sub_recipes (NN1 split)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 3, \
        f"python-repair must have 3 sub_recipes, got {len(subs)}: {subs}"


def test_python_repair_settings():
    """Spec: orchestrator settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "python-repair must have timeout=600 (orchestrator)"
    assert settings.get("max_steps") == 100, \
        "python-repair must have max_steps=100 (orchestrator)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "python-repair must use deepseek model"


def test_python_repair_r01_r09_r10():
    """Spec: R01, R09, R10 (full controller pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "python-repair must declare R01"
    assert "R09" in content, "python-repair must declare R09"
    assert "R10" in content, "python-repair must declare R10"
    assert "CORONASHIELD" in content, \
        "python-repair must declare CORONASHIELD"
