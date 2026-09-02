"""R110-318 — auto-cleanup of test-side-effect zombie files at session start.

Tests for the pytest_sessionstart hook in tests/conftest.py. The hook
auto-cleans two classes of zombie files:
  1. tests/test_zz_*.py (test-side-effect pattern, R110-279 originated)
  2. recipe/sub/*.yaml 0-byte files NOT in RECIPE_EXCLUDE allowlist
     (WARNING only, no auto-delete — could be a legitimate fixture)

Test design:
  - We do NOT call pytest_sessionstart directly. Instead, we import
    the conftest module and call its pytest_sessionstart(session) with
    a mock session. This is the cleanest way to test the hook without
    having to spin up a full pytest subprocess.
  - We test in a tempdir that mirrors the relevant structure: tests/
    and recipe/sub/ relative to a faked REPO_ROOT. The hook uses
    REPO_ROOT (a module-level Path) computed from __file__.parent.parent.
    We monkeypatch conftest.REPO_ROOT and conftest.tests_dir to the
    tempdir for the duration of the test.
  - Each test creates its own zombie(s), calls the hook, and asserts
    the post-state (file removed / file kept / WARNING printed).
"""
import sys
import importlib.util
import io
import contextlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Create a fake repo root with tests/ and recipe/sub/ subdirs.

    Yields a namespace with .REPO_ROOT, .tests_dir, .recipe_sub, .conftest.
    The conftest module is imported fresh against the fake REPO_ROOT
    so its module-level REPO_ROOT matches the fake path.
    """
    # Create dirs
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    pycache = tests_dir / "__pycache__"
    pycache.mkdir()
    recipe_sub = tmp_path / "recipe" / "sub"
    recipe_sub.mkdir(parents=True)

    # Create a minimal test_unix_test_word.py with empty RECIPE_EXCLUDE
    (tests_dir / "test_unix_test_word.py").write_text(
        "RECIPE_EXCLUDE = set()\n"
    )

    # Also write a real conftest.py into the fake tests_dir so that
    # importlib can load it. We do NOT use the production conftest
    # here because we want to test the logic in isolation. Instead
    # we copy the pytest_sessionstart function from production.

    # Load the PRODUCTION conftest so we test the real hook code
    real_conftest = Path("/workspace/dev-branch/mas-engineer-cleanup/mas-engineer/tests/conftest.py")
    spec = importlib.util.spec_from_file_location("conftest_fake", real_conftest)
    conftest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conftest)

    # Monkeypatch REPO_ROOT and the derived paths to tmp_path
    monkeypatch.setattr(conftest, "REPO_ROOT", tmp_path)

    # Manually recompute tests_dir / pycache_dir / recipe_sub inside
    # the hook: the hook reads them as locals from REPO_ROOT, so as
    # long as REPO_ROOT is patched, the hook uses the right paths.
    # We just need to make sure the hook's local variable assignment
    # runs AFTER the monkeypatch. Since the hook is a function, this
    # is automatic — it reads `REPO_ROOT` from the conftest module
    # namespace at call time, not at definition time.

    yield type("FakeRepo", (), {
        "REPO_ROOT": tmp_path,
        "tests_dir": tests_dir,
        "pycache": pycache,
        "recipe_sub": recipe_sub,
        "conftest": conftest,
    })


def _call_hook(conftest):
    """Call the conftest's pytest_sessionstart with a mock session."""
    session = MagicMock()
    conftest.pytest_sessionstart(session)


def test_clean_zombie_test_zz_file(fake_repo):
    """Zombie test_zz_*.py file is deleted by the hook."""
    zombie = fake_repo.tests_dir / "test_zz_r110318_zombie.py"
    zombie.write_text("# zombie\n")
    assert zombie.exists()

    _call_hook(fake_repo.conftest)

    assert not zombie.exists(), \
        f"Zombie {zombie.name} should have been deleted by R110-318 hook"


def test_clean_zombie_pycache(fake_repo):
    """Matching test_zz_*.pyc is also cleaned."""
    zombie_py = fake_repo.tests_dir / "test_zz_r110318_again.py"
    zombie_py.write_text("# zombie\n")
    zombie_pyc = fake_repo.pycache / "test_zz_r110318_again.cpython-311.pyc"
    zombie_pyc.write_bytes(b"fake bytecode\n")
    assert zombie_py.exists()
    assert zombie_pyc.exists()

    _call_hook(fake_repo.conftest)

    assert not zombie_py.exists()
    assert not zombie_pyc.exists(), \
        f"Matching .pyc {zombie_pyc.name} should also be cleaned"


def test_legitimate_test_files_untouched(fake_repo):
    """Legitimate test files (not matching test_zz_*.py) are NOT touched."""
    legit = fake_repo.tests_dir / "test_unix_test_word.py"
    legit.write_text("RECIPE_EXCLUDE = set()\n")
    init = fake_repo.tests_dir / "__init__.py"
    init.write_text("")  # 0-byte by convention
    assert legit.exists()
    assert init.exists()

    _call_hook(fake_repo.conftest)

    assert legit.exists(), "legitimate test file must not be deleted"
    assert init.exists(), "tests/__init__.py is 0-byte by convention, must not be deleted"


def test_warn_on_unhandled_recipe_sub_yaml(fake_repo):
    """0-byte recipe/sub/*.yaml NOT in RECIPE_EXCLUDE triggers WARNING."""
    zombie_yaml = fake_repo.recipe_sub / "sub_-.yaml"
    zombie_yaml.write_text("")  # 0-byte
    assert zombie_yaml.exists()

    # Capture stderr
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        _call_hook(fake_repo.conftest)
    stderr_output = captured.getvalue()

    assert "[R110-318] WARNING" in stderr_output, \
        f"Expected R110-318 WARNING, got: {stderr_output!r}"
    assert "sub_-.yaml" in stderr_output, \
        f"Expected sub_-.yaml in WARNING, got: {stderr_output!r}"
    # WARNING only — file NOT deleted
    assert zombie_yaml.exists(), \
        "R110-318 must NOT auto-delete recipe/sub/*.yaml (destructive, only warns)"


def test_no_warning_when_recipe_sub_yaml_in_allowlist(fake_repo):
    """0-byte recipe/sub/*.yaml IN RECIPE_EXCLUDE does NOT warn."""
    # Override the loaded test_unix_test_word to include sub_-.yaml
    (fake_repo.tests_dir / "test_unix_test_word.py").write_text(
        "RECIPE_EXCLUDE = {'sub_-.yaml'}\n"
    )
    zombie_yaml = fake_repo.recipe_sub / "sub_-.yaml"
    zombie_yaml.write_text("")
    assert zombie_yaml.exists()

    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        _call_hook(fake_repo.conftest)
    stderr_output = captured.getvalue()

    assert "[R110-318] WARNING" not in stderr_output, \
        f"Allowed 0-byte file must not warn. Got: {stderr_output!r}"
    assert zombie_yaml.exists(), "Allowed file must be untouched"


def test_no_op_when_no_zombies(fake_repo):
    """Clean state: hook produces no output, no deletions."""
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        _call_hook(fake_repo.conftest)
    stderr_output = captured.getvalue()

    assert "[R110-318]" not in stderr_output, \
        f"Clean state should be silent, got: {stderr_output!r}"
    # Legitimate files still there
    assert (fake_repo.tests_dir / "test_unix_test_word.py").exists()


def test_multiple_zombies_all_cleaned(fake_repo):
    """Multiple zombie test_zz_*.py files all cleaned in one pass."""
    zombies = []
    for i in range(5):
        z = fake_repo.tests_dir / f"test_zz_r110318_{i}.py"
        z.write_text(f"# zombie {i}\n")
        zombies.append(z)
    for z in zombies:
        assert z.exists()

    _call_hook(fake_repo.conftest)

    for z in zombies:
        assert not z.exists(), f"{z.name} should be cleaned"
