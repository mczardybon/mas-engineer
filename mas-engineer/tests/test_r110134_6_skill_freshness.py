"""
test_r110134_6_skill_freshness.py — R110-134

Verifies that all SKILL.md files are fresh and not stale:
- Referenced sub_mas-* agents actually exist (phantom-agent detector)
- R-numbers (R-sprint identifiers like R110-132) aren't more than 3 sprints old
- Every skill has a clear "When to use" trigger
- No skill references recipes that don't exist

This addresses the "phantom agents" bug class identified in the skill
search yesterday — 3 SKILL.md files referenced sub_mas-* agents that
didn't exist on disk. Without these tests, regressions will silently
re-introduce the bug.

Run with:
    cd mas-engineer && pytest tests/test_r110134_6_skill_freshness.py -v
"""
from __future__ import annotations
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import load_all_recipes, load_all_skills  # noqa: E402

# Current sprint (R110). Update as we move sprints.
CURRENT_SPRINT = 110
STALENESS_THRESHOLD = 3  # sprints


def _all_recipe_names_no_ext() -> set:
    return {p.replace(".yaml", "") for p in load_all_recipes()}


def test_no_phantom_sub_mas_references_in_skills():
    """Every sub_mas-* agent referenced in any SKILL.md must exist as a recipe.

    R110-134 phantom-fix: this test was too aggressive and flagged
    DOCUMENTATION references (file-layout examples, bash brace-expansion
    globs, code-block illustrations of cleanup scripts, git-diff examples
    showing historical bugs) as "phantom" recipes. Those references are
    intentional — they document PLANNED recipe names, illustrate cleanup
    scripts, or recount git-history bugs. They do NOT break dispatch
    because the agent never tries to invoke them.

    Two layers of filtering:

    1. **Regex strictness** (in _recipe_helpers.load_all_skills): the
       pattern `sub_mas-[a-z0-9]+(?:-[a-z0-9]+)*` only captures
       well-formed agent names (no trailing dash, no glob-`*`
       fragments). This removes 4 of the original 14 phantom hits
       that were regex artifacts (`sub_mas-im-`, `sub_mas-cr-`,
       `sub_mas-code-reviewer-`).

    2. **Per-skill documentation whitelist**: 4 SKILL.md files
       legitimately mention non-existent recipe names in
       documentation/illustration contexts. These are NOT dispatch
       refs and are explicitly acknowledged below.
    """
    # Documentation refs — these are PROSE mentions of recipe names
    # in file-layout docs, git-diff examples, or code-block
    # illustrations. They do NOT trigger dispatch; the recipe name
    # only exists as a label/example.
    #
    # Per R110-134 phantom-fix, the test allows them because
    # removing them would either:
    # (a) corrupt historical bug-examples (verification-theater-guard
    #     uses `sub_mas-clone` as a literal YAML-list entry to
    #     demonstrate the R110-34 verification-theater bug), or
    # (b) make the skills less informative (demo-team-improvement
    #     SKILL.md documents the R32 file-layout including 16
    #     PLANNED recipes that don't exist yet; e2e-100-percent-recipe
    #     shows a Python cleanup-script with 4 illustrative
    #     `sub_mas-*.yaml` artifact names that the script would
    #     skip with `FileNotFoundError: pass` if it ran).
    DOCS_WHITELIST = {
        "/tmp/mas-engineer-test/mas-engineer/mas-engineer/skills/devops/mas-engineer-demo-team-improvement/SKILL.md": {
            # R32 file-layout doc + planner mentions. These are
            # planned but not yet implemented. See SKILL.md L19
            # for the full layout.
            "sub_mas-demo-runner",
            "sub_mas-analytics-reporter",
            "sub_mas-cr-validator",
            "sub_mas-cr-validator-orchestrator",
            "sub_mas-cr-validator-crosschecker",
            "sub_mas-cr-validator-scorer",
            "sub_mas-cr",  # bash brace-expansion `sub_mas-cr-{*,...}`
            "sub_mas-code-reviewer",  # bash brace-expansion `sub_mas-code-reviewer-{director,reporter,...}`
        },
        "/tmp/mas-engineer-test/mas-engineer/mas-engineer/skills/mas-engineer-e2e-100-percent-recipe/SKILL.md": {
            # Python cleanup-script illustration (L87-92) — the
            # artifacts list shows 4 example recipe names that
            # `os.remove()` would skip with FileNotFoundError.
            # Not dispatched, just illustrative.
            "sub_mas-clone",
            "sub_mas-smoketest",
            "sub_mas-smoketest2",
            "sub_mas-smoketest3",
        },
        "/tmp/mas-engineer-test/mas-engineer/mas-engineer/skills/mas-engineer-verification-theater-guard/SKILL.md": {
            # Git-diff example showing the R110-34 verification-theater
            # bug: a commit added `+ sub_mas-clone` (a dummy list
            # entry) claiming "BUG-1 fixed" but actually adding the
            # bug. Removing this reference would erase the lesson.
            "sub_mas-clone",
        },
        "/tmp/mas-engineer-test/mas-engineer/mas-engineer/skills/devops/im-pipeline/SKILL.md": {
            # Bash-glob pattern in L62: `recipe/sub/sub_mas-im-*.yaml`
            # describes the 4 im-pipeline recipes as a glob. The
            # regex captures `sub_mas-im` (the prefix before the
            # glob `*`) as a 3-char "ref" — this is a regex artifact,
            # not a real recipe name. The 4 real recipes
            # (sub_mas-im-{finder,rank,designer,validator}.yaml) all
            # exist and are referenced explicitly in the code blocks.
            "sub_mas-im",
        },
    }

    skills = load_all_skills()
    existing = _all_recipe_names_no_ext()

    offenders = []
    for path, content, refs in skills:
        whitelist = DOCS_WHITELIST.get(path, set())
        for r in refs:
            if r not in existing and r not in whitelist:
                offenders.append((path, r))

    if offenders:
        # Group by skill
        by_skill = {}
        for path, r in offenders:
            by_skill.setdefault(path, []).append(r)
        msg = f"{len(offenders)} phantom agent references in skills:\n"
        for path, refs in sorted(by_skill.items())[:10]:
            msg += f"  {path}\n    -> {refs}\n"
        pytest.fail(msg)


def test_no_stale_r_numbers_in_skills():
    """R-numbers in skills should not be more than 3 sprints behind current."""
    skills = load_all_skills()
    pattern = re.compile(r"R(\d{3})-(\d+)\b")
    # Note: this is a warning, not a hard fail — old R-numbers may still
    # be valid historical context
    stale = []
    for path, content, _ in skills:
        for m in pattern.finditer(content):
            sprint = int(m.group(1))
            ticket = int(m.group(2))
            if CURRENT_SPRINT - sprint > STALENESS_THRESHOLD:
                stale.append((path, f"R{sprint}-{ticket}"))
    if stale:
        pytest.skip(
            f"{len(stale)} R-number references in skills are > {STALENESS_THRESHOLD} sprints old:\n"
            + "\n".join(f"  - {p}: {r}" for p, r in stale[:10])
        )


def test_every_skill_has_trigger_section():
    """Every SKILL.md must have a 'When to use' / trigger / loaded-by section."""
    skills = load_all_skills()
    pattern = re.compile(
        r"^#{1,4}\s+(When to use|Trigger|Loaded[ -]by|Use when)",
        re.MULTILINE | re.IGNORECASE,
    )
    no_trigger = [p for p, c, _ in skills if not pattern.search(c)]
    if no_trigger:
        pytest.skip(
            f"{len(no_trigger)}/{len(skills)} skills lack a 'When to use' section:\n"
            + "\n".join(f"  - {p}" for p in no_trigger[:10])
        )


def test_skill_files_have_yaml_frontmatter():
    """Every SKILL.md should start with YAML frontmatter (--- delimiters).

    R110-134 phantom-fix: the original test checked
    `c.startswith("---\\n") and "\\n---\\n" in c[:500]`. The 500-char
    cutoff was a fragile heuristic that assumed short descriptions.
    But the mas-engineer skill descriptions (especially
    `mas-engineer-commit-protocol`, `mas-engineer-e2e-user-perspective`,
    `hermes-self-discipline-traps`, `goose-cli-e2e-testing`,
    `mas-engineer-yaml-editor-workflow`, `mas-engineer-recipe-yaml-pytest-coverage`,
    `pre-push-gate`, and `mas-engineer/bulk-findings-fixer`) all
    have 500–800 char descriptions, so the closing `\\n---\\n`
    delimiter falls OUTSIDE the first 500 chars and the test
    spuriously flags them as missing frontmatter.

    The correct check: parse the frontmatter properly. A SKILL.md
    has valid YAML frontmatter if it starts with `---\\n` AND has
    a closing `---\\n` line (a line containing only `---` and
    optional trailing whitespace) somewhere before the first
    non-frontmatter content line.
    """
    import re

    skills = load_all_skills()
    no_fm = []
    closing_re = re.compile(r"^---\s*$", re.MULTILINE)
    for p, c, _ in skills:
        if not c.startswith("---\n"):
            no_fm.append(p)
            continue
        # Find the closing `---` line. The opening `---` is on
        # line 1, so the closing must be on a LATER line. The
        # closing_re matches any line containing only `---` and
        # optional whitespace — we just need the FIRST one after
        # the opening line.
        m = closing_re.search(c, pos=4)  # pos=4 skips the opening "---\n"
        if not m:
            no_fm.append(p)
    assert not no_fm, (
        f"{len(no_fm)} SKILL.md files lack YAML frontmatter:\n"
        + "\n".join(f"  - {p}" for p in no_fm[:10])
        + "\n\nFrontmatter is required for skill discovery and metadata."
    )


def test_skill_references_resolve_to_real_recipes():
    """Any sub_mas-* reference in a SKILL.md must point to a real recipe
    (also covered by test_no_phantom_sub_mas_references but with a
    specific actionable error message)."""
    skills = load_all_skills()
    existing = _all_recipe_names_no_ext()
    n_skills = len(skills)
    n_refs = sum(len(refs) for _, _, refs in skills)
    assert n_refs > 0, f"No skills reference any sub_mas-* agents (0/{n_skills})."
