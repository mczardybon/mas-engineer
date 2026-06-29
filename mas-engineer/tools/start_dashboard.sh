# ⛔⛔⛔ DEPRECATED v1.0.0 — Replaces durch dev_dashboard_refresh.py (On-Demand)
#!/am/bash
# start_dashboard.sh — Startet den Dashboard-Polling-Daemon
# Nutzung:
#   bash tools/start_dashboard.sh              → Start (if not runs)
#   bash tools/start_dashboard.sh --daemon     → Silent-Start for Autostart
#   bash tools/start_dashboard.sh stop         → Stopp
#   bash tools/start_dashboard.sh status       → Status check

PID_FILE="/tmp/mas-dashboard-poller.pid"
STATUS_FILE="/tmp/mas-dashboard-status.json"
WORKSPACE="."
TOOLS="$WORKSPACE/mas-engineer/tools"

stop_poller() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 $pid 2>/dev/null; then
            kill $pid 2>/dev/null
            echo "✅ Poller gestoppt (PID: $pid)"
        else
            echo "⚠️ Poller not active (stale PID)"
        fi
        rm -f "$PID_FILE"
    else
        echo "⚠️ No Poller active"
    fi
}

status_poller() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 $pid 2>/dev/null; then
            echo "🟢 Runs (PID: $pid)"
            if [ -f "$STATUS_FILE" ]; then
                calls=$(python3 -c "import json; d=json.load(open('$STATUS_FILE')); print(d['dispatch']['total_calls'])" 2>/dev/null || echo "?")
                echo "   Dispatch-Calls: $calls"
            fi
            return 0
        else
            echo "🔴 Gestorben (stale PID: $pid)"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo "⚫ Nicht started"
        return 1
    fi
}

start_poller() {
    # Check ob already runs
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 $pid 2>/dev/null; then
            [ "$1" != "--daemon" ] && echo "🟢 Poller runs already (PID: $pid)"
            return 0
        fi
        rm -f "$PID_FILE"
    fi

    # Starte Poller im Hintergrund
    nohup bash -c '
        cd '"$WORKSPACE"'
        while true; do
            # Status generate (all 5 seconds)
            if [ -f "'"$TOOLS/start_dashboard.sh"'" ]; then
                python3 "'"$TOOLS/dev_app_builder.py"'" 2>/dev/null || true
            fi
            sleep 5
        done
    ' > /tmp/mas-dashboard-poller.log 2>&1 &

    local pid=$!
    echo $pid > "$PID_FILE"
    
    if [ "$1" != "--daemon" ]; then
        echo "✅ Poller started (PID: $pid)"
    fi
    return 0
}

case "${1:-}" in
    stop)
        stop_poller
        ;;
    status)
        status_poller
        ;;
    --daemon)
        start_poller --daemon
        ;;
    *)
        start_poller
        ;;
esac
