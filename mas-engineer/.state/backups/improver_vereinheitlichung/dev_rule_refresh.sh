#!/bin/bash
# dev_rule_refresh.sh — Methode 5: Reaktivierungs-Anker
# Wird alle 5 Schritte aufgerufen. Lädt harte Regeln frisch aus Datei.
# Basiert auf: "Shell-Befehle sind deterministisch — LLM-Kontext ist flüchtig"

REGL_DIR="mas-engineer/.state/rules"

if [ ! -d "$REGL_DIR" ]; then
    mkdir -p "$REGL_DIR"
fi

# Schreibe Regeln in 3 separate Dateien (nach Härte sortiert)
python3 -c "
import yaml, os

path = '$REGL_DIR/harte_regeln.yaml'
with open(path) as f:
    data = yaml.safe_load(f)

regeln = data.get('regeln', [])
stufen = data.get('haerte_stufen', {})

for r in regeln:
    h = r['haerte']
    stufe = stufen.get('extrem_stark' if h >= 5 else 'stark' if h >= 4 else 'normal' if h >= 2 else 'schwach', {})
    symbol = stufe.get('symbol', '')
    r['text'] = f\"{symbol} {r['prompt_text']}\"

for level, label in [(5, '5_extrem'), (4, '4_stark'), (2, '2_normal')]:
    filtered = [r for r in regeln if r['haerte'] == level]
    outpath = f'$REGL_DIR/regeln_{label}.yaml'
    with open(outpath, 'w') as f:
        yaml.dump({'regeln': filtered, 'haerte': level}, f, default_flow_style=False)
    print(f'Geschrieben: {outpath} ({len(filtered)} Regeln)')
"

# Ausgabe: Zeige harte Regeln (fuer LLM-Kontext)
echo ""
echo "=== ⛔⛔⛔⛔⛔ EXTREM-STARK REGELN (frisch geladen $(date +%H:%M:%S)) ==="
python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/regeln_5_extrem.yaml')); [print(f'  → {r[\"text\"]}') for r in d['regeln']]"

echo ""
echo "=== ⛔⛔⛔ STARK REGELN ==="
python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/regeln_4_stark.yaml')); [print(f'  → {r[\"text\"]}') for r in d['regeln']]"

echo ""
echo "=== ⛔ NORMAL REGELN ==="
python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/regeln_2_normal.yaml')); [print(f'  → {r[\"text\"]}') for r in d['regeln']]"

# Schreibe Timestamp
echo "$(date +%s)" > "$REGL_DIR/.last_refresh"
echo "REFRESHED" > "$REGL_DIR/.state"

echo ""
echo "⛔⛔⛔⛔⛔ Reaktivierung abgeschlossen — Regeln frisch im Kontext"
