"""
conftest.py for mas-engineer test suite.

Adds repo root to sys.path so test files can import from recipe/, tools/, etc.

R110-129 — also chdir to REPO_ROOT so tests with relative paths
(like tools/dev_im_finder_scan.py or tools/dev_rule_checker.py)
work regardless of how pytest is invoked:

  cd mas-engineer && pytest tests/test_X.py  →  cwd=mas-engineer (OK)
  pytest mas-engineer/tests/test_X.py         →  cwd=parent (BROKEN pre-fix)

Adding os.chdir(REPO_ROOT) here makes the second invocation work
without changing any test code. Two pre-existing failures
(test_scanner_detects_hardcode_stale + test_run_post_test_checks_fail_prints_recommendation)
were CWD-fragility bugs that hid behind "cd mas-engineer && pytest"
as the only supported invocation. R110-129 makes them CWD-robust.

R110-311 — enable coverage tracking for subprocesses.

Sets COVERAGE_PROCESS_START and PYTHONPATH BEFORE any test or
subprocess is spawned. The repo-root `sitecustomize.py` then
auto-loads for any subprocess whose `sys.path` includes REPO_ROOT
(guaranteed because we put it first in sys.path) and calls
`coverage.process_startup()`. That instruments the subprocess
so its executed lines show up in the coverage report.

This is what makes the 45 untracked CLI tools (R110-310
subprocess smoke tests) actually count toward coverage.
Without this, subprocess.run hits a separate Python process
that pytest-cov cannot see.

R110-318 — auto-cleanup of test-side-effect zombie files at
session start. Some tests (e.g. test_r110279_runtime_var_skip.py)
create ephemeral test files (recipe/sub/sub_-.yaml, tests/test_zz_*.py)
as part of their test logic, with cleanup in a `finally` block.
If pytest-timeout kills the test mid-run, the `finally` block is
skipped and the file persists. The 3-source lockstep test
(R110-316) catches this at pre-push time, but a session-start
auto-cleanup gives "fresh state" guarantees without requiring
the user to manually `rm` zombies. Cleanup is restricted to
files matching the known test-side-effect patterns; legitimate
test files (e.g. tests/__init__.py which is 0-byte by convention)
are NEVER touched. The hook is read-mostly: it only deletes
files matching `tests/test_zz_*.py` (and matching .pyc entries)
and prints a warning for unexpected 0-byte files in recipe/sub/
that are NOT in the RECIPE_EXCLUDE allowlist.
"""
import sys
import os
import glob
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# R110-129: chdir to repo root so subprocess.run(cwd='.') and
# relative paths like 'tools/dev_rule_checker.py' resolve correctly
# regardless of the caller's CWD.
os.chdir(REPO_ROOT)

# R110-311: ensure subprocess coverage tracking is enabled.
# Only set if not already (lets CI pass its own value).
os.environ.setdefault("COVERAGE_PROCESS_START", str(REPO_ROOT / ".coveragerc"))
# Make sure subprocesses find the repo's sitecustomize.py
os.environ["PYTHONPATH"] = (
    str(REPO_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")
)


# R110-318 — pytest_sessionstart auto-cleanup of zombie fixtures.
# Runs BEFORE test collection so any zombie files are gone before
# pytest's test discovery sees them. Read-only-by-default: only
# deletes files matching the known test-side-effect pattern
# (tests/test_zz_*.py). All other 0-byte files in tests/ are
# reported as warnings but not touched (e.g. tests/__init__.py
# is 0-byte by convention and must NOT be deleted).
def pytest_sessionstart(session):
    """Auto-cleanup zombie test-side-effect files at session start.

    R110-318: Some tests create ephemeral files (recipe/sub/*.yaml,
    tests/test_zz_*.py) with `try/finally: os.unlink()` cleanup.
    If pytest-timeout kills the test mid-run, the `finally` block
    is skipped and the file persists as a "zombie". The next
    pytest run inherits the zombie and may:
      (a) get collected as a test (false test, wrong assertion)
      (b) trip the R110-316 3-source lockstep test
      (c) confuse other tests that look for "0-byte" patterns
    Auto-cleanup is the cheapest fix: the file is ephemeral by
    design, so deleting it is always correct.
    """
    import sys as _sys  # ensure we use module-level sys

    tests_dir = REPO_ROOT / "tests"
    pycache_dir = tests_dir / "__pycache__"

    # 1. tests/test_zz_*.py — known test-side-effect pattern.
    #    Pattern derived from R110-279 (test_zz_r110279_*.py).
    #    Any new tests using this pattern MUST use the same prefix.
    zombies = sorted(tests_dir.glob("test_zz_*.py"))
    if zombies:
        print(
            f"\n[R110-318] Cleaning {len(zombies)} zombie test-side-effect file(s):",
            file=_sys.stderr,
        )
        for z in zombies:
            print(f"  rm {z.relative_to(REPO_ROOT)}", file=_sys.stderr)
            z.unlink()
        # also clean matching .pyc entries
        if pycache_dir.exists():
            for pyc in sorted(pycache_dir.glob("test_zz_*.pyc")):
                pyc.unlink()

    # 2. recipe/sub/*.yaml 0-byte files NOT in RECIPE_EXCLUDE
    #    allowlist: warn but do NOT delete (could be a legitimate
    #    fixture the user wants to keep; deletion is destructive).
    #    RECIPE_EXCLUDE is parsed from tests/test_unix_test_word.py.
    #    We only WARN here; R110-316 lockstep test catches this
    #    properly at pre-push time.
    recipe_sub = REPO_ROOT / "recipe" / "sub"
    if recipe_sub.exists():
        zero_byte_recipes = [
            p.name for p in recipe_sub.glob("*.yaml") if p.stat().st_size == 0
        ]
        if zero_byte_recipes:
            # Try to load RECIPE_EXCLUDE from test_unix_test_word.py
            # (best-effort; if import fails, just warn unconditionally)
            allowlist = set()
            try:
                _sys.path.insert(0, str(tests_dir))
                # importlib to avoid pytest-collection side-effects
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "_unix_test_word", tests_dir / "test_unix_test_word.py"
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    allowlist = set(getattr(mod, "RECIPE_EXCLUDE", set()))
            except Exception:
                pass
            unhandled = [n for n in zero_byte_recipes if n not in allowlist]
            if unhandled:
                print(
                    f"\n[R110-318] WARNING: {len(unhandled)} 0-byte recipe/sub/*.yaml "
                    f"file(s) NOT in RECIPE_EXCLUDE allowlist (zombie candidates):",
                    file=_sys.stderr,
                )
                for n in unhandled:
                    print(f"  recipe/sub/{n}", file=_sys.stderr)
                print(
                    "  R110-316 3-source lockstep test will FAIL on pre-push.",
                    file=_sys.stderr,
                )
                print(
                    "  Either rm the file or add it to RECIPE_EXCLUDE + "
                    "tools/e2e_run_all.py::artifacts.",
                    file=_sys.stderr,
                )
