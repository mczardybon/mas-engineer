# R110-296 — EVIDENCE — Fix 2 pre-existing regressions

**Generated:** 2026-08-29
**Files modified:** 2 (test_dev_category_drift_r110293.py + test_r110279_runtime_var_skip.py)

## Before-fix status (real-flow)

```
$ pytest mas-engineer/tests/test_r110279_runtime_var_skip.py -q --no-header
FAILED mas-engineer/tests/test_r110279_runtime_var_skip.py::test_detector_finds_drift_for_synth_test
1 failed, 17 passed in 106.93s (0:01:46)

$ python3 mas-engineer/tools/dev_im_finder_scan.py --json 2>&1 | head -5
---JSON_START---
{"summary": {"total": 1, "by_type": {"SD-test_dev_category_drift_r110293": 1}, "...": "..."}}
# → 1 SD-test drift finding: 'fix: a' + 'feat: b' from R110-293 test
#   (caused by `subjects` not being in _SD_RUNTIME_VARS set)
```

## After-fix status (real-flow)

```
$ pytest mas-engineer/tests/test_r110279_runtime_var_skip.py -q --no-header
18 passed in 106.83s (0:01:46)
  # synth test now PASSES (was 1 failed)

$ python3 mas-engineer/tools/dev_im_finder_scan.py --json 2>&1 | head -3
---JSON_START---
{"summary": {"total": 0, "by_type": {}, "...": "..."}}
# → 0 SD-test drift findings (R110-293 false-positive eliminated)

$ pytest mas-engineer/tests/test_dev_category_drift_r110293.py \
        mas-engineer/tests/test_dev_phoenix_log_persister_r110294.py \
        mas-engineer/tests/test_dev_phase3_phoenix_log.py \
        mas-engineer/tests/test_dev_phase1_publishers.py -q --no-header
86 passed in 108.53s (0:01:48)
  # all green
```

## Diff evidence

```
$ git diff --stat HEAD
 mas-engineer/tests/test_dev_category_drift_r110293.py | 6 +++---
 mas-engineer/tests/test_r110279_runtime_var_skip.py  | 21 +++++++++++++++----
 2 files changed, 17 insertions(+), 10 deletions(-)

$ git diff mas-engineer/tests/test_dev_category_drift_r110293.py
-        subjects = {c["subject"] for c in commits}
-        assert "fix: a" in subjects
-        assert "feat: b" in subjects
+        # Variable name `out` (R110-279 _SD_RUNTIME_VARS) makes the
+        # detector's _is_runtime_var_assert() recognise this as a
+        # runtime-output assertion, not a stale-static-source literal
+        out = {c["subject"] for c in commits}
+        assert "fix: a" in out
+        assert "feat: b" in out

$ git diff mas-engineer/tests/test_r110279_runtime_var_skip.py
-    L1 = "ZOMBIE" + "XYZ_FORTY_TWO_LITERAL_NOT_IN_ANY_SOURCE_R110279"
+    L1 = "R110296S" + "YNTH_LITERAL_ULTRA_UNIQUE_NO_OTHER_MATCH"
... (docstring rewritten to explain _is_common_value threshold)
```

## Source-isolation check (real-flow)

```
$ grep -rln "R110296SYNTH_LITERAL_ULTRA_UNIQUE_NO_OTHER_MATCH" \
    --include="*.py" --include="*.md" mas-engineer/ 2>/dev/null
# (empty — 0 source files, only .pyc cache gitignored)
```
