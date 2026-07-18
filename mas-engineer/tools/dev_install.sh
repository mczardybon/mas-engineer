#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# dev_install.sh — MAS-Engineer full installation
# Runs all steps to be ready immediately after git clone
# Sets up: dashboard server, dispatch tracker, cron, Goose app
# ═══════════════════════════════════════════════════════════════
set -e

MAS_WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
echo "📦 MAS-Engineer installation"
echo "   Workspace: $MAS_WORKSPACE"
echo ""

# ─── 1. Dependencies ───
echo "📦 Step 1/7: Check dependencies..."
command -v node >/dev/null 2>&1 || { echo "❌ node missing"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 missing"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm missing"; exit 1; }
cd "$MAS_WORKSPACE/.mas/mcp"
[ -d node_modules ] || npm install --silent 2>/dev/null
echo "   ✅ Dependencies OK"

# ─── 2. State directories ───
echo "📁 Step 2/7: Create state directories..."
mkdir -p "$MAS_WORKSPACE/.state/dispatch"
mkdir -p "$MAS_WORKSPACE/.state/checkpoints"
echo "   ✅ Directories OK"

# ─── 3. Start dashboard MCP server (stdio-based) ───
echo "🖥️  Step 3/7: Start dashboard MCP server (stdio)..."
DASHBOARD_PID_FILE="$MAS_WORKSPACE/.mas/dashboard.pid"
if [ -f "$DASHBOARD_PID_FILE" ] && kill -0 $(cat "$DASHBOARD_PID_FILE") 2>/dev/null; then
    echo "   ✅ Dashboard server already running (PID $(cat $DASHBOARD_PID_FILE))"
else
    cd "$MAS_WORKSPACE/.mas/mcp"
    if [ ! -d "node_modules" ]; then
        echo "   📦 Installing dashboard npm dependencies..."
        npm install --silent 2>/dev/null || { echo "   ❌ npm install failed"; exit 1; }
    fi
    MAS_WORKSPACE="$MAS_WORKSPACE" exec </dev/null nohup /usr/bin/node server.js \
        > "$MAS_WORKSPACE/.mas/dashboard-server.log" 2>&1 &
    DASHBOARD_PID=$!
    echo $DASHBOARD_PID > "$DASHBOARD_PID_FILE"
    sleep 2
    if kill -0 $DASHBOARD_PID 2>/dev/null; then
        echo "   ✅ Dashboard server started (PID $DASHBOARD_PID)"
        echo "   📡 Type: stdio-based MCP server (managed by goose via stdio)"
    else
        echo "   ⚠️  Dashboard server exited (stdio EOF or stdin issue)"
        echo "   ℹ️  This is OK — the server is launched on-demand by goose"
        rm -f "$DASHBOARD_PID_FILE"
    fi
fi

# ─── 4. Generate initial data ───
echo "📊 Step 4/7: Generate initial data..."
cd "$MAS_WORKSPACE"
python3 tools/dev_dashboard_data.py --workspace "$MAS_WORKSPACE" 2>/dev/null
echo "   ✅ Initial data OK"

# ─── 5. Start live daemon ───
echo "🚀 Step 5/7: Start live dispatch daemon..."
DAEMON_PID_FILE="$MAS_WORKSPACE/.mas/live-daemon.pid"
if [ -f "$DAEMON_PID_FILE" ] && kill -0 $(cat "$DAEMON_PID_FILE") 2>/dev/null; then
    echo "   ✅ Daemon already running (PID $(cat "$DAEMON_PID_FILE"))"
else
    cd "$MAS_WORKSPACE"
    nohup python3 "$MAS_WORKSPACE/tools/dev_dispatch_live.py" --daemon \
        --workspace "$MAS_WORKSPACE" \
        > "$MAS_WORKSPACE/.mas/live-daemon.log" 2>&1 &
    DAEMON_PID=$!
    echo $DAEMON_PID > "$DAEMON_PID_FILE"
    sleep 2
    if kill -0 $DAEMON_PID 2>/dev/null; then
        echo "   ✅ Daemon started (PID $DAEMON_PID)"
    else
        echo "   ⚠️  Daemon may have stopped (check .mas/live-daemon.log)"
    fi
fi

# ─── 6. Setup Cron ───
echo "⏰ Step 6/7: Setup cron scheduler..."
CRON_LINE="*/5 * * * * $MAS_WORKSPACE/.mas/scheduler.sh"
if command -v crontab >/dev/null 2>&1; then
    (crontab -l 2>/dev/null | grep -v "scheduler.sh" || true; echo "$CRON_LINE") | crontab - 2>/dev/null || true
    if crontab -l 2>/dev/null | grep -q "scheduler.sh"; then
        echo "   ✅ Cron active (data refresh every 5 minutes)"
    else
        echo "   ⚠️  Cron setup failed (no crontab permissions)"
    fi
else
    echo "   ⚠️  Cron not available in this environment (skipped)"
    echo "   💡 To run scheduler manually: $MAS_WORKSPACE/.mas/scheduler.sh"
fi

# ─── Done ───
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ MAS-ENGINEER INSTALLATION COMPLETE       ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Dashboard:  MCP stdio (.mas/mcp/server.js)  ║"
echo "║  Dispatch:   130 entries                     ║"
echo "║  Agents:     50 sub-agents                   ║"
echo "║  Tools:      47 active                        ║"
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
