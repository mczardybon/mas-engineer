"""
test_sub_mas_doc_writer.py — sanity tests for doc-writer.

Doc-writer v1.0.0 maintains .md files ONLY. SOT WORKFLOW CONTROL
via workflows.yaml → agents.doc-writer.task_workflows.UPDATE.
NEVER edits .py/.yaml/.json files. Supports UPDATE|CREATE|CONSISTENCY.

Note: doc-writer has NO 'prompt:' field — only 'instructions:'.
The required-fields test is adapted accordingly.

Run with:
    python3 -m pytest tests/test_sub_mas_doc_writer.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-doc-writer.yaml"


def test_doc_writer_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_doc_writer_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_doc_writer_recipe_has_required_fields():
    """Adapted: doc-writer has instructions/settings/extensions but
    NO prompt field. Required fields are the ones it actually has."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_doc_writer_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_doc_writer_sot_workflow_control():
    """Spec: SOT WORKFLOW CONTROL via workflows.yaml."""
    content = RECIPE.read_text()
    assert "workflows.yaml" in content, \
        "doc-writer must reference workflows.yaml SOT"
    assert "SOT WORKFLOW" in content, \
        "doc-writer must declare SOT WORKFLOW CONTROL"
    assert "agents.doc-writer" in content or "doc-writer" in content, \
        "doc-writer must reference its own agent slot"


def test_doc_writer_md_files_only():
    """Spec: ONLY .md files — NEVER .py/.yaml/.json."""
    content = RECIPE.read_text()
    assert "Only .md" in content or "only .md" in content, \
        "doc-writer must declare .md-only rule"
    assert "NEVER edit .py" in content or ".py/.yaml/.json" in content, \
        "doc-writer must forbid editing .py/.yaml/.json"


def test_doc_writer_3_tasks():
    """Spec: 3 tasks — UPDATE, CREATE, CONSISTENCY."""
    content = RECIPE.read_text()
    for task in ("UPDATE", "CREATE", "CONSISTENCY"):
        assert task in content, \
            f"doc-writer must declare task: {task}"


def test_doc_writer_tools():
    """Spec: write, edit, grep, delegate tools."""
    content = RECIPE.read_text()
    for tool in ("write", "edit", "grep", "delegate"):
        assert tool in content, \
            f"doc-writer must declare tool: {tool}"


def test_doc_writer_no_sub_recipes():
    """Doc-writer is a single-role leaf node (no sub_recipes)."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert "sub_recipes" not in data or not data["sub_recipes"], \
        "doc-writer must be a single-role leaf node"


def test_doc_writer_mas_internal():
    """Spec: MAS-Engineer-internal — for maintainability tooling."""
    content = RECIPE.read_text()
    assert "MAS-Engineer-internal" in content or "MAS-internal" in content, \
        "doc-writer must declare MAS-internal role"
