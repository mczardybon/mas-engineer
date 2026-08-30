"""
test_r110308_self_audit_index.py — R110-308: cover _build_repo_literal_index
loops in dev_self_audit that the existing test does not exercise.

Specifically these lines were uncovered:
  - L155-156: open(file) exception path (perms/encoding)
  - L159-161: _B_COUNT_PHRASE_RE indexing loop ("12 tests", "5 issues")
  - L162-163: _B_PATH_LIKE_RE indexing loop (./tools/foo.py)
  - L164-170: _B_YAML_BARE_NAME_RE + self-reference exclusion (sub_mas-*)

Patterns (from tools/dev_self_audit.py L65-76):
  _B_PATH_LIKE_RE     = ^(?:\\./)?[\\w./\\-]+/[\\w./\\-]+\\.(?:yaml|py|md|json|sh|txt)$
  _B_COUNT_PHRASE_RE  = ^\\d{2,}\\s+(?:critical\\s+)?(?:checks?|tests?|sub-agents|tools|
                         phases|rules?|findings?|stages|agents|steps)$
  _B_YAML_BARE_NAME_RE= \\bname:\\s*(sub_mas-[\\w-]+)\\b
"""
import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"


@pytest.fixture
def fixture_repo():
    """Build a tiny fixture repo with pattern-B content + self-referencing YAML.

    Note: _B_COUNT_PHRASE_RE has ^...$ anchors WITHOUT re.MULTILINE flag, so
    the whole FILE must be just the count phrase. We use single-line files
    to exercise the count-phrase loop.

    For _B_PATH_LIKE_RE (which has re.MULTILINE), we use a file with a
    whole-line path-like.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        for sub in ("recipe", "tools", "docs", "tests"):
            (root / sub).mkdir()
        # Single-line file (whole-file match for _B_COUNT_PHRASE_RE)
        (root / "tools" / "fake1.py").write_text("12 tests\n")
        # File with a path-like as its own line (MULTILINE-aware)
        (root / "tools" / "fake2.py").write_text(
            "# See the recipe below\n"
            "./recipe/demo.yaml\n"
        )
        # Self-referencing YAML: name matches sub_mas-* AND file IS the definition
        (root / "recipe" / "sub_mas-demo.yaml").write_text(
            "name: sub_mas-demo\n"
            "title: Demo Recipe\n"
        )
        # Different sub_mas-* reference in a different file (NOT self-ref)
        (root / "recipe" / "main_recipe.yaml").write_text(
            "name: main-recipe\n"
            "sub_recipes:\n"
            "  - name: sub_mas-demo\n"     # bare-name ref to demo sub_mas
            "  - name: sub_mas-other\n"
        )
        yield root


def test_build_repo_literal_index_indexes_count_phrases(fixture_repo):
    """_B_COUNT_PHRASE_RE loop fires for '12 tests' (2+ digits + plural)."""
    sys.path.insert(0, str(TOOLS))
    try:
        from dev_self_audit import _build_repo_literal_index
    finally:
        sys.path.pop(0)

    index = _build_repo_literal_index(fixture_repo, exclude_path="(no-match)")
    assert "12 tests" in index, f"Expected '12 tests' in index, got keys: {sorted(list(index.keys()))[:15]}"


def test_build_repo_literal_index_indexes_path_like(fixture_repo):
    """_B_PATH_LIKE_RE loop fires for './recipe/demo.yaml'."""
    sys.path.insert(0, str(TOOLS))
    try:
        from dev_self_audit import _build_repo_literal_index
    finally:
        sys.path.pop(0)

    index = _build_repo_literal_index(fixture_repo, exclude_path="(no-match)")
    assert "./recipe/demo.yaml" in index, \
        f"Expected './recipe/demo.yaml' in index, got keys: {sorted(list(index.keys()))[:15]}"


def test_build_repo_literal_index_excludes_self_reference():
    """_B_YAML_BARE_NAME_RE: sub_mas-demo.yaml's own 'name: sub_mas-demo' is excluded
    but a different file's reference to sub_mas-demo IS indexed."""
    import sys
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        for sub in ("recipe", "tools", "docs", "tests"):
            (root / sub).mkdir()
        # Self-referencing YAML: name matches sub_mas-* AND file IS the definition
        (root / "recipe" / "sub_mas-demo.yaml").write_text(
            "name: sub_mas-demo\n"
            "title: Demo Recipe\n"
        )
        # Another file that references sub_mas-demo (NOT a self-ref because
        # this file is not named sub_mas-demo)
        (root / "tools" / "fake3.py").write_text(
            "TARGET = 'recipe'\n"
            "name: sub_mas-demo\n"  # bare-name ref to demo
        )
        sys.path.insert(0, str(TOOLS))
        try:
            from dev_self_audit import _build_repo_literal_index
        finally:
            sys.path.pop(0)
        index = _build_repo_literal_index(root, exclude_path="(no-match)")
        # 'sub_mas-demo' IS indexed (from fake3.py's non-self ref)
        # BUT if it were also in the self-ref file, that contribution would be skipped
        # The count is 1, meaning only the non-self-ref was counted
        assert "sub_mas-demo" in index, f"Expected 'sub_mas-demo' from non-self-ref"
        assert index["sub_mas-demo"] == 1, \
            f"Expected count=1 (self-ref excluded), got {index['sub_mas-demo']}"


def test_build_repo_literal_index_skips_excluded_path(fixture_repo):
    """exclude_path removes a single file from the index."""
    sys.path.insert(0, str(TOOLS))
    try:
        from dev_self_audit import _build_repo_literal_index
    finally:
        sys.path.pop(0)

    fake1 = fixture_repo / "tools" / "fake1.py"
    index = _build_repo_literal_index(fixture_repo, exclude_path=str(fake1))
    # fake1.py is excluded → "12 tests" should NOT be in
    assert "12 tests" not in index, "Excluded file's content should not be indexed"
    # fake2.py still contributes the path-like
    assert "./recipe/demo.yaml" in index, "Non-excluded file should still be indexed"


def test_build_repo_literal_index_handles_open_exception(fixture_repo, monkeypatch):
    """open(file) exception path is silently skipped (L153-156)."""
    sys.path.insert(0, str(TOOLS))
    try:
        from dev_self_audit import _build_repo_literal_index
    finally:
        sys.path.pop(0)

    real_open = open

    def fake_open(file, *a, **kw):
        if str(file).endswith("fake1.py"):
            raise OSError("simulated permission denied")
        return real_open(file, *a, **kw)

    monkeypatch.setattr("builtins.open", fake_open)
    # Should not raise, just skip the file
    index = _build_repo_literal_index(fixture_repo, exclude_path="(no-match)")
    # fake1.py's "12 tests" is not indexed because open() failed
    assert "12 tests" not in index
    # fake2.py still works
    assert "./recipe/demo.yaml" in index


def test_build_repo_literal_index_skips_pycache_and_backups(fixture_repo):
    """__pycache__/.pyc/.backups paths are excluded (L149-150)."""
    sys.path.insert(0, str(TOOLS))
    try:
        from dev_self_audit import _build_repo_literal_index
    finally:
        sys.path.pop(0)

    # __pycache__ dir with a .pyc file containing a single-line count phrase
    pyc_dir = fixture_repo / "tools" / "__pycache__"
    pyc_dir.mkdir()
    (pyc_dir / "fake1.cpython-310.pyc").write_text("77 tests\n")
    # .backups dir
    backup_dir = fixture_repo / "tools" / ".backups"
    backup_dir.mkdir()
    (backup_dir / "old.py").write_text("88 tests\n")
    index = _build_repo_literal_index(fixture_repo, exclude_path="(no-match)")
    # Real fake1.py: "12 tests" IS indexed (whole-file match)
    assert "12 tests" in index, f"Expected '12 tests', got keys: {sorted(list(index.keys()))[:15]}"
    # Neither pyc nor backup content should leak in
    assert "77 tests" not in index
    assert "88 tests" not in index
