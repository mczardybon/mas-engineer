# R110-95 — Re-measure pytest timing 5x and re-set the 8.12s spec value

**Status:** DRAFT (2026-08-04)
**Author:** Hermes (R110-89 Finding F follow-up)
**Target:** `mas-engineer/recipe/instructions/sub_mas-pre-push-validator.md`
(Check 17 spec value: 8.12s)

## Goal

Replace the single-point `8.12s` spec value in Check 17 with a
**statistically-grounded range** based on 5x measurements, to make
the validator's pytest-block more robust to environmental variance.

## Why

- R110-89 evidence-doc Finding F: "Re-measure pytest timing 5x and
  re-set the 8.12s spec value to median ± range (currently 7.46s
  to 8.12s observed)."
- The 8.12s figure was a single measurement from R110-71 era. Recent
  measurements (2026-08-04, R110-100 acceptance test) show 9.57s and
  9.64s — variance is real and not negligible.
- Check 17 is the gatekeeper; if we hardcode `8.12s` as a warning
  threshold, real runs at 9.6s would falsely trigger WARN or BLOCK
  on a non-failure condition.
- The spec value should be `median ± 2*sigma` or similar statistical
  range, not a single point.

## Scope

1. Run `python3 -m pytest tests/ -q --tb=line` 5x back-to-back.
2. Record each duration from the pytest summary line.
3. Compute median, mean, std-dev, min, max.
4. Update the Check 17 spec section in
   `mas-engineer/recipe/instructions/sub_mas-pre-push-validator.md`
   with the new range.
5. Add a timing-table to the evidence-doc.

## 9-Section Spec

### 1. EXACT FILE + INSERT-POINT

`mas-engineer/recipe/instructions/sub_mas-pre-push-validator.md`
- The Check 17 spec output block currently says:
    `✅ Check 17 passed: $PASSED passed, ... in ${DURATION}s`
- After this directive, the spec's *example output* should be
  updated to show the measured median value, not a hardcoded 8.12s.

### 2. EXTRACT-PATTERN

From each `pytest -q --tb=line` run, extract:
  `===== 1277 passed in N.NNs =====`
where N.NN is the duration. Regex: `in ([0-9]+\.[0-9]+)s`.

### 3. MATCHING

5x consecutive runs in a single shell session:
  ```bash
  for i in 1 2 3 4 5; do
    python3 -m pytest tests/ -q --tb=line 2>&1 | grep -oE "in [0-9.]+s" | head -1
  done
  ```
Capture output to `R110-95-timing.txt`.

### 4. OUTPUT-SCHEMA

Timing table (example, 5x measurements):
  Run 1: 9.57s
  Run 2: 9.64s
  Run 3: 9.41s
  Run 4: 9.52s
  Run 5: 9.69s
  ---
  Median: 9.57s
  Mean:   9.566s
  Std:    0.103s
  Min:    9.41s
  Max:    9.69s
  Range:  0.28s (9.41s - 9.69s)
  2-sigma: 0.21s → safe range 9.36s - 9.78s

Updated spec example:
  `✅ Check 17 passed: 1277 passed, 0 failed, 0 errors, 0 skipped
   in ~9.5s (median 9.57s, observed range 9.41-9.69s)`

### 5. 3-HOOK-POINTS

Pre-measurement:
  - `cd <mas-engineer-cwd>`
  - `source mas-engineer/.env` (load DEEPSEEK_API_KEY — even though
    not used, sets context)
  - No-op dependencies (pytest is stdlib-installed)

During-measurement:
  - 5x back-to-back runs (no pauses)
  - Same shell session (avoid env drift)
  - Capture only the duration line, discard rest

Post-measurement:
  - Compute statistics
  - Update Check 17 spec with new range
  - Add timing-table to `R110-95-PYTEST-TIMING-EVIDENCE.md`

### 6. SEVERITY

LOW. Cosmetic spec update. Check 17 doesn't BLOCK based on duration
— only on failed/errors. The duration value is documentation-only.

### 7. IDEMPOTENZ

Fully idempotent. Re-running the 5x measurement produces new
statistics (slightly different). The spec-range-update is a
human-judged call (use median ± range, not mean).

### 8. TESTING

1. 5x runs produce 5 valid duration values
2. Median is within min-max (sanity check)
3. Std-dev is positive (variance exists)
4. Updated spec reflects the measured range
5. Pre-push-validator still passes after spec-update

### 9. DO-NOT (anti-patterns)

- **DO NOT** use `mean` as the spec value — use `median` (more
  robust to outliers).
- **DO NOT** include system-load-dependent times (e.g. during a
  parallel CI job). Run 5x in isolation.
- **DO NOT** make Check 17 BLOCK on duration. Duration is
  documentation; failed/errors are the gate.
- **DO NOT** remove the 8.12s reference entirely — keep it as
  historical context (R110-71 era) in the Provenance section.
- **DO NOT** add the timing-table to the recipe-yaml (it's spec
  evidence, not validator config).

## Provenance

- R110-89 evidence-doc Finding F (R110-95 — re-measure timing).
- R110-100 acceptance (2026-08-04): 9.57s and 9.64s observed.
- R110-71 era: 8.12s single-measurement (now historical).

## Acceptance criteria

- [ ] 5x pytest timing measurements recorded in `R110-95-timing.txt`
- [ ] Median, mean, std-dev, min, max computed
- [ ] Check 17 spec output-block updated with measured range
- [ ] Evidence-doc `R110-95-PYTEST-TIMING-EVIDENCE.md` created
- [ ] Historical 8.12s value preserved as reference
- [ ] Pre-push-validator: all 17 checks still PASS
- [ ] Commit body cites: 5x measurements, statistics, file-update
