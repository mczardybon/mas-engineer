#!/usr/bin/env python3
"""dev_app_builder.py v2.2.0 — Dashboard Status Generator (Full Feature)
======================================================================
Generates mas-dashboard-status.json for the "mas-framework-hub" in the workspace.
Contains ALL Framework-Informationen user-freundlich aufreadyet.
"""
import json, os, subprocess, glob, tempfile
from datetime import datetime

WORKSPACE = os.environ.get('MAS_WORKSPACE', '.')
HISTORY_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-history.json")


def shell(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except: return ''


def get_git_log(path, count=10, filter_path=None):
    cmd = ['git', 'log', '--oneline', '--no-decorate', f'-{count}']
    if filter_path: cmd += ['--', filter_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=path, timeout=5)
        return [l for l in r.stdout.strip().split('\n') if l]
    except: return []


def build_status(ws):
    ws_abs = os.path.abspath(ws)
    mas_dir = os.path.join(ws_abs, 'mas-engineer')
    fw_dir = os.path.join(ws_abs, 'framework')
    state_dir = os.path.join(mas_dir, '.state')
    tools_dir = os.path.join(mas_dir, 'tools')
    sub_dir = os.path.join(mas_dir, 'recipe', 'sub')
    docs_dir = os.path.join(mas_dir, 'docs')

    # ─── MODUS ───
    mode_file = os.path.join(ws_abs, '.mas-mode')
    mode = open(mode_file).read().strip() if os.path.exists(mode_file) else 'mas'

    # ─── AGENTEN ───
    agents = []
    sub_files = sorted(glob.glob(os.path.join(sub_dir, 'sub_mas-*.yaml')))
    for f in sub_files:
        agents.append(os.path.basename(f).replace('.yaml', ''))

    guardian_data = {"healthy": 0, "degraded": 0, "total": 0, "details": []}
    gf = os.path.join(state_dir, 'guardian.yaml')
    if os.path.exists(gf):
        try:
            import yaml
            g = yaml.safe_load(open(gf))
            for name, info in g.get('guardian',{}).get('agents',{}).items():
                st = info.get('status','unknown')
                sc = info.get('prompt_score', '?')
                guardian_data['total'] += 1
                if st == 'healthy': guardian_data['healthy'] += 1
                else: guardian_data['degraded'] += 1
                guardian_data['details'].append({
                    'name': name, 'status': st, 'score': sc,
                    'last_ok': str(info.get('last_ok',''))[:19]
                })
        except: pass

    # Scores aus Guardian (has echte Data + 14 Agents)
    # Fallback: prompt_score aus YAML settings (if present) + prompt:-Block-Laenge als Indikator
    prompt_scores = []
    agent_scores = []
    guardian_scores = {}
    for d in guardian_data['details']:
        key = d['name'].replace('sub_mas-', '')
        try: guardian_scores[key] = float(d.get('score', 0)) if d.get('score') not in ('?',None,'None') else 0
        except: guardian_scores[key] = 0
    
    for f in sub_files:
        name = os.path.basename(f).replace('.yaml','')
        # Guardian-Score nehmen (der ist echt)
        score = guardian_scores.get(name, 0)
        try: score = float(score)
        except: score = 0
        prompt_scores.append(score)
        
        try:
            y = yaml.safe_load(open(f))
            agent_scores.append({
                'name': name,
                'score': score,
                'version': str(y.get('version','?')) if y else '?',
                'description': str(y.get('description',''))[:80] if y else ''
            })
        except:
            agent_scores.append({'name': name, 'score': score, 'version': '?', 'description': ''})
    
    prompt_avg = round(sum(prompt_scores)/len(prompt_scores),1) if prompt_scores else 0
    agents_at_10 = sum(1 for s in prompt_scores if s >= 9.5)

    # ─── CHANGES ───
    changes = []
    cf = os.path.join(state_dir, 'changes.json')
    if os.path.exists(cf):
        try:
            changes = json.load(open(cf))
        except: pass
    changes_count = len(changes)
    changes_last = changes[-15:] if changes else []

    # ─── CHANGES STATISTIK ───
    change_types = {}
    for c in changes:
        action = c.get('action', '?')
        # Kategorisieren
        if 'SI-RUN' in action or 'SI-RUN' in action or 'improve' in action.lower():
            key = 'SI-RUN / Self-Improve'
        elif 'PROMPT-OPTIMIZE' in action or 'prompt' in action.lower():
            key = 'Prompt-Optimierung'
        elif 'REGEL' in action or 'Rule' in action:
            key = 'Rule-Changes'
        elif 'APP' in action or 'DISPATCH' in action or 'dashboard' in action.lower():
            key = 'Dashboard / App'
        elif 'MASTER-CONSTITUTION' in action or 'CONSTITUTION' in action:
            key = 'Constitution'
        elif 'FLEET' in action or 'paralll' in action.lower():
            key = 'Fleet mode'
        elif 'FIX' in action or 'fix' in action.lower() or 'repair' in action.lower():
            key = 'Fixes'
        elif 'CHECKPOINT' in action:
            key = 'Checkpoints'
        elif 'FW-' in action or 'framework' in action.lower():
            key = 'Framework'
        else:
            key = 'Elseige'
        change_types[key] = change_types.get(key, 0) + 1

    # ─── CHECKPOINTS ───
    cp_dir = os.path.join(state_dir, 'checkpoints')
    cp_count = 0
    if os.path.exists(cp_dir):
        cp_count = len([d for d in os.listdir(cp_dir) if os.path.isdir(os.path.join(cp_dir, d))])

    # ─── TOOLS ───
    tool_count = len(glob.glob(os.path.join(tools_dir, 'dev_*.py'))) + \
                 len(glob.glob(os.path.join(tools_dir, 'dev_*.sh')))

    # ─── FLEET ───
    pp = os.path.join(tools_dir, 'dev_paralll.py')
    fleet_active = False
    if os.path.exists(pp):
        with open(pp) as f:
            fleet_active = 'max 12' in f.read() or 'max_paralll = 12' in f.read()

    # ─── SELF-IMPROVE LOG ───
    si_log = []
    si_file = os.path.join(docs_dir, 'improve-log.md')
    if os.path.exists(si_file):
        with open(si_file) as f:
            content = f.read()
        # SI-Run Eintraege parsen
        import re
        sections = re.split(r'\n## ', content)
        for sec in sections[1:]:  # Skip header
            lines = sec.strip().split('\n')
            title = lines[0].strip()
            si_log.append({'title': title[:100], 'lines': len(lines)})
    si_run_count = len(si_log)
    last_si_run = si_log[-1]['title'][:80] if si_log else 'No SI-RUN'

    # ─── SESSION-ANALYSE ───
    session_stats = {}
    sa_file = os.path.join(docs_dir, 'session-analysis-report.md')
    if os.path.exists(sa_file):
        with open(sa_file) as f:
            sa = f.read()
        # Wichtige Metriken extrahieren
        for line in sa.split('\n'):
            if 'Gesamtsessions' in line:
                session_stats['total_sessions'] = line.split('|')[2].strip() if '|' in line else '?'
            elif 'Total-Tokens' in line:
                session_stats['total_tokens'] = line.split('|')[2].strip() if '|' in line else '?'
            elif 'Gesamtkosten' in line:
                session_stats['total_cost'] = line.split('|')[2].strip() if '|' in line else '?'
            elif 'Activitysdauer' in line:
                session_stats['active_hours'] = line.split('|')[2].strip() if '|' in line else '?'

    # ─── GIT ───
    git_log = get_git_log(ws_abs, 15)
    fw_git = get_git_log(ws_abs, 10, 'framework/')

    # ─── RECIPES (Framework) ───
    fw_recipes_dir = os.path.join(fw_dir, 'dev-team', 'recipes')
    fw_recipes = {'specialists': 0, 'subs': 0, 'core': 0, 'total': 0, 'list': []}
    if os.path.exists(fw_recipes_dir):
        for root, dirs, files in os.walk(fw_recipes_dir):
            for f in files:
                if f.endswith('.yaml') and not f.endswith('.bak'):
                    fw_recipes['total'] += 1
                    fw_recipes['list'].append({'name': f, 'path': os.path.relpath(os.path.join(root, f), fw_recipes_dir)})
                    if f.startswith('specialist_'): fw_recipes['specialists'] += 1
                    elif f.startswith('sub_'): fw_recipes['subs'] += 1
                    else: fw_recipes['core'] += 1

    # ─── FRAMEWORK CONFIG ───
    fw_config = {}
    config_path = os.path.join(fw_dir, 'dev-team', 'config.yaml')
    if os.path.exists(config_path):
        try:
            import yaml
            fw_config = yaml.safe_load(open(config_path)) or {}
        except: pass

    # ─── DISPATCH ───
    dispatch = {"total": 0, "running": 0, "done": 0, "errors": 0, "avg_duration_ms": 0, "tree": []}
    dt = os.path.join(tools_dir, 'dev_dispatch_tracker.py')
    if os.path.exists(dt):
        try:
            r = subprocess.run(['python3', dt, '--json'], capture_output=True, text=True, timeout=5, cwd=ws_abs)
            if r.returncode == 0:
                data = json.loads(r.stdout)
                dispatch = {"total": data.get('total',0), "running": data.get('running',0),
                           "done": data.get('done',0), "errors": data.get('errors',0),
                           "avg_duration_ms": data.get('avg_duration_ms',0), "tree": data.get('tree',[])}
        except: pass

    # ─── DISTRIBUTION ───
    dist_dir = os.path.join(ws_abs, 'dist')
    dist_zips = sorted(glob.glob(os.path.join(dist_dir, 'mas-framework-*.zip')))
    build_info = {'exists': len(dist_zips) > 0, 'count': len(dist_zips)}
    if dist_zips:
        latest = dist_zips[-1]
        mtime = os.path.getmtime(latest)
        size = os.path.getsize(latest)
        build_info['latest'] = {
            'name': os.path.basename(latest),
            'date': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M'),
            'size_kb': round(size / 1024),
            'size_mb': round(size / 1024 / 1024, 1)
        }
        # Weekly trend
        now = datetime.now().timestamp()
        week_ago = now - 7*86400
        weekly = [z for z in dist_zips if os.path.getmtime(z) > week_ago]
        build_info['weekly_count'] = len(weekly)
        # Size-Trend
        build_info['size_trend'] = []
        for z in dist_zips[-10:]:
            zs = os.path.getsize(z)
            zm = datetime.fromtimestamp(os.path.getmtime(z))
            build_info['size_trend'].append({'date': zm.strftime('%m-%d %H:%M'), 'kb': round(zs/1024)})

    # ─── USER-FRAMEWORK ───
    user_fw = None
    if mode != 'mas' or True:  # Always check
        if os.path.exists(fw_dir):
            user_folders = [d for d in os.listdir(fw_dir)
                           if os.path.isdir(os.path.join(fw_dir, d)) and d != 'dev-team' and not d.startswith('.')]
            if user_folders:
                folder = user_folders[0]
                uf_recipes_dir = os.path.join(fw_dir, folder, 'recipes')
                uf_recipe_count = 0
                uf_recipe_list = []
                if os.path.exists(uf_recipes_dir):
                    for f in os.listdir(uf_recipes_dir):
                        if f.endswith('.yaml'):
                            uf_recipe_count += 1
                            uf_recipe_list.append(f)
                uf_config = {}
                try:
                    import yaml
                    uf_config = yaml.safe_load(open(os.path.join(fw_dir, folder, 'config.yaml'))) or {}
                except: pass
                uf_git = get_git_log(ws_abs, 5, f'framework/{folder}/')
                user_fw = {
                    'detected': True,
                    'name': folder,
                    'workspace': os.path.join(fw_dir, folder),
                    'status': 'active',
                    'recipes': uf_recipe_count,
                    'recipe_list': uf_recipe_list[:10],
                    'config_provider': uf_config.get('active_provider','?'),
                    'config_model': uf_config.get('providers',{}).get(uf_config.get('active_provider',''),{}).get('model','?'),
                    'git': uf_git
                }

    if not user_fw:
        user_fw = {'detected': False, 'workspace': None, 'status': None, 'recipes': 0, 'recipe_list': []}

    # ═══════════════════════════════════════════════════
    #  RESULT
    # ═══════════════════════════════════════════════════

    result = {
        'version': '1.0.0',
        'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'mode': mode,
        'mas': {
            'version': '1.0.0',
            'agents': len(agents),
            'agent_health': {
                'total': guardian_data['total'],
                'healthy': guardian_data['healthy'],
                'degraded': guardian_data['degraded'],
                'details': guardian_data['details']
            },
            'prompt_score_avg': prompt_avg,
            'agents_at_10': agents_at_10,
            'agent_scores': agent_scores,
            'changes': changes_count,
            'changes_by_type': change_types,
            'changes_last': [{'action': c.get('action','')[:80], 'ts': str(c.get('timestamp',''))[:19]} for c in changes_last],
            'checkpoints': cp_count,
            'tools': tool_count,
            'fleet_active': fleet_active,
            'fleet_max_paralll': 12,
            'general_improve': {
                'total_runs': si_run_count,
                'last_run': last_si_run,
                'log_entries': si_log[-10:]  # Letzte 10
            },
            'session_stats': session_stats,
            'build': build_info,
            'git': git_log
        },
        'framework': {
            'recipes': {
                'total': fw_recipes['total'],
                'specialists': fw_recipes['specialists'],
                'subs': fw_recipes['subs'],
                'core': fw_recipes['core'],
                'list': fw_recipes['list'][:20]
            },
            'config': {
                'provider': fw_config.get('active_provider','?'),
                'model': fw_config.get('providers',{}).get(fw_config.get('active_provider',''),{}).get('model','?'),
                'extensions': [k for k,v in fw_config.get('extensions',{}).items() if v.get('enabled')]
            },
            'git': fw_git
        },
        'dispatch': dispatch,
        'user_framework': user_fw,
        'actions': [
            {'id': 'test', 'label': '🧪 Tests execute', 'command': '/develop --test'},
            {'id': 'build', 'label': '📦 Distribution bauen', 'command': '/develop --build'},
            {'id': 'si-run', 'label': '🔄 SI-RUN start', 'command': '/develop --improve'},
            {'id': 'audit', 'label': '🔍 Config-Audit', 'command': '/develop --config-audit'},
            {'id': 'guardian', 'label': '🛡️ Guardian-Check', 'command': '/develop --guardian-check'},
            {'id': 'doc-check', 'label': '📝 Doc-Check', 'command': '/develop --doc-check'},
            {'id': 'knowledge', 'label': '🧠 Wissenslandkarte', 'command': '/develop --knowledge-map'},
            {'id': 'blueprint', 'label': '📐 Bauplan create', 'command': '/develop --blueprint'},
        ]
    }
    return result


def update_history(data):
    history = {"health_trend": [], "dispatch_volume": [], "build_size": []}
    if os.path.exists(HISTORY_FILE):
        try:
            history = json.load(open(HISTORY_FILE))
            # Altlasten clean: missing Keys add
            for k in ["health_trend", "dispatch_volume", "build_size"]:
                if k not in history: history[k] = []
        except:
            history = {"health_trend": [], "dispatch_volume": [], "build_size": []}

    now = datetime.now().strftime('%H:%M')
    mas_health = 100
    if data.get('mas',{}).get('agent_health',{}).get('degraded',0) > 0: mas_health = 70
    if data.get('mas',{}).get('agent_health',{}).get('total',0) == 0: mas_health = 0

    history['health_trend'].append({'time': now, 'mas': mas_health, 'framework': 100})
    if len(history['health_trend']) > 48: history['health_trend'] = history['health_trend'][-48:]

    history['dispatch_volume'].append({'time': now, 'count': data.get('dispatch',{}).get('total',0)})
    if len(history['dispatch_volume']) > 48: history['dispatch_volume'] = history['dispatch_volume'][-48:]

    build = data.get('mas',{}).get('build',{})
    if build.get('exists'):
        kb = build.get('latest',{}).get('size_kb',0)
        history['build_size'].append({'time': now, 'kb': kb})
        if len(history['build_size']) > 48: history['build_size'] = history['build_size'][-48:]

    json.dump(history, open(HISTORY_FILE, 'w'), indent=2)
    return history


def generate_status(ws):
    result = build_status(ws)
    result['history'] = update_history(result)
    os.makedirs(tempfile.gettempdir(), exist_ok=True)
    json.dump(result, open(os.path.join(tempfile.gettempdir(), 'mas-dashboard-status.json'), 'w'), indent=2, ensure_ascii=False)
    return result


# ═══════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════
if __name__ == '__main__':
    import sys
    ws = '.'
    if '--workspace' in sys.argv:
        idx = sys.argv.index('--workspace')
        if idx + 1 < len(sys.argv): ws = sys.argv[idx + 1]
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        ws = sys.argv[1]

    if '--generate' in sys.argv:
        r = generate_status(ws)
        print(json.dumps({"status":"ok", "agents":r['mas']['agents'],
                          "recipes":r['framework']['recipes']['total'],
                          "dispatch":r['dispatch']['total'],
                          "si_runs":r['mas']['general_improve']['total_runs']}))

    elif '--init' in sys.argv:
        r = generate_status(ws)
        print("MAS Framework Hub v2.2.0 — Initialisiert")
        print(f"  Agents: {r['mas']['agents']} (∅{r['mas']['prompt_score_avg']})")
        print(f"  Improve-Runs: {r['mas']['general_improve']['total_runs']}")
        print(f"  FW-Rezepte: {r['framework']['recipes']['total']}")
        print(f"  Dispatch: {r['dispatch']['total']} Calls")
        print(f"  Builds: {r['mas']['build'].get('count',0)}")

    else:
        r = build_status(ws)
        print(f"Dashboard: {r['mas']['agents']} Agents (∅{r['mas']['prompt_score_avg']}), "
              f"{r['mas']['general_improve']['total_runs']} SI-Runs, "
              f"{r['framework']['recipes']['total']} FW-Rezepte, "
              f"{r['dispatch']['total']} Dispatch-Calls")
