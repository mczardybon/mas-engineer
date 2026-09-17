"""
test_r110340_dev_rule_checker_latent_bugs.py — R110-340 audit.

6-test regression suite for the 5 latent-bug classes fixed in
tools/dev_rule_checker.py R110-340 (commit TBD).  1 test per
bug-class (per R110-78 verification-theater guard, except the
3 bare-except sites share one test since they are the same
class of bug):

  Bug class 1: 3 bare `except:` (L96, L552, L597)
  Bug class 2: 2 `yaml.safe_load(open(X))` file-leak (L505, L550)
  Bug class 3: 1 `open(p).read()` file-leak (L311)
  Bug class 4: 12+ `with open() no encoding=`
  Bug class 5: 3 `except Exception:` (L312, L507, L683)
  Bug class 6: end-to-end (--help still works)

  1. TestBareExceptNarrowing::test_bare_except_replaced_in_all_sites
  2. TestFileLeakFix::test_safe_load_open_replaced_with_context_manager
  3. TestFileLeakFix::test_mas_mode_bare_open_replaced
  4. TestEncoding::test_all_with_open_have_encoding_utf8
  5. TestExceptExceptionNarrowing::test_except_exception_narrowed
  6. TestRuleCheckerStillWorks::test_help_still_works

Run with:
    python3 -m pytest tests/test_r110340_dev_rule_checker_latent_bugs.py -v
"""
import inspect
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
RULE_CHECKER = TOOLS / "dev_rule_checker.py"

sys.path.insert(0, str(TOOLS))
import dev_rule_checker as rc  # noqa: E402


def _code_only(source: str) -> str:
    """Strip comment lines and docstring-like lines for source-assert."""
    return "\n".join(
        l for l in source.splitlines()
        if not l.strip().startswith("#")
    )


# ─── Bug class 1: 3 bare `except:` → narrowed ────────────────────

class TestBareExceptNarrowing:
    """Verify all 3 bare `except:` clauses (L96, L552, L597) have
    been replaced with specific exception tuples.  A bare `except:`
    catches EVERYTHING including KeyboardInterrupt (Py2) and
    silently swallows real bugs."""

    def test_bare_except_replaced_in_all_sites(self):
        """Source-assert: zero `except:` lines remain in code.
        All 3 sites now have specific exception tuples."""
        src = inspect.getsource(rc)
        code_only = _code_only(src)
        # No bare `except:` on any code line
        bare = re.findall(r"^\s*except:\s*$", code_only, re.MULTILINE)
        assert bare == [], (
            f"{len(bare)} bare `except:` still present in dev_rule_checker.py"
        )
        # The narrowed form must be present
        assert "(yaml.YAMLError, OSError, KeyError, TypeError)" in code_only
        # The (yaml.YAMLError, OSError) tuple for history-save
        assert "(yaml.YAMLError, OSError)" in code_only


# ─── Bug class 2 + 3: file-leak fixes ────────────────────────────

class TestFileLeakFix:
    """Verify the 3 file-leak sites (yaml.safe_load(open(X)) at
    L505 + L550, and bare `open(p).read()` at L311) are now
    using context managers.  Without context manager the file
    is left unclosed until GC, triggering ResourceWarning."""

    def test_safe_load_open_replaced_with_context_manager(self):
        """`yaml.safe_load(open(X))` pattern (file-leak) is GONE.
        Both counter_path and history_path now use `with open(...)`."""
        # The pattern can appear in comments (R110-340 documents
        # the pre-fix code), so we strip comments first.
        src = inspect.getsource(rc)
        code_only = _code_only(src)
        assert re.search(r"safe_load\(open\(", code_only) is None, (
            "`safe_load(open(...))` pattern still present on a code line (file-leak)"
        )
        # Both sites now use context manager with encoding
        assert "with open(counter_path, encoding=\"utf-8\")" in src
        assert "with open(history_path, encoding=\"utf-8\") as _yf" in src

    def test_mas_mode_bare_open_replaced(self):
        """L311 `work_on = open(p).read().strip().lower()` is GONE.
        Now uses `with open(p, encoding="utf-8") as _f:`.
        This site had 2 bugs: file-leak + no encoding."""
        src = inspect.getsource(rc)
        code_only = _code_only(src)
        # No bare `open(X).read()` pattern on a code line
        assert re.search(r"\bopen\([^)]+\)\.read\(\)", code_only) is None, (
            "Bare `open(X).read()` pattern still present (L311 file-leak)"
        )
        # mas-mode context manager must be present
        assert "with open(p, encoding=\"utf-8\") as _f" in src


# ─── Bug class 4: encoding on all `with open()` sites ─────────────

class TestEncoding:
    """Verify every `with open(...)` statement in dev_rule_checker.py
    has an `encoding="utf-8"` argument.  Comments are excluded."""

    def test_all_with_open_have_encoding_utf8(self):
        """Every `with open(...)` on a code line must have
        `encoding="utf-8"`.  Prevents UnicodeDecodeError on
        non-ASCII rule files."""
        src = inspect.getsource(rc)
        violations = []
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(r"\bwith open\(", line):
                if "encoding=" not in line:
                    violations.append((i, line))
        assert violations == [], (
            f"{len(violations)} `with open()` line(s) without `encoding=`: "
            + "\n".join(f"  L{l}: {ln!r}" for l, ln in violations)
        )


# ─── Bug class 5: 3 `except Exception:` → narrowed ──────────────

class TestExceptExceptionNarrowing:
    """Verify the 3 `except Exception:` clauses (L312, L507, L683)
    are now narrowed to specific exception tuples.  An `except
    Exception:` catches every real bug, hiding regressions."""

    def test_except_exception_narrowed(self):
        """Source-assert: zero `except Exception:` lines remain
        on code lines.  All 3 sites are now specific tuples."""
        src = inspect.getsource(rc)
        code_only = _code_only(src)
        bare = re.findall(r"^\s*except Exception:\s*$", code_only, re.MULTILINE)
        assert bare == [], (
            f"{len(bare)} bare `except Exception:` still present in code"
        )
        # The narrowed tuples for the 3 sites:
        # - L312 mas-mode: (OSError, UnicodeDecodeError)
        # - L507 session-count: (yaml.YAMLError, OSError, ValueError, KeyError, TypeError)
        # - L683 arch-subprocess: (subprocess.SubprocessError, OSError, FileNotFoundError)
        # The mas-mode tuple is the one most likely to be a fresh
        # addition, so we check for it specifically:
        assert "(OSError, UnicodeDecodeError)" in code_only


# ─── Bug class 6: end-to-end (--help still works) ────────────────

class TestRuleCheckerStillWorks:
    """Verify dev_rule_checker.py still imports + runs after all
    the R110-340 changes.  No SyntaxError, no ImportError, no
    crash from any of the edits."""

    def test_help_still_works(self):
        """Subprocess `python3 tools/dev_rule_checker.py --help`
        must not crash with a Python traceback."""
        result = subprocess.run(
            ["python3", str(RULE_CHECKER), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert "Traceback" not in result.stderr, (
            f"dev_rule_checker.py --help crashed: {result.stderr!r}"
        )
        # Some output must be present (stdout or stderr)
        assert len(result.stdout) + len(result.stderr) > 0
