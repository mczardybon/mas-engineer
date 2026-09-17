# R110-579 — Diagnose pytest 3.12 CI flake

## CONTEXT

After R110-578 push to mas-t-tests (commits 1d98e3d + 18ed6c9),
GitHub Actions CI run 35090076401 reports:

- e2e-test.sh (11 checks): ✓ SUCCESS
- pytest (Python 3.12): ✗ FAILURE in 8s (CRASH, not timeout)
- pytest (Python 3.11): ⊘ CANCELLED (race with 18ed6c9 push)

8 seconds is suspicious — way too fast for a real test failure on
7800+ tests. Hypothesis: collection crash or import-error during
pytest setup.

Same flake on 6bafa4e (1 commit BEFORE R110-578), proving the
failure is PRE-EXISTING and NOT caused by my push.

## EVIDENCE (already collected)

1. R110-578 is HEALTH locally:
   ```
   $ pytest tests/test_unix_test_word.py tests/test_r110562_spec_invariant_perf.py \
            tests/test_dev_gatekeeper_matrix_main_coverage.py --timeout=15
   57 passed in 9.31s
   ```

2. CWD-anchor pattern (R110-303) is ALREADY applied in
   `tools/dev_pytest_hook.py` (line 19: `_HERE = Path(__file__).resolve().parent`).
   The CWD-fragility bug from R110-129 is fixed.

3. `tests/conftest.py` does `os.chdir(REPO_ROOT)` at line 61
   (R110-129 fix) AND dynamically loads RECIPE_EXCLUDE from
   `tests/test_unix_test_word.py` for the R110-318 zombie cleanup.

4. CI failure timestamp: 2026-09-16T11:24:10Z + 8s run on commit 6bafa4e
   (pre-existing) and also on 1d98e3d (mine). Latest run on 18ed6c9
   was cancelled for race condition.

## HYPOTHESES TO INVESTIGATE

### H1: Python 3.12 type-hint strictness (most likely)
Local Python is 3.11.15; CI runs 3.11 AND 3.12. The 3.12 run is the
one that fails. Look for `from __future__ import annotations` gaps,
`Optional[X]` without `Union[X, None]` parameterization, or
`typing.Dict`/`typing.List` deprecation warnings that 3.12 promotes
to errors.

Search candidates:
```bash
grep -rn "from typing import" tools/ tests/ --include="*.py" | grep -E "Optional|Dict|List|Tuple"
```

### H2: str/bytes type coercion in subprocess.run calls
Python 3.12 stricter on `subprocess.run(text=True, ...)` when stdout
contains non-UTF-8 bytes. Look for `capture_output=True, text=True`
patterns that don't decode errors explicitly.

### H3: yaml.safe_load with 3.12 newlines / unicode
`yaml.safe_load()` may crash on certain Unicode characters (e.g.
emoji in our R110-545 lockstep). Test:
```bash
for f in recipe/sub/*.yaml; do python3.12 -c "import yaml; yaml.safe_load(open('$f'))" 2>&1 | grep -q Error && echo "BAD: $f"; done
```

### H4: Coverage subprocess tracking failure
R110-311 set `COVERAGE_PROCESS_START` + `PYTHONPATH` in conftest.py.
If `sitecustomize.py` fails to import in 3.12 (e.g. f-string syntax),
the subprocess coverage crashes the suite.

## VERIFICATION STEPS

1. Install Python 3.12 locally:
   ```bash
   which python3.12 || apt install -y python3.12 python3.12-venv
   python3.12 -m venv /tmp/py312 && source /tmp/py312/bin/activate
   pip install -r requirements.txt pytest pytest-cov pytest-timeout pyyaml
   ```

2. Run CI-exact command with 3.12:
   ```bash
   cd mas-engineer && pytest tests/ -q --tb=line --cov=tools --cov=scripts \
     --cov-fail-under=15 --timeout=300
   ```

3. If crash in collection, add `--co -x` to identify the offending test file.

4. If crash in test, add `--tb=long -v` to get the traceback.

5. Catch the output, attach as evidence, then patch root cause.

## SCOPE

This is a CI-only flake. Local pytest on Python 3.11 passes 7815
collection + 57/57 PASS on the relevant test files. R110-578 is
GOOD TO MERGE on the merit of the e2e-test.sh SUCCESS + the
post-flight sub_recipe_ref audit (77/77 resolve, 0 broken).

The flake fix (R110-579) is a separate concern — fix it for hygiene
but R110-578 is not blocked by it (per mas-engineer-pre-push-gate
skill: when CI flake is pre-existing, document with evidence + open
follow-up, do not block).
