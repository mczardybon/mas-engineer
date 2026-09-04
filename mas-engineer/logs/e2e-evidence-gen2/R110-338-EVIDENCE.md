# R110-338 Evidence — dev_message_queue: 4 latent-bug fixes (Prio-2 R-sprint)

## 1. Why

R110-333 folgeplan (commit f14be8c) identified 9 latent-bug
candidates after the R110-320/322/327/328/330/332/334 sprint
brought `dev_dashboard_data` and `dev_registry_merge` to 100%
coverage.  Prio-2 was `dev_message_queue` (the most-used
production-critical module: handles all inter-agent signal
routing in the MQ ecosystem).

4 bug classes were identified and fixed in R110-338 (e6e2696):

1. `int(os.environ.get(name, str(default)))` crash (2 sites)
2. Bare `except Exception:` silent-swallow in `_find_msg`
3. 17 `open()` without `encoding=` (locale-dependent crashes)
4. `_dlq_count()` file-iter bug (unclosed file + ResourceWarning)

## 2. The 4 fixes (in detail)

### 2.1 `_getenv_int(name, default)` helper (NEW, 24 lines)

**Before** (2 sites):
```python
_idempotency_index = _IdempotencyIndex(
    max_size=int(os.environ.get("MAS_MQ_IDEMPOTENCY_MAX", "100000")))
# ...
max_depth = int(os.environ.get("MAS_MQ_MAX_DEPTH_PER_TOPIC", "100000"))
```

**Problem:** if a user sets `MAS_MQ_IDEMPOTENCY_MAX=banana` in
their shell, the module import crashes with ValueError at the
`int(...)` call.  The `_idempotency_index` is built at module
load, so the entire `import dev_message_queue` fails.

**After:**
```python
def _getenv_int(name: str, default: int) -> int:
    """Read an env var as int, falling back to `default` on any parse
    failure (missing, empty, non-numeric, overflow).  Logs a warning
    so silent misconfigurations are visible."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except (ValueError, TypeError) as e:
        print(
            f"⚠️ {name}={raw!r} not an int, using default {default} "
            f"({type(e).__name__}: {e})",
            file=sys.stderr,
        )
        return default
```

**Behavior change:** bad input → soft warning + default, instead
of hard crash.  Operators see a warning, not a stack trace.

### 2.2 Bare `except Exception:` in `_find_msg` (L429)

**Before:**
```python
try:
    with _TopicLock(topic):
        msgs = _read_topic(topic)
        for i, m in enumerate(msgs):
            if m.get("msg_id") == msg_id:
                return topic, (i, m, msgs)
except Exception:
    continue
```

**Problem:** `except Exception:` catches KeyboardInterrupt and
SystemExit in Python 2 (well, it doesn't catch KeyboardInterrupt
but it does catch all real bugs).  In Python 3, KeyboardInterrupt
is NOT a subclass of Exception, so it's not caught.  BUT real
bugs in `_read_topic` (e.g. a TypeError from a code regression)
would be silently swallowed — the whole `_find_msg` would just
return None and the caller has no idea there's a bug.

**After:**
```python
except (FileNotFoundError, OSError, ValueError) as e:
    # FileNotFoundError: topic file deleted between glob and open
    # OSError: lock-acquire / read IO failure
    # ValueError: malformed NDJSON (from _migrate on corrupted header)
    print(
        f"⚠️ _find_msg skipping topic {topic!r}: "
        f"{type(e).__name__}: {e}",
        file=sys.stderr,
    )
    continue
```

**Behavior change:** only the 3 expected exception classes are
caught.  Real bugs in `_read_topic` / `_TopicLock` now propagate
to the caller as unhandled exceptions (visible in logs/tests).

### 2.3 17 `open()` calls without `encoding=`

**Before:** `open(path)` — uses locale default encoding.
**After:** `open(path, ..., encoding="utf-8")` — explicit UTF-8.

Sites changed:
  - L279 `_TopicLock.__enter__`: open(self.path, "w")
  - L302 `_log_dlq_error`: open(qpath, "a")
  - L315 `_read_topic`: open(path)
  - L338 `_write_topic_atomic`: open(tmp, "w")
  - L392 `_log_dlq_error_in_enqueue`: open(_dlq_path(), "a")
  - L495 `ack`: open(comp_path, "a")
  - L547 retry-exhaustion DLQ: open(_dlq_path(), "a")
  - L556 max_retries DLQ: open(_dlq_path(), "a")
  - L582 `_read_completed`: open(path)
  - L598 `_write_completed_atomic`: open(tmp, "w")
  - L611 `_stats_load_or_init`: open(p)
  - L627 `_stats_save`: open(tmp, "w")
  - L794 `_list_ndjson_files`: open(ndjson)
  - L852 `_read_archive`: open(p)
  - L944 TTL-expired DLQ: open(_dlq_path(), "a")
  - L987 `_archive_dump`: open(archive, "w")
  - L991 `_archive_dump`: open(p, "w")

**Behavior change:** all NDJSON reads/writes are now guaranteed
UTF-8 (the module's `json.dumps(ensure_ascii=False)` outputs
already require UTF-8 on read).  Non-ASCII topics like
`tëst_测试` work on Windows / non-UTF-8 locales.

### 2.4 `_dlq_count()` file-iter bug (L842)

**Before:**
```python
def _dlq_count() -> int:
    p = _dlq_path()
    if not p.exists():
        return 0
    return sum(1 for _ in open(p))
```

**Problem:** `open(p)` returns a file object.  Iterating a file
object yields lines (one per `\n`), so the count is correct for
newline-terminated text files.  BUT the file is never explicitly
closed → triggers `ResourceWarning: unclosed file <...>` on
every call.  The file is closed when the generator is GC'd, but
GC timing is non-deterministic.

**After:**
```python
def _dlq_count() -> int:
    p = _dlq_path()
    if not p.exists():
        return 0
    return len(p.read_text(encoding="utf-8").splitlines())
```

**Behavior change:** read + splitlines is the canonical pattern.
File is closed atomically by `read_text()`.  No ResourceWarning.
Encoding is explicit UTF-8 (matches the write side).

## 3. The 9 new tests

```
tests/test_r110338_dev_message_queue_latent_bugs.py
  TestEnvIntHelper:
    test_valid_int_passes_through                       ✓
    test_missing_env_returns_default                    ✓
    test_non_numeric_falls_back_to_default_with_warning ✓
    test_idempotency_max_crash_regression               ✓
  TestFindMsgExceptionNarrowing:
    test_corrupted_topic_skipped_with_warning           ✓
    test_keyboard_interrupt_propagates                  ✓
  TestNDJSONEncoding:
    test_enqueue_with_unicode_topic_succeeds            ✓
    test_topic_path_uses_utf8_encoding                  ✓
  TestDLQCount:
    test_dlq_count_returns_line_count                   ✓
  = 9 passed in 0.09s =
```

Each test maps 1:1 to a specific bug class:
  - 4 tests for `_getenv_int` (valid/missing/non-numeric/regression)
  - 2 tests for `_find_msg` (corrupted-topic-skip + propagation)
  - 2 tests for `open()` encoding (unicode-topic + utf-8-bytes)
  - 1 test for `_dlq_count` (correct count + no ResourceWarning)

## 4. Verification

```
$ python3 -m pytest mas-engineer/tests/ -k "mq or message_queue or dev_message" -q
139 passed, 2944 deselected in 84.31s (0:01:24)
```

- 130 existing MQ tests: still PASS (no regression)
- 9 new R110-338 tests: all PASS
- Combined: 139/139 PASS in 84.31s
- Total change: +309 lines (89 in dev_message_queue.py + 242 test file)
  but -22 lines (the redundant code from bugs #1, #2, #4)

```
$ python3 tools/dev_category_drift.py --since 30
Category-drift report (last 30 days, 232 commits scanned):
  conform: 228
  exempt:  3
  DRIFT:   1
  DRIFT commits: d56ec64 (R110-321, the pre-existing one)
```

R110-338 is CONFORM. d56ec64 drift unchanged (still ages out
on 2026-10-04 per R110-281 force-push-VERSBOT).

## 5. Body-claim-drift audit (R110-305 protocol)

All claims verified:
  - "4 latent-bug classes" → 1 _getenv_int, 1 bare-except, 1
    encoding, 1 _dlq_count = 4 ✓
  - "17 open() without encoding=" → grep -c = 17 ✓
  - "9 new tests" → test file has 9 test_ methods ✓
  - "139 passed" → pytest output matches ✓
  - "drift = 1" → dev_category_drift.py output matches ✓
  - "4 sites of int(os.environ.get(...))" → grep shows 2 sites
    in code (the helper itself has 1 reference; the new helper
    also uses int(raw) which is wrapped in try/except).  So
    actually 2 PATTERN-sites fixed, not 4.  The 2-claim is
    correct.
  - "5-category protocol" → title is 🔧 CONFORM ✓

## 6. References

- R110-333 (f14be8c) — Prio-2 R-sprint plan
- R110-338 (e6e2696) — this commit's paired R-code
- R110-296/297 — 5-category commit protocol
- R110-78 — verification-theater guard
- R110-281 — force-push-VERSBOT
- R110-92 — drift detector (CONFORM confirmed)
- R110-94 — validator (Check 1.5 + Check 16+)
- R110-305 — 4-round numstat body-claim audit
- R110-94 — Check 16+ still BLOCKS on d56ec64 (pre-existing
  unfixable drift; will age out 2026-10-04)
- R110-258 — .mase/ + logs/ .gitignored + force-add pattern
- R110-316/318/319/327/329/335 — R-code → R-evidence pair
  pattern (R110-338/339 follow this)
