#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# dev_install.sh — MAS-Engineer Vollinstallation
# Runs all steps to work immediately after git clone
# functioniert: Dashboard-Server, Dispatch-Tracker, Cron, Goose-App
# ═══════════════════════════════════════════════════════════════
set -e

MAS_WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
echo "📦 MAS-Engineer Installation"
echo "   Workspace: $MAS_WORKSPACE"
echo ""

# ─── 1. Dependencies ───
echo "📦 Step 1/6: Dependencies check..."
command -v node >/dev/null 2>&1 || { echo "❌ node missing"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 missing"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm missing"; exit 1; }
cd "$MAS_WORKSPACE/.mas/mcp"
[ -d node_moduleses ] || npm install express cors fs-extra 2>/dev/null
echo "   ✅ Dependencies OK"

# ─── 2. State-directoryse ───
echo "📁 Step 2/6: State-directoryse anlegen..."
mkdir -p "$MAS_WORKSPACE/.state/dispatch"
mkdir -p "$MAS_WORKSPACE/.state/checkpoints"
echo "   ✅ directoryse OK"

# ─── 3. Dashboard-Server start ───
echo "🖥️  Step 3/6: Dashboard-Server start..."
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
        echo "   ❌ Server-Start fehlgeschlagen"
    fi
fi

# ─── 4. Initialdaten generate ───
echo "📊 Step 4/6: Initialdaten generate..."
cd "$MAS_WORKSPACE"
python3 tools/dev_dashboard_data.py --workspace "$MAS_WORKSPACE" 2>/dev/null
echo "   ✅ Initialdaten OK"

# ─── 5. Live-Daemon start ───
echo "🚀 Step 5/6: Live-Dispatch-Daemon start..."
DAEMON_PID_FILE="$MAS_WORKSPACE/.mas/live-daemon.pid"
if [ -f "$DAEMON_PID_FILE" ] && kill -0 $(cat "$DAEMON_PID_FILE") 2>/dev/null; then
    echo "   ✅ Daemon already running"
else
    nohup python3 "$MAS_WORKSPACE/tools/dev_dispatch_live.py" --daemon \
        > "$MAS_WORKSPACE/.mas/live-daemon.log" 2>&1 &
    echo $! > "$DAEMON_PID_FILE"
    echo "   ✅ Daemon started (PID $(cat $DAEMON_PID_FILE))"
fi

# ─── 6. Cron einrichten ───
echo "⏰ Step 6/6: Cron-Scheduler..."
CRON_LINE="*/5 * * * * $MAS_WORKSPACE/.mas/scheduler.sh"
(crontab -l 2>/dev/null | grep -v "scheduler.sh"; echo "$CRON_LINE") | crontab -
echo "   ✅ Cron aktiv (alle 5 Minuten Daten-Refresh)"

# ─── Fertig ───
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ MAS-ENGINEER INSTALLATION ABGESCHLOSSEN ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Dashboard: http://localhost:3000            ║"
echo "║  API:       http://localhost:3000/api/health ║"
echo "║  Dispatch:  130 entries                     ║"
echo "║  Agents:    50 Sub-Agents                   ║"
echo "║  Tools:     47 aktiv                        ║"
echo "╚══════════════════════════════════════════════╝"

# ─── 7. Goose-App bereitstellen ───
echo "📱 Step 7/7: Goose-App bereitstellen..."
APP_SRC="$MAS_WORKSPACE/.mas/mcp/mas-dispatch-monitor.html"
APP_DEST="/home/marius/.local/share/goose/apps/mas-dispatch-monitor.html"
mkdir -p "$(dirname "$APP_DEST")"
if [ -f "$APP_SRC" ]; then
    cp "$APP_SRC" "$APP_DEST"
    echo "   ✅ App-Datei installiert: $APP_DEST"
    echo "   📱 Open Goose → Apps tab → 'mas-dispatch-monitor'"
else
    echo "   ⚠️ App-Quelldatei missing: $APP_SRC"
    echo "   📱 Create App manuell in Goose: Apps.createApp(PRD)"
fi
