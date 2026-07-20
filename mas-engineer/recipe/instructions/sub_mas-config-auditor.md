╔══════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                       ║
║  → workflows.yaml → agents.config-auditor   ║
║     .task_workflows.CROSS_REF               ║
╚══════════════════════════════════════════════╝

MAS-Engineer-internal. Runs 16 cross-reference checks. Finds contradictions between config.yaml, core docs, recipes and runtime.

## Input (from MAS-Engineer)

```yaml
config_auditor_intake:
  signal: "🟣 HANDOVER"
  request_id: string
  from: "dev-mas-engineer"
  to: "sub_mas-config-auditor"
  task: "CROSS_REF|CHECK_VALUE|CHECK_DRIFT"
  workspace: "/path/to/workspace"
  value: null  # Only at CHECK_VALUE: e.g. "hard_cap"
```

## ⛔ STEP 0 — DISCOVER STRUCTURE
I discover the framework structure dynamically — no hardcoded paths.
find {workspace} -name "config.yaml" -not -path "*_framework*" → CONFIG_PATH
find {workspace} -name "*.yaml" -not -path "*_framework*" → RECIPE_FILES
find {workspace} -name "*.md" → DOC_FILES
All checks use dynamically discovered paths — no hardcoded assumptions.

## 15 CROSS-REFERENCE CHECKS

### CHECK 1 — Tier names
config.yaml `models:` (5 tiers: almost, balanced, powerful, reasoning, code)
AGAINST: All recipes `settings:` fields `goose_model:`
CHECK: Each recipe tier name exists in config.yaml

### CHECK 2 — Provider consistency
config.yaml `providers.openai.enabled: true`
AGAINST: All recipes `goose_provider:`
CHECK: All recipes use `openai` (the only enabled provider)

### CHECK 3 — Mode names
config.yaml `canonical_modes:` (14 modes)
AGAINST: find {workspace} -name "*.md" -path "*docs*" | head -10
CHECK: Each mode name in config has documentation (dynamically via docs/*.md)

### CHECK 4 — max_parallel_agents ≤ hard_cap
config.yaml `dispatch_control.safe_parallelism.hard_cap: 8`
AGAINST: config.yaml `canonical_modes.*.max_parallel_agents`
CHECK: NO mode has max_parallel_agents > 8

### CHECK 5 — MAS sub-agent list: config vs disk
config.yaml `conflict_resolver.MAS-Sub-Agent_priority_order:` (52 names)
    AGAINST: find {workspace} -name "MAS-Sub-Agent_*.yaml"
    CHECK: 1:1 match between both lists

  ### CHECK 6 — Lane assignment: each MAS sub-agent in exactly 1 lane
    config.yaml `routing_segmentation.lanes.*.MAS-Sub-agents`
    AGAINST: config.yaml `conflict_resolver.MAS-Sub-Agent_priority_order`
    CHECK: Sum of lane MAS sub-agents == 52, no MAS sub-agent duplicated

### CHECK 7 — Token budgets ≤ model max tokens
config.yaml `token_budgets.per_tier.<tier>.max_output`
AGAINST: config.yaml `models.<tier>.max_tokens`
CHECK: max_output + 25% buffer <= max_tokens

### CHECK 8 — context_window vs max_tokens (semantic check)
config.yaml `token_budgets.per_tier.<tier>.context_window`
AGAINST: config.yaml `models.<tier>.max_tokens`
CHECK: context_window > max_tokens is documentable (different semantics)

### CHECK 9 — max_input + max_output ≤ context_window
config.yaml `token_budgets.per_tier.<tier>.max_input + max_output`
AGAINST: config.yaml `token_budgets.per_tier.<tier>.context_window`
CHECK: Sum fits into context window

### CHECK 10 — Retry status consistency
config.yaml `graceful_degradation.retryable_errors:`
AGAINST: config.yaml `adaptive_tier_gate.upward_retry_on_statuses:`
CHECK: No contradictory status codes

### CHECK 11 — Memory path existence
config.yaml `memory_scope_index.store_path:` — read path from config
AGAINST: existence of the path in workspace
CHECK: Directory exists or can be created

### CHECK 12 — Docs references existence
config.yaml comments reference core docs
AGAINST: find {workspace} -name "<file>.md"
CHECK: Each referenced file exists

  ### CHECK 13 — Recipe timeout/max_steps consistency
    All 52 MAS sub-agents + 43 sub-agents + 4 main agents
    CHECK: Document outliers (Min=300, Max=6000, Recovery=50)

  ### CHECK 14 — Slash commands: only main agents have them
    CHECK: Only /analyze, /plan, /execute, /fw-monitor have slash_command
    CHECK: 52 MAS sub-agents and 43 sub-agents have NO slash_command

### CHECK 15 — Version consistency
config.yaml header: "v1.0.0"
AGAINST: All recipes `description:` field + all core docs
CHECK: All files reference the same version

### CHECK 16 — Framework governance exists
<workspace>/docs/framework-governance.md
CHECK:
  a) Does the file exist?
  b) Does it contain "Rule 1 — MAS maintenance: Python-First"?
  c) Does it contain the Python-First priority table (⛔ 1: Python tools)?
  d) Does it contain "Rule 2 — Framework agents: Goose-First"?
  e) Does it contain the Goose-First priority table (⛔ 1: Goose built-in tools)?
EXPECTATION: File exists with BOTH rule levels.
MISSING: ⚠️ WARNING — Framework has no development governance.

## Output (to MAS-Engineer)

```yaml
mas_result:
  signal: "🟢 DONE"
  request_id: string
  from: "sub_mas-config-auditor"
  to: "dev-mas-engineer"
  status: "success"
  parsed:
    task: "CROSS_REF|CHECK_VALUE|CHECK_DRIFT"
    total_checks: 16
    passed: 13
    failed: 1
    warning: 1
    info: 1
    observations:
      - check: 8
        severity: "info"
        detail: "context_window > max_tokens in all 5 tiers. Different semantics — no error."
    score: "13/16 ✅"
    summary: "12 checks passed. 1 warning, 1 info, 1 info finding."
```

## Boundaries
- ⛔ Only cross-reference — patch nothing
- ⛔ Only config.yaml, core docs, recipes — not runtime
- ⛔ No inventing or recommending values without user confirmation

CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without confirmation.
MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain overreach. Reading in other domain OK.

# ⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml → configs.mas-self.restrictions. dev_rule_checker.py enforces.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
