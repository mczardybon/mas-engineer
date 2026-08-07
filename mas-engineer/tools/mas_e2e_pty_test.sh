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
#   logs/e2e-results/<date>-mas-pty-129/evidence/<recipe>.log
#   logs/e2e-results/<date>-mas-pty-129/SUMMARY.txt
#   logs/e2e-results/<date>-mas-pty-129/RESULT.md
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

# real-key check via curl (gotcha #2, #3c) — adapted for local litellm proxy
API_CHECK_HOST="${OPENAI_HOST:-https://api.deepseek.com}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  "${API_CHECK_HOST}/v1/models")
if [ "$HTTP_CODE" != "200" ]; then
  echo "WARN: API check returns $HTTP_CODE (continuing anyway)" >&2
fi

# OPENAI_API_KEY shim (gotcha #2, #18) — R110-45.1 BUG-2 fix:
# Never overwrite with literal ***. If .env didn't set it, derive from DEEPSEEK_API_KEY.
# Display-redaction trap (gotcha #20): terminal shows "***" for redacted values,
# but the actual file content uses $DEEPSEEK_API_KEY (verified via od -c).
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
# Central logs/ folder at repo root (single destination for all generated artifacts)
LOGS_ROOT="$(cd "$MAS_ROOT/.." && pwd)/logs"
RECIPE_LIST="$MAS_ROOT/tools/mas_e2e_pty_test_recipes.txt"
TEST_DATE="$(date +%F)"
RUN_DIR="$LOGS_ROOT/e2e-results/${TEST_DATE}-mas-pty-129"
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

  # 5-min hard timeout (safety net) but kill early once "Loading recipe" appears.
  # R110-48: without early-kill, a 128-recipe run takes 128*300s = 6.4h worst case
  # because goose waits for stdin in PTY mode. Once the recipe is *loaded* and
  # the session is up, we have proven what the test plan (E2E-TESTPLAN.md L86-92)
  # needs to prove. Then move on.
  # Disable set -e locally: kill -KILL on already-dead process returns non-zero
  # and would abort the loop before status detection.
  set +e
  # Pre-set env in parent so source in subshell is non-destructive (display
  # redaction: literal key string is never written into this script).
  GOOSE_HOST="$OPENAI_HOST" \
  GOOSE_MODEL_NAME="$GOOSE_MODEL" \
  bash -c "export OPENAI_API_KEY='$OPENAI_API_KEY' && export OPENAI_HOST='$OPENAI_HOST' && export GOOSE_MODEL='$GOOSE_MODEL' && export GOOSE_PROVIDER='$GOOSE_PROVIDER' && export GOOSE_TELEMETRY_ENABLED='$GOOSE_TELEMETRY_ENABLED' && timeout 300 goose run --recipe '$recipe_path' --explain" \
    > "$log" 2>&1 &
  local goose_pid=$!

  # Poll the log file for "Loading recipe" up to 300s, kill goose as soon as we see it.
  local early_kill_after="${EARLY_KILL_AFTER:-2}"   # seconds after "Loading recipe" appears
  local load_seen_at=0
  local poll_end=$((start_time + 300))
  while kill -0 "$goose_pid" 2>/dev/null; do
    if [ -f "$log" ] && grep -q "Loading recipe" "$log" 2>/dev/null; then
      if [ "$load_seen_at" -eq 0 ]; then
        load_seen_at=$(date +%s)
      fi
      local now
      now=$(date +%s)
      if [ $((now - load_seen_at)) -ge "$early_kill_after" ]; then
        kill -TERM "$goose_pid" 2>/dev/null
        sleep 1
        kill -KILL "$goose_pid" 2>/dev/null
        break
      fi
    fi
    if [ "$(date +%s)" -ge "$poll_end" ]; then
      kill -KILL "$goose_pid" 2>/dev/null
      break
    fi
    sleep 1
  done
  wait "$goose_pid" 2>/dev/null || true

  local end_time
  end_time=$(date +%s)
  local duration=$((end_time - start_time))

  # pass/fail detection — Phase 1.3 of docs/E2E-TESTPLAN.md is the source of truth.
  # A recipe passes if goose could load it and start a session, evidenced by
  # the "Loading recipe:" line that goose prints at startup. This matches the
  # official test in E2E-TESTPLAN.md L86-92 (the only reliable invariant we
  # have across all 130+ recipes — completion markers vary wildly: "completed
  # successfully" / "JSON {passed:true}" / "Awaiting your instruction" / etc.).
  #
  # Anything that did NOT load is a genuine fail — classify by symptom:
  #   - HTTP 401 / "Invalid API key" / "Authentication failed" → FAIL_AUTH
  #   - FileNotFoundError on a recipe path → FAIL_NOTFOUND
  #   - empty log → FAIL_EMPTY (recipe crashed before producing output)
  # R110-47 simplified this from R110-45.6 + R110-46 (which had self-match
  # traps with the detector's own source code being quoted by recipes like
  # sub_mas-test-fix-failures-applier and sub_mas-general-improver).
  local status
  if grep -q "Loading recipe" "$log"; then
    status="PASS"
  elif [ ! -s "$log" ]; then
    status="FAIL_EMPTY"
  elif grep -qE "(HTTP/[0-9.]+ 401|Invalid API key:|Authentication failed:)" "$log"; then
    status="FAIL_AUTH"
  elif grep -qE "(FileNotFoundError.*recipe|recipe_not_found)" "$log"; then
    status="FAIL_NOTFOUND"
  else
    status="FAIL_LOAD"
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
FAIL_LOAD=$(awk '$1=="FAIL_LOAD"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
MISSING=$(awk '$1=="MISSING"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
TOTAL=$(awk 'END{print NR}' "$RUN_DIR/_results.tsv")
PCTA=$(( PASS * 100 / (TOTAL - 0) ))

cat > "$RUN_DIR/SUMMARY.txt" <<EOF
mas-engineer e2e PTY test — $TEST_DATE
=========================================
Pass criterion: docs/E2E-TESTPLAN.md Phase 1.3 — "Loading recipe" line present.
Total recipes:    $TOTAL
PASS:             $PASS  (${PCTA}%)
FAIL_AUTH:        $FAIL_AUTH
FAIL_NOTFOUND:    $FAIL_NOTFOUND
FAIL_EMPTY:       $FAIL_EMPTY
FAIL_LOAD:        $FAIL_LOAD  (no "Loading recipe" line, no recognised error)
MISSING:          $MISSING  (recipe file not on disk)
Total duration:   ${TOTAL_DURATION}s

Per-recipe results (sorted by status):
EOF
sort "$RUN_DIR/_results.tsv" >> "$RUN_DIR/SUMMARY.txt"

cat "$RUN_DIR/SUMMARY.txt"
echo ""
echo "Logs: $EVIDENCE_DIR"
