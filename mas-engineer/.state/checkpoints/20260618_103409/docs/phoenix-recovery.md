# Phoenix-Recovery — 5-Stufen-Pipeline
Stand: 20260614_123656

## Anwendung in der Praxis

### Normalfall (vor jeder Change)
1. `recovery --immune` → YAML-Prüfung (60s)
2. `recovery --safezone FORK` → Parallelen Workspace (30s)  
3. `recovery --checkpoint SNAPSHOT` → State speichern (10s)
4. → Change DURCHEXECUTEN →
5. `recovery --safezone MERGE` → Wenn OK (30s)
   oder `recovery --safezone ABORT` → Wenn Fehler (5s)

### Fehlerfall (nach Korruption)
1. `recovery --diagnose` → Schaden analysieren
2. `recovery --timeline FIND_BEST` → Besten Checkpoint finden
3. `recovery --timeline RESTORE_BEST` → Wiederherstellen
4. `recovery --immune VERIFY_STATE` → Complete validieren

### Totalschaden (nichts funktioniert mehr)
1. `recovery --defib DEFIB` → Minimal-Config laden
2. `recovery --defib RESURRECT` → Aus letztem guten Backup
3. `recovery --immune VERIFY_STATE` → Validieren
4. `recovery --checkpoint SNAPSHOT "nach_wiederbelebung"` → Neuen Zustand sichern

## Framework-Blaupause "Phoenix"

Jedes neu erstellte Framework bekommt automatisch:
- `recovery/immnue.yaml` → YAML-Prävention
- `recovery/checkpoint.yaml` → Snapshots
- `recovery/safezone.yaml` → Paralleles Arbeiten
- `recovery/timeline.yaml` → Bestpunkt-Suche
- `recovery/defib.yaml` → Notfall
- `recovery --init` → Erstellt komplette Recovery-Struktur

So ist jedes Framework von Anfang an selbstheilend.
