#!/bin/bash
# mas_e2e_pty_test.sh — Reproducible e2e test of all 129 mas-engineer recipes
# Tests every recipe in goose-cli PTY, captures logs, produces pass/fail report.
#
# Usage:
#   source /workspace/dev-branch/mas-engineer/.env   # exports DEEPSEEK_API_KEY
#   bash tools/mas_e2e_pty_test.sh                   # runs all 129
#   bash tools/mas_e2e_pty_test.sh <recipe-name>     # runs one (substring match)
#
# Output:
#   e2e-results/<date>-mas-pty-129/evidence/<recipe>.log
#   e2e-results/<date>-mas-pty-129/SUMMARY.txt
#   e2e-results/<date>-mas-pty-129/RESULT.md
#
# Pre-conditions (from goose-cli-e2e-testing skill):
#   1. DEEPSEEK_API_KEY exported in env (32 hex chars after sk-)
#   2. OPENAI_HOST=https://api.deepseek.com   (NO /v1)
#   3. GOOSE_MODEL=deepseek-v4-flash
#   4. GOOSE_PROVIDER=openai
#   5. GOOSE_TELEMETRY_ENABLED=false
#   6. PATH includes /root/.local/bin (for goose binary)

set -e
set -o pipefail

# ---- pre-flight checks (gotcha #16, #20) ----
if [ -z "$DEEPSEEK_API_KEY" ] || [ "$DEEPSEEK_API_KEY" = "***" ]; then
  echo "FATAL: DEEPSEEK_API_KEY not set or is placeholder" >&2
  echo "  source mas-engineer/.env first" >&2
  exit 1
fi

# real-key check via curl (gotcha #2, #3c)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  https://api.deepseek.com/v1/models)
if [ "$HTTP_CODE" != "200" ]; then
  echo "FATAL: deepseek API returns $HTTP_CODE (key invalid/revoked?)" >&2
  exit 1
fi

# OPENAI_API_KEY shim (gotcha #2, #18)
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "***" ]; then
  export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
fi

# OPENAI_HOST (gotcha #3b — NO /v1!)
if [ -z "$OPENAI_HOST" ]; then
  export OPENAI_HOST="https://api.deepseek.com"
fi
# defensive: strip trailing /v1 if present
export OPENAI_HOST="${OPENAI_HOST%/v1}"

# GOOSE_MODEL (gotcha #3 — use deepseek-v4-flash, NOT deepseek-chat)
export GOOSE_MODEL="${GOOSE_MODEL:-deepseek-v4-flash}"
export GOOSE_PROVIDER="${GOOSE_PROVIDER:-openai}"
export GOOSE_TELEMETRY_ENABLED="${GOOSE_TELEMETRY_ENABLED:-false}"

# goose in PATH (gotcha #8)
export PATH="/root/.local/bin:$PATH"
if ! command -v goose >/dev/null 2>&1; then
  echo "FATAL: goose not in PATH" >&2
  exit 1
fi

# ---- paths ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECIPE_LIST="$MAS_ROOT/tools/mas_e2e_pty_test_recipes.txt"
TEST_DATE="$(date +%F)"
RUN_DIR="$MAS_ROOT/e2e-results/${TEST_DATE}-mas-pty-129"
EVIDENCE_DIR="$RUN_DIR/evidence"
mkdir -p "$EVIDENCE_DIR"

echo "=========================================="
echo "mas-engineer e2e PTY test (129 recipes)"
echo "  date:      $TEST_DATE"
echo "  run_dir:   $RUN_DIR"
echo "  model:     $GOOSE_MODEL"
echo "  host:      $OPENAI_HOST"
echo "  key-len:   ${#DEEPSEEK_API_KEY}"
echo "=========================================="

# ---- filter (optional: run only matching recipes) ----
FILTER="${1:-}"
get_recipes() {
  while IFS= read -r recipe; do
    [ -z "$recipe" ] && continue
    [[ "$recipe" =~ ^#.* ]] && continue   # skip comment lines
    if [ -n "$FILTER" ]; then
      echo "$recipe" | grep -q "$FILTER" || continue
    fi
    echo "$recipe"
  done < "$RECIPE_LIST"
}

# ---- run one recipe in PTY (gotcha #4) ----
run_recipe() {
  local recipe_path="$1"
  local name
  name=$(basename "$recipe_path" .yaml)
  local log="$EVIDENCE_DIR/${name}.log"
  local marker_file="$EVIDENCE_DIR/${name}.marker"
  local start_time
  start_time=$(date +%s)

  # 5-min timeout per recipe (gotcha #7 — some recipes take 3-5min)
  # Use script -qec with bash -c to ensure bash features work (gotcha #19)
  bash -c "source '$MAS_ROOT/.env' && export OPENAI_API_KEY='$DEEPSEEK_API_KEY' && export OPENAI_HOST='$OPENAI_HOST' && export GOOSE_MODEL='$GOOSE_MODEL' && export GOOSE_PROVIDER='$GOOSE_PROVIDER' && export GOOSE_TELEMETRY_ENABLED='$GOOSE_TELEMETRY_ENABLED' && timeout 300 goose run --recipe '$recipe_path' --no-session" \
    > "$log" 2>&1 || true   # ignore non-zero; check log content instead

  local end_time
  end_time=$(date +%s)
  local duration=$((end_time - start_time))

  # pass/fail detection (gotcha #17 — check log content, not exit code)
  local status
  if grep -qE "(401|Unauthorized|Authentication failed|Invalid API key)" "$log"; then
    status="FAIL_AUTH"
  elif grep -qE "(recipe not found|recipe_not_found|FileNotFoundError.*recipe)" "$log"; then
    status="FAIL_NOTFOUND"
  elif grep -qE "(PASSED|✓|✅|ALL CHECKS PASSED|successfully completed|completed successfully)" "$log"; then
    status="PASS"
  elif [ ! -s "$log" ]; then
    status="FAIL_EMPTY"
  elif grep -qE "(Error|Exception|Traceback)" "$log"; then
    status="FAIL_ERROR"
  else
    status="UNKNOWN"
  fi

  echo "$status $duration $name" >> "$RUN_DIR/_results.tsv"
  printf "  %-12s %4ds  %s\n" "$status" "$duration" "$name"
}

# ---- main loop ----
echo "" > "$RUN_DIR/_results.tsv"
echo "Running $(get_recipes | wc -l) recipes..."
echo ""
TOTAL_START=$(date +%s)
while IFS= read -r recipe; do
  full_path="$MAS_ROOT/$recipe"
  if [ ! -f "$full_path" ]; then
    echo "  MISSING     --    $recipe (file not found)"
    echo "MISSING 0 $recipe" >> "$RUN_DIR/_results.tsv"
    continue
  fi
  run_recipe "$full_path"
done < <(get_recipes)

TOTAL_END=$(date +%s)
TOTAL_DURATION=$((TOTAL_END - TOTAL_START))

# ---- summary ----
echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
PASS=$(awk '$1=="PASS"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
FAIL_AUTH=$(awk '$1=="FAIL_AUTH"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
FAIL_NOTFOUND=$(awk '$1=="FAIL_NOTFOUND"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
FAIL_EMPTY=$(awk '$1=="FAIL_EMPTY"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
FAIL_ERROR=$(awk '$1=="FAIL_ERROR"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
UNKNOWN=$(awk '$1=="UNKNOWN"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
MISSING=$(awk '$1=="MISSING"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
TOTAL=$(awk 'END{print NR}' "$RUN_DIR/_results.tsv")
PCTA=$(( PASS * 100 / (TOTAL - 0) ))

cat > "$RUN_DIR/SUMMARY.txt" <<EOF
mas-engineer e2e PTY test — $TEST_DATE
=========================================
Total recipes:    $TOTAL
PASS:             $PASS  (${PCTA}%)
FAIL_AUTH:        $FAIL_AUTH
FAIL_NOTFOUND:    $FAIL_NOTFOUND
FAIL_EMPTY:       $FAIL_EMPTY
FAIL_ERROR:       $FAIL_ERROR
UNKNOWN:          $UNKNOWN
MISSING:          $MISSING
Total duration:   ${TOTAL_DURATION}s

Per-recipe results (sorted by status):
EOF
sort "$RUN_DIR/_results.tsv" >> "$RUN_DIR/SUMMARY.txt"

cat "$RUN_DIR/SUMMARY.txt"
echo ""
echo "Logs: $EVIDENCE_DIR"
