# Sales-30x E2E — COMPLETE / V3 (final)

**Status:** COMPLETE — 30/30 runs PASS, 100.0% success rate
**Wilson 95% CI:** [88.6%, 100.0%]
**Total wall-clock:** 15 min 30 s (22:11:50 → 22:27:00, R109 rerun)
**Method:** `python3 run_30x_sales.py --n 30 --start 1 --timeout 600 --per-run-sleep 3`
**Model:** DeepSeek-V4 (deepseek-chat via api.deepseek.com)
**Date:** 2026-07-27 (rerun 2026-07-27 22:10–22:27)

## 1. Result

| metric | value |
|---|---|
| runs attempted | 30 |
| runs PASS | 30 |
| runs FAIL | 0 |
| runs ERROR | 0 |
| success rate | 100.0% |
| Wilson 95% CI lower | 88.6% |
| Wilson 95% CI upper | 100.0% |
| per-run wall time (min) | 18.0 s |
| per-run wall time (max) | 31.7 s |
| per-run wall time (avg) | 26.0 s |
| log file size (min) | 9 309 B |
| log file size (max) | 14 945 B |
| log file size (avg) | 11 857 B |
| total log volume | 355 730 B |
| secrets in logs (R109 rule) | 0 |

**All 5 hard-criteria passed for every run (30/30):**
- H1_files: 5/5 required files present
- H2_subcount: 5 sub-recipes per team
- H3_yaml: all YAML valid
- H4_subrecipes: all 4 referenced sub-recipes resolve
- H5_gate: mandatory gate enforced

## 2. Per-run table

| run | status | time (s) | log size (B) |
|---:|:---:|---:|---:|
|  1 | PASS | 31.7 | 14 945 |
|  2 | PASS | 26.0 | 12 537 |
|  3 | PASS | 22.3 |  9 695 |
|  4 | PASS | 23.8 | 10 331 |
|  5 | PASS | 26.7 | 12 685 |
|  6 | PASS | 25.7 | 10 602 |
|  7 | PASS | 31.4 | 12 391 |
|  8 | PASS | 26.3 | 10 354 |
|  9 | PASS | 31.6 | 13 071 |
| 10 | PASS | 25.7 | 12 176 |
| 11 | PASS | 25.3 | 10 484 |
| 12 | PASS | 26.7 | 11 475 |
| 13 | PASS | 23.7 | 10 576 |
| 14 | PASS | 28.3 | 12 549 |
| 15 | PASS | 24.6 | 12 331 |
| 16 | PASS | 27.5 | 12 943 |
| 17 | PASS | 28.1 | 11 439 |
| 18 | PASS | 28.8 | 13 478 |
| 19 | PASS | 18.0 |  9 309 |
| 20 | PASS | 23.7 | 11 443 |
| 21 | PASS | 28.1 | 12 936 |
| 22 | PASS | 26.7 | 14 446 |
| 23 | PASS | 24.5 | 11 920 |
| 24 | PASS | 23.4 | 10 630 |
| 25 | PASS | 22.7 | 11 095 |
| 26 | PASS | 23.0 | 10 728 |
| 27 | PASS | 24.6 | 10 967 |
| 28 | PASS | 29.5 | 13 101 |
| 29 | PASS | 28.1 | 12 817 |
| 30 | PASS | 22.9 | 12 276 |

(Time and log_size values from `evidence/SUMMARY.json`, the canonical
orchestrator output. All 5 hard-checks H1–H5 PASS for every run; per-run
detail in `evidence/run<N>-eval/evaluation.json`.)

## 3. Comparison with same-day control

| test | n | PASS | rate | Wilson 95% CI | per-run time | date |
|---|---:|---:|---:|---|---:|---|
| **sales-30x (this)** | 30 | 30 | 100% | [88.6%, 100.0%] | 19–30 s | 2026-07-27 22:10 |
| demo-team-15x | 15 | 15 | 100% | [79.6%, 100.0%] | 104–215 s | 2026-07-27 12:04 |

Both test the same MAS-engineer framework with the same model. Both
achieved 100% PASS. Sales-30x has tighter CI due to n=30 (vs n=15), and
per-run time is shorter because the sales team is a simpler 5-sub-recipe
structure (vs the more complex demo teams in the 15x test).

## 4. What this folder now contains (after R109 rerun)

```
e2e-results/2026-07-27-sales-30x/
├── .env                             218B   (redacted keys, clean)
├── eval_sales_run.py              6.8KB    (eval, hard+soft criteria)
├── run_30x_sales.sh               3.4KB    (shell, timeout=600s)
├── run_30x_sales.py               9.7KB    (python, default timeout=600s)
├── prompt.txt                     1.5KB    (sales-team generation prompt)
├── README.md                      this file (V3, final)
├── __pycache__/                  .gitignored
└── evidence/
    ├── SUMMARY.json                (V2: 30/30 PASS, 22:27:00)
    ├── SUMMARY.v1-IST.json         (V1: 1/1, 0/1 PASS, 50s timeout — pre-rerun state, preserved)
    ├── run1-sales-build.log … run30-sales-build.log
    ├── run1-eval/evaluation.json … run30-eval/evaluation.json
    └── run1-sales-prompt.txt, run2-sales-prompt.txt
        (reference copy of prompt.txt for run 1 + 2; sales uses the
         same prompt for all 30 runs by design)
```

## 5. What happened before this rerun (history, V1)

Pre-rerun this folder held an abandoned single-run attempt (R109
"verification theater" detection). The state at 2026-07-27 22:10 was:

- 1/30 runs attempted (run #1 only, 0/1 PASS)
- failure mode: `"timeout after 50s"` (source of 50s unknown — neither
  committed script uses 50s; default is 600s in `run_30x_sales.sh` line
  62 and `run_30x_sales.py` argparse default)
- log file `run1-sales-build.log` was never written (or removed before
  the b28244b commit)
- `evidence/SUMMARY.json` contained only the hand-entered 1/30 failure
- folder name "sales-30x" implied a 30x result that did not exist
- no README, no per-run table, no Wilson-CI

The pre-rerun SUMMARY.json is preserved at
`evidence/SUMMARY.v1-IST.json` for audit purposes. The README V1
("INCOMPLETE — 1/30 runs attempted, 0/1 PASS") documented this state
before the R109 rerun.

## 6. R109 work timeline

```
2026-07-27 22:10:08   R109 forensics: file-listing + secret-scan + timeline
2026-07-27 22:10:42   README V1 written (IST-zustand dokumentation)
2026-07-27 22:11:00   dry-run N=2 — both PASS (script works, 24-26s/run)
2026-07-27 22:11:50   full 30x run START
2026-07-27 22:27:00   full 30x run END — 30/30 PASS, Wilson [88.6%, 100.0%]
2026-07-27 22:28:00   README V3 written (this file, final)
```

## 7. Pointer to control comparison

`../2026-07-27-demo-team-15x/README.md` — 15/15 PASS, Wilson 95% CI
[79.6%, 100.0%], 3 teams × 5 runs, full per-run table.
