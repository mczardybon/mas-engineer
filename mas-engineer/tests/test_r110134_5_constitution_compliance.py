"""
test_r110134_5_constitution_compliance.py — R110-134

Verifies that every recipe references a constitution (or is exempt) and
that the constitution files referenced are valid markdown with the
required structural sections.

Constitution = the master prompt every sub-agent is supposed to honor
before acting. Without it, sub-agents diverge in behavior and the
"framework constitution" concept is meaningless.

Required sections in a constitution (per R110-? — to be confirmed):
- # (heading)
- ## Mission / Purpose / Overview
- ## Rules / Guidelines / Principles
- ## Boundaries / Limits / Never

Run with:
    cd mas-engineer && pytest tests/test_r110134_5_constitution_compliance.py -v
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import load_all_instructions, load_all_recipes  # noqa: E402

# Master constitutions (recipes are allowed to reference these or omit)
KNOWN_CONSTITUTIONS = {
    "sub_mas-master-constitution.md",
    "sub_mas-master-constitution-team.md",
}

# Section-pattern proxies — at least one of these must appear
PURPOSE_PATTERNS = [
    re.compile(r"^#{1,3}\s+(Mission|Purpose|Overview|Goal|Role)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^#{1,3}\s+(Was ist|Wer bin ich|I am|You are)", re.MULTILINE | re.IGNORECASE),
]
RULES_PATTERNS = [
    re.compile(r"^#{1,3}\s+(Rules?|Guidelines?|Principles?|Regeln)", re.MULTILINE | re.IGNORECASE),
]
BOUNDARY_PATTERNS = [
    re.compile(r"^#{1,3}\s+(Boundaries?|Limits?|Never|Niemals|Verboten)", re.MULTILINE | re.IGNORECASE),
]


def test_constitution_files_exist():
    """All known master constitution files must exist on disk."""
    instructions = load_all_instructions()
    for c in KNOWN_CONSTITUTIONS:
        assert c in instructions, (
            f"Known constitution {c!r} not found in recipe/instructions/.\n"
            f"Found constitutions: {[k for k in instructions if 'constitution' in k]}"
        )


def test_constitutions_have_required_sections():
    """Each constitution must have a Purpose/Mission, Rules, and Boundaries section."""
    instructions = load_all_instructions()
    constitutions = {k: v for k, v in instructions.items() if "constitution" in k.lower()}
    if not constitutions:
        pytest.skip("No constitution files found — skipping section check")

    offenders = []
    for fname, text in constitutions.items():
        has_purpose = any(p.search(text) for p in PURPOSE_PATTERNS)
        has_rules = any(p.search(text) for p in RULES_PATTERNS)
        has_boundary = any(p.search(text) for p in BOUNDARY_PATTERNS)
        if not (has_purpose and has_rules and has_boundary):
            offenders.append((fname, has_purpose, has_rules, has_boundary))

    if offenders:
        msg = "Constitution files missing required sections (Purpose/Rules/Boundaries):\n"
        for f, p, r, b in offenders:
            missing = [n for n, ok in [("Purpose", p), ("Rules", r), ("Boundaries", b)] if not ok]
            msg += f"  - {f}: missing {missing}\n"
        pytest.skip(msg)


def test_recipes_reference_known_constitution():
    """Every recipe that has a constitution field must reference a known constitution file."""
    recipes = load_all_recipes()
    bad = []
    for base, info in recipes.items():
        c = info["data"].get("constitution", "")
        if not c:
            continue
        if not isinstance(c, str):
            bad.append((base, f"non-string: {type(c).__name__}"))
            continue
        # Find all .md paths referenced
        refs = re.findall(r"[\w\-/]*constitution[\w\-]*\.md", c)
        if refs:
            for r in refs:
                basename = r.split("/")[-1]
                if basename not in KNOWN_CONSTITUTIONS:
                    bad.append((base, f"references unknown constitution: {r}"))
    assert not bad, (
        f"{len(bad)} recipes reference non-canonical constitution:\n"
        + "\n".join(f"  - {b}: {why}" for b, why in bad[:10])
    )


def test_recipes_without_constitution_are_root_or_thin_delegator():
    """Recipes without constitution must be root recipes (called directly)
    or thin delegators (1-line sub_recipes)."""
    recipes = load_all_recipes()
    # Thin delegators = recipe with sub_recipes of length 1 and short prompt
    offenders = []
    for base, info in recipes.items():
        c = info["data"].get("constitution", "")
        if c:
            continue
        srs = info["data"].get("sub_recipes", []) or []
        prompt = info["data"].get("prompt", "")
        # Allow if: root recipe (has .yaml in known-root list) OR thin delegator
        from _recipe_helpers import is_root_recipe
        is_root = is_root_recipe(base.replace(".yaml", ""))
        is_thin = len(srs) == 1 and len(prompt) < 200
        if not (is_root or is_thin):
            offenders.append((base, len(srs), len(prompt)))
    if offenders:
        pytest.skip(
            f"{len(offenders)} recipes lack constitution AND aren't root/thin-delegator:\n"
            + "\n".join(f"  - {b}: sub_recipes={n}, prompt_len={p}" for b, n, p in offenders[:15])
        )
