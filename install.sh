#!/bin/bash
# install.sh — MAS-Engineer Installer
# =====================================
# Installs MAS-Engineer from the ZIP distribution
# into ~/.config/goose/ so Goose can use it directly.
#
# Usage:
#   ./install.sh              → Install MAS (default)
#   ./install.sh --mas        → Install MAS (explicit)
#   ./install.sh --status     → Show status
#   ./install.sh --dry-run    → Only check, don't copy
#   ./install.sh --help       → This help
# =====================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOOSE_CONFIG="$HOME/.config/goose"
GOOSE_RECIPES="$GOOSE_CONFIG/recipes"
GOOSE_DOCS="$GOOSE_CONFIG/docs"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# === SOURCES (Distribution) — Structure Detection ===
if [ -f "$INSTALL_DIR/recipe/dev-mas-engineer.yaml" ]; then
    # Port mode: flat structure (MAS initialized as project)
    SRC_MAS_RECIPE="$INSTALL_DIR/recipe/dev-mas-engineer.yaml"
    SRC_MAS_SUB="$INSTALL_DIR/recipe/sub"
    SRC_MAS_TOOLS="$INSTALL_DIR/tools"
    SRC_MAS_DOCS="$INSTALL_DIR/docs"
    SRC_MAS_STATE="$INSTALL_DIR/.state"
else
    # Traditional: MAS under mas-engineer/
    SRC_MAS_RECIPE="$INSTALL_DIR/mas-engineer/recipe/dev-mas-engineer.yaml"
    SRC_MAS_SUB="$INSTALL_DIR/mas-engineer/recipe/sub"
    SRC_MAS_TOOLS="$INSTALL_DIR/mas-engineer/tools"
    SRC_MAS_DOCS="$INSTALL_DIR/mas-engineer/docs"
    SRC_MAS_STATE="$INSTALL_DIR/mas-engineer/.state"
fi

# === TARGETS (~/.config/goose/) ===
DST_MAS_RECIPE="$GOOSE_RECIPES/dev-mas-engineer.yaml"
DST_MAS_SUB="$GOOSE_RECIPES/sub"
DST_MAS_TOOLS="$GOOSE_RECIPES/mas-engineer-tools"
DST_MAS_DOCS="$GOOSE_DOCS/mas-engineer"
DST_MAS_STATE="$GOOSE_CONFIG/.state"

COPIED=0; SKIPPED=0; ERRORS=0; DRY_RUN=false

info()    { echo -e "${GREEN}${BOLD}INFO${NC}  $1"; }
warn()    { echo -e "${YELLOW}${BOLD}WARN${NC}  $1"; }
error()   { echo -e "${RED}${BOLD}ERROR${NC} $1"; ERRORS=$((ERRORS + 1)); }
header()  { echo -e "\n${BLUE}${BOLD}━━━ $1 ━━━${NC}"; }
dry()     { echo -e "  ${YELLOW}[DRY-RUN]${NC} $1"; }
ok()      { echo -e "  ${GREEN}✔${NC} $1"; }
skip()    { echo -e "  ${YELLOW}→${NC} $1 (skipped)"; }

validate_yaml() {
    python3 -c "import yaml, sys
try:
    with open('$1') as f: yaml.safe_load(f)
    sys.exit(0)
except Exception as e:
    print(str(e)); sys.exit(1)" 2>/dev/null || return 1
}
validate_python() {
    python3 -c "import ast; ast.parse(open('$1').read())" 2>/dev/null || return 1
}

backup() {
    local target="$1"
    local backup_dir="$INSTALL_DIR/.backups/${TIMESTAMP}_pre_install"
    [ "$DRY_RUN" = true ] && { dry "Backup: $target"; return; }
    mkdir -p "$backup_dir" 2>/dev/null || true
    [ -e "$target" ] && cp -r "$target" "$backup_dir/" 2>/dev/null || true
}

copy_file() {
    local src="$1"; local dst="$2"; local label="${3:-}"
    local name; name=$(basename "$src")
    if ! [ -f "$src" ]; then error "Source not found: $src"; return 1; fi
    if [ "$DRY_RUN" = true ]; then
        [ -z "$label" ] && dry "$name → $dst" || dry "${label}${name} → $dst"
        COPIED=$((COPIED + 1)); return
    fi
    mkdir -p "$(dirname "$dst")"
    if [ -f "$dst" ] && diff "$src" "$dst" > /dev/null 2>&1; then
        skip "${label}${name} (already current)"; SKIPPED=$((SKIPPED + 1)); return
    fi
    cp "$src" "$dst"
    case "$name" in *.py|*.sh) chmod +x "$dst" ;; esac
    COPIED=$((COPIED + 1))
    ok "${label}${name}"
}

copy_dir() {
    local src_dir="$1"; local dst_dir="$2"; local pattern="${3:-*}"; local label="${4:-}"
    if ! [ -d "$src_dir" ]; then warn "Source not found: $src_dir (skipped)"; return 0; fi
    if [ "$DRY_RUN" = true ]; then
        local count; count=$(find "$src_dir" -maxdepth 1 -name "$pattern" -typee f 2>/dev/null | wc -l)
        dry "$label $count files → $dst_dir/"; COPIED=$((COPIED + count)); return
    fi
    mkdir -p "$dst_dir"
    for file in "$src_dir"/$pattern; do
        [ -f "$file" ] && copy_file "$file" "$dst_dir/$(basename "$file")" "$label"
    done
}

# ─── VALIDATION ──────────────────────────────────────────────
validate_all() {
    header "Validation"
    local errors=0
    
    # Haupt-Recipe
    if [ -f "$SRC_MAS_RECIPE" ]; then
        validate_yaml "$SRC_MAS_RECIPE" && ok "dev-mas-engineer.yaml ✅" || { error "dev-mas-engineer.yaml: YAML error"; errors=$((errors+1)); }
    else
        error "dev-mas-engineer.yaml missing! No MAS-Engineer to install."
        return 1
    fi
    
    # Sub-Agenten
    local sub_count=0 sub_valid=0
    for f in "$SRC_MAS_SUB"/sub_mas-*.yaml; do
        [ -f "$f" ] && sub_count=$((sub_count+1)) && validate_yaml "$f" && sub_valid=$((sub_valid+1)) || errors=$((errors+1))
    done
    ok "$sub_valid/$sub_count Sub-agents YAML-valid"
    
    # Tools
    local py_ok=0 py_count=0 sh_ok=0 sh_count=0
    for f in "$SRC_MAS_TOOLS"/dev_*.py; do [ -f "$f" ] && py_count=$((py_count+1)) && validate_python "$f" && py_ok=$((py_ok+1)) || errors=$((errors+1)); done
    for f in "$SRC_MAS_TOOLS"/*.sh; do [ -f "$f" ] && sh_count=$((sh_count+1)); done
    ok "$py_ok/$py_count Python-Tools valid"
    ok "$sh_count shell tools (syntax checked)"
    
    # SOT-Workflows
    if [ -f "$SRC_MAS_STATE/workflows.yaml" ]; then
        validate_yaml "$SRC_MAS_STATE/workflows.yaml" && ok "workflows.yaml ✅" || { error "workflows.yaml: YAML error"; errors=$((errors+1)); }
    fi
    
    if [ "$errors" -gt 0 ]; then
        error "$errors Validationserror — Installation nicht sicher!"
        return 1
    fi
    info "All checks passed. Installation can proceed."
    return 0
}

# ─── INSTALL: MAS (Distribution → ~/.config/goose/) ──────────
install_mas() {
    echo ""
    echo -e "${BOLD}MAS-Engineer Installation${NC}"
    echo "  Source: $INSTALL_DIR/mas-engineer/"
    echo "  Target:   ~/.config/goose/"
    echo ""
    
    # 1. Validate
    validate_all || return 1
    echo ""
    
    # 2. Backup bestehender Installation
    header "Backup (previous installation)"
    backup "$DST_MAS_RECIPE"
    backup "$DST_MAS_TOOLS"
    backup "$DST_MAS_DOCS"
    [ "$DRY_RUN" = false ] && [ -d "$HOME/.config/goose/.backups/${TIMESTAMP}_pre_install" ] && ok "Backup created" || dry "Backup would be created"
    echo ""
    
    # 3. copyren
    header "Install"
    
    # Haupt-Recipe
    [ -f "$SRC_MAS_RECIPE" ] && copy_file "$SRC_MAS_RECIPE" "$DST_MAS_RECIPE" "📄 Recipe: "
    
    # Sub-Agenten
    [ -d "$SRC_MAS_SUB" ] && copy_dir "$SRC_MAS_SUB" "$DST_MAS_SUB" "sub_mas-*.yaml" "📁 Subs:    "
    
    # Tools
    [ -d "$SRC_MAS_TOOLS" ] && copy_dir "$SRC_MAS_TOOLS" "$DST_MAS_TOOLS" "*.py" "🔧 Python:  "
    [ -d "$SRC_MAS_TOOLS" ] && copy_dir "$SRC_MAS_TOOLS" "$DST_MAS_TOOLS" "*.sh" "🔧 Shell:   "
    
    # Dokumentation
    [ -d "$SRC_MAS_DOCS" ] && copy_dir "$SRC_MAS_DOCS" "$DST_MAS_DOCS" "*.md" "📝 Docs:    "
    
    # State/Wissen
    if [ -d "$SRC_MAS_STATE/knowledge" ]; then
        if [ "$DRY_RUN" = true ]; then
            local k_count; k_count=$(find "$SRC_MAS_STATE/knowledge" -name "*.md" -typee f | wc -l)
            dry "📚 $k_count knowledge files → $DST_MAS_STATE/knowledge/"
            COPIED=$((COPIED + k_count))
        else
            mkdir -p "$DST_MAS_STATE/knowledge"
            for f in "$SRC_MAS_STATE/knowledge"/*.md; do
                [ -f "$f" ] && copy_file "$f" "$DST_MAS_STATE/knowledge/$(basename "$f")" "📚 Knowledge: "
            done
        fi
    fi
    
    # SOT workflows.yaml
    [ -f "$SRC_MAS_STATE/workflows.yaml" ] && copy_file "$SRC_MAS_STATE/workflows.yaml" "$DST_MAS_STATE/workflows.yaml" "📜 SOT:     "
    

    
    echo ""
    
    # 4. Set .mas-mode
    if [ "$DRY_RUN" = true ]; then
        dry ".mas-mode = Set .mas-mode = framework"
    else
        echo "framework" > "$INSTALL_DIR/.mas-mode" 2>/dev/null || true
        ok ".mas-mode = framework"
    fi
    
    # 5. Summary
    if [ "$DRY_RUN" = false ]; then
        info "Installation complete: $COPIED copied, $SKIPPED skipped"
        echo ""
        echo -e "${YELLOW}${BOLD}⚠️  RESTART REQUIRED${NC}"
        echo -e "${YELLOW}MAS has been installed. remainderart Goose.${NC}"
        echo ""
        echo "Then: goose run --recipe dev-mas-engineer to start"
    fi
}

# ─── STATUS ───────────────────────────────────────────────────
show_status() {
    header "STATUS: Distribution ↔ ~/.config/goose/"
    echo ""
    [ -f "$SRC_MAS_RECIPE" ] && ok "Distribution: dev-mas-engineer.yaml" || warn "Distribution: MAS missing!"
    [ -f "$DST_MAS_RECIPE" ] && ok "~/.config:   dev-mas-engineer.yaml" || warn "~/.config:   MAS not installed"
    
    local src_sub=0 dst_sub=0
    for f in "$SRC_MAS_SUB"/sub_mas-*.yaml; do [ -f "$f" ] && src_sub=$((src_sub+1)); done
    for f in "$DST_MAS_SUB"/sub_mas-*.yaml; do [ -f "$f" ] && dst_sub=$((dst_sub+1)); done
    [ "$src_sub" -gt 0 ] && ok "Distribution: $src_sub Sub-Agenten" || warn "Distribution: No sub-agents"
    [ "$dst_sub" -gt 0 ] && ok "~/.config:   $dst_sub Sub-Agenten" || warn "~/.config:   No sub-agents installiert"
    
    local src_tools=0 dst_tools=0
    for f in "$SRC_MAS_TOOLS"/dev_*.py; do [ -f "$f" ] && src_tools=$((src_tools+1)); done
    for f in "$DST_MAS_TOOLS"/dev_*.py; do [ -f "$f" ] && dst_tools=$((dst_tools+1)); done
    ok "Distribution: $src_tools Tools"
    [ "$dst_tools" -gt 0 ] && ok "~/.config:   $dst_tools Tools" || warn "~/.config:   No tools installed"
    
    [ -f "$SRC_MAS_STATE/workflows.yaml" ] && ok "Distribution: SOT (workflows.yaml)" || warn "Distribution: SOT missing"
    [ -f "$DST_MAS_STATE/workflows.yaml" ] && ok "~/.config:   SOT present" || warn "~/.config:   SOT not installed"
}

# ─── HELP ─────────────────────────────────────────────────────
show_help() {
    echo ""
    echo -e "${BOLD}install.sh — MAS-Engineer Installer v1.0.0${NC}"
    echo ""
    echo "Installs MAS-Engineer from the ZIP distribution"
    echo "into ~/.config/goose/ so Goose can use it directly."
    echo ""
    echo -e "${BOLD}Steps:${NC}"
    echo "  1. Unzip:  unzip mas-framework-*.zip -d ~/mas-install"
    echo "  2. Install:   cd ~/mas-install && ./install.sh"
    echo "  3. Start Goose:  goose run --recipe dev-mas-engineer"
    echo ""
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./install.sh              → Install (Default)"
    echo "  ./install.sh --status     → Show status"
    echo "  ./install.sh --dry-run    → Only check, don't copy"
    echo "  ./install.sh --help       → This help"
    echo ""
}

# ─── MAIN ─────────────────────────────────────────────────────
main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --mas) shift ;;  # Default, ignored
            --dry-run|--test) DRY_RUN=true; shift ;;
            --status) show_status; exit 0 ;;
            --help|-h) show_help; exit 0 ;;
            *) echo -e "${RED}Unknown: $1${NC}"; show_help; exit 1 ;;
        esac
    done

    echo -e "${BOLD}"
    echo "╔════════════════════════════════════════════════════╗"
    echo "║        MAS-Engineer Installer v1.0.0              ║"
    echo "╚════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "Direction: Distribution  →  ~/.config/goose/"
    [ "$DRY_RUN" = true ] && echo -e "${YELLOW}Mode:  DRY-RUN${NC}"
    echo ""

    install_mas

    if [ "$DRY_RUN" = false ]; then
        [ $ERRORS -gt 0 ] && { error "$ERRORS errors"; exit 1; }
    fi
}

main "$@"
