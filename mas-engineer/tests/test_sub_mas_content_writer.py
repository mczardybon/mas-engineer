"""
test_sub_mas_content_writer.py — sanity tests for content-writer.

content-writer v1.0.0 is the marketing content creation specialist:
blog posts, landing page copy, ad copy. Single-role leaf.

Per R101 EVIDENCE: content-writer has 0 R-number rules
(marketing content creator, no YAML/framework interaction).

R110-55: content-writer moved from recipe/sub/ to
demos/demo-team/recipes/ (it's a demo-team agent, not a
framework internal).

Run with:
    python3 -m pytest tests/test_sub_mas_content_writer.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
# R110-55: content-writer is a demo-team agent, lives in
# demos/demo-team/recipes/ (not recipe/sub/)
RECIPE = REPO_ROOT / "demos" / "demo-team" / "recipes" / "sub_mas-content-writer.yaml"


def test_content_writer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_content_writer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_content_writer_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_content_writer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_content_writer_role():
    """Spec: Content creation specialist (blog posts, landing page, ad copy)."""
    content = RECIPE.read_text()
    assert "Content creation" in content or "content creation" in content.lower(), \
        "content-writer must declare content-creation role"
    assert "blog" in content.lower() or "Blog" in content, \
        "content-writer must declare blog-post capability"
    assert "marketing" in content.lower() or "Marketing" in content, \
        "content-writer must declare marketing scope"
    # At least one of: landing page, ad copy
    assert "landing" in content.lower() or "ad copy" in content.lower() \
        or "advertising" in content.lower(), \
        "content-writer must declare landing page or ad copy capability"


def test_content_writer_no_sub_recipes():
    """Single-role leaf — no sub_recipes."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "content-writer must be single-role leaf"


def test_content_writer_settings():
    """Spec: sub-agent settings (timeout=600, max_steps=100, temperature=0.3)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    settings = data.get("settings", {})
    assert settings.get("timeout") == 600, \
        "content-writer must have timeout=600"
    assert settings.get("max_steps") == 100, \
        "content-writer must have max_steps=100"
    assert settings.get("temperature") == 0.3, \
        "content-writer must have temperature=0.3"


def test_content_writer_no_r_rules():
    """Spec: content-writer has 0 R-number rules.
    Per R101 EVIDENCE: content creator, no framework/rule interaction.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    assert flat.count("R0") == 0, \
        f"content-writer must not restate R-rules. Found: {flat.count('R0')}"


def test_content_writer_focus():
    """Spec: content-writer is a Demo-Team marketing generator
    (content-writer is a sub-agent within MAS-Engineer framework,
    but its job is marketing content, not framework engineering).

    Per R101 EVIDENCE: content-writer is a Demo-Team generator,
    so it has marketing-focus, not engineering-focus.
    """
    content = RECIPE.read_text()
    flat = re.sub(r"\s+", " ", content)
    # Should focus on marketing/creative content
    assert "marketing" in flat.lower(), \
        "content-writer must focus on marketing"
    # Should NOT contain framework engineering concerns (R-rules, YAML storage, R10)
    for rule_keyword in ("R01", "R10", "CORONASHIELD"):
        assert rule_keyword not in flat, \
            f"content-writer must NOT have framework rule {rule_keyword}"


def test_content_writer_marketing_focus():
    """Spec: content-writer focuses on marketing/creative content."""
    content = RECIPE.read_text()
    # Marketing-related keywords should appear
    for kw in ("blog", "copy", "marketing"):
        assert kw.lower() in content.lower(), \
            f"content-writer must mention {kw} (marketing focus)"
