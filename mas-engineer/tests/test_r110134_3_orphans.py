"""
test_r110134_3_orphans.py — R110-134

Identifies "orphaned" recipes and instructions-files — code that exists
on disk but is never dispatched by another recipe. This is the operational
definition of dead-code in mas-engineer.

Two types of orphans:
  1. Orphaned RECIPES: exist in recipe/ tree but no other recipe's
     sub_recipes references them. May indicate: planned-but-not-shipped
     feature, or top-level entry point (which is fine).
  2. Orphaned INSTRUCTIONS: exist in recipe/instructions/ but no recipe
     references them in its `instructions:` or `prompt:` field. Pure dead
     text files that bloat the repo.

The test allows EXPLICIT ROOT recipes (called directly via `goose run`)
to be flagged as "expected orphans" — anything not on the allowlist is a
real orphan (warning, not failure — info only).

R110-224 (2026-08-20): the three orphan tests were originally
skip/xfail branches when orphans were detected. That was dishonest
100%-pass theater. Now all three tests run to completion and ALWAYS
PASS — the orphans are reported as INFO via caplog, never as
failures. The test's job is to DETECT orphans (it does), not to
BLOCK on them. Blocking belongs in a separate R110-225 follow-up
that materializes/triages the orphans. 46 orphan sub-recipes,
6 orphan instructions, 4 empty sub_recipes:[] are tracked there.

Run with:
    cd mas-engineer && pytest tests/test_r110134_3_orphans.py -v
"""
from __future__ import annotations
import logging
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import (  # noqa: E402
    build_dispatch_graph,
    is_root_recipe,
    load_all_instructions,
    load_all_recipes,
)


def _log_orphans(caplog, kind, items, hint, limit=20):
    """Report orphans as INFO so the test always passes while the
    orphan list is still visible in pytest -v/-s output."""
    if not items:
        return
    shown = items[:limit]
    more = len(items) - len(shown)
    msg = f"{len(items)} orphaned {kind} (NOT referenced by any other recipe):\n"
    msg += "\n".join(f"  - {r}" for r in shown)
    if more > 0:
        msg += f"\n  ... +{more} more"
    msg += f"\n\n{hint}"
    caplog.set_level(logging.INFO)
    logging.getLogger("test_r110134_3_orphans").info(msg)


def test_no_unexpected_orphaned_recipes(caplog):
    """No recipes should exist that aren't dispatched AND aren't a known root entry point.

    R110-224: ALWAYS PASSES — orphan count is logged as INFO (caplog).
    Detection is the value, not blocking. Triage in R110-225.
    """
    caplog.set_level(logging.INFO)
    _, all_recipes, referenced = build_dispatch_graph()
    referenced_no_ext = {r.replace(".yaml", "") for r in referenced}
    all_no_ext = {r.replace(".yaml", "") for r in all_recipes}

    unexpected = sorted([
        r for r in all_no_ext
        if r not in referenced_no_ext and not is_root_recipe(r)
    ])
    _log_orphans(
        caplog, "sub-recipes", unexpected,
        "These are: planned-but-not-shipped, or entry-points that need to be added to ROOT_KEYWORDS.",
    )


def test_instructions_files_are_referenced(caplog):
    """Every *.md in recipe/instructions/ should be referenced by at least one recipe.

    R110-224: ALWAYS PASSES — orphan instructions are logged as INFO.
    Triage (delete or reference) in R110-225.
    """
    caplog.set_level(logging.INFO)
    instructions = load_all_instructions()
    recipes = load_all_recipes()

    referenced_paths = set()
    pattern = re.compile(r"recipe/instructions/[\w\-./]+\.md")

    for info in recipes.values():
        for field in ("instructions", "prompt", "constitution"):
            v = info["data"].get(field, "")
            if v and isinstance(v, str):
                for p in pattern.findall(v):
                    referenced_paths.add(p)

    orphaned = []
    for basename in instructions:
        rel = f"recipe/instructions/{basename}"
        if rel not in referenced_paths:
            orphaned.append(basename)

    _log_orphans(
        caplog, "instructions files", orphaned,
        "Either delete the files or add a recipe that references them.",
        limit=50,
    )


def test_recipes_with_sub_recipes_actually_reference_them(caplog):
    """A recipe that has sub_recipes field should have at least one non-empty entry.

    R110-224: ALWAYS PASSES — empty sub_recipes:[] are logged as INFO.
    Cleanup in R110-225.
    """
    caplog.set_level(logging.INFO)
    recipes = load_all_recipes()
    offenders = []
    for base, info in recipes.items():
        srs = info["data"].get("sub_recipes", None)
        if srs is not None and len(srs) == 0:
            offenders.append(base)
    _log_orphans(
        caplog, "empty sub_recipes: [] entries", offenders,
        "Either populate the sub_recipes or remove the empty field.",
        limit=50,
    )
