#!/usr/bin/env python3
"""dev_fast_scan.py — 3 Deep-Punkte: Prompts, Settings, structure
Output: JSON {findings, scores, structure_score}"""
import json, os, sys, yaml, glob, re

def scan_prompts(path):
    findings, scores = [], []
    for f in glob.glob(os.path.join(path, '**', '*.yaml'), recursive=True):
        with open(f) as fh:
            try: d = yaml.safe_load(fh)
            except: continue
        p = d.get('prompt', '') or ''
        if not p:
            findings.append({'typ':'A1','agent':os.path.basename(f),'severity':'hoch','detail':f'KEIN prompt in {os.path.basename(f)}'})
            scores.append(0); continue
        s = 10
        if '\U000000a9' not in p: s -= 2
        if '(v1.0.0)' not in p: s -= 2
        if 'NUR' not in p: s -= 2
        if len(p) > 500: s -= 2
        if len(p) < 30: s -= 1
        scores.append(max(0,s))
    return findings, round(sum(scores)/len(scores),1) if scores else 0, len(scores)

def scan_settings(path):
    findings, ok, total = [], 0, 0
    for f in glob.glob(os.path.join(path, '**', '*.yaml'), recursive=True):
        with open(f) as fh:
            try: d = yaml.safe_load(fh)
            except: continue
        s = d.get('settings',{})
        if not s: continue
        total += 1
        t = s.get('timeout',0); m = s.get('max_steps',0)
        if t < 300: findings.append({'typ':'B1', 'severity':'mittel','detail':f'timeout={t} < 300'})
        elif t > 900: findings.append({'typ':'B2','severity':'niedrig','detail':f'timeout={t} > 900'})
        else: ok += 1
        if m < 30: findings.append({'typ':'B3','severity':'niedrig','detail':f'max_steps={m} < 30'})
        elif m > 300: findings.append({'typ':'B4','severity':'niedrig','detail':f'max_steps={m} > 300'})
        elif m >= 50: ok += 1
    return findings, round(ok/total*10,1) if total else 10, total

def scan_structure(path):
    findings = []; score = 10
    files = list(glob.glob(os.path.join(path, '**', '*.yaml'), recursive=True))
    if not files: return [{'typ':'C1','severity':'hoch','detail':'KEINE YAMLs'}], 0, 0
    for f in files:
        with open(f) as fh:
            try: d = yaml.safe_load(fh)
            except: score -= 2; findings.append({'typ':'C2','agent':os.path.basename(f),'severity':'hoch','detail':'YAML-Error'}); continue
        if not isinstance(d,dict): continue
        if 'version' not in d: score -= 1; findings.append({'typ':'C3','agent':os.path.basename(f),'severity':'mittel','detail':'KEIN version'})
        if 'instructions' not in d: score -= 3; findings.append({'typ':'C4','agent':os.path.basename(f),'severity':'hoch','detail':'KEINE instructions'})
    return findings, max(0,score), len(files)

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    if '--validate' in sys.argv:
        _,score,_ = scan_structure(path)
        print(json.dumps({'valid': score>=5, 'score':score})); sys.exit(0)
    pf,ps,pc = scan_prompts(path); sf,ss,sc = scan_settings(path); tf,ts,tc = scan_structure(path)
    r = {'findings': pf+sf+tf, 'scores': {'prompt':ps,'settings':ss,'structure':ts},
         'structure_score': round((ps+ss+ts)/3,1), 'scan_duration': len(pf)+len(sf)+len(tf),
         'agents_scanned': max(pc,sc,tc)}
    print(json.dumps(r, indent=2))
