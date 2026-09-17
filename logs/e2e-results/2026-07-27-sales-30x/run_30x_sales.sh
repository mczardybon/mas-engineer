#!/bin/bash
# 30x Sales-Team E2E Orchestrator (R108-9)
#
# Runs the sales-team prompt N times, evaluates each run,
# aggregates success rate with confidence interval.
#
# Usage:
#   ./run_30x_sales.sh                # default N=30
#   N=50 ./run_30x_sales.sh          # 50 runs
#   START=10 N=20 ./run_30x_sales.sh # runs 11-30
#
# Requirements:
#   - goose CLI installed
#   - DEEPSEEK_API_KEY in env
#   - ~3-5min per run, so 30 runs ≈ 90-150min
#   - Approx cost: N * $0.10-0.30 (deepseek-chat)

set -u
N="${N:-30}"
START="${START:-1}"
END=$((START + N - 1))
EVIDENCE_DIR="e2e-results/2026-07-27-sales-30x/evidence"
PROMPT_FILE="e2e-results/2026-07-27-sales-30x/prompt.txt"
SCRIPT_DIR="e2e-results/2026-07-27-sales-30x"

echo "=========================================="
echo "30x Sales-Team E2E Orchestrator"
echo "Runs: $START to $END (total: $N)"
echo "Evidence: $EVIDENCE_DIR"
echo "=========================================="

# Pre-flight
if ! command -v goose &> /dev/null; then
    echo "❌ goose CLI not found. Install: https://github.com/block/goose"
    exit 1
fi
if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
    echo "⚠️  DEEPSEEK_API_KEY not set. Some runs may fail with 401."
fi
if [ ! -f "$PROMPT_FILE" ]; then
    echo "❌ Prompt file missing: $PROMPT_FILE"
    exit 1
fi

mkdir -p "$EVIDENCE_DIR"
PASS_COUNT=0
FAIL_COUNT=0
ERROR_COUNT=0

for i in $(seq $START $END); do
    echo ""
    echo "=== Run $i / $END ==="
    LOG="$EVIDENCE_DIR/run${i}-sales-build.log"
    OUT_DIR="$EVIDENCE_DIR/run${i}-eval"
    
    # Clean previous run
    rm -rf /tmp/sales-team
    mkdir -p /tmp/sales-team
    
    # Run goose
    START_TIME=$(date +%s)
    if timeout 600 goose run --no-session --instructions "$PROMPT_FILE" > "$LOG" 2>&1; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "  Duration: ${DURATION}s"
        # Evaluate
        if python3 "$SCRIPT_DIR/eval_sales_run.py" --log "$LOG" --output-dir "$OUT_DIR" >> "$EVIDENCE_DIR/run${i}-eval.log" 2>&1; then
            echo "  ✅ PASS"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo "  ❌ FAIL (hard criteria not met)"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        EXIT_CODE=$?
        echo "  ⚠️  ERROR (goose exit $EXIT_CODE)"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        echo "goose exit $EXIT_CODE" > "$OUT_DIR/error.txt"
    fi
done

echo ""
echo "=========================================="
echo "RESULTS: $PASS_COUNT PASS / $FAIL_COUNT FAIL / $ERROR_COUNT ERROR"
TOTAL=$((PASS_COUNT + FAIL_COUNT + ERROR_COUNT))
if [ $TOTAL -gt 0 ]; then
    RATE=$(python3 -c "print(f'{$PASS_COUNT / $TOTAL * 100:.1f}')")
    echo "Success rate: $RATE% ($PASS_COUNT / $TOTAL)"
    # Wilson 95% CI
    python3 -c "
import math
p = $PASS_COUNT / $TOTAL
n = $TOTAL
z = 1.96
denom = 1 + z**2/n
center = (p + z**2/(2*n)) / denom
spread = z * math.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
print(f'Wilson 95% CI: [{max(0, center-spread)*100:.1f}%, {min(1, center+spread)*100:.1f}%]')
"
fi
echo "=========================================="

# Save summary
cat > "$EVIDENCE_DIR/SUMMARY.json" <<EOF
{
    "total_runs": $TOTAL,
    "pass": $PASS_COUNT,
    "fail": $FAIL_COUNT,
    "error": $ERROR_COUNT,
    "success_rate_pct": $(python3 -c "print(f'{$PASS_COUNT/$TOTAL*100:.1f}' if $TOTAL else 0)"),
    "date": "$(date -Iseconds)"
}
EOF
echo "Summary: $EVIDENCE_DIR/SUMMARY.json"
