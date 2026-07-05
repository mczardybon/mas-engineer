#!/bin/bash
# MAS Autostart — wird von ~/.bashrc oder systemd getriggert
# Startet: Dashboard-Server + Dispatch-Tracker

MAS_WORKSPACE="/home/marius/agent_new_start/mas-agent"
TOOLS="$MAS_WORKSPACE/tools"
DASHBOARD_LOG="$MAS_WORKSPACE/.mas/dashboard-server.log"
DISPATCH_LOG="$MAS_WORKSPACE/.state/dispatch/dispatch.ndjson"

cd "$MAS_WORKSPACE"

# 1. Dashboard-Server starten (falls nicht schon aktiv)
if ! curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "[$(date)] Starte Dashboard-Server..."
    cd "$MAS_WORKSPACE/.mas/mcp"
    MAS_WORKSPACE="$MAS_WORKSPACE" nohup /usr/bin/node server.js > "$DASHBOARD_LOG" 2>&1 &
    echo $! > "$MAS_WORKSPACE/.mas/dashboard.pid"
    echo "[$(date)] Dashboard-Server gestartet (PID $(cat $MAS_WORKSPACE/.mas/dashboard.pid))"
    sleep 2
fi

# 2. Dashboard-Daten initial refreshen
echo "[$(date)] Refreshe Dashboard-Daten..."
cd "$MAS_WORKSPACE"
python3 "$TOOLS/dev_dashboard_data.py" --workspace "$MAS_WORKSPACE" >> "$DASHBOARD_LOG" 2>&1

echo "[$(date)] MAS Autostart abgeschlossen."
