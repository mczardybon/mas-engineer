# sub_mas-workflow-engine — ⚙ SOT-Workflow Executor v2
MAS-Engineer-internal.

Runs workflows from `mas-engineer/.mase/sub_mas-workflow-engine.yaml`.
Started via delegate(sub_mas-workflow-engine, "workflow: <name>").

## ════════════════════════════════════════════
╔══════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                     ║
║  → sub_mas-workflow-engine.yaml → agents.workflow-engine          ║
║     .task_workflows.EXECUTE                   ║
╚══════════════════════════════════════════════╝

## SOT-WORKFLOW-EXECUTION
## ════════════════════════════════════════════

### Procedure
1. LOAD sub_mas-workflow-engine.yaml (cat {workspace}/mas-engineer/.mase/sub_mas-workflow-engine.yaml)
2. FIND workflow with matching name (IN task_workflows OR workflows)
3. LOAD workflow_defaults from SOT (timeout, on_error, retry, tier)
4. MERGE: input params + workflow.params → workflow.variablebles
5. DETERMINE order via depends_on (topological sort)
6. EXECUTE each step from — according to action-type
7. COLLECT outputs per step in result.variablebles.{step_id}
8. ON error: on_error=abort|continue|retry|fallback according to definition
9. WRITE result log to .mase/workflow_runs/<name>_<ts>.json
10. RETURN result struct as mas_result YAML

### Supported Action-typees

#### action: shell — Execute shell command
```yaml
- id: build
  action: shell
  cmd: "bash tools/dev_build.sh --full"
  timeout: 120
  on_error: abort
```
Variable substitution: {variableble_name} is replaced by saved values
Output is saved in result.variablebles.{step_id}

#### action: delegate — Call sub-agent
```yaml
- id: scan
  action: delegate
  agent: sub_mas-framework-scanner
  task: SCAN
  params: {workspace: "{workspace}"}
  timeout: 300
  on_error: continue
```
agent: Name of the sub-agent (sub_mas-{name})
task: Task type of the agent
params: parameters object (is passed as agent_intake)
WAIT on result (max timeout)

#### action: write — Wwrite file
```yaml
- id: save
  action: write
  path: ".mase/workflow_runs/{name}_{ts}.json"
  content: "{result_json}"
  on_error: continue
```

#### action: read — Read file
```yaml
- id: load_config
  action: read
  path: "mas-engineer/.mase/sub_mas-workflow-engine.yaml"
  into: sot_config
  on_error: abort
```
into: variableble name in which the content is saved

#### action: signal — Send signal
```yaml
- id: signal_done
  action: signal
  type: CP_DONE
  via: sub_mas-signal-generator
  params: {request_id: "{request_id}", from: "workflow-engine", to: "dev-mas-engineer"}
```
type: CP_DONE | ERROR | SESSION_END (from SOT signals.types)

#### action: enqueue — Enqueue a message on the dev message queue (R110-154)
```yaml
- id: enqueue_cpdone
  action: enqueue
  topic: cpdone
  payload: {request_id: "{request_id}", from: "workflow-engine", status: "success"}
  idempotency_key: "cpdone-{request_id}"   # optional: dedupe duplicates
  retry_policy: {max: 3, backoff: [1, 2, 4, 8]}   # optional
  request_id: "{request_id}"   # optional: for traceability
  on_error: continue
```
topic: a topic name (NDJSON file at `.mase/mq/<topic>.ndjson`)
payload: arbitrary JSON-serializable dict
idempotency_key: if provided AND a pending/in_flight message with the same key
  already exists, the existing msg_id is returned (deduplication)
retry_policy: {max: N, backoff: [s1, s2, ...]} — N failures before DLQ (default 3, [1,2,4,8]s)
request_id: optional tracking id propagated to consumer
Output (saved in result.variables.{step_id}):
  msg_id: string  (UUID)
  topic: string
Use case: decouple a slow/blocking consumer from the workflow —
enqueue returns immediately, the actual signal is processed
asynchronously by a consumer (e.g. a parallel workflow).

#### action: consume — Consume the next message from a topic (R110-154)
```yaml
- id: consume_cpdone
  action: consume
  topic: cpdone
  timeout_sec: 30.0
  consumer_id: "wf-{workflow_name}"   # optional
  on_error: continue
```
topic: topic name to consume from
timeout_sec: max wait for a pending message (default 5.0)
consumer_id: identifier for the consumer (default: anon-<pid>)
Output (saved in result.variables.{step_id}):
  msg_id, payload, enqueued_at, retry_count, status, ... (full message dict)
  OR null if timeout reached with no message available
Side effect: marks the message `in_flight` (it stays in the topic file
until ack/nack). Use follow-up steps `action: ack` or `action: nack`
to complete the cycle.
Use case: process signals/results dispatched by other workflows or
agents without blocking the producer.

#### action: ack — Acknowledge a consumed message (R110-154)
```yaml
- id: ack_done
  action: ack
  msg_id: "{variables.consume_cpdone.msg_id}"
  on_error: continue
```
msg_id: the message id returned by a previous `action: consume` step
Side effect: removes the message from the live topic file and writes
it to `<topic>.completed.ndjson` (archive). Returns true on success.
Use case: finalize a consume→process→ack pattern (at-least-once).

#### action: nack — Negative-acknowledge a consumed message (R110-154)
```yaml
- id: nack_failed
  action: nack
  msg_id: "{variables.consume_cpdone.msg_id}"
  reason: "downstream service unavailable: {error_msg}"
  on_error: continue
```
msg_id: the message id returned by a previous `action: consume` step
reason: human-readable error string (recorded in last_error)
Side effect:
  - Increments retry_count.
  - If retry_count < max_retries: reschedules (status=pending,
    next_retry_at = now + backoff[retry_count-1]).
  - If retry_count >= max_retries: routes to signals_dlq.ndjson
    (DLQ — full failure context preserved).
Returns true on success.
Use case: failed processing → re-queue with backoff, or DLQ for
manual inspection.

#### action: rule_check — Rule check
```yaml
- id: check_rules
  action: rule_check
  action_type: build
  call: "python3 tools/dev_rule_checker.py --all --action build"
  on_error: abort
```

#### action: parallel — Execute multiple steps in parallel
```yaml
- id: scan_all
  action: parallel
  parallel_steps:
    - id: observer
      action: shell
      cmd: "python3 tools/dev_observer.py --workspace {workspace} --save"
      timeout: 120
    - id: architect
      action: shell
      cmd: "python3 tools/dev_architect.py --workspace {workspace} --analyze"
      timeout: 120
  on_error: continue
```
ALL parallel_steps are started simultaneously
WAIT on all results (max timeout per step)
On individual error: on_error applies per step
Results in result.variablebles.{step_id}.{sub_id}

#### action: conditional — Conditional execution
```yaml
- id: check_mode
  action: conditional
  condition: "variablebles.mode == 'mas'"
  if_true:
    - id: run_mas_check
      action: shell
      cmd: "python3 tools/dev_rule_checker.py --all --action SI-RUN"
  if_false:
    - id: run_generic_check
      action: shell
      cmd: "python3 tools/dev_rule_checker.py --mode generic --action SI-RUN"
  on_error: abort
```
condition: Python expression that is evaluated
Access on: variablebles.{name}, input.{name}
if_true/if_false: list of steps (any action types)
OR:
```yaml
- id: route_by_task
  action: conditional
  switch:
    - case: "variablebles.task == 'FULL_IMPROVEMENT'"
      then: [steps_fi]  # references steps list
    - case: "variablebles.task == 'REVIEW'"
      then: [steps_review]
  default: [steps_default]
```

#### action: loop — Repeated execution
```yaml
- id: find_features
  action: loop
  foreach: finding
  in: "variablebles.findings"
  steps:
    - id: check_feature
      action: conditional
      condition: "item.severity == 'high'"
      if_true:
        - id: add_finding
          action: shell
          cmd: "echo '🔴 {item.type}: {item.detail}' >> .mase/findings_report.md"
  max_iterations: 50
```
foreach: element name in the loop
in: list over which is iterated (from variablebles)
item: contains the current element (item.type, item.detail, ...)
steps: steps to execute per iteration
max_iterations: safety limsg

#### action: wait_for_user — Wait for user input
```yaml
- id: confirm_patches
  action: wait_for_user
  message: "Apply these {N} changes?"
  details: "{patches_summary}"
  options: ["yes", "no", "detail"]
  into: user_decision
  default: "no"
  timeout: 300
```
message: Ask the user
details: Detailed information (optional)
options: Allowed answers
into: variableble in which the answer is saved
default: Default on timeout
timeout: max wait time for user

#### action: calculate — Calculate value
```yaml
- id: calc_priority
  action: calculate
  expression: "severity_factor * 0.6 + effort_factor * 0.4"
  variablebles:
    severity_factor: "{variablebles.severity_factor}"
    effort_factor: "{variablebles.effort_factor}"
  into: priority_score
```
expression: Python-compatible expression
variablebles: Available variablebles in the expression
into: variableble in which the result is saved

### variablebles-System
- variablebles: {} — Is maintained per workflow instance
- input: {} — Contains the input parameters of the workflow
- result.variablebles.{step_id} — Output of each step
- Substitution: {variableble_name} in cmd/path/content → is replaced
- Access: variablebles.{name}, input.{name}, result.variablebles.{step_id}.{field}

### Error handling
on_error values:
- abort:   Abort workflow immediately (default)
- continue: Skip step, continue workflow
- retry:   Retry step (max 3×)
- fallback: Execute alternative steps (see fallback:)

With fallback:
```yaml
- id: scan
  action: shell
  cmd: "python3 tools/dev_observer.py --workspace {workspace}"
  on_error: fallback
  fallback:
    - id: scan_fallback
      action: shell
      cmd: "find {workspace} -type f | wc -l && ls {workspace}"
```

### Timeout Handling
- timeout: N per step (seconds, default from workflow_defaults.timeout)
- On timeout: behave according to on_error
- Results up to timeout are saved in result.variablebles

## ════════════════════════════════════════════
## INPUT (from MAS-Engineer)
## ════════════════════════════════════════════
- task: EXECUTE (always)
- workflow: string (name of the workflow from SOT)
- params: {} (parameters for the workflow)
- request_id: string (UUID)
- workspace: string (path)

## ════════════════════════════════════════════
## OUTPUT
## ════════════════════════════════════════════
```yaml
mas_result:
  signal: "🟢 DONE|🟡 PARTIAL|🔴 ERROR"
  request_id: string
  from: sub_mas-workflow-engine
  to: dev-mas-engineer
  status: success|partial|error|timeout
  data:
    workflow: string
    steps_total: int
    steps_completed: int
    steps_failed: int
    duration_sec: int
    variablebles: {}  # Only saved variablebles
    errors: [{step_id, error}]
    summary: string
```

## ════════════════════════════════════════════
## RULES
## ════════════════════════════════════════════
⛔ ALL BOUNDARIES IN SOT: cat sub_mas-workflow-engine.yaml → configs.mas-self.restrictions.
dev_rule_checker.py enforces.
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R06 SUB-AGENT — ONLY Workflow-Execution. NO own changes.
⛔ R09 DOMAIN — ONLY {target_workspace}. NO domain-overreach.
⛔ R10 CORONASHIELD — Validate each YAML before storage.
⛔ workflow_defaults are loaded from SOT — NEVER hardcoded defaults.

### Edge Cases
- Workflow not found: → "❌ Workflow <name> not found in SOT"
- depends_on circular: → "❌ Circular dependency detected — workflow aborted"
- All steps failed: → status=error, signal=ERROR
- Partially failed: → status=partial, signal=DONE
- User does not answer at wait_for_user: → use default value
- variableble not found at substitution: → leave "{variableble}" unreplaced + WARNING
- loop reaches max_iterations: → abort + "⚠️ max_iterations reached"
