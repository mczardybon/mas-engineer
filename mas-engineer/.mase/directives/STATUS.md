# Directives Status Tracker

Wird von mas-engineer IM-pipeline automatisch aktualisiert wenn
PHASEN abgeschlossen werden. Auch vom User manuell editierbar
wenn externe commits (z.B. fix-commits aus anderen R-Runs)
eine PHASE effektiv abschliessen.

## Aktive Direktiven

### R110-94-historical-drift-check
- **Datei**: `R110-94-historical-drift-check.md` (211 lines, 2026-08-04)
- **Ziel**: dev_category_drift.py als pre-push-validator Check 16+ integrieren
- **Created**: 27d8cb7 (R110-94, 2026-08-04)
- **Refs**: R110-92 (standalone detector, ee0b242), R110-90 (rebase precedent),
  R110-89 (validator evidence), R110-78 (spec-drift lesson)

| PHASE | DIREKTIVE | Status | Started | Completed | Commit | Effekt |
|---|---|---|---|---|---|---|
| 1 | validator Check 16+ + dev_category_drift.py | DONE | 2026-08-04 | 2026-08-04 | 27d8cb7 | 5-cat-drift in last 30d blockt pre-push |

**Overall**: 1/1 PHASE done (R110-94 komplett). Status: ARCHIVED-READY
(alle 6 acceptance-kriterien 206-212 erfuellt; validator v2.2.0,
Check 16+ in instructions L714-777, drift detector exits 0 mit
drift_count=0 + 4 conform + 479 exempt + 490 total).

Test-fixture-template: `.mase/directives/test-fixtures/test_check_16_drift_template.py`
(5 skip-tests, optional CI-integration, nicht pytest-discoverable solange
in test-fixtures/).

### R110-78-spec-drift
- **Datei**: `R110-78-spec-drift.md` (528 lines, 2026-08-03)
- **Status**: ARCHIVED-READY (alle 5 PHASEN done, PHASE 4 hermes
  done, R110-78 lesson komplett geschlossen, R110-123 entries
  updated + this closure summary added)
- **Ziel**: mas-engineer spec-drift-resistent machen
- **Created**: 04afe4a (R110-79)
- **Refactoring**: 5f9418e (R110-80), b8f8bc7 (R110-81),
  634f626 (R110-82), 417650d (R110-83/84), f5204f5 (R110-85)
- **Erstellt nach**: 9c73100 (R110-71 spec-drift incident
  admitted)

| PHASE | DIREKTIVE | Status | Started | Completed | Commit | Effekt |
|---|---|---|---|---|---|---|
| 1 | validator + pytest | DONE | 2026-08-03 | 2026-08-04 | 27d8cb7 (R110-94 Check 16+ drift) + c005db6 (R110-100 Check 17 pytest) | spec-drift vor push blocken (drift + pytest-count-mismatch) |
| 2 | SD-* finding | DONE | 2026-08-04 | 2026-08-04 | 3b80259 (R110-106) | spec-drift in IM-scans finden — dev_im_finder_scan.py:check_spec_drift() (4 test-cases), im-finder recipe Z.36 ruft standalone-script auf, 7 SD-* findings in R110-108 run verifiziert |
| 3 | dev_spec_invariant.py | DONE | 2026-08-04 | 2026-08-04 | R110-118 (sub_mas-self-audit agent + tools/dev_self_audit.py + tools/dev_spec_invariant.py + Check 18 in pre-push) | R110-78 PHASE 3 closed: self-audit agent auditiert recipe/instructions/ (Patterns A/B/C), spec-invariant Check 18 blockt test-vs-recipe count-drift vor push |
| 3b | self-audit in IM-pipeline | DONE | 2026-08-04 | 2026-08-04 | R110-120 (STEP 0.6 in sub_mas-im-finder.md + sub_mas-self-audit in im-finder sub_recipes + test_step_0_6) | PHASE 3b closed: sub_mas-self-audit auto-invoked in improvement-pipeline (im-finder STEP 0.6, MM9-EXT findings, BLOCKER fail-fast vor findings-write) |
| 3c | STALE-LITERAL Pattern B fix | DONE | 2026-08-04 | 2026-08-04 | R110-121 (sales→dev-team in 3 files + Pattern B bug-fix + 1 Test) | PHASE 3c closed: 0 STALE-LITERAL findings, im-finder L146 false positive fixed |
| 3d | scanner Pattern A+B | DONE | 2026-08-04 | 2026-08-04 | 5b82fab (R110-124) | PHASE 3d closed: dev_im_finder_scan.py:check_hardcode_stale() + check_stale_literal() wrap dev_self_audit Patterns A+B (lazy importlib import), 6 HARDCODE-STALE-* types emit (18 occurrences on recipe/instructions/), 2 new tests pass (1286→1288) |
| 4 | skill update (Hermes) | DONE | 2026-08-03 | 2026-08-03 | (Hermes session) | pre-push-gate skill, R110-77 |

**Overall**: 5/5 mas-engineer PHASEN done, 1/1 hermes PHASE done.
mas-engineer-side: PHASE 1 (R110-94+R110-100) + PHASE 2
(R110-106) + PHASE 3 (R110-118 sub_mas-self-audit + dev_self_audit
+ dev_spec_invariant + Check 18) + PHASE 3b (R110-120 STEP 0.6
self-audit in IM-pipeline) + PHASE 3c (R110-121 STALE-LITERAL
Pattern B fix) + PHASE 3d (R110-124 scanner Pattern A+B
detection in dev_im_finder_scan.py).
hermes-side: PHASE 4 (R110-77 pre-push-gate skill).
**Status: ARCHIVED-READY** — R110-78 spec-drift lesson komplett
geschlossen. Total: 8 R-Nummern (R110-77, R110-94, R110-100,
R110-106, R110-118, R110-120, R110-121, R110-124), 7 commits auf
origin/cleanup (R110-118 + R110-119 in PHASE 3a, R110-120 in
3b, R110-121 in 3c; plus R110-117 dispatch mechanism + R110-116
commit-hygiene + R110-115 RECURSION-GUARD v3). pytest 1284→1286
(+2 net tests: test_step_0_6 in R110-120 + test_pattern_b in
R110-121; R110-118 added +3 incl. Check 18 — 1281→1286 = +5
total, verified 2026-08-04 via pytest --collect-only). 4 BLOCKER
+ 6 STALE-LITERAL + 5 simple-stale HARDCODE = 15 findings gefixt.

### R110-106-sd-detector-pilot (neu 2026-08-04)
- **Datei**: `R110-106-designer-im-top-n-respect.md` (130 lines, 2026-08-04)
- **Ziel**: SD-detection logic (check_spec_drift) + IM_TOP_N=30 e2e-pilot
- **Created**: 3b80259 (R110-106, 2026-08-04)
- **Effekt**: 2 spec-drifts fixed (F-001 Q4 path, F-022 SD test-literal
  "14 critical checks" -> "17 critical checks"); 4 SD-detector fixture-
  tests; 130 lines follow-up spec fuer im-designer Z.164 hardcoded
  "TOP-5" (R110-107 directive, commit 9136778)

### R110-107-im-designer-top-n-fix (neu 2026-08-04)
- **Datei**: `R110-107-im-designer-top-n-fix.md` (167 lines, 2026-08-04)
- **Ziel**: im-designer Z.164 hardcoded "TOP-5" -> "TOP-N" fix
- **Created**: 9136778 (R110-107, 2026-08-04)
- **Status**: SPEC-DRAFT (no code change yet)
- **Ergebnis R110-107 run**: 0 patches drafted — mas-engineer kann
  recipe-self-bugs nicht selbst fixen (finder sucht code-defects,
  improver lehnt per R06 direct file-writes ab). Architectural fix
  in R110-109 (sub_mas-self-audit).

### R110-108-sd-detector-integration (neu 2026-08-04)
- **Datei**: `R110-108-sd-detector-integration.md` (202 lines, 2026-08-04)
- **Ziel**: SD-detector in sub_mas-im-finder integrieren (R110-78 PHASE 2 spec-compliance)
- **Created**: 391be5b (R110-108, 2026-08-04)
- **Status**: SPEC-DRAFT (DONE confirmed in R110-108 run 2026-08-04 10:53Z:
  recipe/instructions/sub_mas-im-finder.md Z.36 ruft dev_im_finder_scan.py
  auf, 7 SD-* findings in run emittiert). DIREKTIVE 1 (integration) ist
  bereits durch R110-106 commit 3b80259 erfuellt.

### R110-109-self-audit-spec-invariant (neu 2026-08-04)
- **Datei**: `R110-109-self-audit-spec-invariant.md` (238 lines, 2026-08-04)
- **Ziel**: sub_mas-self-audit agent + dev_spec_invariant.py (R110-78 PHASE 3)
- **Created**: bbc76ca (R110-109, 2026-08-04)
- **Status**: DONE (implemented by R110-118 directive-apply, 2026-08-04)
- **Ausfuehrung**: R110-118 applied via sub_mas-apply-directive (RECURSION_OVERRIDE=2):
  sub_mas-self-audit.yaml + recipe/instructions/sub_mas-self-audit.md +
  tools/dev_self_audit.py (Patterns A/B/C) + tools/dev_spec_invariant.py
  (DIREKTIVE 2) + pre-push-validator Check 18 (DIREKTIVE 3, v2.4.0).
  pytest 1284/1284 PASS, scanner 21 findings (no regression).
  R11 GOOSE-EXPERT trigger (type A NEW recipe) fulfilled.

### R110-120-im-finder-step-0-6 (neu 2026-08-04)
- **Datei**: `R110-120-im-finder-step-0-6.md` (2026-08-04)
- **Ziel**: sub_mas-self-audit in improvement-pipeline auto-invoken —
  im-finder STEP 0.6 (R110-78 PHASE 3b closure)
- **Applied**: 2026-08-04 via sub_mas-apply-directive (RECURSION_OVERRIDE=2,
  R110-117 per-directive dispatch, HEAD 0d3317f)
- **Ausfuehrung**: STEP 0.6 "SELF-AUDIT SPEC-DRIFT CHECK" (~78 lines)
  zwischen STEP 0.5b und STEP 0.7 in sub_mas-im-finder.md (R01 BYPASS,
  MM9-EXT mapping, BLOCKER fail-fast) + sub_mas-self-audit in im-finder
  sub_recipes (3 entries: goose-expert + im-designer + self-audit) +
  test_step_0_6_self_audit_attaches_mm9_ext.
- **Status**: R110-78 PHASE 3b = DONE. pytest 1285/1285 PASS,
  registry 9/9 PASS, dev_spec_invariant 0 BLOCKER,
  dev_self_audit 27 WARN (unchanged, 0 NEW findings).

### R110-121-stale-literal-fix (neu 2026-08-04)
- **Datei**: `R110-121-stale-literal-fix.md` (2026-08-04)
- **Ziel**: STALE-LITERAL Pattern B findings fixen — sales-Beispiele →
  dev-team in 3 files + Pattern B Bug-Fix (R110-78 PHASE 3c closure)
- **Applied**: 2026-08-04 via sub_mas-apply-directive (RECURSION_OVERRIDE=2,
  R110-117 per-directive dispatch, HEAD 4050394)
- **Ausfuehrung**: DIREKTIVE 1 sales→dev-team in sub_mas-team-packager.md
  (Package-Tree L16-25 + Invocation-Example L368-397 inkl. agent_count
  6→5) + HOWTO-TEAM-STANDALONE.md (6 refs) + HOWTO-PACKAGE-TEAM.md
  (8 refs); DIREKTIVE 2 Pattern B fix in dev_self_audit.py (MULTILINE
  path-like index + `./`-prefix + YAML bare-name index mit self-definition
  exclusion); DIREKTIVE 3 +1 Test (test_pattern_b_stale_literal_detected,
  Finding.code statt draft-f.type, R110-120 import-pattern).
- **Status**: R110-78 PHASE 3c = DONE. pytest 1286/1286 PASS,
  registry 9/9 PASS, dev_spec_invariant 0 BLOCKER, dev_self_audit
  20 HARDCODE + 0 STALE-LITERAL, grep 'sub_mas-sales' recipe/+docs/ = 0.

### R110-126-mq-consumer-test-pattern (neu 2026-08-17, APPLIED)
- **Datei**: `R110-126-mq-consumer-test-pattern.md` (227 lines, 2026-08-17)
- **Ziel**: 5+5 hard rules aus R110-168+R110-169 lessons in
  den dev-tester/dev-builder sub-agent instructions verankern
  (MQ-consumer test pattern + cross-topic auto-escalation
  pattern), sodass zukuenftige MQ-consumer-arbeit die rules
  automatisch anwendet ohne hermes-side prompting.
- **Applied**: 2026-08-17 via sub_mas-apply-directive
  (RECURSION_OVERRIDE=2, operator-initiated, MAS_CONFIRM=yes
  + MAS_APPROVE=y, task="per directive R110-126")
- **Refs**: R110-168 (phoenix.recovery.completed consumer,
  221a520), R110-169 (phoenix->monitor auto-escalation,
  838ce0d), R110-165 (MQ-1 publishers, 266ceb7), R110-166
  (MQ-2 consumers, 2e0963b), R110-167 (INVARIANT fix,
  5372734), R110-118 (sub_mas-self-audit, 27d8cb7),
  R110-120 (STEP 0.6 in im-finder, 4050394)

| PHASE | DIREKTIVE | Status | Started | Completed | Commit | Effekt |
|---|---|---|---|---|---|---|
| 1 | MQ-consumer test pattern (5 rules) → sub_mas-dev-tester instructions | DONE | 2026-08-17 | 2026-08-17 | (uncommitted, apply-directive run) | `## MQ-CONSUMER TEST PATTERN` in `recipe/sub/sub_mas-dev-tester.yaml` `instructions:` block (envelope vs processor-output, depth()/_read_topic API, MAS_MQ_ROOT isolation, unique request_id, subprocess.run) |
| 2 | Cross-topic auto-escalation pattern (5 rules) → sub_mas-dev-builder instructions | DONE | 2026-08-17 | 2026-08-17 | (uncommitted, apply-directive run) | `## CROSS-TOPIC AUTO-ESCALATION` in `recipe/sub/sub_mas-dev-builder.yaml` `instructions:` block (payload-shape match, unique esc-id, try/except enqueue, rewrite log mit msg-id, dispatch branch mit note) |
| 3 | STATUS.md update mit R110-126 eintrag | DONE | 2026-08-17 | 2026-08-17 | (uncommitted, apply-directive run) | dieser eintrag selbst — DRAFT → APPLIED flipped als self-confirmation |
| 4 | Regression verification: 11 tests + 10 key phrases grep | DONE | 2026-08-17 | 2026-08-17 | (uncommitted, apply-directive run) | `pytest tests/test_dev_phase3_phoenix_log.py tests/test_dev_phase4_escalation.py -v` = 11/11 passed; full suite 1528 passed / 16 skipped; 10/10 key phrases grep-treffer (6 tester + 4 builder) |

**Overall**: 4/4 PHASEN done. Status: **APPLIED** (2026-08-17,
sub_mas-apply-directive run; R11 goose-expert CONFORM HIGH —
beide YAMLs bestehen offizielles `goose recipe validate` exit 0,
idempotent, no-fork; Backups in `.backups/20260817_045607/`).

**Abweichungen (R110-116 ehrlich dokumentiert)**:
  1. **Path-drift**: DIREKTIVE 1+2 nennen
     `recipe/instructions/sub_mas-dev-tester.md` /
     `sub_mas-dev-builder.md` — diese Dateien existierten in
     diesem Repo nie (verifiziert via voller git-history).
     Tatsaechliche SOT fuer die Agent-Instructions ist der
     `instructions:` block-scalar in
     `recipe/sub/sub_mas-dev-tester.yaml` /
     `recipe/sub/sub_mas-dev-builder.yaml` (dev-director
     delegiert ueber die YAML-Rezepte). Directive-Intent
     ("recipe sub-agent instructions") wurde auf die
     tatsaechliche SOT angewendet.
  2. **Anker-drift**: Sektionen "PYTEST ISOLATION" (tester)
     und "PUBLISHER PATTERN" (builder) existieren in diesem
     Repo nicht → neue Sektionen nach `## RULES` (Ende des
     instructions-blocks) eingefuegt statt nach den
     genannten Ankern.
  3. **Scanner-delta**: dev_im_finder_scan.py
     --scope=recipe,+demo-teams 77 → 79 findings (+2 NN1
     multi_role_agent medium: F-006 tester, F-016 builder).
     Ursache: beide Dateien kreuzten die 60-Zeilen
     micro-agent-guard (R98: <60 Zeilen = skip) durch die
     directive-pflicht-content-Erweiterung; NN1 zaehlt
     role-verbs aus instructions-text (u.a. "dispatch",
     "read", "write", "design" aus den verbatim-key-phrases
     der directive). Nicht-blockierend: pre-push Check 1
     gatet nur high-severity (P1); immune_severity=OK;
     NN1 ist advisory (SRP-suggestion), kein Regressions-
     Blocker. Verbatim-content bleibt (directive-Acceptance
     = 11 tests + 10 phrases, vollstaendig gruen).

**Hermes-side mirrors** (fuer wenn hermes selbst MQ-consumer
test code schreibt, z.B. bei hotfixes): skills
`mas-engineer-mq-ecosystem-test-pattern` (5 rules, mit
LOAD-TRIGGER condition) und
`mas-engineer-mq-cross-topic-escalation` (5 rules). Die
skills und die directive haben den gleichen inhalt, aber
leben in verschiedenen layern (hermes skills vs mas
directives). Bei R110-126 application kann mas optional die
skills verifizieren oder updaten (PHASE nicht spezifiziert
in DIREKTIVE 1+2+3 — bewusst out-of-scope, um
layer-bleed zu vermeiden).

### R110-171-pre-push-check17-flake-remediation (new 2026-08-17, APPLIED)
- **File**: (no separate .md file — direct hotfix-tier code-fix,
  see memory rule "EXCEPTION: pre-push BLOCKER + 24h cooldown
  -> hotfix"; push was already 42cda98 done but the 2
  xdist-flakes would surface again in future runs)
- **Goal**: pre-push-validator Check 17 xdist (-n 4) flakes
  deterministically green
- **Refs**: R110-126 (previous commit, 42cda98), R110-129
  (conftest chdir R-FIX), R110-71 (sub-agent count 96->110 rename,
  9c73100), R110-78 (spec-drift lesson)
- **Hotfix-trigger**: validator re-run at 08:00 reported
  2 fails under `-n 4` (test_dev_phase1_publishers
  test_im_finder_publish_enqueues_message + test_dev_parallel_backpressure
  test_backpressure_higher_than_workers_no_extra_throttle). Investigation
  found: 2 different race conditions, NOT spec-drift (the
  '96 sub-agents' and 'recipe_count_matches' names from the first
  validator output were hallucinations — these test names
  exist only in the validator-recipe docs as EXAMPLES
  for R110-78's spec-drift pattern, not as real tests).

| PHASE | DIRECTIVE | Status | Started | Completed | Commit | Effect |
|---|---|---|---|---|---|---|
| 1 | xdist-safe MQ-isolation in test_dev_phase1_publishers.py | DONE | 2026-08-17 | 2026-08-17 | (uncommitted) | autouse `mq_root_isolation` fixture sets `MAS_MQ_ROOT` to per-test `tmp_path/mq` + rebinds `IM_NDJSON`/`MON_NDJSON` module-globals — xdist workers can no longer overwrite each other's ndjson-lines |
| 2 | GIL-race fix in test_backpressure_higher_than_workers_no_extra_throttle | DONE | 2026-08-17 | 2026-08-17 | (uncommitted) | `time.sleep(0.02)` -> `threading.Barrier(4)` so all 4 workers increment SIMULTANEOUSLY before the first one decrements; 8 tasks -> 4 tasks (one round, one barrier) |
| 3 | Regression verification: 3x flake-suite + 1x full suite | DONE | 2026-08-17 | 2026-08-17 | (uncommitted) | `pytest -n 4 tests/test_dev_phase1_publishers.py tests/test_dev_parallel_backpressure.py` = 14/14 passed (3 consecutive runs); `pytest -n 4 tests/` = 1528 passed / 16 skipped / 0 failed in 224.9s |
| 4 | STATUS.md update with R110-171 entry | DONE | 2026-08-17 | 2026-08-17 | (uncommitted) | this entry itself |

**Overall**: 4/4 PHASEN done. Status: **APPLIED** (2026-08-17,
hermes-initiated hotfix, +54/-3 lines, 2 files:
tests/test_dev_phase1_publishers.py + tests/test_dev_parallel_backpressure.py).

**Lesson (R110-78-spec-drift, hallucinations-edition)**: the
pre-push-validator reads its own recipe-instructions-file
(`recipe/instructions/sub_mas-pre-push-validator.md` L843-844)
as 'last 10 lines of pytest output' input and hallucinates
the test names mentioned there as EXAMPLES (`test_bootstrap_distributes_96_subagents`,
`test_recipe_count_matches_subagents`) back as 'failures'.
These test names do not exist in the suite (R110-71
renamed them to 110 on 2026-08-02). Next step
(R110-172, mas-side): validator-instruction explicitly formulated
so that 'last 10 lines' output must be a REAL pytest
run, not the recipe's own documentation.
Hermes-side: skill `mas-engineer-pre-push-check17-flake-handling`
documents the 'git log origin/mas-mq first check' pattern
so future runs do not fall into the same trap.

### R110-172-body-claim-evidence-files-standard (new 2026-08-17, APPLIED)
- **File**: `R110-172-evidence-files-standard.md` (155 lines, 2026-08-17)
- **Goal**: every commit that makes quantitative claims (pytest counts,
  grep results, secret-scan) in its body MUST co-commit the evidence as
  reproducible files in `tests/results/<R-NR>-<topic>/`.
  Standard-directive defined in DIRECTIVE 1+2+3+4.
- **Trigger**: R110-126 body's "10/10 key phrases" was strict-grep
  imprecise (only 5/10 exact), and R110-171 body's pytest-numbers
  lived only in the terminal scrollback. Both are body-claim-drift
  that the mas-engineer-verification-theater-guard skill classifies
  as avoidable. R110-172 fixes that retroactively +
  preventively.
- **R110-172 itself**: docs-only commit, NO code-changes.
  Contains 13 files in tests/results/ (1 README + 1 EVENTS.md +
  11 evidence files for R110-126 + R110-171). `git show` diff:
  only additions (no modify, no delete), 100% transparent.

| PHASE | DIRECTIVE | Status | Started | Completed | Commit | Effect |
|---|---|---|---|---|---|---|
| 1 | tests/results/ LAYOUT-STANDARD (DIRECTIVE 1) | DONE | 2026-08-17 | 2026-08-17 | (R110-172) | standard defined: tests/results/R<NR>-<short-topic>/NN-<claim>.txt with header+command+output+conclusion |
| 2 | tests/results/ not gitignored (DIRECTIVE 2) | DONE | 2026-08-17 | 2026-08-17 | (R110-172) | implementation decision (per .gitignore-check: tests/results/ is NOT in .gitignore); .mase/runtime/ stays gitignored (per design, living state) |
| 3 | BODY EVIDENCE-block (DIRECTIVE 3) | DONE | 2026-08-17 | 2026-08-17 | (R110-172) | R110-172 body itself uses the new EVIDENCE-block standard; future commits can use it |
| 4 | Backward-compat for R110-126 + R110-171 (DIRECTIVE 4) | DONE | 2026-08-17 | 2026-08-17 | (R110-172) | evidence files RETROACTIVELY placed in tests/results/r110-126-mq-pattern/ and tests/results/r110-171-flake-fix/; bodies are NOT amended (git history stays linear + honest: "was at that time as the body says, evidence was retroactively supplied") |

**Evidence files (13 total, all reproducible):**
- `tests/results/README.md` (standard-documentation)
- `tests/results/EVENTS.md` (commit-body-claim -> evidence-file mapping)
- `tests/results/r110-171-flake-fix/01-phantom-test-names-grep.txt` (proof: phantom tests do not exist)
- `tests/results/r110-171-flake-fix/02-pytest-collect-only.txt` (1544 collected)
- `tests/results/r110-171-flake-fix/03-flake-suite-run-{1,2,3}.txt` (3x 14/14)
- `tests/results/r110-171-flake-fix/04-full-suite-pytest-n4.txt` (1528/16/0)
- `tests/results/r110-171-flake-fix/05-secret-scan.txt` (manual grep)
- `tests/results/r110-171-flake-fix/06-official-secret-scan.txt` (official scanner, 4x clean)
- `tests/results/r110-171-flake-fix/07-pytest-collect-only-3x.txt` (3x 1544 deterministic)
- `tests/results/r110-126-mq-pattern/01-phase3-phase4-regression-11-11.txt` (11/11)
- `tests/results/r110-126-mq-pattern/02-key-phrases-grep-10-10.txt` (10/10 case-insensitive, 5/10 case-sensitive, body-claim-drift documented)

**Verification:**
- `git ls-files tests/results/` lists all 13 files (not gitignored)
- `python3 tools/dev_security_scan.py SCAN secrets tests/results/` = issues_found: false
- `pytest tests/ -q -n 4` unchanged 1528/16/0 (no code-change)
- `git show R110-172 --stat` shows only additions in tests/results/ (no modify/delete)

**Lessons captured:**
1. R110-78 (spec-drift) has a second variant: **body-claim-drift**,
   where the body makes a larger claim than the implementation
   exactly proves (R110-126 "10/10 key phrases" with only 5/10 strict-match).
   Solution: use theme-formulation instead of grep-formulation when the
   section-headers are the actual acceptance criterion.
2. **Reproducible evidence** > in-terminal-output. Whoever gets the
   clone should be able to verify without a 4-min pytest-run.
3. **Retroactive evidence-supply** is OK when documented
   transparently (this STATUS.md entry), instead of silently
   amending the bodies.

**Overall**: 4/4 PHASEN done. Status: **APPLIED** (2026-08-17,
hermes-initiated docs-only commit, +13 files, 0 code-changes,
0 recipe-changes).

## PHASE-Status-Legende

- `OPEN` -- spec existiert, implementation ausstehend
- `IN-PROGRESS` -- mas-engineer-design-phase laeuft
- `DONE` -- implementation committet + validiert
- `BLOCKED` -- findet statt, aber durch external issue gestoppt
  (z.B. findet eine abhaengigkeit die nicht erfuellt ist)
- `CANCELLED` -- spec wurde verworfen, dokumentiert in commit
  message warum
- `SPEC-DRAFT` -- directive committet, implementation wartet auf
  naechsten im-pipeline run

## Wann wird aktualisiert

- mas-engineer IM-pipeline: am ende jedes runs (S7 SUMMARIZE
  stage) -- wenn ein PHASE commit committet+gepusht+validiert
  ist, wird `Completed` + `Commit` ausgefuellt
- User: manuell, wenn ein PHASE durch fix-commit aus
  anderem R-Run abgeschlossen wurde (z.B. wenn R110-90
  nebenbei PHASE 1 von R110-78 erfuellt)
- IM-pipeline FIND phase: liest diese datei BEVOR sie
  findings emittiert. Wenn alle PHASEN DONE, wird die
  direktive als `STATUS: ARCHIVED` markiert und nicht mehr
  als offener finding emittiert

## Format-Konvention

Pro direktive ein eintrag mit:
- Datei + lines + creation date
- 1-zeilen ziel
- Created commit + alle folgenden refactorings
- Tabelle mit 1 row pro PHASE: PHASE nr, DIREKTIVE name,
  Status, Started, Completed, Commit (hash), Effekt
- "Overall" summary (X/Y PHASEN done)

## Was NICHT hierher

- Implementation details (die gehoeren in commits/diffs)
- Performance metrics (die gehoeren in mas-engineer
  monitoring + dashboard)
- User-discussion (die gehoeren in logs/e2e-results/<session>/
  oder in user-side notes, nicht hier)
- "Was hat NICHT funktioniert" retros (die gehoeren in
  commit messages der jeweiligen fix-commits)

## R110-115 follow-up: R110-116 (commit-hygiene corrections)

- **R110-115** (b00dade): sub_mas-apply-directive + RECURSION-GUARD v3
  + 2 directive tools. pytest 1281/1281 PASS. 6 files +455/-1.
- **R110-116** (this commit): non-breaking follow-up mit ehrlicher
  body-korrektur. b00dade bleibt unveraendert. 3 bugs im detail
  dokumentiert (yaml-parse-error von `<path>` in single-quote,
  log_change() kwarg collision, description-prefix fehlte).
  "EFFECTIVENESS TEST" → "MANUAL WORKAROUND" re-classifiziert.
  File: `docs/architecture/R110-115-b00dade-body-corrections.md`.

## R110-117+118 — self-improvement loop closed

- **R110-117** (690f39e): RECURSION-GUARD v3 wired end-to-end.
  sub_mas-apply-directive in sub_recipes + TASK-DETECTION
  RECURSION_OVERRIDE=1 → +2. e2e dispatch verified.
- **R110-118** (this commit): R110-109 DIREKTIVE 1+2+3 implemented
  via R110-117 dispatch mechanism. 5 new files (sub_mas-self-audit
  agent + dev_self_audit.py + dev_spec_invariant.py + Check 18 test).
  PHASE 3 R110-78 spec-drift = DONE. Standalone spec-invariant
  finds 4 BLOCKER + 5 HARDCODE on first run (sub_mas-bootstrap.md
  "96 sub-agents" stale, pre-push-validator.md "18 checks" hardcoded).
  pytest 1281+3=1284 PASS.

## R110-78 lesson — spec-drift = ARCHIVED

R110-78 spec-drift lesson (created 04afe4a R110-79, 528 lines
spec, 2026-08-03) is now FULLY CLOSED with all 6 PHASEN done:

- **PHASE 1** (validator + pytest gate, R110-94 + R110-100):
  27d8cb7 (Check 16+ drift) + c005db6 (Check 17 pytest-count-
  mismatch). spec-drift in commits blockt pre-push.
- **PHASE 2** (SD-* finding type, R110-106): 3b80259.
  dev_im_finder_scan.py:check_spec_drift() findet 7 SD-*
  findings in R110-108 run. im-finder recipe Z.36 ruft
  standalone-script auf.
- **PHASE 3** (sub_mas-self-audit + dev_self_audit +
  dev_spec_invariant + Check 18, R110-118): f4277fc.
  Pattern A (HARDCODE stale literals) + Pattern B (STALE-
  LITERAL no-twin references) + Pattern C (count-assertion
  drift). 4 BLOCKER + 5 simple-stale HARDCODE on first run.
- **PHASE 3b** (self-audit in IM-pipeline, R110-120): 4050394.
  STEP 0.6 in sub_mas-im-finder.md (between 0.5 goose-consult
  and 0.7 write findings), MM9-EXT findings, BLOCKER fail-fast
  vor findings-write. +1 test.
- **PHASE 3c** (STALE-LITERAL Pattern B fix, R110-121): 83e4ce7.
  sales→dev-team examples in 3 files, dev_self_audit.py Pattern
  B bug-fix (YAML bare-name detection), 0 STALE-LITERAL
  findings. +1 test.
- **PHASE 4** (hermes-side skill, R110-77): pre-push-gate skill
  with R110-78 lesson documented.

**Total impact (R110-78 lesson):**
- 7 R-Nummern, 7 commits auf origin/cleanup (R110-118+119 in
  PHASE 3a, R110-120 in 3b, R110-121 in 3c; plus R110-117
  dispatch mechanism + R110-116 commit-hygiene + R110-115
  RECURSION-GUARD v3)
- pytest 1281→1286 (+5 tests across R110-118+120+121: +3 in
  R110-118 incl. Check 18, +1 test_step_0_6 in R110-120,
  +1 test_pattern_b in R110-121; verified 2026-08-04 via
  `pytest --collect-only`: 1286 tests collected)
- 15 findings gefixt: 4 BLOCKER + 6 STALE-LITERAL + 5 simple-
  stale HARDCODE
- 0 STALE-LITERAL findings, 0 BLOCKER in dev_spec_invariant
  (clean), 20 HARDCODE-WARN (canonical/context-dependent, both
  documented per R110-119 context-comment + R110-121 Pattern B
  improvement)

**R110-78 spec-drift lesson = KOMPLETT GESCHLOSSEN + ARCHIVED.**
Future drift will be caught by:
- pre-push Check 16+ (5-cat-drift), Check 17 (pytest-count),
  Check 18 (count-assertion drift)
- im-finder STEP 0.6 (auto-invoke sub_mas-self-audit vor
  findings-write, MM9-EXT findings attached)
- dev_self_audit.py (standalone-invokable for ad-hoc checks)
- dev_im_finder_scan.py:check_spec_drift() (called from im-
  finder recipe Z.36 for SD-* finding type)

## R110-124 — scanner Pattern A+B (MM9-EXT scanner support)

- **Datei**: `R110-124-scanner-pattern-ab.md` (357 lines, 2026-08-04)
- **Ziel**: dev_im_finder_scan.py erkennt HARDCODE-STALE-* (Pattern A)
  + STALE-LITERAL-* (Pattern B) — scanner als single source of truth
  fuer recipe-drift, nicht nur sub_mas-self-audit-agent
- **Applied**: 2026-08-04 via sub_mas-apply-directive (RECURSION_OVERRIDE=2,
  R110-117 per-directive dispatch)
- **Ausfuehrung**: DIREKTIVE 1+2 = check_hardcode_stale() + check_stale_literal()
  in tools/dev_im_finder_scan.py (lazy-import dev_self_audit, reuse
  PATTERN_A_RE/PATTERN_A_ACCEPT_CTX/_is_in_fence/_strip_inline_code/
  _scan_pattern_b/_build_repo_literal_index — kein Reimplementieren,
  R02 consumer/producer); DIREKTIVE 3 = 2 try/except call-sites im
  main flow (nach check_spec_drift_reverse); DIREKTIVE 4 = +2 tests.
- **Abweichungen (R110-116 ehrlich dokumentiert, commit body)**:
  1. STALE-LITERAL severity 'warn' → 'medium' (R28 SEVERITY_FILTER
     default medium,high,blocker wuerde 'warn' still droppen)
  2. STALE-LITERAL e2e-test auf synthetisches Fixture umgestellt
     (Repo hat post-R110-121 0 STALE-LITERAL — Acceptance ">=1" war
     stale, kopiert vom Pre-Fix-Stand "6 STALE-LITERAL")
  3. Helper-Name `_strip_inline_code_inline` (directive-Draft) →
     `_strip_inline_code` (tatsaechlicher Name in dev_self_audit)
- **Status**: DONE. pytest 1288/1288 PASS, registry 9/9 PASS,
  scanner --scope=recipe/instructions/ emittiert HARDCODE-STALE-*
  (>=1; Repo hat 18 Kandidaten) + 0 STALE-LITERAL (korrekt, da
  R110-121 alle gefixt hat; Wrapper verifiziert per synthetischem
  Fixture), dev_self_audit 20 WARN (unveraendert), dev_spec_invariant
  0 BLOCKER.
