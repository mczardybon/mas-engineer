  ## 36 FEATURE-TYPEN (VOLLSTÄNDIGE MATRIX)
  Erkenne UND dokumentiere JEDEN gefundenen Typ:

  ### Typ A — Settings-Optimierung
  Erkenne: timeout/max_steps zu niedrig oder zu hoch.
  - A1: timeout zu niedrig → 2+ timeouts in 10 calls → timeout ×1.5
  - A2: max_steps zu niedrig → max_steps erreicht vor Abschluss → ×1.5
  - A3: timeout zu hoch → ∅-Dauer <20% timeout → ∅×3
  - A4: max_steps zu hoch → ∅-Steps <30% max → ∅×3

  ### Typ B — Prompt-Verbesserung
  Erkenne: Prompt-Quality via User-Feedback.
  - B1: Prompt zu vage → User fragt 3× "was machst du?" → Rolle clarify
  - B2: Prompt zu lang → >500 Zeichen → auf ≤300 kürzen
  - B3: Prompt fehlt Kontext → Agent fragt nach Infos aus Intake → ergänzen
  - B4: Prompt-Widerspruch → Prompt ≠ instructions → abgleichen

  ### Typ C — Instructions-Verbesserung
  Erkenne: Fehlende oder unklare Regeln in Instructions.
  - C1: Fehlende ⛔-Regel → Agent tut Verbotenes ohne ⛔ → Regel einfügen
  - C2: Unklarer Ablauf → Agent fragt nach Reihenfolge → nummerieren
  - C3: Fehlende Grenzen → Agent überschreitet Scope → Grenzen ergänzen
  - C4: Veraltete Referenz → Referenzen auf nicht-existente Dateien → updaten

  ### Typ D — Workflow-Optimierung (dev-mas-engineer.yaml)
  Erkenne: Probleme im Haupt-Recipe.
  - D1: Schritt-Reihenfolge falsch → User korrigiert 3× → umsortieren
  - D2: Fehlender Schritt → User sagt 3× "du hast X vergessen" → einfügen
  - D3: Redundant Schritt → 80% übersprungen → entfernen/optional
  - D4: Unklare Frage → User antwortet "?" → präzisieren

  ### Typ E — Erkennungsmuster
  Erkenne: Muster im Intention-Parser.
  - E1: Fehlende Erkennung → User nutzt Befehl ohne Match → Muster hinzu
  - E2: Falsche Erkennung → Muster matcht falsch → anpassen
  - E3: Tote Erkennung → 50+ Sessions kein Match → entfernen

  ### Typ F — Prompt-Block
  Erkenne: Probleme in den Prompt-Blöcken.
  - F1: Fehlender Befehl → Workflow ohne Prompt-Eintrag → ergänzen
  - F2: Sortierung → Most frequent nicht oben → nach Nutzung sortieren
  - F3: Unklare Beschreibung → User fragt "was macht --X?" → präzisieren
  - F4: ⛔ FEHLENDER MODUS-GUARD → prompt hat keine ⛔⛔⛔ MODUS-CHECK → Modus-Guard ergänzen

  ### Typ G — Health-basierte Optimierung (via Guardian HEALTH_REPORT)
  Erkenne: Guardian-Drift-Daten.
  - G1: Degradierter Agent → score < 80 → Settings/Prompt/Instructions optimieren
  - G2: Hohe failure-rate → >10% failures/calls → timeout erhöhen oder prompt präzisieren
  - G3: Loops erkannt → loop=warning oder critical → instructions präzisieren
  - G4: Agent dead → resurrect fehlgeschlagen → check: ist Agent obsolet? ersetzen?

  ### Typ H — Anomalie-basierte Optimierung (via Session-Analyst)
  Erkenne: Anomalien in Session-Daten.
  - H1: Dauer-Anomalie → Session >2x ∅-Dauer → timeout oder max_steps check
  - H2: Token-Anomalie → Tokens >3x ∅ → prompt zu lang / instructions zu ausführlich
  - H3: Kosten-Anomalie → Kosten >5x ∅ → teuren Agenten optimieren (prompt kürzen)
  - H4: Stale-Session → idle >60min → recipe-Erkennung check (incompleteer Task?)

  ### Typ I — Prompt-basierte Optimierung (via Prompt-Engineer REVIEW)
  Erkenne: Prompt-Quality.
  - I1: Niedriger Score → <5/10 Punkte → prompt neu schreiben
  - I2: Fehlende Identität → Kriterium 1=0 → "Wer bin ich"-Satz fehlt → ergänzen
  - I3: Keine ⛔-Grenzen → Kriterium 3=0 → Verbote aus instructions extrahieren
  - I4: Zu lang → >500 Zeichen → auf ≤300 kürzen
  - I5: Nicht alleinstehend → Kriterium 8=0 → prompt ohne instructions unverständlich

  ### Typ J — Config-basierte Optimierung (via Config-Auditor)
  Erkenne: Config-Probleme.
  - J1: Config ❌ gefunden → automatischen Fix-Vorschlag generieren
  - J2: Config-Wert obsolete → Referenzen stimmen nicht → updaten

  ### Typ K — Doc-basierte Optimierung (via Doc-Generator)
  Erkenne: Doc-Probleme.
  - K1: Doc veraltet → instructions oder prompt spiegeln nicht die aktuelle Implementierung
  - K2: Doc fehlt → Sub-Agent ohne Dokumentation → ergänzen

  ### Typ L — Goose-Infrastruktur (via Goose-Admin)
  Erkenne: Goose-Overhead.
  - L1: Zu viele Sessions → Startzeit langsam → goose session rm
  - L2: Zu viele Skills → Overhead → Skills bereinigen
  - L3: Logs zu groß → Plattenplatz → Logs rotieren

  ### Typ M — Migration (via Migration-Helper)
  Erkenne: Migrationsbedarf.
  - M1: Breaking Changes → Migration vor next Build einplanen
  - M2: Non-Breaking → Optional, kann warten

  ### Typ N — Recipe-Verwaltung (via Recipe-Manager)
  Erkenne: Recipe-Probleme.
  - N1: Doppelte Recipes → Bereinigen
  - N2: Alte Version → Update empfohlen
  - N3: Fehlende Dependencies → Add

  ### Typ O — Tiefen-Funde (via cat der MAS-Dateien)
  Erkenne: Strukturelle Probleme.
  - O1: Instructions ≠ Ist-Zustand → instructions sagen X (z.B. "16 Checks"), aber ls/exec zeigt Y
  - O2: Referenz auf nicht-existente Datei → grep findet import/file/path nicht im Workspace
  - O3: Veralteter Counter → "14 Sub-Agenten" in manifest.md, aber find zeigt 13 oder 15
  - O4: Hardcodierter Pfad → /home/marius/... oder absoluter Pfad im instructions-Block

  ### Typ P — Tool-Quality (via cat der dev_*.py/dev_*.sh)
  Erkenne: Tool-Probleme.
  - P1: Syntax-Fehler → python3 -c "compile(...)" fails fehl
  - P2: Hardcodierte Pfade im Code → /home/marius/... im Python/Shell-Script
  - P3: Import-Fehler → import oder dependency nicht installiert

  ### Typ Q — Agent-Kalibrierung (via Session-DB + Settings-Vergleich)
  Erkenne: Über-/Unterdimensionierung.
  - Q1: Oversized → max_steps oder timeout < 20% Auslastung → senken (spart Tokens)
  - Q2: Knapp bemessen → max_steps oder timeout > 80% Auslastung → erhöhen (verhindert Abbruch)
  - Q3: Kalibrierung optimal → 20-80% Auslastung → ✅ Nichts tun

  ### Typ R — Git-Diff-Quality (via git diff HEAD~1)
  Erkenne: Code-Quality.
  - R1: Code reduziert → Zeilen entfernt > Zeilen hinzugefügt → ✅ Positiv
  - R2: Code aufgebläht → Zeilen hinzugefügt > Zeilen entfernt → ⚠️ Negativ
  - R3: ⛔-Regeln vermehrt → Mehr ⛔ als vorher → ✅ Safety verbessert
  - R4: Prompt gekürzt → prompt:-Block kürzer geworden → ✅ Token-Effizienz
  - R5: Complexity erhöht → Neue Datei hinzugefügt → ⚠️ Nur wenn needed

  ### Typ S — Agent-Ranking (via Session-DB + Guardian + Prompt)
  Erkenne: Beste/schlechteste Agenten.
  - S1: Niedrigster Score → ∅ aller Metriken am schlechtesten → optimieren
  - S2: Score gefallen → Ranking-Absteiger → untersuchen warum

  ### Typ T — Session-Content-Quality (via User-Message-Analyse)
  Erkenne: User-Zufriedenheit.
  - T1: Hohe Negativ-Quote → >20% User-Antworten sind negativ → Antwort-Quality untersuchen
  - T2: Viele Nachfragen → >10% User fragt nach ("was?", "wie?", "nochmal") → Antworten präzisieren
  - T3: Positive Stimmung → meist "ja", "weiter", "danke" → ✅ Quality gut

  ### Typ U — Erfolgsrate-Trend (via Session-DB über Wochen)
  Erkenne: Trend.
  - U1: Fallender Trend → Agent wird schlechter → eingreifen
  - U2: Steigender Trend → Agent wird besser → Optimierungen wirken
  - U3: Stabiler Trend → ✅ Kein Handlungsbedarf

  ### Typ V — Test-Coverage (via tests/-Verzeichnis-Analyse)
  Erkenne: Test-Gaps.
  - V1: Keine Tests → Tool hat 0 Tests im tests/-Verzeichnis → Test nachrüsten
  - V2: Niedrige Abdeckung → <50% getestet → Tests ergänzen
  - V3: Volle Abdeckung → ✅ Alle Tools getestet

  ### Typ W — Goose-Kompatibilität (via goose --version)
  Erkenne: Version-Drift.
  - W1: Neue Version available → aktuelle < neueste → Upgrade check
  - W2: Breaking Change gefunden → MAS-Anpassung needed → Migration planen
  - W3: Aktuellste Version → ✅ MAS runs auf neuester Goose-Version

  ### Typ X — Changes-Historie (via changes.json vs git log)
  Erkenne: Dokumentations-Gaps.
  - X1: Fehlende Dokumentation → Commit ohne changes.json-Eintrag → nachtragen
  - X2: Unausgewogene Verteilung → zu viele Patches, zu wenige Prompts → Fokus verschieben
  - X3: Complete dokumentiert → ✅ Alle Changes nachvollziehbar

  ### Typ Y — Recovery-Effizienz (via Session-DB + Guardian-Log)
  Erkenne: Recovery-Trend.
  - Y1: Recovery langsamer → Erholung nach Fehler dauert longer → Timeout/Retry-Logik check
  - Y2: Recovery schneller → ✅ Erholung optimiert sich

  ### Typ Z — Prompt-Churn (via changes.json + git log)
  Erkenne: Changesfrequenz.
  - Z1: Hoher Prompt-Churn → >5 Changes/30 Tage an einer Datei → Prompt stabilisieren
  - Z2: Niedriger Churn → ✅ Weniger als 3 Changes/30 Tage

  ### Typ AA — Dauer-Vorhersage (via Session-DB + Verlauf)
  Erkenne: Performance-Trend.
  - AA1: Runden werden longer → >20% mehr Zeit als vor 5 Runden → Analysen reduzieren
  - AA2: Runden werden kürzer → ✅ Effizienz steigt

  ### Typ FW — Framework-Agent-Optimierung (via dev_agent_doctor.py)
  Erkenne: Framework-Probleme.
  - FW1: Prompt fehlerhaft → tier-Markierung, kürzen, Stop-Regeln ergänzen
  - FW2: Settings falsch → timeout/max_steps anpassen
  - FW3: Struktur inkonsistent → Input/Output, Constitution-Referenz ergänzen
  - FW4: Tests fehlen → pytest-Test erstellen

  ### Typ BB — Framework-Test (via MAS-Einstiegspunkt)
  Erkenne: Framework-Kompatibilität.
  - BB1: Framework-Test fehlgeschlagen → Changes Framework inkompatibel → ROLLBACK
  - BB2: Framework-Test bestanden → ✅ Changes Framework-kompatibel
  - BB3: Framework langsam (>120s) → Performance-Optimierung check

  ### Typ CC — Speicher/Resource-Optimierung (via Session-DB + Guardian)
  Erkenne: Resource-Probleme.
  - CC1: OOM/MemoryError erkannt → Sub-Agent abgebrochen → timeout reduzieren ODER Task splitten
  - CC2: max_turns überschritten (>3 Sessions) → max_steps erhöhen (+20)
  - CC3: Timeout-Anomalie (>2 Sigma) → timeout anpassen (aktuell * 1.5)
  - CC4: Token-Verbrauch steigend (>5%/Session) → Prompt optimieren oder max_steps reduzieren

  ### Typ DD — MCP/Tool-Health (via Session-DB Messages)
  Erkenne: Tool-Probleme.
  - DD1: Tool not found in Session → Extension/Tool registrieren
  - DD2: Plugin-Konflikt in Session → Konflikt auflösen
  - DD3: Extension-Fehler in Session → Extension updaten/deaktivieren
  - DD4: Tool-Syntax-Fehler in Session → Tool-Aufruf korrigieren

  ### Typ EE — Session-Korruption (via sqlite3 + changes.json)
  Erkenne: DB-Probleme.
  - EE1: DB read-only → chmod + Backup aus changes.json
  - EE2: Fehlende Tabelle → Migration oder DB neubauen
  - EE3: DB beschädigt → Backup aus changes.json wiederherstellen
  - EE4: Keine Sessions (0 rows) → Goose neustarten oder Pfad check

  ### Typ FF — Config-Drift (via diff recipe/ vs best-practices.yaml)
  Erkenne: Config-Abweichung.
  - FF1: timeout weicht ab von best-practices.yaml → anpassen
  - FF2: max_steps weicht ab von best-practices.yaml → anpassen
  - FF3: goose_provider weicht ab → vereinheitlichen
  - FF4: goose_model weicht ab → vereinheitlichen

  ### Typ GG — Prompt-Erosion (via grep auf Sub-Agent-YAMLs)
  Erkenne: Prompt-Verfall.
  - GG1: ⛔ fehlt im prompt → ⛔ {NAME} (v1.0.0) ergänzen
  - GG2: Version (v1.0.0) fehlt im prompt → ergänzen
  - GG3: Emoji fehlt im prompt → ergänzen
  - GG4: prompt zu kurz (<100 Zeichen) → erweitern
  - GG5: instructions zu lang (>2000 Zeichen) → auslagern

  ### Typ HH — Backup-Bloat (via find .backups)
  Erkenne: Backup-Müll.
  - HH1: >50 Backup-Verzeichnisse in .backups/ → User fragen: Backups bereinigen?
  - HH2: >100 .bak-Dateien in recipe/sub/ → User fragen: Alte .bak delete?
  - HH3: Kein Backup vor letzter Change → dev_editor.py --backup nutzen
  - HH4: Letztes Backup >30 Tage alt → checkpoint --snapshot empfehlen

  ### Typ JJ — Installations-Drift (via diff workspace vs ~/.config/goose/recipes/)
  Erkenne: Installations-Abweichung.
  - JJ1: dev-mas-engineer.yaml unterschiedlich → update.sh --mas execute
  - JJ2: Sub-Agent fehlt in ~/.config/goose/recipes/sub/ → kopieren
  - JJ3: Tool fehlt in ~/.config/goose/recipes/mas-engineer-tools/ → dev_build.sh + install
  - JJ4: Doc fehlt in ~/.config/goose/docs/mas-engineer/ → kopieren

  ### Typ MM — YAML-Struktur-Validierung (via python3 yaml.safe_load)
  Erkenne: Fehlende oder invalide YAML-Struktur-Felder in JEDEM sub_mas-*.yaml.
  QUELLE: python3 -c "import yaml; yaml.safe_load(open('$f'))" → dict mit allen Keys

  - MM0: YAML-Syntax-Fehler
    Erkennung: yaml.safe_load(f) wirft Exception
    severity: 🔴 hoch
    detail: "YAML-Syntax-Fehler in {file} — Datei korrupt"
    vorschlag: "YAML validieren (python3 -c \"yaml.safe_load(open('$f'))\") und korrigieren"

  - MM1: constitution: Feld fehlt
    Erkennung: 'constitution' not in d OR not d['constitution']
    severity: 🔴 hoch
    detail: "Kein constitution: Feld — Agent nicht an SOT gebunden"
    vorschlag: "constitution: sub_mas-master-constitution.yaml hinzufügen"

  - MM1b: constitution: zeigt auf falsche Datei
    Erkennung: 'constitution' in d and d['constitution'] != 'sub_mas-master-constitution.yaml'
    severity: 🟡 mittel
    detail: "constitution: zeigt auf {d['constitution']} statt master-constitution"
    vorschlag: "constitution: sub_mas-master-constitution.yaml korrigieren"

  - MM2: prompt: Feld fehlt oder zu kurz
    Erkennung: 'prompt' not in d or not d['prompt'] or len(str(d['prompt'])) <= 30
    severity: 🔴 hoch
    detail: "Kein oder zu kurzes prompt: Feld"
    vorschlag: "prompt: mit Emoji + Name + Version + ⛔-Boundary hinzufügen (min 30 Zeichen)"

  - MM3: prompt: enthält kein ⛔
    Erkennung: '⛔' not in str(d.get('prompt', ''))
    severity: 🟡 mittel
    detail: "prompt: enthält kein ⛔ (Boundary-Indikator)"
    vorschlag: "⛔ NUR {scope} — KEINE Changes in prompt aufnehmen"

  - MM4: title: enthält kein Emoji
    Erkennung: No emoji in title string
    severity: 🟢 niedrig
    detail: "title: enthält kein Emoji"
    vorschlag: "Emoji in title: ergänzen für visuelle Erkennung"

  - MM5: settings.timeout ausserhalb 60-3600
    Erkennung: d['settings']['timeout'] not in [60..3600]
    severity: 🟡 mittel
    detail: "settings.timeout = {timeout} — ausserhalb 60-3600"
    vorschlag: "timeout auf 60-3600 setzen (Sweet-Spot: 600)"

  - MM6: settings.max_steps ausserhalb 10-500
    Erkennung: d['settings']['max_steps'] not in [10..500]
    severity: 🟡 mittel
    detail: "settings.max_steps = {steps} — ausserhalb 10-500"
    vorschlag: "max_steps auf 10-500 setzen (Sweet-Spot: 100)"

  ### Typ LL — User-Interaktions-Muster (via session-reader include_messages=true)
  Erkenne: Chat-Verlauf zwischen User und MAS-Agenten (NUR im REVIEW-Modus).
  QUELLE: sub_mas-im-session-reader mit include_messages=true → data.messages.patterns

  - LL1: User-Korrektur-Muster
    Erkennung: patterns.corrections mit count >= 2
    severity: count>=3 → 🔴 hoch | count==2 → 🟡 mittel
    detail: "User korrigierte Agent {N}-mal in Session {session_id}: {examples}"
    vorschlag: "Agent-Prompt um Klarstellung ergänzen — User musste wiederholt korrigieren"

  - LL2: User-Verwirrungs-Muster
    Erkennung: patterns.confusions mit count >= 2
    severity: 🟡 mittel
    detail: "User zeigte Verwirrung {N}-mal in Session {session_id}: {questions}"
    vorschlag: "Agent-Instructions um explizitere Schritt-für-Schritt-Anleitung ergänzen"

  - LL3: User-Zufriedenheits-Muster
    Erkennung: patterns.praises existiert
    severity: 🟢 niedrig
    detail: "User zufrieden mit Agent in Session {session_id} ({N}x Lob)"
    vorschlag: "Keine Change needed — kann als Positiv-Beispiel dienen"

  - LL4: Session-Abbruch-Muster
    Erkennung: patterns.abandoned_sessions existiert (<5 Messages + letzte role=user)
    severity: 🔴 hoch
    detail: "Session {session_id} vorzeitig abgebrochen — nur {N} Messages, letzte: '{preview}'"
    vorschlag: "Agent-Prompt um klareren Abschluss ergänzen — User brach ab ohne Ergebnis"

  - LL5: User-Feature-Request-Muster
    Erkennung: patterns.feature_requests existiert
    severity: 🟢 niedrig
    detail: "User wished sich Feature in Session {session_id}: {requests}"
    vorschlag: "Feature-Request notieren — could neue Agenten-Funktion rechtfertigen"

  ### Typ KK — SOT-Source-Check (via grep auf sub_mas-*.yaml)
  Erkenne: Fehlende SOT-Hardening-Referenzen in Agent-YAMLs.
  FOR jedes sub_mas-*.yaml in recipe/sub/:
    PRUEFE: grep -cE "SOT|configs.mas-self" $f = 0?
      → KK1: SOT-Referenz fehlt — "Nicht an SOT angebunden"
    PRUEFE: grep -c "dev_rule_checker" $f = 0?
      → KK2: dev_rule_checker fehlt — "Kein Enforcement"
    PRUEFE: grep -cE "R01|BESTAETIGUNG" $f = 0?
      → KK3: R01 (BESTAETIGUNG) fehlt — "Keine Confirmation requirement"
    PRUEFE: grep -cE "R09|DOMAIN|Domain" $f = 0?
      → KK4: R09 (DOMAIN) fehlt — "Keine Domain-Trennung"
    PRUEFE: grep -cE "R10|CORONASHIELD" $f = 0? (NUR bei Schreib-Agenten)
      → KK5: R10 (CORONASHIELD) fehlt — "Kein YAML-Schutz"
    SCORE: Anzahl der gefundenen Ref-Kategorien (0-5)
      → KK6: Score < 3 → "Nur X/5 SOT-Refs — needs ≥3"
