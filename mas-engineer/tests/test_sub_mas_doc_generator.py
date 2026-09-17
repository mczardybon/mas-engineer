"""
test_sub_mas_doc_generator.py — sanity tests for doc-generator.

Doc-generator v1.0.0 checks doc currency, generates diffs after
framework changes. Uses R37 external instructions file
(recipe/instructions/sub_mas-doc-generator.md).

Run with:
    python3 -m pytest tests/test_sub_mas_doc_generator.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-doc-generator.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-doc-generator.md"


def test_doc_generator_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_doc_generator_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_doc_generator_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_doc_generator_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_doc_generator_external_instructions():
    """R37: uses external instructions file."""
    content = RECIPE.read_text()
    assert "sub_mas-doc-generator.md" in content, \
        "doc-generator must reference external instructions file (R37)"
    assert "Extended instructions" in content or "external" in content.lower(), \
        "doc-generator must declare external instructions pattern"


def test_doc_generator_instructions_file_exists():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_doc_generator_only_analysis():
    """Spec: ONLY analysis — no changes."""
    content = RECIPE.read_text()
    assert "Only analysis" in content or "only analysis" in content.lower(), \
        "doc-generator must declare ONLY-analysis rule"
    assert "no changes" in content.lower(), \
        "doc-generator must forbid changes"


def test_doc_generator_docs_currency():
    """Spec: checks doc currency and generates diffs."""
    content = RECIPE.read_text()
    assert "currency" in content.lower() or "Documentation Currency" in content, \
        "doc-generator must check docs currency"
    assert "diff" in content.lower(), \
        "doc-generator must generate diffs"


def test_doc_generator_no_sub_recipes():
    """Doc-generator is a single-role leaf node."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "doc-generator must be a single-role leaf node"


def test_doc_generator_framework_change_trigger():
    """Spec: triggers after framework changes."""
    content = RECIPE.read_text()
    assert "framework" in content.lower(), \
        "doc-generator must reference framework changes"
