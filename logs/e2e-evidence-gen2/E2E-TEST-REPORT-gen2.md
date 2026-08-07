# E2E-Test Report: mas-engineer New-Generation (2026-07-24)

## Setup (wie ein mensch es tut)
- Install: `./scripts/mas-reinstall.sh` → 9 root + 96 sub-recipes in goose
- Re-install was already done (symlink existed)
- Verified all 9 root + 96 sub-recipes installed in `/root/.config/goose/recipes/`

## Test 1: Self-improvement run (R40, FULL_IMPROVEMENT)
Recipe: `./recipe/sub/sub_mas-general-improver.yaml`
Params: `workspace=mas-engineer, scan_scope=mas-engineer/recipe/sub/, task=FULL_IMPROVEMENT`
Mode: PTY (per skill mas-engineer-workflow: NEVER --no-session)
Env: `RECURSION_OVERRIDE=2`, `MAS_CONFIRM=yes`, `MAS_APPROVE=y`

Result: **R40 ✅ SUCCESS** (5 min, 0 high/60 medium/1870 low findings)
- 4/6 patches applied
- 25 findings resolved via NN1 splits
- 3 multi-role agents replaced with director orchestrators:
  - sub_mas-python-repair → sub_mas-python-repair-director
  - sub_mas-framework-scanner → sub_mas-framework-scanner-director
  - sub_mas-test-fix-failures-validator → sub_mas-test-fix-failures-validator-director
- All 4 patches validated CONFORM
- Installation completed via tools/dev_install.sh
- No push (mas-mode skipped per recipe instruction)

## Test 2: Smoke test all 96 sub-recipes via `goose run --recipe X --explain`
**77/96 OK, 19/96 BROKEN (all 19 wegen `author:` bug)**

### ROOT CAUSE: author-schema-mismatch
- 20 sub-recipes have `author: "MAS Engineering"` (or "MAS Marketing Team") as **string**
- Goose schema expects `author: {name, email}` as **struct**
- Symptom: `Error: author: invalid type: string "MAS Engineering", expected struct Author`
- 100% correlation: 0/76 ohne author broken, 20/20 mit author broken
- Author field is optional (76/96 recipes have no author field, all work)

### Fixed by R40 (indirectly, 1 of 20):
- sub_mas-test-fix-failures-validator: was broken, R40 split it into director
  (which has no author field) → now OK ✓

### Still broken (19):
- sub_mas-content-writer (Marketing)
- sub_mas-email-campaign-manager (Marketing)
- sub_mas-seo-researcher (Marketing)
- sub_mas-social-media-manager (Marketing)
- sub_mas-test-fix-failures-{applier,designer,director,finder,ranker} (5)
- sub_mas-e2e-auto-repair-{director,runner,validator} (3)
- sub_mas-e2e-german-fixes-{checker,director,runner,validator} (4)
- sub_mas-e2e-phoenix-fixes-{director,runner,validator} (3)

## Test 3: New-generation sub-recipes (worktree-manager, signal-generator, etc.)
**5/6 tested OK via --explain:**
- ✓ sub_mas-worktree-manager
- ✓ sub_mas-signal-generator
- ✓ sub_mas-degradation-handler
- ✓ sub_mas-team-packager
- ✓ sub_mas-framework-scanner (now: sub_mas-framework-scanner-director)

**1/6 not testable standalone (delegator-only):**
- sub_mas-test-fix-failures-{finder,ranker,designer,applier,validator,director}
  → 5 of these are broken (author-bug), 1 (validator) is OK

## Conclusion
- **R40 self-improvement run:** ✅ WORKED (5 min, 4 patches, -25 findings)
- **5 of 7 new-generation recipes:** ✓ WORK (worktree, signal, degradation, team-packager, framework-scanner)
- **1 of 7 new-generation recipes (test-fix-failures):** ⚠️ PARTIAL (1/6 sub-recipes OK, 5/6 broken wegen author-bug)
- **1 of 7 new-generation recipes (e2e-verify-*):** ❌ ALL 3 BROKEN (10 sub-recipes broken wegen author-bug)

The **author-schema-mismatch is the dominant blocker** for the new generation.
Fix: 30-line patch (remove `author:` line from 19 recipes, or convert to struct).

## Files in this evidence folder
- `prompt-test-fix-failures.txt` — initial attempt (failed due to --recipe X -i incompatibility)
- `self-improvement-full.log` — the R40 self-improvement run, 233K, 5 min
- `BUG-REPORT-author-schema-mismatch.md` — root cause + repro + fix options
- `E2E-TEST-REPORT-gen2.md` — this report

## What was NOT tested
- Full e2e pipeline: 3-stage test-fix-failures demo (finder→ranker→designer→validator→applier)
  — only test-fix-failures-director can be invoked, the 5 sub-recipes are broken
- e2e-verify-phoenix-fixes, e2e-verify-german-fixes, e2e-verify-auto-repair
  — all 3 root recipes have broken sub-recipes (10 broken total)
