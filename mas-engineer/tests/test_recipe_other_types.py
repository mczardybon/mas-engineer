"""
test_recipe_other_types.py — sanity tests for testproject/ + docs/.

Other recipe-related assets:
- testproject/workflows.yaml — generic project workflow definitions
- testproject/project.yaml — project metadata
- testproject/recipe/template/agent_template.yaml — copy of agent_template
- docs/ — 32 documentation files (architecture, procedures, governance)

Per R101 EVIDENCE: structural tests, not content tests.

Run with:
    python3 -m pytest tests/test_recipe_other_types.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
TESTPROJECT = REPO_ROOT.parent / "archive" / "testproject"
DOCS_DIR = REPO_ROOT.parent / "docs"


# === testproject/ ===

def test_testproject_dir_exists():
    assert TESTPROJECT.exists(), f"Missing: {TESTPROJECT}"


def test_testproject_workflows_yaml_exists():
    """workflows.yaml — generic project workflow definitions."""
    path = TESTPROJECT / "workflows.yaml"
    assert path.exists(), f"Missing: {path}"


def test_testproject_workflows_valid():
    with open(TESTPROJECT / "workflows.yaml") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert "workflows" in data, "workflows.yaml must have 'workflows' key"
    assert isinstance(data["workflows"], dict)


def test_testproject_workflows_has_expected_workflows():
    """workflows.yaml must define standard workflows: build-test, analyse, deploy."""
    with open(TESTPROJECT / "workflows.yaml") as f:
        data = yaml.safe_load(f)
    workflows = data["workflows"]
    for wf in ("build-test", "analyse", "deploy"):
        assert wf in workflows, f"Missing workflow: {wf}"


def test_testproject_workflows_version():
    """workflows.yaml must have version field."""
    with open(TESTPROJECT / "workflows.yaml") as f:
        data = yaml.safe_load(f)
    assert "version" in data
    assert data["version"] == "1.0.0"


def test_testproject_project_yaml_exists():
    """project.yaml — project metadata."""
    path = TESTPROJECT / "project.yaml"
    assert path.exists(), f"Missing: {path}"


def test_testproject_project_yaml_valid():
    with open(TESTPROJECT / "project.yaml") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)
    assert data.get("type") == "generic-project"


def test_testproject_agent_template_exists():
    """testproject/recipe/template/agent_template.yaml — copied template."""
    path = TESTPROJECT / "recipe" / "template" / "agent_template.yaml"
    assert path.exists(), f"Missing: {path}"


# === docs/ ===

def test_docs_dir_exists():
    assert DOCS_DIR.exists(), f"Missing: {DOCS_DIR}"


def test_docs_minimum_count():
    """docs/ must have >= 20 files (32 actually)."""
    md_files = list(DOCS_DIR.glob("*.md"))
    assert len(md_files) >= 20, \
        f"Expected >= 20 docs, got {len(md_files)}"


def test_docs_have_architecture():
    """Must have ARCHITECTURE doc."""
    arch = DOCS_DIR / "ARCHITECTURE-E2E-TESTING.md"
    assert arch.exists(), f"Missing: {arch}"


def test_docs_have_governance():
    """Must have governance.md."""
    gov = DOCS_DIR / "governance.md"
    assert gov.exists(), f"Missing: {gov}"


def test_docs_have_procedures():
    """Must have procedures.md."""
    proc = DOCS_DIR / "procedures.md"
    assert proc.exists(), f"Missing: {proc}"


def test_docs_have_manifest():
    """Must have manifest.md (SOT)."""
    manifest = DOCS_DIR / "manifest.md"
    assert manifest.exists(), f"Missing: {manifest}"


def test_docs_health_reports_present():
    """Health reports for monitoring — at least 3 present."""
    health = list(DOCS_DIR.glob("health-report-*.md"))
    assert len(health) >= 3, \
        f"Expected >= 3 health-reports, got {len(health)}"


def test_docs_test_reports_present():
    """Test reports — at least 3 present."""
    reports = list(DOCS_DIR.glob("TEST-REPORT-*.md"))
    assert len(reports) >= 3, \
        f"Expected >= 3 test-reports, got {len(reports)}"


def test_docs_howto_present():
    """HOWTO docs for users — at least 3 present."""
    howto = list(DOCS_DIR.glob("HOWTO-*.md"))
    assert len(howto) >= 3, \
        f"Expected >= 3 HOWTOs, got {len(howto)}"
