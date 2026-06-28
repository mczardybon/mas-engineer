# Recovery-System — 5 Stufen

## Stufe 1: IMMUNE (Coronashield)
YAML-Praevention vor jedem Edit.
- CHECK_YAML: YAML-Syntax vor jedem Speichern
- CHECK_SYNTAX: Python + Shell Syntax vor Ausfuehrung
- VERIFY_STATE: Gesamt-Zustand pruefen (alle Rezepte valide?)
Tool: dev_rule_checker.py --check R10
Sub:  sub_mas-recovery-immune

## Stufe 2: CHECKPOINT (Git-aehnliche Snapshots)
Speichert den Workspace-Zustand.
- SNAPSHOT: .state/checkpoints/{timestamp}/ mit recipe/ + tools/ + docs/ + state/
- LIST: Letzte 10 Checkpoints anzeigen
- RESTORE <id>: Checkpoint wiederherstellen
- DIFF <a>..<b>: Unterschied zwischen Checkpoints
Sub: sub_mas-recovery-checkpoint
Checkpoints: ~47 im .state/checkpoints/ (ca. 180 MB)

## Stufe 3: SAFEZONE (Fork-Workspace)
Arbeite in einer Kopie, merge erst bei Erfolg.
- FORK: Parallelen Workspace erstellen
- MERGE: Aenderungen in Haupt uebernehmen
- ABORT: Fork verwerfen
- DIFF: Unterschied zwischen Fork und Haupt
Sub: sub_mas-recovery-safezone

## Stufe 4: TIMELINE (Automatische Bestpunkt-Suche)
Findet den besten Checkpoint automatisch.
- FIND_BEST: Analysiert alle Checkpoints, findet den optimalen
- RESTORE_BEST: Automatisch wiederherstellen
- SHOW_PATH: Zeigt den gefundenen Pfad
Sub: sub_mas-recovery-timeline

## Stufe 5: DEFIB (Notfall-Wiederbelebung)
Letzter Ausweg bei Totalschaden.
- DEFIB: Minimal-Config laden (nur immune + checkpoint)
- RESURRECT: Schrittweise aus Backup wiederbeleben
- DIAGNOSE: Totalschaden-Analyse
Sub: sub_mas-recovery-defib

## Befehle
recovery --checkpoint     # Snapshot erstellen
recovery --list           # Letzte 10 Checkpoints
recovery --restore <id>   # Wiederherstellen
recovery --diff <a>..<b>  # Unterschied
recovery --defib          # Notfall
recovery --diagnose       # Analyse
recovery --resurrect      # Wiederbeleben
