#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# scheduler.sh — Cron-triggered data refresh for MAS-Engineer
# Runs every 5 minutes via crontab (set up by dev_install.sh)
# Refreshes dashboard data, audit log, and live daemon cache.
# ═══════════════════════════════════════════════════════════════
set -e

# Find workspace from script location
MAS_WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"

echo "⏰ [$(date -u +%Y-%m-%dT%H:%M:%SZ)] scheduler: refreshing data"

cd "$MAS_WORKSPACE" || { echo "❌ cannot cd to $MAS_WORKSPACE"; exit 1; }

# 1. Refresh dashboard data
if [ -f "tools/dev_dashboard_data.py" ]; then
    python3 tools/dev_dashboard_data.py --workspace "$MAS_WORKSPACE" 2>/dev/null && \
        echo "   ✅ dashboard data refreshed" || echo "   ⚠️  dashboard data refresh failed"
fi

# 2. Update dispatch tracker
if [ -f "tools/dev_dispatch_tracker.py" ]; then
    python3 tools/dev_dispatch_tracker.py --json 2>/dev/null > /dev/null && \
        echo "   ✅ dispatch tracker updated" || echo "   ⚠️  dispatch tracker update failed"
fi

# 3. Refresh dashboard cache via live daemon (one-shot)
if [ -f "tools/dev_dispatch_live.py" ]; then
    python3 tools/dev_dispatch_live.py --once --workspace "$MAS_WORKSPACE" 2>/dev/null && \
        echo "   ✅ live daemon cache refreshed" || echo "   ⚠️  live daemon cache refresh failed"
fi

# 4. Check daemon health, restart if dead
DAEMON_PID_FILE="$MAS_WORKSPACE/.mas/live-daemon.pid"
if [ -f "$DAEMON_PID_FILE" ]; then
    PID=$(cat "$DAEMON_PID_FILE")
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "   ⚠️  daemon dead (PID $PID), restarting"
        rm -f "$DAEMON_PID_FILE"
        cd "$MAS_WORKSPACE"
        nohup python3 tools/dev_dispatch_live.py --daemon --workspace "$MAS_WORKSPACE" \
            > "$MAS_WORKSPACE/.mas/live-daemon.log" 2>&1 &
        echo $! > "$DAEMON_PID_FILE"
    fi
fi

echo "⏰ scheduler: done"
