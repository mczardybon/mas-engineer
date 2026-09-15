# R110-185 — pre-push Check 17 defib-workflow slowness (follow-up to R110-184)

## Context (R110-184 hit)

R110-184 pre-push-validator run (2026-08-18 08:25Z): Check 17 BLOCK on
timeout (180s cap) — pytest-run consumed >180s before stream drain.

Root cause (analyzed 2026-08-18 08:30Z, single `pytest
tests/test_dev_phoenix_recovery_publish.py` run = 245.60s for **9 tests**):

| Test | Dauer | Reason |
|---|---|---|
| test_dev_phoenix_recovery_run_script_exists | <1s | pure existence-check |
| test_dev_phoenix_recovery_run_dry_run_runs_all_5_levels | ~64s | runs all 5 levels incl. defib (60s) |
| test_dev_phoenix_recovery_run_real_enqueues_message | ~64s | runs all 5 levels incl. defib (60s) |
| test_dev_phoenix_recovery_run_level_subset | <5s | only 2 levels, no defib |
| test_wf_phoenix_recovery_publish_exists_in_workflows_yaml | <1s | yaml parse only |
| test_wf_phoenix_recovery_publish_has_correct_steps | <1s | yaml parse only |
| test_dev_mq_topic_depth_returns_int_for_existing_topic | <1s | helper call |
| test_dev_mq_topic_depth_returns_zero_for_nonexistent_topic | <1s | helper call |
| test_wf_phoenix_recovery_publish_runs_via_runner | ~120s | full workflow via runner, defib 60s + retry 60s |

**Single root cause**: `wf_recovery_defib` step `consume` calls
`python3 tools/dev_mq_consumer.py --timeout 60` which **blocks for 60s
when no message is on `monitor.health.degraded` topic** (returns
"no-message" JSON, but the wait is the cost). 4 tests in this file
trigger defib, so 4×60s = 240s baseline for this file alone. Plus 1581
other tests. Total > 5 minutes, exceeds pre-push 180s cap.

Note: this is NOT a flake. It is **structural** — the consumer is
designed to wait for messages. The trade-off: real production has
messages flowing, so 60s idle window is the appropriate polling interval.
For TEST mode we need a shorter window.

## Goal

Reduce pre-push-validator Check 17 wall-clock from >180s back to <120s
(by default) so the gate can complete in its budget.

Two complementary sub-fixes — both should be applied:

### Sub-fix A: test-only shorter defib timeout (PRIMARY)

Add a `wf_recovery_defib_test` variant of `wf_recovery_defib` in
`.mase/workflows.yaml` that uses `--timeout 5` (5 seconds) and has
`retry: max_retries: 0` (no retry on no-message). Then the 4
test_dev_phoenix_recovery_publish.py tests use the _test variant. Saves
~220s on the file (4×55s = 220s shaved).

**Implementation sketch:**
```yaml
wf_recovery_defib_test:
  desc: 'TEST-ONLY variant of wf_recovery_defib (short timeout, no retry)'
  steps:
  - id: consume
    action: shell
    cmd: 'trap ''kill 0'' TERM; python3 tools/dev_mq_consumer.py --topic monitor.health.degraded --consumer-id wf_recovery_defib_test --processor dev_recovery_defib:process_msg --timeout 5'
    timeout: 15
    on_error: continue
  - id: verify_log
    action: shell
    cmd: '...'
```

Then in `test_dev_phoenix_recovery_publish.py`:
- `test_dev_phoenix_recovery_run_dry_run_runs_all_5_levels`:
  invoke `dev_phoenix_recovery_run.py --levels immune,checkpoint,safezone,timeline`
  (4 fast levels, no defib) OR pass `--level-timeout 5` flag.
- `test_dev_phoenix_recovery_run_real_enqueues_message`: same.
- `test_wf_phoenix_recovery_publish_runs_via_runner`: call
  `wf_recovery_defib_test` (or `--level-timeout 5`).

**Easier alternative:** add `--level-timeout` override to
`dev_phoenix_recovery_run.py` (already exists as argparse flag,
default=120). Tests pass `--level-timeout 5`. Saves 4×55s = 220s on
the file alone. RECOMMENDED.

### Sub-fix B: pre-push-validator cap raise (SECONDARY)

Raise pre-push-validator Check 17 internal cap from 180s to 300s
(matches `workflows.yaml` validator-delegate timeout already at 300
per R110-182 commit 04a1777). This alone does NOT fix the
test-suite-duration problem (it just gives more time for the same
slow run), but it provides headroom for Sub-fix A to be partial.

## Direct connection to other R110s

- **R110-175** (pre-push-validator check17-timeout-fix, OPEN) is a
  parent directive — it proposed raising the cap. R110-185 is the
  child that adds the test-timeout reduction so the cap raise is
  actually sufficient.
- **R110-182** (workflow resilience, APPLIED 04a1777) already raised
  workflow timeouts to 300 — but pytest-run in check 17 is not a
  workflow, it's a direct subprocess.run. So the workflow cap
  doesn't help.
- **R110-171** (pre-push-check17-flake-remediation, APPLIED) addressed
  flake via xdist `-n 4`. The current issue is NOT flake (deterministic
  240s) but structural slowness, so R110-171's flake-retry does not
  help (just retries 3×240s = 720s, then BLOCK).

## Plan

1. **PHASE 1** (test-only speedup): add `--level-timeout` override
   to 4 test_dev_phoenix_recovery_publish.py tests. 1 file, ~4
   `subprocess.run(..., timeout=180)` → `timeout=15` plus add
   `--level-timeout 5` to the cmd. 4 tests × ~5 min saved = 20 min
   total test-suite savings.
2. **PHASE 2** (cap raise): update `sub_mas-pre-push-validator.md`
   Check 17 from `timeout=180` to `timeout=300`. Justified by
   R110-182 timeout harmonization (workflow timeouts 180→300, but
   validator stayed at 180 — gap).
3. **PHASE 3** (verify): re-run pre-push-validator, confirm
   Check 17 completes in <120s.

## Verification

- `python3 -m pytest tests/test_dev_phoenix_recovery_publish.py -v`
  should complete in <30s (was 245s) after PHASE 1.
- `goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml`
  should complete all 18 checks in <420s with Check 17 PASS.
- `python3 -m pytest tests/ -q --collect-only` should still show
  1590 tests (no test removed).

## Status

CLOSED 2026-09-15. R110-185 was actually pushed as commit 2fc96f6 ('defib consumer-idle ok + e2e run-all parity'). Directive never formally marked closed. R110-390 (66f48c7) further reduced per-test phoenix-recovery timeouts. Phoenix test file now 84.81s (was 245s baseline).

Evidence: git log: 2fc96f6 'R110-185 — defib consumer-idle ok + e2e run-all parity'. R110-390 (66f48c7) per-test timeout markers. Current run: tests/test_dev_phoenix_recovery_publish.py 9 passed in 84.81s.

Sibling fixes: R110-185 (2fc96f6), R110-390 (66f48c7), R110-413 (subprocess cap)

## Connection to current session (R110-184 push blocker)

R110-184 commit (R110-184 R-102 max_steps→max_turns demo-team
extension, 117 files) was prepared but pre-push-validator BLOCKed on
Check 17. Per mas-engineer-pre-push-check17-flake-handling skill:
- This is NOT a flake (deterministic 240s, no random failure).
- Document the pre-existing condition with `git diff --stat` evidence
  + R110-185 directive (this file).
- If push is genuinely urgent: write follow-up directive FIRST
  (R110-185), then push R110-184 with `--no-verify` and body that
  says "BLOCKED on Check 17, R110-185 follow-up tracks the fix".
