# R110-123 — R110-78 lesson closure entry in STATUS.md (R110-78 spec-drift = ARCHIVED)

## CONTEXT (R110-78 lesson komplett closure + R110-121 follow-up)

R110-78 spec-drift lesson (4 PHASEN originally, expanded to 5):
- PHASE 1: validator + pytest (R110-94 + R110-100) ✓
- PHASE 2: SD-* finding (R110-106) ✓
- PHASE 3: sub_mas-self-audit + dev_self_audit + dev_spec_invariant
  + Check 18 (R110-118) ✓
- PHASE 3b: self-audit in IM-pipeline STEP 0.6 (R110-120) ✓
- PHASE 3c: STALE-LITERAL Pattern B fix (R110-121) ✓
- PHASE 4: skill update (hermes-side, R110-77) ✓

STATUS.md has entry "R110-78-spec-drift" with table showing all 5
mas-engineer PHASEN (1, 2, 3, 3b, 3c) as DONE.

**BUT** the entry's **Overall** text is OUTDATED (says "3/3
mas-engineer PHASEN done" — that was the count when only PHASE
1+2+3 were done; now 5 are done: 1+2+3+3b+3c).

R110-123 fixes:
1. R110-78 entry "Overall" → "5/5 mas-engineer PHASEN done, 1/1
   hermes PHASE done. R110-78 spec-drift lesson komplett
   geschlossen + ARCHIVED-READY."
2. R110-78 entry "PHASE 3 closed" detail → updated to mention
   3+3b+3c sub-phases
3. Add `Status: ARCHIVED-READY` to R110-78 entry (analog zu
   R110-94's "ARCHIVED-READY")
4. Add `## R110-78 lesson closure` summary section to STATUS.md
   bottom (similar to existing "## R110-117+118 — self-
   improvement loop closed" section)

## DIREKTIVE 1: UPDATE R110-78 entry "Overall" in STATUS.md

Find current Overall text:
```
**Overall**: 3/3 mas-engineer PHASEN done, 3/4 PHASEN done
(hermes-side: skill-update done; mas-engineer-side: PHASE 1+2 done
via R110-94+R110-100+R110-106; PHASE 3 DONE via R110-118
— sub_mas-self-audit agent + dev_self_audit.py + dev_spec_invariant.py
+ pre-push Check 18). R110-78 spec-drift lesson komplett geschlossen.
```

Replace with:
```
**Overall**: 5/5 mas-engineer PHASEN done, 1/1 hermes PHASE done.
mas-engineer-side: PHASE 1 (R110-94+R110-100) + PHASE 2
(R110-106) + PHASE 3 (R110-118 sub_mas-self-audit + dev_self_audit
+ dev_spec_invariant + Check 18) + PHASE 3b (R110-120 STEP 0.6
self-audit in IM-pipeline) + PHASE 3c (R110-121 STALE-LITERAL
Pattern B fix).
hermes-side: PHASE 4 (R110-77 pre-push-gate skill).
**Status: ARCHIVED-READY** — R110-78 spec-drift lesson komplett
geschlossen. Total: 6 R-Nummern (R110-77, R110-94, R110-100,
R110-106, R110-118, R110-120, R110-121), 7 commits auf
origin/cleanup (R110-118 + R110-119 in PHASE 3a, R110-120 in
3b, R110-121 in 3c; plus R110-117 dispatch mechanism + R110-116
commit-hygiene + R110-115 RECURSION-GUARD v3). pytest 1284→1286
(+2 tests in R110-118+121). 4 BLOCKER + 6 STALE-LITERAL + 5
simple-stale HARDCODE = 15 findings gefixt.
```

## DIREKTIVE 2: ADD Status: ARCHIVED-READY line to R110-78 entry

After the "**Datei**: ..." line, before the "**Created**" line,
add:
```
- **Status**: ARCHIVED-READY (alle 5 PHASEN done, PHASE 4 hermes
  done, R110-78 lesson komplett geschlossen, R110-123 entries
  updated + this closure summary added)
```

NOTE: R110-94 has `**Overall**: 1/1 PHASE done. Status:
ARCHIVED-READY` inline. R110-78 entry has Status below the
**Datei** line. Either pattern acceptable; use whichever fits
the existing R110-78 entry structure.

## DIREKTIVE 3: ADD R110-78 lesson closure summary section

After existing "## R110-117+118 — self-improvement loop closed"
section, add new section:

```markdown
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
- 6 R-Nummern, 7 commits auf origin/cleanup (R110-118+119 in
  PHASE 3a, R110-120 in 3b, R110-121 in 3c; plus R110-117
  dispatch mechanism + R110-116 commit-hygiene + R110-115
  RECURSION-GUARD v3)
- pytest 1284→1286 (+2 tests: Check 18 in R110-118, test_step_0_6
  in R110-120, test_pattern_b in R110-121 — total 3 tests across
  R110-118+120+121, +2 in net registry because Check 18 was
  internal helper, not a new pytest test function; verify exact
  count from `pytest --collect-only` if needed)
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
```

NOTE: pytest count +2 must be VERIFIED by the agent. R110-78
impact listing: R110-118 added 3 tests (Check 18 + 2 helpers) per
R110-118 commit message "5 new files (sub_mas-self-audit agent +
dev_self_audit.py + dev_spec_invariant.py + Check 18 test)",
but actual pytest count went 1281→1284 = +3, NOT +2. R110-120
added +1 (test_step_0_6), R110-121 added +1 (test_pattern_b).
Total: 1281→1287 = +6 tests. Verify with `pytest --collect-only
-q | tail -3` if uncertain.

## DIREKTIVE 4: RE-RUN + VERIFY (R110-116 transparency)

After DIREKTIVE 1+2+3:

  1. STATUS.md updates: verify with `git diff` that:
     (a) R110-78 entry Overall = "5/5 mas-engineer PHASEN done"
     (b) Status: ARCHIVED-READY tag present
     (c) New closure summary section "## R110-78 lesson —
         spec-drift = ARCHIVED" present
  2. grep verify: no regressions in other R110-* entries
  3. dev_spec_invariant: 0 BLOCKER (unchanged)
  4. pytest 1286/1286 PASS (unchanged, this commit is doc-only)
  5. R36 cost: archive today's entries if > $20 budget

## SCOPE

  - .directives/STATUS.md (3 sections updated: R110-78 entry
    Overall + Status line + new closure summary section)

## PRE-CONDITIONS

  - 83e4ce7 (R110-121) auf origin/cleanup ✓
  - pytest 1286/1286 PASS ✓
  - dev_spec_invariant: 0 BLOCKER ✓
  - dev_self_audit: 20 WARN (0 STALE-LITERAL) ✓
  - cost 24h: < $20 budget (R36 unlock ggf.)

## ACCEPTANCE

  - STATUS.md R110-78 entry Overall = "5/5 mas-engineer PHASEN
    done, 1/1 hermes PHASE done. Status: ARCHIVED-READY"
  - STATUS.md has new "## R110-78 lesson — spec-drift = ARCHIVED"
    section with PHASE 1+2+3+3b+3c+4 summaries
  - pytest 1286/1286 PASS (no test regressions)
  - 0 secrets
  - R04-block honest: exact pytest count +N must be VERIFIED
    (R02 lesson: don't claim +2 if actually +6)
  - 0 amend (R110-24 non-breaking)
  - dispatched via R110-117 mechanism (per-directive trigger)

## 3 HOOK POINTS

1. PRE-APPLY: pre-apply hook (R36 unlock if needed)
2. POST-APPLY: post-apply hook (pytest + scan + verify STATUS.md
   diff)
3. ERROR: rollback via git checkout (R36 if changes archive
   failed)

## IDEMPOTENZ

pre-apply 2nd returns `ok=false, reason=already applied`.

## TESTING (end-to-end via R110-117 dispatch)

```bash
# 0. R36 unlock (if cost-gate)
[archive today's entries if cost > $20]

# 1. pre-apply (fresh)
rm -f .state/directive_already_applied.json
python3 tools/dev_directive_applier.py --hook pre-apply \
  .directives/R110-123-r110-78-lesson-closure.md

# 2. apply via R110-117 dispatch
set -a; . ./.env; set +a
export RECURSION_OVERRIDE=2
export MAS_TASK=DIRECTIVE_APPLY
export MAS_CONFIRM=yes
export MAS_APPROVE=y
echo "per directive .directives/R110-123-r110-78-lesson-closure.md apply DIREKTIVE 1+2+3+4: update STATUS.md R110-78 entry Overall (3/3 → 5/5 mas-engineer PHASEN done, add Status: ARCHIVED-READY), add new section '## R110-78 lesson — spec-drift = ARCHIVED' with PHASE 1+2+3+3b+3c+4 summary + total impact. Doc-only, no test changes. ack" | \
  timeout 600 goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session \
  > /tmp/r110123-improver.log 2>&1

# 3. verify
git diff .directives/STATUS.md | head -50
# Expected: R110-78 entry Overall updated + Status: ARCHIVED-READY
# + new closure section
cd tools && python3 -m dev_spec_invariant --repo-root ..
# Expected: 0 BLOCKER (unchanged)
cd .. && python3 -m pytest tests/ -q
# Expected: 1286/1286 PASS (doc-only, no test changes)

# 4. post-apply
python3 tools/dev_directive_applier.py --hook post-apply \
  .directives/R110-123-r110-78-lesson-closure.md
```

## ANTI-PATTERNS

- NICHT claim pytest count +2 wenn actually +6 (R02: verify
  with `pytest --collect-only -q | tail -3` BEFORE commit body
  written)
- NICHT modify other R110-* entries (R110-94, R110-100, R110-106,
  R110-118, R110-120, R110-121 already accurate; R02: don't
  touch what isn't broken)
- NICHT remove R110-78 entry from "Aktive Direktiven" (R02:
  ARCHIVED-READY entries STAY in active section, they're not
  removed; pattern from R110-94)
- NICHT amend 83e4ce7 (R110-121)
- NICHT modify dev_self_audit.py or dev_spec_invariant.py (R02:
  doc-only commit per DIREKTIVE scope)
- NICHT skip verify with git diff (R02: see actual changes
  before claiming "STATUS.md updated")
