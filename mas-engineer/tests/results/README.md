# tests/results/

Reproducible evidence files for body-claim verification.

## What this dir is

When a commit body claims a number ("11/11 passed", "1528 passed/16
skipped/0 failed", "3x consecutive flake-suite clean", "10/10 key
phrases grep-treffer"), the corresponding command output lives here as
a `.txt` file. This is the **evidence** for the body claim, frozen
in git.

Standard defined by R110-172 directive:
`.mase/directives/R110-172-evidence-files-standard.md`

## Why not just rerun the test?

Two reasons:
1. **Speed.**  `pytest -n 4 tests/` takes 4 minutes. If 100 commits
   each have a 4-minute verification, that's ~7 hours per clone.
   Reading 14-line pytest output files takes seconds.
2. **Honesty.**  If a body claim drifts from reality (e.g. R110-126's
   "10/10 key phrases" was case-sensitive-false, only 5/10 exact),
   the diff between today's evidence file and the original body
   makes the drift visible. Without the file, the drift hides.

## When to add a file

ANY commit whose body makes a quantitative claim:
- pytest results (passed/failed counts, durations)
- grep results (key-phrase counts, file-existence claims)
- secret-scan results
- audit-history / log / state-file existence claims
- timing claims (e.g. "test X runs in <2s")

Pure refactor / docs commits without numbers do NOT need evidence.

## Layout standard

```
tests/results/
  README.md                                  ← this file
  R<NR>-<short-topic>/                       ← one dir per commit
    01-<claim-1>.txt
    02-<claim-2>.txt
    ...
    NN-<claim-N>.txt
```

Each `.txt` file MUST have:
- Header: `=== R<NR>-<something> EVIDENCE ===` + date + commit-sha
- The verbatim command
- The output (full or relevant tail)
- A `Conclusion:` line stating which body claim is proven

## Current contents

| Dir | Commit | What it proves |
|---|---|---|
| `r110-171-flake-fix/` | 3ba2bfd | R110-171 body claims: 14/14 flake-suite 3x + 1528/16/0 full suite + 1544 collect-only + phantom test-names + secret-scan |
| `r110-126-mq-pattern/` | 42cda98 | R110-126 body claims: 11/11 phase3+4 regression + 10/10 key-phrases sections (with case-sensitivity correction) |

## R110-172 lesson: R110-126's "10/10 key phrases" was imprecise

The R110-126 body said "10/10 key phrases grep-treffer". Strict
case-sensitive grep finds only 5/10. The 10 themes ARE all in the
section bodies (case-insensitive), and the section headers exist
(`## MQ-CONSUMER TEST PATTERN` + `## CROSS-TOPIC AUTO-ESCALATION`),
so the directive's actual goal was achieved — but the body phrasing
was misleading.

This is recorded in
`r110-126-mq-pattern/02-key-phrases-grep-10-10.txt` so future
readers see the exact grep output, not a hand-wave. Future commits
should use the **theme-form** ("10/10 themes anchored in section
bodies, section headers confirmed") instead of **grep-form** when
the user-facing meaning is the themes.
