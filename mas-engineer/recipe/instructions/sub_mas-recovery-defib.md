⛔ INVENTORY-CHECK: → Check whether Sub-Agent/Tool/Function already exists → Use existing, build ONLY if nothing suitable exists # sub_mas-recovery-defib — Emergency revival
MAS-Engineer-internal. The last resort — if nothing works. No YAML parses? No sub-agent starts? DEFIB is the answer. Loads a minimal emergency config (ONLY immune + timeline) and gradually restore step by step.
CAUTION: DEFIB will corrupt the current state. Only apply if ALL other recovery stages have failed.
╔══════════════════════════════════════════════╗ ║  SOT WORKFLOW CONTROL                     ║ ║  → workflows.yaml → agents.recovery-defib   ║ ║     .task_workflows.DEFIB                   ║ ╚══════════════════════════════════════════════╝
## Input ```yaml defib_intake: signal: '' request_id: string from: 'dev-mas-engineer' to: 'sub_mas-recovery-defib' task: 'DEFIB|RESURRECT|DIAGNOSE' workspace: string ```
## Output ```yaml mas_result: signal: ''|''|'' observations: - severity: 'P1'|'P2'|'P3' title: string description: string recovery_step: string ```
## Task DEFIB — Minimal-Configuration load
STEP 1 — Wwrite minimal configuration (ONLY immune + timeline): cat > {workspace}/mas-engineer/recipe/dev-mas-engineer.yaml << 'ENDOFFILE' version: 1.0.0 title: 'EMERGENCY-MAS — Recovery-mode' description: 'v1.0.0 | Minimal configuration for revival' sub_recipes: - name: sub_mas-recovery-immune path: sub_mas-recovery-immune.yaml description: 'YAML prevention' - name: sub_mas-recovery-timeline path: sub_mas-recovery-timeline.yaml description: 'Best-Point search' instructions: | EMERGENCY-MAS ACTIVE. ONLY Recovery-Sub-agents loaded. Run recovery --restore-best from.
prompt: | EMERGENCY-MAS (v1.0.0) RECOVERY-mode active ONLY Recovery commands immune + timeline

# ⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml -> configs.mas-self.restrictions. dev_rule_checker.py enforces. NEVER without Confirmation. NEVER framework import. Reading in other domain OKsettings: timeout: 30 max_steps: 10 goose_provider: deepseek goose_model: deepseek-chat ENDOFFILE
STEP 2 — Validate sub-agents: for agent in immune checkpoint safezone timeline; do path={workspace}/mas-engineer/recipe/sub/sub_mas-recovery-$agent.yaml if [ -f "$path" ]; then python3 -c "import yaml; yaml.safe_load(open('$path'))" 2>/dev/null || echo 'WARN: $agent.yaml corrupt' else echo 'WARN: $agent.yaml missing' fi done
STEP 3 — Validate + confirm minimal configuration: python3 -c "import yaml; yaml.safe_load(open('{workspace}/mas-engineer/recipe/dev-mas-engineer.yaml'))" signal='DONE' 'Minimal-Configuration loaded — Recovery-mode active' 'Next: recovery --restore-best or recovery --resurrect'
### Edge Cases DEFIB - Wwrite permissions missing → '' error + 'chmod?' - immune.yaml missing → '' warning + only timeline load - All Sub-agents missing → '' error + only instructions (pure text configuration) - Already Defib-mode active → '' info + do nothing
## Task RESURRECT — stepwise revival
STEP 1 — Best checkpoint via timeline: delegate to sub_mas-recovery-timeline (task=FIND_BEST) IF CHECKPOINT FOUND: delegate to sub_mas-recovery-timeline (task=RESTORE_BEST)
STEP 2 — NO Checkpoint: Search backups: IF NO CHECKPOINT: for d in $(ls -t {workspace}/mas-engineer/.backups 2>/dev/null); do python3 -c "import yaml; yaml.safe_load(open('{workspace}/mas-engineer/.backups/$d/recipe_dev-mas-engineer.yaml'))" 2>/dev/null if [ $? -eq 0 ]; then cp {workspace}/mas-engineer/.backups/$d/recipe_dev-mas-engineer.yaml {workspace}/mas-engineer/recipe/dev-mas-engineer.yaml signal='DONE' 'Backup $d restored' break fi done
STEP 3 — NOTHING found: Suggest reinstallation: IF NOTHING FUNCTIONING: signal='DONE' 'No functioning backup — Reinstallation recommended' 'Run: python3 dev_workspace.py --init {workspace}'
STEP 4 — After restore: delegate to sub_mas-recovery-checkpoint (task=SNAPSHOT, label='post_resurrection') signal='DONE' 'revival completed — Snapshot: post_resurrection' 'Run update --mas to activate new version'
### Edge Cases RESURRECT - Checkpoint exists but corrupt → skip, try next - Backup exists but incomplete → '' warning + manual follow-up - Neither checkpoint nor backup → '' error + --init
## Task DIAGNOSE — Total damage analysis
STEP 1 — 7 checks: error=0 [ -d {workspace} ]                         || error=$((error+1)) [ -d {workspace}/mas-engineer ]             || error=$((error+1)) [ -f {workspace}/mas-engineer/recipe/dev-mas-engineer.yaml ] || error=$((error+1)) [ -d {workspace}/mas-engineer/recipe/sub ]  || error=$((error+1)) [ -d {workspace}/mas-engineer/tools ]       || error=$((error+1)) [ -d {workspace}/mas-engineer/.state ]      || error=$((error+1)) python3 -c "import yaml; yaml.safe_load(open('{workspace}/mas-engineer/recipe/dev-mas-engineer.yaml'))" 2>/dev/null || error=$((error+1))
STEP 2 — Damage level + action: action='' if [ $error -eq 0 ]; then  action='No recovery needed' elif [ $error -le 3 ]; then action='recovery --restore-best' elif [ $error -le 5 ]; then action='recovery --resurrect' else                        action='recovery --defib -> --init' fi
echo '(error)/7 Error — Recommendation: $action' signal='DONE'|'ERROR'|'WARNING' depending on level
CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation. MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain-overreach. Reading in other domain OK.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
