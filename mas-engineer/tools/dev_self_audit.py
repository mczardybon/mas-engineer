#!/usr/bin/env python3
"""
dev_self_audit.py — R110-118 DIREKTIVE 1.3: recipe-instructions audit agent core.

MAS-internal self-audit: audits recipe/instructions/*.md for
  - Pattern A: hardcoded counts without env-var / default context
  - Pattern B: stale literals (recipe-instructions claim values that no
    longer appear anywhere in the repo)
  - Pattern C: count-assertions that drift from recipe declarations
    (delegated to dev_spec_invariant)

API:
    def run_self_audit(scope: Path, repo_root: Path) -> SelfAuditResult
    class SelfAuditResult:
        def to_findings(self) -> list[Finding]

CLI:
    python3 -m dev_self_audit --scope <dir> --repo-root <path> \
        [--output <path>]
    exit 0 if clean, 1 if ≥1 finding.

Writes a YAML report (default .state/pipeline/self_audit.yaml) with
the same audit_run/file_results structure as dev_self_auditor.py so
downstream consumers (pre-push Check 9 / STEP 6.5) can parse it.

Spec: .directives/R110-118-self-audit-implementation.md DIREKTIVE 1.
"""

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# --- Pattern A -----------------------------------------------------------
# Hardcoded count-of-things that should be configurable or derived.
# \d{2,} avoids flagging trivial numbers (1..9); the type list covers the
# "counting nouns" that historically drifted (R110-71: 96 → 110 sub-agents).
PATTERN_A_RE = re.compile(
    r'\b(\d{2,})\s+(sub-agents|tools|phases|checks)\b', re.IGNORECASE)
# Context that makes a hardcode acceptable: env-var interpolation,
# a documented default ("default 30"), or a config reference (${...}).
PATTERN_A_ACCEPT_CTX = re.compile(
    r'IM_TOP_N|default\s+\d+|\$\{[^}]+\}|env[.:]|getenv', re.IGNORECASE)

# --- Pattern B -----------------------------------------------------------
# Quoted literals in instructions that should exist elsewhere in the repo
# (mirror of check_spec_drift, restricted to recipe/instructions/).
PATTERN_B_STRING_IN_RE = re.compile(
    r'''["']([^"']{4,80})["']''')
PATTERN_B_URL_RE = re.compile(r'https?://', re.IGNORECASE)
PATTERN_B_WS_ONLY_RE = re.compile(r'^\s*$')
_B_PUNCT = re.compile(r'^[\W_]+$')

# Only "load-bearing" literals are audited (the R110-71/R110-111 drift
# patterns): repo-object paths and numeric count anchors. Prose phrases
# ('Good to know') are NOT stale-literal candidates.
_B_PATH_LIKE_RE = re.compile(
    r'^[\w./\-]+/[\w./\-]+\.(?:yaml|py|md|json|sh|txt)$')
_B_COUNT_PHRASE_RE = re.compile(
    r'^\d{2,}\s+(?:critical\s+)?(?:checks?|tests?|sub-agents|tools|'
    r'phases|rules?|findings?|stages|agents|steps)$', re.IGNORECASE)

# Files that are allowed to contain literals without a repo-wide twin:
# the file itself is the definition (self-references, spec docs).
_B_SELF_FILES = {
    'sub_mas-self-audit.md',  # self-reference exclusion per DIREKTIVE 1
}


def _is_in_docstring(lines, idx):
    open_quotes = 0
    for i in range(idx + 1):
        s = lines[i].strip()
        if s.startswith('"""') or '"""' in s:
            open_quotes += 1
    return open_quotes % 2 == 1


@dataclass
class Finding:
    code: str
    severity: str
    description: str
    suggested_fix: str


@dataclass
class SelfAuditResult:
    """Result of a self-audit run over recipe/instructions/."""
    files_scanned: int = 0
    findings: list = field(default_factory=list)

    def to_findings(self):
        return sorted(self.findings, key=lambda f: f.code)


# --- Pattern A -----------------------------------------------------------
def _scan_pattern_a(lines, rel_path):
    """Hardcoded counts without env-var / default context."""
    findings = []
    for idx, line in enumerate(lines):
        if _is_in_docstring(lines, idx):
            continue
        if line.lstrip().startswith('#'):
            continue
        for m in PATTERN_A_RE.finditer(line):
            if PATTERN_A_ACCEPT_CTX.search(line):
                continue
            count, noun = m.group(1), m.group(2).lower()
            findings.append(Finding(
                code=f"HARDCODE-{noun.upper()}",
                severity="WARN",
                description=(
                    f"{rel_path}:{idx + 1}: hardcoded '{count} {noun}' "
                    "without env-var/default/config context"
                ),
                suggested_fix=(
                    f"Reference an env var (e.g. IM_TOP_N), a documented "
                    f"'default {count}' value, or derive the count from "
                    f"the source of truth instead of hardcoding."
                ),
            ))
    return findings


# --- Pattern B -----------------------------------------------------------
def _build_repo_literal_index(repo_root, exclude_path):
    """Index quoted literals + count anchors present in recipe/tools/docs/tests."""
    index = {}
    for base in ('recipe', 'tools', 'docs', 'tests'):
        for f in glob.glob(str(repo_root / base / '**' / '*'), recursive=True):
            if os.path.isdir(f) or not os.path.isfile(f):
                continue
            if '__pycache__' in f or f.endswith('.pyc') or '/.backups/' in f:
                continue
            if os.path.abspath(f) == os.path.abspath(exclude_path):
                continue
            try:
                text = open(f, errors='ignore').read()
            except Exception:
                continue
            for m in PATTERN_B_STRING_IN_RE.finditer(text):
                index[m.group(1)] = index.get(m.group(1), 0) + 1
            for m in _B_COUNT_PHRASE_RE.finditer(text):
                phrase = ' '.join(m.group(0).split()).lower()
                index[phrase] = index.get(phrase, 0) + 1
            for m in _B_PATH_LIKE_RE.finditer(text):
                index[m.group(0)] = index.get(m.group(0), 0) + 1
    return index


def _is_in_fence(lines, line_idx):
    """True if line_idx is inside a fenced code block (``` markers)."""
    count = 0
    for i in range(line_idx + 1):
        if lines[i].lstrip().startswith('```'):
            count += 1
    return count % 2 == 1


def _strip_inline_code(line):
    """Remove `inline code` spans so their content is not scanned."""
    return re.sub(r'`[^`]*`', '', line)


# Literals that look like data values (word-like, no code punctuation).
_B_WORD_LIKE_RE = re.compile(r'^[\w][\w .\-/:,_]*$')


def _scan_pattern_b(lines, rel_path, repo_index, file_stem):
    """Stale literals: instructions claim values not found in the repo.

    Mirrors check_spec_drift filters: skip code blocks, inline code,
    URLs, whitespace-only, punctuation-only; require word-like literals.
    """
    findings = []
    for idx, line in enumerate(lines):
        if _is_in_fence(lines, idx):
            continue
        if line.lstrip().startswith('#'):
            continue
        if '|' in line:  # markdown table row
            continue
        line = _strip_inline_code(line)
        for m in PATTERN_B_STRING_IN_RE.finditer(line):
            lit = m.group(1)
            if len(lit) < 4 or len(lit) > 80:
                continue
            if PATTERN_B_URL_RE.search(lit) or PATTERN_B_WS_ONLY_RE.match(lit):
                continue
            if _B_PUNCT.match(lit) or not _B_WORD_LIKE_RE.match(lit):
                continue
            # Only load-bearing anchors are audited: repo paths + count phrases.
            if not (_B_PATH_LIKE_RE.match(lit) or _B_COUNT_PHRASE_RE.match(lit)):
                continue
            if file_stem in _B_SELF_FILES:
                continue
            if lit in repo_index:
                continue
            findings.append(Finding(
                code="STALE-LITERAL",
                severity="WARN",
                description=(
                    f"{rel_path}:{idx + 1}: literal {lit!r} appears nowhere "
                    "else in recipe/tools/docs/tests"
                ),
                suggested_fix=(
                    "Update the literal to the current value or delete it; "
                    "spec-drift (R110-78) occurs when instructions keep "
                    "stale numbers."
                ),
            ))
    return findings


# --- Pattern C -----------------------------------------------------------
def _scan_pattern_c(repo_root):
    """Delegation to dev_spec_invariant (importable module)."""
    try:
        from dev_spec_invariant import run_spec_invariant_check
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent))
        from dev_spec_invariant import run_spec_invariant_check
    res = run_spec_invariant_check(repo_root)
    return res.to_findings()


def run_self_audit(scope: Path, repo_root: Path) -> SelfAuditResult:
    """Run Patterns A+B+C over `scope` (default recipe/instructions/)."""
    scope = Path(scope)
    repo_root = Path(repo_root)
    result = SelfAuditResult()

    if not scope.is_dir():
        result.findings.append(Finding(
            code="AUDIT-ERROR",
            severity="ERROR",
            description=f"scope directory not found: {scope}",
            suggested_fix="Pass --scope to an existing directory.",
        ))
        return result

    md_files = sorted(scope.glob('*.md'))

    for md in md_files:
        rel = md.relative_to(repo_root)
        stem = md.name
        lines = md.read_text(errors='ignore').splitlines()
        result.findings += _scan_pattern_a(lines, rel)
        # Fresh index per file: excludes THIS file, so a literal that only
        # occurs in the file being scanned is not counted as "found".
        repo_index = _build_repo_literal_index(repo_root, md)
        result.findings += _scan_pattern_b(lines, rel, repo_index, stem)
    result.files_scanned = len(md_files)

    # Pattern C: delegated spec-invariant (test vs recipe counts)
    result.findings += _scan_pattern_c(repo_root)
    return result


def _write_report(result, output, repo_root, scope):
    if output is None:
        output = repo_root / '.state' / 'pipeline' / 'self_audit.yaml'
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    findings = result.to_findings()
    severity_counts = {}
    for f in findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
    summary = (
        f"{severity_counts.get('BLOCKER', 0)} blocker, "
        f"{severity_counts.get('WARN', 0)} warn, "
        f"{severity_counts.get('ERROR', 0)} error "
        f"(of {len(findings)} findings, {result.files_scanned} files)"
    )
    lines = [
        "audit_run:",
        f'  timestamp: "{datetime.now(timezone.utc).isoformat()}"',
        '  auditor: "sub_mas-self-audit (via dev_self_audit.py)"',
        f'  scope: "{Path(scope).as_posix()}"',
        f'  workspace: "{repo_root}"',
        f"  files_scanned: {result.files_scanned}",
        f"  findings_count: {len(findings)}",
        f"  result: {'FAIL' if severity_counts.get('BLOCKER') else 'PASS'}",
        f"  summary: \"{summary}\"",
        "findings:",
    ]
    for f in findings:
        lines += [
            "-",
            f'  id: "{f.code}"',
            f'  severity: "{f.severity}"',
            f'  description: "{f.description}"',
            f'  suggested_fix: "{f.suggested_fix}"',
        ]
    output.write_text("\n".join(lines) + "\n")
    return output


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Self-audit recipe/instructions/ for hardcodes, stale literals, spec-drift")
    ap.add_argument('--scope', default='recipe/instructions/',
                    help='Scope directory to audit (default: recipe/instructions/)')
    ap.add_argument('--repo-root', type=Path, default=Path('.'),
                    help='Repository root (default: .)')
    ap.add_argument('--output', type=Path, default=None,
                    help='Output YAML report path (default: .state/pipeline/self_audit.yaml)')
    args = ap.parse_args(argv)

    result = run_self_audit(Path(args.scope), args.repo_root)
    out = _write_report(result, args.output, args.repo_root, args.scope)
    findings = result.to_findings()
    for f in findings:
        print(f"  {f.code} [{f.severity}]: {f.description}")
    print(f"self-audit report: {out} ({len(findings)} findings, "
          f"{result.files_scanned} files scanned)")
    blockers = [f for f in findings if f.severity == 'BLOCKER']
    if blockers:
        print(f"❌ self-audit: {len(blockers)} BLOCKER finding(s) — exit 1")
        return 1
    print("✅ self-audit: clean")
    return 0


if __name__ == '__main__':
    sys.exit(main())
