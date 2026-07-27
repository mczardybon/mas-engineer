"""
test_sub_mas_system_knowledge.py — sanity tests for system-knowledge.

system-knowledge v1.0.0 is the system-knowledge base (MAS-internal):
Covers Architecture, Communication, Installation, Recovery, Rules,
Tools, Agents, Build. Read-only knowledge base.

Per R101 EVIDENCE: R10 (1x) only (read-only knowledge base,
no R01/R09).

Run with:
    python3 -m pytest tests/test_sub_mas_system_knowledge.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-system-knowledge.yaml"


def test_system_knowledge_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_system_knowledge_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_system_knowledge_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_system_knowledge_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_system_knowledge_role():
    """Spec: MAS-internal: System knowledge base covering 8 domains.
    Required domains: Architecture, Communication, Installation,
    Recovery, Rules, Tools, Agents, Build.
    """
    content = RECIPE.read_text()
    required_domains = [
        "Architecture", "Communication", "Installation",
        "Recovery", "Rules", "Tools", "Agents", "Build"
    ]
    for domain in required_domains:
        assert domain in content, \
            f"system-knowledge must reference {domain} domain"


def test_system_knowledge_read_only():
    """Spec: Read-only knowledge base.

    Note: the recipe delegates to .md file which has:
    L8: "MAS knows the framework. The framework does NOT know MAS."
    L1: "Complete system knowledge — loaded automatically"
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Recipe delegates to external .md file — check the .md file
    md_path = REPO_ROOT / "recipe" / "instructions" / "sub_mas-system-knowledge.md"
    if md_path.exists():
        md_content = md_path.read_text()
        md_flat = re.sub(r"\s+", " ", md_content)
        assert "system knowledge" in md_flat.lower() \
            or "loaded automatically" in md_flat.lower() \
            or "knowledge base" in md_flat.lower() \
            or "MAS knows" in md_flat, \
            "system-knowledge .md must declare system knowledge / loaded automatically"


def test_system_knowledge_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "system-knowledge must be single-role leaf"


def test_system_knowledge_settings():
    """Spec: sub-agent settings (timeout=120, max_steps=30, deepseek)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 120, \
        "system-knowledge must have timeout=120"
    assert settings.get("max_steps") == 30, \
        "system-knowledge must have max_steps=30"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "system-knowledge must use deepseek model"


def test_system_knowledge_r10_only():
    """Spec: R10 (1x) only — no R01, no R09.
    Per R101 EVIDENCE: read-only knowledge base, doesn't modify YAMLs.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R10") >= 1, \
        f"system-knowledge must declare R10. Found: {flat.count('R10')}"
    assert "CORONASHIELD" in flat, \
        "system-knowledge must declare CORONASHIELD"
    assert "R01" not in flat, \
        "system-knowledge must NOT have R01 (read-only)"
    assert "R09" not in flat, \
        "system-knowledge must NOT have R09 (read-only)"


def test_system_knowledge_uses_recovery_immune():
    """Spec: R10 CORONASHIELD delegates YAML validation to
    sub_mas-recovery-immune.
    """
    content = RECIPE.read_text()
    assert "sub_mas-recovery-immune" in content, \
        "system-knowledge must reference sub_mas-recovery-immune"
