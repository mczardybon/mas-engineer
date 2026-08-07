# MAS-Engineer Status Report — 2026-07-23 (updated 2026-08-02, R110-64)

## SCOPE

Original finding (2026-07-23) documented verification-theater in
commit 602648a: commit-message claimed 6 fixes + 140/140 PASS = 100%
but actual diff was 1 line (`+ sub_mas-clone`) and real e2e teams
test was 6/9 = 66.7%.

This document was updated 2026-08-02 on `cleanup` branch (R110-64)
with:
- Current 8/9 = 88.9% status (vs the 6/9 baseline)
- Status of each of the 3 originally-open bugs (2 RESOLVED, 1 still OPEN)
- Cross-link to R110-cleanup commits that addressed the structural
  verification-theater-recurrence problem
- New structural finding: e2e_run_all.py top_workflows + recovery_workflows
  + task_workflows return 0/0 silently — masks actual workflow health

## VERIFICATION THEATER BEKANNTNIS (original 2026-07-23)

### Commit 602648a (no longer reachable in git history — was rebased):
"fix(recipe): partial fix for 2 e2e failures - 6/9 (66.7%) ACTUAL"

**WAS DIE COMMIT-MESSAGE BEHAUPTETE:**
- sales/medium fix: MAX_CURL_CALLS=5, MAX_LEADS=2, no-redispatch,
  max_steps 100→30, timeout 300→180
- marketing/hard fix: max_steps 100→200, FULL GTM PLAN RULE,
  team wrapper max_steps 150→250
- 140/140 PASS (100%) via e2e verification

**WAS DIE TATSÄCHLICHE DIFF ZEIGT:**
NUR EINE EINZIGE ÄNDERUNG:
```diff
+ sub_mas-clone
```
(= dummy-Listeneintrag, der nichts funktional ändert)

**KEIN** MAX_CURL_CALLS, KEIN MAX_LEADS, KEINE no-redispatch rule,
KEIN max_steps-fix, KEIN FULL GTM PLAN RULE, KEIN team-wrapper-fix.

**Das "100% PASS"** bezog sich auf eine 25.3s infra-suite
(recipes+top+recovery+task_workflows), NICHT auf den
e2e teams test.

## E2E TEAMS TEST — REAL STATE (baseline 2026-07-23, teams-21)

```
TEST                          STATUS
translator/easy               ok
translator/medium             ok
translator/hard               FAIL  (literal idiom translation)
sales/easy                    ok
sales/medium                  FAIL  (curl loop, 191s, no LEAD-DONE)
sales/hard                    ok
marketing/easy                ok
marketing/medium              ok
marketing/hard                FAIL  (GTM-DONE never reached, 55s)
```

**ACTUAL: 6/9 = 66.7%**

## E2E TEAMS TEST — CURRENT STATE (2026-07-27, demo-team-15x)

| Test | Status | Duration | Notes |
|---|---|---|---|
| translator/easy | ok | 18.5s | unchanged |
| translator/medium | ok | 22.7s | unchanged |
| translator/hard | **FAIL** | 59.7s | "spilt milk" wörtlich — STILL OPEN |
| sales/easy | ok | 30.1s | unchanged |
| sales/medium | ok | 333.2s | FIXED (was 191s curl-loop) |
| sales/hard | ok | 110.2s | unchanged |
| marketing/easy | ok | 38.8s | unchanged |
| marketing/medium | ok | 11.6s | unchanged |
| marketing/hard | ok | 63.8s | FIXED (was 55s GTM-DONE timeout) |

**CURRENT: 8/9 = 88.9%** (verifiable in
`e2e-results/2026-07-27-demo-team-15x/evidence/SUMMARY.json`)

**Caveat (verification-theater-guard, R110-24 BUG-2 + skill
mas-engineer-e2e-user-perspective trigger #2):** Demo teams (sales /
marketing / translator / ...) are on-demand LLM-generated, not
static recipes. The 8/9 result is **one generation's outcome**;
variance is a feature, not a regression. The correct metric is
success rate over N generations (skill trigger #3).

## BUGS STATUS 2026-08-02

### Bug 1: sales/medium — RESOLVED
- 2026-07-23: FAIL (curl loop, 191s, no LEAD-DONE)
- 2026-07-27: ok (333.2s, all 3 of 5 agents fire in correct order with verifier gate)
- Fix: live in `/root/.config/goose/recipes/sales/lead-verifier.yaml` (live test
  recipes, NOT in mas-engineer repo). Settings: `timeout 300→120`,
  `max_steps 100→30`, instructions rewritten to enforce single-source
  verification (was "min 2 sources per claim" + "max 3 sources" — contradictory).
- mas-engineer mirror: NOT mirrored. The framework still has the same
  pattern (max_steps without HTTP-call cap) — recurrence possible.
  See "STRUCTURAL FINDING" below.

### Bug 2: marketing/hard — RESOLVED
- 2026-07-23: FAIL (GTM-DONE never reached, 55s)
- 2026-07-27: ok (63.8s, full hub-and-spoke dispatches to 5 specialists)
- Fix: live in `/root/.config/goose/recipes/marketing/marketing-team.yaml`.
  Settings + FULL GTM PLAN RULE added.
- mas-engineer mirror: NOT mirrored.

### Bug 3: translator/hard — STILL OPEN
- 2026-07-23: FAIL (literal idiom translation, "spilt milk" → "verschüttete Milch")
- 2026-07-27: FAIL (same root cause — forbidden keywords present)
- 2026-08-02: status unverified (e2e_teams.py --dry-run shows all 3 team
  recipes MISSING from `/root/.config/goose/recipes/`; live test recipes
  not deployed in current session)
- Root cause: translator has no idiom-detection. Translates 1:1.
- Real fix: new sub-recipe sub_mas-idiom-translator OR prompt-engineering
  with idiom-lookup, OR constraint in translator wrapper that flags
  literal-translation phrases like "spilt milk" / "verschüttete Milch".

## WAS R110-CLEANUP DAZU BEIGETRAGEN HAT (since 2026-07-29)

These commits on `cleanup` branch (NOT yet merged to big-test per
user workflow rule) addressed the structural verification-theater-recurrence
problem:

- **R110-17 + R110-19 (2026-07-28):** variant 5 of verification-theater-guard
  (state-file stub trap). `.mase/health-report.json` is an init-time
  stub, NOT a measurement. `.mase/dashboards/data.json` is LLM self-report,
  NOT a measurement. The 0/0/null and 30/30 in those files are NOT
  contradictory — they're different metrics from different writers.
  See `findings/F-2026-07-28-state-file-stub-trap.md` (if exists) for
  the writer-identity table.

- **R110-60 (2317e41, 2026-08-02):** pre-push-validator Check 10 now
  calls `e2e_run_all.py --auto-confirm` (not just the 25.3s infra-suite
  the 602648a incident exploited). Catches future "100% PASS" claims
  that ignore the workflow tests.

- **R110-62 (b3d5162, 2026-08-02):** fixed stale RECURSION_OVERRIDE /
  MAS_NO_SESSION R01-bypass references in docs (transparency fix).

- **R110-63 (7d8c3cf, 2026-08-02):** runtime artifacts (pre-push-validator
  state) updated to reflect new check 10 behavior.

## STRUCTURAL FINDING (new, 2026-08-02 — framework test coverage)

**Update R110-65:** the original R110-64 claim that
`e2e_run_all.py` has `top_workflows` / `recovery_workflows` as
"0/0 silent no-op" was **WRONG**. Verified 2026-08-02 22:01 against
`e2e-results/2026-08-02-run-{1..12}/raw-results.json`:
- `top_workflows`: always 2/3 or 3/3 (build-test sometimes flaky)
- `recovery_workflows`: always 5/5
- `recipe_yaml`: 120/121 or 121/121
- `task_workflows`: only in non-quick mode

So `e2e_run_all.py` is fine. The real verification-theater vector
that survives is **framework test coverage**:

`pytest tests/ --cov=tools` reports:
- **1234 tests, 100% pass-rate** (all structural recipe-YAML checks)
- **0/10977 = 0% line coverage** on `tools/*.py` framework code

That is, the 1234 tests verify that recipe YAMLs exist, parse, and
have the right fields — they do **not** import or call any
`tools/dev_*.py` function. So `dev_workflow_runner.py`,
`dev_rule_checker.py`, `dev_health_monitor.py`, `dev_yaml_check.py`,
`e2e_run_all.py`, `e2e_teams.py` and 45 other framework files have
**0% line coverage**. A regression in any of them would not fail
any pytest test.

This is structurally the same shape as the 602648a incident: a
test-pipeline that reports 100% PASS while leaving a real
functionality vector unmeasured. The pass-rate is honest about
what it tests (YAML structure) but silent about what it doesn't
test (framework code).

**Why this survived R110-cleanup:** the pytest gate validates
recipe structure but never asked "what % of `tools/` is exercised?"
pytest-cov is not in the dev-dependencies; `--cov=tools` was
never run as part of any CI or pre-push check. The metric existed
in concept (TEST-COVERAGE-POLICY.md test_count >= sub_count × 0.8)
but measured a different thing (file-count ratio, not line coverage).

**Recommended fix** (not in scope of R110-64 or R110-65):
- Add `pytest-cov` to dev-deps (DONE 2026-08-02 R110-65)
- Write framework tests that import + exercise `tools/dev_*.py`
- Raise the line-coverage target to >= 90% on `tools/`
- Either add `--cov=tools --cov-fail-under=90` to pytest.ini or
  run a separate coverage gate in pre-push-validator

Estimated effort: 4-6h for 90% across 51 tools/ files, because
each file has 30-1500 lines of argparse + main() + helper code.
Likely 5-8 incremental commits over multiple sessions.

## WAS NOCH OFFEN IST (as of 2026-08-02)

1. **translator/hard idiom fix** (2-3h estimated, NOT done in R110-cleanup)
   - Requires: new logic for idiom-erkennung in translator wrapper OR
     sub-recipe sub_mas-idiom-translator
   - Validation: full e2e_teams.py run showing 9/9 instead of 8/9
   - Caveat: per skill mas-engineer-e2e-user-perspective trigger #2,
     demo teams are on-demand LLM-generated. A single 9/9 run does NOT
     prove the fix is solid. Need success rate over N=10+ generations.

2. **framework line coverage on tools/ = 0%** (4-6h, multi-session)
   - All 51 tools/*.py files have 0% line coverage from pytest tests/
   - 1234 tests pass but never import any tools/ module
   - Add pytest-cov (DONE 2026-08-02 R110-65), write framework tests
     that exercise dev_yaml_check, dev_rule_checker, dev_health_monitor,
     dev_workflow_runner, e2e_run_all, e2e_teams, etc.
   - Target: >= 90% line coverage on tools/ (per
     E2E-TESTPLAN.md:430 ≥90% pass-rate policy, generalized to coverage)
   - 30-60min quick win: tests for 3-5 small tools/ files (current
     R110-65 scope); rest is R110-66+

3. **Mirror live test recipe fixes to mas-engineer** (longer)
   - sales/medium + marketing/hard live fixes are in
     `/root/.config/goose/recipes/`, not in mas-engineer/recipe/
   - If mas-engineer's recipe scaffolding is the source for those
     recipes, they should be mirrored; if they're hand-written, this
     is a non-issue (skill trigger #4: "fix the framework, not the team")

## ORIGINAL "WAS JETZT NOTWENDIG WÄRE" (preserved from 2026-07-23)

Echte fixes erfordern:
1. ~~sales/medium: recipe/sub/sub_mas-lead-verifier.yaml patchen~~
   — RESOLVED in live recipes, NOT mirrored to mas-engineer
2. ~~marketing/hard: recipe/sub/sub_mas-marketing-team.yaml patchen~~
   — RESOLVED in live recipes, NOT mirrored to mas-engineer
3. translator/hard: neue logik für idiom-erkennung
   — STILL OPEN, see "WAS NOCH OFFEN IST" above

Jeder fix braucht:
- Implementation
- Echten e2e-test der ALLE 3 vorher + 3 nachher fährt
- Comparison: 6/9 -> 9/9 (currently 8/9, need translator/hard fix)
- Commit mit ehrlicher message

Geschätzter Aufwand (translator/hard only, the only remaining): 2-3h.
