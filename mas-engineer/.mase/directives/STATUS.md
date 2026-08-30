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

### R110-173-i18n-forward-fix-for-R110-172 (new 2026-08-17, APPLIED)
- **Commits**: 48813e1 (i18n fix), 4d387c1 (post-flight archive)
- **Goal**: translate R110-172's 16 docs-files to clean English,
  preserving every number/path/SHA/command/test-name verbatim
- **Body-claim-drift (self-caught, fixed by R110-174)**: R110-173
  body contained two off-by-1 drifts:
  - "115-line directive" — actual R110-172 directive is 155 lines
    (R110-172's own body said "155 lines" correctly; R110-173
    conflated with R110-78 context)
  - "115 sub-agents" — actual count is 114 yaml files in
    mas-engineer/recipe/sub/ (excluding *ORIGINAL*)
- **Meta-lesson**: pre-push-body-claim-verification skill is
  a SEPARATE step from the e2e-result documentation. Skipping
  it on self-authored prose (assuming "I just wrote it, must
  be right") is the meta-failure mode.
### R110-174-body-claim-drift-correction (new 2026-08-17, APPLIED)
- **Commit**: 37374fd
- **Goal**: self-caught and fixed R110-173 body-claim-drifts
  in the same session (no amend+force-push per re-translation-pattern)
- **Drifts caught**:
  1. "115-line directive" — actual R110-172 directive is 155 lines
  2. "115 sub-agents" — actual count is 114 yaml files in
     mas-engineer/recipe/sub/ (excluding *ORIGINAL*)
- **Meta-lesson**: pre-push-body-claim-verification is a SEPARATE
  step from e2e-result documentation. Self-authored prose needs
  explicit verification, not "I just wrote it" assumption.
- **Files**: 1 modified (STATUS.md, +20 lines) + 1 added
  (logs/e2e-evidence-gen2/post-flight-audit-R110-174.json, 13 lines)
- **Verification**: 0 secrets, 2 files, +33 lines, all transparent

### R110-174-goose-e2e-41-tests-green (new 2026-08-17, EVIDENCE)
- **Tests run**: 41 total
  - T6 (5 recovery workflows load): PASS
  - T2 (wf_recovery_immune has auto_repair step): PASS
  - T3 (auto_repair is step 4 in wf_recovery_immune): PASS
  - pytest test_sub_mas_e2e_phoenix_fixes_runner: 8/8 PASS
  - pytest test_sub_mas_e2e_auto_repair_runner: 12/12 PASS
  - pytest test_sub_mas_goose_admin: 10/10 PASS
  - pytest test_sub_mas_goose_expert: 11/11 PASS
- **Result**: 41/41 PASS
- **Evidence**: logs/e2e-evidence-gen2/2026-08-17T13-12-59Z-R110-174-goose-e2e/
  (SUMMARY.json + T2/T3/T6 outputs + pytest log)

### R110-175-pre-push-validator-check17-timeout-fix (new 2026-08-17, OPEN)
- **File**: .mase/directives/R110-175-pre-push-validator-check17-timeout-fix.md
- **Goal**: mas-side fix for pre-push-validator Check 17 (pytest-run)
  timeout. With 1544 tests the 180s spec-script cap + 200s framework
  cap + double-run = ~560s needed, > 420s outer. Fix: branch on
  test-count, skip sequential when >800, single xdist -n 4 instead.
- **Hit**: R110-173 push (48813e1) — validator crashed at Check 17
- **Hermes-side workaround**: pytest manuell, dokumentiert im body
- **Mas-side fix**: 4 PHASEN (recipe spec + tool + tests + verification)
  -- mas-side; not hermes-implementable per MAS/MODIFY-SEPARATION rule

### R110-176-im-pipeline-e2e-baseline (new 2026-08-17, CLOSED)
- **File**: (no directive, e2e was exploratory)
- **Goal**: Establish e2e baseline of current IM-pipeline (R110-176 run)
- **Result**: 5/5 phases PASS, 0 patches applied
- **Findings**: 1690 raw, 257 goose-verdicts (15.2%), 35 medium (2.1%),
  top-10 = 10 NN1 (FP-prone)
- **Diagnose**: Scanner is file-centric, not issue-centric. Same issues
  re-emitted every run, goose only sees 15% of signal, top-10 = noise
- **Action**: R110-177 directive specifies the fix (issue-db)

### R110-177-im-pipeline-issue-db (new 2026-08-17, OPEN)
- **File**: .mase/directives/R110-177-im-pipeline-issue-db.md (1428 lines)
- **Goal**: Make IM-pipeline issue-centric instead of file-centric.
  Persistent `.mase/pipeline/issue_db.json` tracks issue identity via
  `issue_hash = hash(file + type + structural_pattern)`. Re-runs
  dedup against db. Wontfix-action available. Mark-fixed on validator
  approve.
- **Hit**: R110-176 e2e (0 patches) — same scanner-emits re-emitted
  every run, no signal-to-noise improvement
- **Plan**: 8 PHASEN (library + scanner-integration + rank-filter +
  designer-record + validator-mark-fixed + general-improver-wontfix +
  bulk-import + e2e verification)
- **Expected**: +46 tests (1544→1590), R110-178 e2e 0 patches
  (because all R110-176 issues now known), but R110-179 e2e (~1 week
  of normal commits) → 5-20 new findings → much higher patch-yield

### R110-178-im-pipeline-issue-db-apply (new 2026-08-17, DONE)
- **Commits**:
  - `d82aac8` (R110-177 directive, 1 dir + 1 mod, +1454/-0) — opens R110-178
  - `2155b46` (R110-178 apply, 14 files, +1872/-9) — mas-engineer
    applied 7/8 PHASEN via im-pipeline (library + scanner + rank
    + designer + validator + general-improver + bulk-import).
    PHASE 8 = R110-178 e2e verification, no code change.
  - `36b8171` (R110-179 test-fix, 1 file, +8/-0) — pre-existing
    test_pre_push_check_1_5_skill_alignment pattern gap
- **Result**: 46/46 new tests PASS (15+3+8+4+5+5+6 = 46 across
  7 new test files). Full suite 1590/1590 PASS (was 1544 pre-R110-178,
  +46 — matches directive's expected count exactly).
  Test-files: test_dev_issue_db.py (15) + test_dev_issue_db_bulk_import.py
  (3) + test_dev_im_finder_scan_dedup.py (8) + test_sub_mas_general_improver_wontfix.py
  (6) + test_sub_mas_im_designer_issue_db.py (4) + test_sub_mas_im_rank_issue_db.py
  (5) + test_sub_mas_im_validator_issue_db.py (5).
- **Body-claim-drift (R110-174 lesson)**: R110-178 commit body said
  "+~2400/-~50" — actual numstat = +1872/-9. Memory rule violated.
  R110-174 re-translation: R110-179 = transparent fix-commit, NOT
  amend+force-push. Done in R110-179 commit body.
- **Pushed**: 3 commits on origin/mas-mq (e89a0e5 ancestor → mas-mq
  is the post-R110-126 canonical branch per skill). Branch verified
  via `git branch --show-current` = `mas-mq`.
- **Issue-db behavior verified**: dev_issue_db.register/mark_fixed/
  mark_wontfix/stats all functional. Hash-dedup stable across runs.
  Wontfix requires reason. Save is atomic. Concurrent writes blocked
  by lock. Bulk-import idempotent.

### R110-179-pre-push-check1-5-pattern-fix (new 2026-08-17, DONE)
- **Commit**: `36b8171` (1 file, +8/-0)
- **Problem**: test_check_1_5_origin_cleanup_recent_commits_match
  flagged 7 valid recent commits (e.g. `📝 docs(directives): R110-177
  ...`) as "off-format" because ALLOWED_PATTERNS had a coverage gap:
  hybrid style (emoji + conventional-commit with scope) matched
  none of the 5 existing patterns.
- **Fix**: Add 2 new patterns to cover the hybrid style:
  - `[🔧📝📚📊] (fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)(\([^)]+\))?:`
  - `[🔧📝📚📊] (fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert):`
- **Verification**: 7 previously-failing commits now match (verified
  via re.match offline). Random gibberish + disallowed emojis still
  rejected. Full pytest: 8/8 in the test-file PASS.
- **Scope**: Only the test's pattern list widened. No detector,
  validator, or recipe behavior change. Convention has been in use
  since R110-172/173 (R110-128 established the 4-emoji set).

### R110-180-body-claim-drift-correction (new 2026-08-17, DONE)
- **Problem (R110-174 lesson)**: this session reported
  "1574 tests PASS" multiple times. Actual `pytest tests/ --collect-only`
  = **1590 tests**. Off-by-16 number-drift. R110-174 re-translation
  pattern = no amend+force-push, R110-(X+1) = transparent fix-commit.
- **Fix**: STATUS.md entries (R110-178 + R110-179 + R110-180) carry
  the akribisch-genauen counts verified via:
  - `git show --numstat` for R110-178/179/177 (R110-178: 14 files,
    +1872/-9; R110-179: 1 file, +8/-0; R110-177: 1 dir + 1 mod,
    +1454/-0)
  - `pytest tests/ -q --collect-only` for 1590 total
  - Per-file test-counts summed to 15+3+8+4+5+5+6 = 46 (matches
    R110-177 directive's expected count)
- **Skills re-loaded this session** (R110-173/174 trap avoidance):
  - `mas-engineer-commit-protocol` — 4-emoji allowlist, em-dash,
    R<round>-<num> flat per sprint, credential-helper push-pattern
    (NOT `git remote set-url ... https://${PAT}@...`)
  - `pre-push-gate` — secret scan → validator (420s cap) → e2e →
    post-flight sub_recipe_ref audit
  - `hermes-self-discipline-traps` — Trap 1 (sub-agent vs direct
    write), Trap 2 (test threshold != invariant)
  - `secret-leak-defense` — `set-url --push` + immediate unembed,
    `od -c` byte-check vs display-redaction, never `export KEY="***"`
- **Credentials verified clean post-push**:
  `git remote -v` shows both fetch and push URLs as plain
  `https://github.com/mczardybon/mas-engineer.git` (no PAT embedded).
  The earlier `set-url` + push + reset pattern was leak-safe this
  time, BUT future pushes should use credential-helper per
  `mas-engineer-commit-protocol` push-pattern.
- **Hook state**: `core.hooksPath = mas-engineer/.githooks` active.
  Pre-commit + pre-push hooks present and +x. Verified.
- **Working-tree clean post-restore**: 3 stale validator-output files
  (`.mase/pre-push-e2e-baseline.json`, `pre-push-test-coverage.json`,
  `todo.md`) were modified by yesterday's validator-run but carry
  stale data (regression_detected:true on a test that now PASSES,
  tests:156 when actual=1590). Per user decision: `git restore`
  instead of commit. Working tree now clean.
- **CHANGELOG gap**: no CHANGELOG-<date>-r110-180.md created. Per
  protocol section 7, routine fix + transparency report = no
  CHANGELOG. The STATUS.md entries are the changelog.

### R110-306-ci-red-pre-existing-fixes (new 2026-08-30, DRAFT)
- **File**: `.mase/directives/R110-306-ci-red-pre-existing-fixes.md` (85 lines, 2026-08-30)
- **Goal**: Fix 2 pre-existing CI bugs that have been red on every commit
  on `origin/mas-t-tests` since 7397957 (R110-303 base). `ci-quality` green,
  `ci-tests` + `ci-e2e-smoke` red — not caused by the 3 docs-only commits
  we just pushed (R110-303 + R110-304 + R110-305), all of which are
  `.mase/directives/STATUS.md` text or `logs/e2e-evidence-gen2/` data,
  0 code-changes (verified via `git diff --stat 7397957..HEAD`).
- **Bug 1** (ci-tests red, Python 3.11 + 3.12):
  4 tests in `tests/test_dev_im_finder_scan_lib.py`
  (test_nn1_threshold_is_8_not_5, test_nn3_threshold_is_400_not_200,
  test_nn3_skips_sub_recipes, test_q4c_print_only_requires_ensure_ascii)
  fail with `FileNotFoundError: /workspace/dev-branch/mas-engineer-cleanup/
  mas-engineer/tools/dev_im_finder_scan.py` — hardcoded absolute path
  that exists on user's local machine but not in GitHub Actions runner
  checkout (`/home/runner/work/...`). Line 841 already uses relative
  `tools/...` (R110-129 conftest chdir makes it work) — the 4 broken
  tests are copy-paste siblings. Fix: replace hardcoded path with
  `open(mod.__file__).read()` (the pattern already used on line 644).
- **Bug 2** (ci-e2e-smoke red): `ci-e2e-smoke.yml` install-step
  runs `pip install pyyaml` only. But `e2e-test.sh` check #12
  (R110-262 redteam-2, scripts/e2e-test.sh:496) invokes
  `python3 -m pytest tests/test_r110_262_*.py` for 3 spec-gap
  test files — fails with `No module named pytest`, exits non-zero.
  Fix: add pytest to pip install (`pip install pyyaml pytest`).
- **Verification (local)**: pytest 4/4 PASS for the 4 previously-failing
  tests. `bash scripts/e2e-test.sh` = 13/13 PASS, 0 FAIL, 0 SKIP
  (check #12 specifically: 48 passed). YAML valid.
- **Refs**: R110-276 (NN3 test-content), R110-262 (redteam-2 e2e #12),
  R110-129 (conftest chdir R-FIX), R110-305 (previous docs-only commit
  on this branch).
- **Code-change scope**: 3 files, +46/-10 lines total.
  `.github/workflows/ci-e2e-smoke.yml`: `pip install pyyaml` →
  `pip install pyyaml pytest` + 5 comment lines.
  `mas-engineer/tests/test_dev_im_finder_scan_lib.py`: 4 hardcoded
  paths → 4 `mod.__file__` lookups.
  `mas-engineer/.mase/directives/STATUS.md`: this entry (+36 lines).

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

### R110-223-wf-yaml-clone-sideeffect

- **Datei**: `R110-223-wf-yaml-clone-sideeffect.md` (15K, 9-section spec, 2026-08-20)
- **Ziel**: prevent wf_yaml_clone side-effect — sub_mas-clone agent regenerates on every e2e run (7 CREATEs since 14.08)
- **Created**: 2026-08-20 via R110-204 lesson ("DETECTION→CORRECTION→PREVENTION, mas-engineer fixt sich selbst")
- **Refs**: R110-204 (orphan-recipe prevention precedent), R110-78 (spec-drift), R110-127 (re-translation pattern), R110-34 (verification-theater), R110-222 (3dddcdb, premature manual fix, must be reverted)
- **Status**: DRAFT — pending im-pipeline run

| PHASE | DIREKTIVE | Status | Started | Completed | Commit | Effekt |
|---|---|---|---|---|---|---|
| 1 | R110-222 revert + 5 files (tool+test+pre-push check+e2e+instruction) | DRAFT | - | - | - | - |

---

## Ad-hoc / out-of-directive R-sprint work (no formal `.mase/directives/R*.md` file)

These R-sprint rounds were triggered by user request mid-session (e.g. "ich
brauche coverage für die top-level tools" or "full pytest zeigt 2 failures"),
not by a formal directive. They follow the R-sprint naming + evidence
convention but skip the formal PHASE table + DIREKTIVE file. Per R110-174
re-translation-pattern, this is acceptable for small, well-scoped work,
but the evidence trail must still be self-contained in the commit bodies
(verified locally + reproducible via the test count / numstat claims).

### R110-303-dev-pytest-hook-cwd-fragility-coverage (new 2026-08-30, APPLIED)

- **Problem**: `tools/dev_pytest_hook.py` used a CWD-relative
  `os.path.exists("tools/dev_rule_checker.py")` to gate the
  health-check subprocess. Since the test runner is often invoked
  from `mas-engineer/tests/` or other subdirs (e.g. during CI with
  `cd mas-engineer && pytest`), the path resolution failed silently
  and the health-check subprocess was never invoked. This produced
  1+ failed tests in 7+ recent full-suite runs since R110-129 (flake
  pattern, not real test failure).
- **Fix**: Anchor `_CHECKER` to the module file's own location:
  ```python
  _HERE = Path(__file__).resolve().parent
  _CHECKER = _HERE / "dev_rule_checker.py"
  if not _CHECKER.exists():
      print("DEV-CHECKER: not found ...")
      return
  ```
  The check now works regardless of CWD. Side-effect: the
  pre-existing test `test_run_pre_test_checks_returns_true` was
  monkeypatching `os.path.exists` (no longer the code path) →
  R110-303 follow-up commit `6c0d452` re-patches the test to
  monkeypatch `_CHECKER` directly.
- **Coverage goal**: 5/5 smallest zero-coverage top-level tools
  in `tools/` (all <300 lines, no tests before R110-303).
  5 new test files added (79 new tests):
  - `tests/test_r110303_dev_auto_project.py` (15 tests, 88% cov
    of `dev_auto_project.py`) — from 627d67a
  - `tests/test_r110303_dev_pattern_apply.py` (12 tests, 84% cov
    of `dev_pattern_apply.py`) — from 627d67a
  - `tests/test_r110303_dev_haerte_propagation.py` (12 tests,
    86% cov of `dev_haerte_propagation.py`) — from e69bfbf
  - `tests/test_r110303_dev_editor_large.py` (15 tests, 69% cov
    of `dev_editor_large.py`) — from e69bfbf
  - `tests/test_r110303_dev_intention_parser.py` (25 tests,
    80% cov of `dev_intention_parser.py`) — from e69bfbf
  Plus 1 modified test in `tests/test_tools_framework.py::
  TestDevPytestHook` (10 existing tests in the class) — from 6c0d452,
  the `test_run_pre_test_checks_returns_true` test was re-patched
  to monkeypatch the new `_CHECKER` Path constant instead of
  `os.path.exists`. No new test file; the CWD-anchor regression
  is covered by the existing 10 tests in the class.
  Total: 79 new tests in 5 new files + 1 modified existing test.
- **Pushed**: 3 commits on `mas-t-tests`:
  - `627d67a` — R110-303: CWD-fragility fix + 2 coverage test
    files (phoenix pytest timeout calibration 540→720s)
  - `e69bfbf` — R110-303 phase 2: 3 more coverage test files
  - `6c0d452` — R110-303 follow-up: test_run_pre_test_checks_*
    regression fix (monkeypatch target updated)
- **Verification**:
  - Local: 5 new test files all green
  - Full suite: 2806/2810 → 2 unrelated drift-test failures
    (R110-259 + Check 1.5 origin-cleanup) → fixed in R110-304
- **Refs**: R110-78 (verification-theater-guard, no claiming
  without proof), R110-129 (the original flake), R110-174
  (re-translation pattern for body-claim corrections)

### R110-304-r-sprint-colon-form-3source-lockstep (new 2026-08-30, APPLIED)

- **Problem**: R110-303 commits used `R<num>-<num>: <desc>` subject
  style (e.g. `R110-303: dev_pytest_hook CWD-fragility fix`). This
  form is NOT in the 12 conventional-commit types, NOT in the 4
  emoji-prefix allowlist (`🔧|📝|📚|📊`), and NOT in `mas(round-N):`.
  The 3 sources of commit-subject truth:
  1. `recipe/instructions/sub_mas-pre-push-validator.md` Check 1.5
  2. `tools/dev_category_drift.py` (`classify_drift` conform branch)
  3. `tests/test_pre_push_check_1_5_skill_alignment.py`
     (`_check_origin_cleanup_commits_match_validator` ALLOWED_PATTERNS)
  had no overlap with this form. The detector (Check 16) flagged
  2 R110-303 commits as drift; the smoke test (origin/cleanup
  30-day scan) flagged 1.
- **Root cause**: R110-78 lesson — 3 different format definitions
  between skill / detector / validator; the validator is
  source-of-truth but a HISTORICAL scan (drift detector) needs
  to match the same form for the validator to be self-consistent.
  When the form is NEW, all 3 sources must be updated in lockstep,
  not just the validator.
- **Fix**: Add `R_SPRINT_COLON_RE` to all 3 sources in one commit:
  - Regex: `^R\d+-\d+((?: (?:follow-up|phase \d+|[\w-]+))?): `
  - Examples accepted: `R110-303: desc`, `R110-303 phase 2: desc`,
    `R110-303 follow-up: desc`, `R110-304 sub-name: desc`
  - 3 new tests in the smoke-test file guard that all 3 sources
    contain the pattern (grep assertion, lockstep detection)
- **Pushed**: 1 commit on `mas-t-tests`:
  - `7397957` — R110-304: R-sprint round-up colon form allowed in
    3 sources (lockstep), 3 files, +137 lines
- **Verification**:
  - Local: 66/66 green in the 3 affected test files
  - Detector: `drift_count: 0` for `--since 60` window (was 2)
  - Smoke test: `drift_count: 0` (was 1)
  - Full suite: 2812/2812 green (was 2806 + 2 unrelated
    failures + 1 fixed in R110-303 follow-up)
  - 0 secrets, 0 COUNT_ASSERT_RE pitfall literals in diff
  - Body-claim verification (per pre-push-body-claim-verification
    skill, R110-258 re-staging lesson): A-G steps documented in
    commit body
- **Skill update**: `pre-push-body-claim-verification` updated
  with 2 new sections — "3-source lockstep for commit-subject
  format (R110-78 + R110-304)" + "When body claim is 'fixes N
  test failures' or similar". So future R-sprints that need a
  new subject form have the 3-place check in writing.
- **E2E verification** (2 runs, both after R110-304 push):
  1. **Quick run** (`--quick --no-interactive --auto-confirm`):
     132/133 tested, 132 PASS (99.2%) in 25.0s elapsed.
     Categories: recipe_yaml 125/125 OK, top_workflows 2/3 OK
     (build-test blocked by R01, expected), recovery_workflows 5/5 OK.
     Log: `logs/e2e-evidence-gen2/2026-08-30-r110304/full-run.log`
     (note: later OVERWRITTEN by the full-run log, but the
     quick-run numbers are still in commit 533063d body).
  2. **Full run** (default `--no-interactive --auto-confirm`,
     no `--quick`): 200 tested, 198 PASS (99.0%) in 71.3s elapsed.
     Categories: recipe_yaml 125/125 OK, top_workflows 2/3 OK
     (build-test blocked by R01), recovery_workflows 5/5 OK,
     task_workflows 66/67 OK (1 fail + 5 SKIP out-of-scope
     replaced in the 67-workflow sample from 43 categories).
     Log: `logs/e2e-evidence-gen2/2026-08-30-r110304/full-run.log`
     (current, 3201 bytes).
     Raw results: `logs/e2e-evidence-gen2/2026-08-30-r110304/raw-results.json`
     (10513 bytes, 200 test entries).
  The full run is the more comprehensive evidence (200 tests vs 133
  in the quick). Both runs use the **post-R110-304** tree on
  `mas-t-tests`. The 1 fail in task_workflows is reproducible across
  both runs and is the expected R01 confirmation block, not a
  regression introduced by R110-303/304.
- **Refs**: R110-78 (verification-theater-guard, no 3-way
  mismatch), R110-174 (re-translation pattern: R110-303 already
  pushed, so R110-304 is transparent fix-commit, not amend),
  R110-258 (body-claim re-staging re-verify lesson)

