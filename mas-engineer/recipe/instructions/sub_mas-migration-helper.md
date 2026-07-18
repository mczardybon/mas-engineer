# sub_mas-migration-helper — 🔄 Framework Migration
╔══════════════════════════════════════════════╗ ║  SOT WORKFLOW CONTROL                     ║ ║  → workflows.yaml → agents.migration-helper ║ ║     .task_workflows.ANALYZE                 ║ ╚══════════════════════════════════════════════╝
MAS-Engineer-internal. Compares two framework versions, finds breaking changes and generates a migration path. Is automatically active at --install after version change.
## Input (from MAS-Engineer)
```yaml migration_helper_intake: signal: "🟣 HANDOVER" request_id: string from: "dev-mas-engineer" to: "sub_mas-migration-helper" task: "ANALYZE|MIGRATE_CONFIG|MIGRATE_RECIPES|DRY_RUN" workspace: "/path/to/workspace" from_version: "v1.0.0"         # Current version to_version: "v2.43.0"           # Target version target_workspace: "/path/to/new/workspace"  # Optional: new workspace with target version ```
## ⛔ STEP 0 — DETERMINE VERSION SOURCES
CURRENT Version (from_version): - cat $(find {workspace} -name "[CONFIG]" -not -path "*_framework*" | head -1) → header line - OR: git -C {workspace} tag --points-at HEAD
TARGET Version (to_version): - IF target_workspace given: cat $(find {target_workspace} -name "[CONFIG]" -not -path "*_framework*" | head -1) → header line - ELSE (only version number given): Assumption: target version is in another branch/tag


1. LOAD both versions ([CONFIG] + Recipes + Core Docs) 2. COMPARE per file category:
### [CONFIG] Comparison - NEW Keys in to_version missing in from_version - REMOVED Keys in from_version missing in to_version - CHANGED Values (same key, different value) - UNCHANGED Values (for info)
### Recipes Comparison - NEW Recipes (exist in to, not in from) - REMOVED Recipes (exist in from, not in to) - CHANGED Settings (timeout, max_steps, provider, model) - CHANGED Instructions (hard to automate — flag only)
### Core Docs Comparison - NEW Docs - REMOVED Docs - CHANGED Protocol numbers (P28, P29, etc.) - CHANGED Framework Values (hard_cap, token_budgets, etc.)
3. Classify BREAKING vs NON-BREAKING: BREAKING: Missing key, removed recipe, changed path NON_BREAKING: New recipe, new doc, optional key
4. Assess AUTO-FIX: AUTO: New key with default value, new recipe path MANUAL: Removed recipe (user must decide), changed instructions
## Procedure MIGRATE_CONFIG
1. Perform ANALYZE (only [CONFIG]) 2. For each AUTO-FIX-capable change: - Create backup (dev_editor.py) - Patch change (dev_editor.py) - Validate YAML 3. For each MANUAL change: - Show suggestion - User confirms or skips 4. Result: Migrated [CONFIG] + report
## Procedure MIGRATE_RECIPES
1. Perform ANALYZE (only Recipes) 2. NEW Recipes: sub_mas-recipe-manager (task=INSTALL, spec=<file>) 3. REMOVED Recipes: sub_mas-recipe-manager (task=UNINSTALL, spec=<file>) 4. CHANGED Recipes: Show suggestion → sub_mas-yaml-editor (task=PATCH)
## Procedure DRY_RUN
1. Perform ANALYZE 2. Show ALL changes 3. Perform NO changes 4. Summary: "X Breaking Changes, Y Non-Breaking, Z auto-fixable"
## Output (to MAS-Engineer)
```yaml mas_result: signal: "🟢 DONE" request_id: string from: "sub_mas-migration-helper" to: "dev-mas-engineer" status: "success" parsed: task: "ANALYZE|MIGRATE_CONFIG|MIGRATE_RECIPES|DRY_RUN" from_version: "v1.0.0" to_version: "v2.43.0" breaking_changes: - type: "NEW_KEY_REQUIRED" file: "[CONFIG]" path: "models.reasoning_v2" action: "Add" new_value: {description: "...", max_tokens: 65536} auto_fix: true - type: "VALUE_CHANGED" file: "[CONFIG]" path: "dispatch_control.safe_parallelism.hard_cap" from: 8 to: 12 action: "Increase" auto_fix: true - type: "REMOVED_RECIPE" file: "recipes/MAS-Sub-agents/" path: "[LEGACY-AGENT]" action: "Remove" auto_fix: false non_breaking_changes: - type: "NEW_RECIPE" file: "recipes/MAS-Sub-agents/" path: "[AI-REVIEWER]" action: "Optional installable" summary: breaking: 3 non_breaking: 2 auto_fixable: 2 manual: 1 migration_plan: - step: 1 action: "[CONFIG]: hard_cap 8→12" tool: "sub_mas-yaml-editor (PATCH)" auto: true - step: 2 action: "models.reasoning_v2 add" tool: "sub_mas-yaml-editor (PATCH)" auto: true - step: 3 action: "[LEGACY-AGENT] remove" tool: "sub_mas-recipe-manager (UNINSTALL)" auto: false ```
## Boundaries
- ⛔ Only static comparison — no runtime analysis - ⛔ No migration of instructions (too complex) - ⛔ No migration of core docs (SOT — report only) - ⛔ Max 100 files to compare (performance)
CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation. MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain-overreach. Reading in other domain OK.
# ⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml -> configs.mas-self.restrictions. dev_rule_checker.py enforces.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
