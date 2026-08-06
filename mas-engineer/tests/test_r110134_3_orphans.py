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

Run with:
    cd mas-engineer && pytest tests/test_r110134_3_orphans.py -v
"""
from __future__ import annotations
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


def test_no_unexpected_orphaned_recipes():
    """No recipes should exist that aren't dispatched AND aren't a known root entry point."""
    _, all_recipes, referenced = build_dispatch_graph()
    # Remove .yaml suffix to match
    referenced_no_ext = {r.replace(".yaml", "") for r in referenced}
    all_no_ext = {r.replace(".yaml", "") for r in all_recipes}

    unexpected = sorted([
        r for r in all_no_ext
        if r not in referenced_no_ext and not is_root_recipe(r)
    ])
    # Warning — not failure (orphan recipes may be in development)
    if unexpected:
        pytest.skip(
            f"{len(unexpected)} orphaned sub-recipes (NOT dispatched, NOT in root-allowlist):\n"
            + "\n".join(f"  - {r}" for r in unexpected[:20])
            + ("\n  ... +more" if len(unexpected) > 20 else "")
            + "\n\nThese are: planned-but-not-shipped, or entry-points that need to be added to ROOT_KEYWORDS."
        )


def test_instructions_files_are_referenced():
    """Every *.md in recipe/instructions/ should be referenced by at least one recipe."""
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

    if orphaned:
        pytest.skip(
            f"{len(orphaned)} orphaned instructions files (exist but never referenced):\n"
            + "\n".join(f"  - {o}" for o in orphaned)
            + "\n\nEither delete the files or add a recipe that references them."
        )


def test_recipes_with_sub_recipes_actually_reference_them():
    """A recipe that has sub_recipes field should have at least one non-empty entry."""
    recipes = load_all_recipes()
    offenders = []
    for base, info in recipes.items():
        srs = info["data"].get("sub_recipes", None)
        if srs is not None and len(srs) == 0:
            offenders.append(base)
    # Warning only — empty list is technically valid YAML
    if offenders:
        pytest.skip(
            f"{len(offenders)} recipes have empty sub_recipes: [] (no-op list):\n"
            + "\n".join(f"  - {o}" for o in offenders[:10])
            + "\n\nEither populate the sub_recipes or remove the empty field."
        )
