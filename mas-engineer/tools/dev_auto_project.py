#!/usr/am/env python3
"""dev_auto_project.py — Erkennt Framework-Struktur automatically.
Output: JSON {project, main_recipe, mode, has_tests, has_docs, prefix}"""
import json, os, sys, yaml

def detect(path):
    base = os.path.abspath(path)
    r = {'project': None, 'main_recipe': None, 'mode': 'generic',
         'prefix': None, 'has_tests': False, 'has_docs': False}
    mm = os.path.join(base, '.mas-mode')
    if os.path.exists(mm):
        with open(mm) as f:
            m = f.read().strip()
            if m in ('mas','framework','generic'): r['mode'] = m
    fw = os.path.join(base, 'framework', 'dev-team', 'recipes')
    if os.path.isdir(fw):
        for f in os.listdir(fw):
            if f.endswith('.yaml') and not f.startswith('sub_'):
                r['main_recipe'] = f; r['project'] = 'dev-team'; r['prefix'] = 'fw-'; break
    rc = os.path.join(base, 'recipes')
    if os.path.isdir(rc) and not r['main_recipe']:
        for f in os.listdir(rc):
            if f.endswith('.yaml') and not f.startswith('sub_'):
                r['main_recipe'] = f; r['project'] = os.path.basename(base); r['prefix'] = 'ag-'; break
    r['has_tests'] = os.path.isdir(os.path.join(base, 'tests'))
    r['has_docs'] = os.path.isdir(os.path.join(base, 'docs'))
    r['project_path'] = base
    return r

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(json.dumps(detect(path), indent=2))
