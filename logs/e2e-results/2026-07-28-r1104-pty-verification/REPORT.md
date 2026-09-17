# R110-4 PTY Verification — pipefail, fail-fast, fallback, honest summary

**Date**: 2026-07-28 17:40 UTC
**Branch**: new-agent (3 R110-4 commits ahead of origin: d9bdbca, 127b578, 46afd13)
**Director**: Hermes Agent (post-context-compression)
**Goal**: Verify the 4 verification-theater / e2e-script fixes via real PTY runs

---

## TL;DR

**5/5 PTY tests PASS**:
- T1: `set -o pipefail` catches upstream pipe failures
- T2a/2b: `***` placeholder + empty key trigger fail-fast
- T3: `OPENAI_API_KEY` falls back to `DEEPSEEK_API_KEY` (HTTP 200)
- T4: 401 in log → "E2E TEST FAILED" + exit 1
- **T5: full e2e-full-pipeline.sh → 10/10 LLM runs successful, E2E TEST COMPLETE, exit 0**

The R110-4c commit (46afd13) is structurally correct AND performs
correctly under real LLM load. STEP 7 recovery pattern reproduced
(not scripted — orchestrator ask-for-input triggered genuine MAS auto-fix).

---

## Test 1: `set -o pipefail` catches upstream failure in `tee | tail` pipe

**Scenario**: Simulate a failing command inside `tee | tail` pipe (without
pipefail, `tail` would always succeed and `set -e` would not fire).

**Test script**: `/tmp/pty-test-pipefail.sh`
**Command**: `false 2>&1 | tee -a log | tail -3`
**Without pipefail**: pipeline exit=0 (tail's exit), `set -e` silent
**With pipefail (R110-4c fix)**: pipeline exit=1, propagated to script

**Result**:
```
=== PTY TEST 1: pipefail catches upstream failure ===
Pipeline exit code (with pipefail): 1
PASS: pipefail caught the failure, exit=1
```

**Verification**: The exact same pipe pattern is used in the
e2e-full-pipeline.sh `goose_run()` helper (L51 in current HEAD):
```bash
timeout "$timeout" goose run --no-session --text "$text" \
  2>&1 | tee "$EVIDENCE/${name}.log" | tail -5
```
Without `set -o pipefail` (added at L4 in R110-4c), every goose 401
would be masked. **Test 1 proves the pipefail addition is effective.**

---

## Test 2: Fail-fast on literal `***` or empty DEEPSEEK_API_KEY

**Scenario**: Caller exports `DEEPSEEK_API_KEY=***` (placeholder, the
R110-4c regression pattern) or unsets it entirely.

**Test script**: `/tmp/pty-test-failfast.sh`
**Sub-test 2a**: `DEEPSEEK_API_KEY=***`, `OPENAI_API_KEY=***`
**Sub-test 2b**: both unset

**Result 2a**:
```
FATAL: DEEPSEEK_API_KEY not set or is placeholder.
Source .env first: source mas-engineer/.env && bash scripts/e2e-full-pipeline.sh
Exit code: 1 (expected: 1)
PASS 2a: literal '***' caught, FATAL message printed
```

**Result 2b**:
```
FATAL: DEEPSEEK_API_KEY not set or is placeholder.
Source .env first: source mas-engineer/.env && bash scripts/e2e-full-pipeline.sh
Exit code: 1 (expected: 1)
PASS 2b: empty key caught, script refused to run
```

**Verification**: The new validation block (e2e-full-pipeline.sh L25-32)
runs at script start, BEFORE any API call. This prevents the
R110-4c regression from re-occurring (R110-1 had a similar bug where
the script overwrote the key with `***`).

---

## Test 3: `OPENAI_API_KEY` falls back to `DEEPSEEK_API_KEY`

**Scenario**: Caller sets only `DEEPSEEK_API_KEY` (the standard mas-engineer
`.env` pattern). `OPENAI_API_KEY` is unset.

**Test script**: `/tmp/pty-test-fallback.sh`
**Setup**: `source /tmp/ds-key.sh; unset OPENAI_API_KEY`
**Verification**: Run the new fallback block, then call real DeepSeek API
with `OPENAI_API_KEY` (which should now be set to DEEPSEEK_API_KEY).

**Result**:
```
PRE-SCRIPT: DEEPSEEK=sk-0f3019c..., OPENAI=<unset>
POST-FALLBACK: OPENAI_API_KEY=sk-0f3019c... (same as DEEPSEEK)
Testing API call with OPENAI_API_KEY...
API call result: HTTP 200
API OK

PASS 3: fallback works, API returns 200
```

**Verification**: The shim pattern (e2e-full-pipeline.sh L33-37) is the
same one documented in skill `goose-cli-e2e-testing` gotcha #18. It
works because `OPENAI_API_KEY` is required by goose (config-file value
is silently ignored per gotcha #2) but `DEEPSEEK_API_KEY` is the
user-facing key in `.env`.

---

## Test 4: Honest final summary on log-level 401 errors

**Scenario**: Simulate 3 log files (2 clean, 1 with 401 error). The
script's STEP 11 grep-based counter should detect the 401 and exit 1
instead of printing "E2E TEST COMPLETE" unconditionally.

**Test script**: `/tmp/pty-test-honest-summary.sh`
**Setup**: 3 logs in `/tmp/pty-test4-evidence/`
- `run1.log`: clean
- `run2.log`: contains "Error: 401 Unauthorized" + "Authentication failed"
- `run3.log`: clean

**Result**:
```
=== PTY TEST 4: honest final summary ===
Run summary: 2 succeeded, 1 failed

==================================
E2E TEST FAILED (1 LLM runs errored)
==================================
Inspect failed logs: grep -lE '401|Authentication' /tmp/pty-test4-evidence/*.log
FINAL_EXIT=1
```

**Verification**: This is the **core anti-verification-theater** check.
The pattern (`401|Authentication.*failed|Ran into this error`) is broader
than just `pipefail` because `goose` may return 0 even when the API
call inside it 401s. The error is in the log, not the exit code, so
grep-on-log is more robust than exit-code-only checks.

---

## Test 5: Full e2e-full-pipeline.sh re-run with real LLM

**Status**: ✅ **COMPLETE — 10 succeeded, 0 failed, E2E TEST COMPLETE, exit 0**

**Final run summary** (from STEP 11):
```
[17:56:02] Run summary: 10 succeeded, 0 failed

==================================
E2E TEST COMPLETE
==================================
Evidence: /workspace/e2e-evidence/
/workspace/e2e-evidence/improve-team1.log
/workspace/e2e-evidence/improve-team2.log
/workspace/e2e-evidence/run.log
/workspace/e2e-evidence/team1-create.log
/workspace/e2e-evidence/team1-task1.log
/workspace/e2e-evidence/team1-task2.log
/workspace/e2e-evidence/team2-create.log
/workspace/e2e-evidence/team2-fix-orchestrator.log
/workspace/e2e-evidence/team2-task1-retry.log
/workspace/e2e-evidence/team2-task1.log
/workspace/e2e-evidence/team2-task2.log

Team 1 files: 17
Team 2 files: 19
```

**Per-step results** (10/10 LLM runs successful):
- STEP 1: 119 mas-engineer recipes verified ✓
- STEP 2: team1-create → 6+ team files, health_score formula in output ✓
- STEP 3: team2-create → 6 team files ✓
- STEP 5: team1-task1 → code review findings (division-by-zero, dead code) ✓
- STEP 6: team2-task1 → quality analysis (age 150 anomaly, duplicate Alice row 1=6, Bob salary outlier) ✓
- **STEP 7: USER-FIX (recovery pattern) → team2 orchestrator asked for input, MAS auto-fixed recipe with regex path-extraction, no-asking, fallback path. Recovery flow reproducible** ✓
- STEP 8: team2-task1-retry → quality_report.md created (markdown format — genuine evolution after improve-team1 changed convention) ✓
- STEP 9: improve-team1 (6 YAMLs validated) + improve-team2 (all instructions+recipes reviewed) ✓
- STEP 10: team1-task2 → 94/100 health score, MD5 weakness prioritized (CWE-327), 7 deliverables ✓
- STEP 10: team2-task2 → quality_report_messy_dataset.yaml (remove row 7 empty, merge row 6 dup, add validation rules: age ∈ [0,120], NOT NULL) ✓

**This is the end-to-end integration test**: all 4 R110-4 fixes (pipefail,
fail-fast, fallback, honest summary) work together under real LLM load.
10/10 LLM calls successful, 0 failures, 0 401 errors, 0 verification
theater. STEP 7 recovery pattern reproduced (not scripted theater —
triggered by real orchestrator ask-for-input behavior).

---

## Files in this verification (5)

- `e2e-results/2026-07-28-r1104-pty-verification/REPORT.md` (this file)
- `e2e-results/2026-07-28-r1104-pty-verification/run.log` (test 5, when complete)
- `e2e-results/2026-07-28-r1104-pty-evidence/team1-*.log` (10 LLM runs, when complete)
- Test scripts: `/tmp/pty-test-{pipefail,failfast,fallback,honest-summary}.sh`
- Patched script: `mas-engineer/scripts/e2e-full-pipeline.sh` (commit 46afd13)
