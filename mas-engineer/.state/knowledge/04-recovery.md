# Recovery System — 5 Levels

## Level 1: IMMUNE (Coronashield)
YAML prevention before every edit.
- CHECK_YAML: YAML syntax before every save
- CHECK_SYNTAX: Python + Shell syntax before execution
- VERIFY_STATE: Total state check (all recipes valid?)
Tool: dev_rule_checker.py --check R10
Sub:  sub_mas-recovery-immune

## Level 2: CHECKPOINT (Git-like snapshots)
Memorizes the workspace state.
- SNAPSHOT: .state/checkpoints/{timestamp}/ with recipe/ + tools/ + docs/ + state/
- LIST: Show last 10 checkpoints
- RESTORE <id>: Recreate checkpoint
- DIFF <a>..<b>: Difference between checkpoints
Sub: sub_mas-recovery-checkpoint
Checkpoints: ~47 in .state/checkpoints/ (approx. 180 MB)

## Level 3: SAFEZONE (Fork Workspace)
Work in a copy, merge only on success.
- FORK: Create parallel workspace
- MERGE: Take changes into main
- ABORT: Discard fork
- DIFF: Difference between fork and main
Sub: sub_mas-recovery-safezone

## Level 4: TIMELINE (Automatic best point search)
Finds the best checkpoint automatically.
- FIND_BEST: Analyzes all checkpoints, finds the optimal one
- RESTORE_BEST: Automatic recreate
- SHOW_PATH: Shows the found path
Sub: sub_mas-recovery-timeline

## Level 5: DEFIB (Emergency Resuscitation)
Last resort on total failure.
- DEFIB: Load minimum config (only immune + checkpoint)
- RESURRECT: Stepwise revive from backup
- DIAGNOSE: Total failure analysis
Sub: sub_mas-recovery-defib

## Commands
recovery --checkpoint     # Create snapshot
recovery --list           # Last 10 checkpoints
recovery --restore <id>   # Recreate
recovery --diff <a>..<b>  # Difference
recovery --defib          # Emergency
recovery --diagnose       # Analysis
recovery --resurrect      # Resuscitate
