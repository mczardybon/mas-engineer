#!/usr/bin/env python3
"""dev_dispatch_tracker.py — Dispatch Tree Tracker v2.0.0 (R110-154)
====================================================================

Tracks every delegate() call and builds a dispatch tree.

v2.0.0 changes (R110-156 — migration to dev_message_queue):
  - add() now ALSO enqueues a `dispatch_start` event on the
    `dispatches` topic (at-least-once delivery, retry-able,
    dedup-able via idempotency_key=dispatch_id).
  - done() now ALSO enqueues a `dispatch_done` event on the
    `dispatches` topic. The legacy NDJSON file at /tmp/mas-dispatch.ndjson
    is STILL written (dual-write) for backward compatibility with:
      - dev_dashboard_data.py (reads via subprocess --json)
      - dev_app_builder.py (reads via subprocess --json)
      - any external tool that scrapes /tmp/mas-dispatch.ndjson
  - get_tree() reads from the legacy NDJSON file (full historical view
    of dispatches, including in-flight ones). The MQ-side is treated as
    a parallel event stream that can be consumed by dashboards or
    audit-log workflows (topic `dispatches`, search payload keys:
    event_type=dispatch_start|dispatch_done, dispatch_id, from, to,
    task, mode, duration_ms, result_summary, errors).

Call (unchanged):
  python3 dev_dispatch_tracker.py --add <to> <task> <mode> [parent_id]
      → logs a new dispatch, returns ID
  python3 dev_dispatch_tracker.py --done <id> <duration_sec> <turns> <summary>
      → closes a dispatch
  python3 dev_dispatch_tracker.py --log '<json>'
      → direct JSON-logging
  python3 dev_dispatch_tracker.py --json [--mode mas|framework]
      → dispatch tree as JSON
  python3 dev_dispatch_tracker.py --tree [--mode mas|framework]
      → ASCII-tree in console
  python3 dev_dispatch_tracker.py --stats
      → aggregate stats
  python3 dev_dispatch_tracker.py --mq-stats
      → MQ-side aggregate (depth, lag, dlq for `dispatches` topic)
  python3 dev_dispatch_tracker.py --clear
      → clear legacy log
"""
import datetime
import json
import os
import subprocess
import sys
import tempfile

LEGACY_LOG = os.environ.get(
    "MAS_DISPATCH_LOG",
    os.path.join(tempfile.gettempdir(), "mas-dispatch.ndjson"),
)
MQ_TOPIC = "dispatches"


# ─── MQ adapter (lazy import to keep this file usable if MQ is
#     unavailable — falls back to no-op enqueue) ─────────────────

def _mq():
    """Import dev_message_queue, return None if not available."""
    try:
        tools_dir = os.path.dirname(os.path.abspath(__file__))
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import dev_message_queue  # type: ignore
        return dev_message_queue
    except Exception:
        return None


# ─── Legacy NDJSON I/O (unchanged shape) ─────────────────────────

def _read_all():
    if not os.path.exists(LEGACY_LOG):
        return []
    entries = []
    with open(LEGACY_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries


def _write_all(entries):
    os.makedirs(os.path.dirname(LEGACY_LOG), exist_ok=True)
    with open(LEGACY_LOG, 'w') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')


# ─── Public API ─────────────────────────────────────────────────

def add(ts, entry_id, parent_id, from_agent, to_agent, task,
        mode="mas", workspace=None):
    """Add a new dispatch. Dual-writes to legacy NDJSON + MQ topic."""
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
    # Legacy write (backward compat)
    os.makedirs(os.path.dirname(LEGACY_LOG), exist_ok=True)
    with open(LEGACY_LOG, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    # MQ enqueue (best-effort, no fail if MQ unavailable)
    mq = _mq()
    if mq is not None:
        try:
            mq.enqueue(
                MQ_TOPIC,
                {
                    "event_type": "dispatch_start",
                    **entry,
                },
                idempotency_key=f"dispatch_start-{entry_id}",
                retry_policy={"max": 3, "backoff": [1, 2, 4]},
                request_id=entry_id,
            )
        except Exception:
            pass  # MQ is best-effort
    return entry


def done(entry_id, duration_ms, turns, result_summary, errors=None):
    """Mark a dispatch as done. Updates legacy NDJSON + enqueues
    MQ dispatch_done event."""
    entries = _read_all()
    updated = None
    for e in entries:
        if e["id"] == entry_id:
            e["status"] = "done" if not errors else "error"
            e["duration_ms"] = duration_ms
            e["turns"] = turns
            e["result_summary"] = result_summary
            e["errors"] = errors
            updated = dict(e)
            break
    _write_all(entries)
    # MQ dispatch_done event
    if updated is not None:
        mq = _mq()
        if mq is not None:
            try:
                mq.enqueue(
                    MQ_TOPIC,
                    {
                        "event_type": "dispatch_done",
                        "id": updated["id"],
                        "from": updated.get("from"),
                        "to": updated.get("to"),
                        "task": updated.get("task"),
                        "mode": updated.get("mode"),
                        "parent_id": updated.get("parent_id"),
                        "duration_ms": updated.get("duration_ms"),
                        "turns": updated.get("turns"),
                        "result_summary": updated.get("result_summary"),
                        "errors": updated.get("errors"),
                        "status": updated.get("status"),
                    },
                    idempotency_key=f"dispatch_done-{entry_id}",
                    retry_policy={"max": 3, "backoff": [1, 2, 4]},
                    request_id=entry_id,
                )
            except Exception:
                pass
    return entries


def get_tree(mode=None, last_n=50):
    """Return the dispatch tree (from legacy NDJSON)."""
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
        dur = (f"{e['duration_ms']/1000:.1f}s"
               if e.get("duration_ms") is not None else "...")
        t = f"{e.get('turns', 0)}t"
        summary = (f" — {e['result_summary'][:60]}"
                   if e.get("result_summary") else "")
        err = f" ⚠️ {e['errors']}" if e.get("errors") else ""
        lines = [f"{indent}{icon} {micon} `{e['to']}` {e['task']} "
                 f"({dur}, {t}){err}{summary}"]
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


def mq_stats():
    """MQ-side aggregate for the `dispatches` topic.  Returns:
        {"depth": N, "lag_p95_ms": N, "dlq_count": N, "retry_rate": 0.0,
         "completed_total": N}
    R110-188: sources from the renamed MQ stats keys
    (current_p95_lag_ms / dlq_count_for_topic); output keys kept for
    backward compatibility.  Returns None if MQ is unavailable."""
    mq = _mq()
    if mq is None:
        return None
    try:
        all_stats = mq.stats()
        topic_stats = all_stats.get("topics", {}).get(MQ_TOPIC, {})
        return {
            "depth": topic_stats.get("depth", 0),
            "lag_p95_ms": topic_stats.get("current_p95_lag_ms", 0),
            "dlq_count": topic_stats.get("dlq_count_for_topic", 0),
            "retry_rate": topic_stats.get("retry_rate", 0.0),
            "completed_total": topic_stats.get("completed_total", 0),
        }
    except Exception as e:
        return {"error": str(e)}


def clear():
    if os.path.exists(LEGACY_LOG):
        os.remove(LEGACY_LOG)
    return {"status": "cleared"}


# ─── CLI (unchanged + 1 new flag: --mq-stats) ───────────────────

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
        result.pop("entries", None)  # Only Tree + Stats
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif '--tree' in sys.argv:
        mode = None
        if '--mode' in sys.argv:
            mi = sys.argv.index('--mode') + 1
            mode = sys.argv[mi]
        result = get_tree(mode)
        print(f"Dispatch Tree ({result['total']} entries, "
              f"{result['running']} running, {result['done']} done, "
              f"{result['errors']} errors)")
        for line in result['tree']:
            print(line)

    elif '--stats' in sys.argv:
        entries = _read_all()
        total = len(entries)
        running = sum(1 for e in entries if e.get('status') == 'running')
        completed = sum(1 for e in entries if e.get('status') == 'done')
        failed = sum(1 for e in entries
                     if e.get('status') == 'error' or e.get('errors'))
        durations = [e.get('duration_ms', 0) for e in entries
                     if e.get('duration_ms')
                     and e['duration_ms'] is not None]
        avg_dur = (round(sum(durations) / len(durations))
                   if durations else 0)
        result = {
            'total': total, 'running': running, 'completed': completed,
            'failed': failed, 'avg_duration_ms': avg_dur,
        }
        # R110-270: ensure_ascii=False (data may contain non-ASCII task names);
        # indent=2 not needed for print-to-stdout, kept compact.
        print(json.dumps(result, ensure_ascii=False))

    elif '--mq-stats' in sys.argv:
        # NEW (R110-156): MQ-side aggregate for the `dispatches` topic.
        result = mq_stats()
        if result is None:
            # R110-270: ensure_ascii=False for unicode-safe error message
            print(json.dumps({"error": "dev_message_queue unavailable"},
                             ensure_ascii=False))
        else:
            # R110-270: ensure_ascii=False added
            print(json.dumps(result, indent=2, ensure_ascii=False))

    elif '--clear' in sys.argv:
        clear()
        print("dispatch log cleared")

    else:
        result = get_tree(last_n=20)
        print(f"Dispatch Tree ({result['total']} entries, "
              f"{result['running']} running, {result['done']} done, "
              f"{result['errors']} errors)")
        for line in result['tree'][:30]:
            print(line)
