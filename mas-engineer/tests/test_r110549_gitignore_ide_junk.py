"""R110-549 — verify .gitignore prevents IDE auto-save junk from being committed.

Background (R110-549, 2026-09-14): R110-408/410 fixed single-junk commits,
R110-546/547 cleaned up multi-junk via revert + EXEMPT_HASHES. The root
cause (IDE/editor not honoring existing .gitignore for adjacent files)
was addressed by adding 5 backup-pattern globs to .gitignore:
  - **/*.llm-backup-*
  - **/*.bak.[0-9]*    (timestamped `.bak.YYYYMMDD_HHMMSS`)
  - **/*.yaml.orig
  - **/*.yaml.rej
  - **/*~              (emacs backup)

This test creates files matching each pattern INSIDE the repo (so git
check-ignore can locate the .gitignore via parent-dir walk), and asserts
that git check-ignore reports them as ignored.

Pre-existing tracked backup files (`sub_mas-im-session-reader.yaml.llm-backup-r89`,
`sub_mas-recovery-immune.yaml.llm-backup-r89`) are intentionally still
tracked because they were committed before R110-549 added the pattern;
removing them from history would require force-push (forbidden per
R110-281). This test asserts the PATTERN, not absence of pre-existing
tracked files (since `git rm --cached` would be a separate R110-550+ task).
"""
import os
import subprocess


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Pick a unique untracked dir under an existing tracked dir we trust.
# `tests/` is tracked and not parent-ignored, so test files inside it
# have NO parent-dir ignore, meaning individual pattern-matches can be
# checked without the parent dominating.
TEST_PARENT = os.path.join(REPO_ROOT, "tests", "_r110549_testartifacts")
TEST_PARENT_REL = os.path.join("tests", "_r110549_testartifacts")


def _check_ignore(rel_path):
    """Returns (gitignore:line:pattern, matched_path) or None."""
    out = subprocess.run(
        ["git", "check-ignore", "-v", rel_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if out.returncode == 0:
        # stdout: ".gitignore:<line>:<pattern>\t<path>"
        parts = out.stdout.strip().split("\t")
        return (parts[0], parts[1])
    return None


def _make_test_file(rel_path):
    """Create a file inside the repo (so git can find .gitignore)."""
    abs_path = os.path.join(REPO_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    open(abs_path, "w").close()
    return abs_path


def _cleanup_test_file(abs_path):
    """Remove test file."""
    if os.path.exists(abs_path):
        os.remove(abs_path)
    d = os.path.dirname(abs_path)
    if os.path.isdir(d) and not os.listdir(d):
        os.rmdir(d)


def _pattern_from_match(match):
    """Extract the glob pattern from a check-ignore match tuple."""
    # match[0] is ".gitignore:<line>:<pattern>"
    return match[0].split(":", 2)[2]


def test_gitignore_blocks_llm_backup_pattern():
    """**/*.llm-backup-* matches LLM-editor autosave backups."""
    rel = os.path.join(TEST_PARENT_REL, "sub_mas-foo.yaml.llm-backup-r89")
    abs_ = _make_test_file(rel)
    try:
        match = _check_ignore(rel)
        assert match is not None, f"{rel} should be ignored"
        assert "llm-backup" in _pattern_from_match(match)
    finally:
        _cleanup_test_file(abs_)


def test_gitignore_blocks_timestamped_bak():
    """**/*.bak.[0-9]* matches editor timestamped backups."""
    rel = os.path.join(TEST_PARENT_REL, "sub_bar.yaml.bak.20260914_120000")
    abs_ = _make_test_file(rel)
    try:
        match = _check_ignore(rel)
        assert match is not None, f"{rel} should be ignored"
        assert "bak.[0-9]" in _pattern_from_match(match)
    finally:
        _cleanup_test_file(abs_)


def test_gitignore_blocks_yaml_orig():
    """**/*.yaml.orig matches `.orig` conflict-resolution files."""
    rel = os.path.join(TEST_PARENT_REL, "sub_mas-baz.yaml.orig")
    abs_ = _make_test_file(rel)
    try:
        match = _check_ignore(rel)
        assert match is not None, f"{rel} should be ignored"
        assert ".orig" in _pattern_from_match(match)
    finally:
        _cleanup_test_file(abs_)


def test_gitignore_blocks_yaml_rej():
    """**/*.yaml.rej matches patch-reject files."""
    rel = os.path.join(TEST_PARENT_REL, "sub_mas-qux.yaml.rej")
    abs_ = _make_test_file(rel)
    try:
        match = _check_ignore(rel)
        assert match is not None, f"{rel} should be ignored"
        assert ".rej" in _pattern_from_match(match)
    finally:
        _cleanup_test_file(abs_)


def test_gitignore_blocks_emacs_tilde():
    """**/*~ matches emacs auto-save files."""
    rel = os.path.join(TEST_PARENT_REL, "some_file.yaml~")
    abs_ = _make_test_file(rel)
    try:
        match = _check_ignore(rel)
        assert match is not None, f"{rel} should be ignored"
        assert _pattern_from_match(match) == "**/*~"
    finally:
        _cleanup_test_file(abs_)


def test_real_yaml_files_NOT_ignored():
    """Sanity: a normal .yaml file is NOT ignored (the new patterns
    must be narrow enough not to catch actual source files)."""
    rel = os.path.join(TEST_PARENT_REL, "sub_mas-real.yaml")
    abs_ = _make_test_file(rel)
    try:
        match = _check_ignore(rel)
        assert match is None, f"{rel} (real file) should NOT be ignored, got {match}"
    finally:
        _cleanup_test_file(abs_)


def test_gitignore_present_in_repo():
    """Sanity: .gitignore exists and contains the R110-549 marker."""
    gi = os.path.join(REPO_ROOT, ".gitignore")
    assert os.path.isfile(gi), f".gitignore missing at {gi}"
    with open(gi) as f:
        text = f.read()
    assert "R110-549" in text, "R110-549 marker comment not found in .gitignore"
    for needle in ["llm-backup", "bak.[0-9]", ".orig", ".rej", "*~"]:
        assert needle in text, f"R110-549 pattern '{needle}' not in .gitignore"


def test_no_tracked_timestamped_bak_leaked():
    """No .bak.YYYYMMDD_* file should be tracked (R110-546/547 cleaned
    the historic ones; R110-549 prevents future leaks via the ignore).
    This guards against regressions if someone reintroduces them."""
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    lines = out.stdout.splitlines()
    bak_files = [l for l in lines if ".bak." in l and l.split(".bak.")[-1][:8].isdigit()]
    assert len(bak_files) == 0, f".bak.YYYYMMDD leaked into tracked: {bak_files}"
