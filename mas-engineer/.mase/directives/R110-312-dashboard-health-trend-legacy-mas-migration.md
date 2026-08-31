# R110-312 — dashboard health_trend legacy 'mas' key migration

## Problem

`tests/test_dashboard_data_schema.py::test_health_trend_entries_have_time_score`
fails at HEAD with:
  AssertionError: assert 'score' in {'time': '22:44', 'mas': 0}

`generate_data()` returns health_trend entries from
`.mase/dashboards/history.json`. The current code (line 333) appends
`{'time': ..., 'score': mas_health}` but the on-disk history.json
contains 13 entries with the legacy `mas` key (from a pre-R110-149
era, before R110-149 schema was enforced). The migration was never
written; test was added in R110-149 but the data was already
in legacy shape.

## Fix (single-file + single-test)

- M tools/dev_dashboard_data.py (+7 lines): on history.json load,
  migrate `{'time': X, 'mas': Y}` → `{'time': X, 'score': Y}` for
  any entry that has 'mas' but not 'score'. The migration is
  in-memory only — the on-disk history.json is left as-is (avoids
  rewriting 26 entries during a dashboard run). The next 'score'
  append will keep the file in forward-only 'score' shape.
- M tests/test_dashboard_data_schema.py (+43 lines, R110-312
  regression test): builds a tmp_path workspace with a legacy-shape
  history.json and asserts `generate_data()` migrates correctly.

## Why migrate-on-load instead of rewrite-on-disk

- Lower blast radius: no fs side effects, no race with concurrent
  dashboard readers
- Forward-only: each new append uses 'score', so the file
  naturally becomes pure-'score' over time
- Test isolation: the regression test uses tmp_path and does not
  touch the real .mase/dashboards/history.json
- Matches mas-engineer convention: history files are append-only
  (build_size, health_trend, mq/*.ndjson all use this pattern)

## E2E (real-flow, 1 scenario)

  1. pytest tests/test_dashboard_data_schema.py -v → 39/39 pass
     (was 38/38 + 1 fail; now 39/39 + 0 fail)
  2. generate_data(REPO_ROOT) inline: all 24 entries have 'score'
     (was 11/24 with 'score', 13/24 with 'mas')
  3. data.json + history.json write still happens via script-run
     test (test_dev_dashboard_data_script_runs)

## Coverage

No new files added. The migration is in dev_dashboard_data.py
which was already 41% tracked in R110-310 (subprocess-tracked).
Net coverage delta: ~0% (1 line new + 1 line lost in the pop()).
R110-310's 80/80 tools tracking still holds.

## Lessons learned

1. **Schema-drift in append-only history files is real**: history.json
   keeps entries from every past run. A schema rename in code
   without migration on read = silent test failure years later.
2. **migrate-on-load > rewrite-on-disk**: avoids fs side effects,
   no race with concurrent readers, test isolation is trivial.
3. **R110-149 / R110-161 audit pattern**: any 'pop or migrate?'
   decision should default to in-memory. Persistent rewrites of
   history files belong in a separate one-time migration tool,
   not in a read-path.
4. **history.json is gitignored** (R110-308 .gitignore fix).
   The pre-R110-149 'mas' entries are local-only; this fix
   applies per-clone.

## Related

- R110-149: dashboard data flow + schema (introduced the test
  that catches this bug)
- R110-161: dev_dashboard_data: surface MQ aggregate as `mq.*` keys
  (added 'mq' top-level but missed the 'mas'→'score' migration)
- R110-310: coverage 30.57% → 45.44% (parallel scope)
