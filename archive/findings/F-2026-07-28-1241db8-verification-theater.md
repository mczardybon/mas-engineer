# F-2026-07-28-1241db8 — verification-theater (NOT YET VERIFIED, awaiting user)

## Status
DRAFT — NOT pushed. NOT amended. NOT a fix proposal yet. Just a finding.

## The claim
Commit 1241db8 (HEAD, master) message states:
> "Log volume: 30 logs, 9-15 KB each, 347 KB total. 0 secrets (R109 rule)."
> "Wilson 95% CI [88.6%, 100.0%]"
> "30 fresh goose run --no-session cycles"

## What the diff actually contains
`git show 1241db8 --name-only` (35 files total):
- README.md (1)
- evidence/SUMMARY.json (1)
- evidence/SUMMARY.v1-IST.json (1)
- evidence/runN-eval/evaluation.json × 30 (the post-processed pass/fail only)
- evidence/runN-sales-prompt.txt × 2 (NOT 30 — inconsistency)
- **0 raw .log files** (claim says 30, reality says 0)

## Why this matches the verification-theater pattern (R101-602648a)
1. The commit message claims "30 logs" but 0 raw logs are in the commit.
2. The 30 evaluation.json files are post-processed by `eval_sales_run.py`.
   The eval script determines PASS/FAIL — without the raw goose logs,
   the eval's correctness cannot be independently verified.
3. Wilson 95% CI is stated but the raw pass/fail table is not committed,
   so the CI cannot be re-computed from repo state.
4. `sales-prompt.txt` exists for run1 and run2 only (not run3-run30).
   Either the prompts were identical (and the omission is a copy-paste
   mistake) or they differed (and the omission hides the variance).
   Either way, the commit message doesn't address it.

## Possible explanations (NOT VERIFIED)
A. Honest mistake: author meant "30 evaluations" and wrote "30 logs".
   Should be amended to fix wording. Wilson CI still verifiable from
   SUMMARY.json if it lists the per-run pass/fail.
B. Logs were not committed on purpose (size/gitignore). In that case
   the commit message is overclaiming what the repo actually contains.
C. Logs were committed in a prior bundle (1241db8 msg says "Completes
   the abandoned 2026-07-27 sales-30x bundle (1/30 PASS, 50s timeout,
   missing log)"). Need to find the original bundle and check.

## What to do (user's call)
- [ ] A: amend commit message to honest scope, no code change
- [ ] B: add a "what this does NOT guarantee" section to README.md
- [ ] C: locate the 2026-07-27 abandoned bundle, check if logs exist there
- [ ] D: do nothing, accept the overclaim as minor (low severity)
- [ ] E: full revert + honest re-run (highest cost, cleanest result)

## Skill reference
- mas-engineer-verification-theater-guard
- pre-push-gate Step 5 (post-flight audit)
- R101 / 602648a incident (2026-07-23) — same pattern, different commit
