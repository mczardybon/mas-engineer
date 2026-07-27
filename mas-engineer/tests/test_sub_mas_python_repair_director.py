"""
test_sub_mas_python_repair_director.py — sanity tests for python-repair-director.

python-repair-director v1.0.0 is the orchestrator (MAS-internal)
for the Python repair pipeline. Delegates to 3 specialized
sub-agents (NN1 split):
- analyzer → sub_mas-python-analyzer
- fixer → sub_mas-python-fixer
- validator → sub_mas-python-validator

ONLY orchestration — NO direct Python repair.

Per R101 EVIDENCE: R01+R09+R10 (full controller pattern).

Run with:
    python3 -m pytest tests/test_sub_mas_python_repair_director.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-python-repair-director.yaml"


def test_repair_director_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_repair_director_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_repair_director_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_repair_director_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_repair_director_orchestrator_role():
    """Spec: MAS-internal orchestrator for Python repair pipeline."""
    content = RECIPE.read_text()
    assert "Orchestrates" in content or "orchestrat" in content.lower() \
        or "Orchestrator" in content, \
        "repair-director must declare orchestrator role"
    assert "Python repair" in content or "python repair" in content.lower() \
        or "Python-repair" in content, \
        "repair-director must declare Python-repair scope"


def test_repair_director_only_orchestration():
    """Spec: ONLY orchestration — NO direct Python repair."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "ONLY orchestration" in flat, \
        "repair-director must declare ONLY-orchestration rule"
    assert "NO direct Python" in flat or "no direct python" in flat.lower(), \
        "repair-director must forbid direct Python repair (combined-list)"


def test_repair_director_delegation_map():
    """Spec: 3-way delegation map (NN1 split: analyzer+fixer+validator)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-python-analyzer",
                "sub_mas-python-fixer",
                "sub_mas-python-validator"):
        assert sub in content, \
            f"repair-director must reference {sub} in delegation map"


def test_repair_director_3_sub_recipes():
    """Spec: exactly 3 sub_recipes (NN1 split)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 3, \
        f"repair-director must have 3 sub_recipes, got {len(subs)}: {subs}"


def test_repair_director_settings():
    """Spec: orchestrator settings (timeout=600, max_steps=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "repair-director must have timeout=600 (orchestrator)"
    assert settings.get("max_steps") == 100, \
        "repair-director must have max_steps=100 (orchestrator)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "repair-director must use deepseek model"


def test_repair_director_r01_r09_r10():
    """Spec: R01, R09, R10 (full controller pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "repair-director must declare R01"
    assert "R09" in content, "repair-director must declare R09"
    assert "R10" in content, "repair-director must declare R10"
    assert "CORONASHIELD" in content, \
        "repair-director must declare CORONASHIELD"
