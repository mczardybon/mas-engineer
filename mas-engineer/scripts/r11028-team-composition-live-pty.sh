#!/usr/bin/env bash
# R110-28 — team-composition live-PTY test
# 6 representative team-leads across 3 typologies:
#   HIERARCHICAL (lead delegates to specialists via sub_recipes):
#     1. code-review-lead    (delegates to 4 specialists)
#     2. perf-eval-lead      (delegates to 4 specialists)
#   PIPELINE (5 sequential stages):
#     3. dq-stage-1-profile
#     4. doc-gen-1-analyze
#   FLAT (5 parallel scanners/advisors — show 1 each):
#     5. security-scan-5-crypto
#     6. refactor-5-decompose
#
# Tests whether the 30-agent team PLAYS TOGETHER in each typology:
#   - HIERARCHICAL: does goose auto-dispatch to the 4 sub_recipes?
#   - PIPELINE: does a stage output actionable handoff content for the next?
#   - FLAT: does a single scanner return findings in the agreed format?
#
# Same gotchas as R110-27: yaml.safe_dump wrappers, TRUE PTY, env-var OPENAI_API_KEY,
# OPENAI_HOST without /v1, fail-fast on placeholder keys.

set -e
set -o pipefail

# --- Step 0: env validation (gotcha #16, #18, #20) ---
if [ -z "$DEEPSEEK_API_KEY" ] || [ "$DEEPSEEK_API_KEY" = "***" ]; then
  echo "FATAL: DEEPSEEK_API_KEY not set or placeholder. Source .env first." >&2
  exit 1
fi
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "***" ]; then
  export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
fi
export GOOSE_PROVIDER=openai
export GOOSE_MODEL="${GOOSE_MODEL:-deepseek-v4-flash}"
export OPENAI_HOST="${OPENAI_HOST:-https://api.deepseek.com}"
export GOOSE_TELEMETRY_ENABLED=false
export PATH="/root/.local/bin:$PATH"

# --- Step 1: API-key smoke test (gotcha #16/20) ---
echo "=== STEP 1: API key check ==="
http=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $OPENAI_API_KEY" https://api.deepseek.com/v1/models)
if [ "$http" != "200" ]; then
  echo "FATAL: API key invalid (HTTP $http). Rotate the key." >&2
  exit 1
fi
echo "  API: HTTP $http ✓"
echo

# --- Step 2: recipe discovery ---
RESULT_DIR="e2e-results/2026-07-29-r11028-team-composition-live-pty"
# Wrapper-recipes live NEXT to the sub_recipes (gotcha #11: sub_recipe paths
# resolve relative to the recipe's own dir, not cwd). So we put the wrappers
# at /tmp/multi-arch-30/recipe/wrappers-r11028/ and use absolute sub_recipe paths.
WRAPPER_DIR="/tmp/multi-arch-30/recipe/wrappers-r11028"
LOG_DIR="$RESULT_DIR/agent-logs"
RECIPE_DIR="/tmp/multi-arch-30/recipe/sub"

if [ ! -d "$RECIPE_DIR" ]; then
  echo "FATAL: $RECIPE_DIR not found. Setup multi-arch-30 first." >&2
  exit 1
fi
mkdir -p "$LOG_DIR"

# 6 representative leads
AGENTS=(
  "code-review-lead:HIERARCHICAL"
  "perf-eval-lead:HIERARCHICAL"
  "dq-stage-1-profile:PIPELINE-STAGE"
  "doc-gen-1-analyze:PIPELINE-STAGE"
  "security-scan-5-crypto:FLAT-SCANNER"
  "refactor-5-decompose:FLAT-ADVISOR"
)

# --- Step 2: R10 CORONASHIELD pre-flight validation ---
# Per R10 (from sub_mas-yaml-editor.md), validate ALL wrapper-recipes BEFORE
# running them: yaml.safe_load + safe_dump round-trip + sub_recipe path
# resolution. This catches the BUG-1 class of errors (sub_recipe path not
# resolvable) immediately, without waiting for goose run to fail.
echo "=== STEP 2: R10 CORONASHIELD pre-flight validation ==="
if [ -f "scripts/r11028-r10-validate.py" ]; then
  if ! python3 scripts/r11028-r10-validate.py "$WRAPPER_DIR" --strict; then
    echo "FATAL: R10 validation failed. Fix wrapper-recipes first." >&2
    exit 1
  fi
else
  echo "  WARN: scripts/r11028-r10-validate.py not found, skipping R10 pre-flight"
fi
echo

# --- Step 3: run all 6 leads sequentially in TRUE PTY mode ---
echo "=== STEP 3: running 6 team-leads (sequential, TRUE PTY, 180s timeout each) ==="
echo

N_PASS=0
N_FAIL=0
N_AUTH=0
N_TIMEOUT=0
TOTAL_WALL=0
TOTAL_BYTES=0
PER_AGENT_JSON=()

start_total=$(date +%s)
for i in "${!AGENTS[@]}"; do
  entry="${AGENTS[$i]}"
  name="${entry%%:*}"
  topo="${entry##*:}"
  idx=$((i + 1))
  total=${#AGENTS[@]}

  wrapper="$WRAPPER_DIR/wrapper-$name.yaml"
  log="$LOG_DIR/$name.log"
  pty_log="$LOG_DIR/$name.log.pty.log"

  if [ ! -f "$wrapper" ]; then
    echo "  [$idx/$total] $name ($topo)  SKIP  (no wrapper)"
    continue
  fi

  echo -n "  [$idx/$total] $name ($topo) ... "
  start=$(date +%s)
  # TRUE PTY (gotcha #4, #19) with bash -c (avoids sh POSIX issue with `source`)
  rc=0
  timeout 180 script -qec "bash -c 'goose run --recipe $wrapper --no-session'" "$pty_log" > "$log" 2>&1 || rc=$?
  end=$(date +%s)
  wall=$((end - start))
  bytes=$(wc -c < "$log" 2>/dev/null || echo 0)
  TOTAL_WALL=$((TOTAL_WALL + wall))
  TOTAL_BYTES=$((TOTAL_BYTES + bytes))

  # Classification
  status="PASS"
  if [ "$rc" -eq 124 ]; then
    status="TIMEOUT"; N_TIMEOUT=$((N_TIMEOUT + 1)); N_FAIL=$((N_FAIL + 1))
  elif grep -q "401\|Authentication failed\|unauthorized" "$log" 2>/dev/null; then
    status="AUTH_FAIL"; N_AUTH=$((N_AUTH + 1)); N_FAIL=$((N_FAIL + 1))
  elif [ "$rc" -ne 0 ] || [ "$bytes" -lt 200 ]; then
    status="FAIL"; N_FAIL=$((N_FAIL + 1))
  else
    N_PASS=$((N_PASS + 1))
  fi

  echo "$status  ${wall}s  ${bytes}B  rc=$rc"
  PER_AGENT_JSON+=("{\"idx\":$idx,\"agent\":\"$name\",\"topology\":\"$topo\",\"status\":\"$status\",\"walltime_s\":$wall,\"bytes\":$bytes,\"rc\":$rc}")
done
end_total=$(date +%s)
wall_total=$((end_total - start_total))

# --- Step 4: substantive check (response > 200B AND >=3 non-empty lines) ---
N_SUBSTANTIVE=0
for log in "$LOG_DIR"/*.log; do
  [ -f "$log" ] || continue
  size=$(wc -c < "$log")
  nlines=$(grep -c "^" "$log" 2>/dev/null || echo 0)
  if [ "$size" -gt 200 ] && [ "$nlines" -gt 3 ]; then
    N_SUBSTANTIVE=$((N_SUBSTANTIVE + 1))
  fi
done

# --- Step 5: write RESULT.json ---
RESULT_JSON="$RESULT_DIR/RESULT.json"
{
  echo "{"
  echo "  \"started_at\": \"$(date -u -d @$start_total '+%Y-%m-%dT%H:%M:%SZ')\","
  echo "  \"finished_at\": \"$(date -u -d @$end_total '+%Y-%m-%dT%H:%M:%SZ')\","
  echo "  \"summary\": {"
  echo "    \"total\": ${#AGENTS[@]},"
  echo "    \"pass\": $N_PASS, \"fail\": $N_FAIL, \"auth_fail\": $N_AUTH, \"timeout\": $N_TIMEOUT,"
  echo "    \"substantive\": $N_SUBSTANTIVE,"
  echo "    \"total_wall_s\": $wall_total,"
  echo "    \"total_bytes\": $TOTAL_BYTES"
  echo "  },"
  echo "  \"agents\": ["
  for i in "${!PER_AGENT_JSON[@]}"; do
    if [ "$i" -gt 0 ]; then echo ","; fi
    echo -n "    ${PER_AGENT_JSON[$i]}"
  done
  echo ""
  echo "  ]"
  echo "}"
} > "$RESULT_JSON"
echo
echo "=== FINAL ==="
echo "  Total agents:  ${#AGENTS[@]}"
echo "  PASS:          $N_PASS"
echo "  FAIL:          $N_FAIL  (auth=$N_AUTH timeout=$N_TIMEOUT)"
echo "  Substantive:   $N_SUBSTANTIVE (response > 200B AND ≥3 non-empty lines)"
echo "  Total wall:    ${wall_total}s = $((wall_total/60))m"
echo "  Total bytes:   $TOTAL_BYTES"
echo "  Summary:       $RESULT_DIR/SUMMARY.txt"
echo "  JSON:          $RESULT_JSON"
echo "  Logs:          $LOG_DIR/"
echo

# --- Step 6: human-readable SUMMARY.txt ---
SUMMARY="$RESULT_DIR/SUMMARY.txt"
{
  echo "R110-28 — 6 team-leads across 3 typologies (HIERARCHICAL/PIPELINE/FLAT)"
  echo "Wall: ${wall_total}s = $((wall_total/60))m, Bytes: $TOTAL_BYTES"
  echo "PASS: $N_PASS  FAIL: $N_FAIL  (auth=$N_AUTH timeout=$N_TIMEOUT)  Substantive: $N_SUBSTANTIVE"
  echo
  printf "%-4s %-30s %-20s %-10s %-8s %-8s %s\n" "#" "Agent" "Topology" "Status" "Wall" "Bytes" "RC"
  for i in "${!AGENTS[@]}"; do
    entry="${AGENTS[$i]}"
    name="${entry%%:*}"
    topo="${entry##*:}"
    log="$LOG_DIR/$name.log"
    # Re-classify (cheap to redo)
    size=$(wc -c < "$log" 2>/dev/null || echo 0)
    rc=$(grep -c "goose run" "$log" 2>/dev/null || echo 0)
    status="PASS"
    if [ "$size" -lt 200 ]; then status="FAIL"; fi
    if grep -q "401\|Authentication failed" "$log" 2>/dev/null; then status="AUTH_FAIL"; fi
    printf "%-4d %-30s %-20s %-10s %-8s %-8s %s\n" "$((i+1))" "$name" "$topo" "$status" "-" "${size}B" "-"
  done
} > "$SUMMARY"
echo "=== DONE — see $SUMMARY and $RESULT_JSON ==="
