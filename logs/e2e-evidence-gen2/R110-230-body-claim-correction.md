# R110-230 body-claim correction (R110-231 evidence)

## R110-230 body-claim audit

| Claim in R110-230 body                                  | Real (git show --stat) | Match |
|---------------------------------------------------------|------------------------|-------|
| `M .mase/workflows.yaml (3 f, +7/-3: ...)`             | 1 file, 8+, 2-         | NO    |
| `+ docs/CHANGELOG-2026-08-21-r110-225-229.md (130 lines)` | 146 lines (new)        | NO    |
| `2 files changed, 154 insertions(+), 2 deletions(-)`    | 2 f, 154+, 2-          | YES   |

## Why this happened
- "3 f" was from mind — 3 different replacements (task, desc, task_workflows)
  counted as 3 file changes. But they were 1 file with 3 logical changes.
- "+7/-3" was approximation from reading the diff without counting.
- "130 lines" was the size BEFORE post-hoc e2e section addition.
  Post-fix, CHANGELOG grew to 146 lines.

## R110-174 source-of-truth
- `git show --stat` is the SOLE source of line/file counts.
- Mind-derived numbers MUST be replaced with stat-derived numbers.
- R110-174 added "body-claim-verification" skill for this.

## Skill update
- mas-engineer-commit-protocol updated with R110-225..230 lessons.
- Pitfall 1: copy EXACT line from `git show --stat` into body.
  No paraphrase, no round, no +1/-1.
