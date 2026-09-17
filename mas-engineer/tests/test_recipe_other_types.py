"""
test_recipe_other_types.py — sanity tests for docs/.

R110-224 (2026-08-20): REMOVED 8 testproject/ tests. The fixtures
(testproject/workflows.yaml, project.yaml, agent_template.yaml) were
never materialized in git history (R110-141 "moved to archive/testproject"
was verification-theater — the files were never copied). R110-225 will
re-add these tests if/when the fixtures are actually created. Keeping
xfail(skip-disguised) tests was theater — better to delete them and
have an honest test suite.

R110-224 also: REMOVED `requires_testproject` decorator, the
TESTPROJECT path constant, and the ARCHIVE_DOCS_DIR constant (still
referenced for the 3 health-reports / test-reports tests below).

Per R101 EVIDENCE: structural tests, not content tests.

Run with:
    python3 -m pytest tests/test_recipe_other_types.py -v
"""
import re
import pytest
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
DOCS_DIR = REPO_ROOT.parent / "docs"
# Historic timestamped reports (health/test/evidence/changelog) moved to
# archive/docs/ on 2026-08-07 (R110-143 cleanup) — docs/ holds only real docs.
ARCHIVE_DOCS_DIR = REPO_ROOT.parent / "archive" / "docs"


# === docs/ ===

def test_docs_dir_exists():
    assert DOCS_DIR.exists(), f"Missing: {DOCS_DIR}"


def test_docs_minimum_count():
    """docs/ must have >= 20 files (32 actually)."""
    md_files = list(DOCS_DIR.glob("*.md"))
    assert len(md_files) >= 20, \
        f"Expected >= 20 docs, got {len(md_files)}"


def test_docs_have_architecture():
    """Must have architecture doc (docs/architecture.md, current doc)."""
    arch = DOCS_DIR / "architecture.md"
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
    """Health reports for monitoring — at least 3 present (archived)."""
    health = list(ARCHIVE_DOCS_DIR.glob("health-report-*.md"))
    assert len(health) >= 3, \
        f"Expected >= 3 health-reports in archive/docs/, got {len(health)}"


def test_docs_test_reports_present():
    """Test reports — at least 3 present (archived)."""
    reports = list(ARCHIVE_DOCS_DIR.glob("TEST-REPORT-*.md"))
    assert len(reports) >= 3, \
        f"Expected >= 3 test-reports in archive/docs/, got {len(reports)}"


def test_docs_howto_present():
    """HOWTO docs for users — at least 3 present."""
    howto = list(DOCS_DIR.glob("HOWTO-*.md"))
    assert len(howto) >= 3, \
        f"Expected >= 3 HOWTOs, got {len(howto)}"
