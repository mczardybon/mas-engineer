#!/usr/bin/env python3
"""
dev_dispatch_tracer.py — Dispatch-Tracing for MAS
=================================================
Schreibt jeden delegate()-call in /tmp/mas-dispatch.ndjson.
Das Dashboard reads these file und zeigt den Dispatch-Tree.

Usage:
  python3 dev_dispatch_tracer.py log "mas-engineer" "sub_mas-scanner" "SCAN" "sync"
  python3 dev_dispatch_tracer.py status
  python3 dev_dispatch_tracer.py tree  --last 20
"""
import json, os, sys, time, tempfile
from datetime import datetime, timezone

DISPATCH_LOG = os.path.join(tempfile.gettempdir(), "mas-dispatch.ndjson")
STATUS_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-status.json")

def get_next_id():
    """Next ID aus bestehenden entries"""
    entries = []
    if os.path.exists(DISPATCH_LOG):
        with open(DISPATCH_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
    # ID = Date + laufende Number
    date = datetime.now().strftime("%Y%m%d")
    existing = [e.get("id", "") for e in entries if e.get("id", "").startswith(date)]
    nums = []
    for eid in existing:
        try:
            nums.append(int(eid.split("_")[-1]))
        except:
            nums.append(0)
    next_num = max(nums) + 1 if nums else 1
    return f"{date}_{next_num:04d}"

def log_dispatch(from_agent, to_agent, task, mode="sync", parent_id=None):
    """Einen Dispatch-entry loggen"""
    entry = {
        "id": get_next_id(),
        "parent_id": parent_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "from": from_agent,
        "to": to_agent,
        "task": task,
        "mode": mode,
        "status": "active",
        "duration_ms": 0
    }
    with open(DISPATCH_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"✅ Dispatch: {from_agent} → {to_agent} ({task})")
    return entry["id"]

def complete_dispatch(entry_id, duration_ms, status="completed"):
    """Einen Dispatch als completed markieren"""
    entries = []
    if os.path.exists(DISPATCH_LOG):
        with open(DISPATCH_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        e = json.loads(line)
                        if e.get("id") == entry_id:
                            e["status"] = status
                            e["duration_ms"] = duration_ms
                        entries.append(e)
                    except:
                        pass
    with open(DISPATCH_LOG, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    print(f"✅ Dispatch {entry_id}: {status} ({duration_ms}ms)")

def show_status():
    """Dispatch-Status anshow"""
    entries = []
    if os.path.exists(DISPATCH_LOG):
        with open(DISPATCH_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
    
    total = len(entries)
    active = sum(1 for e in entries if e.get("status") == "active")
    completed = sum(1 for e in entries if e.get("status") == "completed")
    failed = sum(1 for e in entries if e.get("status") == "failed")
    durations = [e.get("duration_ms", 0) for e in entries if e.get("duration_ms", 0) > 0]
    avg_dur = round(sum(durations)/len(durations)) if durations else 0
    
    print(f"=== DISPATCH-STATUS ===")
    print(f"Total:  {total}")
    print(f"Active: {active}")
    print(f"Done:   {completed}")
    print(f"Failed: {failed}")
    print(f"Avg:    {avg_dur}ms")
    
    # Letzte 5
    print(f"\nLetzte 5:")
    for e in entries[-5:]:
        status_icon = {"active": "🟡", "completed": "🟢", "failed": "🔴"}.get(e.get("status", ""), "⚪")
        print(f"  {status_icon} {e.get('from','?')} → {e.get('to','?')} ({e.get('task','?')}) [{e.get('duration_ms',0)}ms]")

def build_tree(last_n=20):
    """Dispatch-Tree for Dashboard bauen (letzte N entries)"""
    entries = []
    if os.path.exists(DISPATCH_LOG):
        with open(DISPATCH_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
    
    recent = entries[-last_n:] if len(entries) > last_n else entries
    
    # treestruktur: Eltern-ID → Children
    tree = []
    child_map = {}
    for e in recent:
        parent = e.get("parent_id")
        if parent:
            child_map.setdefault(parent, []).append(e)
        else:
            tree.append(e)
    
    # Attach children to parents
    def attach_children(node):
        node["children"] = []
        for child in child_map.get(node["id"], []):
            node["children"].append(child)
            attach_children(child)
    
    for root in tree:
        attach_children(root)
    
    return tree

def update_dashboard():
    """Dashboard-Status-JSON mit Dispatch-Data update"""
    entries = []
    if os.path.exists(DISPATCH_LOG):
        with open(DISPATCH_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
    
    total = len(entries)
    active = sum(1 for e in entries if e.get("status") == "active")
    completed = sum(1 for e in entries if e.get("status") == "completed")
    failed = sum(1 for e in entries if e.get("status") == "failed")
    durations = [e.get("duration_ms", 0) for e in entries if e.get("duration_ms", 0) > 0]
    avg_dur = round(sum(durations)/len(durations)) if durations else 0
    
    # In Dashboard-JSON einread, update, backwrite
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE) as f:
            dashboard = json.load(f)
        
        dashboard["dispatch"] = {
            "total_calls": total,
            "active": active,
            "completed": completed,
            "failed": failed,
            "avg_duration_ms": avg_dur,
            "tree": build_tree(20)
        }
        
        # History fortwrite
        now = datetime.now().strftime("%H:%M")
        dashboard["history"]["dispatch_volume"].append({"time": now, "count": total})
        if len(dashboard["history"]["dispatch_volume"]) > 24:
            dashboard["history"]["dispatch_volume"] = dashboard["history"]["dispatch_volume"][-24:]
        dashboard["history"]["health_trend"].append({
            "time": now,
            "mas": 100 if dashboard["mas"]["status"] == "operational" else 50,
            "framework": 100 if dashboard["framework"]["status"] == "operational" else 50
        })
        if len(dashboard["history"]["health_trend"]) > 24:
            dashboard["history"]["health_trend"] = dashboard["history"]["health_trend"][-24:]
        
        with open(STATUS_FILE, "w") as f:
            json.dump(dashboard, f, indent=2)
        print(f"✅ Dashboard updated: {total} Calls, {active} active")
    else:
        print("⚠️ No Dashboard-JSON found")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dev_dispatch_tracer.py log|complete|status|tree|update [args]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "log" and len(sys.argv) >= 5:
        log_dispatch(sys.argv[2], sys.argv[3], sys.argv[4], 
                     sys.argv[5] if len(sys.argv) > 5 else "sync",
                     sys.argv[6] if len(sys.argv) > 6 else None)
    elif cmd == "complete" and len(sys.argv) >= 4:
        complete_dispatch(sys.argv[2], int(sys.argv[3]), 
                         sys.argv[4] if len(sys.argv) > 4 else "completed")
    elif cmd == "status":
        show_status()
    elif cmd == "tree":
        last = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        tree = build_tree(last)
        print(json.dumps(tree, indent=2))
    elif cmd == "update":
        update_dashboard()
    else:
        print(f"Unbekannter Command: {cmd}")
        print("Available: log, complete, status, tree, update")
