# ⛔⛔⛔ DEPRECATED v1.0.0 — Replaces durch dev_dashboard_refresh.py (On-Demand)
#!/usr/am/env python3
"""dev_dashboard_pending.py — Schreibt pending.json bei Signal-Change
====================================================================
Will from Sub-Agent sub_mas-dashboard-live aufgerufen.
Liest Signal + Status, vergleicht Timestamp, schreibt kompaktes
Info-Objekt (max 500 Bytes) after /tmp/mas-dashboard-pending.json.
"""
import json, os, sys, tempfile

SIGNAL_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-signal.json")
STATUS_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-status.json")
STATE_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-state.ini")
PENDING_FILE = os.path.join(tempfile.gettempdir(), "mas-dashboard-pending.json")

def main():
    if not os.path.exists(SIGNAL_FILE):
        return
    if not os.path.exists(STATUS_FILE):
        return

    sig = json.load(open(SIGNAL_FILE))
    current_ts = sig.get("ts", "")

    # Letzten Timestamp read
    previous_ts = ""
    if os.path.exists(STATE_FILE):
        for line in open(STATE_FILE):
            if line.startswith("previous="):
                previous_ts = line.strip().split("=", 1)[1]

    # Only bei Change write
    if current_ts == previous_ts:
        return

    data = json.load(open(STATUS_FILE))
    si = data.get("mas", {}).get("self_improve", {})
    build = data.get("mas", {}).get("build", {})
    dispatch = data.get("dispatch", {})
    ah = data.get("mas", {}).get("agent_health", {})

    info = {
        "ts": current_ts,
        "agents": data.get("mas", {}).get("agents", 0),
        "healthy": ah.get("healthy", 0),
        "total_agents": ah.get("total", 0),
        "si_run": si.get("total_runs", 0),
        "sessions": data.get("mas", {}).get("session_stats", {}).get("total_sessions", "?"),
        "builds": build.get("count", 0),
        "build_size": build.get("latest", {}).get("size_kb", 0),
        "dispatch_done": dispatch.get("done", 0),
        "dispatch_running": dispatch.get("running", 0),
        "dispatch_errors": dispatch.get("errors", 0),
        "changes": data.get("mas", {}).get("changes", 0),
        "fleet": data.get("mas", {}).get("fleet_active", False),
        "score": data.get("mas", {}).get("prompt_score_avg", 0),
        "ten": data.get("mas", {}).get("agents_at_10", 0)
    }

    with open(PENDING_FILE, "w") as f:
        json.dump(info, f)

    with open(STATE_FILE, "w") as f:
        f.write(f"previous={current_ts}\n")

    print(f"Pending: {len(json.dumps(info))}B | agents={info['agents']} si={info['si_run']} ts={current_ts}")

if __name__ == "__main__":
    main()
