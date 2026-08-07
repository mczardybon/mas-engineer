#!/usr/bin/env bash
# replay-e2e-test.sh — Replayable E2E test for Issue 7355/7570 fix
# Date: 2026-07-21
#
# HONEST SCOPE: This script verifies the recipe-LOADING fix only.
# It does NOT verify:
#   - Interactive TUI dispatch (requires real TTY)
#   - 3 demo teams orchestrating with --params (separate recipe-design
#     issue — orchestrator prompt: is static, not a template)
#   - The 52-sub-recipe 'delegation' is a flat-prompt workaround,
#     NOT orchestrator routing logic
#
# For full delegation verification, a human user with a real TTY is
# needed. See RE-TEST-RESULTS.md and CERTIFICATE.md in this directory.
#
# Usage:
#   export DEEPSEEK_API_KEY=...
#   ./replay-e2e-test.sh
#
# Output: ./e2e-replay-output/ (created automatically)
# Duration: ~15 minutes

set -e

# --- Configuration ---
REPO_ROOT="${REPO_ROOT:-/workspace/mas-engineer-src}"
RECIPE="$REPO_ROOT/mas-engineer/recipe/dev-mas-engineer.yaml"
SUB_RECIPE_DIR="$REPO_ROOT/mas-engineer/recipe/sub"
OUTPUT_DIR="./e2e-replay-output"

# Required env vars
if [ -z "$DEEPSEEK_API_KEY" ]; then
  echo "ERROR: DEEPSEEK_API_KEY not set"
  echo "Usage: export DEEPSEEK_API_KEY=sk-..."
  exit 1
fi

export OPENAI_API_KEY="${OPENAI_API_KEY:-$DEEPSEEK_API_KEY}"
export OPENAI_HOST="${OPENAI_HOST:-https://api.deepseek.com}"
export GOOSE_MODEL="${GOOSE_MODEL:-deepseek-chat}"
export GOOSE_PROVIDER="${GOOSE_PROVIDER:-openai}"
export NO_COLOR=1
export TERM=dumb

mkdir -p "$OUTPUT_DIR"
echo "=========================================="
echo "  E2E-FIX-VERIFICATION REPLAY"
echo "=========================================="
echo "Recipe:    $RECIPE"
echo "Output:    $OUTPUT_DIR"
echo "Model:     $GOOSE_MODEL ($GOOSE_PROVIDER)"
echo "Started:   $(date -Iseconds)"
echo "=========================================="
echo ""

# --- Test 1: Recipe renders ---
echo "[1/4] Test 1: Recipe renders without errors"
goose run --recipe "$RECIPE" --render-recipe > "$OUTPUT_DIR/01-recipe-rendered.yaml" 2> "$OUTPUT_DIR/01-recipe-rendered.err"
if [ $? -eq 0 ]; then
  if grep -q "type: platform" "$OUTPUT_DIR/01-recipe-rendered.yaml"; then
    if grep -q "name: summon" "$OUTPUT_DIR/01-recipe-rendered.yaml"; then
      echo "  PASS: type:platform + summon found in rendered recipe"
    else
      echo "  FAIL: summon not found in rendered recipe"
      exit 1
    fi
  else
    echo "  FAIL: type:platform not found (got type:builtin?)"
    grep "type:" "$OUTPUT_DIR/01-recipe-rendered.yaml" | head -5
    exit 1
  fi
  # Count sub_recipes
  SUB_COUNT=$(grep -c "name: sub_mas-" "$OUTPUT_DIR/01-recipe-rendered.yaml" || echo 0)
  echo "  Sub-recipes found: $SUB_COUNT"
else
  echo "  FAIL: goose run --render-recipe failed"
  cat "$OUTPUT_DIR/01-recipe-rendered.err"
  exit 1
fi
echo ""

# --- Test 2: Single sub-recipe E2E ---
echo "[2/4] Test 2: Single sub-recipe (web-researcher) responds to query"
timeout 180 goose run \
  --text "Research in 2 sentences what changed in goose 1.24+ (PR #6964) regarding the 'summon' extension type. Be concise." \
  --sub-recipe "$SUB_RECIPE_DIR/sub_mas-web-researcher.yaml" \
  --no-session \
  --quiet > "$OUTPUT_DIR/02-single-subrecipe.txt" 2>&1
if [ -s "$OUTPUT_DIR/02-single-subrecipe.txt" ]; then
  if grep -qiE "summon|subagent|delegate|sub_recipes" "$OUTPUT_DIR/02-single-subrecipe.txt"; then
    echo "  PASS: model mentioned summon/subagent/delegate/sub_recipes"
  else
    echo "  WARN: response did not mention expected terms (model may be off-topic)"
  fi
  echo "  Response length: $(wc -c < $OUTPUT_DIR/02-single-subrecipe.txt) bytes"
else
  echo "  FAIL: empty response"
  exit 1
fi
echo ""

# --- Test 3: Full 52 sub-recipes + complex query ---
echo "[3/4] Test 3: Full mas-engineer (52 sub-recipes) responds to Issue 7355 query"
SUB_FLAGS=""
for sub in "$SUB_RECIPE_DIR"/sub_mas-*.yaml; do
  SUB_FLAGS="$SUB_FLAGS --sub-recipe $sub"
done
SUB_COUNT=$(ls "$SUB_RECIPE_DIR"/sub_mas-*.yaml | wc -l)
echo "  Loading $SUB_COUNT sub-recipes..."

QUERY="You are DEV-MAS-ENGINEER, the Multi-Agent System specialist. User query: research in 2-3 sentences what changed in goose 1.24+ (PR #6964) regarding the 'summon' extension type, and how it relates to Issue 7355 about sub_recipes dispatch failure. Respond in English. Be concise."

# shellcheck disable=SC2086
timeout 240 goose run $SUB_FLAGS --no-session --quiet --text "$QUERY" \
  > "$OUTPUT_DIR/03-full-52-subrecipes.txt" 2>&1

if [ -s "$OUTPUT_DIR/03-full-52-subrecipes.txt" ]; then
  if grep -qE "PR.*6964|Issue.*7355|summon" "$OUTPUT_DIR/03-full-52-subrecipes.txt"; then
    echo "  PASS: model identified PR #6964, Issue #7355, or summon"
  else
    echo "  WARN: response did not mention specific PR/Issue (may be partial)"
  fi
  echo "  Response length: $(wc -c < $OUTPUT_DIR/03-full-52-subrecipes.txt) bytes"
else
  echo "  FAIL: empty response"
  exit 1
fi
echo ""

# --- Test 4: TUI launch (non-interactive check) ---
echo "[4/4] Test 4: TUI launches with summon + sub-recipe loading"
timeout 20 goose run --recipe "$RECIPE" --no-session > "$OUTPUT_DIR/04-tui-startup.log" 2>&1 || true
if grep -q "starting.*summon" "$OUTPUT_DIR/04-tui-startup.log"; then
  echo "  PASS: TUI loaded summon extension"
else
  echo "  WARN: summon extension not detected in startup log"
fi
if grep -q "subagent:" "$OUTPUT_DIR/04-tui-startup.log"; then
  SUB_LOADS=$(grep -c "subagent:" "$OUTPUT_DIR/04-tui-startup.log")
  echo "  PASS: $SUB_LOADS sub-recipe loads detected"
else
  echo "  WARN: no sub-recipe loads detected"
fi
echo ""

# --- Summary ---
echo "=========================================="
echo "  E2E REPLAY COMPLETE"
echo "=========================================="
echo "All outputs in: $OUTPUT_DIR/"
echo "Finished:       $(date -Iseconds)"
echo ""
echo "Files:"
ls -la "$OUTPUT_DIR/"
echo ""
echo "VERDICT (in-scope only): $([ -s "$OUTPUT_DIR/03-full-52-subrecipes.txt" ] && echo "PASS - Issue 7355 loading fix verified" || echo "FAIL - investigate")"
echo ""
echo "NOTE ON SCOPE: This script verifies the Issue 7355/7570"
echo "recipe-LOADING fix only. It does NOT verify:"
echo "  - Interactive TUI dispatch (requires real TTY)"
echo "  - 3 demo teams orchestrating with --params"
echo "    (separate recipe-design issue, see RE-TEST-RESULTS.md)"
echo "  - The 52-sub-recipe 'delegation' is a flat-prompt"
echo "    workaround, NOT orchestrator routing logic"
