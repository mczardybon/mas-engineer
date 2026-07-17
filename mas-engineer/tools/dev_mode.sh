#!/bin/bash
# dev_mode.sh — MAS mode-Wechsel
# ================================
# Usage:
#   dev_mode.sh              → Show current mode
#   dev_mode.sh --mas        → Wechsel zu MAS
#   dev_mode.sh --framework  → Wechsel zu framework
#   dev_mode.sh --help       → Hilfe

set -euo pipefail

MODE_FILE="$HOME/.config/goose/.mas-mode"


register_domain() {
    local name="$1"
    local path="$2"
    if [ -z "$name" ] || [ -z "$path" ]; then
        echo -e "${RED}❌ Usage: dev_mode.sh --register <name> <path>${NC}"
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
    local script_dir; script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    python3 -c "
import os, shutil
base = '$script_dir/..'
path = os.path.expanduser('$2')
if os.path.exists(path):
    # rules.yaml
    dst = path + '/rules.yaml'
    if not os.path.exists(dst):
        shutil.copy2(base + '/.state/templates/user_rules_template.yaml', dst)
        print('  ✅ rules.yaml copyrt')
    # .goosehints
    dst2 = path + '/.goosehints'
    if not os.path.exists(dst2):
        shutil.copy2(base + '/.state/templates/goosehints_generic_template', dst2)
        print('  ✅ .goosehints copyrt')
    # Tools
    d = path + '/tools'
    os.makedirs(d, exist_ok=True)
    shutil.copy2(base + '/tools/dev_rule_checker.py', d + '/dev_rule_checker.py')
    shutil.copy2(base + '/tools/dev_yaml_generator.py', d + '/dev_yaml_generator.py')
    print('  ✅ checker + yaml-generator copyrt')
    # SOT-template
    st = path + '/.state/templates'
    os.makedirs(st, exist_ok=True)
    shutil.copy2(base + '/.state/templates/agent_schema_generic.yaml', st + '/agent_schema.yaml')
    print('  ✅ agent_schema.yaml copyrt (SOT-template)')
    # Initiale YAMLs generate
    import subprocess
    subprocess.run(['python3', d + '/dev_yaml_generator.py', '--target', path], capture_output=True)
    print('  ✅ Initiale YAMLs aus SOT generates')
    print('  📋 GENERIC-HAERTUNG + SOT INSTALLIERT')
    print('     - rules.yaml (6 Rulen)')
    print('     - .goosehints (Rule-Refresh)')
    print('     - dev_rule_checker.py (Checker (--mode generic)')
    print('     - dev_yaml_generator.py (Massen-Changeen aus SOT)')
    print('     - agent_schema.yaml (Source of Truth)')
"
    echo -e "${GREEN}✅ Mode=generic, Domain=$name${NC}"
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
            *)         echo "❓ Unknown mode: $mode" ;;
        esac
    else
        echo "❌ No mode file found (should be at ~/.config/goose/.mas-mode)"
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
        echo "Arbeite jetzt only am framework (framework/, update.sh)"
        ;;
    --generic|generic)
        echo "generic" > "$MODE_FILE"
        echo "🟡 GENERIC-MODUS aktiviert"
        echo "Working in Generic mode (project mode)"
        ;;
    --help|-h)
        echo "dev_mode.sh — MAS mode-Wechsel"
        echo ""
        echo "  dev_mode.sh              → Show current mode"
        echo "  dev_mode.sh --mas        → Wechsel zu MAS"
        echo "  dev_mode.sh --framework  → Wechsel zu framework"
        echo "  dev_mode.sh --generic    → Wechsel zu Generic"
        echo "  dev_mode.sh --help       → This help"
        ;;
    *)
        show_mode
        ;;
esac
