#!/bin/bash
# =============================================================================
# dev_session_cleanup.sh – Session-Cleaner for Goose Chat-Verlauf (v2.0)
# =============================================================================
# Deletes auto-generated sessions, keeps only real user chats.
#
# Verwendung:
#   ./dev_session_cleanup.sh              # Trockenlauf
#   ./dev_session_cleanup.sh --exec       # Wirklich delete + VACUUM
#   ./dev_session_cleanup.sh --status     # Only Status anshow
#
# Was will deleted? (mit --exec)
#   - All 'scheduled' Sessions (Dashboard-Cron)
#   - Health-Ping Sub-Agents (<1000 Tokens, older 1h)
#   - All 'sub_agent' Sessions older als 24h
#   - framework-interne 'user' Sessions (Name: 'Agent ...')
#   - Empty 'New Chat' User-Sessions
#
# Was bleibt keep?
#   - Echte User-Chats (vom User started)
#   - Current Sub-Agent Sessions (<24h)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$HOME/.local/share/goose/sessions/sessions.db"
MODE="${1:-dry-run}"
KEEP_HOURS="${2:-24}"

# Farben
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo -e "${CYAN}  Goose Session Cleanup v2.0               ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"
echo ""

if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}❌ Database not found: $DB_PATH${NC}"
    exit 1
fi

# ===== STATUS =====
if [ "$MODE" = "--status" ]; then
    echo -e "${YELLOW}📊 Status der Sessions-Database:${NC}"
    python3 -c "
import sqlite3, datetime, os
os.environ['DB_PATH'] = '$DB_PATH'
db = sqlite3.connect(os.environ['DB_PATH'])
c = db.cursor()
c.execute('SELECT COUNT(*) FROM sessions')
total = c.fetchone()[0]
c.execute(\"SELECT session_typee, COUNT(*) FROM sessions GROUP BY session_typee ORDER BY COUNT(*) DESC\")
print('  typee-Verteilung:')
for t, n in c.fetchall():
    print(f'    {t:15s}: {n:3d} Sessions')
c.execute(\"SELECT session_typee, MIN(created_at), MAX(created_at) FROM sessions GROUP BY session_typee\")
print('  datesspanne:')
for t, mi, ma in c.fetchall():
    print(f'    {t:15s}: {mi} bis {ma}')
c.execute('SELECT SUM(COALESCE(total_tokens,0)) FROM sessions')
tokens = c.fetchone()[0]
print(f'\n  Total-Tokens: {tokens:,}')
print(f'  Total-Sessions: {total}')
db.close()
"
    exit 0
fi

# ===== ANALYSE =====
echo -e "${YELLOW}🔍 Analyze deletable Sessions...${NC}"
echo ""

python3 << 'PYEOF'
import sqlite3, datetime, os, sys

db_path = os.environ.get('DB_PATH', os.path.expanduser('~/.local/share/goose/sessions/sessions.db'))
keep_hours = int(os.environ.get('KEEP_HOURS', '24'))

db = sqlite3.connect(db_path)
c = db.cursor()

now = datetime.datetime.now()
cutoff = now - datetime.timedelta(hours=keep_hours)
cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
cutoff_1h = (now - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

total_del = 0
total_tokens_del = 0

# 1. Scheduled Sessions (all)
c.execute("SELECT COUNT(*), SUM(COALESCE(total_tokens,0)) FROM sessions WHERE session_typee='scheduled'")
cnt_sched, tok_sched = c.fetchone()
print(f'  1. Scheduled (all):          {cnt_sched or 0:3d} Sessions, {tok_sched or 0:>8,} Tokens')
total_del += (cnt_sched or 0)
total_tokens_del += (tok_sched or 0)

# 2. Sub-Agent Sessions older als KEEP_HOURS
c.execute("SELECT COUNT(*), SUM(COALESCE(total_tokens,0)) FROM sessions WHERE session_typee='sub_agent' AND created_at < ?", (cutoff_str,))
cnt_sub, tok_sub = c.fetchone()
print(f'  2. Sub-Agent >{keep_hours}h old:   {cnt_sub or 0:3d} Sessions, {tok_sub or 0:>8,} Tokens (older als {cutoff_str})')
total_del += (cnt_sub or 0)
total_tokens_del += (tok_sub or 0)

# 2a. Health-Ping Sub-Agents (tokens < 1000, older als 1h)
c.execute("SELECT COUNT(*), SUM(COALESCE(total_tokens,0)) FROM sessions WHERE session_typee='sub_agent' AND COALESCE(total_tokens,0) < 1000 AND created_at < ?", (cutoff_1h,))
cnt_ping, tok_ping = c.fetchone()
print(f'     Health-Pings (<1K Tokens): {cnt_ping or 0:3d} Sessions, {tok_ping or 0:>8,} Tokens')
total_del += (cnt_ping or 0)
total_tokens_del += (tok_ping or 0)

# 2b. Sub-agents that are newer (remain)
c.execute("SELECT COUNT(*), SUM(COALESCE(total_tokens,0)) FROM sessions WHERE session_typee='sub_agent' AND created_at >= ?", (cutoff_str,))
cnt_sub_keep, tok_sub_keep = c.fetchone()
print(f'     Sub-Agent <{keep_hours}h old:    {cnt_sub_keep or 0:3d} Sessions, {tok_sub_keep or 0:>8,} Tokens (BLEIBT)')

# 3. framework-interne User-Sessions ('Agent ...')
c.execute("SELECT COUNT(*), SUM(COALESCE(total_tokens,0)) FROM sessions WHERE session_typee='user' AND name LIKE 'Agent %'")
cnt_agent, tok_agent = c.fetchone()
print(f'  3. framework-User (Agent):   {cnt_agent or 0:3d} Sessions, {tok_agent or 0:>8,} Tokens')
total_del += (cnt_agent or 0)
total_tokens_del += (tok_agent or 0)

# 4. Empty 'New Chat' User-Sessions
c.execute("SELECT COUNT(*), SUM(COALESCE(total_tokens,0)) FROM sessions WHERE session_typee='user' AND (name = 'New Chat' OR name IS NULL)")
cnt_new, tok_new = c.fetchone()
print(f'  4. Empty New Chat:           {cnt_new or 0:3d} Sessions, {tok_new or 0:>8,} Tokens')
total_del += (cnt_new or 0)
total_tokens_del += (tok_new or 0)

# 5. Echte User-Chats (BLEIBT)
c.execute("SELECT COUNT(*), SUM(COALESCE(total_tokens,0)) FROM sessions WHERE session_typee='user' AND name NOT LIKE 'Agent %' AND name != 'New Chat' AND name IS NOT NULL")
cnt_real, tok_real = c.fetchone()
print(f'  5. Echte User-Chats:         {cnt_real or 0:3d} Sessions, {tok_real or 0:>8,} Tokens (BLEIBT)')

print(f'\n  ==========================================')
print(f'  ZU DELETE:                  {total_del:3d} Sessions, {total_tokens_del:>8,} Tokens')
print(f'  BLEIBT:                      {cnt_real or 0:3d} Sessions, {tok_real or 0:>8,} Tokens')
print(f'  ==========================================')
db.close()
PYEOF

# ===== EXEC =====
echo ""
case "$MODE" in
    --exec)
        echo -e "${RED}⚠️  EXEC-Modus! Delete jetzt...${NC}"
        python3 << 'PYEOF'
import sqlite3, datetime, os

db_path = os.environ.get('DB_PATH', os.path.expanduser('~/.local/share/goose/sessions/sessions.db'))
keep_hours = int(os.environ.get('KEEP_HOURS', '24'))

db = sqlite3.connect(db_path)
c = db.cursor()

now = datetime.datetime.now()
cutoff = now - datetime.timedelta(hours=keep_hours)
cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
cutoff_1h = (now - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

total = 0

# 1. Scheduled
c.execute("DELETE FROM sessions WHERE session_typee='scheduled'")
total += c.rowcount
print(f'  ✅ Deleted: scheduled = {c.rowcount} Sessions')

# 2. Health-Ping Sub-Agents (tokens < 1000, older als 1h)
c.execute("DELETE FROM sessions WHERE session_typee='sub_agent' AND COALESCE(total_tokens,0) < 1000 AND created_at < ?", (cutoff_1h,))
total += c.rowcount
print(f'  ✅ Deleted: Health-Pings <1K Tokens = {c.rowcount} Sessions')

# 3. Sub-Agent older als KEEP_HOURS
c.execute("DELETE FROM sessions WHERE session_typee='sub_agent' AND created_at < ?", (cutoff_str,))
total += c.rowcount
print(f'  ✅ Deleted: sub_agent >{keep_hours}h = {c.rowcount} Sessions')

# 4. framework-User (Agent ...)
c.execute("DELETE FROM sessions WHERE session_typee='user' AND name LIKE 'Agent %'")
total += c.rowcount
print(f'  ✅ Deleted: Agent-User = {c.rowcount} Sessions')

# 5. Empty New Chat
c.execute("DELETE FROM sessions WHERE session_typee='user' AND (name = 'New Chat' OR name IS NULL)")
total += c.rowcount
print(f'  ✅ Deleted: New Chat = {c.rowcount} Sessions')

db.commit()
db.close()
print(f'\n  🎯 Insgesamt {total} Sessions deleted!')
PYEOF

        # VACUUM + WAL-Checkpoint
        echo -e "${CYAN}💿 Komprimiere Database...${NC}"
        python3 << 'PYEOF'
import sqlite3, os
db_path = os.environ.get('DB_PATH', os.path.expanduser('~/.local/share/goose/sessions/sessions.db'))
if os.path.exists(db_path):
    db = sqlite3.connect(db_path)
    db.execute('PRAGMA wal_checkpoint(TRUNCATE);')
    db.execute('VACUUM;')
    db.execute('PRAGMA wal_checkpoint(TRUNCATE);')
    db.close()
    size_mb = round(os.path.getsize(db_path) / 1024 / 1024, 1)
    print(f'  ✅ DB komprimiert: {size_mb} MB')
else:
    print('  ⚠️  DB not found')
PYEOF
        ;;
    *)
        echo -e "${YELLOW}⚠️  Trockenlauf – nothing deleted.${NC}"
        echo -e "   Mit ${GREEN}--exec${NC} execute um wirklich zu delete."
        ;;
esac

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Finished.${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
