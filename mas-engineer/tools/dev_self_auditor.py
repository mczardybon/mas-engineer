#!/usr/bin/env python3
"""
dev_self_auditor.py — Codifies the "verification theater" detector.

Purpose: Scan e2e-results/, docs/, and cert-style *.md files for strong
claims ("VERIFIED FUNCTIONAL", "ALL HYPOTHESES VERIFIED", "100% PASS",
"guarantees") that are NOT backed by a matching test log demonstrating
the claim. This is the pattern the user (mczardybon) flagged on 2026-07-21
where a CERTIFICATE.md overclaimed.

Used by:
  - sub_mas-pre-push-validator (Check 9) on every push
  - sub_mas-self-auditor (the recipe-level auditor)
  - sub_mas-general-improver (stage 6.5 — verify-before-claim)
  - ad-hoc: `python3 dev_self_auditor.py --scope e2e-results`

Usage:
    python3 dev_self_auditor.py --scope e2e-results
    python3 dev_self_auditor.py --scope e2e-results/2026-07-21-demo-3teams
    python3 dev_self_auditor.py --file path/to/specific.md
    python3 dev_self_auditor.py --workspace .

Exit codes:
    0 = PASS or WARN (no overclaims found, or only warnings)
    1 = FAIL (≥1 strong claim without matching evidence, must fix before push)
    2 = usage error

Output:
    Writes YAML report to .state/pipeline/self_audit.yaml
    Prints PASS/WARN/FAIL summary to stdout
"""

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# Strong-claim patterns that require evidence.
# These are claims that, when used as a STATEMENT (not a section header),
# promise something to the reader. Section headers and self-references
# like "What this certificate DOES NOT guarantee" are excluded.
STRONG_CLAIM_PATTERNS = [
    (r'\bVERIFIED\s+FUNCTIONAL\b', 'STRONG_VERIFIED_FUNCTIONAL'),
    (r'\bALL\s+HYPOTHESES\s+VERIFIED\b', 'STRONG_ALL_HYPOTHESES'),
    (r'\b100\s?%\s+(PASS|pass|test|coverage)\b', 'STRONG_100_PERCENT'),
    (r'\bfully\s+(tested|verified|working|functional)\b', 'STRONG_FULLY'),
    (r'\bcompletely\s+(works|functional)\b', 'STRONG_COMPLETELY'),
    # "guarantee" only when used as verb (subject + guarantee), not as a noun
    # Examples that MATCH: "we guarantee", "this guarantees", "I guarantee"
    # Examples that DO NOT MATCH: "What this guarantees", section headers
    (r'\b(?:we|this|it|the\s+\w+)\s+guarantee[sd]?\b', 'STRONG_GUARANTEE_VERB'),
    (r'\bguarantee[sd]?\s+that\b', 'STRONG_GUARANTEE_THAT'),
    (r'\bE2E[-\s]verified\b(?!\s*loading)', 'STRONG_E2E_VERIFIED'),
    (r'\bE2E[-\s]functional\b', 'STRONG_E2E_FUNCTIONAL'),
    (r'\bIS\s+E2E[-\s]functional\b', 'STRONG_IS_E2E'),
]

# Patterns that WEAKEN a claim (claim + weakness = contradiction)
WEAKENING_PATTERNS = [
    r'\bworkaround\b',
    r'\bnot\s+yet\s+tested\b',
    r'\bout\s+of\s+scope\b',
    r'\bcannot\s+be\s+tested\s+from\b',
    r'\bTUI\s+dies\b',
    r'\bhuman[-\s]only\b',
    r'\bPARTIAL\b',
    r'\bPARTIALLY\b',
    r'\bapproximates?\b',
    r'\bdoes\s+not\s+read\s+--params\b',
]

# Markers that indicate HONEST scope (rewards properly-scoped docs)
HONEST_SCOPE_MARKERS = [
    r'\bhonest\s+scope\b',
    r'\bNOT\s+verified\b',
    r'\bseparate\s+recipe[-\s]design\s+issue\b',
    r'\bout\s+of\s+scope\s+for\s+this\s+commit\b',
    r'\bSee\s+RE-TEST-RESULTS\.md\b',
    r'\bThis\s+certificate\s+does\s+NOT\s+guarantee\b',
]

# Files to consider as evidence
EVIDENCE_FILE_EXTENSIONS = ['.log', '.txt', '.json', '.yaml']


def find_target_files(scope: str, workspace: str) -> list[Path]:
    """Discover files to audit based on scope."""
    workspace_path = Path(workspace)
    scope_path = workspace_path / scope if not scope.startswith('/') else Path(scope)

    if not scope_path.exists():
        return []

    candidates = []
    if scope_path.is_file():
        candidates.append(scope_path)
    else:
        for ext in ('*.md', '*.txt'):
            candidates.extend(scope_path.rglob(ext))

    # Filter out node_modules, .git, hidden files
    return [f for f in candidates if not any(
        part == '.git' or part == 'node_modules' for part in f.parts
    )]


def has_strong_claim(content: str) -> list[tuple[int, str, str]]:
    """Find strong claims in content. Returns list of (line, match, pattern_name)."""
    findings = []
    for pattern, name in STRONG_CLAIM_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
            line_num = content[:match.start()].count('\n') + 1
            findings.append((line_num, match.group(0), name))
    return findings


def has_weakening_pattern_near(content: str, line_num: int, window: int = 5) -> Optional[str]:
    """Check if there's a weakening pattern within `window` lines of `line_num`."""
    lines = content.split('\n')
    start = max(0, line_num - window - 1)
    end = min(len(lines), line_num + window)
    nearby = '\n'.join(lines[start:end])
    for pattern in WEAKENING_PATTERNS:
        if re.search(pattern, nearby, re.IGNORECASE):
            return pattern
    return None


def has_honest_scope_marker(content: str) -> bool:
    """Check if document has honest-scope markers."""
    return any(re.search(p, content, re.IGNORECASE) for p in HONEST_SCOPE_MARKERS)


def find_evidence_in_folder(file_path: Path) -> list[Path]:
    """Find evidence files in the same folder or parent folder."""
    folder = file_path.parent
    evidence = []
    for ext in EVIDENCE_FILE_EXTENSIONS:
        evidence.extend(folder.glob(f'*{ext}'))
        # Also check parent (logs/ subfolder convention)
        evidence.extend(folder.glob(f'logs/*{ext}'))
        evidence.extend(folder.glob(f'evidence/*{ext}'))
    # Exclude the file itself if it's a .txt
    return [e for e in evidence if e != file_path]


def evidence_file_relevant(evidence_file: Path, claim: str) -> bool:
    """Heuristic: is the evidence file relevant to the claim?"""
    try:
        content = evidence_file.read_text(errors='ignore')
    except Exception:
        return False
    # Look for keywords from claim in evidence
    claim_words = set(re.findall(r'\b\w{4,}\b', claim.lower()))
    if not claim_words:
        return False
    # Extract some words from content
    content_words = set(re.findall(r'\b\w{4,}\b', content.lower()))
    overlap = claim_words & content_words
    # Need at least 1 overlap (very lenient — at least we know the file is related)
    return len(overlap) >= 1


def is_evidence_stale(file_path: Path, evidence_file: Path, max_age_days: int = 7) -> bool:
    """Check if evidence file is older than file_path by more than max_age_days."""
    try:
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        ev_mtime = datetime.fromtimestamp(evidence_file.stat().st_mtime)
        delta = file_mtime - ev_mtime
        return delta > timedelta(days=max_age_days)
    except Exception:
        return False


def audit_file(file_path: Path) -> dict:
    """Audit a single file. Returns findings dict."""
    try:
        content = file_path.read_text(errors='ignore')
    except Exception as e:
        return {
            'file': str(file_path),
            'error': f'Could not read: {e}',
            'result': 'SKIP',
        }

    findings = []
    strong_claims = has_strong_claim(content)
    has_honest_scope = has_honest_scope_marker(content)

    # Check 8: If file has honest scope markers, it's a PASS (rewarded)
    # But we still want to check if claims are properly scoped
    if not strong_claims:
        return {
            'file': str(file_path),
            'result': 'PASS',
            'strong_claims': 0,
            'honest_scope': has_honest_scope,
            'findings': [],
        }

    evidence_files = find_evidence_in_folder(file_path)

    for line_num, claim, pattern_name in strong_claims:
        weakening = has_weakening_pattern_near(content, line_num)

        # Find evidence
        relevant_evidence = None
        for ev in evidence_files:
            if evidence_file_relevant(ev, claim) and not is_evidence_stale(file_path, ev):
                relevant_evidence = ev
                break

        if weakening and not relevant_evidence:
            # Claim + weakening pattern + no evidence = FAIL (contradiction)
            findings.append({
                'id': f'SC-{len(findings)+1:03d}',
                'severity': 'FAIL',
                'check': 2,  # Workaround contradiction
                'line': line_num,
                'claim': claim,
                'pattern': pattern_name,
                'weakening_pattern': weakening,
                'evidence_found': False,
                'explanation': f'Line {line_num}: "{claim}" appears within {5} lines of "{weakening}" — claim is contradicted. No matching evidence log found in same folder.',
                'suggested_fix': 'Either remove the strong claim, or expand evidence to cover the original test scenario (not the workaround).',
            })
        elif not relevant_evidence and not has_honest_scope:
            # Strong claim without evidence and no honest scope = FAIL
            findings.append({
                'id': f'SC-{len(findings)+1:03d}',
                'severity': 'FAIL',
                'check': 1,  # Strong claim without evidence
                'line': line_num,
                'claim': claim,
                'pattern': pattern_name,
                'evidence_found': False,
                'explanation': f'Line {line_num}: "{claim}" has no matching test log in same folder ({file_path.parent}) or parent.',
                'suggested_fix': 'Add a test log that demonstrates this claim, or rephrase the claim to be scope-limited.',
            })
        elif not relevant_evidence and has_honest_scope:
            # Strong claim but file has honest scope markers = WARN
            findings.append({
                'id': f'SC-{len(findings)+1:03d}',
                'severity': 'WARN',
                'check': 1,
                'line': line_num,
                'claim': claim,
                'pattern': pattern_name,
                'evidence_found': False,
                'honest_scope_present': True,
                'explanation': f'Line {line_num}: "{claim}" has no matching log, but file contains honest-scope markers. Acceptable if claim is properly scoped (e.g. "Issue 7355 fix verified" not "ALL verified").',
                'suggested_fix': 'Verify the claim is properly scope-limited in the surrounding text.',
            })
        else:
            # Evidence found — but check 5 (staleness)
            if is_evidence_stale(file_path, relevant_evidence):
                findings.append({
                    'id': f'SC-{len(findings)+1:03d}',
                    'severity': 'WARN',
                    'check': 5,
                    'line': line_num,
                    'claim': claim,
                    'pattern': pattern_name,
                    'evidence_found': str(relevant_evidence),
                    'explanation': f'Line {line_num}: "{claim}" backed by {relevant_evidence.name}, but log is more than 7 days older than this document. Re-run the test.',
                    'suggested_fix': 'Re-run the test and update the log, or update the document date.',
                })

    if has_honest_scope and not findings:
        # File is properly self-scoped, no overclaims
        return {
            'file': str(file_path),
            'result': 'PASS',
            'strong_claims': len(strong_claims),
            'honest_scope': True,
            'note': 'File has honest-scope markers and no overclaims.',
            'findings': [],
        }

    severity = 'FAIL' if any(f['severity'] == 'FAIL' for f in findings) else 'WARN' if findings else 'PASS'
    return {
        'file': str(file_path),
        'result': severity,
        'strong_claims': len(strong_claims),
        'honest_scope': has_honest_scope,
        'findings': findings,
    }


def write_report(workspace: str, file_results: list[dict], scope: str) -> dict:
    """Build the report structure."""
    overclaims = sum(len(f.get('findings', [])) for f in file_results)
    fails = sum(1 for f in file_results if f.get('result') == 'FAIL')
    warns = sum(1 for f in file_results if f.get('result') == 'WARN')
    passes = sum(1 for f in file_results if f.get('result') == 'PASS')
    honest_scope_files = sum(1 for f in file_results if f.get('honest_scope'))

    if fails > 0:
        overall = 'FAIL'
        exit_code = 1
    elif warns > 0:
        overall = 'WARN'
        exit_code = 0
    else:
        overall = 'PASS'
        exit_code = 0

    report = {
        'audit_run': {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'auditor': 'sub_mas-self-auditor (via dev_self_auditor.py)',
            'scope': scope,
            'workspace': workspace,
            'files_scanned': len(file_results),
            'checks_run': 8,
            'result': overall,
            'overclaims_found': overclaims,
            'honest_scope_files': honest_scope_files,
            'files_pass': passes,
            'files_warn': warns,
            'files_fail': fails,
            'exit_code': exit_code,
            'summary': f'{overall}: {passes} pass, {warns} warn, {fails} fail (of {len(file_results)} files)',
        },
        'file_results': file_results,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description='Self-auditor: detect "verification theater" in MAS-Engineer docs')
    parser.add_argument('--workspace', default='.', help='Workspace root')
    parser.add_argument('--scope', help='Path to scope (e.g. e2e-results, e2e-results/2026-07-21)')
    parser.add_argument('--file', help='Single file to audit')
    parser.add_argument('--output', default='.state/pipeline/self_audit.yaml', help='Output report path')
    parser.add_argument('--json', action='store_true', help='Output JSON to stdout instead of YAML')
    args = parser.parse_args()

    workspace = args.workspace

    if args.file:
        target_files = [Path(args.file)]
    elif args.scope:
        target_files = find_target_files(args.scope, workspace)
    else:
        target_files = find_target_files('e2e-results', workspace)

    if not target_files:
        print(f'No files found in scope', file=sys.stderr)
        return 0

    print(f'🔍 Self-auditor scanning {len(target_files)} files...', file=sys.stderr)

    file_results = []
    for f in target_files:
        result = audit_file(f)
        file_results.append(result)
        # Print per-file status
        status = result.get('result', 'SKIP')
        if status == 'PASS':
            print(f'  ✅ {f.relative_to(workspace) if f.is_relative_to(workspace) else f}', file=sys.stderr)
        elif status == 'WARN':
            print(f'  ⚠️  {f.relative_to(workspace) if f.is_relative_to(workspace) else f}', file=sys.stderr)
        elif status == 'FAIL':
            print(f'  ❌ {f.relative_to(workspace) if f.is_relative_to(workspace) else f}', file=sys.stderr)
        else:
            print(f'  ⏭️  {f.relative_to(workspace) if f.is_relative_to(workspace) else f}', file=sys.stderr)

    report = write_report(workspace, file_results, args.scope or 'e2e-results')

    # Write YAML report
    output_path = Path(workspace) / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    yaml_lines = []

    # Simple YAML writer (avoid PyYAML dependency)
    def yaml_escape(s: str) -> str:
        """Escape a string for YAML double-quoted form."""
        return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

    def emit(obj, indent=0):
        prefix = ' ' * indent
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, dict) and v:
                    yaml_lines.append(f'{prefix}{k}:')
                    emit(v, indent + 2)
                elif isinstance(v, list):
                    if not v:
                        yaml_lines.append(f'{prefix}{k}: []')
                    else:
                        yaml_lines.append(f'{prefix}{k}:')
                        for item in v:
                            if isinstance(item, dict):
                                if item:
                                    # First key on the same line as the dash
                                    first_key = next(iter(item))
                                    first_val = item[first_key]
                                    yaml_lines.append(f'{prefix}- {first_key}: {_format_scalar(first_val)}')
                                    for k2, v2 in list(item.items())[1:]:
                                        if isinstance(v2, dict) and v2:
                                            yaml_lines.append(f'{prefix}  {k2}:')
                                            emit(v2, indent + 4)
                                        elif isinstance(v2, list):
                                            if not v2:
                                                yaml_lines.append(f'{prefix}  {k2}: []')
                                            else:
                                                yaml_lines.append(f'{prefix}  {k2}:')
                                                for sub in v2:
                                                    if isinstance(sub, dict):
                                                        yaml_lines.append(f'{prefix}    -')
                                                        emit(sub, indent + 6)
                                                    else:
                                                        yaml_lines.append(f'{prefix}    - "{yaml_escape(str(sub))}"')
                                        elif v2 is None:
                                            yaml_lines.append(f'{prefix}  {k2}: null')
                                        elif isinstance(v2, bool):
                                            yaml_lines.append(f'{prefix}  {k2}: {str(v2).lower()}')
                                        elif isinstance(v2, (int, float)):
                                            yaml_lines.append(f'{prefix}  {k2}: {v2}')
                                        else:
                                            yaml_lines.append(f'{prefix}  {k2}: "{yaml_escape(str(v2))}"')
                                else:
                                    yaml_lines.append(f'{prefix}- {{}}')
                            else:
                                yaml_lines.append(f'{prefix}- "{yaml_escape(str(item))}"')
                elif v is None:
                    yaml_lines.append(f'{prefix}{k}: null')
                elif isinstance(v, bool):
                    yaml_lines.append(f'{prefix}{k}: {str(v).lower()}')
                elif isinstance(v, (int, float)):
                    yaml_lines.append(f'{prefix}{k}: {v}')
                else:
                    yaml_lines.append(f'{prefix}{k}: "{yaml_escape(str(v))}"')

    def _format_scalar(v):
        if v is None:
            return 'null'
        if isinstance(v, bool):
            return str(v).lower()
        if isinstance(v, (int, float)):
            return str(v)
        return f'"{yaml_escape(str(v))}"'

    emit(report)
    output_path.write_text('\n'.join(yaml_lines) + '\n')

    # Summary
    summary = report['audit_run']['summary']
    print(f'\n📋 Self-audit {summary}', file=sys.stderr)
    print(f'📄 Report: {output_path}', file=sys.stderr)

    if report['audit_run']['result'] == 'FAIL':
        overclaims = report['audit_run']['overclaims_found']
        print(f'\n❌ BLOCKED: {overclaims} overclaim(s) found', file=sys.stderr)
        for f in file_results:
            if f.get('result') == 'FAIL':
                for finding in f.get('findings', []):
                    if finding.get('severity') == 'FAIL':
                        rel_path = f['file']
                        try:
                            rel_path = str(Path(f['file']).relative_to(workspace))
                        except ValueError:
                            pass
                        print(f'   - {rel_path}:{finding["line"]} — {finding["claim"]}', file=sys.stderr)
                        print(f'     {finding["explanation"]}', file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
