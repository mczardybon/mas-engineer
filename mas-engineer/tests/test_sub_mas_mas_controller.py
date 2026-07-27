"""
test_sub_mas_mas_controller.py — sanity tests for mas-controller.

MAS-controller v1.0.0 is the FRAMEWORK-CONTROLLER. Monitors framework
health, comms, memory, runtime, and architecture-enforcement. Uses
R37 external instructions. NEVER modifies anything (PROHIBITION BOUNDARY).

Run with:
    python3 -m pytest tests/test_sub_mas_mas_controller.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-mas-controller.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-mas-controller.md"


def test_mas_controller_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_mas_controller_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_mas_controller_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_mas_controller_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_mas_controller_external_instructions():
    """R37: uses external instructions file."""
    content = RECIPE.read_text()
    assert "sub_mas-mas-controller.md" in content, \
        "mas-controller must reference external instructions file (R37)"
    assert "Extended instructions" in content, \
        "mas-controller must declare external instructions pattern"


def test_mas_controller_instructions_file_exists():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_mas_controller_framework_monitor_role():
    """Spec: FRAMEWORK-CONTROLLER — monitors framework permanent."""
    content = RECIPE.read_text()
    assert "FRAMEWORK-CONTROLLER" in content, \
        "mas-controller must declare FRAMEWORK-CONTROLLER role"
    assert "Monitor" in content or "monitor" in content, \
        "mas-controller must declare monitoring role"


def test_mas_controller_prohibition_boundary():
    """Spec: 7 NEVER-X prohibition boundary rules."""
    content = RECIPE.read_text()
    for forbid in ("NEVER modify any recipe", "NEVER change framework configuration",
                   "NEVER execute recovery actions",
                   "NEVER modify session data",
                   "NEVER skip R01 confirmation",
                   "NEVER operate outside target workspace",
                   "NEVER save YAML without"):
        assert forbid in content, \
            f"mas-controller must forbid: {forbid[:40]}..."


def test_mas_controller_3_sub_agents():
    """Spec: 3 sub-agents — health-monitor, runtime-monitor, recovery-monitor."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-mas-controller-health-monitor",
                "sub_mas-mas-controller-runtime-monitor",
                "sub_mas-mas-controller-recovery-monitor"):
        assert sub in content, \
            f"mas-controller must declare sub-agent: {sub}"


def test_mas_controller_5_monitor_domains():
    """Spec: 5 monitor domains — Health, Comms, Memory, Runtime, Arch-Enforcement."""
    content = RECIPE.read_text()
    for domain in ("Health", "Comms", "Memory", "Runtime", "Arch-Enforcement"):
        assert domain in content, \
            f"mas-controller must declare domain: {domain}"
