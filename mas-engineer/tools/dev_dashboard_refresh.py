#!/usr/bin/env python3
"""dev_dashboard_refresh.py v1.0.0 — On-Demand Dashboard Generator
=================================================================
Will NUR auf User-Refresh aufgerufen. KEIN Daemon. KEIN Polling.
Generates Dashboard for den AKTUELLEN Workspace.

Aufruf: python3 dev_dashboard_refresh.py
Output: .mas/dashboards/project.json + formatierte Text-Output
"""
import json, os, subprocess, glob, re, sys
from datetime import datetime

WORKSPACE = os.environ.get('MAS_WORKSPACE', '.')
DASH_DIR = os.path.join(WORKSPACE, '.mas', 'dashboards')
HISTORY_FILE = os.path.join(DASH_DIR, 'history.json')


def shell(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ''


def get_git_log(path, count=10):
    try:
        r = subprocess.run(['git', 'log', '--oneline', '--no-decorate', f'-{count}'],
                           capture_output=True, text=True, cwd=path, timeout=5)
        return [l for l in r.stdout.strip().split('\n') if l]
    except:
        return []


def load_json(path, default=None):
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except:
            pass
    return default if default is not None else {}


def generate_dashboard(ws):
    ws_abs = os.path.abspath(ws)
    mas_dir = os.path.join(ws_abs, 'mas-engineer')
    state_dir = os.path.join(mas_dir, '.state')
    tools_dir = os.path.join(mas_dir, 'tools')
    sub_dir = os.path.join(mas_dir, 'recipe', 'sub')
    docs_dir = os.path.join(mas_dir, 'docs')
    dist_dir = os.path.join(ws_abs, 'dist')

    # ─── MODUS ───
    mode_file = os.path.join(ws_abs, '.mas-mode')
    mode = open(mode_file).read().strip() if os.path.exists(mode_file) else 'mas'

    # ─── AGENTEN ───
    sub_files = sorted(glob.glob(os.path.join(sub_dir, 'sub_mas-*.yaml')))
    agent_count = len(sub_files)

    guardian_data = {"healthy": 0, "degraded": 0, "critical": 0, "total": 0, "avg_score": 0}
    gf = os.path.join(state_dir, 'guardian.yaml')
    scores = []
    if os.path.exists(gf):
        try:
            g = yaml_load(gf)
            agents = g.get('guardian', {}).get('agents', {})
            for name, info in agents.items():
                st = info.get('status', 'unknown')
                sc = info.get('score', info.get('prompt_score', 0))
                try:
                    sc = float(sc)
                except:
                    sc = 0
                scores.append(sc)
                guardian_data['total'] += 1
                if st == 'healthy':
                    guardian_data['healthy'] += 1
                elif st == 'degraded':
                    guardian_data['degraded'] += 1
                else:
                    guardian_data['critical'] += 1
        except:
            pass

    guardian_data['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0

    # ─── CHANGES ───
    changes_path = os.path.join(state_dir, 'changes.json')
    changes = []
    if os.path.exists(changes_path):
        raw = open(changes_path).read().strip()
        if raw.startswith('['):
            # JSON array format
            changes = load_json(changes_path, [])
            if isinstance(changes, dict):
                changes = changes.get('changes', changes.get('entries', []))
        else:
            # NDJSON format (line-by-line)
            for line in raw.split('\n'):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        changes.append(json.loads(line))
                    except:
                        pass
    changes_count = len(changes)
    changes_last = []
    for c in changes[-10:]:
        action = c.get('action', c.get('msg', c.get('description', '?')))[:80]
        ts = str(c.get('timestamp', c.get('ts', c.get('time', '?'))))[:19]
        changes_last.append(f"{ts} {action}")

    # Categorization
    change_types = {}
    for c in changes:
        action = c.get('action', c.get('msg', c.get('description', '')))
        if 'SI-RUN' in action or 'improve' in action.lower():
            key = 'SI-RUN / Self-Improve'
        elif 'prompt' in action.lower():
            key = 'Prompt-Optimierung'
        elif 'CONSTITUTION' in action or 'constitution' in action.lower():
            key = 'Constitution'
        elif 'FIX' in action or 'fix' in action.lower() or 'repair' in action.lower():
            key = 'Fixes'
        elif 'CHECKPOINT' in action:
            key = 'Checkpoints'
        elif 'DASHBOARD' in action or 'dashboard' in action.lower():
            key = 'Dashboard'
        else:
            key = 'Elseige'
        change_types[key] = change_types.get(key, 0) + 1

    # ─── BUILD / DISTRIBUTION ───
    dist_zips = sorted(glob.glob(os.path.join(dist_dir, 'mas-framework-*.zip')))
    build_info = {'count': len(dist_zips)}
    if dist_zips:
        latest = dist_zips[-1]
        mtime = os.path.getmtime(latest)
        size = os.path.getsize(latest)
        build_info['latest'] = {
            'name': os.path.basename(latest),
            'date': datetime.fromtimestamp(mtime).strftime('%d.%m %H:%M'),
            'size_kb': round(size / 1024),
            'file_count': '?'
        }
        # Weekly count
        week_ago = datetime.now().timestamp() - 7 * 86400
        weekly = [z for z in dist_zips if os.path.getmtime(z) > week_ago]
        build_info['weekly_count'] = len(weekly)
        # Size trend (last 10)
        build_info['size_trend'] = []
        for z in dist_zips[-10:]:
            zs = os.path.getsize(z)
            zm = datetime.fromtimestamp(os.path.getmtime(z))
            build_info['size_trend'].append({'date': zm.strftime('%d.%m %H:%M'), 'kb': round(zs / 1024)})

    # ─── GIT ───
    git_log = get_git_log(ws_abs, 10)
    git_total = len(get_git_log(ws_abs, 1000))

    # ─── SELF-IMPROVE ───
    si_runs = 0
    si_last = 'No SI-RUN'
    si_last_10 = []
    si_file = os.path.join(docs_dir, 'improve-log.md')
    if os.path.exists(si_file):
        with open(si_file) as f:
            content = f.read()
        sections = re.split(r'\n## ', content)
        for sec in sections[1:]:
            lines = sec.strip().split('\n')
            title = lines[0].strip()
            si_last_10.append({'title': title[:100]})
        si_runs = len(si_last_10)
        si_last = si_last_10[-1]['title'][:80] if si_last_10 else 'No SI-RUN'

    # ─── SESSIONS ───
    session_stats = {}
    sa_file = os.path.join(docs_dir, 'session-analysis-report.md')
    if os.path.exists(sa_file):
        with open(sa_file) as f:
            sa = f.read()
        for line in sa.split('\n'):
            if 'Gesamtsessions' in line:
                session_stats['total'] = line.split('|')[2].strip() if '|' in line else '?'
            elif 'Total-Tokens' in line:
                session_stats['tokens'] = line.split('|')[2].strip() if '|' in line else '?'
            elif 'Gesamtkosten' in line:
                session_stats['cost'] = line.split('|')[2].strip() if '|' in line else '?'
            elif 'Activitysdauer' in line:
                session_stats['hours'] = line.split('|')[2].strip() if '|' in line else '?'

    # ─── DISPATCH ───
    dispatch = {"total": 0, "active": 0, "done": 0, "failed": 0, "avg_duration_ms": 0}
    dispatch_file = os.path.join(DASH_DIR, '_dispatch.json')
    if os.path.exists(dispatch_file):
        dispatch = load_json(dispatch_file, dispatch)
    else:
        # Fallback: dev_dispatch_tracer.py
        dt = os.path.join(tools_dir, 'dev_dispatch_tracer.py')
        if os.path.exists(dt):
            try:
                r = subprocess.run(['python3', dt, 'status'], capture_output=True, text=True, timeout=5, cwd=ws_abs)
                out = r.stdout
                for line in out.split('\n'):
                    if 'Total:' in line:
                        dispatch['total'] = int(line.split()[-1])
                    elif 'Active:' in line:
                        dispatch['active'] = int(line.split()[-1])
                    elif 'Done:' in line:
                        dispatch['done'] = int(line.split()[-1])
                    elif 'Failed:' in line:
                        dispatch['failed'] = int(line.split()[-1])
                    elif 'Avg:' in line:
                        ms = line.split()[-1].replace('ms', '')
                        try:
                            dispatch['avg_duration_ms'] = int(ms)
                        except:
                            pass
            except:
                pass

    # ─── TOOLS ───
    tool_count = len(glob.glob(os.path.join(tools_dir, 'dev_*.py'))) + \
                 len(glob.glob(os.path.join(tools_dir, 'dev_*.sh')))

    # ─── EXECUTION STATUS (aus memory) ───
    execution = {"has_active_plan": False, "current_task": None,
                 "last_status": None, "done": 0, "total": 0, "running": []}
    mem_dir = os.path.join(ws_abs, '.dev-team', 'memory')
    if os.path.exists(mem_dir):
        summary_files = glob.glob(os.path.join(mem_dir, 'summary-*.md'))
        if summary_files:
            latest = sorted(summary_files)[-1]
            with open(latest) as f:
                content = f.read()
            m = re.search(r'Tasks:\s*(\d+)/(\d+)/(\d+)/(\d+)', content)
            if m:
                execution['done'] = int(m.group(1))
                execution['total'] = int(m.group(2))
            execution['last_status'] = 'completed'

    # ─── HISTORY ───
    history = load_json(HISTORY_FILE, {"health_trend": [], "build_size": [], "dispatch_volume": []})

    now_str = datetime.now().strftime('%H:%M')
    mas_health = 100
    if guardian_data['degraded'] > 0:
        mas_health = 70
    if guardian_data['total'] == 0:
        mas_health = 0

    history['health_trend'].append({'time': now_str, 'mas': mas_health})
    if len(history['health_trend']) > 48:
        history['health_trend'] = history['health_trend'][-48:]

    history['dispatch_volume'].append({'time': now_str, 'count': dispatch['total']})
    if len(history['dispatch_volume']) > 48:
        history['dispatch_volume'] = history['dispatch_volume'][-48:]

    if build_info.get('latest'):
        kb = build_info['latest']['size_kb']
        history['build_size'].append({'time': now_str, 'kb': kb})
        if len(history['build_size']) > 48:
            history['build_size'] = history['build_size'][-48:]

    # ─── RESULT ───
    return {
        'dashboard_version': '1.0.0',
        'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'mode': mode,
        'workspace': ws_abs,
        'agents': {
            'total': agent_count,
            'healthy': guardian_data['healthy'],
            'degraded': guardian_data['degraded'],
            'critical': guardian_data['critical'],
            'avg_score': guardian_data['avg_score']
        },
        'execution': execution,
        'changes': {
            'total': changes_count,
            'last_10': changes_last,
            'by_type': change_types
        },
        'build': build_info,
        'git': {
            'last_10': git_log,
            'total': git_total
        },
        'self_improve': {
            'runs': si_runs,
            'last': si_last,
            'last_10': si_last_10[-10:]
        },
        'sessions': session_stats,
        'dispatch': dispatch,
        'tools': tool_count,
        'history': history
    }


def yaml_load(path):
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except:
        return {}


def format_dashboard(data):
    """Formatierte Text-Output for den User"""
    ws = data.get('workspace', '?')
    ts = data.get('generated_at', '?')[:19].replace('T', ' ')
    mode = data.get('mode', '?')
    a = data.get('agents', {})
    ch = data.get('changes', {})
    b = data.get('build', {})
    d = data.get('dispatch', {})
    si = data.get('self_improve', {})
    sess = data.get('sessions', {})
    tools = data.get('tools', 0)
    ex = data.get('execution', {})

    def line(s):
        return f"║  {str(s)[:60].ljust(60)}║"

    out = []
    out.append("╔══════════════════════════════════════════════════════════════╗")
    out.append(line("📊 DASHBOARD"))
    out.append(line(ws))
    out.append(line(f"Generates: {ts} | Refresh: manuell"))
    out.append("╠══════════════════════════════════════════════════════════════╣")
    out.append(line(""))

    # Agents
    health_icon = "✅" if a.get('degraded', 0) == 0 else "⚠️"
    out.append(line(f"🧠 AGENTEN: {a.get('total',0)} | {health_icon} Healthy {a.get('healthy',0)} | "
                    f"Degraded {a.get('degraded',0)} | ⌀ {a.get('avg_score',0)}"))
    out.append(line(""))

    # Changes
    out.append(line(f"📝 CHANGES: {ch.get('total',0)}"))
    for c in ch.get('last_10', [])[:5]:
        out.append(line(f"   {c[:57]}"))
    out.append(line(""))

    # Build
    lb = b.get('latest', {})
    if lb:
        out.append(line(f"📦 BUILD: {b.get('count',0)} | Letzter: {lb.get('date','?')} "
                        f"({lb.get('size_kb','?')} KB)"))
    else:
        out.append(line("📦 BUILD: No Distribution gebaut"))
    out.append(line(""))

    # Dispatch
    out.append(line(f"🔄 DISPATCH: {d.get('total',0)} Calls | "
                    f"✅ {d.get('done',0)} | ❌ {d.get('failed',0)} | ⌀ {d.get('avg_duration_ms',0)}ms"))
    out.append(line(""))

    # Self-Improve
    out.append(line(f"🔧 SELF-IMPROVE: {si.get('runs',0)} Runs | {si.get('last','?')[:57]}"))
    out.append(line(""))

    # Footer
    session_str = f"{sess.get('total','?')} Sessions"
    cost_str = f"💰 {sess.get('cost','?')}" if sess.get('cost') else ""
    out.append(line(f"🛠️ TOOLS: {tools} | 📊 {session_str} {cost_str}"))
    out.append(line(""))
    out.append("╚══════════════════════════════════════════════════════════════╝")

    return '\n'.join(out)


# ═══════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════
if __name__ == '__main__':
    ws = '.'
    if '--workspace' in sys.argv:
        idx = sys.argv.index('--workspace')
        if idx + 1 < len(sys.argv):
            ws = sys.argv[idx + 1]
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        ws = sys.argv[1]

    # Dashboard generate
    data = generate_dashboard(ws)

    # JSON write
    os.makedirs(DASH_DIR, exist_ok=True)
    with open(os.path.join(DASH_DIR, 'project.json'), 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # History write
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data['history'], f, indent=2)

    # Formatierte Output for User
    print(format_dashboard(data))
