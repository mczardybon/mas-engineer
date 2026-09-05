"""
R110-345: coverage-push round 1 for tools/dev_im_finder_scan.py.

Targets the high-value pure-function helpers that are partially
covered by test_r110309_im_finder_scan_lib.py but have untested
branches:

  1. _is_common_value (L962-984): walks search_dirs, returns True
     if literal appears in 3+ files. Currently 0% covered.
  2. _is_path_excluded with _INCLUDE_EXTERNAL=True (L165):
     when --include-external-recipes is set, external recipes
     should NOT be excluded. Branch at L165 untested.
  3. _collect_scope_dirs (L109-130) CLI-arg branch and
     comma-separated env branch. (The env-var branch is
     covered by the ifs fixture's setup; we test the
     CLI-arg parsing here.)

Target: bump coverage from 25% to ~40% (additive 15pp).
"""
import sys
import os
import importlib
from pathlib import Path
import pytest

TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def ifs(tmp_path, monkeypatch):
    """Import dev_im_finder_scan with a sandboxed CWD (per R110-309).

    The module-level scan runs but is neutralized by
    SCAN_SCOPE=non-existent-dir.  The fixture's tmp_path is
    used for the search_dirs in TestIsCommonValue.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCAN_SCOPE", str(tmp_path / "no-such-dir"))
    monkeypatch.setenv("SEVERITY_FILTER", "critical,warning,info,error,medium,high,low,debug")
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_im_finder_scan", None)
    sys.modules.pop("dev_issue_db", None)
    mod = importlib.import_module("dev_im_finder_scan")
    yield mod
    sys.modules.pop("dev_im_finder_scan", None)
    sys.modules.pop("dev_issue_db", None)


class TestIsCommonValue:
    """Cover _is_common_value (L962-984)."""

    def test_is_common_value_true_when_3plus_hits(self, ifs, tmp_path):
        """If literal appears in 3+ files in search_dirs, return True."""
        for i in range(3):
            (tmp_path / f"file{i}.py").write_text("X = 'MAGIC_LITERAL_42'")
        result = ifs._is_common_value("MAGIC_LITERAL_42", [str(tmp_path)])
        assert result is True

    def test_is_common_value_false_when_fewer_than_3_hits(self, ifs, tmp_path):
        """If literal appears in <3 files, return False."""
        (tmp_path / "file0.py").write_text("X = 'MAGIC_LITERAL_42'")
        (tmp_path / "file1.py").write_text("Y = 'something else'")
        result = ifs._is_common_value("MAGIC_LITERAL_42", [str(tmp_path)])
        assert result is False

    def test_is_common_value_skips_pycache(self, ifs, tmp_path):
        """Files in __pycache__ should be skipped."""
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "file0.py").write_text("X = 'MAGIC_LITERAL_42'")
        (pycache / "file1.py").write_text("X = 'MAGIC_LITERAL_42'")
        (pycache / "file2.py").write_text("X = 'MAGIC_LITERAL_42'")
        result = ifs._is_common_value("MAGIC_LITERAL_42", [str(tmp_path)])
        assert result is False  # all 3 hits were in pycache

    def test_is_common_value_missing_search_dir(self, ifs, tmp_path):
        """Non-existent search_dir should be silently skipped (not raise)."""
        result = ifs._is_common_value(
            "ANYTHING", [str(tmp_path / "no-such-dir")]
        )
        assert result is False


class TestIsPathExcludedIncludeExternal:
    """Cover the _INCLUDE_EXTERNAL=True branch of _is_path_excluded (L165)."""

    def test_external_recipes_included_when_flag_set(self, ifs, monkeypatch):
        """When _INCLUDE_EXTERNAL is True, /.config/goose/recipes/ should
        NOT be excluded."""
        monkeypatch.setattr(ifs, "_INCLUDE_EXTERNAL", True)
        result = ifs._is_path_excluded("/home/user/.config/goose/recipes/x.yaml")
        assert result is False

    def test_external_recipes_excluded_by_default(self, ifs):
        """Default behavior: external recipes ARE excluded."""
        result = ifs._is_path_excluded("/home/user/.config/goose/recipes/x.yaml")
        assert result is True


class TestCollectScopeDirs:
    """Cover _collect_scope_dirs (L109-130) branches.

    _collect_scope_dirs reads sys.argv AND os.environ at call-time
    (not just import-time), so we can patch sys.argv with
    monkeypatch.setattr() and call directly.  The env-var branch
    is exercised by the ifs fixture.
    """

    def test_collect_scope_dirs_with_cli_arg(self, ifs, tmp_path, monkeypatch):
        """--scope=DIR CLI arg should be in the result."""
        d1 = tmp_path / "a"
        d1.mkdir()
        # _collect_scope_dirs reads sys.argv[1:] at call time
        saved_argv = sys.argv
        sys.argv = ["dev_im_finder_scan.py", f"--scope={d1}"]
        try:
            result = ifs._collect_scope_dirs()
            assert str(d1) in result
        finally:
            sys.argv = saved_argv

    def test_collect_scope_dirs_with_multiple_cli_args(self, ifs, tmp_path, monkeypatch):
        """Multiple --scope=DIR CLI args should all appear in result."""
        d1 = tmp_path / "a"
        d2 = tmp_path / "b"
        d1.mkdir()
        d2.mkdir()
        saved_argv = sys.argv
        sys.argv = [
            "dev_im_finder_scan.py",
            f"--scope={d1}",
            f"--scope={d2}",
        ]
        try:
            result = ifs._collect_scope_dirs()
            assert str(d1) in result
            assert str(d2) in result
        finally:
            sys.argv = saved_argv

    def test_collect_scope_dirs_comma_separated_env(self, ifs, tmp_path, monkeypatch):
        """SCAN_SCOPE=dir1,dir2 env should be split on comma."""
        d1 = tmp_path / "x"
        d2 = tmp_path / "y"
        d1.mkdir()
        d2.mkdir()
        monkeypatch.setenv("SCAN_SCOPE", f"{d1},{d2}")
        # Clear CLI args to ensure env-only path is tested
        saved_argv = sys.argv
        sys.argv = ["dev_im_finder_scan.py"]
        try:
            result = ifs._collect_scope_dirs()
            assert str(d1) in result
            assert str(d2) in result
        finally:
            sys.argv = saved_argv
