# Recovery-System — 5 Leveln

## Level 1: IMMUNE (Coronashield)
YAML-Praevention before jedem Edit.
- CHECK_YAML: YAML-Syntax before jedem Save
- CHECK_SYNTAX: Python + Shell Syntax vor Ausfuehrung
- VERIFY_STATE: Total-State check (all Rezepte valide?)
Tool: dev_rule_checker.py --check R10
Sub:  sub_mas-recovery-immune

## Level 2: CHECKPOINT (Git-similare Snapshots)
memoryt den Workspace-State.
- SNAPSHOT: .state/checkpoints/{timestamp}/ mit recipe/ + tools/ + docs/ + state/
- LIST: Letzte 10 Checkpoints anshow
- RESTORE <id>: Checkpoint againhcreate
- DIFF <a>..<b>: Unterschied zwischen Checkpoints
Sub: sub_mas-recovery-checkpoint
Checkpoints: ~47 im .state/checkpoints/ (ca. 180 MB)

## Level 3: SAFEZONE (Fork-Workspace)
Arbeite in a copy, merge erst bei Success.
- FORK: Paralllen Workspace create
- MERGE: Changeen in Main aboutnehmen
- ABORT: Fork verwerfen
- DIFF: Unterschied zwischen Fork und Main
Sub: sub_mas-recovery-safezone

## Level 4: TIMELINE (Automatische Best point-Suche)
Findet den besten Checkpoint automatically.
- FIND_BEST: Analyzed all Checkpoints, finds den optimalen
- RESTORE_BEST: Automatic againhcreate
- SHOW_PATH: Zeigt den founden Path
Sub: sub_mas-recovery-timeline

## Level 5: DEFIB (Emergency-Resuscitation)
Last resort bei Total failure.
- DEFIB: minimum-Config load (only immune + checkpoint)
- RESURRECT: Stepweise aus Backup againbeleben
- DIAGNOSE: Total failure-Analysis
Sub: sub_mas-recovery-defib

## Commands
recovery --checkpoint     # Snapshot create
recovery --list           # Letzte 10 Checkpoints
recovery --remainderore <id>   # Wiederhcreate
recovery --diff <a>..<b>  # Unterschied
recovery --defib          # Emergency
recovery --diagnose       # Analysis
recovery --resurrect      # Resuscitate
