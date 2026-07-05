#!/bin/bash
# MAS Scheduler — refreshed Dashboard-Daten alle 5 Minuten
# Kann via cron oder systemd timer laufen

MAS_WORKSPACE="/home/marius/agent_new_start/mas-agent"
TOOLS="$MAS_WORKSPACE/tools"
LOG="$MAS_WORKSPACE/.mas/scheduler.log"

echo "[$(date)] Scheduler: Refreshe Dashboard-Daten..." >> "$LOG"
cd "$MAS_WORKSPACE"
python3 "$TOOLS/dev_dashboard_data.py" --workspace "$MAS_WORKSPACE" >> "$LOG" 2>&1
echo "[$(date)] Scheduler: Fertig." >> "$LOG"
