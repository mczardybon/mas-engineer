#!/bin/bash
# dev_autobuild.sh — Automatischer Distribution-Builder v2.0.0
# =======================================================
# Will after jedem git commit automatically started.
# Nutzt dev_build.sh --dry-run + manifest.yaml (equale Logik).
#
# Usage:
#   ./mas-engineer/tools/dev_autobuild.sh                  → Auto-Build (checks + baut)
#   ./mas-engineer/tools/dev_autobuild.sh --force          → Always bauen
#   ./mas-engineer/tools/dev_autobuild.sh --status         → Only check
#   ./mas-engineer/tools/dev_autobuild.sh --install        → Bauen + update.sh --mas
#   ./mas-engineer/tools/dev_autobuild.sh --help           → Hilfe
# =======================================================

set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
DIST_DIR="$WORKSPACE/dist"
TOOLS_DIR="$WORKSPACE/mas-engineer/tools"
CHANGES_FILE="$WORKSPACE/mas-engineer/.state/changes.json"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✔${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
info() { echo -e "  ${BLUE}ℹ${NC} $1"; }
err()  { echo -e "  ${RED}✘${NC} $1"; }

show_help() {
    echo ""
    echo -e "${BOLD}dev_autobuild.sh v2.0.0 — Auto-Distribution-Builder${NC}"
    echo ""
    echo "Usage:"
    echo "  ./mas-engineer/tools/dev_autobuild.sh              Auto-Build (checks + baut)"
    echo "  ./mas-engineer/tools/dev_autobuild.sh --force      Always bauen"
    echo "  ./mas-engineer/tools/dev_autobuild.sh --status     Only check"
    echo "  ./mas-engineer/tools/dev_autobuild.sh --install    Bauen + update.sh --mas"
    echo "  ./mas-engineer/tools/dev_autobuild.sh --help       This help"
    echo ""
}

needs_build() {
    local latest_build_zip
    latest_build_zip=$(ls -t "$DIST_DIR"/mas-framework-*.zip 2>/dev/null | head -1)
    
    if [ -z "$latest_build_zip" ]; then
        return 0
    fi
    
    local last_commit
    last_commit=$(git -C "$WORKSPACE" log -1 --format=%ct 2>/dev/null || echo "0")
    
    local build_name
    build_name=$(basename "$latest_build_zip")
    local build_date_str
    build_date_str=$(echo "$build_name" | sed 's/.*_\([0-9]\{8\}\)_\([0-9]\{6\}\)\..*/\1 \2/')
    local build_ts
    build_ts=$(date -d "$build_date_str" +%s 2>/dev/null || echo "0")
    
    if [ "$last_commit" -gt "$build_ts" ]; then
        return 0
    fi
    return 1
}

show_status() {
    echo ""
    echo "  ─── Auto-Build Status ───"
    local latest_zip
    latest_zip=$(ls -t "$DIST_DIR"/mas-framework-*.zip 2>/dev/null | head -1)
    if [ -n "$latest_zip" ]; then
        local zip_name; zip_name=$(basename "$latest_zip")
        local zip_size; zip_size=$(du -h "$latest_zip" | cut -f1)
        local zip_count; zip_count=$(unzip -l "$latest_zip" 2>/dev/null | tail -1 | awk '{print $2}')
        ok "Letztes ZIP: $zip_name ($zip_count files, $zip_size)"
    else
        warn "No ZIP present"
    fi
    ok "ZIPs total: $(ls "$DIST_DIR"/mas-framework-*.zip 2>/dev/null | wc -l)"
    ok "commits: $(git -C "$WORKSPACE" log --oneline 2>/dev/null | wc -l || echo "0")"
    if needs_build; then
        warn "Build needed! Letzter commit ist new als letztes ZIP."
    else
        ok "No Build needed"
    fi
}

# ══════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🔧 Auto-Distribution-Builder v2.0.0             ${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

MODE="${1:-auto}"

case "$MODE" in
    --help|-h)
        show_help
        ;;
    --status)
        show_status
        ;;
    --force)
        info "Force-Build"
        # equaler Build wie dev_build.sh
        bash "$TOOLS_DIR/dev_build.sh"
        ;;
    --install)
        bash "$TOOLS_DIR/dev_build.sh" && bash "$WORKSPACE/update.sh" --mas
        ;;
    auto|--auto)
        if needs_build; then
            info "Build needed — start dev_build.sh"
            bash "$TOOLS_DIR/dev_build.sh"
        else
            ok "No Build needed"
            show_status
        fi
        ;;
    *)
        err "Unbekannt: $1"
        show_help; exit 1
        ;;
esac
