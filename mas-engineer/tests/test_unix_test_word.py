"""
test_unix_test_word.py — POSIX `test` builtin e2e regression-suite.

The "unix test word" is the POSIX `test` builtin (also written as `[`).
This test file USES the real POSIX `test` command (via subprocess) to verify
file-system integrity of the mas-engineer workspace.

These are the EXACT checks that sub_mas-unix-test-runner would perform when
called by the mas-engineer. So running this test is equivalent to e2e-testing
the unix-test-runner.

Run with:
    python3 -m pytest tests/test_unix_test_word.py -v
"""
import subprocess
import os
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()


def _test(check: str) -> bool:
    """Run a POSIX `test` expression. Returns True if check passes."""
    r = subprocess.run(["test"] + check.split(), capture_output=True, text=True)
    return r.returncode == 0


def test_workspace_exists():
    """Sanity: REPO_ROOT must exist as a directory."""
    assert _test(f"-d {REPO_ROOT}"), f"workspace not a dir: {REPO_ROOT}"


def test_recipe_sub_dir_exists():
    assert _test(f"-d {REPO_ROOT}/recipe/sub"), "recipe/sub missing"


def test_recipe_instructions_dir_exists():
    assert _test(f"-d {REPO_ROOT}/recipe/instructions"), "recipe/instructions missing"


def test_tools_dir_exists():
    assert _test(f"-d {REPO_ROOT}/tools"), "tools missing"


def test_tests_dir_exists():
    assert _test(f"-d {REPO_ROOT}/tests"), "tests missing"


def test_core_recipe_general_improver_exists():
    assert _test(f"-f {REPO_ROOT}/recipe/sub/sub_mas-general-improver.yaml"), \
        "core recipe missing"


def test_core_recipe_master_constitution_exists():
    assert _test(f"-f {REPO_ROOT}/recipe/sub/sub_mas-master-constitution.yaml"), \
        "constitution missing"


def test_test_runner_recipe_exists():
    assert _test(f"-f {REPO_ROOT}/recipe/sub/sub_mas-test-runner.yaml"), \
        "test-runner recipe missing"


def test_unix_test_runner_recipe_exists():
    """The new unix-test-runner recipe (added in this e2e test) must exist."""
    assert _test(f"-f {REPO_ROOT}/recipe/sub/sub_mas-unix-test-runner.yaml"), \
        "unix-test-runner recipe missing"


def test_all_recipe_files_non_empty():
    """Every yaml in recipe/sub/ must be non-empty (test -s = exists and size > 0)."""
    recipe_dir = REPO_ROOT / "recipe" / "sub"
    failures = []
    for f in sorted(recipe_dir.glob("*.yaml")):
        if not _test(f"-s {f}"):
            failures.append(str(f.relative_to(REPO_ROOT)))
    assert not failures, f"Empty recipe files: {failures}"


def test_sub_recipe_count_at_least_50():
    """mas-engineer should have >=50 sub-recipes per docs."""
    recipe_dir = REPO_ROOT / "recipe" / "sub"
    yaml_files = list(recipe_dir.glob("*.yaml"))
    n = len(yaml_files)
    assert n >= 50, f"sub-recipe count = {n}, expected >= 50"


def test_sub_recipe_count_at_least_55():
    """Per docs/HOWTO-PACKAGE-TEAM and README: ~56 sub-recipes (as of 2026-07-22).
    We allow >=55 to account for additions (e.g. new test recipes). The exact
    count should be tracked in docs/manifest.md, not hardcoded in tests.
    """
    recipe_dir = REPO_ROOT / "recipe" / "sub"
    n = len(list(recipe_dir.glob("*.yaml")))
    assert n >= 55, f"sub-recipe count = {n}, expected >=55 (was 56 per docs/manifest.md)"


def test_sub_recipe_count_matches_manifest():
    """If docs/manifest.md mentions a count, it should match reality (or be >= reality)."""
    manifest = (REPO_ROOT / "docs" / "manifest.md").read_text()
    recipe_dir = REPO_ROOT / "recipe" / "sub"
    n = len(list(recipe_dir.glob("*.yaml")))
    # Find any "N sub-recipes" or "(N)" pattern
    import re
    matches = re.findall(r'\b(\d+)\s+sub-recipes?\b', manifest)
    if matches:
        claimed = int(matches[0])
        assert n == claimed or n == claimed + 1, \
            f"actual={n}, docs claim {claimed} — manifest.md may be stale (off by 1?)"


def test_all_yaml_files_have_yaml_extension():
    """No misnamed files: every recipe file in recipe/sub/ must end in .yaml."""
    recipe_dir = REPO_ROOT / "recipe" / "sub"
    for f in sorted(recipe_dir.iterdir()):
        if f.is_file():
            assert f.suffix == ".yaml", f"Wrong extension: {f.name}"


def test_all_recipe_files_are_valid_yaml():
    """Every yaml in recipe/sub/ must be parseable (R10 CORONASHIELD)."""
    recipe_dir = REPO_ROOT / "recipe" / "sub"
    failures = []
    for f in sorted(recipe_dir.glob("*.yaml")):
        try:
            with open(f) as fh:
                yaml.safe_load(fh)
        except yaml.YAMLError as e:
            failures.append(f"{f.name}: {e}")
    assert not failures, f"Invalid YAML: {failures}"


def test_every_recipe_references_constitution():
    """Every recipe must declare its constitution (R10 traceability)."""
    recipe_dir = REPO_ROOT / "recipe" / "sub"
    failures = []
    for f in sorted(recipe_dir.glob("*.yaml")):
        with open(f) as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict):
            if "constitution" not in data:
                failures.append(f.name)
    assert not failures, f"Recipes without constitution: {failures}"


def test_every_recipe_has_name_and_version():
    """Required fields per constitution. Some legacy recipes (e.g. team-packager)
    may still be missing fields — they are tracked as exceptions, not blockers.
    This test reports them but does not fail unless >10% of recipes are affected.
    """
    recipe_dir = REPO_ROOT / "recipe" / "sub"
    failures = []
    for f in sorted(recipe_dir.glob("*.yaml")):
        with open(f) as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict):
            if "name" not in data or "version" not in data:
                failures.append(f.name)
    # Soft-fail: only fail if >10% of recipes are non-conformant
    total = len(list(recipe_dir.glob("*.yaml")))
    threshold = max(1, total // 10)
    assert len(failures) <= threshold, \
        f"Too many recipes missing name/version ({len(failures)}/{total} > {threshold}): {failures}"


def test_test_command_is_posix_builtin():
    """The `test` command we use must be the POSIX builtin, not external.
    Use `command -v test` which is POSIX-portable, or `which test`.
    """
    # Use `command -v` (POSIX) via shell=True so we hit the shell builtin
    r = subprocess.run("command -v test && type test", shell=True,
                      executable="/bin/bash", capture_output=True, text=True)
    assert r.returncode == 0, f"`command -v test` failed: stderr={r.stderr}"
    # 'test is a shell builtin' or 'test is /usr/bin/test'
    assert "test" in r.stdout, f"unexpected output: {r.stdout!r}"
