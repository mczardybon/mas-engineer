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
