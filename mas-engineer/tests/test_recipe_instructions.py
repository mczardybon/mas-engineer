"""
test_recipe_instructions.py — sanity tests for instruction manuals.

recipe/instructions/*.md contains extended instructions for sub_mas
recipes that delegate long content to external files.

Per R101 EVIDENCE: 43 sub_mas-*.md files + 2 non-sub .md files
(security-scanner, static-analyzer) = 45 total.

Run with:
    python3 -m pytest tests/test_recipe_instructions.py -v
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
INST_DIR = REPO_ROOT / "recipe" / "instructions"


def test_instructions_dir_exists():
    assert INST_DIR.exists(), f"Missing: {INST_DIR}"


def test_instructions_have_sub_mas_files():
    """Most instructions should be sub_mas-*.md files."""
    md_files = list(INST_DIR.glob("sub_mas-*.md"))
    assert len(md_files) >= 30, \
        f"Expected >= 30 sub_mas-*.md files, got {len(md_files)}"


def test_instructions_have_non_sub_files():
    """Some instructions are for non-sub recipes (e.g. security-scanner)."""
    non_sub = [f for f in INST_DIR.glob("*.md")
               if not f.name.startswith("sub_mas-")]
    assert len(non_sub) >= 1, \
        f"Expected >= 1 non-sub instruction file, got {len(non_sub)}"
    # These should be security-scanner + static-analyzer
    names = [f.name for f in non_sub]
    assert "security-scanner.md" in names, \
        "Expected security-scanner.md in non-sub instructions"


def test_instructions_non_empty():
    """All instruction files should have content (not empty)."""
    empty = []
    for f in INST_DIR.glob("*.md"):
        if f.stat().st_size < 50:  # Less than 50 bytes
            empty.append(f.name)
    assert not empty, f"Empty/near-empty instructions: {empty}"


def test_instructions_have_title():
    """Most instructions should have # title at top."""
    missing_title = []
    for f in INST_DIR.glob("sub_mas-*.md"):
        content = f.read_text()
        if not re.search(r"^#\s+\S", content, re.MULTILINE):
            missing_title.append(f.name)
    # Allow up to 5% missing title (some may use other formats)
    max_missing = max(2, len(list(INST_DIR.glob("sub_mas-*.md"))) // 20)
    assert len(missing_title) <= max_missing, \
        f"Too many instructions without title: {missing_title[:5]}"


def test_instructions_reference_constitution_or_rules():
    """Instructions should reference R-rules (R01, R09, etc.) or
    master constitution.
    """
    found_rules = 0
    for f in INST_DIR.glob("sub_mas-*.md"):
        content = f.read_text()
        if re.search(r"R0[149]", content) or "master-constitution" in content \
                or "MASTER-CONSTITUTION" in content \
                or "MAS-Engineer" in content or "MAS-ENGINEER" in content:
            found_rules += 1
    assert found_rules >= 20, \
        f"Expected >= 20 instructions referencing R-rules/constitution, " \
        f"got {found_rules}"


def test_instructions_sub_mas_count():
    """Spec: 43 sub_mas-*.md instruction files."""
    md = list(INST_DIR.glob("sub_mas-*.md"))
    assert len(md) >= 40, \
        f"Expected >= 40 sub_mas-*.md files, got {len(md)}"
