"""
test_sub_mas_dashboard_refresh.py — sanity tests for dashboard-refresh.

dashboard-refresh v1.0.0 is the user-refresh orchestrator
(MAS-internal): Orchestrates dashboard generation by delegating
to specialized sub-agents (NN1 split).
- dashboard-collector → sub_mas-dashboard-collector
- dashboard-builder → sub_mas-dashboard-builder

NO daemon. NO polling. ONLY orchestration.

Per R101 EVIDENCE: R01+R09+R10 (full controller pattern).

Run with:
    python3 -m pytest tests/test_sub_mas_dashboard_refresh.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-dashboard-refresh.yaml"


def test_refresh_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_refresh_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_refresh_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_refresh_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_refresh_orchestrator_role():
    """Spec: User refresh orchestrator — delegates to 2 sub-agents."""
    content = RECIPE.read_text()
    assert "Orchestrates" in content or "orchestrat" in content.lower() \
        or "Orchestrator" in content, \
        "refresh must declare orchestrator role"
    assert "dashboard" in content.lower(), \
        "refresh must declare dashboard scope"
    assert "User refresh" in content or "user refresh" in content.lower(), \
        "refresh must declare user-refresh scope"


def test_refresh_only_orchestration():
    """Spec: ONLY orchestration — NO direct data collection or building."""
    content = RECIPE.read_text()
    assert "ONLY orchestration" in content, \
        "refresh must declare ONLY-orchestration rule"
    assert "NO direct data collection" in content \
        or "no direct data collection" in content.lower(), \
        "refresh must forbid direct data collection (combined-list)"
    assert "dashboard building" in content.lower() or "NO direct" in content, \
        "refresh must forbid direct dashboard building (combined-list)"


def test_refresh_no_daemon_no_polling():
    """Spec: NO daemon, NO polling."""
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert "NO daemon" in flat or "no daemon" in flat.lower(), \
        "refresh must declare NO-daemon"
    assert "NO polling" in flat or "no polling" in flat.lower(), \
        "refresh must declare NO-polling"


def test_refresh_delegation_map():
    """Spec: 2-way delegation map (NN1 split: collector+builder)."""
    content = RECIPE.read_text()
    for sub in ("sub_mas-dashboard-collector",
                "sub_mas-dashboard-builder"):
        assert sub in content, \
            f"refresh must reference {sub} in delegation map"


def test_refresh_2_sub_recipes():
    """Spec: exactly 2 sub_recipes (NN1 split)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert len(subs) == 2, \
        f"refresh must have 2 sub_recipes, got {len(subs)}: {subs}"


def test_refresh_settings():
    """Spec: orchestrator settings (timeout=600, max_turns=100, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "refresh must have timeout=600 (orchestrator)"
    assert settings.get("max_turns") == 100, \
        "refresh must have max_turns=100 (orchestrator)"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "refresh must use deepseek model"


def test_refresh_r01_r09_r10():
    """Spec: R01, R09, R10 (full controller pattern)."""
    content = RECIPE.read_text()
    assert "R01" in content, "refresh must declare R01"
    assert "R09" in content, "refresh must declare R09"
    assert "R10" in content, "refresh must declare R10"
    assert "CORONASHIELD" in content, \
        "refresh must declare CORONASHIELD"
