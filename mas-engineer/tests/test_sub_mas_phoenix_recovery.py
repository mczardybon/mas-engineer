"""
test_sub_mas_phoenix_recovery.py — sanity tests for sub_mas-phoenix-recovery.

Orchestrator that runs the 5 recovery levels (immune → checkpoint → safezone
→ timeline → defib) in sequence. Each level is delegated to its specialized
sub-agent (sub_mas-recovery-{immune,checkpoint,safezone,timeline,defib}).

Per docs/TEST-COVERAGE-POLICY.md:125, this is a R103 phase-1 candidate.

Run with:
    python3 -m pytest tests/test_sub_mas_phoenix_recovery.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-phoenix-recovery.yaml"

FIVE_LEVELS = ("immune", "checkpoint", "safezone", "timeline", "defib")
FIVE_SUB_AGENTS = tuple(f"sub_mas-recovery-{lvl}" for lvl in FIVE_LEVELS)


def test_phoenix_recovery_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_phoenix_recovery_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_phoenix_recovery_recipe_has_required_fields():
    """Spec: name + version + constitution + title + description + instructions
    + prompt + settings + extensions."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "constitution", "title", "description",
                  "instructions", "prompt", "settings", "extensions"):
        assert field in data, f"Missing required field: {field}"


def test_phoenix_recovery_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_phoenix_recovery_is_orchestrator():
    """Spec: orchestrator that runs the 5 recovery levels in sequence."""
    content = RECIPE.read_text()
    assert "Orchestrat" in content or "orchestrator" in content.lower(), \
        "phoenix-recovery must be an orchestrator"
    assert "5-Level" in content or "5 recovery" in content or \
           "5 recovery levels" in content, \
        "phoenix-recovery must declare 5 recovery levels"


def test_phoenix_recovery_declares_all_5_levels():
    """Spec: IMMUNE → CHECKPOINT → SAFEZONE → TIMELINE → DEFIB."""
    content = RECIPE.read_text()
    for level in FIVE_LEVELS:
        assert level.upper() in content, \
            f"phoenix-recovery must reference level {level.upper()}"


def test_phoenix_recovery_order_immune_first_defib_last():
    """Spec: order is escalating severity (immune=light, defib=last resort)."""
    content = RECIPE.read_text()
    pos_immune = content.upper().find("IMMUNE")
    pos_checkpoint = content.upper().find("CHECKPOINT")
    pos_safezone = content.upper().find("SAFEZONE")
    pos_timeline = content.upper().find("TIMELINE")
    pos_defib = content.upper().find("DEFIB")
    assert pos_immune < pos_checkpoint < pos_safezone < pos_timeline < pos_defib, \
        f"phoenix-recovery must order levels: immune({pos_immune}) < " \
        f"checkpoint({pos_checkpoint}) < safezone({pos_safezone}) < " \
        f"timeline({pos_timeline}) < defib({pos_defib})"


def test_phoenix_recovery_references_all_5_sub_agents():
    """Spec: delegates each level to sub_mas-recovery-{level}."""
    content = RECIPE.read_text()
    for sub in FIVE_SUB_AGENTS:
        assert sub in content, \
            f"phoenix-recovery must reference sub-agent: {sub}"


def test_phoenix_recovery_has_reasonable_settings():
    """Spec: timeout >= 300 (5 levels, each up to 60s), max_steps >= 50."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout", 0) >= 300, \
        f"phoenix-recovery timeout must be >= 300 (5 levels), got {settings.get('timeout')}"
    assert settings.get("max_steps", 0) >= 50, \
        f"phoenix-recovery max_steps must be >= 50, got {settings.get('max_steps')}"


def test_phoenix_recovery_has_required_extensions():
    """Spec: summon + developer extensions (parity with other sub-agents)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    ext_names = [e.get("name") for e in data.get("extensions", [])]
    assert "summon" in ext_names, "phoenix-recovery must have summon extension"
    assert "developer" in ext_names, "phoenix-recovery must have developer extension"


def test_phoenix_recovery_r10_coronashield_reference():
    """Spec: R10 CORONASHIELD — every YAML save must be validated by sub_mas-recovery-immune."""
    content = RECIPE.read_text()
    assert "R10" in content and "CORONASHIELD" in content, \
        "phoenix-recovery must reference R10 CORONASHIELD"
    assert "sub_mas-recovery-immune" in content, \
        "phoenix-recovery must reference sub_mas-recovery-immune for R10"


def test_phoenix_recovery_5_target_sub_agents_exist_on_disk():
    """Spec: all 5 delegated sub-agents must exist as recipe files."""
    for sub in FIVE_SUB_AGENTS:
        path = REPO_ROOT / "recipe" / "sub" / f"{sub}.yaml"
        assert path.exists(), f"Missing delegated sub-agent: {path}"


def test_phoenix_recovery_5_target_workflows_exist():
    """Spec: all 5 wf_recovery_* workflows must exist in .mase/workflows.yaml."""
    wf_path = REPO_ROOT / ".mase" / "workflows.yaml"
    with open(wf_path) as f:
        content = f.read()
    for level in FIVE_LEVELS:
        assert f"wf_recovery_{level}:" in content, \
            f"Missing workflow wf_recovery_{level} in {wf_path}"
