#!/bin/bash
# dev_rule_refresh.sh — method 5: Reaktivierungs-Anker (MAS + Generic)
# Will all 5 Steps aufgerufen. Loads Rulen frisch aus file.
# --mode mas     → MAS-eigene Rulen (hard_rules.yaml → rulen_5/4/2_*.yaml)
# --mode generic → User-Rulen (rulen.yaml)
# Based on: "Shell commands are deterministic — LLM context is ephemeral"

MODE="${1:-mas}"
if [ "$MODE" = "--mode" ]; then
    MODE="$2"
fi

# CWD-independent path resolution (R110-217 fix for C3 nested-path bug).
# Same defensive pattern as tools/dev_rule_checker.py:14-15.
# Find script's own dir (works regardless of CWD), then resolve.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -d "$WORKSPACE_ROOT/mas-engineer/.mase/rules" ]; then
    # Outer layout: workspace_root/mas-engineer/.mase/rules/
    REGL_DIR="$WORKSPACE_ROOT/mas-engineer/.mase/rules"
    TEMPLATE_DIR="$WORKSPACE_ROOT/mas-engineer/.mase/templates"
elif [ -d "$SCRIPT_DIR/../.mase/rules" ]; then
    # Inner layout: invoked from inside mas-engineer/ subdir
    REGL_DIR="$SCRIPT_DIR/../.mase/rules"
    TEMPLATE_DIR="$SCRIPT_DIR/../.mase/templates"
else
    # Fallback: legacy CWD-relative (may write to wrong nested path)
    REGL_DIR="mas-engineer/.mase/rules"
    TEMPLATE_DIR="mas-engineer/.mase/templates"
fi

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
        echo "  → Copy user_rulen_template.yaml after .mase/rules/rulen.yaml"
        cp -n "$TEMPLATE_DIR/user_rulen_template.yaml" "$REGL_DIR/rulen.yaml" 2>/dev/null
    fi
else
    # ── MAS-MODE: Harte Rulen load ──
    # R110-218: real hard_rules.yaml uses 'rules' (not 'rulen') and
    # 'hardness' (not 'haerte') keys. R110-140 rename was incomplete.
    python3 -c "
import yaml, os

path = '$REGL_DIR/hard_rules.yaml'
if not os.path.exists(path):
    print('⚠️  No hard_rules.yaml found')
    exit(0)

with open(path) as f:
    data = yaml.safe_load(f)

# R110-218.b: top-level key is 'rules' (was 'rulen')
rules = data.get('rules', [])
# R110-218.d: top-level metadata key is 'hardness_levels' (was 'haerte_leveln')
leveln = data.get('hardness_levels', {})

# R110-218.c: rule inner key is 'hardness' (was 'haerte').
# R110-218 also: hardness_levels sub-keys are extreme/strong/normal/weak
# (not the German extrem_stark/stark/normal/schwach the old code assumed).
for r in rules:
    h = r['hardness']
    level = leveln.get('extreme' if h >= 5 else 'strong' if h >= 4 else 'normal' if h >= 2 else 'weak', {})
    symbol = level.get('symbol', '')
    r['text'] = f\"{symbol} {r['prompt_text']}\"

# R110-218.e: output filenames and key names match the rest of the codebase
# (rules_5_extreme.yaml, rules_4_strong.yaml, rules_2_normal.yaml already exist
# and are loaded by dev_rule_checker.py:20-21).
for level, label in [(5, '5_extreme'), (4, '4_strong'), (2, '2_normal')]:
    filtered = [r for r in rules if r['hardness'] == level]
    outpath = f'$REGL_DIR/rules_{label}.yaml'
    with open(outpath, 'w') as f:
        yaml.dump({'rules': filtered, 'hardness': level}, f, default_flow_style=False)

print(f'Geschrieben: rules_5_extreme.yaml ({sum(1 for r in rules if r[\"hardness\"]==5)} EXTREM-Rulen)')
print(f'Geschrieben: rules_4_strong.yaml ({sum(1 for r in rules if r[\"hardness\"]==4)} STARK-Rulen)')
print(f'Geschrieben: rules_2_normal.yaml ({sum(1 for r in rules if r[\"hardness\"]==2)} NORMAL-Rulen)')
"

    # Output: Show harte Rulen
    echo ""
    echo "=== ⛔⛔⛔⛔⛔ EXTREM-STARK RULES (frisch loaded $(date +%H:%M:%S)) ==="
    # R110-218: output file is rules_5_extreme.yaml with 'rules' key and 'text' field
    python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/rules_5_extreme.yaml')); [print(f'  → {r[\"text\"]}') for r in d.get('rules', [])]" 2>/dev/null

    echo ""
    echo "=== ⛔⛔⛔ STARK RULES ==="
    python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/rules_4_strong.yaml')); [print(f'  → {r[\"text\"]}') for r in d.get('rules', [])]" 2>/dev/null

    echo ""
    echo "=== ⛔ NORMAL RULES ==="
    python3 -c "import yaml; d=yaml.safe_load(open('$REGL_DIR/rules_2_normal.yaml')); [print(f'  → {r[\"text\"]}') for r in d.get('rules', [])]" 2>/dev/null
fi

# Write Timestamp
echo "$(date +%s)" > "$REGL_DIR/.last_refresh"
echo "REFRESHED" > "$REGL_DIR/.state"

echo ""
echo "⛔⛔⛔⛔⛔ Reaktivierung completed (mode=$MODE) — Rulen frisch im Context"
