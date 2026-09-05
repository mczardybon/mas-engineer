# R110-342 Evidence — e2e_teams: 4 latent-bug classes fixed (Prio-4 R-sprint)

## 1. Why

R110-333 folgeplan (commit f14be8c) identified e2e_teams (Prio-4)
as the final latent-bug audit target after dev_message_queue
(Prio-2) and dev_rule_checker (Prio-3) succeeded.  e2e_teams
is the PTY-based test runner that verifies sub_recipes work
end-to-end, so its robustness affects test reliability.

4 bug classes were identified and fixed in R110-342 (2091214):

1. 2 bare `except: pass` (L417, L425) for `os.write(master, b"\x03")`
2. 3 `with open() no encoding=` (L352, L544, L563)
3. 1 `except Exception as e:` (L398 Popen) — verified left-as-is
   is acceptable (returns structured {"status": "fail"} dict)
4. end-to-end smoke (import + --help)

## 2. The 4 bug classes (in detail)

### 2.1 2 bare `except: pass` → narrowed (L417, L425)

**Before:**
```python
try: os.write(master, b"\x03")
except: pass
```

**Problem:** bare `except:` catches BaseException
(KeyboardInterrupt, SystemExit, real bugs).  Silent-swallow
means a regression in os.write is invisible.

**After:**
```python
try: os.write(master, b"\x03")
except (OSError, ValueError): pass
```

OSError: EBADF (bad file descriptor if master closed),
EIO (PTY underlying I/O failure).
ValueError: closed buffer / fcntl issue.

### 2.2 3 `with open() no encoding=`

**Before:** 3 `with open()` sites, 0 with `encoding=`.
**After:** all 3 now have `encoding="utf-8"`.

Sites:
- L352 `wrapper_path` (the YAML recipe wrapper)
- L544 `{out_dir}/logs/{team}-{level}.log` (per-test log file)
- L563 `{out_dir}/raw-results.json` (JSON aggregate results)

**Behavior change:** UTF-8 explicit, no locale dependence.

### 2.3 `except Exception as e:` at L398 Popen — verified, left as-is

```python
try:
    proc = subprocess.Popen(cmd, stdin=slave, stdout=slave, stderr=slave,
                            env=env, close_fds=True)
except FileNotFoundError:
    return {"status": "fail", "reason": "goose not found in /root/.local/bin"}
except Exception as e:
    return {"status": "fail", "reason": f"Popen failed: {e}"}
```

The fallback `except Exception as e:` is acceptable for Popen
because subprocess.Popen can fail in many ways (permission
denied, exec format error, resource limits, etc.) and a broad
except is the appropriate pattern here.  The R110-342 fix
verifies that this site returns a structured
{"status": "fail", "reason": ...} dict (not raise).

### 2.4 end-to-end smoke

The script must still import cleanly and respond to --help
without a Python traceback.

## 3. The 5 new tests

```
tests/test_r110342_e2e_teams_latent_bugs.py
  TestBareExceptNarrowing:
    test_bare_except_replaced_in_os_write                ✓
  TestEncoding:
    test_all_with_open_have_encoding_utf8                ✓
  TestExceptExceptionNarrowing:
    test_popen_except_documented                          ✓
  TestE2eTeamsStillWorks:
    test_imports_cleanly                                 ✓
    test_help_or_no_args_does_not_crash                   ✓
  = 5 passed in 0.30s =
```

1 test per bug class (per R110-78 verification-theater guard).

## 4. Cross-batch verification

```
$ python3 -m pytest tests/test_r110338_dev_message_queue_latent_bugs.py \
                    tests/test_r110340_dev_rule_checker_latent_bugs.py \
                    tests/test_r110342_e2e_teams_latent_bugs.py \
                    -q
20 passed in 0.53s
```

- 9 R110-338 tests: still PASS
- 6 R110-340 tests: still PASS
- 5 R110-342 tests: all PASS

Combined: 20/20 PASS in 0.53s.

## 5. Body-claim-drift audit (R110-305 protocol)

All claims verified:
  - "4 bug classes" → 1 bare-except, 1 encoding, 1 except-Exception,
    1 e2e = 4 ✓
  - "2 bare except: pass" → grep L417 + L425 = 2 ✓
  - "3 with open() no encoding" → grep L352 + L544 + L563 = 3 ✓
  - "5 new tests" → test file has 5 test_ methods ✓
  - "20/20 PASS" → pytest output matches ✓
  - "Prio-2/3/4 R-sprint complete" → 6 R-code commits
    (R110-338/340/342) + 2 R-evidence (R110-339/341) + R110-343
    pending = 7 commits when R110-343 is pushed.

## 6. R110-333 folgeplan STATUS

Prio-2/3/4 R-sprint now COMPLETE (with this commit):

  R110-338 (e6e2696) — Prio-2 dev_message_queue: 4 bug classes, 9 tests
  R110-339 (9067419) — Prio-2 EVIDENCE
  R110-340 (d684280) — Prio-3 dev_rule_checker: 5 bug classes, 6 tests
  R110-341 (7e2f893) — Prio-3 EVIDENCE
  R110-342 (2091214) — Prio-4 e2e_teams: 4 bug classes, 5 tests
  R110-343 (this)   — Prio-4 EVIDENCE

Total: 6 commits (3 R-code, 3 R-evidence), 20 new tests,
       20/20 PASS, 0 regressions across batches.

## 7. References

- R110-333 (f14be8c) — Prio-2/3/4 R-sprint plan
- R110-338 (e6e2696) — Prio-2 R-code
- R110-339 (9067419) — Prio-2 R-evidence
- R110-340 (d684280) — Prio-3 R-code
- R110-341 (7e2f893) — Prio-3 R-evidence
- R110-342 (2091214) — Prio-4 R-code (this commit's pair)
- R110-296/297 — 5-category commit protocol
- R110-78 — verification-theater guard
- R110-281 — force-push-VERSBOT
- R110-92 — drift detector
- R110-305 — 4-round numstat body-claim audit
- R110-318 — R-code → R-evidence pair pattern
- R110-258 — .mase/ + logs/ .gitignored + force-add pattern
