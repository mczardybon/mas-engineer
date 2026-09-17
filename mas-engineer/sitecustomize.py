"""R110-311 sitecustomize: auto-enable coverage for subprocesses.

When pytest-cov runs the test suite, it sets COVERAGE_PROCESS_START
to the .coveragerc path in the environment. By default, only the
pytest process itself is instrumented. This sitecustomize.py,
loaded automatically by Python when the repo root is in
sys.path (which conftest.py ensures), enables coverage tracking
for any subprocess that inherits the env var.

This is the "free lunch" for the 45 untracked CLI tools:
they are invoked as `python3 tools/X.py` by R110-310's
subprocess smoke tests. Without this, those runs are invisible
to coverage. With this, every line they execute is tracked and
combined with the main pytest coverage at the end.

Mechanism:
  - conftest.py sets COVERAGE_PROCESS_START + PYTHONPATH
    BEFORE pytest collects any tests.
  - Python auto-loads sitecustomize.py from any sys.path entry.
  - If COVERAGE_PROCESS_START is set, we call
    `coverage.process_startup()` which instruments the current
    Python process for coverage collection.
  - The instrumented process writes its data to `.coverage.<host>.<pid>`
    (parallel mode from .coveragerc).
  - pytest-cov calls `coverage combine` at session end, merging
    all parallel data files into `.coverage`.

Pre-conditions (set by conftest.py):
  - REPO_ROOT on sys.path (so sitecustomize is found)
  - COVERAGE_PROCESS_START=REPO/.coveragerc in env
  - COV_CORE_SOURCE=tools in env (optional, but safer)

Reference: https://coverage.readthedocs.io/en/latest/subprocess.html
"""
import os
import sys

# Only activate if explicitly enabled (avoids double-instrumenting pytest)
if os.environ.get("COVERAGE_PROCESS_START") and "coverage" not in sys.modules:
    try:
        import coverage

        coverage.process_startup()
    except Exception:
        # Never let sitecustomize break a normal import chain
        # (would cascade through every subprocess).
        pass
