#!/bin/bash
# dev_build.sh — Distribution Builder v3.0.0
# ==============================================================
# Baut ZIP 1:1 aus Workspace-Struktur.
# NUR Build — no Installation (dafor givet's install.sh + update.sh).
#
# Usage:
#   ./mas-engineer/tools/dev_build.sh                    → ZIP bauen
#   ./mas-engineer/tools/dev_build.sh --full             → MAS + ALL frameworks
#   ./mas-engineer/tools/dev_build.sh --dry-run          → Only check
#   ./mas-engineer/tools/dev_build.sh --version x.y.z    → Version setn
#   ./mas-engineer/tools/dev_build.sh --help             → Hilfe
# ==============================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✔${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
error(){ echo -e "  ${RED}✘${NC} $1"; }
info() { echo -e "  ${BLUE}${BOLD}INFO${NC}  $1"; }
header(){ echo -e "\n${BLUE}${BOLD}━━━ $1 ━━━${NC}"; }
fail() { echo -e "  ${RED}${BOLD}ERROR${NC} $1"; exit 1; }

BUILD_WORKSPACE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Workspace detect: --workspace, traditionell (mas-engineer/), oder Port-Modus (flach)
if [ -n "$BUILD_WORKSPACE" ]; then
    WORKSPACE="$BUILD_WORKSPACE"
elif [ -d "$SCRIPT_DIR/../../mas-engineer" ]; then
    WORKSPACE="$(cd "$SCRIPT_DIR/../.." && pwd)"
else
    WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
DIST_DIR="$WORKSPACE/dist"
mkdir -p "$DIST_DIR"

FULL_MODE=false
DRY_RUN=false
PROJECT_MODE=""
VERSION=""

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --workspace) BUILD_WORKSPACE="$2"; shift 2 ;;
            --full|--mas) FULL_MODE=true; shift ;;
            --dry-run|--test) DRY_RUN=true; shift ;;
            --project) PROJECT_MODE="$2"; shift 2 ;;
            --version) VERSION="$2"; shift 2 ;;
            --help|-h) show_help; exit 0 ;;
            *) error "Unbekannt: $1"; show_help; exit 1 ;;
        esac
    done
}

show_help() {
    echo ""
    echo -e "${BOLD}dev_build.sh v3.0.0 — Distribution Builder${NC}"
    echo ""
    echo "Baut ZIP 1:1 aus Workspace-Struktur."
    echo "NUR Build — no Installation."
    echo ""
    echo "Usage:"
    echo "  ./mas-engineer/tools/dev_build.sh                    → ZIP bauen"
    echo "  ./mas-engineer/tools/dev_build.sh --full             → MAS + ALL Projekte"
    echo "  ./mas-engineer/tools/dev_build.sh --dry-run          → Only check"
    echo "  ./mas-engineer/tools/dev_build.sh --version x.y.z    → Version setn"
    echo ""
}

build_zip() {
    local timestamp; timestamp=$(date +%Y%m%d_%H%M%S)
    local zip_name="mas-framework-v${VERSION}_${timestamp}.zip"
    local zip_path="$DIST_DIR/$zip_name"

    header "Distribution bauen"
    echo "  Version: ${VERSION}"
    echo "  Modus:   MAS-only (no framework)"

    # Backup-directoryse ausclose
    find "$WORKSPACE/mas-engineer" -name "__pycache__" -typee d -exec rm -rf {} + 2>/dev/null || true
    rm -rf "$WORKSPACE/mas-engineer/.state/checkpoints" 2>/dev/null || true

    cd "$WORKSPACE"
    
    # Clean up
    find mas-engineer -typee d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    rm -f mas-engineer/.state/checkpoints/checkpoint_config.yaml 2>/dev/null || true
    
    # Build ZIP
    zip -r "$zip_path" .mas-mode install.sh mas-engineer/ \
        -x "*/.backups/*" "*/.git/*" "*/__pycache__/*" "*.pyc" "*.bak" \
        -x "mas-engineer/.state/checkpoints/*" \
        -x "mas-engineer/.state/workflow_runs/*" \
        -x "mas-engineer/tools/dev_build.sh.v*" -x "mas-engineer/dist/*" \
        -x "mas-engineer/recipe/sub/*.bak*" 2>&1 | grep -v "^  adding:" || true
    
    local zip_size; zip_size=$(du -h "$zip_path" | cut -f1)
    local zip_count; zip_count=$(unzip -l "$zip_path" 2>/dev/null | tail -1 | awk '{print $2}')
    ok "ZIP creates: $zip_name ($zip_count files, $zip_size)"
}

validate_zip() {
    local zip_path; zip_path=$(ls -t "$DIST_DIR"/mas-framework-*.zip 2>/dev/null | head -1)
    [ -n "$zip_path" ] || { error "No ZIP found"; return 1; }

    local errors=0

    header "ZIP validate"
    echo ""

    # 1. MAS-Subs (≥36 in sub/)
    echo -n "MAS-Subs:       "
    local mas_subs
    mas_subs=$(unzip -l "$zip_path" 2>/dev/null | grep -c "mas-engineer/recipe/sub/sub_mas-")
    [ "$mas_subs" -ge 36 ] && ok "✅ ($mas_subs)" || { error "❌ ($mas_subs)"; errors=$((errors + 1)); }

    # 2. MAS-Tools (≥40)
    echo -n "MAS-Tools:      "
    local mas_tools
    mas_tools=$(unzip -l "$zip_path" 2>/dev/null | grep -c "mas-engineer/tools/")
    [ "$mas_tools" -ge 40 ] && ok "✅ ($mas_tools)" || { error "❌ ($mas_tools)"; errors=$((errors + 1)); }

    # 6. install.sh
    echo -n "install.sh:     "
    unzip -l "$zip_path" 2>/dev/null | grep -c "install.sh$" > /dev/null && ok "✅" || { warn "⚠️ (optional)"; }

    # 7. No Pycache
    echo -n "No Pycache:   "
    local pycache
    pycache=$(unzip -l "$zip_path" 2>/dev/null | grep -c "__pycache__\|\.pyc" || true)
    [ "$pycache" -gt 0 ] && { error "❌ ($pycache)"; errors=$((errors + 1)); } || ok "✅"

    # 8. MAS-State (Rulen)
    echo -n "MAS-State:      "
    local state_count
    state_count=$(unzip -l "$zip_path" 2>/dev/null | grep -c "mas-engineer/.state/rules/")
    [ "$state_count" -ge 4 ] && ok "✅ ($state_count rules)" || { warn "❌ ($state_count)"; errors=$((errors + 1)); }

    echo ""
    if [ "$errors" -eq 0 ]; then
        ok "ZIP complete und korrekt — 0 Error"
    else
        error "$errors Error im ZIP"
    fi
    return $errors
}


build_project_zip() {
    local project_name="$1"
    local project_path="$WORKSPACE/$project_name"
    timestamp=$(date +%Y%m%d_%H%M%S)
    local zip_name="${project_name}-v${VERSION}_${timestamp}.zip"
    local zip_path="$DIST_DIR/$zip_name"

    header "Projekt-Distribution bauen"
    echo "  Projekt: $project_name"
    echo "  Version: ${VERSION}"

    # Check ob Projekt exists
    [ -d "$project_path" ] || fail "Projekt '$project_name' not found in $WORKSPACE"

    # Symlink aufloesen (tools/ -> echte files)
    if [ -L "$project_path/tools" ]; then
        local symlink_target
        symlink_target=$(readlink "$project_path/tools")
        info "Symlink found: $symlink_target"
        info "Loese Symlink auf -> copy Tools als echte files"
        rm -f "$project_path/tools"
        rsync -a "$symlink_target/" "$project_path/tools/" || cp -rL "$symlink_target" "$project_path/tools"
        ok "tools/ -> echte files (standalone)"
    fi

    # Backup-directoryse ausclose
    find "$project_path" -name "__pycache__" -typee d -exec rm -rf {} + 2>/dev/null || true

    # ZIP create
    cd "$WORKSPACE"
    zip -r "$zip_path" "$project_name/" \
        -x "*/\.backups/*" "*/\.git/*" "*/__pycache__/*" "*.pyc" "*.bak"
    ok "ZIP creates: $zip_name"

    # Check: no sub_mas-* im ZIP (ausser generatede)
    local mas_subs
    mas_subs=$(unzip -l "$zip_path" 2>/dev/null | grep -c "sub_mas-" || true)
    if [ "$mas_subs" -gt 0 ]; then
        warn "ZIP contains $mas_subs sub_mas-* files"
        warn "Projekt sollte no MAS-Components contain"
    else
        ok "No MAS-Components im ZIP — standalone"
    fi

    echo ""
    if [ "$DRY_RUN" = false ]; then
        echo -e "${YELLOW}${BOLD}📦 Projekt-Build completed${NC}"
        echo -e "${YELLOW}Installation: cd dist/ && unzip ${zip_name} && ${project_name}/installr.sh${NC}"
        echo -e "${YELLOW}No MAS-Dependency — standalone${NC}"
    fi
}


main() {
    parse_args "$@"
    [ -z "$VERSION" ] && VERSION="1.0.0"

    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║  Distribution Builder v3.0.0                ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo ""

    # Check Workspace
    echo "  ✅ MAS-only Modus (no framework)"
    [ -d "$WORKSPACE/mas-engineer" ] || [ -f "$WORKSPACE/recipe/dev-mas-engineer.yaml" ] || fail "Nicht im Workspace (mas-engineer/ oder recipe/dev-mas-engineer.yaml missing)"

    if [ -n "$PROJECT_MODE" ]; then
        build_project_zip "$PROJECT_MODE"
    else
        build_zip
    fi

    if [ "$DRY_RUN" = false ]; then
        validate_zip || exit 1
    fi

    echo ""
    if [ "$DRY_RUN" = true ]; then
        info "DRY-RUN completed. No Changeen."
    else
        echo -e "${YELLOW}${BOLD}📦 Build completed${NC}"
        echo -e "${YELLOW}Installation: cd dist/ && unzip mas-framework-*.zip && ./installr.sh${NC}"
        echo -e "${YELLOW}MAS-Update:   ./update.sh --mas${NC}"
        echo -e "${YELLOW}FW-Update:    ./update.sh --framework${NC}"
    fi
}

main "$@"
