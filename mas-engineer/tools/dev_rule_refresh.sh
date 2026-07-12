#!/bin/bash
# dev_rule_refresh.sh — method 5: Reaktivierungs-Anker (MAS + Generic)
# Will all 5 Steps aufgerufen. Loads Rulen frisch aus file.
# --mode mas     → MAS-eigene Rulen (harte_rulen.yaml → rulen_5/4/2_*.yaml)
# --mode generic → User-Rulen (rulen.yaml)
# Based on: "Shell commands are deterministic — LLM context is ephemeral"

MODE="${1:-mas}"
if [ "$MODE" = "--mode" ]; then
    MODE="$2"
fi

REGL_DIR="mas-engineer/.state/rules"

if [ ! -d "$REGL_DIR" ]; then
    mkdir -p "$REGL_DIR"
fi

if [ "$MODE" = "generic" ]; then
    # ── GENERIC-MODE: User-Rulen load ──
    echo ""
    echo "=== ⛔ GENERIC-RULES (frisch loaded $(date +%H:%M:%S)) ==="
    if [ -f "$REGL_DIR/rulen.yaml" ]; then
        python3 -c "
import yaml
with open('$REGL_DIR/rulen.yaml') as f:
    data = yaml.safe_load(f)
rulen = data.get('rulen', data.get('rules', []))
for r in rulen:
    h = r.get('haerte', 3)
    symbol = '⛔⛔⛔⛔⛔' if h >= 5 else '⛔⛔⛔' if h >= 4 else '⛔' if h >= 2 else '⚠️'
    print(f'  {symbol} {r.get(\"prompt_text\", r.get(\"name\", \"?\"))}')
print()
print(f'⛔ {len(rulen)} Generic-Rulen loaded')
"
    else
        echo "  ⚠️  No rulen.yaml found — Generic-Rulen not active"
        echo "  → Copy user_rulen_template.yaml after .state/rules/rulen.yaml"
        cp -n mas-engineer/.state/templates/user_rulen_template.yaml "$REGL_DIR/rulen.yaml" 2>/dev/null
    fi
else
    # ── MAS-MODE: Harte Rulen load ──
    python3 -c "
import yaml, os

path = '$REGL_DIR/harte_rulen.yaml'
if not os.path.exists(path):
    print('⚠️  No harte_rulen.yaml found')
    exit(0)

with open(path) as f:
    data = yaml.safe_load(f)

rulen = data.get('rulen', [])
leveln = data.get('haerte_leveln', {})

for r in rulen:
    h = r['haerte']
    level = leveln.get('extrem_stark' if h >= 5 else 'stark' if h >= 4 else 'normal' if h >= 2 else 'schwach', {})
    symbol = level.get('symbol', '')
    r['text'] = f\"{symbol} {r['prompt_text']}\"

for level, label in [(5, '5_extrem'), (4, '4_stark'), (2, '2_normal')]:
    filtered = [r for r in rulen if r['haerte'] == level]
    outpath = f'$REGL_DIR/rulen_{label}.yaml'
    with open(outpath, 'w') as f:
        yaml.dump({'rulen': filtered, 'haerte': level}, f, default_flow_style=False)

with open(f'$REGL_DIR/rulen_5_extrem.yaml') as f:
    d5 = yaml.safe_load(f)
if d5 and d5.get('rulen'):
    print(f'Geschrieben: rulen_5_extrem.yaml ({len(d5[\"rulen\"])} EXTREM-Rulen)')
with open(f'$REGL_DIR/rulen_4_stark.yaml') as f:
    d4 = yaml.safe_load(f)
if d4 and d4.get('rulen'):
    print(f'Geschrieben: rulen_4_stark.yaml ({len(d4[\"rulen\"])} STARK-Rulen)')
with open(f'$REGL_DIR/rulen_2_normal.yaml') as f:
    d2 = yaml.safe_load(f)
if d2 and d2.get('rulen'):
    print(f'Geschrieben: rulen_2_normal.yaml ({len(d2[\"rulen\"])} NORMAL-Rulen)')
"

    # Output: Show harte Rulen
    echo ""
    echo "=== ⛔⛔⛔⛔⛔ EXTREM-STARK RULES (frisch loaded $(date +%H:%M:%S)) ==="
    python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/rulen_5_extrem.yaml')); [print(f'  → {r[\"text\"]}') for r in d['rulen']]" 2>/dev/null

    echo ""
    echo "=== ⛔⛔⛔ STARK RULES ==="
    python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/rulen_4_stark.yaml')); [print(f'  → {r[\"text\"]}') for r in d['rulen']]" 2>/dev/null

    echo ""
    echo "=== ⛔ NORMAL RULES ==="
    python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/rulen_2_normal.yaml')); [print(f'  → {r[\"text\"]}') for r in d['rulen']]" 2>/dev/null
fi

# Write Timestamp
echo "$(date +%s)" > "$REGL_DIR/.last_refresh"
echo "REFRESHED" > "$REGL_DIR/.state"

echo ""
echo "⛔⛔⛔⛔⛔ Reaktivierung completed (mode=$MODE) — Rulen frisch im Context"
