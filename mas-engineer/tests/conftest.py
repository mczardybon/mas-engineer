"""
conftest.py for mas-engineer test suite.

Adds repo root to sys.path so test files can import from recipe/, tools/, etc.
"""
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
