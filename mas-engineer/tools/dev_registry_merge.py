#!/usr/am/env python3
"""dev_registry_merge.py — Extrahiert Muster aus Findings und merged in Registry.
Usage: dev_registry_merge.py --findings <json-str> --registry <path> --project <name>
Output: {new_patterns, merged_count, confidence_avg}"""
import json, os, sys, yaml, datetime

PATTERN_NAMES = {
    'A1': 'prompt_fehlt_komplett', 'A2': 'timeout_zu_niedrig', 'A3': 'max_steps_zu_niedrig',
    'A4': 'timeout_zu_hoch', 'B1': 'prompt_no_boundary', 'B2': 'prompt_ohne_version',
    'B3': 'prompt_ohne_emoji', 'B4': 'prompt_zu_short', 'B5': 'prompt_zu_long',
    'C1': 'instructions_ohne_input', 'C2': 'yaml_syntax_error', 'C3': 'settings_drift',
    'D1': 'no_output_format', 'D2': 'no_berechtigung', 'D3': 'rekursion',
    'E1': 'hardcodierte_pathe', 'E2': 'no_rollback', 'E3': 'backup_bloat',
    'F1': 'config_inkonsistent', 'F2': 'documentation_fehlt', 'G1': 'agent_degradiert',
    'H1': 'session_kosten_anomalie', 'H2': 'veraltete_goose_version',
    'Z1': 'cross_generisch'
}

def generate_id(typ, existing_ids):
    base = f'BP-CF-{PATTERN_NAMES.get(typ, "generic").upper()[:6]}'
    n = 1
    while f'{base}-{str(n).zfill(3)}' in existing_ids:
        n += 1
    nid = f'{base}-{str(n).zfill(3)}'
    return nid, base

def merge_findings(findings, registry_path, project):
    with open(registry_path) as f:
        reg = yaml.safe_load(f) or {}
    patterns = reg.get('patterns', [])
    existing_ids = {p['id'] for p in patterns}
    new_count, merged_count = 0, 0
    existing_projects = set()
    for p in patterns:
        if isinstance(p.get('repeated_in'), list):
            for item in p['repeated_in']:
                existing_projects.add(item)
    for p in patterns:
        if isinstance(p.get('repeated_in'), list):
            existing_projects.update(p['repeated_in'])
    existing_projects.add(project)
    total = max(1, len(existing_projects))
    for f_item in findings:
        if not isinstance(f_item, dict): continue
        typ = f_item.get('typ', 'Z1')
        name = PATTERN_NAMES.get(typ, 'cross_generisch')
        agent = f_item.get('agent', 'unknown')
        detail = f_item.get('detail', '')
        existing = None
        for p in patterns:
            if p.get('name') == name:
                existing = p
                break
        now = datetime.datetime.now().isoformat()
        if existing:
            existing['count'] += 1
            existing['last_seen'] = now
            existing['repeated_in'] = list(set(existing.get('repeated_in', []) + [project]))
            existing['confidence'] = round(existing['count'] / len(set(existing['repeated_in'])), 2)
            ev = existing.get('evidence', [])
            if len(ev) < 5:
                ev.append({'project': project, 'run': f'{now[:10]}', 'patch': f'{agent}: {detail[:50]}'})
            existing['evidence'] = ev
            merged_count += 1
        else:
            pid, _ = generate_id(typ, existing_ids)
            existing_ids.add(pid)
            new_p = {
                'id': pid, 'name': name, 'repeated_in': [project],
                'count': 1, 'first_seen': now, 'last_seen': now,
                'confidence': round(1.0 / total, 2),
                'severity': 3 if 'hoch' in f_item.get('severity','') else 2,
                'rule': f'{name.replace("_"," ").capitalize()}: {detail}',
                'evidence': [{'project': project, 'run': f'{now[:10]}', 'patch': f'{agent}: {detail[:50]}'}],
                'auto_applied': False,
                'auto_applied_to': []
            }
            patterns.append(new_p)
            new_count += 1
    reg['patterns'] = patterns
    reg['pattern_stats'] = {
        'total_projects': len(existing_projects),
        'total_runs': len(patterns),
        'total_patterns': len(patterns),
        'avg_confidence': round(sum(p.get('confidence',0) for p in patterns) / max(1,len(patterns)), 2)
    }
    reg['last_updated'] = now
    with open(registry_path, 'w') as f:
        yaml.dump(reg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return {'new_patterns': new_count, 'merged_count': merged_count,
            'confidence_avg': reg['pattern_stats']['avg_confidence']}

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--findings', required=True)
    parser.add_argument('--registry', required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    findings = json.loads(args.findings)
    result = merge_findings(findings, args.registry, args.project)
    print(json.dumps(result, indent=2))
