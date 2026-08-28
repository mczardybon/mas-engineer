# R110-273 — by_type status-filtered fields (8 tests)

## Summary

Adds status-filtered type-count fields to `dev_issue_db._compute_summary()`:
`by_type_open`, `by_type_fixed`, `by_type_wontfix`, `by_type_false_positive`.
The legacy `by_type` field is unchanged (still counts ALL issues by type)
for backward compatibility with any existing dashboard / consumer.

R110-271 noticed `by_type` was misleading (e.g. showed A2=3 when only
1 A2 was actually open). The new `by_type_open` field is what dashboards
should use for "currently broken by type" views.

## Files changed (2)

| File | +/− | Purpose |
|---|---|---|
| `tools/dev_issue_db.py` | +17/−0 | Added 4 status-filtered by_type fields in `_compute_summary()` |
| `tests/test_dev_issue_db_summary_by_type.py` | +220/−0 | NEW: 8 unit tests |

## New fields in summary dict

```python
{
  "by_type":               {"A2": 4, "Q4c": 3, ...},  # all (legacy, unchanged)
  "by_type_open":          {"A2": 1, "Q4c": 1, ...},  # only status=open
  "by_type_fixed":         {"A2": 1, ...},             # only status=fixed
  "by_type_wontfix":       {"Q4c": 2, ...},            # only status=wontfix
  "by_type_false_positive":{"NN1": 1, ...},            # only status=false_positive
}
```

The 4 new fields are always present (empty dict `{}` if no issues
match), so consumers can do `summary["by_type_open"].get("A2", 0)`
without `KeyError`.

## Tests (8, all passing in 0.24s)

1. `test_compute_summary_empty_db_has_empty_type_dicts` — empty db: all 5 dicts are `{}`
2. `test_compute_summary_by_type_open_only_counts_open` — by_type_open excludes fixed
3. `test_compute_summary_by_type_fixed_only_counts_fixed` — by_type_fixed excludes open
4. `test_compute_summary_by_type_wontfix` — by_type_wontfix excludes open
5. `test_compute_summary_by_type_false_positive` — by_type_false_positive excludes open
6. `test_compute_summary_legacy_by_type_counts_all` — legacy by_type still counts all
7. `test_compute_summary_by_status_totals_unchanged` — by_status + total_issues unchanged
8. `test_compute_summary_mixed_status_independence` — same type in 3 status dicts is independent

## Verification (R110-174 body-claim)

- 2 files changed: +237 (git diff --stat to verify on commit)
- 8 new tests pass in 0.24s (pytest)
- Pre-flight 92/92 tests pass in 16.33s (5 test files: summary_by_type,
  mark_fixed_cli, dev_im_finder_scan_lib, dev_dispatch_tracker_mq_integration,
  sub_mas_pre_push_validator)
- 0 regressions (legacy by_type unchanged; existing 84 tests still pass)
- Backward compat: any consumer reading `summary["by_type"]` still gets
  the same mixed-status dict

## Pitfalls (read me if you touch this code)

1. **No removal of legacy by_type**: intentionally kept for backward
   compat. Dashboards should migrate to `by_type_open` for "currently
   broken" views. Don't remove the legacy field until you've grep'd
   the codebase for `.by_type` consumers.

2. **Empty dict vs missing key**: the 4 new fields are always
   present even if no issues match (empty `{}`). This avoids
   `KeyError` in consumers. If you do `summary["by_type_open"]["A2"]`
   for an empty db, you get `KeyError: 'A2'`, NOT a missing-key
   error on `by_type_open` itself. Use `.get("A2", 0)` if unsure.

3. **Stats on the real db**: the live `issue_db.json` has 79 open
   issues, but `by_type` showed counts of 3+ for many types because
   HARDCODE-STALE-001..006 (20 issues) are status=fixed and were
   inflating the legacy by_type. After R110-273, by_type_open shows
   the actual open counts (A2=3, Q4c=3, JJ1=2, NN3=2, etc.).

4. **JSON schema**: the new fields are part of `summary` (a transient
   computed field), not `issues`. They're recomputed on every
   `IssueDB.load()` from the current state. No migration needed.

5. **Python 3.7+ dict ordering**: the 4 new dicts are in the order
   they appear in the code (open, fixed, wontfix, false_positive).
   This is deterministic in Python 3.7+, so tests can rely on it.

## Open follow-ups (R110-274+)

- Migrate dashboard to use `by_type_open` instead of `by_type`
  (search for `by_type` in `dashboard-data-refresh.yaml` etc.)
- DB-cleanup: 20 HARDCODE-STALE-* issues in `fixed` status are R110-270
  dedupes and look correct (file+type+status match), but the type-name
  is unusual. Consider renaming to a friendlier schema.
- NN1: 19 (orchestrator design-philosophy) — R110-274 dedup-helper
- mark-false-positive CLI surface (Python API exists, no CLI yet)

## Files

  M tools/dev_issue_db.py                            |  17 +
  A tests/test_dev_issue_db_summary_by_type.py       | 220 ++++++++
  2 files changed, 237 insertions(+), 0 deletions(-)

Refs: R110-174, R110-177, R110-270, R110-271, R110-272
