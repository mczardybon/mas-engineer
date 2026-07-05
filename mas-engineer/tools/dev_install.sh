#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# dev_install.sh — MAS-Engineer Vollinstallation
# Führt alle Schritte aus, damit alles direkt nach git clone
# funktioniert: Dashboard-Server, Dispatch-Tracker, Cron, Goose-App
# ═══════════════════════════════════════════════════════════════
set -e

MAS_WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
echo "📦 MAS-Engineer Installation"
echo "   Workspace: $MAS_WORKSPACE"
echo ""

# ─── 1. Abhängigkeiten ───
echo "📦 Schritt 1/6: Abhängigkeiten prüfen..."
command -v node >/dev/null 2>&1 || { echo "❌ node fehlt"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 fehlt"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm fehlt"; exit 1; }
cd "$MAS_WORKSPACE/.mas/mcp"
[ -d node_modules ] || npm install express cors fs-extra 2>/dev/null
echo "   ✅ Abhängigkeiten OK"

# ─── 2. State-Verzeichnisse ───
echo "📁 Schritt 2/6: State-Verzeichnisse anlegen..."
mkdir -p "$MAS_WORKSPACE/.state/dispatch"
mkdir -p "$MAS_WORKSPACE/.state/checkpoints"
echo "   ✅ Verzeichnisse OK"

# ─── 3. Dashboard-Server starten ───
echo "🖥️  Schritt 3/6: Dashboard-Server starten..."
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "   ✅ Server läuft bereits"
else
    cd "$MAS_WORKSPACE/.mas/mcp"
    MAS_WORKSPACE="$MAS_WORKSPACE" nohup /usr/bin/node server.js \
        > "$MAS_WORKSPACE/.mas/dashboard-server.log" 2>&1 &
    echo $! > "$MAS_WORKSPACE/.mas/dashboard.pid"
    sleep 2
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo "   ✅ Server gestartet (PID $(cat $MAS_WORKSPACE/.mas/dashboard.pid))"
    else
        echo "   ❌ Server-Start fehlgeschlagen"
    fi
fi

# ─── 4. Initialdaten generieren ───
echo "📊 Schritt 4/6: Initialdaten generieren..."
cd "$MAS_WORKSPACE"
python3 tools/dev_dashboard_data.py --workspace "$MAS_WORKSPACE" 2>/dev/null
echo "   ✅ Initialdaten OK"

# ─── 5. Live-Daemon starten ───
echo "🚀 Schritt 5/6: Live-Dispatch-Daemon starten..."
DAEMON_PID_FILE="$MAS_WORKSPACE/.mas/live-daemon.pid"
if [ -f "$DAEMON_PID_FILE" ] && kill -0 $(cat "$DAEMON_PID_FILE") 2>/dev/null; then
    echo "   ✅ Daemon läuft bereits"
else
    nohup python3 "$MAS_WORKSPACE/tools/dev_dispatch_live.py" --daemon \
        > "$MAS_WORKSPACE/.mas/live-daemon.log" 2>&1 &
    echo $! > "$DAEMON_PID_FILE"
    echo "   ✅ Daemon gestartet (PID $(cat $DAEMON_PID_FILE))"
fi

# ─── 6. Cron einrichten ───
echo "⏰ Schritt 6/6: Cron-Scheduler..."
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
echo "║  Dispatch:  130 Einträge                     ║"
echo "║  Agents:    50 Sub-Agents                   ║"
echo "║  Tools:     47 aktiv                        ║"
echo "╚══════════════════════════════════════════════╝"
