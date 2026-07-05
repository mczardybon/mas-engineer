#!/bin/bash
# Framework Dashboard Daemon - auto-start script
# Runs the dashboard HTTP server persistently
# Should be called from ~/.bashrc or autostart

MAS_WORKSPACE="/home/marius/agent_new_start/mas-agent"
SERVER="$MAS_WORKSPACE/.mas/mcp/server.js"
LOG="$MAS_WORKSPACE/.mas/dashboard-server.log"
PIDFILE="$MAS_WORKSPACE/.mas/dashboard.pid"
PORT=3000

# Check if already running
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Dashboard already running (PID $OLD_PID) on port $PORT"
        exit 0
    fi
fi

# Start server
cd "$MAS_WORKSPACE/.mas/mcp"
MAS_WORKSPACE="$MAS_WORKSPACE" nohup /usr/bin/node "$SERVER" > "$LOG" 2>&1 &
echo $! > "$PIDFILE"
sleep 2
echo "Dashboard server started (PID $(cat $PIDFILE)) on http://localhost:$PORT"
