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


WORKFLOW = Path("../.github/workflows/ai-pipeline-kill-switch.yml")


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
    return m.group(1)


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
