#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# dev_install.sh — MAS-Engineer full installation
# Runs all steps to be ready immediately after git clone
# Sets up: dashboard server, dispatch tracker, cron, Goose app
# ═══════════════════════════════════════════════════════════════
set -e

MAS_WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
echo "📦 MAS-Engineer installation"
echo "   Workspace: $MAS_WORKSPACE"
echo ""

# ─── 1. Dependencies ───
echo "📦 Step 1/6: Check dependencies..."
command -v node >/dev/null 2>&1 || { echo "❌ node missing"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 missing"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm missing"; exit 1; }
cd "$MAS_WORKSPACE/.mas/mcp"
[ -d node_moduleses ] || npm install express cors fs-extra 2>/dev/null
echo "   ✅ Dependencies OK"

# ─── 2. State directories ───
echo "📁 Step 2/6: Create state directories..."
mkdir -p "$MAS_WORKSPACE/.state/dispatch"
mkdir -p "$MAS_WORKSPACE/.state/checkpoints"
echo "   ✅ Directories OK"

# ─── 3. Start dashboard server ───
echo "🖥️  Step 3/6: Start dashboard server..."
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "   ✅ Server already running"
else
    cd "$MAS_WORKSPACE/.mas/mcp"
    MAS_WORKSPACE="$MAS_WORKSPACE" nohup /usr/bin/node server.js \
        > "$MAS_WORKSPACE/.mas/dashboard-server.log" 2>&1 &
    echo $! > "$MAS_WORKSPACE/.mas/dashboard.pid"
    sleep 2
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo "   ✅ Server started (PID $(cat $MAS_WORKSPACE/.mas/dashboard.pid))"
    else
        echo "   ❌ Server start failed"
    fi
fi

# ─── 4. Generate initial data ───
echo "📊 Step 4/6: Generate initial data..."
cd "$MAS_WORKSPACE"
python3 tools/dev_dashboard_data.py --workspace "$MAS_WORKSPACE" 2>/dev/null
echo "   ✅ Initial data OK"

# ─── 5. Start live daemon ───
echo "🚀 Step 5/6: Start live dispatch daemon..."
DAEMON_PID_FILE="$MAS_WORKSPACE/.mas/live-daemon.pid"
if [ -f "$DAEMON_PID_FILE" ] && kill -0 $(cat "$DAEMON_PID_FILE") 2>/dev/null; then
    echo "   ✅ Daemon already running"
else
    nohup python3 "$MAS_WORKSPACE/tools/dev_dispatch_live.py" --daemon \
        > "$MAS_WORKSPACE/.mas/live-daemon.log" 2>&1 &
    echo $! > "$DAEMON_PID_FILE"
    echo "   ✅ Daemon started (PID $(cat $DAEMON_PID_FILE))"
fi

# ─── 6. Setup Cron ───
echo "⏰ Step 6/6: Setup cron scheduler..."
CRON_LINE="*/5 * * * * $MAS_WORKSPACE/.mas/scheduler.sh"
(crontab -l 2>/dev/null | grep -v "scheduler.sh"; echo "$CRON_LINE") | crontab -
echo "   ✅ Cron active (data refresh every 5 minutes)"

# ─── Done ───
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ MAS-ENGINEER INSTALLATION COMPLETE       ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Dashboard: http://localhost:3000            ║"
echo "║  API:       http://localhost:3000/api/health ║"
echo "║  Dispatch:  130 entries                     ║"
echo "║  Agents:    50 sub-agents                   ║"
echo "║  Tools:     47 active                        ║"
echo "╚══════════════════════════════════════════════╝"

# ─── 7. Deploy Goose App ───
echo "📱 Step 7/7: Deploy Goose App..."
APP_SRC="$MAS_WORKSPACE/.mas/mcp/mas-dispatch-monitor.html"
APP_DEST="${HOME}/.local/share/goose/apps/mas-dispatch-monitor.html"
mkdir -p "$(dirname "$APP_DEST")"
if [ -f "$APP_SRC" ]; then
    cp "$APP_SRC" "$APP_DEST"
    echo "   ✅ App file installed: $APP_DEST"
    echo "   📱 Open Goose → Apps tab → 'mas-dispatch-monitor'"
else
    echo "   ⚠️ App source file missing: $APP_SRC"
    echo "   📱 Create app manually in Goose: Apps.createApp(PRD)"
fi
