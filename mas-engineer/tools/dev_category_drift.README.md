# dev_category_drift.py

Standalone check for **commit-subject category drift** in the mas-engineer repo.

## What it does

Scans `git log` for the last N days and reports commits whose **subject** does not
match the 5-category commit-protocol:

- `chore:`  -- housekeeping, refactors, renames
- `docs:`   -- documentation only
- `fix:`    -- bug fixes
- `wrench:` -- tool/script/validator changes
- `book:`   -- test-suite additions / test infrastructure

Exempted (not flagged as drift):

- `Merge ...` -- merge commits
- `Revert ...` -- revert commits
- `[auto]`, `[bot]`, `[MAS-ENGINEER] test commit`, `'test'` -- auto/test commits
- Anything before `--convention-since` (default: 2026-08-04, day after R110-90
  rebase that established the convention in practice)

## Why it exists

`sub_mas-pre-push-validator` (Check 1.5) already validates the **latest commit's
subject** at push time. This script is the **historical-drift counterpart**:

- It scans ALL commits in a window, not just the latest one.
- It surfaces commits that violate the convention but were pushed before the
  validator was tightened, so a maintainer can see the historical drift and
  decide whether to rebase (R110-90 established the rebase-and-normalize pattern).

## Usage

```bash
# Default: scan last 30 days, post-2026-08-04 enforcement window
python3 tools/dev_category_drift.py

# Last 7 days
python3 tools/dev_category_drift.py --since 7

# JSON output (for CI / cron integration)
python3 tools/dev_category_drift.py --json

# Scan a different repo
python3 tools/dev_category_drift.py --path /path/to/other/repo

# Show historical drift (since formal protocol introduction 2026-07-27)
python3 tools/dev_category_drift.py --convention-since 2026-07-27
```

## Exit codes

- 0 = no drift (all scanned commits conform or are exempt)
- 1 = drift found (one or more commits violate the protocol)
- 2 = usage error (e.g. `--since 0`, git log failed)

The non-zero exit on drift makes it suitable for:

- pre-push-validator as an optional future Check 16+ (tighten from "latest only" to "last N")
- CI gates (block merges if drift > 0 in the relevant window)
- Cron alerts (notify on weekly drift scan)

## When to run

| Trigger                 | Command                              | Why                                |
|-------------------------|--------------------------------------|------------------------------------|
| Before opening a PR     | `--since 7`                          | Catch your own recent drift        |
| Weekly maintainer review| `--since 7 --json`                   | Trend over time                    |
| Pre-release sweep       | `--since 30`                         | Catch drift from new contributors  |
| Historical audit        | `--convention-since 2026-07-27`      | See the full pre-enforcement history |

## Provenance

Created as R110-92 follow-up, after the R110-90 rebase proved that 11 of 11
historical commits could be normalized to the 5-category convention. The script
is the standalone detector that surfaces such drift without needing to attempt
a push.

## Related

- `mas-engineer-commit-protocol` (skill) -- the 5-category rules
- `sub_mas-pre-push-validator` (recipe) -- the push-time gate (Check 1.5)
- `R110-90` (commit `2bdac8b`) -- the precedent rebase
- `R110-78-spec-drift` (directive) -- the spec-drift lesson (different domain)
