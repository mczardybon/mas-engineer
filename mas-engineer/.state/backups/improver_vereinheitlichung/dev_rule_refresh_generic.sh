#!/bin/bash
# dev_rule_refresh_generic.sh — Methode 5: Reaktivierungs-Anker (Generic-Version)
# Wird alle 5 Schritte aufgerufen. Lädt Regeln aus User-Definition.
# Generic: Keine MAS-Abhängigkeiten. 0 Sub-Agenten nötig.

REGL_DIR=".state/rules"
PROMPT_DATEI=".state/last_refresh.txt"

if [ ! -d "$REGL_DIR" ]; then
    mkdir -p "$REGL_DIR"
fi

if [ -f "$REGL_DIR/regeln.yaml" ]; then
    python3 -c "
import yaml
with open('$REGL_DIR/regeln.yaml') as f:
    data = yaml.safe_load(f) or {'regeln': []}
regeln = data.get('regeln', [])
print('=== ⛔ AKTIVE REGELN (frisch geladen ' + '$(date +%H:%M:%S)' + ') ===')
print(f'Geladene Regeln: {len(regeln)}')
for r in regeln:
    h = r.get('haerte', 1)
    sym = '⛔⛔⛔⛔⛔' if h >= 5 else '⛔⛔⛔' if h >= 4 else '⛔' if h >= 2 else '⚠️'
    block = ' [BLOCKIERT]' if r.get('block') else ''
    print(f'{sym} {r[\"name\"]}{block}: {r[\"prompt_text\"]}')
print()
print('=== ENDE REGELN ===')
"
else
    cat > "$REGL_DIR/regeln.yaml" << 'DEFAULT'
# regeln.yaml — User-definierte Verhaltensregeln (Generic-Improver)
# Härte-Stufen: 5=⛔⛔⛔⛔⛔ (blockt Aktion), 4=⛔⛔⛔ (Warnung ohne Block)
#               2=⛔ (Hinweis), 1=⚠️ (optional)
#
# blocked_files: Dateinamen die von dieser Regel geschützt werden
# block: true → Aktion wird gestoppt bis Bestätigung
version: "1.0.0"
last_updated: "$(date -Iseconds)"
regeln:
  - id: "G01"
    name: "README_GESCHUETZT"
    haerte: 5
    prompt_text: "Niemals README.md oder CHANGELOG.md automatisch ueberschreiben"
    block: true
    blocked_files: ["README.md", "CHANGELOG.md"]
  - id: "G02"
    name: "REQUIREMENTS_GESCHUETZT"
    haerte: 4
    prompt_text: "requirements.txt/pyproject.toml nur mit User-Bestaetigung aendern"
    block: false
    blocked_files: ["requirements.txt", "pyproject.toml", "Cargo.toml", "package.json"]
DEFAULT
    echo "=== ⛔ AKTIVE REGELN (frisch geladen $(date +%H:%M:%S)) ==="
    echo "ℹ️ Keine User-Regeln — Default angelegt: .state/rules/regeln.yaml"
    echo "ℹ️ Bearbeite die Datei um eigene Regeln mit Härte-Stufen zu definieren"
    echo "=== ENDE REGELN ==="
fi

if [ -f ".goosehints" ]; then
    echo ""
    echo "=== 📋 .goosehints (Projekt-Hinweise) ==="
    head -20 .goosehints
    echo "=== ENDE .goosehints ==="
fi

date +%s > "$PROMPT_DATEI"
echo "REFRESHED" > "$REGL_DIR/.state"
echo ""
echo "⛔ Regeln reaktiviert — $(date '+%H:%M:%S')"
