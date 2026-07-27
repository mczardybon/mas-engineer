# Test Coverage Policy — MAS-Engineer

**Version:** 1.0.0
**Status:** ACTIVE — established by user (mczardybon) on 2026-07-25
**Owner:** Check 12 of `sub_mas-pre-push-validator`

---

## 1. Policy

The MAS-Engineer framework enforces a **minimum test-to-sub-agent ratio
of 80%** before any code can be pushed to the `Dev` branch.

**Formula:**

```
test_count  =  number of files matching mas-engineer/tests/test_*.py
sub_count   =  number of files matching mas-engineer/recipe/sub/*.yaml
              (excluding files containing "ORIGINAL" in name)
threshold   =  floor(sub_count × 0.8)
gate_passed =  test_count >= threshold
```

**Rationale (user requirement, 2026-07-25):**

> "tests/test_*.py count must be >= recipe/sub/*.yaml count × 0.8"

Each sub-agent in `recipe/sub/` exposes a surface area that warrants a
dedicated regression test. Shipping sub-agents without tests is the
primary mechanism by which mas-engineer's self-improvement loop
introduces silent regressions — the same pattern that motivated
[BUG-BRIEF-2026-07-23.md](./BUG-BRIEF-2026-07-23.md) (verification
theater).

---

## 2. Current State (as of 2026-07-27)

| Metric | Value |
|--------|-------|
| sub_agents (yaml, excluding *.llm-backup-r89) | 119 |
| sub_agents (yaml, including backups) | 124 |
| tests (test_*.py) | 6 |
| threshold_80pct | 95 |
| gap (tests needed) | **89** |
| ratio | 0.050 |
| gate_passed | **false** |

**Status:** the gate currently FAILS by design. The framework was
intentionally allowed to ship with this debt to expose the test-coverage
problem and force incremental growth.

**Three existing test files:**

| File | Lines | Scope |
|------|-------|-------|
| `test_pre_check_benchmark.py` | 255 | pre_check vs LLM-validator agreement |
| `test_unix_test_word.py` | 176 | POSIX `test` builtin regression |
| `test_sub_mas_test_runner.py` | 70 | sub_mas-test-runner recipe validity |

**92 missing tests** to reach the 80% threshold. See §5 for the
migration plan.

---

## 3. Operator Override (escape hatch)

For emergency pushes where the operator has explicitly assessed that
shipping without full coverage is acceptable (e.g. a critical
security fix, a docs-only change), the gate can be bypassed:

```bash
MAS_SKIP_TEST_COVERAGE_GATE=1 goose run --recipe mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml
```

**Rules for use of the escape hatch:**

- **Operator-initiated only.** Never auto-skip. The validator MUST be
  invoked with the env var set explicitly by a human or by an
  authenticated CI workflow, never silently.
- **Documented justification required.** The push commit message MUST
  reference this policy and explain why the gate was bypassed.
- **Logged in evidence.** The `.state/pre-push-test-coverage.json`
  file is still written, even when the gate is bypassed, so the
  bypass is auditable after the fact.
- **One bypass per push at most.** Never combine a coverage-gate
  bypass with other gate bypasses (e.g. Check 10, Check 11) in the
  same push.

---

## 4. Why 80% (not 100%)?

A 100% requirement (test_count == sub_count) would force the framework
to write a regression test for every new sub-agent on the same commit
that introduces it. That creates a perverse incentive: contributors
ship the sub-agent and a weak test together, just to pass the gate.

The 80% threshold accepts that ~20% of sub-agents may rely on coverage
from sibling tests, integration tests, or the structural e2e checks
in Check 10 and Check 11. This still leaves a strong floor without
the perverse incentive.

---

## 5. Migration Plan

The 92-test gap cannot be closed in a single round. Recommended
phasing (this is a R103+ epic, not a single-commit fix):

| Phase | Round | Target | Tests to add |
|-------|-------|--------|--------------|
| 1 | R103 | 10% (12 tests) | Add 9 tests for the most-used sub-agents |
| 2 | R104-R105 | 25% (30 tests) | Add 18 tests for recovery-workflows |
| 3 | R106-R108 | 50% (60 tests) | Add 30 tests for task-workflows |
| 4 | R109+ | 80% (95 tests) | Add 35 tests for remaining surface |

**Test priorities (R103 phase 1 candidates):**

- `sub_mas-pre-push-validator` (the validator itself — dogfooding)
- `sub_mas-general-improver` (FIND→RANK→DESIGN pipeline)
- `sub_mas-health-reporter` (used every commit)
- `sub_mas-cost-tracker` (cost-control R70+R99)
- `sub_mas-test-runner` (test infrastructure)
- `sub_mas-phoenix-recovery` (5 recovery levels)
- `sub_mas-session-cleanup` (R88 cleanup rule)
- `sub_mas-config-audit` (16 config consistency checks)
- `sub_mas-prompt-review` (prompt quality)

Each new test should follow the pattern of
`test_sub_mas_test_runner.py` (recipe YAML validity + required fields
per constitution).

---

## 6. Evidence

Each pre-push run writes `.state/pre-push-test-coverage.json`:

```yaml
checked_at: <ISO-8601>
sub_agents: <int>
tests: <int>
threshold_80pct: <int>
ratio: <float>
gate_passed: <bool>
gap: <int>
```

This file is the audit trail. Health reports reference the latest
values; the `MAS_SKIP_TEST_COVERAGE_GATE` env var is recorded in
the validator's log output (search for "operator override").

---

## 7. References

- [BUG-BRIEF-2026-07-23.md](./BUG-BRIEF-2026-07-23.md) — verification
  theater root cause
- Commit `d1a40ea` (R56) — Check 11+12 introduced
- `recipe/instructions/sub_mas-pre-push-validator.md` — Check 12
  definition (line 370-422)
- R88 memory entry — "vor `git log --oneline` glauben, IMMER
  `git show <hash> -- <file>` LESEN" — keep evidence-first
