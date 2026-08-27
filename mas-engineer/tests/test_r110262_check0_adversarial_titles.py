"""
R110-262 redteam-1 test 1: pre-push-validator Check 0 commit-title regex
adversarial coverage (R110-259 origin).

The R110-259 fix added a CONVENTIONAL_COMMIT_RE to dev_category_drift.py
(Check 16+) so that `fix(scope):` subjects pass the drift detector. But
the spec-level allowed_patterns in sub_mas-pre-push-validator.md were
NOT updated to allow the hybrid form `🔧 fix: R110-N — title` (emoji +
conventional-prefix + R-num + em-dash + desc).

This test extracts the spec's allowed_patterns from the validator spec,
then asserts both that good titles match AND that bad titles are
rejected. A real failure of the spec shows up as a mismatch.

Refs: R110-258 (drift detector gap), R110-259 (drift detector fix,
uncovered spec-level gap), R110-262 (this test), R110-78 (verification
theater guard).
"""

import re
import subprocess
from pathlib import Path

import pytest


SPEC = Path("recipe/instructions/sub_mas-pre-push-validator.md")
ALLOWED_EMOJIS = {"🔧", "📝", "📚", "📊"}


def _extract_allowed_patterns():
    """Parse the validator spec to extract the allowed_patterns list.

    The spec has TWO kinds of allowed patterns:
      1. Initial 2 raw strings inside `allowed_patterns = [ ... ]`
      2. Additional patterns appended via `allowed_patterns.append(f'...')`
         inside `for allowed in ALLOWED_EMOJIS:` loops.

    The cleanest way to reconstruct the FINAL evaluated list is to
    extract the spec's Python snippet and actually run it in a
    subprocess. This avoids the backslash-escape mess (the spec
    contains `R\\d+` literally, which Python's f-string semantics
    collapse to `R\d+` for use in regex; reproducing this by hand
    from the markdown is fragile).

    The subprocess approach has the side benefit of catching SPEC
    syntax errors at test-collection time, before the suite runs.
    """
    import subprocess
    import json as _json

    spec_text = SPEC.read_text(encoding="utf-8")

    # Extract list body
    m = re.search(r"allowed_patterns = \[(.*?)\n\]", spec_text, re.DOTALL)
    if not m:
        raise RuntimeError(
            f"could not find `allowed_patterns = [...]` in {SPEC}"
        )
    list_body = m.group(1)

    # Extract ALLOWED_EMOJIS
    m_e = re.search(r"ALLOWED_EMOJIS\s*=\s*\{([^}]+)\}", spec_text)
    if not m_e:
        raise RuntimeError(f"could not find ALLOWED_EMOJIS in {SPEC}")
    emojis_literal = "{" + m_e.group(1) + "}"

    # Extract append patterns (raw f-string bodies)
    append_patterns = re.findall(
        r"allowed_patterns\.append\(f'(.+?)'\)",
        spec_text,
        re.DOTALL,
    )
    if not append_patterns:
        raise RuntimeError(
            f"no allowed_patterns.append(f'...') calls found in {SPEC}"
        )

    # Build a Python snippet that produces the FINAL list after all
    # for-loops have run, then prints it as JSON.
    parts = [
        "import re",
        f"ALLOWED_EMOJIS = {emojis_literal}",
        f"allowed_patterns = [{list_body}\n]",
        "for allowed in ALLOWED_EMOJIS:",
    ]
    for p in append_patterns:
        parts.append(f"    allowed_patterns.append(f'{p}')")
    parts.append("import json")
    parts.append("print(json.dumps(allowed_patterns))")
    snippet = "\n".join(parts)

    result = subprocess.run(
        ["python3", "-c", snippet],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"failed to evaluate spec snippet in {SPEC}:\n"
            f"--- STDOUT ---\n{result.stdout}\n"
            f"--- STDERR ---\n{result.stderr}\n"
            f"--- SNIPPET ---\n{snippet}"
        )
    try:
        patterns = _json.loads(result.stdout)
    except _json.JSONDecodeError as e:
        raise RuntimeError(
            f"failed to parse patterns JSON from snippet output: {e}\n"
            f"Output: {result.stdout[:500]}"
        )

    if not patterns:
        raise RuntimeError(f"no patterns found in {SPEC} after evaluation")
    return patterns


# Extract at module import time so a missing spec fails fast (not on
# every test invocation).
ALLOWED_PATTERNS = _extract_allowed_patterns()


def _matches(title: str) -> bool:
    return any(re.match(p, title) for p in ALLOWED_PATTERNS)


# ===========================================================================
# KNOWN-GOOD inputs (the regex must accept these)
# ===========================================================================
KNOWN_GOOD = [
    # (title, why)
    ("🔧 R110-261 — test",                "R108+ convention: emoji + R-N + em-dash + desc"),
    ("🔧 R110-261a-evidence — title",     "R-num with sub-id and word suffix"),
    ("🔧 R110-9 follow-up — bump",        "R-num with follow-up suffix"),
    ("📊 EVIDENCE — R110-261",            "evidence-marker form"),
    ("📚 R110-7 — docs",                  "non-🔧 emoji + R-num"),
    ("🔧 FIX — foo",                      "uppercase TYPE convention"),
    ("📝 DOCS — bar",                     "non-🔧 uppercase TYPE"),
    ("fix: add foo",                      "conventional commits, no scope"),
    ("fix(scope): add bar",               "conventional commits, with scope"),
    ("feat(tools): new feature",          "conventional feat with scope"),
    ("chore: cleanup",                    "conventional chore no scope"),
    ("mas(round-5): improvement",         "MAS self-improve round form"),
]


# ===========================================================================
# KNOWN-BAD inputs (the regex must REJECT these — adversarial negative space)
# ===========================================================================
KNOWN_BAD = [
    # (title, why)
    ("🔧 fix: R110-261 title",            "missing em-dash (R110-259 hybrid form is also missing this)"),
    ("🔧 Fix — R110-261",                 "wrong TYPE case (Fix not FIX)"),
    ("🪤 TRAP — R110-261",                "non-allowed emoji (R36 anti-pattern)"),
    ("🛡️ PUSH — R110-261",                "non-allowed emoji (R36 anti-pattern)"),
    ("random commit message",             "no convention at all"),
    ("🔧 R110-261 title",                 "missing em-dash after R-num"),
    ("🔧 R-261 — title",                  "missing round prefix"),
    ("🔧 R110 261 — title",               "missing dash in R-num"),
    ("WIP: half-done work",               "WIP prefix is not allowed"),
    ("Merge branch 'feature' into main",  "merge commits are not allowed"),
    ("Update README.md",                  "non-conventional, non-R-num"),
    ("🔧 fix: R110-261 — title",          "R110-259 hybrid form (emoji + conventional-prefix + R-num + em-dash) — CURRENTLY REJECTED by spec"),
    # False-positive traps (substring must NOT cause a match)
    ("my-copilot-fork",                   "user with 'copilot' in name (not in scope)"),
    ("depends-on-fix",                    "user with 'fix' in name (not in scope)"),
]


# ===========================================================================
# Tests
# ===========================================================================

@pytest.mark.parametrize("title,why", KNOWN_GOOD, ids=[t[0] for t in KNOWN_GOOD])
def test_check0_accepts_known_good(title, why):
    """Good titles must match the allowed_patterns."""
    assert _matches(title), (
        f"GOOD title was rejected: {title!r} ({why}). "
        f"Patterns: {ALLOWED_PATTERNS}"
    )


@pytest.mark.parametrize("title,why", KNOWN_BAD, ids=[t[0] for t in KNOWN_BAD])
def test_check0_rejects_known_bad(title, why):
    """Bad titles must NOT match the allowed_patterns.

    This is the adversarial negative-space test. If a known-bad title
    matches, the spec has a gap (like R110-259 hybrid-form bug).
    """
    matched_patterns = [p for p in ALLOWED_PATTERNS if re.match(p, title)]
    assert not matched_patterns, (
        f"BAD title was ACCEPTED: {title!r} ({why}). "
        f"Matched patterns: {matched_patterns}. "
        f"Either fix the title or fix the spec (update allowed_patterns "
        f"in {SPEC})."
    )


def test_check0_spec_has_at_least_four_allowed_emojis():
    """The spec must enumerate the 4 hardcoded allowed emojis (🔧 📝 📚 📊).

    Regression guard for the R36 lesson: if someone removes emojis from
    ALLOWED_EMOJIS, the test fails before pushing.
    """
    spec_text = SPEC.read_text(encoding="utf-8")
    for emoji in ALLOWED_EMOJIS:
        # The emoji should appear in the spec's ALLOWED_EMOJIS set
        assert emoji in spec_text, (
            f"Allowed emoji {emoji!r} missing from spec {SPEC}. "
            f"If you intentionally removed it, update this test too."
        )


def test_check0_spec_has_r_num_pattern():
    """The R-num pattern (R<digits>-<word>) must be in allowed_patterns.

    Regression guard: if the R-num pattern is removed by mistake,
    every R-sprint commit will be rejected.

    The ALLOWED_PATTERNS list contains Python strings like:
        "^🔧 (R\\\\d+-[\\\\w-]+( follow-up)? — |EVIDENCE — R\\\\d+-)"
    (these are 4-backslash escapes that, when interpreted as regex
    patterns, match "R<digit>-<word>"). So in the Python string form,
    we look for "R\\\\d" (literal R followed by backslash followed by d).
    """
    # Look for the substring "R\\d" (4 chars: R, backslash, backslash, d)
    # in the Python source representation of each pattern.
    r_num_patterns = [p for p in ALLOWED_PATTERNS if "R\\\\d" in repr(p) or r"R\d" in p]
    assert r_num_patterns, (
        f"No R-num pattern found in allowed_patterns. "
        f"This would reject every R-sprint commit. Patterns: {ALLOWED_PATTERNS}"
    )
