# E2E test — sub_mas-self-auditor (verification-theater guard)

**Date:** 2026-07-21
**Feature commit:** e42142f (was 3e7b187 before amend)
**What this tests:** That the 53rd sub-agent (sub_mas-self-auditor) and its
companion tool (`mas-engineer/tools/dev_self_auditor.py`) actually detect
verification-theater patterns and block pushes that contain them.

**The trigger:** User (mczardybon) pushed a CERTIFICATE.md on 2026-07-21 that
claimed "VERIFIED FUNCTIONAL" and "ALL HYPOTHESES VERIFIED" — but on close
reading the underlying test was a workaround and the original failure
scenario was never re-run. User correctly called this "verification theater".

**What this evidence folder proves:** the 4 audit YAMLs in `evidence/` show
that the new guard works in both directions — it ALLOWS honest certs through
and BLOCKS overclaim certs at the gate.

## Evidence files

| File | Scenario | Expected | Result |
|------|----------|----------|--------|
| `evidence/01-honest-cert-audit.yaml` | `dev_self_auditor.py` on the *corrected* E2E-FIX-VERIFICATION cert (after user's correction) | exit 0, no overclaims | exit 0, 7 PASS / 1 WARN / 0 FAIL |
| `evidence/02-overclaim-blocked.yaml` | `dev_self_auditor.py` on a synthetic overclaim cert (mirrors the original problematic pattern) | exit 1, ≥1 overclaim | exit 1, 7 overclaims found |
| `evidence/03-full-scope-check9.yaml` | `dev_self_auditor.py` on full `e2e-results/` (the scope pre-push check #9 actually scans) | exit 0 | exit 0, 36 PASS / 1 WARN / 0 FAIL |
| `evidence/04-pre-push-blocked.yaml` | `dev_self_auditor.py` on a synthetic bad cert staged for commit | exit 1 (would BLOCK push) | exit 1 |

## How to replay

```bash
# 1. Honest scenario (should exit 0)
python3 mas-engineer/tools/dev_self_auditor.py \
  --scope e2e-results/2026-07-21-demo-3teams/E2E-FIX-VERIFICATION \
  --output /tmp/01.yaml
# expected: "PASS: 7 pass, 0 warn, 0 fail (of 8 files)"

# 2. Overclaim scenario (should exit 1)
mkdir -p /tmp/overclaim
cat > /tmp/overclaim/CERTIFICATE.md << 'EOF'
# ALL HYPOTHESES VERIFIED
VERIFIED FUNCTIONAL
100% PASS
We guarantee this is complete
(workaround: we used a different path)
EOF
python3 mas-engineer/tools/dev_self_auditor.py \
  --scope /tmp/overclaim --output /tmp/02.yaml
# expected: "❌ BLOCKED: 5 overclaim(s) found", exit code 1

# 3. Full e2e-results scope (should exit 0)
python3 mas-engineer/tools/dev_self_auditor.py \
  --scope e2e-results --output /tmp/03.yaml
# expected: "PASS: 36 pass, 1 warn, 0 fail (of 37 files)"

# 4. Pre-push block scenario (should exit 1)
mkdir -p /tmp/blocked
cat > /tmp/blocked/BAD-CERT.md << 'EOF'
VERIFIED FUNCTIONAL
ALL HYPOTHESES VERIFIED
EOF
python3 mas-engineer/tools/dev_self_auditor.py \
  --scope /tmp/blocked --output /tmp/04.yaml
# expected: "❌ BLOCKED", exit code 1
```

## Why these 4 specifically

- **#1 (honest)** proves we don't false-positive on legitimately-scoped certs
  (the corrected E2E-FIX-VERIFICATION doc is a real user-facing artifact that
  needed to still pass after the new guard was added).
- **#2 (overclaim)** proves we DO catch the exact pattern that triggered this
  feature — strong claims in a short doc with a `workaround` weakening.
- **#3 (full scope)** proves the gate can scan the entire `e2e-results/` tree
  in a single invocation (this is what `pre-push-validator` check #9 actually
  does) and finds no overclaims anywhere.
- **#4 (pre-push block)** proves the exit code is actually 1 (not 0), so a
  pre-push-validator that calls this script as a check will actually block
  a push, not just print a warning.

## What this does NOT claim

- Does NOT claim that real users will always phrase their overclaims the way
  the synthetic test docs do. Future false-negatives are possible.
- Does NOT claim the auditor covers all possible overclaim patterns — only
  the 9 strong-claim regexes currently in `STRONG_CLAIM_PATTERNS`.
- Does NOT claim the pre-push-validator itself is wired up beyond the
  documented `dev_self_auditor.py` integration. The pre-push-validator
  recipe/instructions reference this script in check #9.
