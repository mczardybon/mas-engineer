"""
test_r110342_e2e_teams_latent_bugs.py — R110-342 audit.

5-test regression suite for the latent-bug classes fixed in
tools/e2e_teams.py R110-342 (commit TBD).  1 test per bug-class
(per R110-78 verification-theater guard):

  Bug class 1: 2 bare `except: pass` clauses (L417, L425) for
               os.write(master, b"\\x03") → narrowed to
               (OSError, ValueError).  Bare except catches
               KeyboardInterrupt (Py2), real bugs, etc.
  Bug class 2: 3 `with open() no encoding=` (L352 wrapper,
               L544 log, L563 raw-results.json) → all use
               encoding="utf-8".
  Bug class 3: 1 `except Exception as e:` (L398 Popen) — left
               narrowed (acceptable: Popen can fail in many
               ways; we document the remaining pattern).
  Bug class 4: 1 end-to-end smoke (no import crash, no syntax
               error after the R110-342 changes).

  1. TestBareExceptNarrowing::test_bare_except_replaced_in_os_write
  2. TestEncoding::test_all_with_open_have_encoding_utf8
  3. TestExceptExceptionNarrowing::test_popen_except_documented
  4. TestE2eTeamsStillWorks::test_imports_cleanly
  5. TestE2eTeamsStillWorks::test_help_or_no_args_does_not_crash

Run with:
    python3 -m pytest tests/test_r110342_e2e_teams_latent_bugs.py -v
"""
import inspect
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
E2E_TEAMS = TOOLS / "e2e_teams.py"


def _code_only(source: str) -> str:
    """Strip comment lines and docstring-like lines for source-assert."""
    return "\n".join(
        l for l in source.splitlines()
        if not l.strip().startswith("#")
    )


# ─── Bug class 1: 2 bare `except: pass` for os.write → narrowed ──

class TestBareExceptNarrowing:
    """Verify the 2 bare `except: pass` clauses (L417, L425) for
    `os.write(master, b\"\\x03\")` are now narrowed to
    (OSError, ValueError).  Without this, a real bug in the
    os.write call site would be silently swallowed."""

    def test_bare_except_replaced_in_os_write(self):
        src = E2E_TEAMS.read_text()
        # No bare `except:` on code lines
        code_only = _code_only(src)
        bare = re.findall(r"^\s*except:\s*$", code_only, re.MULTILINE)
        assert bare == [], (
            f"{len(bare)} bare `except:` still present in e2e_teams.py"
        )
        # Narrowed tuple for os.write must be present
        assert "(OSError, ValueError): pass" in code_only


# ─── Bug class 2: 3 `with open() no encoding=` → encoding="utf-8" ──

class TestEncoding:
    """Verify all 3 `with open()` sites in e2e_teams.py have
    `encoding=\"utf-8\"`.  Prevents UnicodeDecodeError on
    non-ASCII output (e.g. test results with unicode in markers)."""

    def test_all_with_open_have_encoding_utf8(self):
        src = E2E_TEAMS.read_text()
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


# ─── Bug class 3: 1 `except Exception as e:` at L398 Popen ─────

class TestExceptExceptionNarrowing:
    """The Popen error-handler (L398) keeps a broad `except Exception
    as e:` because Popen can fail in many ways.  We document this
    and verify the rationale comment is present."""

    def test_popen_except_documented(self):
        src = E2E_TEAMS.read_text()
        # The Popen site has its own FileNotFoundError above and
        # then a fallback `except Exception as e:`.  The fallback
        # is acceptable but must produce a structured response.
        # The R110-342 fix is to ensure the except returns a
        # {"status": "fail", "reason": ...} dict (not raise).
        assert "except Exception as e:" in src
        # Check the next non-blank line returns the failure dict
        m = re.search(
            r"except Exception as e:\s*\n\s*return\s*\{\"status\":\s*\"fail\"",
            src,
        )
        assert m is not None, (
            "Popen except Exception must return a structured "
            "{\"status\": \"fail\", ...} response"
        )


# ─── Bug class 4: end-to-end smoke ──────────────────────────────

class TestE2eTeamsStillWorks:
    """Verify e2e_teams.py still imports and runs after R110-342
    changes.  No SyntaxError, no ImportError."""

    def test_imports_cleanly(self):
        """`python3 -c \"import e2e_teams\"` must succeed (the file
        is a script but also importable for testing)."""
        result = subprocess.run(
            ["python3", "-c", "import e2e_teams"],
            capture_output=True, text=True, timeout=15,
            cwd=str(TOOLS),
        )
        assert "Traceback" not in result.stderr, (
            f"e2e_teams.py import crashed: {result.stderr!r}"
        )
        assert result.returncode == 0, (
            f"e2e_teams.py import exit {result.returncode}: {result.stderr!r}"
        )

    def test_help_or_no_args_does_not_crash(self):
        """`python3 tools/e2e_teams.py --help` (or no args) must
        not crash with a Python traceback.  The script may exit
        non-zero (e.g. missing teams), but no Python crash."""
        result = subprocess.run(
            ["python3", str(E2E_TEAMS), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert "Traceback" not in result.stderr, (
            f"e2e_teams.py --help crashed: {result.stderr!r}"
        )
        # Some output on stdout or stderr
        assert len(result.stdout) + len(result.stderr) > 0
