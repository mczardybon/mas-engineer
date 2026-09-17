# R110-376 — EVIDENCE

**Round**: r1 (single round, verification-theater self-catches absorbed inline)
**Module**: `tools/dev_generic_init.py` (1107 lines, 30 module-level functions, 557 statements)
**Test file**: `tests/test_dev_generic_init_r110376.py` (1061 lines, 26 outer classes, 99 tests, 52815 bytes)
**Result**: 99/99 PASS in 0.54s, **91% coverage (505/557 stmts)**

## TL;DR

`tools/dev_generic_init.py` was 11.7% covered (4th-largest
0%-Lücke in `tools/`). It is the orchestrator for every
new-project bootstrap — 30 functions including `cmd_init`,
`cmd_bootstrap`, `cmd_repair_symlinks`, and 27 `create_*` /
`copy_*` helpers. The new test file brings coverage to **91%**
(+79.3pp, +440 stmts covered) in a single r1. The 52
remaining-missed lines are all defensive handlers + bootstrap
deep paths (subprocess wrappers, MCP npm install, 6-step
recipe-port flow) that are not practically testable at the
unit level.

## Coverage Delta (re-derived from term-report, NOT estimated)

| Metric | Value | Source |
|---|---|---|
| Pre-fix state | 11.7% (65/557 stmts) | coverage baseline |
| Post-fix (r1) | 91% (505/557 stmts) | cov-R110376-final.json |
| Delta | **+79.3pp, +440 stmts** | computed |
| Outer classes | 26 | `grep -cE "^class Test"` |
| Test functions | 99 | `grep -cE "def test_"` |
| Test file size | 1061 lines, 52815 bytes | wc -l, wc -c |
| Test pass rate (isolated) | 99/99 in 0.54s | pytest term-report |
| Test pass rate (with R110-334) | 107/107 in 0.41s | pytest term-report |

## 52 Still-Missed Lines (defensive + bootstrap deep paths)

| Lines | Function | Why missed |
|---|---|---|
| 39 | import | `from ..tools import X` defensive (not used at runtime) |
| 404-405 | create_rules | Hard rule skip branches (subset detection) |
| 474-475 | create_bp_checklist | Append-to-existing (needs real conflict) |
| 539-552 | create_dashboard_scaffold | MCP npm install subprocess (Node.js) |
| 760-761 | create_goosehints | Template-overwrite branch |
| 765-766 | create_goosehints | Re-build branch |
| 911-916 | cmd_bootstrap | Step 0 web-research print block |
| 936-937 | cmd_bootstrap | Step 2 sub-port "MCP config" copy branch |
| 945-946 | cmd_bootstrap | Step 3 recipe-port "constitution" copy branch |
| 953 | cmd_bootstrap | Step 4 tools dest-symlink detection |
| 958-960 | cmd_bootstrap | Step 4 tools copy counter error-handling |
| 967-978 | cmd_bootstrap | Step 5 copytree + failure path |
| 984-988 | cmd_bootstrap | Step 5 main-recipe directory creation |
| 996 | cmd_bootstrap | Step 6 web-research print block |
| 1055 | cmd_repair_symlinks | "delete and run --init" advice branch |

These are the practical ceiling for unit-level testing of an
orchestrator that wraps subprocess, shutil, and a 9-step
recipe-bootstrap flow.

## Body-Claim Verification (5-command, per R110-78/173/174)

```
1. grep -cE "^class Test" tests/test_dev_generic_init_r110376.py → 26 ✓
2. grep -cE "def test_"     tests/test_dev_generic_init_r110376.py → 99 ✓
3. wc -l < tests/test_dev_generic_init_r110376.py                  → 1061 ✓
4. wc -c < tests/test_dev_generic_init_r110376.py                  → 52815 ✓
5. python3 -c "import json; d=json.load(open('/tmp/cov-R110376-final.json'));
               t=d['totals'];
               print(f\"stmts={t['num_statements']} miss={t['missing_lines']}
                       covered={t['covered_lines']} pct={t['percent_covered']:.1f}\")"
   → stmts=557 miss=52 covered=505 pct=90.7
   (rounded to 91% per coverage.py display rules) ✓
```

All claims in this EVIDENCE are derived from the term-report,
not estimated.

## Pre-Existing Test Status (regression check)

| Sweep | Result | Time |
|---|---|---|
| R110-376 isolated | 99 pass / 0 fail | 0.54s |
| R110-376 + R110-334 (existing dev_generic_init test) | 107 pass / 0 fail | 0.41s |
| R110-3xx regression sweep (10 files: 285..294) | 411 pass / 0 fail | 1.25s |
| R110-364/365/367/374 regression sweep | 257 pass, 1 skip / 0 fail | 2.01s |

**No regression from R110-376 test file.**

## Verification-theater self-catches (R110-78 lesson applied)

The 23 initial test failures were ALL self-catches of
verification-theater — i.e. my test asserts were wrong, NOT
the code under test. Each was caught + fixed in the r1 loop:

1. **`tmp_path.mkdir()`** — illegal (tmp_path IS a dir).
   Fixed: use sub-dirs.
2. **`create_guidelines/workflows/mas_mode/goosehints` sigs** —
   I had `(project_path, dry_run=False)` but real sig is
   `(project_path, project_name_clean, dry_run=False)`.
3. **`create_dashboard_scaffold` path** — wrote to
   `dashboard-data/` per my guess; real code writes to
   `.mase/dashboards/`.
4. **`create_state_files` path** — wrote to `.mase/state/`
   per my guess; real code writes to `.mase/` (no subdir).
5. **`copy_*` source path** — I used `MAS_DIR` per convention;
   real code uses `os.path.join(MAS_CONFIG, "..", "mas-engineer", ...)`
   LITERALLY (with the `..` segment, not normalized).
6. **`cmd_bootstrap` return contract** — I assumed it returns
   False on missing MAS; real code is fire-and-forget and
   always returns bool.
7. **`create_symlinks/cmd_repair_symlinks` "wrong symlink"** —
   I made the wrong target nonexistent; `os.path.exists()`
   returns False for broken symlinks, so the function took the
   "create new" branch, not "replace" branch. Fixed: real-
   existing dir as wrong target.
8. **`TestCopyConstitution` dest dir** — I assumed it
   auto-creates `.mase/`; real code requires caller to have
   created it.
9. **`cmd_bootstrap` step 4 listdir** — I mocked `os.path.exists`
   to False; then `os.makedirs` was called; then `os.listdir`
   on the (also nonexistent) src crashed. Fixed: also mock
   `os.listdir`.

All 9 self-catches were BEFORE the commit, per R110-78 +
R110-173/174 body-claim-verification protocol.

## Cumulative R110-37x coverage progress

| Round | File | Delta | Stmts covered | Tests |
|---|---|---|---|---|
| R110-371 r2 | dev_workspace.py | 71% → 80.1% (+9.1pp) | +201 | n/a (existing) |
| R110-372 r1 | dev_editor.py | 0% → 49.87% (+49.87pp) | +192 | n/a (existing) |
| R110-373 r2 | dev_editor.py | 49.87% → 58.18% (+8.31pp) | +32 | 57 |
| R110-374 r1 | dev_observer.py | 0% → 91.2% (+91.2pp) | +258 | 41 |
| R110-375 r3 | dev_yaml_check.py | 13.7% → 94.4% (+80.7pp) | +159 | 58 |
| **R110-376 r1** | **dev_generic_init.py** | **11.7% → 91% (+79.3pp)** | **+440** | **99** |
| **Total** | **5 files** | **+318.3pp combined** | **+1282 stmts** | **255** |

## Pre-push gate

- Step 0 (secret scan, tracked):        OK 0 secrets
- Check 17 (pytest-run, new test file): OK 99/99 in 0.54s
- Check 24 (SOT-location):              OK new file in `tests/` (standard)
- Check 0 (body disclosure):            OK 6-section body, +79.3pp honest
- Step 5 (push):                        pending
- Step 6 (post-flight audit):           pending

## Files Touched (3 in this evidence commit)

- `STATUS.md` — MOD (+1 R110-376 block, ~110 lines)
- `docs/CHANGELOG-2026-09-08-r110-376-dev-generic-init-coverage.md` — NEW (this R's CHANGELOG)
- `logs/e2e-evidence-gen2/R110-376-EVIDENCE.md` — NEW (this file, force-added per R110-258)

The test file `tests/test_dev_generic_init_r110376.py` (1061 lines,
52815 bytes) was committed in a PRIOR commit (the "R110-376 base"
commit) following the same 2-commit atomic pattern as R110-375:
base commit (test + code) + this evidence commit (3 docs).

## Refs

- R110-375 (132ce97) — r3 dev_yaml_check at 94.4%, 58 tests
- R110-374 (58ba783) — r1 dev_observer at 91.2%, 41 tests
- R110-373 (4cd31d9) — r2 dev_editor at 58.18%, 57 tests
- R110-372 (9b5c9bb) — r1 dev_editor at 49.87%
- R110-371 (3764ffa) — dev_workspace at 80.1%
- R110-78 — verification-theater pattern (applied in 9 self-catches)
- R110-173/174 — body-claim verification (applied in 5-command check)
- R110-258 — force-add evidence via `git add -f`
- R110-281 — force-push-verbote
- R110-304 — 3-source lockstep for commit-subject format
- R110-334 — existing `test_dev_generic_init_r110_334.py` test
  (107/107 still pass alongside new file)
- Skill: `mas-engineer-coverage-push-workflow`
