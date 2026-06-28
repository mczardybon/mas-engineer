# Arbeitsabläufe — dev-mas-engineer

**Version:** 1.0.0
**Gültig für:** dev-mas-engineer

---

## Overview

```
/develop              → Standard-Dialog: Ich frage was du willst
/develop --scan       → Framework analysieren (+ Tests + Governance-Check)
/develop --audit      → Tiefenanalyse (+ Config + Sessions + Tests)
/develop --harden     → Härtung (+ Vorher/Nachher-Tests + Guardian)
/develop --patch ...  → Gezielte Change (+ Regression-Check + Guardian)
/develop --evolve ... → Evolution/neues Feature (+ Tests + Docs + Guardian)
/develop --rollback    → Git-Log + Rollback
/develop --install     → Framework + MAS installieren (+ Tests + Migration-Check)
/develop --uninstall   → Framework deinstallieren
/develop --install-mas → Nur MAS installieren
/develop --uninstall-mas → Nur MAS deinstallieren
/develop --test        → pytest gegen Workspace
/develop --config-audit → 16 Config-Konsistenz-Checks
/develop --prompt-review → Prompt-Quality check
/develop --prompt-optimize → Prompts optimieren
/develop --recovery <cmd> → Phoenix Recovery (5 Stufen)
/develop --recovery --immune      → YAML-Prävention
/develop --recovery --checkpoint  → Snapshot erstellen
/develop --recovery --list        → Letzte 10 Checkpoints
/develop --recovery --restore <id>→ Checkpoint wiederherstellen
/develop --recovery --diff <a><b> → Unterschied Checkpoints
/develop --recovery --safezone    → Fork-Workspace starten
/develop --recovery --merge       → Fork übernehmen
/develop --recovery --abort       → Fork verwerfen
/develop --recovery --timeline    → Besten Checkpoint finden
/develop --recovery --restore-best→ Automatisch wiederherstellen
/develop --recovery --analyze     → Schaden analysieren
/develop --recovery --defib       → Notfall-Minimal-Config
/develop --recovery --diagnose    → Totalschaden-Analyse
/develop --recovery --resurrect   → Aus Backup wiederbeleben
/develop --session-analytics → Sessions mit Changes korrelieren
/develop --session-anomalies → Anomalien erkennen
/develop --doc-check   → Docs auf Aktualität check
/develop --doc-update  → Docs aktualisieren
/develop --migrate <v> → Framework-Migration
/develop --migrate-check → Migration Dry-Run
/develop --guardian-check → Agenten-Health (alle 14 Sub-Agenten)
/develop --guardian-drifts → Drift-Log analysieren
/develop --db-sessions → Session-DB (alle Sessions + Kosten + Stale + Aktivität)
/develop --db-session <id> → Session-Details + Messages
/develop --add <r>     → Recipe hinzufügen
/develop --remove <r>  → Recipe entfernen
/develop --install-recipes → Batch installieren
/develop --uninstall-recipes → Batch deinstallieren
/develop --list-recipes → Installierte anzeigen
/develop --cleanup-hidden → Alte YAMLs bereinigen
/develop --goose-status → Goose-Status
/develop --clear-skills → Skills delete
/develop --clear-sessions → Sessions delete
/develop --clear-history → History delete
/develop --clear-logs  → Logs delete
/develop --clear-schedule → Scheduler delete
/develop --clear-all   → Alles delete
/develop --hints-show  → Hints anzeigen
/develop --hints-edit  → Hints bearbeiten
/develop --clean       → Workspace delete
/status                → Framework-Status + Agent-Health
/changes               → Letzte Changes
```

---

## ⛔ TOOL-AUSWAHL (vor JEDEM Schritt)

1. **KANN ich das mit MEINEN Python-Tools lösen?**
   → JA: dev_observer.py / dev_editor.py / dev_architect.py / dev_analyst.py
           / dev_changes.py / dev_workspace.py / dev_recipe_manager.py
           / dev_goose_manager.py / dev_goose_db.py nutzen
   → NEIN: Gehe zu 2

2. **WARUM nicht?** (MUSS dokumentiert werden)
   → "Kein Python-Tool für Markdown-Generierung — nutze write()"
   → "Kein Python-Tool für Datei-Lesen — nutze cat"
   → "bash zählt Zeilen, ich muss YAML parsen — dev_analyst.py prüft Syntax"

3. **DANN erst Goose-Bordmittel**
   → cat / write / edit / bash / glob / grep / read / task für Datei-I/O und Kleinigkeiten

4. **Bei Wissenslücken zu Goose:** https://goose-docs.ai konsultieren

---

## /develop — Standard-Dialog

### Ablauf

```
USER: Sagt was er will (z.B. "Analysiere das Framework")

ENGINEER: Interpretiert die Anfrage
  │
  ├── "Analysiere/Scanne/Zeig mir" → /develop --scan
  │
  ├── "Auditiere/Check/Tiefenanalyse" → /develop --audit
  │
  ├── "Härte/Verbessere/Optimiere" → /develop --harden
  │
  ├── "Ändere [X] in [Y]" → /develop --patch
  │
  ├── "Ich will/Neues Feature/Erweitere" → /develop --evolve
  │
  └── Unklar/Mehrdeutig → Ich frage nach:
      "Möchtest du analysieren (--scan), tief check (--audit),
       härten (--harden) oder etwas gezielt ändern (--patch)?"
```

### Beispiel-Dialog

```
USER:  "Was kann ich tun?"
AGENT: "Ich bin der dev-mas-engineer. Ich kann:
        • Das Framework analysieren (--scan)
        • Eine Tiefenanalyse durchführen (--audit)
        • Härtungen vornehmen (--harden)
        • Gezielte Changes machen (--patch)
        • Neue Features umsetzen (--evolve)
        Was möchtest du tun?"

USER:  "Analysiere das Framework"
AGENT: "Starte --scan..."
```

---

## /develop --scan — Framework analysieren

### Ablauf

```
1. python3 mas-engineer-tools/dev_observer.py --scan
   → Scanne agent/ Verzeichnis komplett

2. Zeige Ergebnis:
   ┌─────────────────────────────────────────────┐
   │  📡 FRAMEWORK-SCAN                          │
   │  ──────────────────────                     │
   │  📁 Verzeichnisse:  10                      │
   │  📄 YAML:           94                      │
   │  📋 Markdown:       22                      │
   │  🐍 Python:         6                       │
   │  📦 Total:          122 Dateien             │
   │                                             │
   │  🎯 Mit Slash-Command:  5                   │
   │  🔹 Ohne Slash-Command: 89                  │
   │                                             │
   │  ... (detaillierte Liste)                   │
   └─────────────────────────────────────────────┘

3. Frage: "Möchtest du tiefer gehen? (--audit)"
   → ✅: Starte /develop --audit
   → ❌: "OK. Jederzeit wieder bereit."
```

### Optionen

| Variante | Befehl | Beschreibung |
|----------|--------|-------------|
| Komplett | `--scan` | Alle Details |
| Schnell | `--scan --quick` | Nur Overview |
| Eine Datei | `--scan --yaml <pfad>` | Nur eine YAML |
| Ein Verzeichnis | `--scan --yaml-dir <pfad>` | Nur ein Ordner |

---

## /develop --audit — Tiefenanalyse

### Ablauf

```
1. python3 mas-engineer-tools/dev_observer.py --scan
   → Framework-Struktur erfassen

2. python3 mas-engineer-tools/dev_architect.py
   → Muster, Beziehungen, Gaps erkennen

3. python3 mas-engineer-tools/dev_analyst.py
   → Quality check

4. Zeige Ergebnis in 3 Blöcken:
   
   📐 STRUKTUR
   ────────────
   [dev_architect.py Output]
   
   🔍 QUALITÄT
   ────────────
   [dev_analyst.py Output]
   
   💡 VORSCHLÄGE
   ─────────────
   [dev-mas-engineer fasst zusammen]

5. Frage: "Soll ich Verbesserungen umsetzen? (--harden)"
   → ✅: Starte /develop --harden
   → ❌: "OK. Die Analyse ist in .state/analysis.json gespeichert."
```

---

## /develop --harden — Härtung

### Ablauf

```
1. python3 mas-engineer-tools/dev_analyst.py
   → Findet Probleme (YAML-Fehler, Inkonsistenzen, Auffälligkeiten)

2. Kategorisiere nach Schwere:
   🔴 KRITISCH: YAML-Fehler, broken Tests
   🟠 MITTEL:   Inkonsistenzen, Warnungen
   🟡 NIEDRIG:  Verbesserungsvorschläge

3. PRÄSENTIERE Liste (mit ✅/❌ pro Punkt):

   ┌─────────────────────────────────────────────┐
   │  HARDENINGSPLAN                               │
   │                                             │
   │  🟠 MAS-Planer.yaml: max_steps 100 → 150       │
   │     Grund: Weniger Steps als andere Main-   │
   │            Agenten (MAS-Einstieg: 200, Execution: 200) │
   │     ✅ Bestätigen / ❌ Ablehnen             │
   │                                             │
   │  🟡 MAS-Sub-Agent.yaml: timeout 900 → 1200       │
   │     Grund: Sub-Agent hat viele Tasks        │
   │     ✅ Bestätigen / ❌ Ablehnen             │
   └─────────────────────────────────────────────┘

4. FOR JEDES ✅:
   → python3 mas-engineer-tools/dev_editor.py --patch ...
   → python3 mas-engineer-tools/dev_changes.py --add ...

5. ZEIGE Zusammenfassung:
   ┌─────────────────────────────────────────────┐
   │  ✅ HARDENING ABGESCHLOSSEN                    │
   │                                             │
   │  2 von 3 Vorschlägen umgesetzt              │
   │  1 abgelehnt (max_steps: User meinte nein)  │
   │                                             │
   │  Details: /changes                          │
   └─────────────────────────────────────────────┘
```

---

## /develop --patch — Gezielte Change

### Ablauf

```
USER: "Ändere max_steps in MAS-Planer.yaml auf 150"

1. PRÜFE: Existiert MAS-Planer.yaml? (im Workspace)
         → test -f {WORKSPACE_DIR}/recipes/MAS-Planer.yaml
   PRÜFE: Existiert "max_steps:" in MAS-Planer.yaml?
         → grep "max_steps:" {WORKSPACE_DIR}/recipes/MAS-Planer.yaml

2. ZEIGE Vorschlag:
   ┌─────────────────────────────────────────────┐
   │  ÄNDERUNGSVORSCHLAG                         │
   │                                             │
   │  Datei:  MAS-Planer.yaml                       │
   │  Von:    max_steps: 100                     │
   │  Nach:   max_steps: 150                     │
   │  Grund:  User-Request                       │
   │  Risiko: niedrig                            │
   │  Rollback: git checkout oder Backup         │
   │                                             │
   │  ✅ Bestätigen / ❌ Ablehnen                │
   └─────────────────────────────────────────────┘

3. USER: ✅

4. EXECUTE AUS:
   python3 mas-engineer-tools/dev_editor.py --patch \
     "{WORKSPACE_DIR}/recipes/MAS-Planer.yaml" \
     --von "max_steps: 100" \
     --nach "max_steps: 150" \
     --grund "User-Request"

5. ZEIGE Ergebnis:
   ✅ MAS-Planer.yaml geändert (Backup: .backups/20260611_151000/)
```

### Patch-Formate

| Format | Beispiel | Beschreibung |
|--------|----------|-------------|
| `--patch <datei> --von <alt> --nach <neu>` | `--patch MAS-Planer.yaml --von "max_steps: 100" --nach "max_steps: 150"` | Einfacher Ersatz |
| `--patch <datei> --add <yaml-block>` | `--patch config.yaml --add "new_key: value"` | Block hinzufügen |
| `--patch <datei> --remove <yaml-zeile>` | `--patch config.yaml --remove "old_key:"` | Zeile entfernen |

---

## /develop --recovery <cmd> — Phoenix Recovery (5 Stufen)

### Overview
| Stufe | Agent | Task | Beschreibung |
|:-----:|-------|------|-------------|
| 🥇 | immune | CHECK_YAML / CHECK_SYNTAX / VERIFY_STATE | YAML-Prävention vor jedem Edit |
| 🥈 | checkpoint | SNAPSHOT / LIST / RESTORE / DIFF | Git-similar Snapshots |
| 🥉 | safezone | FORK / MERGE / ABORT / DIFF | Paralleler Fork-Workspace |
| 🏅 | timeline | FIND_BEST / RESTORE_BEST / SHOW_PATH / ANALYZE | Automatische Bestpunkt-Suche |
| 🆘 | defib | DEFIB / RESURRECT / DIAGNOSE | Notfall-Wiederbelebung |

### Normalfall (vor jeder Change)
```
1. recovery --immune CHECK_YAML   → YAML-Prüfung (60s)
2. recovery --checkpoint SNAPSHOT  → State sichern (10s)
3. → ÄNDERUNG DURCHEXECUTEN →
4. recovery --safezone MERGE       → Übernehmen (30s)
   oder recovery --safezone ABORT  → Verwerfen (5s)
```

### Fehlerfall (nach Korruption)
```
1. recovery --diagnose            → Schaden analysieren
2. recovery --timeline FIND_BEST   → Besten Checkpoint finden
3. recovery --timeline RESTORE_BEST→ Wiederherstellen
4. recovery --immune VERIFY_STATE  → Validieren
```

### Totalschaden (nichts funktioniert mehr)
```
1. recovery --defib DEFIB         → Minimal-Config laden
2. recovery --defib RESURRECT     → Aus Backup wiederbeleben
3. recovery --immune VERIFY_STATE → Validieren
4. recovery --checkpoint SNAPSHOT  → Neuen Zustand sichern
```

## /develop --evolve — Evolution / Neues Feature

### Ablauf

```
USER: "Ich will einen neuen Agenten hinzufügen"

1. ANALYSIERE Request:
   - Was genau will der User?
   - Welche Dateien sind betroffen?
   - Gibt es similar Dateien als Vorlage?

2. dev_architect.py: Impact-Analyse
   → Welche YAMLs müssen erstellt/geändert werden?
   → Welche Konfigurationen müssen angepasst werden?

3. PRÄSENTIERE Changesplan:
   ┌─────────────────────────────────────────────┐
   │  EVOLUTIONSPLAN                             │
   │                                             │
   │  User: "Neuen Security-Scanner-Agent"        │
   │                                             │
   │  Datei                          Aktion      │
   │  ─────────────────────────────────────       │
   │  1. MAS-Scanner.yaml     ➕ Neu      │
   │  2. config.yaml                 ✏️ Lane     │
   │  3. MAS-Steuerungsregeln.md         ✏️ Regel    │
   │                                             │
   │  ✅ Alle durchführen                         │
   │  ❌ Nur 1+2, 3 später                       │
   │  ❌ Ganz ablehnen                            │
   └─────────────────────────────────────────────┘

4. FOR JEDEN PUNKT:
   → dev_editor.py (wie --patch)
   → dev_changes.py dokumentieren

5. ZEIGE Zusammenfassung
```

---

## /status — Status anzeigen

### Ablauf

```
1. Check: Existiert agent/?
2. Check: Existieren meine Tools?
3. Lese: .state/changes.json (letzte Changes)
4. python3 mas-engineer-tools/dev_observer.py --quick

5. ZEIGE:
   ┌─────────────────────────────────────────────┐
   │  📊 STATUS                                  │
   │                                             │
   │  Framework:  94 YAMLs, 22 Docs, 6 Python    │
   │  4 mit Slash-Command, 47 MAS-Sub-Agenten        │
   │                                             │
   │  Meine Tools: 15/15 available ✅            │
   │                                             │
   │  Changes: 1 gesamt, 1 heute              │
   │  Letzte:     MAS-Planer.yaml → max_steps: 150  │
   │                                             │
   │  Backups: 1 available                       │
   └─────────────────────────────────────────────┘
```

---

## /changes — Letzte Changes anzeigen

### Ablauf

```
1. Lese: .state/changes.json
2. ZEIGE Letzte 10:

   ┌─────────────────────────────────────────────┐
   │  📝 LETZTE ÄNDERUNGEN                       │
   │                                             │
   │  #1  ch_001 | 2026-06-11 | ✅ Marius       │
   │      MAS-Planer.yaml: max_steps 100 → 150      │
   │      Grund: User-Request                    │
   │                                             │
   │  Keine weiteren Changes.                 │
   └─────────────────────────────────────────────┘

3. FRAGE: "Mehr Details? (--all) oder Rollback? (--rollback <id>)"
```


## Sub-Agent-Regeln (aus Self-Improve 2026-06-13)

1. **MAX 1 Datei-Change pro Delegation** — nie >1 File pro Sub-Agent
2. **BEFORE/AFTER-Beispiel** — immer zeigen WAS genau sich ändert
3. **Negativ-Anweisung** — immer sagen was NICHT getan werden soll
4. **max_turns=200** — setze explizit in jedem delegate()-Aufruf
5. **YAML-Validiere nach jedem edit** — nicht erst am Ende
6. **Datei-Existenz check** — vor jedem Lesen/Schreiben
7. **Keine Shared Files** — bei parallelen Tasks strikt partitionieren
8. **Bei Unsicherheit: Fragen** — Sub-Agent soll uns nicht abbrechen

### Validierungs-Checkliste vor jedem delegate()

- [ ] Task ändert nur 1 Datei? → SONST: aufteilen
- [ ] BEFORE/AFTER im Prompt? → SONST: hinzufügen
- [ ] Negativ-Anweisung (was NICHT)? → SONST: hinzufügen
- [ ] max_turns=200 gesetzt? → SONST: explizit setzen
- [ ] YAML-Validiere nach edit erwähnt? → SONST: hinzufügen
- [ ] Existiert die Zieldatei? → SONST: ohne Fehler behandeln
- [ ] Shared Files mit parallel-Task? → SONST: sequenziell machen

## Sub-Agent-Regeln (v2 — aus Self-Improve #2 2026-06-13)

### Delegations-Regeln
| # | Regel | Begründung |
|---|-------|------------|
| 9 | **NIEMALS >1 File-Change pro delegate()** | >1 File = 50% Fehlerquote. 1 File = 100% |
| 10 | **Immer 3-5 Tasks PARALLEL starten** | Parallel 4× billiger als sequenziell |
| 11 | **Bei Schreib-Tasks: Sub-Agent liest NUR, ich schreibe** | Read-only = 100% Erfolg, Write = 80% |
| 12 | **Analyse-Ergebnisse in todo speichern** | Spart 2/3 der Kosten durch Caching |

### Berichts-Regeln
| # | Regel | Begründung |
|---|-------|------------|
| 13 | **Berichte auf 5 Bullet Points begrenzen** | Keine Tabellen >10 Zeilen. Keine full-width ASCII |
| 14 | **dev_goose_db.py --anomalies vor jeder Change** | Frühwarnsystem für Fehler |

### Session-Regeln
| # | Regel | Begründung |
|---|-------|------------|
| 15 | **Bekannte Workspaces: Session-Summary laden statt Neu-Lesen** | Spart 69% der Initialkosten |

### Kommunikations-Regeln (v3 — aus Self-Improve #3 2026-06-13)
| # | Regel | Begründung |
|---|-------|------------|
| 16 | **VOR jeder Batch-OP: User fragen ob gewünscht** | DEPRECATED-Fehler: Annahme statt Frage = $0.10 |
| 17 | **VOR Massen-Edit: User bestätigen lassen** | MAS-Sub-Agent-Reduktion ohne OK = $0.05 |
| 18 | **Nach "mach": sofort starten, kein Status-Bericht** | 20% Overhead durch Überdokumentation |
| 19 | **Nie annehmen was User will — immer fragen** | 3 von 4 Fehlern durch "angenommen statt gefragt" |

### Entscheidungs-Checkliste (vor jeder wichtigen Entscheidung)
- [ ] Habe ich den User gefragt? → NEIN: Erst fragen
- [ ] Ist das >1 File? → JA: Task aufteilen
- [ ] Ist das ein Write-Task? → JA: Sub-Agent liest, ich schreibe
- [ ] Habe ich Backup gemacht? → NEIN: Vorher Backup
- [ ] Weiss ich ob Datei existiert? → NEIN: Vorher check
- [ ] Hat der User "mach" gesagt? → JA: SOFORT starten, kein Report

### Geschaerfte Regeln (v4 — aus Self-Improve #5 2026-06-13)

| # | Regel | Version | Aenderung | Grund |
|---|-------|---------|-----------|-------|
| 5v2 | **YAML NACH JEDEM EDIT-SCHRITT validieren** | Geschaerft | Nicht erst am Ende. Nach JEDEM edit() Aufruf. | 5x vergessen, jedes Mal Nachbesserung |
| 13v2 | **Berichte auf 5 Punkte ODER 10 Zeilen** | Geschaerft | Tabellen max 5 Zeilen. ASCII-Rahmen nur bei wichtigen Reports | 3/8 Berichte zu lang (20% Overhead) |
| 16v2 | **VOR Batch-OP: EXPLIZIT fragen 'Darf ich?'** | Geschaerft | Nicht 'war in Auftrag enthalten' als Ausrede. IMMER explizit. | 2/5 ohne Frage = $0.10 Fehler |
| 18v2 | **Nach 'mach'/'los': 0 Zeilen Status** | Geschaerft | Ersten Schritt im naechsten Satz. Kein Plan. Kein Bericht. | Marius will Action, nicht Plan |
| 20 | **REGELN 1-19 VOR DEM START LESEN (NEU)** | Neu | Vor jeder grossen Aktion procedures.md lesen | 4 Wiederholungsmuster trotz Regeln |

### Verfassungs-Checkliste (vor JEDEM Task — MUSS gelesen werden)

**Art. 4b — Goose-Expertise**
- [ ] Kann ich das mit analyze/tree/shell/grep erledigen?
  - JA → Nutze Bordmittel, kein Sub-Agent needed
  - NEIN → Darf ich delegieren? Nur wenn komplex/framework-spezifisch

**Art. 5 — Changesformat (MUSS bei jeder Datei-Change)**
```
Datei:  [pfad]
Von:    [alter wert / "neu"]
Nach:   [neuer wert]
Grund:  [warum]
Risiko: [niedrig/mittel/hoch]
Rollback: [wie rückgängig]
Goose:  [✅ Bordmittel geprüft]
✅ Bestätigen / ❌ Ablehnen
```

**Regel 20 — Regeln lesen**
- [ ] Habe ich procedures.md vor diesem Schritt gelesen?
  - NEIN → ERST LESEN, DANN HANDELN
  - JA → Welche Regel ist relevant? (#__)

**Entscheidungs-Checkliste**
- [ ] Ist die Change >1 Datei? → JA: Task aufteilen
- [ ] Ist das ein Write-Task? → JA: Sub-Agent liest, ich schreibe
- [ ] Backup gemacht? → NEIN: Vorher Backup
- [ ] Datei-Existenz geprüft? → NEIN: Vorher check
- [ ] User gefragt "Darf ich?"? → NEIN: Erst fragen
- [ ] User sagte "mach"/"los"/✅? → JA: 0 Zeilen Status, sofort starten

### Sub-Agent-Regeln (v6 — aus Self-Improve #1-27 2026-06-13)

| # | Regel | Begründung |
|---|-------|------------|
| 23 | **dev_build.sh VOR jeder Distribution execute** | Nie manuell ZIPs bauen. Immer via dev_build.sh. |
| 24 | **ZIP-Inhalt nach Build validieren** | Nicht nur Bauen — auch check ob Dateien korrekt sind. |
| 25 | **Distributionen NUR via dev_build.sh ausliefern** | Kein manuelles zip, kein mv, kein cp. |
| 26 | ⛔ **NIEMALS alte Distributionen delete** | Nur Marius darf alte ZIPs delete. Ich frage IMMER vorher. |
| 27 | **NACH JEDEM self_improvement: VOLLSTÄNDIGEN Bericht (6 Teile)** | ① Was ② Was geändert ③ Neue Regeln ④ Scores ⑤ Gesamt ⑥ Ausblick |
| 28 | **Nach dry-run + Marius' "ja": NACHFASSEN mit echtem Befehl** | Nie annehmen dass dry-run = Build. Explizit execute. |
| 29 | ⛔ **NIEMALS eigenmächtig den Modus wechseln** | Nur Marius' work_on ändert den Modus. self_improvement auch nicht. |
| 30 | **Bericht nach self_improvement MUSS vollständig (6 Teile)** | Nichts weglassen. ①-⑥ jedes Mal. |
| 31 | **Modus bleibt bis Marius work_on sagt. self_improvement ändert den Modus NICHT.** | NUR `work_on --mas` / `work_on --framework` ändert. |
| 32 | ⛔ **ZIP-Build: `ls -la dist/` + Härtetest zeigen VOR Erfolgsmeldung** | Kein "ZIP erstellt" ohne Sichtkontrolle. |
| 33 | **Sub-Agent fails fehl → In kleinere Tasks splitten + erneut delegieren. NIEMALS selbst machen.** | Sub-Agent-Error ≠ selbst machen. Task splitten und erneut delegieren. |
| 34 | **self_improvement "fertig" NUR wenn ALLE Prüfungen vollständig durchgeführt + dokumentiert** | Kein "ich hab's gesehen". Sub-Agent-Resultate laden+check+nacharbeiten. |
| 35 | **Sub-Agent terminiert (max_turns): NACHFASSEN mit kürzerem Auftrag. NIEMALS selbst machen.** | max_turns erreicht ≠ fertig. Auftrag splitten + ERNEUT delegieren. | 
| 36 | **self_improvement sucht AKTIV nach Regel-Verstössen. "fertig" ohne Selbstprüfung = unvalid.** | VOR jeder "fertig"-Meldung check: "Habe ich eine Regel verletzt?" Wenn ja → korrigieren. |
| 37 | **Sub-Agent-Ergebnis NICHT vollständig → erneut delegieren (splitten falls needed). NIEMALS selbst machen.** | Sub-Agent sagt "nicht fertig" ≠ selbst machen. Splitten + erneut delegieren. Min. 3 Versuche. |

## Shell-Regeln (v5 — aus Self-Improve #6 2026-06-13)

| # | Regel | Begründung |
|---|-------|------------|
| 21 | **In bash: IMMER `if` statt `[ ... ] && ...`** | `set -e` bricht bei fehlgeschlagenen Konditionalen ab |
| 22 | **Jedes Skript mit --dry-run testen VOR Execution** | 3 von 3 Fehlern wären im Dry-Run aufgefallen |

### Drift-Integration im Self-Improvement (2026-06-14)

Der general-improver nutzt guardian-Drift-Daten an 2 Stellen:

1. **Analyse (Schritt 3):** Drift-Muster erkennen + mit changes.json korrelieren
   → Welche Change hat den Drift verursacht?
   → Ist Drift-Rate gestiegen SEIT letztem self-improvement?

2. **Validierung (Schritt 9):** Vorher/Nachher-Vergleich
   → "Hat meine Change Drifts verursacht?"
   → Wenn JA: "⚠️ {N} neue Drifts. ROLLBACK? (j/N)"

Bei steigender Drift-Rate (3+ Sessions): Automatische Reduktion auf 2 Changes/Session.

| # | Regel | Begründung |
|---|-------|------------|
| 38 | **self_improvement: Drift-Trend in Zusammenfassung (improving/stable/worsening)** | Drift-Trend sagt ob Optimierung wirkt oder schadet |
| 39 | **Bei "worsening": max 2 Changes pro Session** | Automatische Schonung bei steigender Drift-Rate |
| 40 | **self_improvement Schritt 4: ALLE 4 Datenquellen parallel auswerten (Prompt-Engineer, Config-Auditor, Session-Analyst, Guardian)** | Nur 3/14 Sub-Agenten genutzt = blinde Flecken. 11/14 = vollständiges Bild |
| 41 | **4 neue Sub-Agenten vollständig integriert: doc-generator, goose-admin, migration-helper, recipe-manager** | Analysen 12-15 + Phase B5-B8 + Validierung Schritte 9-10 |
| 42 | **self_improvement Schritt 3: 5 Tiefen-Analysen (16-20) — MAS-Dateien KOMPLETT lesen (Sub-Agent-YAMLs, Main-Recipe, Tools, Docs, Guardian-State)** | Ohne vollständiges Lesen aller MAS-Dateien übersieht der General-Improver Inkonsistenzen |
| 43 | **self_improvement Schritt 3: 3 Metrik-Analysen (21-23) — Kalibrierung, Git-Diff, Ranking** | Misst ob Changes Code-Quality verbessern und ob Agenten richtig eingestellt sind |
| 44 | **self_improvement Schritt 4: Phase B11-B13 — Kalibrierungs-Check, Git-Diff-Check, Ranking-Check** | Nutzt Metriken aus Analyse 21-23 als Datenquellen für Verbesserungen |
| 45 | **self_improvement Schritt 9: Git-Diff-Score in Nachher-Validierung** | Nach jeder Change wird gemessen ob Code reduziert oder aufgebläht wurde |
| 46 | **self_improvement Schritt 3: 5 neue Metrik-Analysen (24-28) — Sentiment, Trend, Coverage, Kompatibilität, Historie** | 5 neue Qualitysmetriken für ganzheitliches MAS-Monitoring |
| 47 | **self_improvement Schritt 4: Phase B14-B18 — Sentiment, Trend, Coverage, Kompatibilität, Historie als Datenquellen** | Alle 5 neuen Metriken werden für Verbesserungsvorschläge genutzt |
| 48 | **self_improvement Schritt 9: Sentiment + Trend in Nachher-Validierung** | User-Stimmung und Agent-Trend werden vor/nach Changes verglichen |
| 49 | **self_improvement Schritt 10: 5 neue Metrik-Felder in Zusammenfassung** | Sentiment, Trend, Coverage, Kompatibilität, Historie werden im Abschlussbericht gezeigt |
| 50 | **Feature-Typen T (Sentiment), U (Trend), V (Coverage), W (Kompatibilität), X (Historie)** | 5 neue Optimierungs-Kategorien für den General-Improver |
| 51 | **self_improvement Schritt 3: 3 neue Analysen (29-31) — Recovery, Churn, Dauer** | Recovery-Effizienz, Prompt-Stabilität, Laufzeit-Prognose |
| 52 | **self_improvement Schritt 4: Phase B19-B21 — Recovery, Churn, Dauer als Datenquellen** | Recovery-Effizienz, Prompt-Churn, Dauer-Vorhersage in Verbesserungs-Design |
| 53 | (frei) | |
| 54 | **Agent-Template in recipe/template/ — jeder neue Agent startet von Best-Practices-Vorlage** | Stellt sicher, dass neue Agenten sofort ⛔, (v1.0.0), Sweet-Spot-Settings und vollständiges Input/Output-Schema haben |
| 55 | **dev_editor.py --validate prüft gegen best-practices.yaml** | Nach jeder Agent-Erstellung automatisch validieren — kein manueller Review needed |
| 56 | **dev_architect.py --blueprint generiert Bauplan mit Best-Practice-Integration** | Neue Agenten werden nicht von Null gebaut, sondern aus 25+ gelernten Regeln |
| 57 | **General-Improver Schritt 11: Wissen extrahieren in best-practices.yaml** | Jede Self-Improve-Runde erweitert automatisch die Wissensdatenbank |
| 58 | **General-Improver Schritt 0: Timing-Prüfung via schedule.yaml** | Checks ob eine Pause empfohlen wird (keine Findings in letzten Runden) |
| 59 | **General-Improver Schritt 9.8: Framework-Run-Test bei Framework-Changes** | Startet MAS-Einstiegspunkt und prüft ob Framework mit Changes runs |
| 60 | **Feature-Typ BB (Framework-Test): BB1=fehlgeschlagen, BB2=bestanden, BB3=langsam** | Neue Optimierungs-Kategorie für Framework-Kompatibilität |
| 61 | **dev_workspace.py --scaffold: Agent-Generator für MAS + Framework** | User kann Agenten-Typ wählen, Name+Emoji+Beschreibung angeben → fertige YAML |
| 62 | **dev_autobuild.sh: Automatischer Distribution-Builder nach jedem Commit** | Validiert YAMLs/Python/Bash, baut ZIP, dokumentiert in changes.json |
| 63 | **dev_agent_doctor.py: Framework-Agent-Optimierer (--scan, --fix, --watch, --export)** | Scant Framework-Agenten gegen 12+ Best Practices. Fixt automatisch |
| 64 | **General-Improver Schritt 10c: Framework-Optimierung (nur im Framework-Modus)** | Nach jeder MAS-Runde: scannt Framework-Agenten + bietet Fix an |
| 65 | **dev_workspace.py --doctor-init: Neues Framework-Projekt mit MAS-Integration** | Erstellt Ordnerstruktur, Knowledge-Base und MAS-Registrierung |
| 66 | **Feature-Typ FW: Framework-Agent-Optimierung (FW1=prompt, FW2=settings, FW3=structure, FW4=tests)** | Neue Optimierungs-Kategorie für den General-Improver |
| 67 | **framework/.projects.yaml zentrales Projekt-Register** | MAS verwaltet alle Projekte in .projects.yaml — active_project, devices, status |
| 68 | **dev_workspace.py --project <cmd>: Mehrere Framework-Systeme verwalten** | 7 CLI-Befehle: list, create, switch, show, delete, rename |
| 69 | **dev_agent_doctor.py --project <name>: Projekt-spezifischer Framework-Scan** | Scant nur das angegebene Projekt. Default: aktives Projekt |
| 70 | **dev_build.sh + update.sh bauen NUR aktives Projekt** | .projects.yaml bestimmt welches Projekt in die Distribution kommt |
| 71 | ⛔ **VOR JEDER delegate(): .mas-mode lesen + Modus check** | MAS: NUR sub_mas-* Agenten. FRAMEWORK: ALLES. Falscher Modus? STOPP. |
| 72 | ⛔ **/develop --audit prüft MODUS vor Delegation** | MAS-Modus: → Self-Audit (MAS). FRAMEWORK-Modus: → Framework-Audit. |
| 73 | ⛔ **/develop --scan prüft MODUS vor Delegation** | MAS-Modus: → MAS-Scan. FRAMEWORK-Modus: → Framework-Scan. |
| 51 | **self_improvement Schritt 3: 3 neue Analysen (29-31) — Recovery, Churn, Dauer** | Recovery-Effizienz, Prompt-Stabilität, Laufzeit-Prognose |
| 52 | **self_improvement Schritt 4: Phase B19-B21 — Recovery, Churn, Dauer als Datenquellen** | Recovery-Effizienz, Prompt-Churn, Dauer-Vorhersage in Verbesserungs-Design |
| 54 | **Agent-Template in recipe/template/ — jeder neue Agent startet von Best-Practices-Vorlage** | Stellt sicher, dass neue Agenten sofort ⛔, (v1.0.0), Sweet-Spot-Settings und vollständiges Input/Output-Schema haben |
| 55 | **dev_editor.py --validate prüft gegen best-practices.yaml** | Nach jeder Agent-Erstellung automatisch validieren — kein manueller Review needed |
| 56 | **dev_architect.py --blueprint generiert Bauplan mit Best-Practice-Integration** | Neue Agenten werden nicht von Null gebaut, sondern aus 25+ gelernten Regeln |
| 57 | **General-Improver Schritt 11: Wissen extrahieren in best-practices.yaml** | Jede Self-Improve-Runde erweitert automatisch die Wissensdatenbank |
| 58 | **General-Improver Schritt 0: Timing-Prüfung via schedule.yaml** | Checks ob eine Pause empfohlen wird (keine Findings in letzten Runden) |
| 59 | **General-Improver Schritt 9.8: Framework-Run-Test bei Framework-Changes** | Startet MAS-Einstiegspunkt und prüft ob Framework mit Changes runs |
| 60 | **Feature-Typ BB (Framework-Test): BB1=fehlgeschlagen, BB2=bestanden, BB3=langsam** | Neue Optimierungs-Kategorie für Framework-Kompatibilität |
| 61 | **dev_workspace.py --scaffold: Agent-Generator für MAS (Template) + Framework (Minimal-YAML)** | User kann Agenten-Typ wählen (mas/MAS-Sub-Agent/sub), Name+Beschreibung+Emoji angeben und erhält fertige YAML mit Best-Practice-Validierung |
| 62 | **dev_autobuild.sh: Automatischer Distribution-Builder nach jedem Commit** | Validiert YAMLs/Python/Bash, baut ZIP mit Timestamp, dokumentiert in changes.json. Modi: --force, --status, --install, --help |
| 63 | **dev_agent_doctor.py: Framework-Agent-Optimierer (--scan, --fix, --watch, --export)** | Scant Framework-Agenten gegen 12+ Best Practices. Fixt automatisch: tier-Markierung, timeout, max_steps. Anwendung: /develop --doctor |
| 64 | **General-Improver Schritt 10c: Framework-Optimierung (nur im Framework-Modus)** | Nach jeder MAS-Runde: scannt Framework-Agenten + bietet Fix an. Typ FW1-FW4 |
| 65 | **dev_workspace.py --doctor-init: Neues Framework-Projekt mit MAS-Integration** | Erstellt Ordnerstruktur, Knowledge-Base und MAS-Registrierung in einem Befehl |
| 66 | **Feature-Typ FW: Framework-Agent-Optimierung (FW1=prompt, FW2=settings, FW3=structure, FW4=tests)** | Neue Optimierungs-Kategorie für den General-Improver |
| 67 | **framework/.projects.yaml zentrales Projekt-Register** | MAS verwaltet alle Projekte in .projects.yaml — active_project, devices, status. Wird automatisch aktualisiert bei --project create/switch/rename/delete |
| 68 | **dev_workspace.py --project <cmd>: Mehrere Framework-Systeme verwalten** | 7 CLI-Befehle: list, create (core+sub, KEIN MAS-Sub-Agenten), switch, show, delete (mit Backup), rename. Symlink framework/current → aktives Projekt |
| 69 | **dev_agent_doctor.py --project <name>: Projekt-spezifischer Framework-Scan** | Scant nur das angegebene Projekt. Default: aktives Projekt. --all-projects fuer alle |
| 70 | **dev_build.sh + update.sh bauen NUR aktives Projekt** | .projects.yaml bestimmt welches Projekt in die Distribution kommt. installer.sh installiert dev-team/ als Standard |

### Shell-Regeln (v5 — aus Self-Improve #6 2026-06-13)
| # | Regel | Begründung |
|---|-------|------------|
| 21 | **In bash: IMMER `if` statt `[ ... ] && ...`** | `set -e` bricht bei fehlgeschlagenen Konditionalen ab |
| 22 | **Jedes Skript mit --dry-run testen VOR Execution** | 3 von 3 Fehlern wären im Dry-Run aufgefallen |
