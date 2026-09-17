"""
test_r110134_2_dispatch_cycles.py — R110-134

Verifies that the dispatch graph (recipe → sub_recipes → sub_recipes → ...)
has no cycles. A cycle would cause infinite recursion at runtime, e.g.:
  A dispatches B, B dispatches A → deadlock / stack overflow.

This is a structural property of the recipe topology — different from
test_r110134_1 (broken refs) which checks link integrity, not graph shape.

Run with:
    cd mas-engineer && pytest tests/test_r110134_2_dispatch_cycles.py -v
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import build_dispatch_graph, find_cycles  # noqa: E402


def test_no_dispatch_cycles():
    """The complete dispatch graph must be acyclic (DAG)."""
    edges, _, _ = build_dispatch_graph()
    cycles = find_cycles(edges)
    assert not cycles, (
        f"{len(cycles)} dispatch cycle(s) detected (would cause infinite recursion):\n"
        + "\n".join(f"  - {' -> '.join(c)}" for c in cycles[:5])
    )


def test_dispatch_graph_is_finite():
    """A graph with N nodes and N edges has average degree 1. A cycle-free
    graph with N nodes has at most N-1 edges (forest property)."""
    edges, all_recipes, _ = build_dispatch_graph()
    n_nodes = len(all_recipes)
    n_edges = sum(len(v) for v in edges.values())
    # Looser check: just make sure it's not absurdly over-connected
    # (a true cycle would show edges >= nodes in worst case)
    assert n_edges < n_nodes * 3, (
        f"Suspicious: {n_edges} edges for {n_nodes} nodes "
        f"(avg degree {n_edges/max(1,n_nodes):.1f}). Possible cycle or duplication."
    )


def test_dispatch_depth_is_bounded():
    """Indirect cycle detection: maximum BFS depth from any root should be < 50.
    (A real cycle would be infinite; this catches accidental cycles via depth.)"""
    edges, _, _ = build_dispatch_graph()

    def max_depth(start: str, seen=None) -> int:
        if seen is None:
            seen = set()
        if start in seen:
            return 999  # cycle detected via depth
        seen = seen | {start}
        if not edges.get(start):
            return 0
        depths = [max_depth(c, seen) for c in edges[start]]
        return 1 + max(depths) if depths else 0

    # Find all nodes with no incoming edges (potential roots)
    incoming = {n: 0 for n in edges}
    for src, dsts in edges.items():
        for d in dsts:
            incoming[d] = incoming.get(d, 0) + 1
    roots = [n for n in edges if incoming.get(n, 0) == 0]
    # Also add any node that has no edges at all
    all_nodes = set(edges.keys()) | {d for v in edges.values() for d in v}
    for n in all_nodes:
        if n not in incoming and n not in roots:
            roots.append(n)

    deep = [(r, max_depth(r)) for r in roots if max_depth(r) > 50]
    assert not deep, (
        f"{len(deep)} recipes have dispatch depth > 50 (likely cycle):\n"
        + "\n".join(f"  - {r}: depth {d}" for r, d in deep[:5])
    )
