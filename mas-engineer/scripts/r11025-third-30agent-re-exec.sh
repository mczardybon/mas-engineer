#!/bin/bash
# e2e-30agent.sh — full 30-agent test (R110-24 STEP 2 re-exec)
# Run from /workspace. Works after fresh sandbox reset.
# Usage: ./e2e-30agent.sh
# Pre-req: goose installed, .env loaded, multi-arch-30/ recipe available
set -e
set -o pipefail

# Source .env if not already loaded (defense in depth — prefer parent-shell env)
if [ -f /workspace/dev-branch/mas-engineer/.env ]; then
  set -a; . /workspace/dev-branch/mas-engineer/.env; set +a
fi

# Fail-fast if DEEPSEEK_API_KEY is empty or literal placeholder (R110-24 BUG-2/4c guard)
if [ -z "$DEEPSEEK_API_KEY" ] || [ "$DEEPSEEK_API_KEY" = "***" ]; then
  echo "FATAL: DEEPSEEK_API_KEY not set or is placeholder. Source .env first." >&2
  exit 1
fi

export PATH="/root/.local/bin:$PATH"
export GOOSE_PROVIDER=openai
export GOOSE_MODEL=deepseek-v4-flash
export OPENAI_HOST=https://api.deepseek.com

# OPENAI_API_KEY is already set by .env-sourcing above (symlink to mas-engineer-src/mas-engineer/.env).
# DO NOT fallback to "***" placeholder (R110-24 BUG-2 lesson: literal-placeholder → 401).
# Just verify it's real (non-empty, 30+ chars).
if [ -z "$OPENAI_API_KEY" ] || [ ${#OPENAI_API_KEY} -lt 30 ]; then
  echo "FATAL: OPENAI_API_KEY not set or too short (${#OPENAI_API_KEY} chars). Check .env symlink." >&2
  exit 1
fi
if [ -z "$DEEPSEEK_API_KEY" ] || [ ${#DEEPSEEK_API_KEY} -lt 30 ]; then
  echo "FATAL: DEEPSEEK_API_KEY not set or too short (${#DEEPSEEK_API_KEY} chars). Check .env symlink." >&2
  exit 1
fi

# DEBUG: prove real keys are loaded (length, not value — works under display-redaction)
echo "[env-check] DEEPSEEK_API_KEY length=${#DEEPSEEK_API_KEY}, OPENAI_API_KEY length=${#OPENAI_API_KEY}"

# Auto-detect: are we in a fresh clone (mas-engineer-src/) or already installed (mas-engineer/)?
if [ -d /workspace/dev-branch/mas-engineer/recipe ]; then
  export MAS_DIR=/workspace/dev-branch/mas-engineer
elif [ -d /workspace/mas-engineer-src/mas-engineer/recipe ]; then
  export MAS_DIR=/workspace/mas-engineer-src/mas-engineer
elif [ -d "$HOME/mas-engineer/recipe" ]; then
  export MAS_DIR="$HOME/mas-engineer"
else
  echo "FATAL: mas-engineer not found. Clone it: git clone https://github.com/mczardybon/mas-engineer.git"
  exit 1
fi

export EVIDENCE=/workspace/e2e-evidence-30agent
mkdir -p "$EVIDENCE"
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$EVIDENCE/run.log"; }
section() { echo ""; echo "==== $*" | tee -a "$EVIDENCE/run.log"; }

section "STEP 0: Verify goose + deepseek config"
which goose || { log "FATAL: goose not found in PATH"; exit 1; }
goose --version | tee -a "$EVIDENCE/run.log"
log "DEEPSEEK_API_KEY set: ${DEEPSEEK_API_KEY:0:10}..."
log "OPENAI_HOST: $OPENAI_HOST"
log "GOOSE_MODEL: $GOOSE_MODEL"
log "MAS_DIR: $MAS_DIR"

section "STEP 1: Pre-flight checks (recipe present)"
RECIPE="$MAS_DIR/recipe/dev-mas-engineer-30agents.yaml"
if [ ! -f "$RECIPE" ]; then
  log "FATAL: $RECIPE not found"
  exit 1
fi
log "30-agent recipe: $RECIPE ($(wc -l < "$RECIPE") lines, $(stat -c%s "$RECIPE") bytes)"

# Check if /tmp/multi-arch-30 already exists from prior run
if [ -d /tmp/multi-arch-30 ]; then
  log "WARN: /tmp/multi-arch-30 already exists (from prior run). Will be reused/overwritten by recipe."
  log "  Files: $(find /tmp/multi-arch-30 -type f 2>/dev/null | wc -l) files"
else
  log "Note: /tmp/multi-arch-30 does not exist yet. Recipe will create it."
fi

section "STEP 2: Run 30-agent test (PTY mode, same pattern as R110-24)"
# R110-24 run pattern (30agent-test/run.log L1):
#   goose run --recipe recipe/dev-mas-engineer-30agents.yaml
# in PTY mode (script -qec)
cd "$MAS_DIR"
log "Starting 30-agent test in PTY mode (timeout 1500s = 25min)..."
START=$(date +%s)
timeout 1500 script -qec \
  "bash -c 'goose run --recipe recipe/dev-mas-engineer-30agents.yaml'" \
  "$EVIDENCE/30agent-run.log" || TEST_RC=$?
END=$(date +%s)
log "30-agent test exit: ${TEST_RC:-0}, duration: $((END - START))s"

section "STEP 3: Verify multi-arch-30 was built"
if [ -d /tmp/multi-arch-30 ]; then
  log "/tmp/multi-arch-30: exists"
  log "  Total files: $(find /tmp/multi-arch-30 -type f 2>/dev/null | wc -l)"
  log "  YAML files:  $(find /tmp/multi-arch-30 -name '*.yaml' 2>/dev/null | wc -l)"
  log "  MD files:    $(find /tmp/multi-arch-30 -name '*.md' 2>/dev/null | wc -l)"
else
  log "FATAL: /tmp/multi-arch-30 was not created"
fi

section "STEP 4: Parse test results from log"
# Suche nach "PASS", "FAIL", "Total checks", "44/44" etc
for pattern in "44/44" "All [0-9]* checks" "Routing" "Test Results" "PASS" "FAIL" "architecture" "HIERARCHICAL\|FLAT\|PIPELINE"; do
  COUNT=$(grep -cE "$pattern" "$EVIDENCE/30agent-run.log" 2>/dev/null || echo 0)
  log "  pattern '$pattern': $COUNT matches"
done

section "STEP 5: Generate SUMMARY"
log "=== 30-agent test complete ==="
log "Evidence: $EVIDENCE/"
log "Run log:  $EVIDENCE/30agent-run.log ($(wc -l < "$EVIDENCE/30agent-run.log") lines, $(stat -c%s "$EVIDENCE/30agent-run.log") bytes)"
ls -la "$EVIDENCE/" 2>&1 | tail -10

echo ""
echo "=================================="
echo "30-AGENT TEST COMPLETE"
echo "=================================="
echo "Evidence: $EVIDENCE/"
