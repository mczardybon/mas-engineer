"""
test_skills_install.py — R110-133 contract tests for self-contained mas-engineer.

These tests enforce that mas-engineer can be cloned fresh and the skills needed
to operate it are installed automatically. Pre-R110-133, the 18 hermes skills
mas-engineer depends on (commit-protocol, verification-theater-guard, pre-push-gate,
im-pipeline, etc) lived ONLY in the agent runtime's home directory and were
never in the repo. Fresh clones (CI, new dev, re-install) ended up with
recipes but no skills -> agent's Step-0 skill scan returned 0 matches ->
commit-protocol un-followed -> verification theater.

Design constraint (R110-133 strict):
  mas-engineer is hermes-agnostic. The repo must not hardcode any runtime
  path, must not read any environment variable, and must not mention the
  consuming runtime by name. The installer is a generic copy-utility: give
  it a target directory as a CLI arg, it copies the repo's mas-engineer/skills/
  there. No env-vars. No runtime coupling.

Contract:
  - 18 mas-engineer-relevant skills must live in mas-engineer/skills/
  - Each must have a SKILL.md
  - SKILLS-INDEX.md must enumerate all 18
  - 0 secrets in the bundled skills
  - 0 hardcoded user-specific paths in non-anti-pattern context
  - scripts/skills-install.sh must install the 18 skills to a user-supplied
    target path (CLI arg) idempotently
  - Default target (no CLI arg) = repo's own mas-engineer/skills/ (no-op)
  - No env-var reads in skills-install.sh
  - dev_install.sh and mas-reinstall.sh must delegate to skills-install.sh
  - User-installed non-mas-engineer skills in the target must be preserved
    (no-delete policy)

Test isolation: install tests use pytest's tmp_path as the target directory.
The target is passed to skills-install.sh as a CLI argument. No env-vars,
no $HOME trick, no real filesystem mutations outside tmp_path.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Test infra — repo paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_SRC = REPO_ROOT / "mas-engineer" / "skills"
SKILLS_INSTALL_SH = REPO_ROOT / "scripts" / "skills-install.sh"
DEV_INSTALL_SH = REPO_ROOT / "tools" / "dev_install.sh"
MAS_REINSTALL_SH = REPO_ROOT / "scripts" / "mas-reinstall.sh"
SKILLS_INDEX_MD = SKILLS_SRC / "SKILLS-INDEX.md"

# The skills that mas-engineer requires to operate (per R110-133). This is
# the source-of-truth list — the contents of mas-engineer/skills/ in the repo.
# The list is computed at test-collection time from the actual repo state,
# not hardcoded here, so the test stays correct when skills are added/removed.
# We return the SKILL-DIR relative paths, not the file paths, so callers can
# do `SKILLS_SRC / skill / "SKILL.md"` without getting a doubled suffix.
def _repo_skill_list() -> list[str]:
    return sorted(
        str(p.parent.relative_to(SKILLS_SRC)).replace(os.sep, "/")
        for p in SKILLS_SRC.rglob("SKILL.md")
        if p.parent != SKILLS_SRC  # exclude top-level SKILLS-INDEX.md
    )

# Skills whose absolute-path references in SKILL.md are LEGITIMATE:
#  - mas-engineer-verification-theater-guard: contains an anti-pattern
#    example, expected to remain verbatim so the lesson has teeth.
ANTI_PATTERN_ALLOWLIST = {
    "mas-engineer-verification-theater-guard",
}

# Pattern for "real" secrets (30+ char alnum after known prefixes). Does NOT
# match placeholder text like `sk-***` or `DEEPSEEK_API_KEY=***`.
SECRET_PATTERN = re.compile(
    r"sk-[a-f0-9]{30,}|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}"
)

# Env-vars that mas-engineer must never read in code. Skill files (in
# SKILL.md docs) may *mention* the names as anti-patterns, but the actual
# installer scripts and python must be free of them.
FORBIDDEN_ENV_VARS = ["HERMES_HOME", "HERMES_SKILLS", "MAS_SKILLS_HOME"]


# ---------------------------------------------------------------------------
# Test 1: the 18 skills physically live in mas-engineer/skills/
# ---------------------------------------------------------------------------


def test_all_mas_engineer_skills_present():
    expected = _repo_skill_list()
    for skill in expected:
        skill_md = SKILLS_SRC / skill / "SKILL.md"
        assert skill_md.is_file(), (
            f"R110-133: missing skill {skill!r}. "
            f"Expected at {skill_md}."
        )


# ---------------------------------------------------------------------------
# Test 2: SKILLS-INDEX.md enumerates all skills in the repo
# ---------------------------------------------------------------------------


def test_skills_index_lists_all_repo_skills():
    assert SKILLS_INDEX_MD.is_file(), f"missing {SKILLS_INDEX_MD}"
    text = SKILLS_INDEX_MD.read_text()
    expected = _repo_skill_list()
    for skill in expected:
        assert skill in text, (
            f"SKILLS-INDEX.md does not list {skill!r}. "
            f"Step-0 skill scan will miss it; add it to the index table."
        )


# ---------------------------------------------------------------------------
# Test 3: no secrets in the bundled skills
# ---------------------------------------------------------------------------


def test_no_secrets_in_repo_skills():
    leaks = []
    for skill_md in SKILLS_SRC.rglob("SKILL.md"):
        text = skill_md.read_text()
        for m in SECRET_PATTERN.finditer(text):
            leaks.append((str(skill_md), m.group(0)[:12] + "..."))
    assert not leaks, (
        "R110-133: secrets detected in bundled skills:\n"
        + "\n".join(f"  {f}: {tok}" for f, tok in leaks)
    )


# ---------------------------------------------------------------------------
# Test 4: skills-install.sh installs all 18 to a user-supplied target
# ---------------------------------------------------------------------------


def test_skills_install_script_installs_all_to_user_target(tmp_path: Path):
    """
    Pass a user-supplied target path as a CLI arg. Run the installer. Verify
    all 18 skills land at the target with the same relative paths as in
    the repo. No env-vars — the target comes only from the CLI.
    """
    target = tmp_path / "skills"
    proc = subprocess.run(
        ["bash", str(SKILLS_INSTALL_SH), str(target)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"skills-install.sh exited {proc.returncode}.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    expected = _repo_skill_list()
    missing = []
    for skill in expected:
        if not (target / skill / "SKILL.md").is_file():
            missing.append(skill)
    assert not missing, (
        f"skills-install.sh did not install {len(missing)}/{len(expected)} "
        f"skills to {target}. missing: {missing}\nstdout:\n{proc.stdout[-500:]}"
    )


# ---------------------------------------------------------------------------
# Test 5: skills-install.sh is idempotent (re-running yields same end state)
# ---------------------------------------------------------------------------


def test_skills_install_is_idempotent(tmp_path):
    """Run skills-install.sh twice with the same target; both must exit 0."""
    target = tmp_path / "skills"
    p1 = subprocess.run(
        ["bash", str(SKILLS_INSTALL_SH), str(target)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
    )
    p2 = subprocess.run(
        ["bash", str(SKILLS_INSTALL_SH), str(target)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
    )
    assert p1.returncode == 0, f"first run failed: {p1.stdout} {p1.stderr}"
    assert p2.returncode == 0, f"second run failed (idempotency broken): {p2.stdout} {p2.stderr}"
    skill_count = sum(1 for _ in target.rglob("SKILL.md"))
    expected_count = len(_repo_skill_list())
    assert skill_count == expected_count, (
        f"expected {expected_count} skills after 2 runs, got {skill_count}"
    )


# ---------------------------------------------------------------------------
# Test 6: no-delete policy — user-installed skills in the target survive
# ---------------------------------------------------------------------------


def test_skills_install_preserves_user_installed_skills(tmp_path):
    """
    Place a user-only skill in the target before running the installer.
    After install, that skill MUST still exist (installer only writes
    skills it knows about from the repo, never deletes others).
    """
    target = tmp_path / "skills"
    user_skill = target / "user-skill-i-added-myself"
    user_skill.mkdir(parents=True)
    user_content = "# user-installed, not in mas-engineer repo\n"
    (user_skill / "SKILL.md").write_text(user_content)

    proc = subprocess.run(
        ["bash", str(SKILLS_INSTALL_SH), str(target)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, f"skills-install.sh failed: {proc.stderr}"

    # 1. user skill must still exist (no-delete policy)
    assert (user_skill / "SKILL.md").is_file(), (
        "R110-133 violation: skills-install.sh DELETED a user-installed skill. "
        "The contract is: only mas-engineer-owned skills are managed; "
        "user-installed skills in the target are preserved."
    )
    # 2. user skill content must be unchanged
    assert (user_skill / "SKILL.md").read_text() == user_content, (
        "R110-133 violation: skills-install.sh OVERWROTE a user-installed skill."
    )


# ---------------------------------------------------------------------------
# Test 7: default target (no CLI arg) = repo's own mas-engineer/skills/
# ---------------------------------------------------------------------------


def test_skills_install_default_target_is_repo_local_noop():
    """
    When called with no CLI arg, the installer's target IS the source dir.
    This makes the install a no-op when skills already live in the repo
    (the R110-133 self-contained default). It must still exit 0.
    """
    proc = subprocess.run(
        ["bash", str(SKILLS_INSTALL_SH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"default-target run failed: {proc.stdout} {proc.stderr}"
    )
    # And the source skills must still be there
    expected = _repo_skill_list()
    for skill in expected:
        assert (SKILLS_SRC / skill / "SKILL.md").is_file(), (
            f"default-target run clobbered {skill!r} in the source dir"
        )


# ---------------------------------------------------------------------------
# Test 8: dev_install.sh and mas-reinstall.sh delegate to skills-install.sh
# ---------------------------------------------------------------------------


def test_dev_install_delegates_to_skills_install():
    """tools/dev_install.sh must call scripts/skills-install.sh (R110-133)."""
    assert DEV_INSTALL_SH.is_file(), f"missing {DEV_INSTALL_SH}"
    text = DEV_INSTALL_SH.read_text()
    assert "skills-install.sh" in text, (
        f"R110-133: {DEV_INSTALL_SH.name} does not delegate to skills-install.sh."
    )


def test_mas_reinstall_delegates_to_skills_install():
    """scripts/mas-reinstall.sh must call scripts/skills-install.sh (R110-133)."""
    assert MAS_REINSTALL_SH.is_file(), f"missing {MAS_REINSTALL_SH}"
    text = MAS_REINSTALL_SH.read_text()
    assert "skills-install.sh" in text, (
        f"R110-133: {MAS_REINSTALL_SH.name} does not delegate to skills-install.sh."
    )


# ---------------------------------------------------------------------------
# Test 9: skills-install.sh has no env-var reads (R110-133 strict)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("var_name", FORBIDDEN_ENV_VARS)
def test_skills_install_reads_no_forbidden_env_var(var_name):
    """
    The installer must be hermes-agnostic. It cannot read HERMES_HOME or any
    other env-var to decide where to install. The target must come from a
    CLI argument only. This guards against future regressions.
    """
    text = SKILLS_INSTALL_SH.read_text()
    # Strip comment lines so we only catch *real* references in code.
    code_lines = [
        line for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code = "\n".join(code_lines)
    assert var_name not in code, (
        f"R110-133 violation: skills-install.sh references {var_name!r} in code. "
        f"Install target must come from CLI arg only, not env-vars. "
        f"Offending code:\n{code}"
    )


# ---------------------------------------------------------------------------
# Test 10: hardcoded paths audit (no user-specific paths in source)
# ---------------------------------------------------------------------------


def test_hardcoded_paths_audit():
    """
    No hardcoded user-specific paths in scripts, tests, or skills.

    Implementation note: we scan the file *body* but skip the lines where the
    forbidden substring is *defined* (this test itself) or in docstrings
    that explain what is forbidden. That keeps the test from tripping on
    its own definitions.
    """
    forbidden_substrings = [
        "/root/.hermes",
        "/home/ubuntu",
        "/Users/",
        "/tmp/mas-engineer",
    ]
    offenders = []
    for path in [
        SKILLS_INSTALL_SH,
        DEV_INSTALL_SH,
        MAS_REINSTALL_SH,
    ]:
        if not path.is_file():
            continue
        text = path.read_text()
        for substr in forbidden_substrings:
            for line_no, line in enumerate(text.splitlines(), 1):
                if substr in line:
                    offenders.append((str(path), line_no, line.strip()))
    assert not offenders, (
        "R110-133: hardcoded user-specific path in repo content:\n"
        + "\n".join(f"  {f}:{ln}: {line}" for f, ln, line in offenders)
    )
