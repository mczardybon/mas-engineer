#!/usr/bin/env python3
"""dev_dashboard_data.py v1.0.0 — Dashboard Data Generator for MCP App
======================================================================
Liest Monitoring-Data und writes JSON for the framework-Dashboard.
Will via Goose Scheduler all 5 Min OR auf User-Refresh ausgeleads.

Output: {workspace}/.mas/dashboards/data.json
History: {workspace}/.mas/dashboards/history.json

call: python3 dev_dashboard_data.py --workspace /path
"""
import json, os, subprocess, glob, sys, re
from datetime import datetime

def shell(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ''

def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except:
            pass
    return default if default is not None else {}

def yaml_load(path):
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except:
        return {}

def get_git_log(path, count=10):
    try:
        r = subprocess.run(['git', 'log', '--oneline', '--no-decorate', f'-{count}'],
                           capture_output=True, text=True, cwd=path, timeout=5)
        return [l for l in r.stdout.strip().split('\n') if l]
    except:
        return []

def generate_data(ws):
    ws_abs = os.path.abspath(ws)
    state_dir = os.path.join(ws_abs, 'mas-engineer', '.state')
    dash_dir = os.path.join(ws_abs, '.mas', 'dashboards')
    sub_dir = os.path.join(ws_abs, 'mas-engineer', 'recipe', 'sub')
    dist_dir = os.path.join(ws_abs, 'dist')
    docs_dir = os.path.join(ws_abs, 'mas-engineer', 'docs')

    mode_file = os.path.join(ws_abs, '.mas-mode')
    mode = open(mode_file).read().strip() if os.path.exists(mode_file) else 'mas'

    # ─── AGENTS ───
    sub_files = sorted(glob.glob(os.path.join(sub_dir, 'sub_mas-*.yaml')))
    agent_count = len(sub_files)

    gu = yaml_load(os.path.join(state_dir, 'guardian.yaml'))
    g = gu.get('guardian', {})
    g_agents = g.get('agents', {})

    agent_scores = []
    total_score = 0
    healthy_count = 0
    degraded_count = 0
    dead_count = 0

    for name, info in g_agents.items():
        st = info.get('status', 'unknown')
        score = info.get('score', 0)
        try:
            score = float(score)
        except:
            score = 0
        total_score += score
        agent_scores.append({'name': name.replace('.yaml', ''), 'score': score, 'status': st})
        if st == 'healthy':
            healthy_count += 1
        elif st in ('degraded', 'soft_dead'):
            degraded_count += 1
        else:
            dead_count += 1

    if agent_scores and healthy_count == 0 and degraded_count == 0 and dead_count == 0:
        healthy_count = len(g_agents)

    avg_score = round(total_score / len(g_agents), 1) if g_agents else 0

    issues = g.get('findings_summary', {})
    last_scan = g.get('last_scan', None)

    # ─── CHANGES ───
    changes = load_json(os.path.join(state_dir, 'changes.json'), [])
    if isinstance(changes, dict):
        changes = list(changes.values()) if not isinstance(changes.get('changes'), list) else changes.get('changes', [])
    changes_last = []
    for c in changes[-10:]:
        action = c.get('action', c.get('description', '?'))[:80]
        ts = str(c.get('timestamp', c.get('ts', '?')))[:19]
        changes_last.append({'ts': ts, 'desc': action})
    changes_total = len(changes)
    change_typees = {}
    for c in changes:
        a = c.get('action', c.get('description', ''))
        if 'SI-RUN' in a or 'improve' in a.lower():
            k = 'Self-Improve'
        elif 'prompt' in a.lower():
            k = 'Prompt'
        elif 'FIX' in a or 'fix' in a.lower():
            k = 'Fixes'
        elif 'CONSTITUTION' in a:
            k = 'Constitution'
        elif 'CHECKPOINT' in a:
            k = 'Checkpoints'
        elif 'DASHBOARD' in a:
            k = 'Dashboard'
        else:
            k = 'Elseige'
        change_typees[k] = change_typees.get(k, 0) + 1

    # ─── IMPROVEMENT ───
    schedule = yaml_load(os.path.join(state_dir, 'schedule.yaml'))
    hist = schedule.get('history', [])
    rec = schedule.get('recommendation', {})

    si_runs = len(hist)
    si_last = hist[-1] if hist else None
    si_status = rec.get('status', 'n/a')
    si_next = rec.get('next_round_after', '?')

    # Improve Log letzter entry
    si_last_title = 'No SI-RUN'
    si_log_file = os.path.join(docs_dir, 'improve-log.md')
    if os.path.exists(si_log_file):
        with open(si_log_file) as f:
            content = f.read()
        sections = re.split(r'\n## ', content)
        for sec in sections[1:]:
            lines = sec.strip().split('\n')
            si_last_title = lines[0].strip()[:80]

    # ─── BUILD ───
    dist_zips = sorted(glob.glob(os.path.join(dist_dir, 'mas-framework-*.zip')))
    build = {'exists': len(dist_zips) > 0, 'total_count': len(dist_zips)}
    if dist_zips:
        latest = dist_zips[-1]
        mtime = os.path.getmtime(latest)
        build['latest_name'] = os.path.basename(latest)
        build['latest_date'] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        build['latest_size_kb'] = round(os.path.getsize(latest) / 1024)

    # ─── DISPATCH ───
    dispatch = {"total": 0, "done": 0, "failed": 0, "active": 0, "avg_duration_ms": 0}
    dt_file = os.path.join(dash_dir, '_dispatch.json')
    if os.path.exists(dt_file):
        dispatch = load_json(dt_file, dispatch)
    else:
        dt_tool = os.path.join(ws_abs, 'mas-engineer', 'tools', 'dev_dispatch_tracker.py')
        if os.path.exists(dt_tool):
            out = shell(f'python3 {dt_tool} --json 2>/dev/null', timeout=5)
            if out:
                try:
                    d = json.loads(out)
                    dispatch = {"total": d.get('total', 0), "done": d.get('done', 0),
                                "failed": d.get('errors', 0), "active": d.get('running', 0),
                                "avg_duration_ms": d.get('avg_duration_ms', 0)}
                except:
                    pass

    # ─── HEALTH REPORT ───
    health_report = load_json(os.path.join(state_dir, 'health-report.json'), {})
    health_checks = {}
    for c in health_report.get('checks', []):
        health_checks[c['name']] = c.get('detail', '')

    # ─── HEALTH TREND (History) ───
    history_file = os.path.join(dash_dir, 'history.json')
    history = load_json(history_file, {"health_trend": [], "build_size": []})

    now_str = datetime.now().strftime('%H:%M')
    mas_health = 100
    if degraded_count > 0:
        mas_health = 70
    if agent_count == 0:
        mas_health = 0

    history['health_trend'].append({'time': now_str, 'score': mas_health})
    if len(history['health_trend']) > 24:
        history['health_trend'] = history['health_trend'][-24:]

    history.setdefault('build_size', [])
    if build.get('exists'):
        history['build_size'].append({'time': now_str, 'kb': build.get('latest_size_kb', 0)})
        if len(history['build_size']) > 24:
            history['build_size'] = history['build_size'][-24:]

    # ─── PROJECT NAME ───
    project_name = os.path.basename(ws_abs)

    # ─── RESULT ───
    return {
        "version": "1.0.0",
        "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "workspace": ws_abs,
        "mode": mode,
        "project_name": project_name,
        "agents": {
            "total": max(agent_count, len(g_agents)),
            "healthy": healthy_count,
            "degraded": degraded_count,
            "dead": dead_count,
            "avg_score": avg_score,
            "scores": sorted(agent_scores, key=lambda x: x['score'], reverse=True)[:15],
            "guardian_scan": last_scan,
            "issues": {
                "total": issues.get('total_issues', 0),
                "long_instructions": issues.get('long_instructions', 0),
            }
        },
        "changes": {
            "total": changes_total,
            "last_10": changes_last,
            "by_typee": change_typees,
        },
        "improvement": {
            "total_runs": si_runs,
            "last_run": si_last_title,
            "schedule_status": si_status,
            "next_round_after": si_next,
        },
        "dispatch": dispatch,
        "build": build,
        "health": {
            "score": health_report.get('score', None),
            "last_report": health_report.get('timestamp', None),
            "checks": health_checks,
        },
        "health_trend": history['health_trend'],
    }


def main():
    ws = '.'
    if '--workspace' in sys.argv:
        idx = sys.argv.index('--workspace')
        if idx + 1 < len(sys.argv):
            ws = sys.argv[idx + 1]
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        ws = sys.argv[1]

    data = generate_data(ws)
    ws_abs = os.path.abspath(ws)
    dash_dir = os.path.join(ws_abs, '.mas', 'dashboards')
    os.makedirs(dash_dir, exist_ok=True)

    data_path = os.path.join(dash_dir, 'data.json')
    with open(data_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    history_path = os.path.join(dash_dir, 'history.json')
    with open(history_path, 'w') as f:
        json.dump({"health_trend": data['health_trend'],
                   "build_size": data.get('build', {}).get('latest_size_kb', [])}, f, indent=2)

    print(f"✅ Dashboard-Data written: {data_path}")
    print(f"   Agents: {data['agents']['total']} | Changes: {data['changes']['total']} | "
          f"SI-Runs: {data['improvement']['total_runs']} | Dispatch: {data['dispatch']['total']}")

if __name__ == '__main__':
    main()
