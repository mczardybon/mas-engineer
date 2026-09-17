"""
test_sub_mas_recipe_manager.py — sanity tests for recipe-manager.

recipe-manager v1.0.0 installs/uninstalls recipes via
dev_recipe_manager.py. 4 tasks: INSTALL, UNINSTALL, LIST, CLEANUP.
SOT WORKFLOW CONTROL via workflows.yaml.

Run with:
    python3 -m pytest tests/test_sub_mas_recipe_manager.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-recipe-manager.yaml"
SCRIPT = REPO_ROOT / "tools" / "dev_recipe_manager.py"


def test_recipe_manager_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_recipe_manager_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_recipe_manager_recipe_has_required_fields():
    """Adapted: no 'settings' field — required-fields check based on actual recipe."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "description", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_recipe_manager_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_recipe_manager_sot_workflow_control():
    """Spec: SOT WORKFLOW CONTROL — workflows.yaml → agents.recipe-manager."""
    content = RECIPE.read_text()
    assert "SOT WORKFLOW CONTROL" in content, \
        "recipe-manager must declare SOT WORKFLOW CONTROL"
    assert "workflows.yaml" in content, \
        "recipe-manager must reference workflows.yaml"
    assert "agents.recipe-manager" in content, \
        "recipe-manager must register in agents.recipe-manager"


def test_recipe_manager_4_tasks():
    """Spec: 4 tasks — INSTALL, UNINSTALL, LIST, CLEANUP."""
    content = RECIPE.read_text()
    for task in ("INSTALL", "UNINSTALL", "LIST", "CLEANUP"):
        assert task in content, \
            f"recipe-manager must declare task: {task}"


def test_recipe_manager_install_uninstall_list_procedures():
    """Spec: 3 procedures — INSTALL, UNINSTALL, LIST (CLEANUP may share)."""
    content = RECIPE.read_text()
    for proc in ("Procedure INSTALL", "Procedure UNINSTALL", "Procedure LIST"):
        assert proc in content, \
            f"recipe-manager must declare procedure: {proc}"


def test_recipe_manager_dev_recipe_manager_script():
    """Spec: delegates to dev_recipe_manager.py."""
    content = RECIPE.read_text()
    assert "dev_recipe_manager.py" in content, \
        "recipe-manager must delegate to dev_recipe_manager.py"


def test_recipe_manager_r01_r09():
    """Spec: R01 (confirmation), R09 (domain)."""
    content = RECIPE.read_text()
    assert "R01" in content, "recipe-manager must declare R01"
    assert "R09" in content, "recipe-manager must declare R09"
    assert "MODE-DOMAIN" in content or "domain-overreach" in content, \
        "recipe-manager must declare domain-overreach protection"


def test_recipe_manager_script_exists():
    """EVIDENCE: tools/dev_recipe_manager.py must exist."""
    assert SCRIPT.exists(), \
        f"Missing: {SCRIPT} (recipe-manager delegation target)"
