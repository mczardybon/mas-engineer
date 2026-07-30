#!/bin/bash
# mas_e2e_pty_all.sh — run all 132 mas-recipes in PTY, background-friendly.
#
# Output: e2e-results/<date>-pty-all-132/{evidence,SUMMARY.tsv,RESULT.md}
# Each recipe: 180s timeout, log to evidence/<name>.log, status in SUMMARY.tsv

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECIPE_LIST="$MAS_ROOT/tools/mas_e2e_pty_test_recipes.txt"

# pre-flight env
set -a
source "$MAS_ROOT/.env"
set +a
# R110-45 BUG-2 fix: never overwrite with literal ***. Derive from DEEPSEEK_API_KEY.
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "***" ]; then
  export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
fi
export OPENAI_HOST="${OPENAI_HOST:-https://api.deepseek.com}"
export OPENAI_HOST="${OPENAI_HOST%/v1}"   # gotcha #3b
export GOOSE_MODEL="${GOOSE_MODEL:-deepseek-v4-flash}"
export GOOSE_PROVIDER="${GOOSE_PROVIDER:-openai}"
export GOOSE_TELEMETRY_ENABLED="${GOOSE_TELEMETRY_ENABLED:-false}"
export PATH="/root/.local/bin:$PATH"

# mode: mas
echo -n "mas" > "$HOME/.config/goose/.mas-mode"

# key sanity
if [ -z "$DEEPSEEK_API_KEY" ] || [ ${#DEEPSEEK_API_KEY} -lt 30 ]; then
  echo "FATAL: DEEPSEEK_API_KEY not set (len=${#DEEPSEEK_API_KEY})" >&2
  exit 1
fi

# curl check
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models)
if [ "$HTTP" != "200" ]; then
  echo "FATAL: deepseek API returns $HTTP" >&2
  exit 1
fi

# output dirs
DATE=$(date +%F)
RUN_DIR="$MAS_ROOT/e2e-results/${DATE}-pty-all-132"
EVIDENCE_DIR="$RUN_DIR/evidence"
mkdir -p "$EVIDENCE_DIR"

echo "==========================================="
echo "mas-engineer e2e PTY (132 recipes)"
echo "  date:    $DATE"
echo "  run_dir: $RUN_DIR"
echo "  model:   $GOOSE_MODEL"
echo "  host:    $OPENAI_HOST"
echo "==========================================="

# tsv header
printf "status\tduration_s\trecipe\n" > "$RUN_DIR/_results.tsv"

run_one() {
  local recipe="$1"
  local name
  name=$(basename "$recipe" .yaml)
  local log="$EVIDENCE_DIR/${name}.log"
  local start end dur status

  start=$(date +%s)

  # 180s timeout per recipe
  bash -c "timeout 180 goose run --recipe '$recipe' --no-session" > "$log" 2>&1 || true

  end=$(date +%s)
  dur=$((end - start))

  # status detection
  # R110-45.6: classifier refined. See tools/mas_e2e_pty_test.sh for the
  # full rationale — bare "401" is not an auth error (LLMs quote git
  # hashes, diff stats, file sizes, R-numbers, audit tables).
  if grep -qE "(HTTP/[0-9.]+ 401|status_code[\"\\x27]?[[:space:]]*:[[:space:]]*401|[\"\\x27]status[\"\\x27][[:space:]]*:[[:space:]]*401|Received 401|got 401 Unauthorized|Authentication failed:|Invalid API key:)" "$log"; then
    status="FAIL_AUTH"
  elif grep -qE "(recipe not found|recipe_not_found|FileNotFoundError.*recipe)" "$log"; then
    status="FAIL_NOTFOUND"
  elif [ ! -s "$log" ]; then
    status="FAIL_EMPTY"
  elif grep -qP "(Traceback|^Error:(?! unsupported image format)|Exception:)" "$log"; then
    status="FAIL_ERROR"
  elif grep -qE "(PASSED|ALL CHECKS PASSED|completed successfully|status: ok)" "$log"; then
    status="PASS"
  else
    status="UNKNOWN"
  fi

  printf "%s\t%d\t%s\n" "$status" "$dur" "$recipe" >> "$RUN_DIR/_results.tsv"
  printf "  %-12s %4ds  %s\n" "$status" "$dur" "$name"
}

# main loop
TOTAL=0
while IFS= read -r line; do
  [[ "$line" =~ ^#.* ]] && continue
  [[ -z "$line" ]] && continue
  TOTAL=$((TOTAL+1))
  if [ ! -f "$MAS_ROOT/$line" ]; then
    printf "MISSING\t0\t%s\n" "$line" >> "$RUN_DIR/_results.tsv"
    continue
  fi
  run_one "$MAS_ROOT/$line"
done < "$RECIPE_LIST"

# summary
echo
echo "==========================================="
echo "SUMMARY"
echo "==========================================="
PASS=$(awk -F'\t' '$1=="PASS"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
FAIL_AUTH=$(awk -F'\t' '$1=="FAIL_AUTH"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
FAIL_NOTFOUND=$(awk -F'\t' '$1=="FAIL_NOTFOUND"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
FAIL_EMPTY=$(awk -F'\t' '$1=="FAIL_EMPTY"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
FAIL_ERROR=$(awk -F'\t' '$1=="FAIL_ERROR"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
UNKNOWN=$(awk -F'\t' '$1=="UNKNOWN"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
MISSING=$(awk -F'\t' '$1=="MISSING"{c++} END{print c+0}' "$RUN_DIR/_results.tsv")
PCT=0
if [ "$TOTAL" -gt 0 ]; then PCT=$((PASS * 100 / TOTAL)); fi

cat > "$RUN_DIR/SUMMARY.tsv" <<EOF
metric	count
total	$TOTAL
pass	$PASS
fail_auth	$FAIL_AUTH
fail_notfound	$FAIL_NOTFOUND
fail_empty	$FAIL_EMPTY
fail_error	$FAIL_ERROR
unknown	$UNKNOWN
missing	$MISSING
pass_pct	${PCT}%
EOF

cat "$RUN_DIR/SUMMARY.tsv"
echo
echo "Details: $RUN_DIR/_results.tsv"
