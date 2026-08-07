#!/usr/bin/env bash
# replay-e2e-test.sh — Reproduce the 4 e2e audits for sub_mas-self-auditor
#
# Replays the exact scenarios documented in
# e2e-results/2026-07-21-self-auditor-feature-test/README.md
#
# Usage:  bash e2e-results/2026-07-21-self-auditor-feature-test/replay-e2e-test.sh
# Exits:  0 if all 4 audits produce expected outcome, 1 if any diverge.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

PASS=0
FAIL=0
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

run_audit() {
  local label="$1"
  local expected_exit="$2"
  local scope="$3"
  local report="$4"
  shift 4

  echo ""
  echo "──────────────────────────────────────────────────────"
  echo "▶ $label"
  echo "  scope:   $scope"
  echo "  expect:  exit $expected_exit"

  set +e
  python3 mas-engineer/tools/dev_self_auditor.py \
    --scope "$scope" --output "$report" > /dev/null 2>&1
  local got=$?
  set -e

  echo "  got:     exit $got"
  if [ "$got" = "$expected_exit" ]; then
    echo "  ✅ PASS"
    PASS=$((PASS + 1))
  else
    echo "  ❌ FAIL (expected $expected_exit, got $got)"
    echo "  Report at: $report"
    FAIL=$((FAIL + 1))
  fi
}

# 1. Honest cert → exit 0
run_audit "1. Honest cert (corrected E2E-FIX-VERIFICATION)" \
  0 \
  "e2e-results/2026-07-21-demo-3teams/E2E-FIX-VERIFICATION" \
  "$TMPDIR/01.yaml"

# 2. Synthetic overclaim → exit 1
mkdir -p "$TMPDIR/overclaim"
cat > "$TMPDIR/overclaim/CERTIFICATE.md" << 'EOF'
# ALL HYPOTHESES VERIFIED
VERIFIED FUNCTIONAL
100% PASS
We guarantee this is complete
(workaround: we used a different path)
EOF
run_audit "2. Synthetic overclaim (mirrors original problematic pattern)" \
  1 \
  "$TMPDIR/overclaim" \
  "$TMPDIR/02.yaml"

# 3. Full e2e-results scope → exit 0
run_audit "3. Full e2e-results/ scope (the gate's actual scope)" \
  0 \
  "e2e-results" \
  "$TMPDIR/03.yaml"

# 4. Pre-push block scenario → exit 1
mkdir -p "$TMPDIR/blocked"
cat > "$TMPDIR/blocked/BAD-CERT.md" << 'EOF'
VERIFIED FUNCTIONAL
ALL HYPOTHESES VERIFIED
EOF
run_audit "4. Pre-push block (minimal bad cert)" \
  1 \
  "$TMPDIR/blocked" \
  "$TMPDIR/04.yaml"

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  PASS: $PASS / 4"
echo "  FAIL: $FAIL / 4"
echo "══════════════════════════════════════════════════════════════"
[ "$FAIL" -eq 0 ]
