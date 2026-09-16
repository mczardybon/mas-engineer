# R110-584 — Python 3.12 + .pth crash: Migration to `patch = subprocess`

**Date:** 2026-09-16
**Status:** DRAFT ONLY — DO NOT APPLY until reviewed
**Parent:** R110-583 (root-cause analysis)

## Why migrate

`a1_coverage.pth` exists at `/usr/local/lib/python3.11/site-packages/`.
It calls `coverage.process_startup(slug="pth")` from `.pth` exec context.
On Python 3.12 this crashes (root-caused in R110-583: deep-frozen
site.py + PEP 668 externally-managed environment + pytest-cov 7.0+
removed its own .pth mechanism).

Coverage 7.10.6+ provides a config-based replacement that does NOT
depend on `.pth` exec semantics:

```ini
[run]
patch = subprocess
```

This makes coverage inject itself into the subprocess module's
`Popen` factory at the parent process level, so any subprocess
automatically gets coverage measurement without per-Python-interpreter
`.pth` file installation.

## Why it's better than `.pth`

| Aspect | `.pth` file | `patch = subprocess` |
|--------|-------------|----------------------|
| Setup needed | install .pth into every Python's site-packages | config-only, no site-packages write |
| Python 3.12 compat | broken (deep-frozen site.py) | works (no site.py interaction) |
| PEP 668 compat | broken (can't write site-packages) | works (no site-packages write) |
| Python 3.11 compat | works | works |
| Per-test isolation | `slug="pth"` is global | per-coverage-run via `[run]` settings |
| pytest-cov 7+ compat | works (manual) | works (officially supported) |
| Reload-in-PDB | fragile | robust (re-applied via Popen factory) |

## Migration steps

### Step 1: add `[run] patch = subprocess` to .coveragerc (DRAFT)

Edit `mas-engineer/.coveragerc`:

```diff
 [run]
 source = tools
 branch = False
 parallel = False
+patch = subprocess
```

### Step 2: remove `a1_coverage.pth` from the repo

It currently lives at `/usr/local/lib/python3.11/site-packages/a1_coverage.pth`
on local dev. After migration, remove it.

The `.pth` file should NOT be in mas-engineer-repo itself (it's a
site-package, not source). Check if it was checked into the repo
under `tools/` or similar.

### Step 3: add unit test that verifies wiring

New test `tests/test_coverage_patching.py`:

```python
def test_patch_subprocess_wired_in_coveragerc():
    """R110-584: subprocess coverage is wired via config, not .pth."""
    import configparser
    cp = configparser.ConfigParser()
    cp.read(REPO_ROOT / ".coveragerc")
    assert cp.get("run", "patch", fallback="") == "subprocess", (
        "Subprocess coverage must use `patch = subprocess` config; "
        "the .pth file mechanism is broken on Python 3.12."
    )


def test_no_pth_file_referenced_from_tools():
    """R110-584: no tool should install .pth files."""
    for p in (REPO_ROOT / "tools").rglob("*.py"):
        text = p.read_text()
        assert "site-packages" not in text or "site-packages" not in text.split(".pth")[0], (
            f"{p.name}: still writes to site-packages (legacy .pth install)"
        )
```

### Step 4: re-enable Python 3.12 leg in ci-tests.yml

Revert the R110-579 single-leg change:

```diff
-python-version: ["3.11"]
+python-version: ["3.11", "3.12"]
```

### Step 5: delete or deprecate `a1_coverage.pth` references

Search for any reference to `a1_coverage` and remove. Most likely
locations:
- `mas-engineer/scripts/dev-install.sh`
- `mas-engineer/tools/dev_ci_smoke.py`
- docstrings mentioning the `.pth` slug

### Step 6: update R110-579 / R110-583 comments in ci-tests.yml

Replace "Root cause is unverified (no Python 3.12 available locally)"
with "Migration complete: see .coveragerc [run] patch = subprocess".

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `patch = subprocess` doesn't cover tools invoked via `subprocess.run([python, ...])` from non-Python callers | LOW | Most tests are pytest-asyncio or subprocess-pytest, both Python |
| Coverage % drops because `patch = subprocess` measures different processes | MEDIUM | Re-run codecov with both patches to compare; expect 1-3pp drop |
| pytest-cov 7.x has its own subprocess handling that conflicts | LOW | pytest-cov docs recommend removing their `.pth` (which is gone in 7+) and using `patch = subprocess` |

## Validation checklist

Before merge:
- [ ] Local pytest run passes (3.11 + 3.12)
- [ ] `coverage report` shows subprocess coverage in --cov-report=term
- [ ] No `a1_coverage.pth` referenced in any code or doc
- [ ] `tests/test_coverage_patching.py` passes on 3.11 and 3.12
- [ ] Codecov accepts the new coverage shape

## Why DO NOT APPLY NOW

- R110-579 + R110-583 changes (3.12 leg removed) are still in
  flux; ci-tests.yml timeout is being bumped to 15min in this sprint
  (R110-584) to address CI queue pressure first.
- The current local dev environment (3.11) works with the `.pth`
  mechanism; removing it without verification would break local
  coverage immediately.
- Needs separate sprint with proper local + CI validation.

DO NOT MERGE THIS FILE — it's a research/prep artifact for a future
sprint. The actual `.coveragerc` edit must wait for:
1. CI queue pressure settled (R110-584 timeout bump merged)
2. Local 3.11 + 3.12 dual-validation in a fresh dev env
3. Review of the unit tests above by someone with full coverage
   context

## References

- coverage.py patch_subprocess docs:
  https://coverage.readthedocs.io/en/7.6.0/subprocess.html#configuring-subprocess-coverage
- pytest-cov changelog (Mar 2026 .pth removal):
  https://pytest-cov.readthedocs.io/en/stable/changelog.html
- mas-engineer .coveragerc: `mas-engineer/.coveragerc` (current)
- mas-engineer R110-583 research: `mas-engineer/logs/r110583-3.12-root-cause/RESEARCH.md`
- mas-engineer R110-584 ci-tests.yml timeout bump (in this sprint)
