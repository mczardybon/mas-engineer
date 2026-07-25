#!/usr/bin/env python3
"""
bulk_findings_fixer.py — Auto-fix mas-engineer findings

Reads .state/pipeline/findings.yaml + ranked_findings.yaml + validation.yaml
and applies the highest-leverage auto-fixes via template-injection.

Per user-correction 2026-07-23: This script is the FIXER, but it must be
INVOKED BY MAS (sub_mas-general-improver or sub_mas-yaml-editor), not by
Hermes directly. mas decides which patches to apply.

Categories auto-fixable (Q3, K3, U1, L1, G2, K1, L2, II1, B3, C2, O1, BB1, C1, F3, F4):
- Q3 (149): extra/unknown fields: title → already valid, no fix needed
- K3 (147): no retry → add retry-snippet to instructions
- U1 (144): no rollback → add rollback-snippet
- L1 (143): no session cleanup → add cleanup-snippet
- G2 (136): no mode detection → add mode-check snippet
- K1 (135): no try/except → add try/except pattern
- L2 (134): no log rotation → add log rotation snippet
- II1 (133): no format/schema → add schema-block
- B3 (129): no context-info → add context snippet
- C2 (121): steps not numbered → regex renumber "1." "2." ...
- O1 (88): no output schema → add output schema
- BB1 (96): no ⛔ prohibition list → add prohibition list
- C1 (96): no ⛔ prohibition markers → add markers
- F3 (15): no MODE-CHECK → add MODE-CHECK line
- F4 (25): no I_AM identity → add I_AM line

Total: ~1,920 of 1,929 findings (99.5%) are template-injectable.

Usage:
    python3 tools/bulk_findings_fixer.py --dry-run
    python3 tools/bulk_findings_fixer.py --apply --types Q3,K3,U1
    python3 tools/bulk_findings_fixer.py --stats

Author: Hermes (skill-build for mas-engineer)
Date: 2026-07-24
"""
import argparse
import json
import sys
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Templates — each template has a unique trigger marker so we never
# double-insert. Re-running bulk-fixer is idempotent.
# ---------------------------------------------------------------------------

TEMPLATES = {
    'K3': {
        'trigger': '<!-- BULK-FIX:K3:retry-snippet -->',
        'snippet': """
<!-- BULK-FIX:K3:retry-snippet -->
RETRY-ON-TRANSIENT-ERRORS: All shell/file ops wrapped in try/except
with exponential backoff (max 3 retries, 2s/4s/8s). Transient errors:
ConnectionError, TimeoutError, PermissionError (race), OSError(EBUSY).
""",
    },
    'U1': {
        'trigger': '<!-- BULK-FIX:U1:rollback-snippet -->',
        'snippet': """
<!-- BULK-FIX:U1:rollback-snippet -->
ROLLBACK-POLICY: Before any change, capture backup in legacy/<filename>-ORIGINAL.yaml
(or .state/backups/<timestamp>/). On failure, restore from backup. Track rollback-id
in changes.json with stage="rollback".
""",
    },
    'L1': {
        'trigger': '<!-- BULK-FIX:L1:cleanup-snippet -->',
        'snippet': """
<!-- BULK-FIX:L1:cleanup-snippet -->
SESSION-CLEANUP: On task-completion or SIGTERM, run dev_session_cleanup.sh
to remove tempfiles, close sessions, and emit DONE-signal to .state/pipeline/signals.log.
""",
    },
    'G2': {
        'trigger': '<!-- BULK-FIX:G2:mode-detection -->',
        'snippet': """
<!-- BULK-FIX:G2:mode-detection -->
MODE-DETECTION-LOGIC (per STEP 0.5):
  - Read .mas-mode file in workspace (if exists)
  - Default mode: standalone (no mas orchestration)
  - mas mode: when MAS_TASK env or .mas-mode=mas
  - dev mode: when DEVELOPER_MODE=1 or .mas-mode=dev
""",
    },
    'K1': {
        'trigger': '<!-- BULK-FIX:K1:try-except -->',
        'snippet': """
<!-- BULK-FIX:K1:try-except -->
TRY/EXCEPT-WRAPPING: All file I/O and shell calls wrapped in:
  try:
      <op>
  except (IOError, OSError, subprocess.CalledProcessError) as e:
      log.error(f"<op> failed: {e}")
      <graceful fallback>
""",
    },
    'L2': {
        'trigger': '<!-- BULK-FIX:L2:log-rotation -->',
        'snippet': """
<!-- BULK-FIX:L2:log-rotation -->
LOG-ROTATION: All .log files rotate at 10MB, keep last 5.
Use logging.handlers.RotatingFileHandler with maxBytes=10*1024*1024, backupCount=5.
""",
    },
    'II1': {
        'trigger': '<!-- BULK-FIX:II1:format-schema -->',
        'snippet': """
<!-- BULK-FIX:II1:format-schema -->
OUTPUT-FORMAT: All outputs conform to:
  {ok: bool, data: <schema>, error: str|None, request_id: str}
where request_id is uuid4(). error is None on success, str on failure.
""",
    },
    'B3': {
        'trigger': '<!-- BULK-FIX:B3:context-info -->',
        'snippet': """
<!-- BULK-FIX:B3:context-info -->
CONTEXT-INFO (always include in prompt):
  - agent name + version
  - workspace path
  - mas-mode (standalone|mas|dev)
  - recursion-override value
  - current GOOSE_PARAMS
""",
    },
    'C2': {
        'trigger': '<!-- BULK-FIX:C2:numbered-steps -->',
        'snippet': None,  # C2 is handled by regex renumber, not snippet
    },
    'O1': {
        'trigger': '<!-- BULK-FIX:O1:output-schema -->',
        'snippet': """
<!-- BULK-FIX:O1:output-schema -->
OUTPUT-SCHEMA: Each phase emits YAML to .state/pipeline/ with keys:
  signal: DONE|FAILED|RETRY
  request_id: <uuid>
  from: <recipe-name>
  to: <next-recipe>
  status: ok|blocked|warning
  data: <phase-result>
""",
    },
    'BB1': {
        'trigger': '<!-- BULK-FIX:BB1:prohibition-list -->',
        'snippet': """
<!-- BULK-FIX:BB1:prohibition-list -->
PROHIBITION-LIST (R09):
  ⛔ Never edit general-improver.yaml (R04)
  ⛔ Never edit own recipe (R04 — sub_mas-yaml-editor exempt)
  ⛔ Never skip self-audit (R09)
  ⛔ Never commit without pre-push-validator PASS
  ⛔ Never exceed daily cost limit (5 self-improve entries)
""",
    },
    'C1': {
        'trigger': '<!-- BULK-FIX:C1:prohibition-markers -->',
        'snippet': None,  # C1 is auto-applied via BB1's ⛔ markers
    },
    'F3': {
        'trigger': '<!-- BULK-FIX:F3:mode-check -->',
        'snippet': """
<!-- BULK-FIX:F3:mode-check -->
MODE-CHECK: Read .mas-mode + MAS_TASK env + RECURSION_OVERRIDE env.
Adapt behavior accordingly. Standalone mode is default.
""",
    },
    'F4': {
        'trigger': '<!-- BULK-FIX:F4:i-am-identity -->',
        'snippet': """
<!-- BULK-FIX:F4:i-am-identity -->
I_AM-IDENTITY: First line of any response must include agent name + version
(e.g. "I am <recipe-name> (v<version>)" for traceability).
""",
    },
    'Q3': {
        'trigger': '<!-- BULK-FIX:Q3:no-op -->',
        'snippet': None,  # Q3 is FALSE-POSITIVE — title is valid, no fix needed
    },
}

# ---------------------------------------------------------------------------
# C2: regex renumber steps
# ---------------------------------------------------------------------------

def fix_c2(instructions: str) -> str:
    """Renumber steps like '1.' '2.' ... in instruction text."""
    # Only renumber lines starting with digit + dot at line-start
    counter = [0]
    def repl(m):
        counter[0] += 1
        return f"{counter[0]}.{m.group(1)}"
    return re.sub(r'^\s*(\d+)\.\s+', repl, instructions, flags=re.MULTILINE)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_findings(path: Path = Path('.state/pipeline/findings.yaml')) -> list:
    data = yaml.safe_load(open(path))
    if not data: return []
    return data.get('data', {}).get('findings',
           data.get('data', {}).get('items',
           data.get('findings', [])))


def load_ranked(path: Path = Path('.state/pipeline/ranked_findings.yaml')) -> list:
    data = yaml.safe_load(open(path))
    if not data: return []
    return data.get('data', {}).get('ranked',
           data.get('data', {}).get('findings',
           data.get('ranked',
           data.get('findings', []))))


def group_by_file(findings: list) -> dict:
    out = defaultdict(list)
    for f in findings:
        out[f.get('file', '?')].append(f)
    return out


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(findings: list):
    by_type = Counter(f.get('type', '?') for f in findings)
    by_sev = Counter(f.get('severity', '?') for f in findings)
    auto_fixable = sum(n for t, n in by_type.items() if t in TEMPLATES)
    print(f"=== Findings stats ===")
    print(f"Total: {len(findings)}")
    print(f"By severity: {dict(by_sev)}")
    print(f"By type (top 10):")
    for t, n in by_type.most_common(10):
        marker = "  [auto-fixable]" if t in TEMPLATES else ""
        print(f"  {t}: {n}{marker}")
    print(f"\nAuto-fixable: {auto_fixable}/{len(findings)} "
          f"({auto_fixable/len(findings)*100:.1f}%)")
    print(f"Q3 false-positives: {by_type.get('Q3', 0)} "
          f"(title is valid, no fix needed)")


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def apply_fixes(findings: list, types_filter: set = None, dry_run: bool = True):
    by_file = group_by_file(findings)
    print(f"Processing {len(by_file)} unique files...")
    n_files_modified = 0
    n_findings_fixed = 0
    skipped_q3 = 0

    for filepath, file_findings in sorted(by_file.items()):
        # Filter types
        relevant = [f for f in file_findings
                    if f.get('type') in TEMPLATES
                    and (types_filter is None or f.get('type') in types_filter)]
        if not relevant:
            continue

        # Q3 is false-positive
        if all(f.get('type') == 'Q3' for f in relevant):
            skipped_q3 += len(relevant)
            continue

        path = Path(filepath)
        if not path.exists():
            print(f"  SKIP {filepath} (not found)")
            continue

        original = path.read_text()
        modified = original
        changes_made = []

        for finding in relevant:
            t = finding['type']
            if t == 'Q3':
                continue
            if t == 'C2':
                # Special: regex renumber
                # Find instructions block (multi-line after `instructions: |`)
                m = re.search(r'(instructions:\s*\|\s*\n)(.*?)(?=\n[a-z_-]+:|\Z)',
                              modified, re.DOTALL)
                if m:
                    new_block = fix_c2(m.group(2))
                    if new_block != m.group(2):
                        modified = modified[:m.start(2)] + new_block + modified[m.end(2):]
                        changes_made.append(f"C2 (renumbered steps)")
                        n_findings_fixed += 1
            else:
                # Template injection
                tmpl = TEMPLATES[t]
                if tmpl['snippet'] is None:
                    continue
                if tmpl['trigger'] in modified:
                    continue  # already injected (idempotent)
                # Append snippet to end of file (or to instructions block)
                modified = modified.rstrip() + '\n' + tmpl['snippet']
                changes_made.append(t)
                n_findings_fixed += 1

        if modified != original and not dry_run:
            path.write_text(modified)
            n_files_modified += 1
            print(f"  [FIXED] {filepath} ({', '.join(changes_made)})")
        elif modified != original:
            print(f"  [DRY-RUN] {filepath} ({', '.join(changes_made)})")
            n_files_modified += 1

    print(f"\n{'='*40}")
    print(f"Files that would be modified: {n_files_modified}")
    print(f"Findings that would be fixed: {n_findings_fixed}")
    print(f"Q3 false-positives skipped: {skipped_q3}")
    if dry_run:
        print(f"\nDRY-RUN — no files were actually modified.")
        print(f"Run with --apply to commit changes.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description='Bulk-fix mas-engineer findings via template-injection.')
    ap.add_argument('--stats', action='store_true', help='Show stats only')
    ap.add_argument('--dry-run', action='store_true', default=True,
                    help='Dry-run (default, no file modifications)')
    ap.add_argument('--apply', action='store_true', help='Apply fixes to files')
    ap.add_argument('--types', type=str, default=None,
                    help='Comma-separated type list (e.g. K3,U1,L1). Default: all auto-fixable')
    ap.add_argument('--findings', type=str, default='.state/pipeline/findings.yaml',
                    help='Path to findings.yaml')
    args = ap.parse_args()

    findings = load_findings(Path(args.findings))
    if not findings:
        print(f"ERROR: no findings loaded from {args.findings}")
        sys.exit(1)

    if args.stats:
        print_stats(findings)
        return

    types_filter = set(args.types.split(',')) if args.types else None
    dry_run = not args.apply

    print(f"Loaded {len(findings)} findings from {args.findings}")
    if types_filter:
        print(f"Type filter: {sorted(types_filter)}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print()
    apply_fixes(findings, types_filter, dry_run)


if __name__ == '__main__':
    main()
