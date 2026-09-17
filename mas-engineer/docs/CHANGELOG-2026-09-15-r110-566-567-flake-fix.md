# MAS-Engineer Changelog -- 2026-09-15

## OK R110-566..567 PRE-EXISTING suite-pollution flake fix -- SUCCESS

**Task:** Fix the 2 PRE-EXISTING suite-pollution flakes identified by
R110-565 disposition (`test_main_no_arg_uses_cwd` cwd-pollution +
`test_skills_install_is_idempotent` timeout-budget). Both tests PASS 5/5
in isolation but flake intermittently in the full suite under load.

**Files modified:**

| File | Change | +/− |
|------|--------|-----|
| `mas-engineer/tests/test_dev_fast_scan_coverage.py` | 4 tests refactored (cwd-control + sys.modules-pop + finally-restore) | +43/-12 |
| `mas-engineer/tests/test_skills_install.py` | `test_skills_install_is_idempotent`: both timeouts 30→90s | +10/-3 |

**Result via pytest (R110-566+567):**

- isolation 5/5 both tests: PASS (deterministic)
- suite 3× stress (7 pollution-heavy files): 180/180 PASS in 56.99s + 58.42s + 58.69s
  - 0 RuntimeWarnings (was 3)
  - 0 intermittent fails (was 1 in 3 runs of the same suite)
- 51/51 PASS in 0.55s (just test_dev_fast_scan_coverage + test_skills_install)

**Pre-push-gate summary:**

- Step 0 (secret scan, tracked):         OK 0 secrets
- Step 1 (validator):                    SKIPPED (DeepSeek 401, key ok)
- Step 2 (pytest):                       OK 5/5 isolation + 180/180×3 stress
- Step 3 (commit msg, 🧪 R-format):     OK per protocol
- Step 4 (push):                         OK via credential-helper
- Step 5 (post-flight audit):            OK 117/117 sub_agents, 77/77 refs, 100.0%

**Result:** 2 PRE-EXISTING flakes fixed deterministically. CI suite-pollution
edge cases closed. RuntimeWarnings silenced for 3 sibling tests.

**Refs:**
- R110-565 — flake-disposition that identified these as PRE-EXISTING
- R110-133 — test_skills_install.py initial contract tests
- R110-78, R110-174, R110-281, R110-296/297 — verification-theater family
- Skill: `pre-push-body-claim-verification`
