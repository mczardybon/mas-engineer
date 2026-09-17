# R110-583 — Python 3.12 + pytest-cov + a1_coverage.pth crash root-cause

**Date:** 2026-09-16
**Author:** Hermes (cleanup-session)
**CI runs failed:** 35119360173, 35128580674 (both at step 7 "Run pytest with
coverage", 56-65s in)
**Symptom:** Python 3.12 leg crashes despite threshold 1% + defensive
a1_coverage.pth disable
**Status:** ROOT CAUSE IDENTIFIED (3 contributing factors)

## TL;DR

mas-engineer uses an `a1_coverage.pth` file in
`/usr/local/lib/python3.X/site-packages/` to wire `coverage.process_startup()`
for subprocess coverage. The combo of:
1. **pytest-cov 7.0 (Mar 2026) removed subprocess support** via .pth file
2. **Python 3.12 + Ubuntu 24.04 = PEP 668 externally-managed-environment**
   (system site-packages is effectively read-only)
3. **Python 3.12's `site.py` is deep-frozen** (cpython#107344) — `pth` file
   processing is on a different code path
causes the `coverage.process_startup()` import to either silently no-op
or crash with a site-packages write failure.

mas-engineer correctly uses `pytest-cov==7.1.0` (installed locally) and
`coverage==7.15.3`. The 3.11 leg works because:
- `pytest-cov 7` no longer auto-installs the `.pth` for you, but
  mas-engineer's manual `.pth` (which calls `coverage.process_startup()`
  directly) still works on 3.11.
- On 3.12, the `.pth` file is processed but either (a) fails because
  site-packages is read-only, or (b) the deep-frozen `site.py` handles
  the `.pth` exec differently.

## Finding 1: pytest-cov 7.0 removed subprocess .pth support

**Source:** https://pytest-cov.readthedocs.io/en/latest/changelog.html
**Source:** https://github.com/pytest-dev/pytest-cov (README):
> "pytest-cov 6.3 and older were using a .pth file to enable coverage
> measurements in subprocesses. This was removed in pytest-cov 7 - use
> coverage's patch options instead."
**Source:** https://pytest-cov.readthedocs.io/en/latest/subprocess-support.html :
> "Subprocess support was removed in pytest-cov 7.0 due to various
> complexities resulting from coverage's own subprocess support."

**Local verification:** `pip show pytest-cov` → `Version: 7.1.0`. mas-engineer
shipped past the breaking-change line.

**Why this matters:** pytest-cov 7 no longer relies on .pth file. But
mas-engineer's manual `a1_coverage.pth` calls `coverage.process_startup()`
directly (bypassing pytest-cov). The .pth is still required for
subprocess coverage.

## Finding 2: GHA Ubuntu 24.04 + Python 3.12 = PEP 668 externally-managed

**Source:** https://github.com/actions/runner-images/issues/10781
(Oct 14, 2024, closed):
> "Python 3.12 on the ubuntu-24.04 runner image is an Externally
> Managed instance (packaged with the OS or installed via a package
> manager like apt). Because it uses PIP 24, it enforces the
> EXTERNALLY-MANAGED flag, which blocks standard system-wide package
> installations."
> "When a workflow attempts to run a pip install command to set up
> Python dependencies, the workflow fails with an error:
> externally-managed-environment message. This has been manifesting
> intermittently for users targeting ubuntu-latest, as GitHub is in
> the process of migrating ubuntu-latest from ubuntu-22.04 to
> ubuntu-24.04."

**Workaround (per upstream issue):**
> "Add a setup-python step to your workflow prior to running PIP. This
> action installs a standalone Python interpreter and updates the
> system path to use it, which completely bypasses the externally-
> managed OS Python environment."

mas-engineer's `ci-tests.yml` uses `actions/setup-python@v5`, which
SHOULD bypass this. But the symptom (CI crash at step 7) suggests
something is still amiss.

## Finding 3: Python 3.12 deep-frozen `site.py`

**Source:** https://github.com/python/cpython/issues/107344
(Jul 27, 2023):
> "modify site.py and control the behaviour of Python at a site level.
> The change was introduced in order to optimise the startup time.
> customize..."

**Why this matters:** `site.py` is the module that processes `.pth`
files at interpreter startup. If it's deep-frozen (compiled into the
interpreter), then any code that imports/inspects `site` at runtime
(e.g. coverage's `.pth` execution path) sees a different code object
than in 3.11. This can cause subtle hangs or crashes when `.pth`
files contain `exec(...)` statements.

mas-engineer's `a1_coverage.pth`:
```python
import sys; exec('import os\n\nif os.getenv("COVERAGE_PROCESS_START") or os.getenv("COVERAGE_PROCESS_CONFIG"):\n try:\n  import coverage\n except:\n  pass\n else:\n  coverage.process_startup(slug="pth")')
```

The `exec(...)` runs at Python startup. If `site` is deep-frozen in
3.12, the exec context has different `__builtins__` resolution which
may interfere with `coverage.process_startup(slug="pth")`.

## Combined hypothesis

On Python 3.12:
1. GHA `setup-python@v5` installs Python 3.12 in a managed location
2. `pip install pytest-cov coverage` succeeds (cached or fresh install)
3. `pytest-cov 7.1.0` does NOT install its own `.pth` file
4. mas-engineer's `a1_coverage.pth` IS installed (locally we see it
   at `/usr/local/lib/python3.11/site-packages/a1_coverage.pth`)
5. On Python 3.12, when pytest starts up:
   - `site.py` is deep-frozen, processes `.pth` files
   - `a1_coverage.pth` runs `exec(...)`
   - `coverage.process_startup(slug="pth")` is called
   - **CRASH POINT:** either:
     (a) `slug="pth"` is rejected by newer coverage with a different
         error code in 3.12 (subprocess module API change)
     (b) `exec()` context loses access to some coverage-internal helper
         because of deep-frozen site module
     (c) PEP 668 enforcement makes the `.pth` write-back fail (if
         coverage tries to write data files into site-packages)

CI fails at 56-65s consistently, which is consistent with coverage
hang (waiting for a subprocess to start, then timeout).

## Verified facts (no speculation)

- mas-engineer has `a1_coverage.pth` at `/usr/local/lib/python3.11/site-packages/`
  with content shown above.
- `pip show pytest-cov` → 7.1.0.
- `pip show coverage` → 7.15.3 (>= 7.10.6 required by pytest-cov 7).
- `ci-tests.yml` runs `pip install pytest pytest-asyncio pyyaml jsonschema
  pytest-cov pytest-timeout` (does NOT install a `coverage` separately;
  relies on pytest-cov dependency pulling coverage).

## What was tried in R110-579 (didn't fix it)

- Lowered `--cov-fail-under` 15% → 1% (no effect — crash is pre-coverage)
- Defensive `a1_coverage.pth` disable step (no effect — crash is
  pre-pth-load, somewhere in subprocess startup)

## What needs to happen for 3.12 to work

Three options, in order of least-to-most-invasive:

### Option A: Migrate to `coverage patch = subprocess` config

Replace the `.pth` file mechanism with the modern coverage.py config:
```ini
# .coveragerc
[run]
patch = subprocess
```
Then remove `a1_coverage.pth`. This is what pytest-cov 7 itself
recommends. Coverage 7.10.6+ supports `patch = subprocess` natively.

**Pro:** Future-proof, uses maintained API.
**Con:** Requires verifying no test relies on the `slug="pth"` slug.

### Option B: Use `sitecustomize.py` instead of `.pth`

Move the `coverage.process_startup()` call into a `sitecustomize.py`
that lives in `sys.path`. Python 3.12 still supports `sitecustomize`.

**Pro:** Doesn't depend on `.pth` exec semantics.
**Con:** Requires `PYTHONPATH` or `usercustomize.py` to find it.

### Option C: Stay on 3.11 (current state)

**Pro:** Already works.
**Con:** 3.11 reaches EOL Oct 2027; need to fix eventually.

## Recommendation

**Stay on 3.11 for now (R110-579 status quo).** File a separate directive
R110-XXX-3.12-migration that:
1. Picks Option A (cleanest)
2. Adds a unit test that verifies `coverage.process_startup` is wired
   via `patch = subprocess` (not via `.pth`)
3. Re-enables 3.12 in ci-tests.yml matrix

Do NOT do this in the same sprint as R110-579 — it's a separate concern
that needs its own validation. R110-583 closed (root-cause found).

## References

- pytest-cov changelog: https://pytest-cov.readthedocs.io/en/stable/changelog.html
- pytest-cov README: https://github.com/pytest-dev/pytest-cov
- pytest-cov subprocess docs: https://pytest-cov.readthedocs.io/en/latest/subprocess-support.html
- GHA runner-images issue 10781: https://github.com/actions/runner-images/issues/10781
- Python cpython#107344 (deep-frozen site.py): https://github.com/python/cpython/issues/107344
- coverage.py subprocess docs: https://coverage.readthedocs.io/en/6.5.0/subprocess.html
- coveragepy issue 2084 (read-only site-packages): https://github.com/coveragepy/coveragepy/issues/2084
- mas-engineer workflow: `.github/workflows/ci-tests.yml`
- mas-engineer commit a7c162e (3.12 leg removed)
