#!/usr/bin/env bash
# mas-reinstall.sh — Reinstall MAS-Engineer recipes/config in goose
#
# Per user rule (2026-07-19): MAS aus goose deinstallieren und neueste
# Version installieren.
#
# This script does NOT touch the goose binary itself. It only:
#   1. Removes the currently-installed MAS recipes from ~/.config/goose/
#   2. Installs the latest MAS recipes from this workspace
#
# Usage:
#   ./scripts/mas-reinstall.sh
#
# Returns:
#   0 — uninstall + install succeeded
#   1 — any step failed

set -e

cd "$(dirname "$0")/.."
ROOT=$(pwd)

GOOSE_CONFIG_DIR="${HOME}/.config/goose"
RECIPES_DIR="${GOOSE_CONFIG_DIR}/recipes"
SUB_RECIPES_DIR="${RECIPES_DIR}/sub"

echo "================================================================"
echo "MAS REINSTALL — ${ROOT}"
echo "Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================================"

# -----------------------------------------------------------------
# Step 1: Uninstall old MAS recipes
# -----------------------------------------------------------------
echo ""
echo "[1/4] Uninstall old MAS recipes from goose"

# Remove only the MAS-installed files (preserves any other user recipes
# that may live in the same directory)
if [ -d "$RECIPES_DIR" ]; then
  # Remove root-level recipes (files from recipe/*.yaml in source)
  for f in "$RECIPES_DIR"/*.yaml; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    if [ -f "recipe/$base" ]; then
      rm -f "$f"
      echo "  removed root recipe: $base"
    fi
  done
  # Remove sub-recipes (files from recipe/sub/*.yaml in source)
  if [ -d "$SUB_RECIPES_DIR" ]; then
    for f in "$SUB_RECIPES_DIR"/*.yaml; do
      [ -e "$f" ] || continue
      base=$(basename "$f")
      if [ -f "recipe/sub/$base" ]; then
        rm -f "$f"
        echo "  removed sub recipe: $base"
      fi
    done
  fi
else
  echo "  no existing recipes dir — skip"
fi

# Remove MAS-specific config files
for f in .goosehints .mas-mode; do
  if [ -f "${GOOSE_CONFIG_DIR}/$f" ]; then
    rm -f "${GOOSE_CONFIG_DIR}/$f"
    echo "  removed config file: $f"
  fi
done

echo "  uninstall complete"

# -----------------------------------------------------------------
# Step 2: Install new MAS recipes
# -----------------------------------------------------------------
echo ""
echo "[2/4] Install new MAS recipes to goose"
mkdir -p "$SUB_RECIPES_DIR"

# Copy root recipes
ROOT_COUNT=0
for f in recipe/*.yaml; do
  [ -f "$f" ] || continue
  base=$(basename "$f")
  cp "$f" "$RECIPES_DIR/$base"
  ROOT_COUNT=$((ROOT_COUNT + 1))
done
echo "  installed $ROOT_COUNT root recipes"

# Copy sub-recipes
SUB_COUNT=0
for f in recipe/sub/*.yaml; do
  [ -f "$f" ] || continue
  base=$(basename "$f")
  cp "$f" "$SUB_RECIPES_DIR/$base"
  SUB_COUNT=$((SUB_COUNT + 1))
done
echo "  installed $SUB_COUNT sub-recipes"

# Copy .goosehints and .mas-mode
for f in .goosehints .mas-mode; do
  if [ -f "$f" ]; then
    cp "$f" "${GOOSE_CONFIG_DIR}/$f"
    echo "  installed config file: $f"
  fi
done

# -----------------------------------------------------------------
# Step 3: Verify recipe count
# -----------------------------------------------------------------
echo ""
echo "[3/4] Verify installation"
INSTALLED_ROOT=$(ls "$RECIPES_DIR"/*.yaml 2>/dev/null | wc -l)
INSTALLED_SUB=$(ls "$SUB_RECIPES_DIR"/*.yaml 2>/dev/null | wc -l)
echo "  expected root recipes: $ROOT_COUNT, installed: $INSTALLED_ROOT"
echo "  expected sub recipes:  $SUB_COUNT, installed: $INSTALLED_SUB"

if [ "$ROOT_COUNT" -ne "$INSTALLED_ROOT" ] || [ "$SUB_COUNT" -ne "$INSTALLED_SUB" ]; then
  echo "  ❌ count mismatch — install incomplete"
  exit 1
fi
echo "  ✅ all recipes installed"

# -----------------------------------------------------------------
# Step 4: Goose binary check (do NOT modify, just verify)
# -----------------------------------------------------------------
echo ""
echo "[4/4] Verify goose binary (read-only — do not modify)"
if command -v goose >/dev/null 2>&1; then
  echo "  ✅ goose installed: $(goose --version)"
else
  echo "  ❌ goose NOT in PATH"
  exit 1
fi

echo ""
echo "================================================================"
echo "MAS REINSTALL COMPLETE"
echo "  Root recipes: $INSTALLED_ROOT → $RECIPES_DIR"
echo "  Sub recipes:  $INSTALLED_SUB → $SUB_RECIPES_DIR"
echo "  Goose binary: $(goose --version 2>/dev/null || echo 'NOT FOUND') (untouched)"
echo "================================================================"
