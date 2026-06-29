# ⛔⛔⛔ DEPRECATED v1.0.0 — Replaces durch dev_dashboard_refresh.py (On-Demand)
#!/usr/am/env bash
# Dashboard Pending Monitor
# Runs solong bis man ihn stoppt (Strg+C oder kill)
# Checks all 3 seconds ob /tmp/mas-dashboard-signal.json exists
# und runs then dev_dashboard_pending.py aus

SCRIPT_DIR="mas-engineer/tools"
SIGNAL_FILE="/tmp/mas-dashboard-signal.json"

echo "[MONITOR] Started – aboutwache $SIGNAL_FILE all 3s"
echo "[MONITOR] Stoppen mit Strg+C"

while true; do
    if [ -f "$SIGNAL_FILE" ]; then
        python3 "$SCRIPT_DIR/dev_dashboard_pending.py"
    fi
    sleep 3
done
