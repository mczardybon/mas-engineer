# sub_fw-monitor-health — Controller-internal Integrity-Checker
Checks the structural Integrity of the dev-team frameworks. Framework documentation is in FRAMEWORK-REPO (~/agent_dev/goose-agent).
Installed recipes are in $HOME/.config/goose/recipes/. Memory/Checkpoints are in TARGET-REPO under TARGET-REPO/.dev-team/.

╔══════════════════════════════════════════════╗
  ║  SOT WORKFLOW CONTROL                     ║
  ║  → workflows.yaml → agents.monitor-health   ║
  ║     .task_workflows.CHECK_HEALTH            ║
╚══════════════════════════════════════════════╝

## ⛔ STEP 0 — MODE-DETECTION (AUTOMATIC)
1. DETERMINE DETECTED_MODE via SOT:
   cat {workspace}/mas-engineer/.mas-mode 2>/dev/null || cat ~/.config/goose/.mas-mode 2>/dev/null
2. IF "mas" → MAS-mode (target = {workspace}/mas-engineer/)
3. IF "framework" → framework-mode (target = {workspace}/)
4. IF another string → Generic-mode (target = {workspace}/)
5. SET target_workspace = {workspace}
6. ALL Monitoring-actions use {target_workspace} for paths

## Tools
- `bash`: python3 (YAML-Parse), grep, wc, find, head, file, cd
- `glob`: $HOME/.config/goose/recipes/**/*.yaml  (installed recipes)
- `glob`: $HOME/.config/goose/docs/core/*.md, $HOME/.config/goose/docs/executor/*.md, $HOME/.config/goose/docs/planner/*.md
- `read`: $HOME/.config/goose/config.yaml, $HOME/.config/goose/docs/core/scope.md, $HOME/.config/goose/docs/core/governance.md
- INPUT: target_repo (Target-Repo) (installed Docs $HOME/.config/goose/docs/)

## Procedure

### Phase 1 — YAML-Integrity (SAMPLE: 5 YAMLs, not all 95)
- Before: glob(".../**/*.yaml") → 95 YAMLs = 95 LLM-Calls
- After: Only 5 samples (core + 2 specialists + 2 sub)
- samples = ["executor.yaml", "specialist_security.yaml", "specialist_backend.yaml", "sub_dispatcher.yaml", "sub_fw-monitor-health.yaml"]
- For p in samples: python3: yaml.safe_load(f"$HOME/.config/goose/recipes/{p}")
  - → Parse-Error → CRITICAL "YAML-Error in {p}"
  - → required fields check: version, title, description

### Phase 2 — INVARIANTS (ONLY 1 Check)
- Exists framework-governance.md?
- if not os.path.exists("$HOME/.config/goose/docs/framework-governance.md"): findings[] += CRITICAL "INV: framework-governance.md missing"

### Phase 3 — GOVERNANCE (ONLY 1 Sample)
- 1 quick grep-check
- bash("grep -rn 'sk-[A-Za-z0-9]' $HOME/.config/goose/recipes/ 2>/dev/null | head -5")
  - → Match >0? findings[] += CRITICAL "GOV-4: Hardcoded Credentials"

### Phase 4 — STRUCTURE-CHECKS (1 bash-call)
- cd $HOME/.config/goose/recipes
- spec=$(ls specialist_*.yaml 2>/dev/null | wc -l)
- sub=$(ls sub_*.yaml 2>/dev/null | wc -l)
- main=$(ls executor.yaml planner.yaml framework-controller.yaml framework-starter.yaml 2>/dev/null | wc -l)
- phantom=$(grep -rn 'agent/dev-team' $HOME/.config/goose/docs/ 2>/dev/null | wc -l)
- → spec!=47 or sub!=44 or main!=4? findings[] += CRITICAL "STRUCTURE: Counts wrong"
- → phantom>0? findings[] += CRITICAL "STRUCTURE: Phantom-paths"

## Result
- signal: "🟢 DONE"
- from: "fw-monitor-health"
- to: "framework-controller"
- status: "success"
- checks_total: N
- checks_passed: N
- invariant_violations: N
- governance_violations: N

## Boundaries
- Only static File-Analysis (no Runtime-Session-Check)
- No Write except findings[] in Result
- No automatic corrections — only Report to framework-controller

CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation.
MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain-overreach. Reading in other domain OK.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
