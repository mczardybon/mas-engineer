# R110-272 — mark-fixed CLI for dev_issue_db (8 tests)

## Summary

Restores the `mark-fixed` CLI surface for the issue-db. R110-271 had to
use `mark-wontfix` as a workaround for fixed issues (because the
`mark_fixed` Python method existed but no CLI subcommand was wired
up), which polluted the wontfix stats. R110-272 closes the tooling
gap with a proper CLI + 8 unit tests.

## Files changed (2)

| File | +/− | Purpose |
|---|---|---|
| `tools/dev_issue_db.py` | +25/−1 | `mark-fixed` subparser + handler |
| `tests/test_dev_issue_db_mark_fixed_cli.py` | +176/−0 | NEW: 8 unit tests |

## CLI surface

```bash
python3 tools/dev_issue_db.py mark-fixed <hash> \
    --commit-sha <sha> \
    [--validated-by <agent-name>]
```

- `hash` (positional): full sha256:hex of the issue
- `--commit-sha` (required): commit SHA that fixed the issue
- `--validated-by` (default: `im-validator`): agent name
- Exit 0 on success, prints `mark-fixed changed=True/False`
- Exit 1 if `--commit-sha` is empty
- Idempotent: marking an already-fixed issue returns changed=False,
  does NOT append a duplicate past_validation_outcomes entry

## Tests (8, all passing in 0.21s)

1. `test_mark_fixed_open_to_fixed` — basic transition
2. `test_mark_fixed_already_fixed_returns_false` — idempotency
3. `test_mark_fixed_unknown_hash_returns_false` — graceful no-op
4. `test_mark_fixed_validated_by_override` — custom validator name
5. `test_cli_mark_fixed_basic` — CLI subprocess integration
6. `test_cli_mark_fixed_empty_commit_sha_rejected` — error path
7. `test_cli_mark_fixed_validated_by_flag` — CLI flag roundtrip
8. `test_cli_mark_fixed_help_shows_arguments` — argparse self-doc

## Verification (R110-174 body-claim)

- 2 files changed: +201/-1  (git diff --stat VERIFIED)
- 8 new tests pass in 0.21s (pytest)
- Pre-flight 84/84 tests pass in 15.02s (4 test files: mark_fixed,
  dev_im_finder_scan_lib, dev_dispatch_tracker_mq_integration,
  sub_mas_pre_push_validator)
- 0 regressions (existing 76 tests still pass)
- mark_fixed() is unchanged in this commit (only CLI surface added)

## Pitfalls (read me if you touch this code)

1. **DB is in-memory after register**: `_register_sample_issue` writes
   the issue to JSON directly, then `IssueDB(str(path))` reads it. If
   you swap the order (IssueDB first, then write), the new write is
   NOT in IssueDB's `_data` because IssueDB loads once on `__init__`.
   Test fixture order is critical.

2. **No mark-fixed batch mode**: this CLI handles one hash at a time.
   For bulk-fixed issues, loop in shell or write a `--from-csv` mode
   later. R110-271 closed 6 issues with 6 separate CLI calls; that
   was acceptable but won't scale to R110-273+ where 50+ fixes are
   expected.

3. **--commit-sha is required**: even if you want to mark something
   fixed without a known commit (e.g. legacy issues), you must pass
   a placeholder like `--commit-sha LEGACY`. The CLI does NOT accept
   empty string; the regex in `_now_iso()`-validation is stricter
   than `--reason` for `mark-wontfix`. This is intentional — fixed
   without a traceable commit is a documentation gap.

4. **stats-command bug NOT fixed in R110-272**: `by_type` still
   counts all issues by type, not just open. Left for R110-273 to
   avoid scope creep. If you call `stats` and see A2=3 (when only
   1 A2 is actually open), filter on `status='open'` client-side
   or use `list-open --type A2`.

5. **--validated-by is recorded verbatim**: no normalization. If you
   pass `R110-272-test` and another tool passes `R110-272-Test`,
   they show as different validators in past_validation_outcomes.
   Use lowercase, hyphen-separated names only.

## Open follow-ups (R110-273+)

- Stats `by_type` filter on status
- Bulk-mark-fixed (--from-csv or --from-bulk-import)
- Fix the 6 issues closed in R110-271 that were marked wontfix
  with "fixed" reason: convert them to proper `fixed` status
  with `mark-fixed --commit-sha 879b02b` (this commit's SHA).
  This is a 1-line DB-cleanup, not a code change.
- Add `mark-false-positive` CLI (the `false_positive` status is
  already supported in the Python API, but no CLI surface yet).

## Files

  M tools/dev_issue_db.py                             |  25 ++++-
  A tests/test_dev_issue_db_mark_fixed_cli.py         | 176 +++++++++
  2 files changed, 201 insertions(+), 1 deletion(-)

Refs: R110-174, R110-177, R110-270, R110-271
