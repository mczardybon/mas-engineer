  ## 36 FEATURE TYPES (COMPLETE MATRIX)
  Detect AND document EVERY found type:

  ### Type A — Settings optimization
  Detect: timeout/max_steps too low or too high.
  - A1: timeout too low → 2+ timeouts in 10 calls → timeout ×1.5
  - A2: max_steps too low → max_steps reached before completion → ×1.5
  - A3: timeout too high → avg-duration <20% timeout → avg×3
  - A4: max_steps too high → avg-Steps <30% max → avg×3

  ### Type B — Prompt improvement
  Detect: Prompt-Quality via User-Feedback.
  - B1: Prompt too vague → User asks 3× "what are you doing?" → clarify role
  - B2: Prompt too long → >500 characters → shorten to ≤300
  - B3: Prompt missing context → Agent asks after info from intake → add
  - B4: Prompt-contradiction → Prompt ≠ instructions → equalize

  ### Type C — Instructions improvement
  Detect: Missing or unclear Rules in Instructions.
  - C1: Missing ⛔-Rule → Agent does forbidden things without ⛔ → insert Rule
  - C2: Unclear flow → Agent asks for sequence/order → number them
  - C3: Missing boundaries → Agent exceeds scope → add boundaries
  - C4: Outdated reference → references to non-existent files → update

  ### Type D — Workflow optimization (dev-mas-engineer.yaml)
  Detect: Problems in the Main-Recipe.
  - D1: step-order wrong → User corrects 3× → reorder
  - D2: Missing step → User says 3× "you forgot X" → insert
  - D3: Redundant step → 80% skipped → remove/optional
  - D4: Unclear question → User answers "?" → make precise

  ### Type E — Detection-pattern
  Detect: pattern in Intention-Parser.
  - E1: Missing Detection → User uses command without match → add pattern
  - E2: False Detection → pattern matches wrong → adjust
  - E3: Dead Detection → 50+ sessions no match → remove

  ### Type F — prompt block
  Detect: Problems in the prompt blocks.
  - F1: Missing Command → Workflow without Prompt-entry → add
  - F2: Sorting → Most frequent not on top → sort by usage
  - F3: Unclear description → User asks "what does --X do?" → make precise
  - F4: ⛔ MISSING MODE-GUARD → prompt has no ⛔⛔⛔ MODE-CHECK → add Mode-Guard

  ### Type G — Health-based optimization (via Guardian HEALTH_REPORT)
  Detect: Guardian-Drift-Data.
  - G1: Degraded agent → score < 80 → optimize Settings/Prompt/Instructions
  - G2: High failure rate → >10% failures/calls → increase timeout or make prompt precise
  - G3: Loops detected → loop=warning or critical → make instructions precise
  - G4: Agent dead → resurrect failed → check: is Agent obsolete? replace?

  ### Type H — Anomaly-based optimization (via Session-Analyst)
  Detect: Anomalies in Session-Data.
  - H1: Duration anomaly → Session >2x avg-duration → check timeout or max_steps
  - H2: token-Anomaly → tokens >3x avg → prompt too long / instructions too verbose
  - H3: Cost anomaly → cost >5x avg → optimize expensive agents (shorten prompt)
  - H4: Stale session → idle >60min → check recipe-Detection (incomplete Task?)

  ### Type I — Prompt-based optimization (via Prompt-Engineer REVIEW)
  Detect: Prompt-Quality.
  - I1: Low Score → <5/10 points → rewrite prompt
  - I2: Missing identity → Criterion 1=0 → "Who am I"-sentence missing → add
  - I3: No ⛔-boundaries → Criterion 3=0 → extract prohibitions from instructions
  - I4: Too long → >500 characters → shorten to ≤300
  - I5: Not self-contained → Criterion 8=0 → prompt without instructions incomprehensible

  ### Type J — Config-based optimization (via Config-Auditor)
  Detect: Config-Problems.
  - J1: Config ❌ found → generate automatic fix-suggestion
  - J2: Config-Value obsolete → references don't match → update

  ### Type K — Doc-based optimization (via Doc-Generator)
  Detect: Doc-Problems.
  - K1: Doc outdated → instructions or prompt don't reflect the current implementation
  - K2: Doc missing → Sub-Agent without documentation → add

  ### Type L — Goose-Infrastructure (via Goose-Admin)
  Detect: Goose-Overhead.
  - L1: Too many sessions → startup slow → goose session rm
  - L2: Too many skills → Overhead → clean skills
  - L3: Logs too large → disk space → rotate logs

  ### Type M — Migration (via Migration-Helper)
  Detect: Migration need.
  - M1: Breaking Changes → Migration before next Build schedule
  - M2: Non-Breaking → Optional, can wait

  ### Type N — Recipe-Management (via Recipe-Manager)
  Detect: Recipe-Problems.
  - N1: Duplicate recipes → Clean
  - N2: Old Version → Update recommended
  - N3: Missing Dependencies → Add

  ### Type O — Deep-Findings (via cat the MAS-files)
  Detect: Structural problems.
  - O1: Instructions ≠ Actual-State → instructions say X (e.g. "16 Checks"), but ls/exec shows Y
  - O2: reference to non-existent file → grep finds import/file/path not in Workspace
  - O3: Outdated counter → "14 Sub-Agents" in manifest.md, but find shows 13 or 15
  - O4: Hardcoded Path → /home/marius/... or absolute path in instructions-block

  ### Type P — Tool-Quality (via cat the dev_*.py/dev_*.sh)
  Detect: Tool-Problems.
  - P1: Syntax-Error → python3 -c "compile(...)" fails
  - P2: Hardcoded Paths in code → /home/marius/... in Python/Shell-Script
  - P3: Import-Error → import or dependency not installed

  ### Type Q — Agent-Calibration (via Session-DB + Settings-Comparison)
  Detect: Over-/Under-dimensioning.
  - Q1: Oversized → max_steps or timeout < 20% utilization → reduce (saves tokens)
  - Q2: Tightly sized → max_steps or timeout > 80% utilization → increase (prevents cancel)
  - Q3: Calibration optimal → 20-80% utilization → ✅ do nothing

  ### Type R — Git-Diff-Quality (via git diff HEAD~1)
  Detect: Code-Quality.
  - R1: Code reduced → lines removed > lines added → ✅ positive
  - R2: Code bloated → lines added > lines removed → ⚠️ negative
  - R3: ⛔-Rules increased → More ⛔ than before → ✅ Safety improved
  - R4: Prompt shortened → prompt:-Block became shorter → ✅ token-Efficiency
  - R5: Complexity increased → New file added → ⚠️ Only if needed

  ### Type S — Agent-Ranking (via Session-DB + Guardian + Prompt)
  Detect: Best/worst Agents.
  - S1: Lowest Score → avg of all metrics worst → optimize
  - S2: Score dropped → ranking-descender → investigate why

  ### Type T — Session-Content-Quality (via User-Message-Analysis)
  Detect: User-Satisfaction.
  - T1: High negative-quote → >20% User-answers are negative → investigate response-quality
  - T2: Many follow-ups → >10% User asks after ("what?", "how?", "again") → make answers precise
  - T3: Positive mood → mostly "yes", "continue", "thanks" → ✅ Quality good

  ### Type U — Success rate trend (via Session-DB about weeks)
  Detect: Trend.
  - U1: Falling Trend → Agent gets worse → intervene
  - U2: Rising Trend → Agent gets better → Optimizations work
  - U3: Stable Trend → ✅ No action needed

  ### Type V — Test-Coverage (via tests/-Directory-Analysis)
  Detect: Test-Gaps.
  - V1: No Tests → Tool has 0 tests in tests/-Directory → retrofit tests
  - V2: Low Coverage → <50% tested → add tests
  - V3: Full Coverage → ✅ all tools tested

  ### Type W — Goose Compatibility (via goose --version)
  Detect: Version-Drift.
  - W1: New Version available → current < latest → check upgrade
  - W2: Breaking Change found → MAS-Adjustment needed → plan migration
  - W3: Current Version → ✅ MAS runs on latest Goose Version

  ### Type X — Change History (via changes.json vs git log)
  Detect: Documentation-Gaps.
  - X1: Missing Documentation → commit without changes.json-entry → add afterwards
  - X2: Unbalanced Distribution → too many patches, too few prompts → shift focus
  - X3: Completely documented → ✅ all changes traceable

  ### Type Y — Recovery-Efficiency (via Session-DB + Guardian-Log)
  Detect: Recovery-Trend.
  - Y1: Recovery slower → recovery after error takes longer → check Timeout/Retry-Logic
  - Y2: Recovery faster → ✅ recovery optimizes itself

  ### Type Z — prompt churn (via changes.json + git log)
  Detect: Change Frequency.
  - Z1: High prompt churn → >5 Changes/30 days on a file → stabilize prompt
  - Z2: Low Churn → ✅ less than 3 Changes/30 days

  ### Type AA — Duration forecast (via Session-DB + History)
  Detect: Performance-Trend.
  - AA1: Rounds get longer → >20% more time than before 5 rounds → reduce analysis
  - AA2: Rounds get shorter → ✅ efficiency rises

  ### Type FW — Framework agent optimization (via dev_agent_doctor.py)
  Detect: framework-Problems.
  - FW1: Prompt faulty → tier-Marking, shorten, add Stop-Rules
  - FW2: Settings wrong → adjust timeout/max_steps
  - FW3: Structure inconsistent → add Input/Output, Constitution-reference
  - FW4: Tests missing → create pytest-Test

  ### Type BB — Framework test (via MAS-Entry-Point)
  Detect: framework Compatibility.
  - BB1: framework Test failed → Changes framework incompatible → ROLLBACK
  - BB2: framework Test passed → ✅ Changes framework-compatible
  - BB3: framework slow (>120s) → check performance-optimization

  ### Type CC — Memory/resource optimization (via Session-DB + Guardian)
  Detect: Resource-Problems.
  - CC1: OOM/MemoryError detected → Sub-Agent cancelled → reduce timeout OR split task
  - CC2: max_turns exceeded (>3 sessions) → increase max_steps (+20)
  - CC3: Timeout-Anomaly (>2 Sigma) → adjust timeout (current * 1.5)
  - CC4: token-Consumption rising (>5%/session) → optimize prompt or reduce max_steps

  ### Type DD — MCP/tool health (via Session-DB Messages)
  Detect: Tool-Problems.
  - DD1: Tool not found in session → register extension/tool
  - DD2: Plugin-Conflict in session → resolve conflict
  - DD3: Extension-Error in session → update/deactivate extension
  - DD4: Tool-Syntax-Error in session → correct tool-call

  ### Type EE — Session corruption (via sqlite3 + changes.json)
  Detect: DB-Problems.
  - EE1: DB read-only → chmod + backup from changes.json
  - EE2: Missing Table → migration or rebuild DB
  - EE3: DB corrupted → backup from changes.json and recreate
  - EE4: No sessions (0 rows) → restart Goose or check path

  ### Type FF — Config-Drift (via diff recipe/ vs best-practices.yaml)
  Detect: Config-Deviation.
  - FF1: timeout deviates from best-practices.yaml → adjust
  - FF2: max_steps deviates from best-practices.yaml → adjust
  - FF3: goose_provider deviates → unify
  - FF4: goose_model deviates → unify

  ### Type GG — Prompt erosion (via grep on Sub-Agent-YAMLs)
  Detect: Prompt-Decay.
  - GG1: ⛔ missing in prompt → add ⛔ {NAME} (v1.0.0)
  - GG2: Version (v1.0.0) missing in prompt → add
  - GG3: Emoji missing in prompt → add
  - GG4: prompt too short (<100 characters) → extend
  - GG5: instructions too long (>2000 characters) → externalize

  ### Type HH — Backup bloat (via find .backups)
  Detect: Backup junk.
  - HH1: >50 Backup-directories in .backups/ → ask user: clean backups?
  - HH2: >100 .bak-files in recipe/sub/ → ask user: delete old .bak?
  - HH3: No backup before last change → use dev_editor.py --backup
  - HH4: Last backup >30 days old → checkpoint --snapshot missing

  ### Type JJ — Installation drift (via diff workspace vs ~/.config/goose/recipes/)
  Detect: Installation-Deviation.
  - JJ1: dev-mas-engineer.yaml differs → execute update.sh --mas
  - JJ2: Sub-Agent missing in ~/.config/goose/recipes/sub/ → copy
  - JJ3: Tool missing in ~/.config/goose/recipes/mas-engineer-tools/ → dev_build.sh + install
  - JJ4: Doc missing in ~/.config/goose/docs/mas-engineer/ → copy

  ### Type MM — YAML structure validation (via python3 yaml.safe_load)
  Detect: Missing or invalid YAML-Structure-Fields in EVERY sub_mas-*.yaml.
  SOURCE: python3 -c "import yaml; yaml.safe_load(open('$f'))" → dict with all keys

  - MM0: YAML-Syntax-Error
    Detection: yaml.safe_load(f) throws exception
    severity: 🔴 high
    detail: "YAML-Syntax-Error in {file} — file corrupt"
    suggestion: "Validate YAML (python3 -c \"yaml.safe_load(open('$f'))\") and correct"

  - MM1: constitution: field missing
    Detection: 'constitution' not in d OR not d['constitution']
    severity: 🔴 high
    detail: "No constitution: field — Agent not bound to SOT"
    suggestion: "add constitution: sub_mas-master-constitution.yaml"

  - MM1b: constitution: points to wrong file
    Detection: 'constitution' in d and d['constitution'] != 'sub_mas-master-constitution.yaml'
    severity: 🟡 medium
    detail: "constitution: points to {d['constitution']} instead of master-constitution"
    suggestion: "correct constitution: sub_mas-master-constitution.yaml"

  - MM2: prompt: field missing or too short
    Detection: 'prompt' not in d or not d['prompt'] or len(str(d['prompt'])) <= 30
    severity: 🔴 high
    detail: "No or too short prompt: field"
    suggestion: "add prompt: with Emoji + Name + Version + ⛔-Boundary (min 30 characters)"

  - MM3: prompt: contains no ⛔
    Detection: '⛔' not in str(d.get('prompt', ''))
    severity: 🟡 medium
    detail: "prompt: contains no ⛔ (Boundary-Indicator)"
    suggestion: "⛔ ONLY {scope} — NO changes in prompt"

  - MM4: title: contains no Emoji
    Detection: No emoji in title string
    severity: 🟢 low
    detail: "title: contains no Emoji"
    suggestion: "add Emoji in title: for visual detection"

  - MM5: settings.timeout outside 60-3600
    Detection: d['settings']['timeout'] not in [60..3600]
    severity: 🟡 medium
    detail: "settings.timeout = {timeout} — outside 60-3600"
    suggestion: "set timeout to 60-3600 (Sweet-Spot: 600)"

  - MM6: settings.max_steps outside 10-500
    Detection: d['settings']['max_steps'] not in [10..500]
    severity: 🟡 medium
    detail: "settings.max_steps = {steps} — outside 10-500"
    suggestion: "set max_steps to 10-500 (Sweet-Spot: 100)"

  ### Type LL — User-Interactions-pattern (via session-reader include_messages=true)
  Detect: Chat-History between User and MAS-Agents (ONLY in REVIEW mode).
  SOURCE: sub_mas-im-session-reader with include_messages=true → data.messages.patterns

  - LL1: User-Correction-pattern
    Detection: patterns.corrections with count >= 2
    severity: count>=3 → 🔴 high | count==2 → 🟡 medium
    detail: "User corrected Agent {N}-times in Session {session_id}: {examples}"
    suggestion: "Add clarification to agent-prompt — User had to correct repeatedly"

  - LL2: User-Confusion-pattern
    Detection: patterns.confusions with count >= 2
    severity: 🟡 medium
    detail: "User showed confusion {N}-times in Session {session_id}: {questions}"
    suggestion: "Add more explicit step-by-step instructions to agent-instructions"

  - LL3: User-Satisfaction-pattern
    Detection: patterns.praises exists
    severity: 🟢 low
    detail: "User satisfied with Agent in Session {session_id} ({N}x praise)"
    suggestion: "No change needed — can serve as positive example"

  - LL4: Session-Cancel-pattern
    Detection: patterns.abandoned_sessions exists (<5 messages + last role=user)
    severity: 🔴 high
    detail: "Session {session_id} cancelled prematurely — only {N} messages, last: '{preview}'"
    suggestion: "Add clearer conclusion to agent-prompt — User aborted without result"

  - LL5: User-Feature-Request-pattern
    Detection: patterns.feature_requests exists
    severity: 🟢 low
    detail: "User wished for feature in Session {session_id}: {requests}"
    suggestion: "Note feature-request — could justify new agent-functionality"

  ### Type KK — SOT source check (via grep on sub_mas-*.yaml)
  Detect: Missing SOT-Hardening-references in Agent-YAMLs.
  FOR each sub_mas-*.yaml in recipe/sub/:
    CHECK: grep -cE "SOT|configs.mas-self" $f = 0?
      → KK1: SOT-reference missing — "Not bound to SOT"
    CHECK: grep -c "dev_rule_checker" $f = 0?
      → KK2: dev_rule_checker missing — "No enforcement"
    CHECK: grep -cE "R01|CONFIRMATION" $f = 0?
      → KK3: R01 (CONFIRMATION) missing — "No confirmation requirement"
    CHECK: grep -cE "R09|DOMAIN|Domain" $f = 0?
      → KK4: R09 (DOMAIN) missing — "No Domain-Separation"
    CHECK: grep -cE "R10|CORONASHIELD" $f = 0? (ONLY at write-Agents)
      → KK5: R10 (CORONASHIELD) missing — "No YAML-Protection"
    SCORE: number of found Ref-Categories (0-5)
      → KK6: Score < 3 → "Only X/5 SOT-Refs — needs ≥3"
