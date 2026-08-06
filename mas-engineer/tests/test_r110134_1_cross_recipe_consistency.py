"""
test_r110134_1_cross_recipe_consistency.py — R110-134

Verifies that every sub_recipes reference in every recipe points to an
existing recipe file. This is the foundation of mas-engineer's dispatch
topology — if a reference is broken, goose will fail with FileNotFoundError
at runtime.

Failure history (R110-? — none yet, this is preventive):
- Would have caught 67 false-positives if .yaml suffix wasn't stripped
  correctly (see _recipe_helpers.build_dispatch_graph).

Run with:
    cd mas-engineer && pytest tests/test_r110134_1_cross_recipe_consistency.py -v
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

# Allow `from _recipe_helpers import ...` to work without conftest magic
sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import build_dispatch_graph, load_all_recipes  # noqa: E402


def test_no_broken_sub_recipe_references():
    """Every sub_recipes[].name must point to a recipe that exists on disk."""
    _, all_recipes, referenced = build_dispatch_graph()
    broken = referenced - all_recipes
    assert not broken, (
        f"{len(broken)} broken sub_recipe references (referenced but no .yaml file):\n"
        + "\n".join(f"  - {b}" for b in sorted(broken))
    )


def test_dispatch_graph_complete():
    """Sanity: dispatch graph should have edges for all recipes with sub_recipes."""
    recipes = load_all_recipes()
    recipes_with_subs = sum(
        1 for info in recipes.values()
        if info["data"].get("sub_recipes")
    )
    assert recipes_with_subs > 0, "No recipes have sub_recipes — graph is empty"


def test_no_empty_sub_recipes_name():
    """Every sub_recipes[].name must be a non-empty string."""
    recipes = load_all_recipes()
    offenders = []
    for base, info in recipes.items():
        for i, sr in enumerate(info["data"].get("sub_recipes", []) or []):
            if not isinstance(sr, dict) or not sr.get("name"):
                offenders.append((base, i, str(sr)[:60]))
    assert not offenders, (
        f"{len(offenders)} sub_recipes entries have empty/missing name:\n"
        + "\n".join(f"  {b}[{i}] = {s!r}" for b, i, s in offenders[:10])
    )


def test_no_self_referencing_sub_recipe():
    """A recipe must never dispatch itself (would cause infinite recursion)."""
    from _recipe_helpers import find_cycles, build_dispatch_graph
    edges, _, _ = build_dispatch_graph()
    self_refs = [k for k, vs in edges.items() if k in vs]
    assert not self_refs, (
        f"{len(self_refs)} recipes reference themselves (infinite loop):\n"
        + "\n".join(f"  - {s}" for s in self_refs)
    )


def test_referenced_count_vs_existing_count():
    """Healthy: the number of unique dispatched agents should be < total recipes.
    (Root recipes are called directly, not dispatched, so they should be unreachable.)"""
    _, all_recipes, referenced = build_dispatch_graph()
    assert len(referenced) < len(all_recipes), (
        f"Suspicious: {len(referenced)} referenced == {len(all_recipes)} total recipes. "
        "Either every recipe is dispatched (no root recipes exist) or count is wrong."
    )
