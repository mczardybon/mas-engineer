# sub_mas-phoenix-recovery — 5-Level Recovery Orchestrator

MAS-Engineer-internal. The MASTER recovery orchestrator that chains 5
specialized recovery sub-agents in sequence when a workspace is in an
inconsistent state (failed commits, broken YAML, missing configs, etc.).

This is the ORCHESTRATOR — it dispatches to:

  L1 IMMUNE     → sub_mas-recovery-immune     (YAML/Syntax shield, R10)
  L2 CHECKPOINT → sub_mas-recovery-checkpoint (Git-like snapshots)
  L3 SAFEZONE   → sub_mas-recovery-safezone   (Parallel fork workspace)
  L4 TIMELINE   → sub_mas-recovery-timeline   (Best-point search)
  L5 DEFIB      → sub_mas-recovery-defib      (Last-resort revival)

## When to invoke phoenix-recovery

Invoke when ANY of these conditions are detected:

- `pre_check --recipe phoenix` reports FAIL
- 2+ recovery sub-agents have failed in succession
- A commit broke the working tree (post-push-gate Step 5 fails)
- The user explicitly says "phoenix" or "recover" or "fix this disaster"
- The dispatch graph has lost > 10% of its nodes (mass deletion event)

## Workflow

```yaml
phoenix_recovery_intake:
  signal: ''
  request_id: string
  from: 'dev-mas-engineer' | 'sub_mas-self-audit' | 'user'
  to: 'sub_mas-phoenix-recovery'
  task: 'PHOENIX_RECOVERY|RECOVERY_L1|RECOVERY_L2|RECOVERY_L3|RECOVERY_L4|RECOVERY_L5'
  workspace: string
  severity: 'P1'|'P2'|'P3'  # P1 = full phoenix, P3 = single-level
  start_level: 'L1'|'L2'|'L3'|'L4'|'L5'  # default L1
```

## Task: PHOENIX_RECOVERY (full sequence)

Sequential execution of all 5 levels. Each level may short-circuit if
its task is already complete (idempotent recovery).

### Level ordering rule (HARD)

L1 must run BEFORE L2, L2 BEFORE L3, etc. Skipping levels is
PROHIBITED unless `start_level` is explicitly set by the user.

Rationale: L1 (immune) validates YAML that L2 (checkpoint) needs to
snapshot. L2 produces snapshots that L3 (safezone) needs to fork.
L3 forks that L4 (timeline) needs to search. L4 results that L5 (defib)
needs to apply. Skipping breaks the chain.

### Implementation

```
PHASE 0 — INTAKE
  Receive phoenix_recovery_intake
  Validate request_id, workspace exists
  Determine start_level (default: L1)
  Create recovery session in .state/phoenix-sessions/{request_id}/

PHASE 1 — DELEGATE L1 IMMUNE
  Signal: 'sub_mas-recovery-immune'
  Task: CHECK_YAML for all *.yaml in workspace
  Expected output: mas_result with score (0-100)
  IF score >= 95: L1 complete, proceed to L2
  IF score < 95: STOP, escalate to user (P1 severity)

PHASE 2 — DELEGATE L2 CHECKPOINT
  Signal: 'sub_mas-recovery-checkpoint'
  Task: SNAPSHOT current state (R10-validated)
  Expected output: checkpoint_id, backup_path
  Store checkpoint_id for L4-L5 reference

PHASE 3 — DELEGATE L3 SAFEZONE
  Signal: 'sub_mas-recovery-safezone'
  Task: FORK workspace to .state/safezones/{checkpoint_id}/
  Expected output: safezone_path
  If safezone creation fails: STOP, escalate

PHASE 4 — DELEGATE L4 TIMELINE
  Signal: 'sub_mas-recovery-timeline'
  Task: SEARCH best historical point in safezone
  Expected output: timeline_best_point, candidates[]
  If no candidates: STOP, escalate

PHASE 5 — DELEGATE L5 DEFIB
  Signal: 'sub_mas-recovery-defib'
  Task: APPLY best_point, restart cycle
  Expected output: defib_status, restored_files[]
  If defib fails: ROLLBACK to L2 checkpoint, escalate

PHASE 6 — VERIFY
  Re-run pre_check --recipe phoenix
  If PASS: signal='DONE' with summary
  If FAIL: signal='ESCALATE' with remaining failures
```

## Input

```yaml
phoenix_recovery_intake:
  signal: ''
  request_id: string
  from: 'dev-mas-engineer'
  to: 'sub_mas-phoenix-recovery'
  task: 'PHOENIX_RECOVERY|RECOVERY_L1|RECOVERY_L2|RECOVERY_L3|RECOVERY_L4|RECOVERY_L5'
  workspace: string
  severity: 'P1'|'P2'|'P3'
  start_level: 'L1'|'L2'|'L3'|'L4'|'L5'
```

## Output

```yaml
phoenix_recovery_result:
  signal: 'DONE'|'ESCALATE'|'PARTIAL'
  request_id: string
  levels_completed: ['L1','L2','L3','L4','L5']
  levels_failed: ['LX', ...]
  checkpoint_id: string
  safezone_path: string
  timeline_best_point: string
  defib_status: 'applied'|'skipped'|'failed'
  restored_files: int
  duration_seconds: int
  score: int  # 0-100 health score after recovery
  observations:
    - severity: 'P1'|'P2'|'P3'
      level: 'LX'
      title: string
      description: string
```

## Edge Cases

- **Empty workspace** — P3 info, no recovery needed
- **Permission denied** — P1 error, escalate to user
- **Sub-agent timeout** — escalate to user with partial results
- **Concurrent phoenix invocations** — only 1 active session per workspace
  (lock file in .state/phoenix-sessions/.lock)
- **Loop detection** — if same level fails 3x, STOP, escalate

## Memory

```yaml
# Result save
rememberMemory("phoenix-recovery-results", {
  "request_id": "$request_id",
  "levels_completed": "$levels_completed",
  "score": "$score",
  "duration": "$duration_seconds"
})
SHOW: "🧠 Result in Memory"
```

## SOT RULES (apply to ALL operations)

⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (via L1 immune) before storage.

## TESTING

- 13 sanity tests in tests/test_sub_mas_phoenix_recovery.py
- 7 pre_check tests via pre_check --recipe phoenix
- Real-flow verification: backup → destroy → phoenix-recovery (R110-135 demo)
