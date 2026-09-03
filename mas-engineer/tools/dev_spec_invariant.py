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
    c) extract_count_from_docstrings(tests_dir)   (R110-206)
       Regex: r'(\d+)\s+(\w[\w-]*)' on the MODULE-LEVEL docstring
       (the first triple-quoted block at line 1 of tests/test_*.py).
       Skips: version-context digit runs (e.g. the "0" of "v1.0.0 checks").
       Returns: dict[type, set[count]] e.g. {"critical": {22}}
    d) extract_count_from_instructions(instructions_dir)   (R110-206)
       Regex: r'(\d+)\s+(\w[\w-]*)' on single-line prose of
       recipe/instructions/*.md.  Skips: fenced code blocks, markdown
       table rows, HTML comments, markdown headings, version-context
       digit runs.
       Returns: dict[type, set[count]] e.g. {"checks": {22}}

Invariant-check (R110-118 + R110-206 scope extension):
    for type, test_counts in test_assertions.items():
      recipe_counts = recipe_counts.get(type, set())
      if test_counts != recipe_counts:
        emit_finding(code=f"INVARIANT-{type}", severity=BLOCKER,
                     description=..., suggested_fix=...)
    # R110-206: test-docstrings and recipe/instructions/*.md prose are
    # ALSO cross-checked against the recipe count-declarations — but
    # scoped to the COUNT-DECLARATION types (checks/check/critical,
    # the F-082 class).  A docstring/instruction count that
    # contradicts the recipe declaration is a BLOCKER, and the
    # diverging files are named in the finding (F-082 scope-gap
    # closure).  Other prose types are deliberately not cross-checked
    # (R110-206 out-of-scope: "Scanning ALL prose — too noisy").
    # Cross-check skips: version/identifier contexts (v1.0.0, L01),
    # fenced + indented code blocks, inline shell one-liners,
    # markdown tables, HTML comments, headings.

Spec: .mase/directives/R110-118-self-audit-implementation.md DIREKTIVE 2.
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
        if data is None:
            # Empty yaml / yaml that parses to None -> nothing to scan
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

        # R110-322: was `if not isinstance(data, (dict, list)): continue`,
        # which silently dropped top-level string scalars. A top-level string
        # with a count-declaration (e.g. `5 ab here`) is exactly the kind of
        # single-line scalar value the docstring promises to scan, and a
        # recipe whose entire body is a one-liner count-declaration was
        # being skipped — a real spec-drift false negative. Now: any node
        # that walk() can handle (dict / list / single-line str) is walked;
        # only None (parse-to-null) is treated as "no data".
        walk(data)
    return result


def _version_context(line, digit_start):
    """True when a digit run is part of a version/range/identifier context.

    COUNT_DECLARE_RE would match the trailing '0' of 'v1.0.0' as a count
    ('0 checks').  Version strings are declarations of identity, not
    count-declarations, so digit runs immediately preceded by '.' or '-'
    are skipped (R110-206 noise filter).  Also skip digit runs preceded
    by a LETTER — identifier/lesson contexts such as 'L01 check' or
    'R110-115 DIREKTIVE' are identity tokens, not count-declarations
    (R110-206 scope-extension noise filter).
    """
    if digit_start == 0:
        return False
    prev = line[digit_start - 1]
    return prev in '.-' or prev.isalpha()


def _scan_instructions_file(md_path):
    """Yield (count, typ) pairs from single-line prose in one .md file.

    Skips: fenced code blocks (```/~~~), markdown table rows (| ... |),
    HTML comments (<!-- ... -->), ATX headings (# ...), and
    version-context digit runs.
    """
    lines = open(md_path, errors='ignore').read().splitlines()
    in_code_block = False
    in_html_comment = False
    for line in lines:
        if re.match(r'^\s*(```|~~~)', line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if '<!--' in line:
            in_html_comment = True
        if in_html_comment:
            if '-->' in line:
                in_html_comment = False
            continue
        if '-->' in line:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith('|'):
            continue
        if re.match(r'^#{1,6}\s', stripped):
            continue
        if re.match(r'^\s{4,}\S', line):
            # CommonMark: 4+ leading spaces = indented CODE block, not
            # prose (e.g. '    summary: "13 checks passed."').  The
            # directive says code blocks are skipped; this covers the
            # non-fenced form (R110-206 scope-extension noise filter).
            continue
        if '||' in line or '&&' in line or '$(' in line:
            # inline shell one-liner embedded in prose
            # (e.g. 'STEP 1 — 7 checks: error=0 [ ... ] || error=...').
            # Code, not a count-declaration (R110-206 noise filter).
            continue
        for m in COUNT_DECLARE_RE.finditer(line):
            cnt, typ = m.group(1), m.group(2).lower()
            if _version_context(line, m.start()):
                continue
            if len(typ) < TYPE_MIN_LEN or typ in TYPE_BLACKLIST:
                continue
            yield int(cnt), typ


def _scan_module_docstring(py_path):
    """Yield (count, typ) pairs from the MODULE-LEVEL docstring of a test file.

    Only the first triple-quoted block at line 1 counts (R110-206 scope).
    Function/class docstrings and code comments are NOT scanned (the
    docstring extraction is the focused case; see R110-206 out-of-scope).
    """
    lines = open(py_path, errors='ignore').read().splitlines()
    if not lines or not lines[0].lstrip().startswith('"""'):
        return
    end = 1
    while end < len(lines) and '"""' not in lines[end]:
        end += 1
    for idx in range(0, min(end, len(lines))):
        if not _is_docstring_or_comment(lines, idx):
            continue
        for m in COUNT_DECLARE_RE.finditer(lines[idx]):
            cnt, typ = m.group(1), m.group(2).lower()
            if _version_context(lines[idx], m.start()):
                continue
            if len(typ) < TYPE_MIN_LEN or typ in TYPE_BLACKLIST:
                continue
            yield int(cnt), typ


def extract_count_from_docstrings(tests_dir):
    """Return dict[type, set[count]] from module-level test docstrings.

    R110-206: closes the F-082 scope gap — a test file whose module
    docstring says "18 critical checks" (while the recipe declares 22)
    is now visible to Check 18.
    """
    tests_dir = Path(tests_dir)
    result = {}
    if not tests_dir.is_dir():
        return result
    for tf in sorted(glob.glob(str(tests_dir / 'test_*.py'))):
        if '__pycache__' in tf or tf.endswith('.pyc'):
            continue
        try:
            for cnt, typ in _scan_module_docstring(tf):
                result.setdefault(typ, set()).add(cnt)
        except Exception:
            continue
    return result


def extract_count_from_instructions(instructions_dir):
    """Return dict[type, set[count]] from single-line prose in
    recipe/instructions/*.md.

    R110-206: closes the F-082 scope gap — an instruction file whose
    prose says "21 checks" (while the recipe declares 22) is now visible
    to Check 18.  Code blocks, tables, HTML comments and headings are
    prose-noise and are skipped.
    """
    instructions_dir = Path(instructions_dir)
    result = {}
    if not instructions_dir.is_dir():
        return result
    for mf in sorted(glob.glob(str(instructions_dir / '*.md'))):
        try:
            for cnt, typ in _scan_instructions_file(mf):
                result.setdefault(typ, set()).add(cnt)
        except Exception:
            continue
    return result


def _files_with_count(files, scanner, typ, count):
    """Return sorted file names whose scan contains (typ, count)."""
    hits = []
    for f in sorted(files):
        try:
            if any(t == typ and c == count for c, t in scanner(f)):
                hits.append(Path(f).name)
        except Exception:
            continue
    return hits


@dataclass
class Finding:
    code: str
    severity: str
    description: str
    suggested_fix: str
    files: list = field(default_factory=list)  # R110-206: diverged file names


@dataclass
class SpecInvariantResult:
    """Result of a spec-invariant check run."""
    test_assertions: dict = field(default_factory=dict)
    recipe_counts: dict = field(default_factory=dict)
    test_docstrings: dict = field(default_factory=dict)      # R110-206
    instructions_counts: dict = field(default_factory=dict)  # R110-206
    findings: list = field(default_factory=list)

    def to_findings(self):
        """Return the findings list (stable ordering by code)."""
        return sorted(self.findings, key=lambda f: f.code)


def run_spec_invariant_check(repo_root: Path) -> SpecInvariantResult:
    """Run the full invariant check over a repo root (R110-118 + R110-206)."""
    repo_root = Path(repo_root)
    tests_dir = repo_root / 'tests'
    recipe_dir = repo_root / 'recipe' / 'sub'
    instructions_dir = repo_root / 'recipe' / 'instructions'
    test_assertions = extract_count_assertions_from_tests(tests_dir)
    recipe_counts = extract_count_from_recipes(recipe_dir)
    test_docstrings = extract_count_from_docstrings(tests_dir)
    instructions_counts = extract_count_from_instructions(instructions_dir)
    res = SpecInvariantResult(
        test_assertions=test_assertions,
        recipe_counts=recipe_counts,
        test_docstrings=test_docstrings,
        instructions_counts=instructions_counts,
    )
    test_files = sorted(glob.glob(str(tests_dir / 'test_*.py')))
    instruction_files = sorted(glob.glob(str(instructions_dir / '*.md')))

    # 1) R110-118: test count-assertions vs recipe count-declarations
    #    (recipe-canonical, strict — original behavior, MUST NOT regress).
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

    # 2) R110-206: test-docstrings + recipe/instructions prose are ALSO
    #    cross-checked against the recipe counts for COUNT-DECLARATION
    #    types (the F-082 class: checks/check/critical).  Recipe stays
    #    canonical; diverging files are named in the finding.
    #    Scope note (R110-206 out-of-scope "Scanning ALL prose — too
    #    noisy"): other types are NOT cross-checked here — unrelated
    #    counters legitimately share type names (e.g. the defib
    #    procedure's "7 checks" vs the validator's "23 checks"), so
    #    prose cross-checks are limited to the check-count family that
    #    F-082/MM9-EXT-002 demonstrated.  The original R110-118
    #    assert-vs-recipe check above is unchanged and still covers
    #    every type the tests assert.
    CHECK_DECL_TYPES = {"checks", "check", "critical"}

    def _check_kind(kind_label, counts, files, scanner):
        for typ in sorted(counts):
            if typ not in CHECK_DECL_TYPES:
                continue
            kc = counts[typ]
            rc = recipe_counts.get(typ, set())
            if not rc:
                # recipe silent for this type -> nothing canonical to
                # compare against (cross-kind prose agreement is
                # deferred, R110-207+ per R110-206 out-of-scope)
                continue
            for c in sorted(kc):
                if c in rc:
                    continue
                res.findings.append(Finding(
                    code=f"INVARIANT-{typ}",
                    severity="BLOCKER",
                    description=(
                        f"{kind_label} says {c} '{typ}' "
                        f"but recipe declares {sorted(rc)}"
                    ),
                    suggested_fix=(
                        "Update the diverged file OR the recipe to "
                        "match (find which is canonical via git blame)."
                    ),
                    files=_files_with_count(files, scanner, typ, c),
                ))

    _check_kind('Test docstring', test_docstrings, test_files,
                _scan_module_docstring)
    _check_kind('Instructions prose', instructions_counts,
                instruction_files, _scan_instructions_file)
    return res


def _print_findings(res):
    for f in res.to_findings():
        print(f"  ❌ {f.code} [{f.severity}]: {f.description}")
        if f.files:
            print(f"     files: {', '.join(f.files)}")
        print(f"     fix: {f.suggested_fix}")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Spec-invariant: test count-assertions + test-docstrings + "
                    "recipe/instructions/*.md literals vs recipe count-declarations")
    ap.add_argument('--repo-root', type=Path, default=Path('.'),
                    help='Repository root (default: .)')
    args = ap.parse_args(argv)

    res = run_spec_invariant_check(args.repo_root)
    findings = res.to_findings()
    if findings:
        print(f"🔍 spec-invariant: {len(findings)} BLOCKER finding(s)")
        _print_findings(res)
        print("   → spec-drift present (R110-78): fix test/recipe/instructions, then re-run")
        return 1
    print("✅ spec-invariant: all count sources match recipe count-declarations")
    return 0


if __name__ == '__main__':
    sys.exit(main())
