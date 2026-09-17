# R110-191 — im-finder `findings_top` key-mismatch + C-batch MQ hardening wrap-up

## Context

R110-189 follow-up reveal: running `python3 -m pytest tests/ -q` after pulling
the latest mas-mq HEAD exposed **2 pre-existing failures** in
`tests/test_dev_phase1_publishers.py::test_publish_im_finder_findings` /
`test_publish_im_finder_findings_with_filter`:

```
KeyError: 'location'
  at tools/dev_im_finder_scan.py:1278 in `findings_top` builder
```

The im-finder scanner (R110-165) was authored against the **consument spec**
(`dev_im_design_patches.py:59` documents `{type, severity, location, description}`)
but the actual finding dicts (built by the 15 detector-functions above) use
`{type, severity, file, issue}`. The bug shipped in R110-165 (commit `266ceb7`,
2026-08-16) and was **invisible for 2 days** because the 2 affected tests are
in the **MQ topic**, not the default `tests/` collection order that most
local runs cover.

Same diagnostic session also exposed that R110-189-C (defects 6,7,8,9,12,13
from the directive) had been **written into the working tree by the
general-improver but never committed**. 6 new MQ tests + MQ hardening code
sat in the working tree, all green, but invisible to `git log`.

## Goal

1. Fix the `findings_top` builder to ship the real keys + legacy aliases.
2. Wrap R110-189-C into the same commit (one consistent MQ-hardening
   phase 2 finalisation; Check 20 in the pre-push-validator already covers
   all 15 defects so no new check needed).

## Root-cause analysis

```
File: tools/dev_im_finder_scan.py:1278 (R110-165 266ceb7 2026-08-16)
Author intent:  findings carry (type, severity, location, description) per
                consumer doc dev_im_design_patches.py:59
Actual finding dicts (lines 70-1180, 15 detectors):
                {type, severity, file, issue}
```

Decision: ship BOTH keys (real + legacy aliases). Reasons:
- Forward-compatible: any future consumer reading `file`/`issue` gets them
  directly.
- Backward-compatible: existing `dev_im_design_patches.py` keeps working.
- Lowest-risk: no consumer code change needed; no schema migration.
- Aligns producer output with the actual finding-shape reality, so we
  stop pretending the docs are right and start documenting the truth.

## Changes

### tools/dev_im_finder_scan.py:1278

```diff
-        'findings_top': [
-            {k: f[k] for k in ('type', 'severity', 'location', 'description')}
-            for f in findings
-            if f.get('severity') in ('high', 'blocker')
-        ][:20],
+        # only ship the high+medium findings inline; low-severity are counted but not listed
+        # (R110-191 fix: real finding keys are 'file'/'issue', not 'location'/'description' —
+        #  ship both so consumers using either spec work; pre-existing since R110-165 266ceb7)
+        'findings_top': [
+            {k: f[k] for k in ('type', 'severity', 'file', 'issue')
+             if k in f} | {'location': f['file'], 'description': f['issue']}
+            for f in findings
+            if f.get('severity') in ('high', 'blocker')
+        ][:20],
```

### R110-189-C wrap-up (working tree → commit)

Defects shipped (all covered by pre-push Check 20):

| R-id | Type | File | Status |
|------|------|------|--------|
| R-189-6 | A3-EXT retry-with-backoff | tools/dev_message_queue.py | applied |
| R-189-7 | A3 jitter (R110-189-7) | tools/dev_message_queue.py | applied |
| R-189-8 | A3-EXT circuit-breaker | tools/dev_message_queue.py | applied |
| R-189-9 | A3 idempotency-key | tools/dev_message_queue.py | applied |
| R-189-12 | L1 cap MAS_MQ_MAX_DEPTH_PER_TOPIC | tools/dev_message_queue.py | applied |
| R-189-13 | X1 DLQ error-class classifier | tools/dev_message_queue.py | applied |

+ 6 new pytest tests in `tests/test_dev_message_queue.py` for each defect.
+ Pre-push-validator Check 20 covers all 15 F-MQ-189-* markers (verified
  15/15 hits in current tree, 2026-08-18).

## Verification

- `python3 -m pytest tests/ -q --timeout=300` → **1600 passed, 16 skipped, 129s**
- `python3 -m pytest tests/test_dev_phase1_publishers.py -q` → 7/7 PASS
  (previously 2 FAILED with KeyError: 'location')
- `python3 -m pytest tests/test_dev_message_queue.py -v` → 43/43 PASS
  (37 base + 6 new C-batch tests)
- Check 20 (MQ markers): 15/15 ✓

## Not in this commit (R110-192 separate)

- The **issue-db backfill** of R-201..R-211 as `status=fixed` entries.
  That is a R110-192 directive (issue-db reconciliation) and is its own
  commit. Reason: scope separation — the im_finder fix is a code fix
  on a specific file, the backfill is issue-db bookkeeping across 10 patches.
