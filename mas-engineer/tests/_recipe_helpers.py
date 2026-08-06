"""
_recipe_helpers.py — shared utilities for the 8 new test suites
(R110-134 — "alle nur erdenklichen szenarien" test expansion).

R110-132 portability: $HERMES_HOME + $HOME/.hermes fallback + @pytest.mark.skipif
                       not needed here (we use absolute REPO_ROOT resolution).

Provides:
- load_all_recipes()       → dict[basename → {path, data}]
- load_all_instructions()  → dict[basename → text]
- load_all_skills()        → list[(path, content, referenced_sub_mas_names)]
- find_orphans()           → recipes that are never dispatched
- find_cycles()            → dispatch-graph cycles
- scan_evidence_secrets()  → R110-102 regression scanner

Run with:
    cd mas-engineer && pytest tests/test_r110134_*.py -v
"""
from __future__ import annotations
import glob as _glob
import os as _os
import re as _re
from collections import defaultdict as _defaultdict
from pathlib import Path as _Path
from typing import Any, Dict, List, Set, Tuple

import yaml as _yaml

REPO_ROOT = _Path(__file__).parent.parent.resolve()
RECIPE_DIR = REPO_ROOT / "recipe"
INSTRUCTIONS_DIR = RECIPE_DIR / "instructions"
SKILLS_DIR = REPO_ROOT / "mas-engineer" / "skills"
E2E_RESULTS_DIR = REPO_ROOT / "e2e-results"
EVIDENCE_DIRS = [E2E_RESULTS_DIR]  # R110-74a gitignored


# --- Recipe loading ---

def load_all_recipes() -> Dict[str, Dict[str, Any]]:
    """Load all *.yaml recipes under recipe/**/*.yaml.
    Returns {basename: {'path': str, 'data': dict}}."""
    out: Dict[str, Dict[str, Any]] = {}
    for f in sorted(_glob.glob(str(RECIPE_DIR / "**" / "*.yaml"), recursive=True)):
        try:
            with open(f) as fh:
                d = _yaml.safe_load(fh)
            if isinstance(d, dict) and "name" in d:
                out[_os.path.basename(f)] = {"path": f, "data": d}
        except Exception:
            pass
    return out


def load_all_instructions() -> Dict[str, str]:
    """Load all *.md instructions. Returns {basename: text}."""
    out: Dict[str, str] = {}
    for f in sorted(_glob.glob(str(INSTRUCTIONS_DIR / "*.md"))):
        try:
            with open(f) as fh:
                out[_os.path.basename(f)] = fh.read()
        except Exception:
            pass
    return out


def load_all_skills() -> List[Tuple[str, str, Set[str]]]:
    """Load all SKILL.md. Returns list of (path, content, referenced_sub_mas_names)."""
    out: List[Tuple[str, str, Set[str]]] = []
    for root, _, files in _os.walk(SKILLS_DIR):
        for f in files:
            if f == "SKILL.md":
                full = _os.path.join(root, f)
                try:
                    with open(full) as fh:
                        content = fh.read()
                except Exception:
                    continue
                # R110-134 phantom-fix: stricter regex — `sub_mas-X` segments
                # separated by `-` where each segment has at least 1
                # alphanum char. The OLD regex `sub_mas-[a-z0-9\-]+`
                # captured trailing-dash prefixes like `sub_mas-im-`
                # from bash-glob patterns such as `sub_mas-im-*.yaml`
                # in skill prose, falsely flagging them as phantom
                # recipe names. The NEW pattern:
                #
                #   sub_mas-[a-z0-9]+(?:-[a-z0-9]+)*
                #
                # - Each segment must contain at least 1 alphanum char
                #   (no empty segments, no trailing dash)
                # - Segments are separated by exactly one `-`
                # - A trailing `*` (bash glob) terminates the match
                #   (the `*` is not alphanum, so the match stops before
                #   it, leaving the trailing-dash segment empty and
                #   thus invalid)
                #
                # Also dedupe to the LONGEST match per occurrence.
                # Python's findall returns non-overlapping; we use
                # finditer and keep the longest match per start
                # position. E.g. from
                # `sub_mas-cr-validator-orchestrator` we want
                # `sub_mas-cr-validator-orchestrator` (the full
                # name), not `sub_mas-cr` or `sub_mas-cr-validator`
                # as separate "phantom" hits.
                matches = list(
                    _re.finditer(
                        r"sub_mas-[a-z0-9]+(?:-[a-z0-9]+)*", content
                    )
                )
                longest_per_start: dict = {}
                for m in matches:
                    s = m.start()
                    if s not in longest_per_start or len(m.group()) > len(
                        longest_per_start[s]
                    ):
                        longest_per_start[s] = m.group()
                refs = set(longest_per_start.values())
                out.append((full, content, refs))
    return out


# --- Topology analysis ---

def build_dispatch_graph() -> Tuple[Dict[str, List[str]], Set[str], Set[str]]:
    """Build dispatch graph from recipes.
    Returns (edges, all_recipes_no_ext, all_referenced_no_ext)."""
    recipes = load_all_recipes()
    all_basenames: Set[str] = set(_os.path.basename(p).replace(".yaml", "")
                                   for p in _glob.glob(str(RECIPE_DIR / "**" / "*.yaml"), recursive=True))
    edges: Dict[str, List[str]] = {}
    referenced: Set[str] = set()
    for base, info in recipes.items():
        key = base.replace(".yaml", "")
        srs = info["data"].get("sub_recipes", []) or []
        names: List[str] = []
        for sr in srs:
            n = sr.get("name", "") if isinstance(sr, dict) else str(sr)
            if n:
                names.append(n)
                referenced.add(n)
        edges[key] = names
    return edges, all_basenames, referenced


def find_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """DFS cycle detection in dispatch graph. Returns list of cycle paths."""
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    cycles: List[List[str]] = []

    def dfs(node: str, path: List[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for nbr in graph.get(node, []):
            if nbr not in visited:
                if dfs(nbr, path + [nbr]):
                    return True
            elif nbr in rec_stack:
                cycles.append(path + [nbr])
                return True
        rec_stack.discard(node)
        return False

    for n in graph:
        if n not in visited:
            dfs(n, [n])
    return cycles


# --- Root-recipe detection ---

ROOT_KEYWORDS = (
    "dev-mas-engineer", "dashboard-", "e2e-verify-", "test-fix-failures",
    "test-mas-user", "root_", "setup-", "static-analyzer", "security-scanner",
    "agent_template", "checkpoint", "defib", "immune", "safezone", "timeline",
    "sub_mas-bootstrap", "sub_mas-master-constitution", "sub_mas-generic-init",
)


def is_root_recipe(name: str) -> bool:
    """A root recipe is one that's called directly via `goose run` (not dispatched)."""
    return any(name.startswith(k) for k in ROOT_KEYWORDS)


# --- R110-102 secret-leak scanner ---

# Patterns that indicate an API-key leak in evidence logs
SECRET_PATTERNS = [
    (_re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "DeepSeek/OpenAI sk- key"),
    (_re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub PAT (ghp_)"),
    (_re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained PAT"),
    (_re.compile(r"Bearer\s+[A-Za-z0-9_\-]{30,}"), "Bearer token"),
    (_re.compile(r"xox[bpars]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (_re.compile(r"sk_live_[A-Za-z0-9]{20,}"), "Stripe live key"),
]


def scan_evidence_secrets() -> List[Tuple[str, str, int, str]]:
    """Scan all e2e-results/*/evidence/*.log for secret patterns.
    Returns list of (log_path, pattern_name, line_no, excerpt)."""
    leaks: List[Tuple[str, str, int, str]] = []
    for ev_dir in EVIDENCE_DIRS:
        if not ev_dir.exists():
            continue
        for log in _glob.glob(str(ev_dir / "*" / "evidence" / "*.log")):
            try:
                with open(log, errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        for pat, name in SECRET_PATTERNS:
                            if pat.search(line):
                                # Excerpt: 20 chars before, 30 after match
                                m = pat.search(line)
                                start = max(0, m.start() - 20)
                                excerpt = line[start: m.end() + 30].strip()
                                leaks.append((log, name, i, excerpt))
            except Exception:
                pass
    return leaks
