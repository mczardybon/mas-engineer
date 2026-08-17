#!/usr/bin/env python3
"""One-time bulk-import of run-findings into the issue-db (R110-177 PHASE 7).

Reads a findings YAML/JSON file (run-findings artifact) and registers
every finding as an open issue in `.mase/pipeline/issue_db.json`.

Spec: .mase/directives/R110-177-im-pipeline-issue-db.md PHASE 7.
R110-177-ADAPTATION (documented in apply commit): the R110-24 file's
actual layout is `data.findings[]` (nested under `data`), not top-level
`ranked_findings`/`findings`. The loader accepts all three shapes.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dev_issue_db import IssueDB, compute_issue_hash  # noqa: E402


def load_findings(path):
    """Load findings from yaml or json, accepting multiple layouts."""
    import yaml
    if path.endswith('.json'):
        with open(path) as f:
            data = json.load(f)
    else:
        with open(path) as f:
            data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return []
    findings = (data.get('ranked_findings')
                or data.get('findings')
                or (data.get('data') or {}).get('findings')
                or [])
    if not isinstance(findings, list):
        return []
    return findings


def main():
    p = argparse.ArgumentParser(
        description='Bulk-import run-findings into issue-db (R110-177 P7)')
    p.add_argument('--source', required=True,
                   help='Path to run-findings yaml/json')
    p.add_argument('--db', default='.mase/pipeline/issue_db.json')
    p.add_argument('--default-status', default='open',
                   choices=['open', 'false_positive'])
    args = p.parse_args()

    findings = load_findings(args.source)
    if not findings:
        print(f"No findings in {args.source}", file=sys.stderr)
        sys.exit(1)

    db = IssueDB(args.db)
    registered = 0
    skipped = 0
    duplicates = 0
    for f in findings:
        if 'type' not in f or 'file' not in f:
            skipped += 1
            continue
        # For old run-files we have no structural_pattern; use a generic one
        struct = f"{f['type'].lower()}:{f.get('id', 'unknown')}"
        h = compute_issue_hash(f['file'], f['type'], struct)
        # R110-177 PHASE 7.5 idempotency: re-importing the same source (or
        # duplicate hashes within one source) must NOT double instance_count.
        if db.exists(h):
            duplicates += 1
            continue
        instance = {
            'file': f['file'],
            'line_start': None, 'line_end': None,
            'context': 'bulk-import',
            'scanner_version': 'dev_issue_db_bulk_import.py:1.0',
            'finding_id': f.get('id', 'unknown'),
        }
        db.register(
            hash=h, type=f['type'], severity=f.get('severity', 'medium'),
            file=f['file'], structural_pattern=struct,
            issue_summary=f.get('issue', ''),
            fix_summary=f.get('fix', ''),
            instance=instance,
        )
        registered += 1

    db.save()
    print(f"BULK-IMPORT: registered {registered} issues from {args.source} "
          f"(skipped {skipped}, duplicates {duplicates})")
    print(f"DB: {args.db}")
    print(f"Summary: {db._data['summary']}")


if __name__ == '__main__':
    main()
