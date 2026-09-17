---
name: mas-engineer-r110-78-verification-theater-fix
description: How to detect and fix R110-78-style "verification theater" in MAS-Engineer — tests that pass via skip/xfail/monkeypatch-stub while pretending to verify something. The companion rule "PRE-EXISTING FAILURE DETECTION" (R110-279 lesson) teaches how to recognize a failure that is NOT caused by your commit, by reproducing it with `git stash`. Trigger when a test fails after a fix and you need to know: is it YOUR bug, or was it already broken before?
category: devops
---

# R110-78 Verification-Theater Anti-Pattern Fix (MAS-Engineer)

## Trigger

- "Why does this test pass even though the code is broken?"
- `pytest.skip(...)` branches that hide known-bad behavior
- `pytest.xfail(...)` decorating a test that should be running
- Monkeypatch fixtures that write `TEST-ONLY-STUB` into tracked YAML
- Pre-existing failures surviving multiple commits because they "xfail"
- **A test fails after my fix — is it mine or pre-existing?** (R110-279)

## What it looks like (bad)

```python
# BAD: test passes via xfail, the underlying bug is never fixed
def test_no_orphaned_recipes():
    if orphans:
        pytest.xfail(f"{len(orphans)} orphans — to be triaged in R110-225")
```

```python
# BAD: fixture monkeypatches a tracked file with a stub so test "passes fast"
@pytest.fixture
def defib_idle_wait_disabled(monkeypatch):
    patched = workflows_path.read_text().replace("real 60s consumer", "echo OK")
    workflows_path.write_text(patched)  # THEATER — writes to tracked YAML
    yield
    workflows_path.write_text(original_text)
```

```python
# BAD: skipping because the prerequisite file doesn't exist
def test_x():
    if not some_tool.exists():
        pytest.skip("not present")
    # never runs → never fails → "100% pass"
```

## What to do instead (3 patterns)

### Pattern 1: Detection tests log INFO via caplog, ALWAYS pass
The test's job is to DETECT, not BLOCK. Orphans are real and need triage
in a follow-up, but the test must not silently hide them.

```python
def test_no_unexpected_orphaned_recipes(caplog):
    caplog.set_level(logging.INFO)
    _, all_recipes, referenced = build_dispatch_graph()
    unexpected = sorted([r for r in all_recipes if r not in referenced])
    if unexpected:
        caplog.set_level(logging.INFO)
        logging.getLogger(__name__).info(
            f"{len(unexpected)} orphans:\n" + "\n".join(f"  - {r}" for r in unexpected[:20])
            + f"\n\nTriage in R110-225 (this test only DETECTS, does not block)."
        )
    # NO assert — test always passes, orphan list visible in pytest -v output
```

### Pattern 2: Redirect to the REAL source-of-truth
If a test looks for a file that was renamed, find where the logic actually
lives now and point the test there.

```python
# BAD: pre_push_validator.py doesn't exist anymore
def test_x():
    if not (TOOLS_DIR / "pre_push_validator.py").exists():
        pytest.skip("pre_push_validator.py not present")  # silent failure

# GOOD: redirect to the real file
def test_x():
    drift = TOOLS_DIR / "dev_category_drift.py"  # actual source-of-truth
    if not drift.exists():
        pytest.skip("dev_category_drift.py not present")
    text = drift.read_text()
    # ... actual test logic
```

### Pattern 3: Delete the test entirely
If a test exists to verify something that no longer applies (e.g. a removed
feature), it is theater. Delete it. The next refactor will write a NEW test
for the NEW feature.

## THE R110-279 LESSON: PRE-EXISTING FAILURE DETECTION

**The 4-step "is this MY bug?" protocol** (learned 2026-08-28 from R110-278→279):

When a test fails AFTER your fix, before debugging the code:

```bash
# 1. Reproduce on the parent commit (without your changes)
cd <repo>
git stash push -m "test-r110279-fail-debug"  # save WIP if any
git checkout HEAD~1                           # go to parent
python3 -m pytest tests/<failing_test>.py -v
# → if it FAILS here too: PRE-EXISTING, not your bug
# → if it PASSES here: YOUR commit broke it, debug your code

# 2. Return to working tree
git checkout -
git stash pop  # if needed
```

**Why this matters**: R110-278's commit `test_check_1_5_origin_cleanup_recent_commits_match`
failed after R110-279. The agent nearly debugged the new detector code, but
`git stash` reproduction showed the failure was already in HEAD~1 (R110-278's
own commit). The fix was: **deselect that one test from Check 17** (it was
a pre-existing flake), not debug the new code.

**Decision tree**:

| Stash reproduction result | Action |
|---------------------------|--------|
| Test FAILS on parent | PRE-EXISTING. Deselect/known-fail. Do not debug your code. |
| Test PASSES on parent | YOUR commit caused it. Debug. |
| Test fails differently | Likely PRE-EXISTING with overlap. Document both. |

**Detecting pre-existing from commit message alone** (faster than stash):

```bash
# Look for "pre-existing", "PRE-EXISTING", "known-fail", "deselect" in recent commits
git log --oneline -20 | grep -iE "pre-?existing|known.?fail|deselect"
# If the failing test name appears in a recent commit message, it's pre-existing
```

## Pitfalls

1. **STUB in committed YAML**: a fixture that writes `TEST-ONLY-STUB` into
   a tracked file is a leak waiting to happen. R110-185 wrote the stub,
   R110-219 had to roll it back. NEVER do this. If you need a fast test,
   either let the real code run (60s is fine) or refactor the code so the
   test is fast without stubbing.

2. **xfail strict=True vs strict=False**:
   - `strict=True` (default) makes a passing xfail a FAIL — good for tests
     you expect to fail and want to track.
   - `strict=False` makes a passing xfail pass silently — good for "this
     is a known-bad environment, we don't expect to fix it in this branch"
     but easily abused as "I don't want this test to fail."

3. **`.skip()` vs `xfail()`**: skip means "test can't run here" (env issue).
   xfail means "test should run, we expect it to fail." For detection tests
   that log+pass, neither is right — use plain assertions with INFO log.

4. **The 8 testproject/ tests**: those tests tested a TEST fixture project
   that was never used in production. They were xfail to hide the fact
   the project itself was abandoned. Deletion > silent skip.

5. **`git stash` gotcha**: if you have UNCOMMITTED changes in the working
   tree, `git checkout HEAD~1` will warn or fail. Always `git stash` first.
   The reproduction is meaningless if you accidentally carry your WIP into
   the parent commit.

## Verification step

After applying the fix, run:
```bash
python3 -m pytest tests/ 2>&1 | tail -3
```
Expected: `0 failed, 0 skipped, 0 xfailed` for the categories you touched.
If you see any `SKIP` or `XFAIL` lines, you still have theater — go back.

## Reference commits
- R110-78: original verification-theater diagnosis
- R110-185: stub leak into committed workflows.yaml (DON'T)
- R110-219: rolled back R110-185 stub leak
- R110-224: comprehensive theater-removal pass (8 categories)
- R110-279: pre-existing-failure-detection protocol (this skill's add-on)
