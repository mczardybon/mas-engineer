#!/usr/bin/env python3
"""dev_pattern_apply.py — Wendet high-confidence Patterns auf framework an.
Usage: dev_pattern_apply.py --registry <path> --project <name> --threshold 0.3
Output: {applied: [{pattern, agent, action}], skipped: int}"""
import json, os, sys, yaml, datetime

def get_scoped_agents(pattern_name, project_files):
    mapping = {
        'prompt_braucht_boundary': lambda f: any('prompt' in str(d.get('prompt',''))[:5] for d in [load(f)] if d),
        'settings_timeout_sweetspot': lambda f: 'settings' in str(f),
        'instructions_mit_inputblock': lambda f: 'instructions' in str(f),
        'prompt_mit_outputformat': lambda f: 'prompt' in str(f),
        'backup_vor_patch': lambda f: True
    }
    return [f for f in project_files if f.endswith('.yaml')]

def load(path):
    with open(path) as f:
        try: return yaml.safe_load(f)
        except: return {}

def apply_patterns(registry_path, project, threshold=0.3):
    with open(registry_path) as f:
        reg = yaml.safe_load(f)
    patterns = reg.get('patterns', [])
    project_files = []
    for root, dirs, files in os.walk(project):
        for f in files:
            if f.endswith('.yaml'):
                project_files.append(os.path.join(root, f))
    applied, skipped = [], 0
    for p in patterns:
        if p.get('confidence', 0) < threshold:
            skipped += 1
            continue
        if p.get('auto_applied') and project not in p.get('auto_applied_to', []):
            candidates = get_scoped_agents(p['name'], project_files)
            for cf in candidates[:3]:
                applied.append({'pattern': p['name'], 'file': cf,
                                'action': f'Apply {p["rule"][:40]}',
                                'status': 'pending'})
            p.setdefault('auto_applied_to', []).append(project)
    with open(registry_path, 'w') as f:
        yaml.dump(reg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return {'applied': applied, 'skipped': skipped}

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--registry', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--threshold', type=float, default=0.3)
    args = parser.parse_args()
    result = apply_patterns(args.registry, args.project, args.threshold)
    print(json.dumps(result, indent=2))
