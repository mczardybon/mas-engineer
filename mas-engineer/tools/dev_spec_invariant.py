#!/usr/bin/env python3
"""
dev_spec_invariant.py — R110-118 DIREKTIVE 2: test-count vs recipe-count invariant.

Detects spec-drift (R110-78) between what tests ASSERT and what recipes DECLARE:
    test asserts  "110 sub-agents"   but recipe declares "96 sub-agents"
    → INVARIANT-sub-agents BLOCKER finding.

The invariant is the machine-checkable core of "spec-drift resistance":
when a count changes in the canonical source (recipe or test), the other
side MUST be updated in the same commit. This tool makes that drift
visible at pre-push time (Check 18) and in the IM-pipeline (Pattern C
of dev_self_audit.py).

API:
    def run_spec_invariant_check(repo_root: Path) -> SpecInvariantResult
    class SpecInvariantResult:
        def to_findings(self) -> list[Finding]

CLI:
    python3 -m dev_spec_invariant --repo-root <path>
    exit 0 if all invariants match, 1 if ≥1 BLOCKER finding.

Extract-functions (also importable for unit tests):
    a) extract_count_assertions_from_tests(tests_dir)
       Regex: COUNT_ASSERT_RE = re.compile(
                r'''assert\s+["'](\d+)\s+(\w[\w-]*)["']\s+in\s+''')
       TYPE_MIN_LEN = 2
       TYPE_BLACKLIST = {"tests", "files", "lines", "args",
                         "items", "keys", "values", "chars"}
       Returns: dict[type, set[count]] e.g. {"sub-agents": {110}}
    b) extract_count_from_recipes(recipe_dir)
       Regex: r'(\d+)\s+(\w[\w-]*)' on recipe/sub/*.yaml
       Skip in: comments, multiline-strings, valid_yaml
       Returns: dict[type, set[count]]

Invariant-check:
    for type, test_counts in test_assertions.items():
      recipe_counts = recipe_counts.get(type, set())
      if test_counts != recipe_counts:
        emit_finding(code=f"INVARIANT-{type}", severity=BLOCKER,
                     description=..., suggested_fix=...)

Spec: .directives/R110-118-self-audit-implementation.md DIREKTIVE 2.
"""

import argparse
import glob
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

COUNT_ASSERT_RE = re.compile(
    r'''assert\s+["'](\d+)\s+(\w[\w-]*)["']\s+in\s+''')
COUNT_DECLARE_RE = re.compile(r'(\d+)\s+(\w[\w-]*)')

TYPE_MIN_LEN = 2
TYPE_BLACKLIST = {
    "tests", "files", "lines", "args",
    "items", "keys", "values", "chars",
}

# Heuristic: a line inside a docstring (""" ... """) or comment.
def _is_docstring_or_comment(lines, idx):
    stripped = lines[idx].lstrip()
    if stripped.startswith('#'):
        return True
    # crude docstring region detection: count triple-quotes up to idx
    open_quotes = 0
    for i in range(idx + 1):
        s = lines[i].strip()
        if s.startswith('"""') or '"""' in s:
            open_quotes += 1
    return open_quotes % 2 == 1


def extract_count_assertions_from_tests(tests_dir):
    """Return dict[type, set[count]] from assert "N type" in ... literals."""
    tests_dir = Path(tests_dir)
    result = {}
    if not tests_dir.is_dir():
        return result
    for tf in sorted(glob.glob(str(tests_dir / 'test_*.py'))):
        if '__pycache__' in tf or tf.endswith('.pyc'):
            continue
        try:
            lines = open(tf, errors='ignore').read().splitlines()
        except Exception:
            continue
        for idx, line in enumerate(lines):
            if _is_docstring_or_comment(lines, idx):
                continue
            for m in COUNT_ASSERT_RE.finditer(line):
                cnt, typ = m.group(1), m.group(2).lower()
                if len(typ) < TYPE_MIN_LEN or typ in TYPE_BLACKLIST:
                    continue
                result.setdefault(typ, set()).add(int(cnt))
    return result


def extract_count_from_recipes(recipe_dir):
    """Return dict[type, set[count]] from recipe/sub/*.yaml scalar values.

    Skips: comments, multiline (block) strings, YAML keys — i.e. only
    single-line string scalar VALUES of the parsed YAML are scanned
    (the 'valid_yaml' rule from the spec).
    """
    import yaml
    recipe_dir = Path(recipe_dir)
    result = {}
    if not recipe_dir.is_dir():
        return result
    for yf in sorted(glob.glob(str(recipe_dir / '*.yaml'))):
        if '__pycache__' in yf or 'template' in yf or 'legacy' in yf:
            continue
        try:
            data = yaml.safe_load(open(yf, errors='ignore'))
        except Exception:
            continue
        if not isinstance(data, (dict, list)):
            continue

        def walk(node):
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
            elif isinstance(node, str) and '\n' not in node:
                for m in COUNT_DECLARE_RE.finditer(node):
                    cnt, typ = m.group(1), m.group(2).lower()
                    if len(typ) < TYPE_MIN_LEN or typ in TYPE_BLACKLIST:
                        continue
                    result.setdefault(typ, set()).add(int(cnt))

        walk(data)
    return result


@dataclass
class Finding:
    code: str
    severity: str
    description: str
    suggested_fix: str


@dataclass
class SpecInvariantResult:
    """Result of a spec-invariant check run."""
    test_assertions: dict = field(default_factory=dict)
    recipe_counts: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)

    def to_findings(self):
        """Return the findings list (stable ordering by code)."""
        return sorted(self.findings, key=lambda f: f.code)


def run_spec_invariant_check(repo_root: Path) -> SpecInvariantResult:
    """Run the full invariant check over a repo root."""
    repo_root = Path(repo_root)
    tests_dir = repo_root / 'tests'
    recipe_dir = repo_root / 'recipe' / 'sub'
    test_assertions = extract_count_assertions_from_tests(tests_dir)
    recipe_counts = extract_count_from_recipes(recipe_dir)
    res = SpecInvariantResult(
        test_assertions=test_assertions,
        recipe_counts=recipe_counts,
    )
    for typ in sorted(test_assertions):
        tc = test_assertions[typ]
        rc = recipe_counts.get(typ, set())
        if tc == rc:
            continue
        res.findings.append(Finding(
            code=f"INVARIANT-{typ}",
            severity="BLOCKER",
            description=(
                f"Test asserts {sorted(tc)} '{typ}' "
                f"but recipe declares {sorted(rc) if rc else '∅'}"
            ),
            suggested_fix=(
                "Update test OR recipe to match (find which "
                "is canonical via git blame)."
            ),
        ))
    return res


def _print_findings(res):
    for f in res.to_findings():
        print(f"  ❌ {f.code} [{f.severity}]: {f.description}")
        print(f"     fix: {f.suggested_fix}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Spec-invariant: test count-assertions vs recipe count-declarations")
    ap.add_argument('--repo-root', type=Path, default=Path('.'),
                    help='Repository root (default: .)')
    args = ap.parse_args(argv)

    res = run_spec_invariant_check(args.repo_root)
    findings = res.to_findings()
    if findings:
        print(f"🔍 spec-invariant: {len(findings)} BLOCKER finding(s)")
        _print_findings(res)
        print("   → spec-drift present (R110-78): fix test or recipe, then re-run")
        return 1
    print("✅ spec-invariant: all test count-assertions match recipe count-declarations")
    return 0


if __name__ == '__main__':
    sys.exit(main())
