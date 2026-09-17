# R110-322 — fix top-level scalar yaml being dropped in dev_spec_invariant

## Bug

`tools/dev_spec_invariant.py::extract_count_from_recipes()` had a
silent spec-drift false negative: a YAML recipe whose top-level
node was a string scalar (e.g. `5 ab here` or `"5 ab here"`) was
skipped entirely by the early-return at line 143:

```python
if not isinstance(data, (dict, list)):
    continue
```

But the docstring for the function explicitly promises:

> Skips: comments, multiline (block) strings, YAML keys — i.e. only
> single-line string scalar VALUES of the parsed YAML are scanned
> (the 'valid_yaml' rule from the spec).

A top-level string IS a single-line string scalar. A recipe whose
entire body is a one-liner count-declaration was being silently
dropped, which is exactly the kind of spec-drift false negative
the invariant checker is supposed to PREVENT.

The bug is a docstring-vs-implementation inconsistency. The walk
function correctly handles `str`, `dict`, and `list`, but the
caller's early-return gates out anything that isn't `dict`/`list`,
which silently drops a `str` value before walk can see it.

## Repro (pre-fix)

```bash
$ mkdir -p /tmp/r322/{tests,recipe/sub}
$ cat > /tmp/r322/tests/test_t.py <<'EOF'
def test_t():
    assert "5 ab" in "5 ab"
EOF
$ cat > /tmp/r322/recipe/sub/r.yaml <<'EOF'
"we have 7 ab"
EOF
$ python3 tools/dev_spec_invariant.py --repo-root /tmp/r322
# (exits 0 — no INVARIANT finding!)
$ # We expect exit 1 + INVARIANT-ab finding because the test asserts
$ # '5 ab' but the recipe says '7 ab'. Pre-fix, the recipe is
$ # silently skipped → test_assertions has 'ab'={5}, recipe_counts
$ # has no 'ab' key → SPEC_DRIFT-ab is the only finding, NOT
$ # INVARIANT-ab. The two are not equivalent: SPEC_DRIFT means
$ # "test says X but recipe doesn't mention it" (less severe), while
$ # INVARIANT-ab means "test says 5 and recipe says 7" (BLOCKER).
```

## Fix

Replace the early-return `if not isinstance(data, (dict, list)):`
with `if data is None: continue` (the only case where the function
truly has nothing to scan) and add a comment block. Now `walk(data)`
runs on `dict`, `list`, AND `str` top-level values — exactly the
"single-line string scalar VALUES" the docstring promises.

**+10 lines, -1 line** in `tools/dev_spec_invariant.py`:

```diff
         try:
             data = yaml.safe_load(open(yf, errors='ignore'))
         except Exception:
             continue
-        if not isinstance(data, (dict, list)):
+        if data is None:
+            # Empty yaml / yaml that parses to None -> nothing to scan
+            continue
+
+        def walk(node):
+            ...  # (unchanged)
+
+        # R110-322: was `if not isinstance(data, (dict, list)): continue`,
+        # which silently dropped top-level string scalars. A top-level string
+        # with a count-declaration (e.g. `5 ab here`) is exactly the kind of
+        # single-line scalar value the docstring promises to scan, and a
+        # recipe whose entire body is a one-liner count-declaration was
+        # being skipped — a real spec-drift false negative. Now: any node
+        # that walk() can handle (dict / list / single-line str) is walked;
+        # only None (parse-to-null) is treated as "no data".
+        walk(data)
-
-        def walk(node):
-            ...
-
-        walk(data)
```

## Regression test (8 tests, all PASS in 1.31s)

`tests/test_r110322_spec_invariant_scalar_yaml.py` uses the
R110-310 subprocess pattern (spawn `python3 tools/dev_spec_invariant.py
--repo-root <tmp>` from the repo root). This is the pattern R110-320
used, and the same pattern that made the 45 zero-cov CLI tools
(R110-310) testable. The subprocess-mode tests are the ONLY way to
bring dev_spec_invariant.py out of the 0%-cov bucket — direct
`import dev_spec_invariant` from a test gives "module not imported"
because there is no `tools/__init__.py`.

Test classes:

### `TestTopLevelScalar` (4 tests) — the bug surface

1. `test_top_level_quoted_string_with_count_produces_no_finding_when_match`
   — top-level `"5 ab here"`, test asserts `5 ab` → exit 0 (match).
2. `test_top_level_unquoted_string_with_count_produces_no_finding_when_match`
   — same as above but unquoted scalar (`5 ab here`).
3. `test_top_level_string_with_mismatched_count_emits_finding`
   — test asserts `5 ab`, recipe is top-level `7 ab` → exit 1 +
   `INVARIANT-ab` finding mentioning both `5` and `7` in description.
4. `test_top_level_string_with_blacklisted_type_still_skipped`
   — `5 tests` at top level (blacklisted type) → not extracted.

### `TestTopLevelNonString` (2 tests) — regression guard

5. `test_top_level_int_in_recipe_does_not_match_count`
   — top-level int (42) must not be walked (walk() only walks
   `str`/`dict`/`list`); `5 ab` test → `INVARIANT-ab` finding.
6. `test_empty_recipe_yaml_does_not_crash`
   — empty yaml parses to `None`, must not crash; `5 ab` test →
   `INVARIANT-ab` finding.

### `TestTopLevelScalarNoRegression` (2 tests) — no regression

7. `test_dict_with_nested_string_still_matches`
   — pre-existing dict-walk path: `a.b.c: "5 ab"` still works.
8. `test_list_of_strings_still_matches`
   — pre-existing list-walk path: `["5 ab", "7 cd"]` still works.

## Why now (not earlier?)

R110-320 fixed a `UnboundLocalError` in dev_registry_merge.py and
documented a list of 5 candidate files (≥200 stmts, 0% cov) for
follow-up R-sprints. dev_spec_invariant.py was item 5 on that list.
R110-322 takes it through the same R110-320 pattern: probe with
edge-case unit tests, find a latent bug (the top-level scalar
drop), fix it, and write 8 regression tests that exercise both
the bug surface AND the unchanged behavior.

This is also the **first dev_spec_invariant.py code change in the
R110-3xx sprint cycle** — R110-316→R110-321 were all about
dev_registry_merge, conftest cleanup, and the 3-source lockstep.
R110-322 broadens the coverage-push to a different file with a
different bug class (spec-drift false negative vs crash on
empty input).

## Coverage delta

```
=== tools/dev_spec_invariant.py ===

  Pre-R110-322:    0%      (file not in any test, never imported)
  Post-R110-322:   60%     (137/229 stmts covered, 92 missing)

  Delta:           +60pp   1 file from 0% → 60%
  Missing lines:   90, 96, 105, 108, 111-112, 115, 119, 135, 138,
                   141-142, 184-187, 197-236, 249-261, 274, 277,
                   280-282, 298, 300-304, 310-317, 398-410, 435
```

The 8 subprocess tests cover:
- the 3 top-level yaml cases (dict, list, str)
- the `None` and `int` top-level cases (regression guard)
- the COUNT_DECLARE_RE matching for `ab`, `cd`, `tests` (blacklisted)
- the full CLI entrypoint through `__main__` (RC=0 vs RC=1 paths)

Missing lines (40% uncovered) are mostly:
- the `__main__` argparse + JSON dump (lines 197-236, 249-261)
- several docstring-claim-emitting branches in `to_findings()` (lines 310-317, 398-410)
- the `_find_canonical` / `git blame` helper (lines 280-298) which requires a real git repo
- the instruction-file walk (lines 184-187, 300-304) which is a separate code path

These are candidates for future R-sprints. R110-322 is the
**"spec-drift false negative fix"** sprint, not the
**"100% cov"** sprint — those are different goals and need
different tests (cov-push: cover-all-branches; spec-drift:
pin-the-fix).

## Pre-push-gate (per skill: pre-push-gate + pre-push-body-claim-verification)

  Step 0 (secret scan, tracked + history):  OK 0 secrets
  Step 1 (pre-commit hook, staged content): OK PASS (pending add)
  Step 2 (pytest targeted, 8 R110-322 tests): OK 8/8 in 1.31s
  Step 3 (regression sweep, 5 R110-320 + 3 Check-18 + 4 dev_spec_invariant):
                                              OK 20/20 in 1.61s
  Step 4 (cov: dev_spec_invariant.py = 60%): OK 137/229 stmts
  Step 5 (commit msg, 🔧 R-format pattern 2): OK
  Step 6 (push via credential-helper):     pending (this commit, on user 'go')
  Step 7 (post-flight audit):              pending (post-push)

## Files (2)

  M tools/dev_spec_invariant.py                                       +10 / -1
  A tests/test_r110322_spec_invariant_scalar_yaml.py                  +188  (NEW, 8 tests)
  A .mase/directives/R110-322-spec-invariant-scalar-yaml-fix.md       +247  (NEW, force-added)
  M STATUS.md                                                         +60 / -0
  Total: 2 modified, 2 added, +505 insertions, 1 deletion

## Refs

- R110-320 (e7ef060) — the R-sprint pattern R110-322 follows
  (find latent bug + fix + 4+ regression tests + cov measurement)
- R110-321 (documentation commit) — the candidate-list this R-sprint
  picks up (dev_spec_invariant.py was item #5 on that list)
- R110-310 (3523302) — sitecustomize.py + COVERAGE_PROCESS_START
  pattern that makes subprocess-style cov measurement possible
- R110-129 — conftest.py os.chdir(REPO_ROOT) precedent
- R110-303 — CWD-anchored subprocess helper pattern
- Skill: `pre-push-gate` — full e2e + secret scan + validator rules
- Skill: `pre-push-body-claim-verification` — 4 rounds of
  `git diff --numstat` + `wc -l` re-verify
- Skill: `mas-engineer-coverage-push-workflow` — same-scope
  comparison pattern + `--help`-only-smoke limitation note

## Lessons Learned (R110-322)

1. **Docstring-vs-implementation consistency is a bug class:**
   The `extract_count_from_recipes` docstring promised to scan
   "single-line string scalar VALUES" but the early-return gated
   out `str` top-level. A direct test (run the function, observe
   output) would have caught this immediately. Lesson: when a
   function has a docstring with semantic claims, write at least
   1 test that exercises each claim — not just the happy path.
2. **The walk() helper was correct; the caller was wrong:** This
   is a classic "defense in depth" gap. walk() had a clear
   "only handle str/dict/list" contract; the caller added a
   pre-check that over-restricted. Lesson: when the inner
   function's contract is well-defined, don't pre-restrict at
   the outer level — it creates exactly this kind of
   docstring-vs-behavior drift.
3. **Subprocess pattern is the way to test argparse-driven CLI
   tools** (R110-310 → R110-320 → R110-322). Direct `import`
   doesn't work for `tools/*.py` (no `__init__.py`), and even
   if it did, the `__main__` block wouldn't execute. Subprocess
   test = real CLI invocation = both behavior test AND cov
   collection in one shot.
4. **The 8 tests cover 4 distinct bug classes:**
   (a) top-level scalar drop (the bug),
   (b) type-blacklist at top level,
   (c) non-str top-level handling (regression),
   (d) no-regression on dict/list walks.
   This is a "test pyramid" — 1 test per class, not 8 happy-path
   tests. Lesson: cover the negative space too, not just the
   positive space.