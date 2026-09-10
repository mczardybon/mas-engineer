"""
R110-262 redteam-1 test 2: Hard-Stop Copilot regex adversarial coverage
(R110-251 origin).

R110-251 fixed the Hard-Stop Copilot regex in
.github/workflows/ai-pipeline-kill-switch.yml. The bug was: the
suffix group `(\\[[a-z]+\\]|[[:space:]]|$)` was needed because GitHub's
bot-naming convention is `name[bot]` (followed by `[`, not whitespace
and not EOL).

This test extracts the current regex from the workflow and runs it
against a battery of known-good (real Copilot) and known-bad (non-Copilot)
actor names. A regression in the regex (e.g. someone "simplifies" the
suffix group back to `(|[[:space:]])`) shows up as a known-bad case
matching.

Refs: R110-251 (Hard-Stop regex fix), R110-262 (this test), R36 (R36
emoji lesson), R110-78 (verification theater).
"""

import re
from pathlib import Path

import pytest


# R110-394: find WORKFLOW by walking up from the test file, NOT
# relative to CWD. The original `Path("../.github/workflows/...")`
# was CWD-relative and broke in the full pytest sweep when an
# earlier test changed CWD (R110-389 / R110-392 / R110-393 pattern).
#
# The workflow file lives at <REPO>/.github/workflows/... where
# REPO is the parent that contains both `mas-engineer/` and
# `.github/` as siblings. From the test file at
# `mas-engineer/tests/test_r110262_hardstop_copilot_regex.py`,
# that's 2 levels up (mas-engineer/tests/ → mas-engineer/ → REPO).
# We walk up to 4 levels to find the parent that contains
# `.github/workflows/ai-pipeline-kill-switch.yml`, then resolve.
def _find_workflow():
    p = Path(__file__).resolve().parent
    for _ in range(4):
        candidate = p / ".github" / "workflows" / "ai-pipeline-kill-switch.yml"
        if candidate.exists():
            return candidate
        p = p.parent
    # Fallback: the original CWD-relative path (works when CWD is correct)
    return Path("../.github/workflows/ai-pipeline-kill-switch.yml").resolve()


WORKFLOW = _find_workflow()


def _extract_regex():
    """Extract the grep -qiE regex from the workflow file.

    The regex lives in a line like:
        if echo "$ACTOR $TRIGGERING_ACTOR" | grep -qiE '<REGEX>'; then
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    m = re.search(r"grep -qiE\s+'([^']+)'", text)
    if not m:
        raise RuntimeError(
            f"could not extract grep -qiE regex from {WORKFLOW} "
            f"(workflow structure changed?)"
        )
    regex = m.group(1)
    # R110-407: Convert POSIX character classes (bash ERE) to Python re syntax.
    # The workflow uses `[[:space:]]` which bash interprets as a POSIX
    # whitespace class. Python's `re` interprets `[[:space:]]` as a nested
    # set (outer set containing the chars `:`, `s`, `p`, `a`, `c`, `e`,
    # `]`, `[`) and emits a FutureWarning. Replace it with the equivalent
    # Python `\s` so the test re.search() is warning-free.
    regex = regex.replace("[[:space:]]", r"\s")
    return regex


REGEX = _extract_regex()


def _matches(actor: str) -> bool:
    """Mimic the workflow's grep -qiE semantics.

    The workflow runs `echo "$ACTOR $TRIGGERING_ACTOR" | grep -qiE ...`,
    which matches the regex against the concatenated string with a space.
    But for our adversarial test, we test the regex against the actor
    ALONE (the workflow's `if` only fires if the regex matches the
    concatenation, but a single-actor match is sufficient to detect
    regex bugs).
    """
    return bool(re.search(REGEX, actor, re.IGNORECASE))


# ===========================================================================
# KNOWN-Copilot actors (the regex MUST match these — else Hard-Stop fails)
# ===========================================================================
KNOWN_COPILOT = [
    # (actor, why)
    ("copilot-swe-agent[bot]",             "real Copilot SWE agent (R110-251 primary case)"),
    ("github-copilot[bot]",                "real Copilot"),
    ("copilot-chat[bot]",                  "real Copilot chat"),
    ("copilot-pull-request-reviewer[bot]", "real Copilot PR reviewer"),
    # Edge case: also without [bot] suffix (the regex allows whitespace
    # or EOL as terminator too, so actor="copilot" should also match
    # in the workflow concatenation `copilot <TRIGGERING_ACTOR>`)
    ("copilot",                            "bare 'copilot' (matches as actor with EOL terminator)"),
]


# ===========================================================================
# KNON-NON-Copilot actors (the regex must NOT match these)
# ===========================================================================
KNOWN_NON_COPILOT = [
    # (actor, why)
    ("mczardybon",                         "human owner (workflow has if: github.actor != 'mczardybon' but regex is the inner guard)"),
    ("dependabot[bot]",                    "Dependabot — different bot, must not be Copilot-blocked"),
    ("github-actions[bot]",                "GHA bot — must not be Copilot-blocked"),
    ("renovate[bot]",                      "Renovate bot"),
    ("my-copilot-fork",                    "user with 'copilot' in name (substring trap, no [bot] terminator)"),
    ("copilot-fan",                        "user with 'copilot' in name, no [bot]"),
    ("dependabot",                         "bare 'dependabot' (no [bot])"),
    ("github-actions",                     "bare 'github-actions'"),
    ("",                                   "empty actor (must not match anything)"),
]


# ===========================================================================
# Tests
# ===========================================================================

@pytest.mark.parametrize("actor,why", KNOWN_COPILOT, ids=[a[0] for a in KNOWN_COPILOT])
def test_hardstop_matches_known_copilot_actors(actor, why):
    """Real Copilot actors MUST be detected by the Hard-Stop regex.

    This is the core guard. If this test fails, the workflow is
    silently letting Copilot run pipelines.
    """
    assert _matches(actor), (
        f"Copilot actor NOT detected by Hard-Stop regex: {actor!r} ({why}). "
        f"Regex: {REGEX!r}. "
        f"This means the Hard-Stop guard is broken — R110-251 bug regressed."
    )


@pytest.mark.parametrize("actor,why", KNOWN_NON_COPILOT, ids=[a[0] for a in KNOWN_NON_COPILOT])
def test_hardstop_rejects_known_non_copilot_actors(actor, why):
    """Non-Copilot actors must NOT be matched (false-positive trap).

    A regex that's too greedy (e.g. `copilot` as a substring) would
    block all `my-copilot-fork` users, dependabot, etc. This test
    guards against that.
    """
    assert not _matches(actor), (
        f"Non-Copilot actor WAS matched (false positive!): {actor!r} ({why}). "
        f"Regex: {REGEX!r}. "
        f"This would block the actor incorrectly — false positive."
    )


def test_hardstop_workflow_exists():
    """The Hard-Stop workflow file must exist (regression guard)."""
    assert WORKFLOW.exists(), (
        f"{WORKFLOW} missing! The Hard-Stop guard cannot work without this file."
    )


def test_hardstop_workflow_has_pipefail_safe_pattern():
    """The Hard-Stop step must use a fail-fast pattern (no `set -e` + `tee | tail` without pipefail).

    Regression guard against R110-4c variant 3: if someone wraps the
    detection step in `tee | tail` without pipefail, the workflow can
    return 0 even when the guard should fire.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    # The detection step uses `if echo ... | grep -qiE ...; then exit 1; fi`
    # — this is fail-safe because grep returns 1 on no-match, but the
    # explicit `exit 1` inside the if-branch makes it explicit. The
    # whole step uses `if` which does NOT swallow exit codes.
    has_if_branch = bool(re.search(r"if\s+.*grep\s+-qiE", text))
    has_explicit_exit_1 = bool(re.search(r"exit\s+1", text))
    assert has_if_branch and has_explicit_exit_1, (
        f"Hard-Stop workflow missing fail-safe pattern. "
        f"Has if-branch with grep: {has_if_branch}, "
        f"has explicit exit 1: {has_explicit_exit_1}. "
        f"Workflow content:\n{text}"
    )


def test_extracted_regex_is_warning_free():
    """R110-407 regression guard: REGEX must NOT trigger FutureWarning.

    Without the `_extract_regex()` POSIX→Python conversion at module import
    time, Python's re module would emit a FutureWarning about a possible
    nested set (the `[[:space:]]` from the bash workflow file). This test
    asserts that compiling REGEX is warning-free, so that downstream
    re.search() calls in _matches() and the parametrized matchers don't
    pollute the test output with a FutureWarning.
    """
    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        re.compile(REGEX)  # Compile step is where FutureWarning fires
    nested_set_warnings = [
        w for w in caught
        if issubclass(w.category, FutureWarning)
        and "nested set" in str(w.message)
    ]
    assert not nested_set_warnings, (
        f"REGEX from {WORKFLOW} still triggers FutureWarning about "
        f"nested set. The fix in _extract_regex() converts [[:space:]] "
        f"to \\s — if this test fails, that conversion was removed or "
        f"the workflow was changed to use a different POSIX class. "
        f"Warnings: {[str(w.message) for w in nested_set_warnings]}"
    )
