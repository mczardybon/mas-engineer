"""R110-334: regression tests for 4 latent-bug fixes in tools/dev_generic_init.py.

Fixes:
  1. L977-981: bare `except:` in cmd_bootstrap (npm install) → narrow except
  2. L263:    lazy `import shutil` in create_bp_checklist → removed (top-level already has it)
  3. L625:    lazy `import yaml as _y` in create_state_files → uses top-level yaml
  4. L634:    lazy `import yaml as _y` in create_state_files → uses top-level yaml

Each test must FAIL on the pre-fix code and PASS on the post-fix code.
The pre-fix verification is implicit (git diff shows the 4 hunks; if any is missing,
the corresponding test will fail).

Why these matter:
- Bug 1 (bare except) silently swallows KeyboardInterrupt/SystemExit, masking user
  cancellation as a npm failure. Ctrl-C during a bootstrap would print "npm install
  failed — manuell execute" instead of exiting.
- Bugs 2-4 are copy-paste / drift bugs — the top of the file already has the imports
  (L18, L19). Lazy re-imports inside function bodies suggest the file was edited in
  different places at different times, and the imports should live at the top.

Pattern: anchor tests use Path(__file__).resolve().parent to find the module
(CWD-independent, R110-303 pattern).
"""
import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path

# R110-303 anchor pattern: CWD-independent module resolution
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
TOOL_PATH = REPO_ROOT / "tools" / "dev_generic_init.py"


def _load_source() -> str:
    """Read the live dev_generic_init.py source for AST + text assertions."""
    return TOOL_PATH.read_text(encoding="utf-8")


def _get_function_source(src: str, func_name: str) -> str:
    """Extract the source of a top-level function by name."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.get_source_segment(src, node) or ""
    raise AssertionError(f"Function {func_name!r} not found in {TOOL_PATH}")


class TestR110334BareExceptRemoved(unittest.TestCase):
    """Bug 1: L977-981 `except:` → narrow except."""

    def test_no_bare_except_in_bootstrap(self):
        """No `except:` (without exception type) anywhere in dev_generic_init.py."""
        tree = ast.parse(_load_source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                self.assertIsNotNone(
                    node.type,
                    f"Bare `except:` found at L{node.lineno} — should be `except (SomeError) as e:`"
                )

    def test_cmd_bootstrap_npm_except_is_narrow(self):
        """cmd_bootstrap's npm-install try/except must use a narrow exception type."""
        func_src = _get_function_source(_load_source(), "cmd_bootstrap")
        # The fix: except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e
        self.assertIn(
            "except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:",
            func_src,
            "cmd_bootstrap npm-install handler must catch only the expected exception types, not bare `except:`"
        )
        # And the old bare-except line must be gone
        bare_lines = [ln for ln in func_src.splitlines() if ln.strip() == "except:"]
        self.assertEqual(
            len(bare_lines), 0,
            f"Found bare `except:` in cmd_bootstrap: {bare_lines}"
        )


class TestR110334NoLazyShutilReimport(unittest.TestCase):
    """Bug 2: L263 `import shutil` inside create_bp_checklist → removed."""

    def test_no_lazy_import_in_create_bp_checklist(self):
        """create_bp_checklist must not contain `import shutil` (use top-level)."""
        func_src = _get_function_source(_load_source(), "create_bp_checklist")
        # The lazy `import shutil` was a single-line statement inside an `if not dry_run:` block.
        for ln in func_src.splitlines():
            stripped = ln.strip()
            self.assertNotEqual(
                stripped, "import shutil",
                f"`import shutil` is a lazy re-import inside create_bp_checklist. "
                f"Use the top-level import (L19) instead."
            )

    def test_top_level_shutil_still_present(self):
        """Top of file must still `import shutil` (we only removed the lazy one)."""
        src = _load_source()
        # Find the first ~25 lines (imports area)
        head = "\n".join(src.splitlines()[:25])
        self.assertIn("import shutil", head, "Top-level `import shutil` must remain")


class TestR110334NoLazyYamlReimport(unittest.TestCase):
    """Bugs 3+4: L625+L634 `import yaml as _y` inside create_state_files → use top-level."""

    def test_no_lazy_yaml_as__y_in_create_state_files(self):
        """create_state_files must not contain `import yaml as _y` (use top-level)."""
        func_src = _get_function_source(_load_source(), "create_state_files")
        for ln in func_src.splitlines():
            stripped = ln.strip()
            self.assertNotEqual(
                stripped, "import yaml as _y",
                f"`import yaml as _y` is a lazy re-import inside create_state_files. "
                f"Use the top-level `yaml` (L18) instead."
            )

    def test_create_state_files_uses_top_level_yaml(self):
        """After the fix, create_state_files calls `yaml.dump(...)` directly, not `_y.dump(...)`."""
        func_src = _get_function_source(_load_source(), "create_state_files")
        self.assertIn("yaml.dump(", func_src, "create_state_files should call top-level yaml.dump")
        self.assertNotIn("_y.dump(", func_src, "create_state_files should not use `_y` alias")


class TestR110334ModuleStillCompiles(unittest.TestCase):
    """Sanity: the fixed module must still compile + import successfully."""

    def test_pycompile(self):
        """`python3 -m py_compile tools/dev_generic_init.py` returns 0."""
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", str(TOOL_PATH)],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        self.assertEqual(
            r.returncode, 0,
            f"py_compile failed:\nstdout={r.stdout}\nstderr={r.stderr}"
        )

    def test_module_imports(self):
        """`import dev_generic_init` must succeed and the 4 fixed functions are present."""
        # Add the tools/ dir to sys.path so the import resolves
        tools_dir = str(TOOL_PATH.parent)
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        try:
            import dev_generic_init  # noqa: F401
        except Exception as e:
            self.fail(f"import dev_generic_init failed: {type(e).__name__}: {e}")
        for fn in ("cmd_bootstrap", "create_bp_checklist", "create_state_files"):
            self.assertTrue(
                hasattr(dev_generic_init, fn),
                f"dev_generic_init.{fn} is missing"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
