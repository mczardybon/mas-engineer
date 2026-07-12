  ## 36 FEATURE TYPES (COMPLETE MATRIX)
  Detect AND document EVERY found type:

  ### Type A — Settings optimization
  Detect: timeout/max_steps too low oder too high.
  - A1: timeout too low → 2+ timeouts in 10 calls → timeout ×1.5
  - A2: max_steps too low → max_steps erreicht before Abschluss → ×1.5
  - A3: timeout too high → ∅-duration <20% timeout → ∅×3
  - A4: max_steps too high → ∅-Steps <30% max → ∅×3

  ### Type B — Prompt improvement
  Detect: Prompt-Quality via User-Feedback.
  - B1: Prompt too vague → User asks 3× "what are you doing?" → role clarify
  - B2: Prompt too long → >500 characters → auf ≤300 shorten
  - B3: Prompt missing context → Agent asks after Infos from Intake → add
  - B4: Prompt-Widerspruch → Prompt ≠ instructions → abequalen

  ### Type C — Instructions improvement
  Detect: Missing oder uncleare Rules in Instructions.
  - C1: Missing ⛔-Rule → Agent tut Verbotenes without ⛔ → Rule insert
  - C2: Unklarer Ablauf → Agent asks for sequence/order → numberieren
  - C3: Missing boundaries → Agent overschreitet Scope → boundaries add
  - C4: Veraltete reference → referenceen auf not-existente files → updaten

  ### Type D — Workflow optimization (dev-mas-engineer.yaml)
  Detect: Probleme im Main-Recipe.
  - D1: step-Reihenfolge wrong → User korrigiert 3× → umsortieren
  - D2: Missingr step → User sagt 3× "du hast X vergessen" → insert
  - D3: Redundant step → 80% oversprungen → remove/optional
  - D4: Unklare question → User ansvalue "?" → make precise

  ### Type E — Detectionspattern
  Detect: pattern im Intention-Parser.
  - E1: Missing Detection → User nutzt Command without Match → pattern hinzu
  - E2: Falsee Detection → pattern matcht wrong → anpassen
  - E3: Tote Detection → 50+ Sessions no Match → remove

  ### Type F — prompt block
  Detect: Probleme in den prompt blocks.
  - F1: Missingr Command → Workflow without Prompt-entry → add
  - F2: Sortierung → Most frequent not oben → after Usage sort
  - F3: Unklare description → User asks "was macht --X?" → make precise
  - F4: ⛔ MISSING MODE-GUARD → prompt has no ⛔⛔⛔ MODE-CHECK → add Mode-Guard

  ### Type G — Health-basierte Optimierung (via Guardian HEALTH_REPORT)
  Detect: Guardian-Drift-Data.
  - G1: Degraded agent → score < 80 → Settings/Prompt/Instructions optimize
  - G2: High failure rate → >10% failures/calls → timeout increase oder prompt make precise
  - G3: Loops detected → loop=warning oder critical → instructions make precise
  - G4: Agent dead → resurrect failed → check: ist Agent obsolet? replace?

  ### Type H — Anomalie-basierte Optimierung (via Session-Analyst)
  Detect: Anomalien in Session-Data.
  - H1: Duration anomaly → Session >2x ∅-duration → timeout oder max_steps check
  - H2: token-Anomalie → tokens >3x ∅ → prompt too long / instructions zu verbose
  - H3: Cost anomaly → cost >5x ∅ → Optimize expensive agents (prompt shorten)
  - H4: Stale session → idle >60min → recipe-Detection check (incomplete Task?)

  ### Type I — Prompt-basierte Optimierung (via Prompt-Engineer REVIEW)
  Detect: Prompt-Quality.
  - I1: Lower Score → <5/10 Punkte → prompt new write
  - I2: Missing identity → Kriterium 1=0 → "Wer am ich"-Satz missing → add
  - I3: No ⛔-boundaries → Kriterium 3=0 → Verbote from instructions extrahieren
  - I4: Zu long → >500 characters → auf ≤300 shorten
  - I5: Nicht allinstehend → Kriterium 8=0 → prompt without instructions incomprehensible

  ### Type J — Config-basierte Optimierung (via Config-Auditor)
  Detect: Config-Probleme.
  - J1: Config ❌ found → automatischen Fix-suggestion generate
  - J2: Config-Value obsolete → referenceen stimmen not → updaten

  ### Type K — Doc-basierte Optimierung (via Doc-Generator)
  Detect: Doc-Probleme.
  - K1: Doc outdated → instructions oder prompt spiegeln not die current Implementation
  - K2: Doc missing → Sub-Agent without Documentation → add

  ### Type L — Goose-Infrastruktur (via Goose-Admin)
  Detect: Goose-Overhead.
  - L1: Too many sessions → Startzeit longsam → goose session rm
  - L2: Too many skills → Overhead → Skills clean
  - L3: Logs too large → Plattenplatz → Logs rotate

  ### Type M — Migration (via Migration-Helper)
  Detect: Migration need.
  - M1: Breaking Changes → Migration before next Build schedule
  - M2: Non-Breaking → Optional, can warten

  ### Type N — Recipe-Management (via Recipe-Manager)
  Detect: Recipe-Probleme.
  - N1: Duplicate recipes → Clean
  - N2: Old Version → Update recommended
  - N3: Missing Dependencies → Add

  ### Type O — Tiefen-Funde (via cat der MAS-files)
  Detect: Strukturelle Probleme.
  - O1: Instructions ≠ Ist-State → instructions sagen X (z.B. "16 Checks"), aber ls/exec zeigt Y
  - O2: reference auf not-existente file → grep finds import/file/path not im Workspace
  - O3: Veralteter Counter → "14 Sub-Agents" in manifest.md, aber find zeigt 13 oder 15
  - O4: Hardcodierter Path → /home/marius/... oder absoluter Path im instructions-Block

  ### Type P — Tool-Quality (via cat der dev_*.py/dev_*.sh)
  Detect: Tool-Probleme.
  - P1: Syntax-Error → python3 -c "compile(...)" fails fehl
  - P2: Hardcodierte Pathe im Code → /home/marius/... im Python/Shell-Script
  - P3: Import-Error → import oder dependency not installiert

  ### Type Q — Agent-Calibration (via Session-DB + Settings-Comparison)
  Detect: About-/Unterdimensionierung.
  - Q1: Oversized → max_steps oder timeout < 20% utilization → reduce (spart tokens)
  - Q2: Tightly sized → max_steps oder timeout > 80% utilization → increase (verhindert Cancel)
  - Q3: Calibration optimal → 20-80% utilization → ✅ Nothing tun

  ### Type R — Git-Diff-Quality (via git diff HEAD~1)
  Detect: Code-Quality.
  - R1: Code reduced → lines removed > lines added → ✅ positiveee
  - R2: Code bloated → lines added > lines removed → ⚠️ negativeee
  - R3: ⛔-Rules vermehrt → Mehr ⛔ als beforeher → ✅ Safety improved
  - R4: Prompt shortened → prompt:-Block shorter geworden → ✅ token-Effizienz
  - R5: Complexity increased → New file added → ⚠️ Only if needed

  ### Type S — Agent-Ranking (via Session-DB + Guardian + Prompt)
  Detect: Beste/schlechteste Agents.
  - S1: Lowster Score → ∅ allr Metriken am schlechtest → optimize
  - S2: Score gefalln → Ranking-Absteiger → untersuchen warum

  ### Type T — Session-Content-Quality (via User-Message-Analyse)
  Detect: User-Zufriedenheit.
  - T1: Hohe negativeee-Quote → >20% User-answers are negative → Response-Quality untersuchen
  - T2: Many follow-ups → >10% User asks after ("was?", "wie?", "again") → answers make precise
  - T3: positiveeee Stimmung → meist "ja", "weiter", "danke" → ✅ Quality gut

  ### Type U — Success rate trend (via Session-DB about Wochen)
  Detect: Trend.
  - U1: Fallnder Trend → Agent will worse → eingreifen
  - U2: Steigender Trend → Agent will better → Optimierungen wirken
  - U3: Stabiler Trend → ✅ No Handlungsbedarf

  ### Type V — Test-Coverage (via tests/-Directory-Analyse)
  Detect: Test-Gaps.
  - V1: No Tests → Tool has 0 Tests im tests/-Directory → Test retrofit
  - V2: Lowe Abdeckung → <50% getestet → Tests add
  - V3: Volle Abdeckung → ✅ All Tools getestet

  ### Type W — Goose Compatibility (via goose --version)
  Detect: Version-Drift.
  - W1: New Version available → current < latest → Upgrade check
  - W2: Breaking Change found → MAS-Adjustment needed → Migration planen
  - W3: Currentste Version → ✅ MAS runs auf latest Goose Version

  ### Type X — Change History (via changes.json vs git log)
  Detect: Documentations-Gaps.
  - X1: Missing Documentation → commit without changes.json-entry → aftertragen
  - X2: Unfromgewogene Verteilung → too many Patches, zu wenige Prompts → Fokus move
  - X3: Complete documented → ✅ All Changes aftervollziehbar

  ### Type Y — Recovery-Effizienz (via Session-DB + Guardian-Log)
  Detect: Recovery-Trend.
  - Y1: Recovery longsamer → Erholung after Error dauert longer → Timeout/Retry-Logik check
  - Y2: Recovery schneller → ✅ Erholung optimiert sich

  ### Type Z — prompt churn (via changes.json + git log)
  Detect: Change Frequency.
  - Z1: Hoher prompt churn → >5 Changes/30 Tage an a file → Prompt stabilize
  - Z2: Lower Churn → ✅ Weniger als 3 Changes/30 Tage

  ### Type AA — Duration forecast (via Session-DB + Verlauf)
  Detect: Performance-Trend.
  - AA1: Runden will longer → >20% mehr time als before 5 Runden → Analysen reduce
  - AA2: Runden will shorter → ✅ Effizienz steigt

  ### Type FW — Framework agent optimization (via dev_agent_doctor.py)
  Detect: framework-Probleme.
  - FW1: Prompt faulty → tier-Markierung, shorten, Stop-Rules add
  - FW2: Settings wrong → timeout/max_steps anpassen
  - FW3: Struktur inconsistent → Input/Output, Constitution-reference add
  - FW4: Tests missing → pytest-Test create

  ### Type BB — Framework test (via MAS-Einstiegspunkt)
  Detect: framework Compatibility.
  - BB1: framework Test failed → Changes framework incompatible → ROLLBACK
  - BB2: framework Test bestanden → ✅ Changes framework-kompatibel
  - BB3: framework longsam (>120s) → Performance-Optimierung check

  ### Type CC — Memory/resource optimization (via Session-DB + Guardian)
  Detect: Resource-Probleme.
  - CC1: OOM/MemoryError erkannt → Sub-Agent cancelled → timeout reduce OR Task splitten
  - CC2: max_turns exceeded (>3 Sessions) → max_steps increase (+20)
  - CC3: Timeout-Anomalie (>2 Sigma) → timeout anpassen (current * 1.5)
  - CC4: token-Verbrauch steigend (>5%/Session) → Prompt optimize oder max_steps reduce

  ### Type DD — MCP/tool health (via Session-DB Messages)
  Detect: Tool-Probleme.
  - DD1: Tool not found in Session → Extension/Tool registrieren
  - DD2: Plugin-Konflikt in Session → Konflikt resolve
  - DD3: Extension-Error in Session → Extension updaten/deactiveieren
  - DD4: Tool-Syntax-Error in Session → Tool-call korrigieren

  ### Type EE — Session corruption (via sqlite3 + changes.json)
  Detect: DB-Probleme.
  - EE1: DB read-only → chmod + Backup from changes.json
  - EE2: Missing Table → Migration oder DB neubauen
  - EE3: DB corrupted → Backup from changes.json againhcreate
  - EE4: No Sessions (0 rows) → Goose neustart oder Path check

  ### Type FF — Config-Drift (via diff recipe/ vs best-practices.yaml)
  Detect: Config-Deviation.
  - FF1: timeout weicht ab von best-practices.yaml → anpassen
  - FF2: max_steps weicht ab von best-practices.yaml → anpassen
  - FF3: goose_provider weicht ab → vereinheitlichen
  - FF4: goose_model weicht ab → vereinheitlichen

  ### Type GG — Prompt erosion (via grep auf Sub-Agent-YAMLs)
  Detect: Prompt-Verfall.
  - GG1: ⛔ missing im prompt → ⛔ {NAME} (v1.0.0) add
  - GG2: Version (v1.0.0) missing im prompt → add
  - GG3: Emoji missing im prompt → add
  - GG4: prompt zu short (<100 characters) → extend
  - GG5: instructions too long (>2000 characters) → fromlagern

  ### Type HH — Backup bloat (via find .backups)
  Detect: Backup junk.
  - HH1: >50 Backup-directoryse in .backups/ → User ask: Backups clean?
  - HH2: >100 .bak-files in recipe/sub/ → User ask: Old .bak delete?
  - HH3: No Backup before letzter Change → dev_editor.py --backup nutzen
  - HH4: Letztes Backup >30 Tage old → checkpoint --snapshot empmissing

  ### Type JJ — Installation drift (via diff workspace vs ~/.config/goose/recipes/)
  Detect: Installations-Deviation.
  - JJ1: dev-mas-engineer.yaml unterschiedlich → update.sh --mas execute
  - JJ2: Sub-Agent missing in ~/.config/goose/recipes/sub/ → copyren
  - JJ3: Tool missing in ~/.config/goose/recipes/mas-engineer-tools/ → dev_build.sh + install
  - JJ4: Doc missing in ~/.config/goose/docs/mas-engineer/ → copyren

  ### Type MM — YAML structure validation (via python3 yaml.safe_load)
  Detect: Missing oder invalide YAML-Struktur-Felder in JEDEM sub_mas-*.yaml.
  QUELLE: python3 -c "import yaml; yaml.safe_load(open('$f'))" → dict mit alln Keys

  - MM0: YAML-Syntax-Error
    Detection: yaml.safe_load(f) wirft Exception
    severity: 🔴 hoch
    detail: "YAML-Syntax-Error in {file} — file korrupt"
    beforeschlag: "YAML validate (python3 -c \"yaml.safe_load(open('$f'))\") und korrigieren"

  - MM1: constitution: Feld missing
    Detection: 'constitution' not in d OR not d['constitution']
    severity: 🔴 hoch
    detail: "No constitution: Feld — Agent not an SOT gebunden"
    beforeschlag: "constitution: sub_mas-master-constitution.yaml add"

  - MM1b: constitution: points to falsee file
    Detection: 'constitution' in d and d['constitution'] != 'sub_mas-master-constitution.yaml'
    severity: 🟡 mittel
    detail: "constitution: points to {d['constitution']} instead of master-constitution"
    beforeschlag: "constitution: sub_mas-master-constitution.yaml korrigieren"

  - MM2: prompt: Feld missing oder zu short
    Detection: 'prompt' not in d or not d['prompt'] or len(str(d['prompt'])) <= 30
    severity: 🔴 hoch
    detail: "No oder zu shortes prompt: Feld"
    beforeschlag: "prompt: mit Emoji + Name + Version + ⛔-Boundary add (min 30 characters)"

  - MM3: prompt: contains no ⛔
    Detection: '⛔' not in str(d.get('prompt', ''))
    severity: 🟡 mittel
    detail: "prompt: contains no ⛔ (Boundary-Indikator)"
    beforeschlag: "⛔ ONLY {scope} — NO changes in prompt aufnehmen"

  - MM4: title: contains no Emoji
    Detection: No emoji in title string
    severity: 🟢 niedrig
    detail: "title: contains no Emoji"
    beforeschlag: "Emoji in title: add for visuelle Detection"

  - MM5: settings.timeout fromserhalb 60-3600
    Detection: d['settings']['timeout'] not in [60..3600]
    severity: 🟡 mittel
    detail: "settings.timeout = {timeout} — fromserhalb 60-3600"
    beforeschlag: "timeout auf 60-3600 setn (Sweet-Spot: 600)"

  - MM6: settings.max_steps fromserhalb 10-500
    Detection: d['settings']['max_steps'] not in [10..500]
    severity: 🟡 mittel
    detail: "settings.max_steps = {steps} — fromserhalb 10-500"
    beforeschlag: "max_steps auf 10-500 setn (Sweet-Spot: 100)"

  ### Type LL — User-Interactions-pattern (via session-reader include_messages=true)
  Detect: Chat-Verlauf between User und MAS-Agents (ONLY im REVIEW mode).
  QUELLE: sub_mas-im-session-reader mit include_messages=true → data.messages.patterns

  - LL1: User-Korrektur-pattern
    Detection: patterns.corrections mit count >= 2
    severity: count>=3 → 🔴 hoch | count==2 → 🟡 mittel
    detail: "User korrigierte Agent {N}-mal in Session {session_id}: {examples}"
    beforeschlag: "Agent-Prompt um clarification add — User musste againholt korrigieren"

  - LL2: User-Verwirrungs-pattern
    Detection: patterns.confusions mit count >= 2
    severity: 🟡 mittel
    detail: "User zeigte Verwirrung {N}-mal in Session {session_id}: {questions}"
    beforeschlag: "Agent-Instructions um explicitre step-by-step instructions add"

  - LL3: User-Zufriedenheits-pattern
    Detection: patterns.praises exists
    severity: 🟢 niedrig
    detail: "User zufrieden mit Agent in Session {session_id} ({N}x Lob)"
    beforeschlag: "No Change needed — can als positiveee-Example dienen"

  - LL4: Session-Cancel-pattern
    Detection: patterns.abandoned_sessions exists (<5 Messages + letzte role=user)
    severity: 🔴 hoch
    detail: "Session {session_id} beforezeitig cancelled — only {N} Messages, letzte: '{preview}'"
    beforeschlag: "Agent-Prompt um klareren Abschluss add — User brach ab without Result"

  - LL5: User-Feature-Request-pattern
    Detection: patterns.feature_requests exists
    severity: 🟢 niedrig
    detail: "User wished sich Feature in Session {session_id}: {requests}"
    beforeschlag: "Feature-Request notieren — could new Agents-Function rechtfertigen"

  ### Type KK — SOT source check (via grep auf sub_mas-*.yaml)
  Detect: Missing SOT-Hardening-referenceen in Agent-YAMLs.
  FOR jedes sub_mas-*.yaml in recipe/sub/:
    CHECK: grep -cE "SOT|configs.mas-self" $f = 0?
      → KK1: SOT-reference missing — "Nicht an SOT angebunden"
    CHECK: grep -c "dev_rule_checker" $f = 0?
      → KK2: dev_rule_checker missing — "No Enforcement"
    CHECK: grep -cE "R01|CONFIRMATION" $f = 0?
      → KK3: R01 (CONFIRMATION) missing — "No Confirmation requirement"
    CHECK: grep -cE "R09|DOMAIN|Domain" $f = 0?
      → KK4: R09 (DOMAIN) missing — "No Domain-Trennung"
    CHECK: grep -cE "R10|CORONASHIELD" $f = 0? (ONLY at Schreib-Agents)
      → KK5: R10 (CORONASHIELD) missing — "No YAML-Schutz"
    SCORE: Number der founden Ref-Kategorien (0-5)
      → KK6: Score < 3 → "Only X/5 SOT-Refs — needs ≥3"
