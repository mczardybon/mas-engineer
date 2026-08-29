# R110-293 — EVIDENCE — dev_category_drift.py 68%→100%

**Generated:** 2026-08-29
**Test file:** `mas-engineer/tests/test_dev_category_drift_r110293.py`
**Charge 9** of R110-285+ coverage-sprint series.

## Coverage measurement (real-flow)

```
$ pytest tests/test_dev_category_drift_r110293.py \
    --cov=dev_category_drift --cov-report=term

Name                                       Stmts   Miss  Cover
--------------------------------------------------------------
mas-engineer/tools/dev_category_drift.py      80      0   100%
--------------------------------------------------------------
TOTAL                                         80      0   100%
48 passed in 0.34s
```

## Test breakdown (N=48)

| Group                       | Count | Highlights                                        |
|-----------------------------|-------|---------------------------------------------------|
| Constants & structure       | 6     | 12 types, 4 emojis, default cutoff 2026-08-04      |
| CONVENTIONAL_COMMIT_RE      | 6     | R110-259 mirror: all-12 +with-scope +rejects     |
| run_git_log                 | 3     | 2-commit-list, CalledProcessError, mock malformed  |
| classify_drift              | 15    | 6 paths + mixed + cutoff precedence + noise rules |
| format_human                | 5     | empty/drift/exempt/<unset>/hash-shortened-to-8    |
| main (CLI)                  | 12    | exit-codes 0/1/2 + --json + runpy __main__ exec    |
| **Total**                   | **48**| **100% in 0.34s**                                 |

## Pitfalls discovered + fixed during dev

1. **wip: stuff NOT exempt** — `NON_PROTOCOL_NOISE` is an exact-match
   check (lowercased), not a startswith. Only bare `wip` / `tmp` /
   `draft` (any case) are exempt. Updated tests accordingly.

2. **`main()` takes 0 args** — it reads `sys.argv` directly. Tests
   use `monkeypatch.setattr(sys, "argv", [...])` instead of
   `main(["--flag"])`.

3. **runpy.run_module needed for `if __name__ == "__main__":`
   coverage** — just calling `dcd.main()` doesn't execute the
   guard. `runpy.run_module("dev_category_drift", run_name="__main__")`
   does.

4. **Malformed-line filtering** — patches `subprocess.run` to
   return a fake stdout with 4 lines (1 well-formed, 1 blank,
   1 no-separator, 1 only-2-parts) and asserts only the well-formed
   one survives.

5. **GIT_COMMITTER_DATE** must be passed via `env` dict, NOT as a
   shell-prefix on the subprocess.run call (initial test had a
   syntax-error from trying to do both).

## Refs

- R110-292 (f1a824b) — charge 8
- R110-291 (cae8420) — charge 7
- R110-259 (regex spec gap fix)
- R110-258 (parenthesized scope gap detector)
- R110-130 (wrench: legacy removal)
- R110-94 (initial category-drift detector)
