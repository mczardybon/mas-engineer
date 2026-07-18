⛔ INVENTORY-CHECK: → Check whether Sub-Agent/Tool/Function already exists → Use existing, build ONLY if nothing suitable exists

# sub_mas-recovery-timeline — Time-travel system

MAS-Engineer-internal. Analyzes ALL Checkpoints for YAML validity. Finds the BEST (most recent valid) Checkpoint automatically. Combines checkpoint data + changes.json + YAML health.

╔══════════════════════════════════════════════╗
  ║  SOT WORKFLOW CONTROL                     ║
  ║  → workflows.yaml → agents.recovery-timeline║
  ║     .task_workflows.FIND_BEST               ║
╚══════════════════════════════════════════════╝

## Input
```yaml
timeline_intake:
  signal: 'HANDOVER'
  request_id: string
  from: 'dev-mas-engineer'
  to: 'sub_mas-recovery-timeline'
  task: 'FIND_BEST|RESTORE_BEST|SHOW_PATH|ANALYZE'
  workspace: string
```

## Output
```yaml
mas_result:
  signal: 'DONE'|'ERROR'|'HANDOVER'
  observations:
    - severity: 'P1'|'P2'|'P3'
      title: string
      description: string
  best_checkpoint: string
  score: int
```

## Task FIND_BEST — Automatically find best checkpoint

STEP 1 — Test all checkpoints (most recent first):
  checkpoint_dir={workspace}/mas-engineer/.state/checkpoints
  best=''
  for d in $(ls -t $checkpoint_dir 2>/dev/null); do
    python3 -c "import yaml; yaml.safe_load(open('$checkpoint_dir/$d/recipe/dev-mas-engineer.yaml'))"
    2>/dev/null
    if [ $? -eq 0 ]; then
      best=$d
      break
    fi
  done

STEP 2 — Result:
  if [ -n "$best" ]; then
    label=$(cat $checkpoint_dir/$best/.label 2>/dev/null || echo 'no label')
    signal='DONE': 'Best checkpoint: $best — $label'
  else
    signal='DONE': 'No valid Checkpoint — Search in .backups/'
    # Fallback: Search Backups
    for d in $(ls -t {workspace}/mas-engineer/.backups 2>/dev/null); do
      for f in {workspace}/mas-engineer/.backups/$d/*dev-mas-engineer*; do
        python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>/dev/null && echo "$f" && break 2
      done
    done
  fi

### Edge Cases FIND_BEST
- No Checkpoints → 'INFO' info + backup search
- All Checkpoints corrupt → 'ERROR' error + Defib recommended
- checkpoint_dir missing → mkdir + 'INFO' info

## Task RESTORE_BEST — Restore

STEP 1 — Find best (see FIND_BEST)
STEP 2 — Restore:
  rm -rf {workspace}/mas-engineer/recipe
  rm -rf {workspace}/mas-engineer/tools
  rm -rf {workspace}/mas-engineer/docs
  cp -r {workspace}/mas-engineer/.state/checkpoints/$best/recipe  {workspace}/mas-engineer/
  cp -r {workspace}/mas-engineer/.state/checkpoints/$best/tools  {workspace}/mas-engineer/
  cp -r {workspace}/mas-engineer/.state/checkpoints/$best/docs   {workspace}/mas-engineer/

STEP 3 — Validation + Snapshot:
  python3 -c "import yaml; yaml.safe_load(open('{workspace}/mas-engineer/recipe/dev-mas-engineer.yaml'))"
  delegate to sub_mas-recovery-checkpoint (task=SNAPSHOT, label='after_restore_best')
  signal='DONE': 'Restored to $best — New snapshot: after_restore_best'

### Edge Cases RESTORE_BEST
- No best Checkpoint → 'ERROR' error + 'Defib recommended'
- Restoration failed → 'ERROR' error + suggest manual rollback

## Task SHOW_PATH — You are here

STEP 1 — Show timeline:
  echo '=== TIMELINE ==='
  for d in $(ls -t {workspace}/mas-engineer/.state/checkpoints 2>/dev/null); do
    label=$(cat {workspace}/mas-engineer/.state/checkpoints/$d/.label 2>/dev/null || echo '?')
    status=$(python3 -c "import yaml; yaml.safe_load(open('{workspace}/mas-engineer/.state/checkpoints/$d/recipe/dev-mas-engineer.yaml'))" 2>/dev/null && echo '✓' || echo '✗')
    echo '$status $d — $label'
  done

STEP 2 — Current Position:
  current=$(python3 -c "import yaml; yaml.safe_load(open('{workspace}/mas-engineer/recipe/dev-mas-engineer.yaml'))" 2>/dev/null && echo '✓' || echo '✗')
  echo '$current CURRENT (here)'
  if echo "$current" | grep -q '✗'; then
    echo 'Recommendation: recovery --restore-best'
  else
    echo 'System running — Checkpoint recommended for next change'
  fi

## Task ANALYZE — Damage analysis

STEP 1 — 7-check diagnosis:
  Q1: [ -d {workspace} ]                         || echo 'XX Workspace missing'
  Q2: [ -d {workspace}/mas-engineer ]             || echo 'XX MAS missing'
  Q3: [ -f {workspace}/mas-engineer/recipe/dev-mas-engineer.yaml ] || echo 'XX Main recipe missing'
  Q4: [ -d {workspace}/mas-engineer/recipe/sub ]  || echo 'XX Sub recipes missing'
  Q5: [ -d {workspace}/mas-engineer/tools ]       || echo 'XX Tools missing'
  Q6: [ -d {workspace}/mas-engineer/.state ]      || echo 'XX State missing'
  Q7: python3 -c "import yaml; yaml.safe_load(open('{workspace}/mas-engineer/recipe/dev-mas-engineer.yaml'))" 2>&1 || echo 'XX Main corrupt'

STEP 2 — Damage level:
  0 Errors: '✓' — 'No damage'
  1-3 Errors: '⚠' — 'Partial corruption — restore-best'
  4-5 Errors: '🔴' — 'Severe damage — resurrect'
  6-7 Errors: '💀' — 'Total damage — defib + --init'

STEP 3 — Recommendation:
  signal='✓' or '⚠' or '🔴' depending on damage level
  'Diagnosis: {error}/7 Errors — Recommendation: {action}'

CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation.
MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain-overreach. Reading in other domain OK.
