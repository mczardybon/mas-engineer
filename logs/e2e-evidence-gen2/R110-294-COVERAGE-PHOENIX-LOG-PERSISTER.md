# R110-294 — EVIDENCE — dev_phoenix_log_persister.py 69%→100% (FINAL charge)

**Generated:** 2026-08-29
**Test file:** `mas-engineer/tests/test_dev_phoenix_log_persister_r110294.py`
**Charge 10 (FINAL)** of R110-285+ coverage-sprint series.

## Coverage measurement (real-flow)

```
$ pytest tests/test_dev_phoenix_log_persister_r110294.py \
    --cov=dev_phoenix_log_persister --cov-report=term

Name                                                 Stmts   Miss  Cover
--------------------------------------------------------------------------
mas-engineer/tools/dev_phoenix_log_persister.py          61      0   100%
--------------------------------------------------------------------------
TOTAL                                                   61      0   100%
25 passed in 0.23s
```

## Test breakdown (N=25)

| Group                 | Count | Highlights                                            |
|-----------------------|-------|-------------------------------------------------------|
| TestLogDir            | 3     | env-override, default REPO_ROOT, mkdir idempotency     |
| TestClassify          | 4     | ok, degraded, unknown, levels_passed>total edge-case   |
| TestDigestLevels      | 6     | empty, ok-true/false, missing-ok, non-dict-error, order |
| TestProcessMsg        | 10    | happy, degraded+escalate, mock-MQ, fail-keep-log,     |
|                       |       | missing-fields, unicode, idempotent-overwrite          |
| TestMainGuard         | 2     | stdin→stdout via runpy + empty-stdin-defaults          |
| **Total**             | **25**| **100% in 0.23s**                                     |

## Pitfalls discovered + fixed during dev

1. **monkeypatch REPO_ROOT alone insufficient** — module caches
   `DEFAULT_LOG_DIR` at import time → must monkeypatch both.
2. **`if __name__ == "__main__":` does NOT call sys.exit()** —
   use `runpy.run_module(...)` without `pytest.raises(SystemExit)`.
3. **import dev_message_queue is INSIDE process_msg()** — not
   at module top — so test environment can mock without full MQ.
4. **Escalation payload shape** (R110-169) has nested
   `summary.degraded_levels` derived from `_digest_levels()` ok-false.
5. **`ensure_ascii=False` in BOTH writes** (R110-270) — original
   + re-write after escalation.
6. **`log_dir` outside `REPO_ROOT`** → `relative_to()` ValueError
   → fall back to `str(log_path)` (absolute path).

## Refs

- R110-293 (5576556) — charge 9
- R110-292 (f1a824b) — charge 8
- R110-291 (cae8420) — charge 7
- R110-168 (phase 3 phoenix-log persister)
- R110-169 (phase 4 auto-escalation contract)
- R110-270 (ensure_ascii=False for unicode)
