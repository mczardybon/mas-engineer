# R110-125 — STATUS.md R110-78 PHASE 3d entry + CHANGELOG-2026-08-04 (non-breaking follow-up to R110-124)

## CONTEXT

R110-78 spec-drift lesson was closed by R110-123 (commit 6e8d280,
2026-08-04). STATUS.md table currently lists PHASE 3 = 3 sub-phases
(3a R110-118, 3b R110-120, 3c R110-121) but R110-124 (5b82fab) added
a 4th sub-phase: scanner-side HARDCODE-STALE + STALE-LITERAL
detection in dev_im_finder_scan.py.

The STATUS.md table is missing a 3d row for R110-124, AND the
"Overall: 5/5 mas-engineer PHASEN done" line does not include 3d
either. The narrative also says "7 R-Nummern" but the actual count
is 8 (R110-77, 94, 100, 106, 118, 120, 121, 124).

R110-125 closes this documentation gap WITHOUT amending R110-124
(per R110-24: 0 amend on non-breaking changes).

ALSO: per mas-engineer-commit-protocol section 7, R-sprint
completions warrant a CHANGELOG entry. R110-124 closed R110-78
PHASE 3d (sub-phase completion) without CHANGELOG update. R110-125
adds CHANGELOG-2026-08-04-r110-78-final-closure.md to document
the full closure of the R110-78 lesson across all 4 sub-phases.

## DIREKTIVE 1: ADD 3d row to STATUS.md table

In `.directives/STATUS.md` table, after line 48 (3c), add new
row for 3d. Locate by content not line number.

```markdown
| 3d | scanner Pattern A+B | DONE | 2026-08-04 | 2026-08-04 | 5b82fab (R110-124) | PHASE 3d closed: dev_im_finder_scan.py:check_hardcode_stale() + check_stale_literal() wrap dev_self_audit Patterns A+B (lazy importlib import), 6 HARDCODE-STALE-* types emit (18 occurrences on recipe/instructions/), 2 new tests pass (1286→1288) |
```

Verify uniqueness: "3c" + "STALE-LITERAL" must match EXACTLY once.

## DIREKTIVE 2: UPDATE STATUS.md narrative

In the "**Overall**: 5/5 mas-engineer PHASEN done" block, update:

OLD: "PHASE 3 (R110-118 sub_mas-self-audit + dev_self_audit +
       dev_spec_invariant + Check 18) + PHASE 3b (R110-120 STEP 0.6
       self-audit in IM-pipeline) + PHASE 3c (R110-121 STALE-LITERAL
       Pattern B fix)."

NEW: "PHASE 3 (R110-118 sub_mas-self-audit + dev_self_audit +
       dev_spec_invariant + Check 18) + PHASE 3b (R110-120 STEP 0.6
       self-audit in IM-pipeline) + PHASE 3c (R110-121 STALE-LITERAL
       Pattern B fix) + PHASE 3d (R110-124 scanner Pattern A+B
       detection in dev_im_finder_scan.py)."

ALSO update the "Total: 7 R-Nummern" line to "Total: 8 R-Nummern":
OLD: "R110-77, R110-94, R110-100, R110-106, R110-118, R110-120,
      R110-121"
NEW: "R110-77, R110-94, R110-100, R110-106, R110-118, R110-120,
      R110-121, R110-124"

## DIREKTIVE 3: ADD CHANGELOG entry

Create new file `mas-engineer/docs/CHANGELOG-2026-08-04-r110-78-final-closure.md`
per protocol section 7 template.

```markdown
# MAS-Engineer Changelog -- 2026-08-04 -- R110-78 Final Closure

## OK R110-78 spec-drift lesson -- CLOSED (all 4 sub-phases done)

**Task:** Close R110-78 spec-drift lesson across all 4 PHASE 3
sub-phases. Make mas-engineer spec-drift-resistant.

**Approach:** Iterative dispatch via R110-117 mechanism. Each
sub-phase independently verified (pytest 1281→1288 = +7 tests,
dev_self_audit: 20 WARN, dev_spec_invariant: 0 BLOCKER).

**PHASE 3 sub-phases:**
- 3a (R110-118): sub_mas-self-audit agent + dev_self_audit.py +
  dev_spec_invariant.py + pre-push Check 18 -- self-audit
  agent audits recipe/instructions/ for Patterns A/B/C
- 3b (R110-120): STEP 0.6 in sub_mas-im-finder.md -- self-audit
  auto-invoked in improvement-pipeline, MM9-EXT findings,
  BLOCKER fail-fast before findings-write
- 3c (R110-121): STALE-LITERAL Pattern B fix -- sales→dev-team
  in 3 files, Pattern B bug-fix, 0 STALE-LITERAL findings
- 3d (R110-124): dev_im_finder_scan.py:check_hardcode_stale() +
  check_stale_literal() -- standalone scanner now detects
  HARDCODE-STALE-* + STALE-LITERAL-*, 25 findings on
  recipe/instructions/ (was 2)

**Result via 4-layer defense:**
- pre-push Check 18 (test↔recipe count-drift BLOCKER)
- im-finder STEP 0.6 (self-audit auto-invoke, MM9-EXT)
- dev_self_audit ad-hoc (manual scan via 3 patterns)
- standalone scanner (R110-124, fires on ad-hoc invocation
  AND as sub-step in pre-apply hook)

**Files modified (R110-78 closure, 8 commits):**
- R110-77: docs/skill pre-push-gate (hermes PHASE 4)
- R110-94 + R110-100: PHASE 1 fixes
- R110-106: PHASE 2 SD-* finding type
- R110-118: PHASE 3a sub_mas-self-audit + dev_self_audit
- R110-120: PHASE 3b STEP 0.6 in im-finder
- R110-121: PHASE 3c STALE-LITERAL fix
- R110-124: PHASE 3d scanner Pattern A+B
- R110-123: R110-78 closure entry in STATUS.md (doc-only)
- R110-125: this changelog + 3d row in STATUS.md (doc-only)

**E2E-N result:** OK 4-layer defense verified, 0 regressions
(20 HARDCODE-WARN documented, 0 STALE-LITERAL, 0 BLOCKER).

**Verified (R110-125 pre-conditions, 2026-08-04):**
- pytest: 1288/1288 PASS (delta R110-124: +2)
- dev_self_audit: 20 WARN unchanged
- dev_spec_invariant: 0 BLOCKER unchanged
- 0 secrets in R110-124 commit (post-flight verified)
- 0 amend (R110-124 stays as 5b82fab, R110-125 is new commit)
```

## DIREKTIVE 4: VERIFY (R110-116 transparency)

After DIREKTIVE 1+2+3:

  1. grep "3d" .directives/STATUS.md → 1 match (the new row)
  2. grep "R110-124" .directives/STATUS.md → ≥1 match in the
     3d row Effekt column
  3. wc -l .directives/STATUS.md → original +3 lines (1 new
     table row + 2 narrative edits)
  4. ls -la docs/CHANGELOG-2026-08-04-r110-78-final-closure.md
     → exists, ~50 lines
  5. python3 -m pytest tests/ -q → 1288/1288 PASS unchanged
     (no code touched, only docs)
  6. dev_spec_invariant: 0 BLOCKER unchanged

## SCOPE

  - mas-engineer/.directives/STATUS.md (DIREKTIVE 1: +1 table
    row, DIREKTIVE 2: 2 narrative edits)
  - mas-engineer/docs/CHANGELOG-2026-08-04-r110-78-final-
    closure.md (DIREKTIVE 3: new file ~50 lines)
  - .directives/STATUS.md (R110-125 entry)
  - .state/directive_already_applied.json (marker)

## PRE-CONDITIONS

  - 5b82fab (R110-124) on origin/cleanup ✓
  - pytest 1288/1288 PASS ✓
  - dev_self_audit: 20 WARN unchanged ✓
  - dev_spec_invariant: 0 BLOCKER ✓
  - 0 secrets in R110-124 commit ✓
  - hooks active (core.hooksPath=mas-engineer/.githooks) ✓
  - mas-engineer-commit-protocol skill loaded BEFORE this
    directive (R110-124 post-mortem lesson applied)

## ACCEPTANCE

  - STATUS.md table has 3a, 3b, 3c, 3d rows
  - STATUS.md narrative lists R110-118/120/121/124
  - CHANGELOG-2026-08-04-r110-78-final-closure.md exists
  - pytest 1288/1288 PASS (no regression)
  - 0 amend (R110-124 5b82fab stays as-is)
  - commit title uses `wrench` emoji per protocol section 1
  - commit body uses 5-section Bug/Fix/E2E/R-evidence/
    Pre-push-gate format per protocol section 1
  - pre-commit + pre-push hooks active + pass
  - 0 secrets in commit
  - dispatched via R110-117 mechanism

## 3 HOOK POINTS

1. PRE-APPLY: pre-apply hook (R36 unlock if needed)
2. POST-APPLY: post-apply hook (pytest + scan + status check)
3. ERROR: rollback via git checkout

## IDEMPOTENZ

pre-apply 2nd returns `ok=false, reason=already applied`.

## TESTING (end-to-end via R110-117 dispatch)

```bash
# 0. R36 unlock (if cost-gate)
[archive today's entries if cost > $20]

# 1. pre-apply (fresh)
rm -f .state/directive_already_applied.json
python3 tools/dev_directive_applier.py --hook pre-apply \
  .directives/R110-125-status-3d-changelog.md

# 2. apply via R110-117 dispatch
set -a; . ./.env; set +a
export RECURSION_OVERRIDE=2
export MAS_TASK=DIRECTIVE_APPLY
export MAS_CONFIRM=yes
export MAS_APPROVE=y
echo "per directive .directives/R110-125-status-3d-changelog.md apply DIREKTIVE 1+2+3+4: add 3d row to STATUS.md table (after 3c, with R110-124 5b82fab reference), update narrative 'Overall' + 'Total R-Nums' lines to include PHASE 3d, create mas-engineer/docs/CHANGELOG-2026-08-04-r110-78-final-closure.md per protocol section 7 template. Verify 3d row appears, narrative has 4 sub-phases, CHANGELOG file exists, pytest 1288/1288 still PASS (no code touched). ack" | \
  timeout 600 goose run --with-builtin developer \
  --recipe recipe/sub/sub_mas-general-improver.yaml --no-session \
  > /tmp/r110125-improver.log 2>&1

# 3. verify
grep -c "| 3d " .directives/STATUS.md
# Expected: 1
grep -c "R110-124" .directives/STATUS.md
# Expected: >=1
ls -la docs/CHANGELOG-2026-08-04-r110-78-final-closure.md
# Expected: exists
python3 -m pytest tests/ -q
# Expected: 1288 passed in T.TTs

# 4. post-apply
python3 tools/dev_directive_applier.py --hook post-apply \
  .directives/R110-125-status-3d-changelog.md
```

## ANTI-PATTERNS

- NICHT amend 5b82fab (R110-24: 0 amend on non-breaking)
- NICHT modify dev_im_finder_scan.py or any code (R110-125
  is doc-only)
- NICHT skip CHANGELOG creation (protocol section 7)
- NICHT use emoji other than `wrench` (R-sprint fix-commit
  per protocol section 1 table)
- NICHT skip the 5-section body format (protocol section 1
  mandatory for wrench + book)
- NICHT push before pre-commit + pre-push hooks both pass
- NICHT skip R04-block honest: if file edits diverge from
  DIREKTIVE 1+2+3, document the divergence in commit body
- NICHT skip the 3 R110-124 protocol-violation lessons
  (R110-125 commit body must include "Supersedes: R110-124
  partial-protocol" line per R110-116 precedent)
