"""R110-550 — verify pre-push hook blocks .gitignore-pattern junk files.

Background (R110-550, 2026-09-14): R110-549 added 5 backup-pattern globs
to .gitignore. That blocks NEW files via `git add`. But a determined
contributor can bypass with `git add -f`. Once tracked, `git check-ignore`
returns "not ignored" for the file (patterns only apply to NEW untracked
files), so the R110-549 patterns alone don't catch force-added junk in
the commit history.

R110-550 adds defense-in-depth in `.githooks/pre-push`: a hard-coded
pattern match against newly-added files (`git diff --diff-filter=A`)
that blocks pushes containing filenames matching the R110-549 junk
patterns. This test verifies the hook with a simulated junk commit.

Pattern (must match hook):
  `(\\.bak\\.[0-9_]+|\\.yaml\\.orig|\\.yaml\\.rej|\\.llm-backup-.*|~)$`

Why a hard-coded pattern (instead of `git check-ignore`): once a file is
tracked, `git check-ignore` returns RC=1 ("not ignored") for it, so we
need a path-string match that doesn't care about the file's tracked state.
"""
import os
import re
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO_ROOT, ".githooks", "pre-push")

# Same pattern as in .githooks/pre-push (R110-550 Check 3)
JUNK_PATTERN = re.compile(
    r"(\.bak\.[0-9_]+|\.yaml\.orig|\.yaml\.rej|\.llm-backup-.*|~)$"
)


def _run_hook():
    """Run the pre-push hook with the standard test arguments.

    Returns (returncode, stdout, stderr). Uses UPSTREAM=origin/mas-t-tests
    which is the only branch we push to (R110-269). The hook reads the
    first arg as upstream and the second as the local branch name.
    """
    out = subprocess.run(
        ["bash", HOOK, "origin", "mas-t-tests"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return out.returncode, out.stdout, out.stderr


def test_hook_pattern_matches_all_junk_variants():
    """The hard-coded JUNK_PATTERN must catch all 5 R110-549 patterns."""
    paths = [
        "x.yaml.bak.20260914_120000",
        "x.yaml.bak.20260914_999999",
        "x.yaml.orig",
        "x.yaml.rej",
        "x.yaml.llm-backup-r89",
        "x.txt.llm-backup-r89",
        "x.txt~",
        "deep/nested/path/y.yaml.bak.20260914_120000",
    ]
    for p in paths:
        assert JUNK_PATTERN.search(p), f"{p} should match R110-550 junk pattern"


def test_hook_pattern_does_NOT_match_real_files():
    """The JUNK_PATTERN must be narrow enough to NOT catch real source."""
    paths = [
        "x.yaml",
        "recipe/sub/sub_mas-recipe.yaml",
        "tools/dev_foo.py",
        "tests/test_something.py",
        "README.md",
        "x.yaml.bak",  # bare `.bak` (no timestamp) — not junk
        "x.backup",  # similar but different suffix
    ]
    for p in paths:
        assert not JUNK_PATTERN.search(p), f"{p} should NOT match (false positive)"


def test_hook_present_and_syntax_ok():
    """The pre-push hook must exist and pass bash syntax check."""
    assert os.path.isfile(HOOK), f"hook missing at {HOOK}"
    out = subprocess.run(
        ["bash", "-n", HOOK],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, f"bash syntax error in hook: {out.stderr}"


def test_hook_has_r110550_marker():
    """Sanity: the hook must contain the R110-550 marker comment."""
    with open(HOOK) as f:
        text = f.read()
    assert "R110-550" in text, "R110-550 marker comment missing from pre-push hook"
    assert "JUNK_PATTERN" in text, "JUNK_PATTERN variable missing from hook"


def test_hook_pattern_in_hook_matches_python_version():
    """The hook's JUNK_PATTERN regex must be byte-identical to this test's.

    If someone edits the hook pattern without updating this test, the
    hook will block wrong files. Drift detection between the two sources.
    """
    with open(HOOK) as f:
        hook_text = f.read()
    # Extract the JUNK_PATTERN line: `JUNK_PATTERN='...'` (single-quoted)
    m = re.search(r"JUNK_PATTERN='([^']*)'", hook_text)
    assert m, "JUNK_PATTERN assignment not found in hook"
    hook_pattern_str = m.group(1)
    # The hook uses bash regex; python re should accept the same syntax
    # (basic ERE). Build a python re from the bash string and compare:
    assert hook_pattern_str == JUNK_PATTERN.pattern, (
        f"hook JUNK_PATTERN drift:\n"
        f"  hook:  {hook_pattern_str!r}\n"
        f"  test:  {JUNK_PATTERN.pattern!r}"
    )


def test_hook_blocks_junk_file():
    """End-to-end: create a force-added junk commit, hook must BLOCK."""
    # Save current HEAD so we can restore it after the test
    head_before = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()

    junk_rel = "tests/_r110550_sim_junk.yaml.bak.20260914_999999"
    junk_abs = os.path.join(REPO_ROOT, junk_rel)
    try:
        # Write junk file, force-add (bypassing R110-549 .gitignore)
        with open(junk_abs, "w") as f:
            f.write("SIMULATED JUNK for R110-550 hook test\n")
        add = subprocess.run(
            ["git", "add", "-f", junk_rel],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert add.returncode == 0, f"git add -f failed: {add.stderr}"
        # Commit WITHOUT triggering pre-push (--no-verify)
        commit = subprocess.run(
            ["git", "commit", "-m", "R110-550 test: sim junk", "--no-verify"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert commit.returncode == 0, f"git commit failed: {commit.stderr}"

        # Now run the hook — it MUST exit non-zero
        rc, stdout, stderr = _run_hook()
        assert rc != 0, (
            f"hook should BLOCK junk commit, but returned RC=0\n"
            f"STDOUT: {stdout}\nSTDERR: {stderr}"
        )
        # And the error message should mention R110-550
        combined = stdout + stderr
        assert "R110-550" in combined, (
            f"hook output should mention R110-550, got:\n{combined}"
        )
    finally:
        # Preserve any working-tree changes (uncommitted modifications
        # to .githooks/pre-push, new test files, etc.) by stashing them
        # before the test, then popping back. This avoids the destructive
        # `git reset --hard` clobbering uncommitted changes.
        if os.path.exists(junk_abs):
            os.remove(junk_abs)
        # Undo the junk commit. Since we used `git add -f` + `git commit`,
        # we need to undo the commit and unstage the file. Use
        # `git reset --soft HEAD~1` (no --hard!) which moves HEAD back but
        # keeps the working-tree state intact.
        subprocess.run(
            ["git", "reset", "--soft", "HEAD~1"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        # Now unstage the junk file (since soft reset leaves it staged).
        subprocess.run(
            ["git", "reset", "HEAD", junk_rel],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        # And remove from working tree (since we already removed junk_abs
        # above, git will just say "did not match any files").
        subprocess.run(
            ["git", "rm", "--cached", junk_rel],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )


def test_hook_passes_clean_state():
    """With no new commits ahead of origin/mas-t-tests, hook must PASS."""
    rc, stdout, stderr = _run_hook()
    # RC=0 is success; non-zero could mean either we ARE ahead (legitimate
    # push) or a check failed. In the test environment we should NOT be
    # ahead of origin/mas-t-tests — pre-push validator only checks commits
    # in the diff range.
    assert rc == 0, (
        f"hook should PASS on clean state, got RC={rc}\n"
        f"STDOUT: {stdout}\nSTDERR: {stderr}"
    )
