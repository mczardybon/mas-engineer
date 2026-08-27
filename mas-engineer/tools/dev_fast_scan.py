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
            findings.append({'type':'A1','agent':os.path.basename(f),'severity':'hoch','detail':f'NO prompt in {os.path.basename(f)}'})
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
    """Score settings quality. Per-file pass/fail, capped at 10.

    R110-261a: the original logic incremented `ok` once for EACH passing
    condition (timeout in range AND max_turns in range), but `total`
    was incremented once per FILE. This made 1 good file contribute
    ok=2,total=1,score=20.0 (math was per-condition, not per-file).
    Fix: count ok as "1 if BOTH conditions pass for this file, 0 else".
    Cap at 10 in the rounding step.
    """
    findings, ok, total = [], 0, 0
    for f in glob.glob(os.path.join(path, '**', '*.yaml'), recursive=True):
        with open(f) as fh:
            try: d = yaml.safe_load(fh)
            except: continue
        s = d.get('settings',{})
        if not s: continue
        total += 1
        t = s.get('timeout',0); m = s.get('max_turns', s.get('max_steps',0))
        # Per-file pass/fail: each condition still emits its own finding,
        # but `ok` is only 1 if BOTH are in range.
        timeout_ok = 300 <= t <= 900
        max_turns_ok = 30 <= m <= 300
        if not timeout_ok:
            if t < 300: findings.append({'type':'B1','severity':'mittel','detail':f'timeout={t} < 300'})
            elif t > 900: findings.append({'type':'B2','severity':'niedrig','detail':f'timeout={t} > 900'})
        if not max_turns_ok:
            if m < 30: findings.append({'type':'B3','severity':'niedrig','detail':f'max_turns={m} < 30'})
            elif m > 300: findings.append({'type':'B4','severity':'niedrig','detail':f'max_turns={m} > 300'})
        if timeout_ok and max_turns_ok:
            ok += 1
    # Cap at 10 — per-file pass/fail means max ok=total → max score=10.
    return findings, min(10.0, round(ok/total*10, 1)) if total else 10, total

def scan_structure(path):
    findings = []; score = 10
    files = list(glob.glob(os.path.join(path, '**', '*.yaml'), recursive=True))
    if not files: return [{'type':'C1','severity':'hoch','detail':'NOE YAMLs'}], 0, 0
    for f in files:
        with open(f) as fh:
            try: d = yaml.safe_load(fh)
            except: score -= 2; findings.append({'type':'C2','agent':os.path.basename(f),'severity':'hoch','detail':'YAML-Error'}); continue
        if not isinstance(d,dict): continue
        if 'version' not in d: score -= 1; findings.append({'type':'C3','agent':os.path.basename(f),'severity':'mittel','detail':'NO version'})
        if 'instructions' not in d: score -= 3; findings.append({'type':'C4','agent':os.path.basename(f),'severity':'hoch','detail':'NOE instructions'})
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
