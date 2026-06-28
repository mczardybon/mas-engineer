# Framework-Blaupause Phoenix-Recovery
Stand: 20260614_124259

## Was jedes neue Framework automatisch bekommt

### recovery/ Verzeichnis
```
recovery/
├── immune.yaml        → YAML-Pravention (timeout: 60, max_steps: 20)
├── checkpoint.yaml    → Snapshots (timeout: 120, max_steps: 30)
├── safezone.yaml      → Fork-Workspace (timeout: 300, max_steps: 30)
├── timeline.yaml      → Bestpunkt-Suche (timeout: 120, max_steps: 40)
└── defib.yaml         → Notfall (timeout: 120, max_steps: 30)
```

### Integration in main-Rezept
- 5 sub_recipes automatisch registriert
- Checkpoint-Verzeichnis .state/checkpoints/ angelegt
- Prompt-Block: 14 Recovery-Kommandos

### Sub-Agent-Template
Jeder neue Sub-Agent bekommt Recovery-System in instructions:
- Bei Fehler: Automatischer Rollback
- Bei Absturz: Immune + Timeline
- Notfall: Minimal-Config laden

## Nutzung
```bash
# Recovery-Diagnose
python3 dev_agent_doctor.py --analyze

# Checkpoint erstellen (vor Aenderung)
python3 dev_agent_doctor.py --checkpoint --label "vor_grosser_aenderung"

# Bei Fehler: Besten Checkpoint finden + wiederherstellen
recovery --restore-best
```
