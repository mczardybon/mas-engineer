"""
test_recipe_agent_template.py — sanity tests for agent_template.yaml.

agent_template.yaml is the template for creating new sub_mas agents.
Used by recipe-manager when installing new agents.

Per R101 EVIDENCE: template recipe (not a real sub-agent).

Run with:
    python3 -m pytest tests/test_recipe_agent_template.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
TEMPLATE = REPO_ROOT / "recipe" / "template" / "agent_template.yaml"


def test_template_exists():
    assert TEMPLATE.exists(), f"Missing: {TEMPLATE}"


def test_template_is_valid_yaml():
    with open(TEMPLATE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_template_has_required_fields():
    """Template should have all fields that a real sub_mas recipe has."""
    with open(TEMPLATE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "title", "description",
                  "instructions", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_template_references_master_constitution():
    """Template should reference master constitution (like real recipes).

    Note: template uses {name} placeholder, so constitution field
    is set by recipe-manager when generating the actual recipe.
    """
    with open(TEMPLATE) as f:
        data = yaml.safe_load(f)
    # Either constitution is set OR template uses placeholder
    constitution = data.get("constitution", "")
    assert "master-constitution" in constitution \
        or "sub_mas-master-constitution.yaml" in constitution \
        or data.get("name") == "sub_mas-{name}", \
        "agent_template must either set constitution or use {name} placeholder"


def test_template_has_placeholders():
    """Template should have { } placeholders for substitution."""
    with open(TEMPLATE) as f:
        content = f.read()
    # Template uses {name}, {EMOJI}, {TASK} etc (not Jinja2 {{ }})
    placeholders = re.findall(r"\{[A-Z_][A-Z0-9_]*\}", content)
    assert len(placeholders) >= 2, \
        f"Template must have placeholders, found {len(placeholders)}"


def test_template_settings():
    """Template should have standard settings (timeout, max_steps, etc)."""
    with open(TEMPLATE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert "timeout" in settings, "Template settings must have timeout"
    assert "max_steps" in settings, "Template settings must have max_steps"


def test_template_role():
    """Template should declare it's a template (via {name} placeholder)."""
    with open(TEMPLATE) as f:
        data = yaml.safe_load(f)
    # Template uses {name} placeholder, which indicates it's a template
    assert data.get("name") == "sub_mas-{name}", \
        "agent_template name must be 'sub_mas-{name}' (placeholder)"
