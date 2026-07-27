"""
test_sub_mas_framework_knowledge.py — sanity tests for framework-knowledge.

framework-knowledge v1.0.0 discovers framework structure
dynamically, extracts concepts from EVERY file, explains,
analyzes impact, generates blueprints. Has sub_mas-yaml-editor
as sub-recipe.

Per R101 EVIDENCE: framework-knowledge has only R10+CORONASHIELD
(no R01/R04/R05/R09). It's the only framework recipe with a
sub_recipes block (yaml-editor).

Run with:
    python3 -m pytest tests/test_sub_mas_framework_knowledge.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-framework-knowledge.yaml"


def test_framework_knowledge_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_framework_knowledge_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_framework_knowledge_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_framework_knowledge_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_framework_knowledge_dynamic_discovery():
    """Spec: discovers framework structure dynamically — no hardcoded paths."""
    content = RECIPE.read_text()
    assert "dynamic" in content.lower() or "dynamically" in content.lower(), \
        "framework-knowledge must declare dynamic discovery"
    assert "No hardcoded paths" in content or "no hardcoded" in content.lower() \
        or "everything dynamically" in content, \
        "framework-knowledge must forbid hardcoded paths"


def test_framework_knowledge_yaml_editor_sub_recipe():
    """Spec: 1 sub_recipe — sub_mas-yaml-editor (parses and edits YAML)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-yaml-editor" in subs, \
        f"framework-knowledge must delegate to sub_mas-yaml-editor. subs: {subs}"


def test_framework_knowledge_settings():
    """Spec: standard settings (timeout=600, max_steps=100, deepseek-v4-flash)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "framework-knowledge must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "framework-knowledge must have max_steps=100"
    assert "deepseek" in settings.get("goose_model", "").lower(), \
        "framework-knowledge must use deepseek model"


def test_framework_knowledge_5_capabilities():
    """Spec: 5 capabilities — discovers, extracts, explains, analyzes,
    generates (blueprints).
    """
    content = RECIPE.read_text()
    for cap in ("Discovers", "extracts", "explains",
                "analyzes", "generates"):
        assert cap in content, \
            f"framework-knowledge must declare capability: {cap}"


def test_framework_knowledge_r10_coronashield():
    """Spec: R10 + CORONASHIELD (per R101 EVIDENCE — only rule declared)."""
    content = RECIPE.read_text()
    assert "R10" in content, "framework-knowledge must declare R10"
    assert "CORONASHIELD" in content, \
        "framework-knowledge must declare CORONASHIELD"


def test_framework_knowledge_no_r01_r04_r05_r09():
    """Spec: per R101 EVIDENCE, this recipe has NO R01/R04/R05/R09.
    It's a discovery/blueprint agent, not an action-taker.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R01") == 0, \
        "framework-knowledge must NOT have R01 (discovery, no changes)"
    assert flat.count("R04") == 0, \
        "framework-knowledge must NOT have R04 (no recursion needed)"
