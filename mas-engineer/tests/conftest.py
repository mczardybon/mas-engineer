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
"""
import sys
import os
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
