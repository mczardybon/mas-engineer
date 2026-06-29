#!/am/bash
# dev_mode.sh — MAS-Modus-Wechsel
# ================================
# Nutzung:
#   dev_mode.sh              → Zeigt aktuellen Modus
#   dev_mode.sh --mas        → Wechsel zu MAS
#   dev_mode.sh --framework  → Wechsel zu Framework
#   dev_mode.sh --help       → Hilfe

set -euo pipefail

MODE_FILE="$HOME/.config/goose/.mas-mode"


register_domain() {
    local name="$1"
    local path="$2"
    if [ -z "$name" ] || [ -z "$path" ]; then
        echo -e "${RED}❌ Nutzung: dev_mode.sh --register <name> <path>${NC}"
        exit 1
    fi
    echo -e "${YELLOW}📝 Registriere new Domain: $name ($path)${NC}"
    python3 -c "
import yaml
registry_path = 'mas-engineer/.state/domains/registry.yaml'
with open(registry_path) as f:
    reg = yaml.safe_load(f) or {'version': '1.0.0', 'domains': {}}
reg['domains']['$name'] = {'path': '$path', 'mode': 'generic', 'isolated': True}
with open(registry_path, 'w') as f:
    yaml.dump(reg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
print('  ✅ Domain registriert')
"
    echo -n "$name" > "$HOME/.config/goose/.active_domain"
    echo -n "generic" > "$MODE_FILE"
    
    # Copy hardening tools to user project
    python3 -c "
import os, shutil
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.expanduser('$2')
if os.path.exists(path):
    # rulen.yaml
    dst = path + '/rulen.yaml'
    if not os.path.exists(dst):
        shutil.copy2(base + '/.state/templates/user_rulen_template.yaml', dst)
        print('  ✅ rulen.yaml kopiert')
    # .goosehints
    dst2 = path + '/.goosehints'
    if not os.path.exists(dst2):
        shutil.copy2(base + '/.state/templates/goosehints_generic_template', dst2)
        print('  ✅ .goosehints kopiert')
    # Tools
    d = path + '/tools'
    os.makedirs(d, exist_ok=True)
    shutil.copy2(base + '/tools/dev_rule_checker.py', d + '/dev_rule_checker.py')
    shutil.copy2(base + '/tools/dev_yaml_generator.py', d + '/dev_yaml_generator.py')
    print('  ✅ checker + yaml-generator kopiert')
    # SOT-Vorlage
    st = path + '/.state/templates'
    os.makedirs(st, exist_ok=True)
    shutil.copy2(base + '/.state/templates/agent_schema_generic.yaml', st + '/agent_schema.yaml')
    print('  ✅ agent_schema.yaml kopiert (SOT-Vorlage)')
    # Initiale YAMLs generate
    import subprocess
    subprocess.run(['python3', d + '/dev_yaml_generator.py', '--target', path], capture_output=True)
    print('  ✅ Initiale YAMLs aus SOT generates')
    print('  📋 GENERIC-HAERTUNG + SOT INSTALLIERT')
    print('     - rulen.yaml (6 Rulen)')
    print('     - .goosehints (Rule-Refresh)')
    print('     - dev_rule_checker.py (Checker (--mode generic)')
    print('     - dev_yaml_generator.py (Massen-Changeen aus SOT)')
    print('     - agent_schema.yaml (Source of Truth)')
"
    echo -e "${GREEN}✅ Modus=generic, Domain=$name${NC}"
}

list_domains() {
    local registry="mas-engineer/.state/domains/registry.yaml"
    if [ ! -f "$registry" ]; then
        echo -e "${RED}❌ No registry.yaml${NC}"
        return
    fi
    python3 -c "
import yaml
reg = yaml.safe_load(open('$registry'))
print('📋 Domains:')
for d, c in reg.get('domains', {}).items():
    print(f'  {d}: mode={c.get("mode","?")}, path={c.get("path","?")}')
"
}


show_mode() {
    if [ -f "$MODE_FILE" ]; then
        local mode; mode=$(cat "$MODE_FILE")
        case "$mode" in
            mas)       echo "🔵 MAS-MODUS" ;;
            framework) echo "🟢 FRAMEWORK-MODUS" ;;
            generic)   echo "🟡 GENERIC-MODUS" ;;
            *)         echo "❓ Unbekannter Modus: $mode" ;;
        esac
    else
        echo "❌ No Modus-file (sollte in ~/.config/goose/.mas-mode liegen)"
    fi
}

case "${1:-}" in
    --mas|mas)
        echo "mas" > "$MODE_FILE"
        echo "🔵 MAS-MODUS aktiviert"
        echo "Arbeite jetzt only am MAS (mas-engineer/, update.sh --mas)"
        ;;
    --framework|framework|--fw|fw)
        echo "framework" > "$MODE_FILE"
        echo "🟢 FRAMEWORK-MODUS aktiviert"
        echo "Arbeite jetzt only am Framework (framework/, update.sh)"
        ;;
    --generic|generic)
        echo "generic" > "$MODE_FILE"
        echo "🟡 GENERIC-MODUS aktiviert"
        echo "Arbeite jetzt im Generic-Modus (Projekt-Modus)"
        ;;
    --help|-h)
        echo "dev_mode.sh — MAS-Modus-Wechsel"
        echo ""
        echo "  dev_mode.sh              → Zeigt aktuellen Modus"
        echo "  dev_mode.sh --mas        → Wechsel zu MAS"
        echo "  dev_mode.sh --framework  → Wechsel zu Framework"
        echo "  dev_mode.sh --generic    → Wechsel zu Generic"
        echo "  dev_mode.sh --help       → Diese Hilfe"
        ;;
    *)
        show_mode
        ;;
esac
