#!/usr/am/env python3
"""dev_dispatch_tracker.py — Dispatch Tree Tracker v1.0.0
========================================================
Trackt jeden delegate()-Aufruf und baut a Dispatch-Tree.

Aufruf:
  python3 dev_dispatch_tracker.py --add <to> <task> <mode> [parent_id]
      → logged a neuen Dispatch, givet ID back
  python3 dev_dispatch_tracker.py --done <id> <duration_sec> <turns> <summary>
      → schliesst a Dispatch ab
  python3 dev_dispatch_tracker.py --log '<json>'
      → direktes JSON-logging (for sub-agenten)
  python3 dev_dispatch_tracker.py --json [--mode mas|framework]
      → Dispatch-Tree als JSON (for dev_app_builder)
  python3 dev_dispatch_tracker.py --tree [--mode mas|framework]
      → ASCII-Tree in Konsole
  python3 dev_dispatch_tracker.py --clear
      → Log empty
"""
import json, os, sys, datetime, tempfile

LOG_FILE = os.path.join(tempfile.gettempdir(), "mas-dispatch.ndjson")


def _read_all():
    if not os.path.exists(LOG_FILE):
        return []
    entries = []
    with open(LOG_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    return entries


def _write_all(entries):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'w') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')


def add(ts, entry_id, parent_id, from_agent, to_agent, task, mode="mas", workspace=None):
    entry = {
        "ts": ts,
        "id": entry_id,
        "parent_id": parent_id,
        "from": from_agent,
        "to": to_agent,
        "task": task,
        "mode": mode,
        "status": "running",
        "duration_ms": None,
        "turns": 0,
        "result_summary": None,
        "errors": None,
        "workspace": workspace or os.getcwd()
    }
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry


def done(entry_id, duration_ms, turns, result_summary, errors=None):
    entries = _read_all()
    for e in entries:
        if e["id"] == entry_id:
            e["status"] = "done" if not errors else "error"
            e["duration_ms"] = duration_ms
            e["turns"] = turns
            e["result_summary"] = result_summary
            e["errors"] = errors
    _write_all(entries)
    return entries


def get_tree(mode=None, last_n=50):
    entries = _read_all()
    if mode:
        entries = [e for e in entries if e.get("mode") == mode]
    entries = entries[-last_n:]

    roots = [e for e in entries if not e.get("parent_id")]
    children = {}
    for e in entries:
        pid = e.get("parent_id")
        if pid:
            children.setdefault(pid, []).append(e)

    def _build_lines(e, depth=0):
        indent = "  " * depth
        s = e["status"]
        icon = {"done": "✅", "running": "⏳", "error": "❌"}.get(s, "⏹️")
        micon = "🎩" if e.get("mode") == "mas" else "🏗️"
        dur = f"{e['duration_ms']/1000:.1f}s" if e.get("duration_ms") is not None else "..."
        t = f"{e.get('turns', 0)}t"
        summary = f" — {e['result_summary'][:60]}" if e.get("result_summary") else ""
        err = f" ⚠️ {e['errors']}" if e.get("errors") else ""
        lines = [f"{indent}{icon} {micon} `{e['to']}` {e['task']} ({dur}, {t}){err}{summary}"]
        for child in children.get(e["id"], []):
            lines.extend(_build_lines(child, depth + 1))
        return lines

    tree = []
    for r in roots:
        tree.extend(_build_lines(r))

    return {
        "total": len(entries),
        "running": sum(1 for e in entries if e["status"] == "running"),
        "done": sum(1 for e in entries if e["status"] == "done"),
        "errors": sum(1 for e in entries if e.get("errors")),
        "tree": tree,
        "entries": entries
    }


def clear():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    return {"status": "cleared"}


if __name__ == '__main__':
    if '--add' in sys.argv:
        idx = sys.argv.index('--add') + 1
        to_agent = sys.argv[idx]
        task = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "?"
        mode = sys.argv[idx + 2] if len(sys.argv) > idx + 2 else "mas"
        parent = sys.argv[idx + 3] if len(sys.argv) > idx + 3 else None
        eid = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:17]
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        add(now, eid, parent, "dev-mas-engineer", to_agent, task, mode)
        print(eid)

    elif '--done' in sys.argv:
        idx = sys.argv.index('--done') + 1
        eid = sys.argv[idx]
        dur = float(sys.argv[idx + 1]) * 1000 if len(sys.argv) > idx + 1 else 0
        turns = int(sys.argv[idx + 2]) if len(sys.argv) > idx + 2 else 0
        summary = sys.argv[idx + 3] if len(sys.argv) > idx + 3 else ""
        err = sys.argv[idx + 4] if len(sys.argv) > idx + 4 else None
        done(eid, int(dur), turns, summary, err)
        print(f"done: {eid}")

    elif '--log' in sys.argv:
        idx = sys.argv.index('--log') + 1
        entry = json.loads(sys.argv[idx])
        add(**entry)
        print(entry.get("id", "?"))

    elif '--json' in sys.argv:
        mode = None
        if '--mode' in sys.argv:
            mi = sys.argv.index('--mode') + 1
            mode = sys.argv[mi]
        result = get_tree(mode)
        result.pop("entries")  # Only Tree + Stats
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif '--tree' in sys.argv:
        mode = None
        if '--mode' in sys.argv:
            mi = sys.argv.index('--mode') + 1
            mode = sys.argv[mi]
        result = get_tree(mode)
        print(f"Dispatch Tree ({result['total']} entries, {result['running']} running, {result['done']} done, {result['errors']} errors)")
        for line in result['tree']:
            print(line)

    elif '--stats' in sys.argv:
        entries = _read_all()
        total = len(entries)
        running = sum(1 for e in entries if e.get('status') == 'running')
        completed = sum(1 for e in entries if e.get('status') == 'done')
        failed = sum(1 for e in entries if e.get('status') == 'error' or e.get('errors'))
        durations = [e.get('duration_ms', 0) for e in entries if e.get('duration_ms') and e['duration_ms'] is not None]
        avg_dur = round(sum(durations)/len(durations)) if durations else 0
        result = {'total': total, 'running': running, 'completed': completed, 'failed': failed, 'avg_duration_ms': avg_dur}
        print(json.dumps(result))

    elif '--clear' in sys.argv:
        clear()
        print("dispatch log cleared")

    else:
        result = get_tree(last_n=20)
        print(f"Dispatch Tree ({result['total']} entries, {result['running']} running, {result['done']} done, {result['errors']} errors)")
        for line in result['tree'][:30]:
            print(line)
