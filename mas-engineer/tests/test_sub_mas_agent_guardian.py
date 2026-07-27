"""
test_sub_mas_agent_guardian.py — sanity tests for agent-guardian.

Agent-guardian (v1.0.0) is the MAS-internal watchdog: monitors all
sub-agents for death, drift, loops, and degradation. R10 CORONASHIELD
validates YAML before storing. Writes to .state/guardian.yaml.

Run with:
    python3 -m pytest tests/test_sub_mas_agent_guardian.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-agent-guardian.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-agent-guardian.md"


def test_agent_guardian_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_agent_guardian_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_agent_guardian_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_agent_guardian_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_agent_guardian_instructions_exist():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_agent_guardian_read_only():
    """Spec: GUARDIAN — I patch nothing, I only report."""
    content = RECIPE.read_text()
    assert "GUARDIAN" in content, "agent-guardian must declare GUARDIAN role"
    assert "I patch nothing" in content or "I only report" in content, \
        "agent-guardian must declare read-only contract"


def test_agent_guardian_r10_coronashield():
    """Spec: R10 CORONASHIELD — every YAML validated before storing."""
    content = RECIPE.read_text()
    assert "R10" in content, "agent-guardian must declare R10"
    assert "CORONASHIELD" in content, \
        "agent-guardian must declare CORONASHIELD rule"
    assert "recovery-immune" in content or "sub_mas-recovery-immune" in content, \
        "agent-guardian must use sub_mas-recovery-immune for YAML validation"


def test_agent_guardian_writes_to_health_yaml():
    """Spec: writes Agent Health to .state/guardian.yaml."""
    content = RECIPE.read_text()
    assert "guardian.yaml" in content, \
        "agent-guardian must write to .state/guardian.yaml"
    assert "Agent Health" in content, \
        "agent-guardian must declare Agent Health report"


def test_agent_guardian_external_instructions_ref():
    """Recipe must reference the external instructions file (R37)."""
    content = RECIPE.read_text()
    assert "sub_mas-agent-guardian.md" in content, \
        "Recipe must reference external instructions file (R37)"


def test_agent_guardian_monitors_drift_death_loops():
    """Spec: monitors death, drift, loops, degradation."""
    content = RECIPE.read_text()
    # At least 3 of 4 must be mentioned
    found = []
    for metric in ("death", "drift", "loop", "degradation"):
        if metric in content.lower():
            found.append(metric)
    assert len(found) >= 3, \
        f"agent-guardian must monitor death/drift/loops/degradation. found: {found}"
