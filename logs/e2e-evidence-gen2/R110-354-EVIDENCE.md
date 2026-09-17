# R110-353 Evidence — workspace coverage-push round 2 (Prio-2)

## 1. Why

R110-323+ coverage-push queue, Prio-2 (workspace).
R110-353 continues the workspace push after R110-351 brought
the testable surface from 0% to 16%.

## 2. R110-353 (1295413) — Round 2: interactive + agent-generation

### 2.1 Strategy
Target the interactive _ask_* functions and the agent
generation logic.  All take user input via `input()` which
is mockable via `monkeypatch.setattr(builtins, "input", ...)`.

### 2.2 5 helper groups targeted, 28 tests, 5 test classes

**TestAskType (5 tests)** — covers `_ask_type` (L762-783).
Branches:

  - choice "1" → ('mas_sub', 'mas-engineer/recipe/sub/', 'agent_template.yaml')
  - choice "2" → ('fw_specialist', 'framework/recipes/specialists/', None)
  - choice "3" → ('fw_sub', 'framework/recipes/sub/', None)
  - invalid input "5" → loops, second valid input accepted
  - EOFError → (None, None, None)

All 5 PASS.

**TestAskName (8 tests)** — covers `_ask_name` (L788-820).
Branches:

  - valid name for each of 3 types (3 tests)
  - uppercase normalized to lowercase
  - spaces replaced with dashes
  - empty name → loops
  - invalid name (underscore) → loops
  - EOFError → None

All 8 PASS.

**TestAskDescription (5 tests)** — covers `_ask_description`
(L814-833).  Branches:

  - valid desc + emoji
  - empty desc → name-derived fallback (R110-324-BUG-A fix)
  - empty emoji → defaults to '🤖'
  - whitespace-only desc → name fallback
  - EOFError → (None, None)

All 5 PASS.

**TestGenerateAgent (7 tests)** — covers `_generate_agent`
(L836-940).  Branches:

  - mas_sub → file in mas-engineer/recipe/sub/
  - fw_specialist → file in framework/recipes/specialists/
  - fw_sub → file in framework/recipes/sub/
  - existing file + 'j' → overwrites
  - existing file + 'n' → returns None (skip)
  - generated YAML is parseable
  - special chars (quotes) in description don't break YAML
    (R110-324-BUG-B regression test)

All 7 PASS.

**TestAskNamePrintsHint (3 tests)** — verifies hint text per
agent_type.  Branches:

  - mas_sub hint mentions 'sub_mas-'
  - fw_specialist hint shows '.yaml' without sub_ prefix
  - fw_sub hint mentions 'sub_' prefix

All 3 PASS.

### 2.3 Result

| Metric | R0 | R1 | R2 |
|---|---|---|---|
| Lines covered | 0 / 595 | 95 / 595 | 187 / 595 |
| Coverage % | 0% | 16% | 31% |
| Tests | 0 | 25 | 53 |
| Tests runtime | n/a | 0.19s | 0.97s |

## 3. Cross-batch regression

```
$ python3 -m pytest tests/test_r110351_workspace_coverage_push_r1.py \
                    tests/test_r110353_workspace_coverage_push_r2.py \
                    --cov=dev_workspace --cov-report=term
53 passed in 0.97s
TOTAL                      595    408    31%
```

- 25 prior R110-351 tests: still PASS
- 28 new R110-353 tests: all PASS
- Coverage report: 31% (was 16%)

## 4. Honest assessment

Round 2 is +15pp on 595 testable stmts.  workspace is
the LARGEST pure-helper surface in the queue.  Round 3
can target cmd_project_* functions (L1064-1242, ~178
lines) + cmd_init's YAML-generating branches (L79-126,
47 lines).  Expected yield: 31% → 50% in round 3.

## 5. Body-claim-drift audit (R110-305 protocol)

All claims verified:
  - "28 new tests" → 28 test_ methods: ✓
  - "5 test classes" → 5 Test* classes: ✓
  - "16% → 31% (+15pp)" → coverage report: ✓
  - "53/53 PASS in 0.97s" → pytest output: ✓
  - "187/595 stmts covered" → coverage report: ✓
  - "R110-324-BUG-B regression test" → test included: ✓

## 6. R110-323+ queue status

Prio-1 (im_finder_scan, 1660 lines): DONE
  - 25% → 30% (+5pp, 34 lines newly covered)
Prio-2 (workspace, 1478 lines): IN PROGRESS
  - R1 (R110-351): 0% → 16% (+16pp) ✓
  - R2 (R110-353): 16% → 31% (+15pp) ✓
  - R3: 31% → 50% (targeted cmd_project_*, cmd_init)
Prio-3 (template_gen, 901 lines): queued
Prio-4 (dashboard, 566 lines): queued

## 7. References

- R110-322 (f4f8b3a) — coverage pattern documentation
- R110-323 — coverage-push queue
- R110-333 (f14be8c) — Prio-2/3/4 R-sprint plan
- R110-345/346/347/348/349/350 — Prio-1 im_finder_scan
- R110-351 (6ece410) — workspace round 1
- R110-352 (2160da2) — R110-351 EVIDENCE
- R110-266/269/300/309/324 — prior workspace tests
- R110-324 (existing) — workspace bug fixes
  (R110-324-BUG-A, BUG-B tested here)
- R110-296/297 — 5-category commit protocol
- R110-78 — verification-theater guard
- R110-281 — force-push-VERSBOT
- R110-92 — drift detector
- R110-305 — 4-round numstat body-claim audit
- R110-258 — .mase/ + logs/ .gitignored + force-add pattern
- R110-318 — R-code → R-evidence pair pattern
