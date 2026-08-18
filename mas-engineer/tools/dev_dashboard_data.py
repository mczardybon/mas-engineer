#!/usr/bin/env python3
"""dev_dashboard_data.py v1.1.0 - Dashboard Data Generator for MCP App
======================================================================
Reads Monitoring data and writes JSON for the framework dashboard.
Will be called via Goose Scheduler every 5 Min OR on User-Refresh.

Output: {workspace}/.mase/dashboards/data.json
History: {workspace}/.mase/dashboards/history.json

Features:
- Auto-generates data.json on each run
- Sends MCP notification for realtime dashboard updates
- Tracks health trend over time
- R110-161: Surfaces MQ aggregate (dev_message_queue) as `mq.*` keys
  in data.json so the dashboard can show queue depth, lag, DLQ count,
  and per-topic stats without needing a separate MQ-UI page.

call: python3 dev_dashboard_data.py --workspace /path

"""
import json, os, subprocess, glob, sys, re
from datetime import datetime

# R110-161: dev_message_queue is optional (graceful degradation if
# the MQ module is missing — the dashboard still renders, just
# without the `mq` block).
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    import dev_message_queue as mq
    _MQ_AVAILABLE = True
except ImportError:
    mq = None
    _MQ_AVAILABLE = False
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

def _phase1_topics_summary(topics: dict) -> dict:
    """R110-166 phase 2.3: per-phase-1-topic summary for the dashboard.

    For each of the 3 phase-1 producer topics, surface the depth,
    completed count, and a "last_msg" projection (one-line digest
    of the most recent message payload). Tells the user at a glance
    what the publishers in phase 1 have been emitting and what the
    consumers in phase 2.1/2.2 have been processing.

    Always returns a dict with all 3 keys (even when empty), so the
    dashboard template can iterate safely.
    """
    PHASE1 = (
        "im.finding.created",
        "monitor.health.degraded",
        "phoenix.recovery.completed",
    )
    # mq.stats() keys topics by the SANITIZED name (dots→underscores).
    # Reverse that here so we can look up by the logical name.
    def _safe(t: str) -> str:
        return "".join(c if c.isalnum() or c in "_-" else "_" for c in t)
    safe_to_logical = {_safe(t): t for t in PHASE1}
    out = {}
    for topic in PHASE1:
        info = topics.get(_safe(topic)) or {}
        entry = {
            "depth": int(info.get("depth", 0)),
            "completed_total": int(info.get("completed_total", 0)),
            "lag_p95_ms": int(info.get("current_p95_lag_ms", 0)),
            "dlq_count": int(info.get("dlq_count_for_topic", 0)),
            "last_msg": None,
        }
        # Try to surface the most recent message on the topic. We look
        # in the live topic first (status==pending); if none pending,
        # we read the completed file (status==done) and pick the latest
        # by acked_at. Best-effort: if anything goes wrong, leave
        # last_msg=None (we never want the dashboard refresh to fail).
        try:
            from pathlib import Path
            import json as _json
            import os as _os
            mq_root_env = _os.environ.get("MAS_MQ_ROOT")
            if mq_root_env:
                mq_root = Path(mq_root_env)
            else:
                mq_root = Path(".mase/mq")
            safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in topic)
            live = mq_root / f"{safe}.ndjson"
            done = mq_root / f"{safe}.completed.ndjson"
            last = None
            if live.exists():
                with open(live) as f:
                    for line in f:
                        try:
                            d = _json.loads(line)
                        except Exception:
                            continue
                        if d.get("status") == "pending":
                            last = d  # we keep overwriting → newest pending
            if last is None and done.exists():
                # Latest by acked_at
                candidates = []
                with open(done) as f:
                    for line in f:
                        try:
                            d = _json.loads(line)
                        except Exception:
                            continue
                        if d.get("status") == "done":
                            candidates.append(d)
                if candidates:
                    candidates.sort(key=lambda d: d.get("acked_at") or "")
                    last = candidates[-1]
            if last is not None:
                payload = last.get("payload") or {}
                # Topic-specific digest: keep payload small + readable
                if topic == "im.finding.created":
                    digest = {
                        "request_id": payload.get("request_id"),
                        "findings_total": payload.get("findings_total"),
                        "by_severity": payload.get("findings_by_severity"),
                    }
                elif topic == "monitor.health.degraded":
                    digest = {
                        "request_id": payload.get("request_id"),
                        "has_problem": payload.get("has_problem"),
                        "issues_found": payload.get("issues_found"),
                        "command": payload.get("command"),
                    }
                elif topic == "phoenix.recovery.completed":
                    digest = {
                        "request_id": payload.get("request_id"),
                        "levels_passed": payload.get("levels_passed"),
                        "levels_total": payload.get("levels_total"),
                        "final_status": payload.get("final_status"),
                    }
                else:
                    digest = {"request_id": payload.get("request_id")}
                entry["last_msg"] = {
                    "msg_id": last.get("msg_id"),
                    "consumer_id": last.get("consumer_id"),
                    "enqueued_at": last.get("enqueued_at"),
                    "acked_at": last.get("acked_at"),
                    "status": last.get("status"),
                    "digest": digest,
                }
        except Exception:
            # Best-effort: never let a broken topic file break the dashboard
            pass
        out[topic] = entry
    return out


def generate_data(ws):
    ws_abs = os.path.abspath(ws)
    # Find the mas-engineer workspace (may be ws itself or ws/mas-engineer)
    if os.path.isdir(os.path.join(ws_abs, 'recipe')):
        # ws is already the mas-engineer directory
        mas_root = ws_abs
    elif os.path.isdir(os.path.join(ws_abs, 'mas-engineer', 'recipe')):
        # ws is the parent of mas-engineer
        mas_root = os.path.join(ws_abs, 'mas-engineer')
    else:
        mas_root = ws_abs

    state_dir = os.path.join(mas_root, '.mase')
    dash_dir = os.path.join(mas_root, '.mase', 'dashboards')
    sub_dir = os.path.join(mas_root, 'recipe', 'sub')
    dist_dir = os.path.join(mas_root, 'dist')
    docs_dir = os.path.join(mas_root, 'docs')

    mode_file = os.path.join(mas_root, '.mas-mode')
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
    change_types = {}
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
            k = 'Other'
        change_types[k] = change_types.get(k, 0) + 1

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

    # ─── MQ (R110-161, R110-166 phase 2.3) ───
    # Reads dev_message_queue stats and surfaces them as `mq.*` keys.
    # Graceful: returns an empty stub if MQ module is unavailable or
    # the .mase/mq/ directory doesn't exist yet (first run).
    mq_block = {
        "available": _MQ_AVAILABLE,
        "generated_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "depth_total": 0,
        "lag_p95_ms": 0,
        "dlq_count": 0,
        "retry_rate": 0.0,
        "completed_total": 0,
        "topic_count": 0,
        "by_topic": {},
        # R110-166 phase 2.3: per-phase-1-topic summary so the dashboard
        # surfaces what the publishers in phase 1 actually emitted and
        # what the consumers in phase 2.1/2.2 actually processed.
        "phase1_topics": {},
    }
    if _MQ_AVAILABLE:
        try:
            mq_stats = mq.stats()  # see dev_message_queue.stats()
            topics = mq_stats.get('topics', {})
            mq_block['by_topic'] = topics
            mq_block['topic_count'] = len(topics)
            mq_block['depth_total'] = sum(
                t.get('depth', 0) for t in topics.values())
            mq_block['completed_total'] = sum(
                t.get('completed_total', 0) for t in topics.values())
            mq_block['dlq_count'] = sum(
                t.get('dlq_count_for_topic', 0) for t in topics.values())
            # R110-188: mq.stats() renamed lag_p95_ms→current_p95_lag_ms
            # and dlq_count→dlq_count_for_topic.  The dashboard keeps its
            # own output contract (lag_p95_ms/dlq_count keys); mirror the
            # new keys back so by_topic consumers keep working.
            for _t in topics.values():
                _t.setdefault("lag_p95_ms", _t.get("current_p95_lag_ms", 0))
                _t.setdefault("dlq_count", _t.get("dlq_count_for_topic", 0))
            # Worst-case lag across topics
            lags = [t.get('current_p95_lag_ms', 0) for t in topics.values()
                    if t.get('current_p95_lag_ms', 0) > 0]
            mq_block['lag_p95_ms'] = max(lags) if lags else 0
            # Average retry rate across topics
            rates = [t.get('retry_rate', 0.0) for t in topics.values()]
            mq_block['retry_rate'] = (
                round(sum(rates) / len(rates), 4) if rates else 0.0)
            # Phase-1 topics summary (R110-166 phase 2.3)
            mq_block['phase1_topics'] = _phase1_topics_summary(topics)
        except Exception:
            # MQ is best-effort; never let a broken queue break the
            # dashboard refresh.
            pass

    # ─── RESULT ───
    return {
        "version": "1.1.0",
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
            "by_type": change_types,
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
        "mq": mq_block,
    }


def send_dashboard_notification(data: dict = None, workspace: str = None):
    """Send MCP notification for realtime dashboard updates

    This notifies the Goose UI dashboard to refresh its display.
    Call this after writing new data.json.
    """
    import time
    ws = workspace or os.environ.get('MAS_WORKSPACE', '.')
    if ws == '.':
        # Try to find correct workspace by walking up the directory tree
        # looking for a .mas directory (a MAS-Engineer workspace marker)
        current = os.path.abspath('.')
        while current != os.path.dirname(current):
            if os.path.isdir(os.path.join(current, '.mase')):
                ws = current
                break
            current = os.path.dirname(current)
        else:
            # Fallback: try common workspace locations
            for candidate in [os.path.expanduser('~/mas-engineer'),
                              os.path.expanduser('~/mas')]:
                if os.path.isdir(candidate):
                    ws = candidate
                    break
    flag_dir = os.path.join(ws, '.mase', 'dashboards')
    os.makedirs(flag_dir, exist_ok=True)
    flag_file = os.path.join(flag_dir, '.updated')
    with open(flag_file, 'w') as f:
        f.write(str(int(time.time())))
    return True


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
    dash_dir = os.path.join(ws_abs, '.mase', 'dashboards')
    os.makedirs(dash_dir, exist_ok=True)

    data_path = os.path.join(dash_dir, 'data.json')
    with open(data_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    history_path = os.path.join(dash_dir, 'history.json')
    with open(history_path, 'w') as f:
        json.dump({"health_trend": data['health_trend'],
                   "build_size": data.get('build', {}).get('latest_size_kb', [])}, f, indent=2)

    # Send notification for realtime updates
    send_dashboard_notification(data, workspace=ws_abs)

    print(f"[OK] Dashboard Data written: {data_path}")
    print(f"   Agents: {data['agents']['total']} | Changes: {data['changes']['total']} | "
          f"SI-Runs: {data['improvement']['total_runs']} | Dispatch: {data['dispatch']['total']}")
    print(f"   Realtime: Notification sent to dashboard")

if __name__ == '__main__':
    main()
