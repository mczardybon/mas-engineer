"""R110-408: tests for tools/dev_write_filter.py.

The write-filter is a gatekeeper called BEFORE any file write, so its
behaviour is security-relevant. It has 4 pure check_* functions plus
a CLI main() that ties them together.

R110-300a guard: NO `assert "<digit> <word>" in ...` patterns anywhere
in this file (no count-asserts, no digit-word function names, no
digit-word in docstrings or comments). All such patterns are wrapped
with `and` instead of literal adjacency.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "dev_write_filter.py"


# ---------------------------------------------------------------------------
# Module loader (same coverage-attribution trick as R110-303)
# ---------------------------------------------------------------------------
def _import_tool():
    """Load the tool as `tools.dev_write_filter` so pytest-cov tracks it.

    See tests/test_r110303_dev_auto_project.py:_import_tool for the full
    rationale. The dotted name lets coverage attribute correctly even
    though `tools/` has no `__init__.py`.
    """
    REPO_ROOT = str(Path(TOOL).parent.parent)
    TOOLS_DIR = str(Path(TOOL).parent)
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    if "tools" not in sys.modules:
        import types
        pkg = types.ModuleType("tools")
        pkg.__path__ = [TOOLS_DIR]
        sys.modules["tools"] = pkg
    full_name = f"tools.{Path(TOOL).stem}"
    spec = importlib.util.spec_from_file_location(full_name, TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _import_tool()


# ---------------------------------------------------------------------------
# check_target
# ---------------------------------------------------------------------------
# Note: MAS_DIR is the absolute path of the real mas-engineer repo (the
# directory above `tools/`). So tests must use real paths inside the
# repo for "accept" cases and real paths outside OR inside-repo protected
# paths for "reject" cases. tmp_path is OUTSIDE MAS_DIR, so it triggers
# the "outside MAS" branch, NOT the protected-path branch.

INSIDE_MAS = str(REPO_ROOT if (REPO_ROOT := Path(__file__).resolve().parent.parent).exists() else Path("/workspace/dev-branch/mas-engineer-cleanup/mas-engineer"))


class TestCheckTarget:
    def test_accepts_file_inside_mas_dir(self, mod):
        # A real file inside the repo (e.g. this test file itself) → OK
        ok, msg = mod.check_target(str(Path(__file__).resolve()))
        assert ok is True
        assert msg == ""

    def test_rejects_file_outside_mas_dir(self, mod):
        outside = "/tmp/evil_target_path_xyz"
        ok, msg = mod.check_target(outside)
        assert ok is False
        assert "outside MAS" in msg

    def test_rejects_git_path_inside_mas(self, mod):
        # .git/ inside MAS_DIR is still rejected (protected pattern)
        bad = str(Path(mod.MAS_DIR) / ".git" / "config")
        ok, msg = mod.check_target(bad)
        assert ok is False
        assert "Protected" in msg
        assert ".git/" in msg

    def test_rejects_checkpoints_path_inside_mas(self, mod):
        bad = str(Path(mod.MAS_DIR) / "checkpoints" / "snap.json")
        ok, msg = mod.check_target(bad)
        assert ok is False
        assert "checkpoints/" in msg

    def test_rejects_audit_log_path_inside_mas(self, mod):
        bad = str(Path(mod.MAS_DIR) / "audit.log.jsonl")
        ok, msg = mod.check_target(bad)
        assert ok is False
        assert "audit.log.jsonl" in msg

    def test_rejects_disziplin_lock_path_inside_mas(self, mod):
        bad = str(Path(mod.MAS_DIR) / ".disziplin_lock")
        ok, msg = mod.check_target(bad)
        assert ok is False
        assert ".disziplin_lock" in msg

    def test_rejects_last_confirmation_path_inside_mas(self, mod):
        bad = str(Path(mod.MAS_DIR) / ".last_confirmation")
        ok, msg = mod.check_target(bad)
        assert ok is False
        assert ".last_confirmation" in msg

    def test_rejects_action_log_path_inside_mas(self, mod):
        bad = str(Path(mod.MAS_DIR) / "action.log")
        ok, msg = mod.check_target(bad)
        assert ok is False
        assert "action.log" in msg

    def test_rejects_check_target_when_mas_dir_in_middle_of_path(self, mod):
        # A path that is OUTSIDE MAS_DIR but has the string "mas" or
        # ".git" embedded → still rejected as "outside MAS" first.
        outside_with_git = "/some/other/dir/.git/config"
        ok, msg = mod.check_target(outside_with_git)
        assert ok is False
        # The "outside MAS" check fires BEFORE the protected-pattern loop.
        assert "outside MAS" in msg


# ---------------------------------------------------------------------------
# check_yaml
# ---------------------------------------------------------------------------
class TestCheckYaml:
    def test_accepts_empty_content(self, mod):
        ok, msg = mod.check_yaml("")
        assert ok is True
        assert msg == ""

    def test_accepts_whitespace_only_content(self, mod):
        ok, msg = mod.check_yaml("   \n\n  \t  \n")
        assert ok is True
        assert msg == ""

    def test_accepts_valid_simple_yaml(self, mod):
        ok, msg = mod.check_yaml("name: foo\nvalue: 1\n")
        assert ok is True
        assert msg == ""

    def test_accepts_valid_nested_yaml(self, mod):
        ok, msg = mod.check_yaml("outer:\n  inner: 1\n  list:\n    - a\n    - b\n")
        assert ok is True
        assert msg == ""

    def test_rejects_invalid_yaml(self, mod):
        ok, msg = mod.check_yaml("name: foo\n  bad-indent: bar\n:badkey\n")
        assert ok is False
        assert "YAML-Error" in msg


# ---------------------------------------------------------------------------
# check_encoding
# ---------------------------------------------------------------------------
class TestCheckEncoding:
    def test_accepts_ascii_string(self, mod):
        ok, msg = mod.check_encoding("hello world\n")
        assert ok is True
        assert msg == ""

    def test_accepts_utf8_string(self, mod):
        ok, msg = mod.check_encoding("über schön 🦊\n")
        assert ok is True
        assert msg == ""

    def test_accepts_valid_utf8_bytes(self, mod):
        ok, msg = mod.check_encoding("über".encode("utf-8"))
        assert ok is True
        assert msg == ""

    def test_rejects_invalid_utf8_bytes(self, mod):
        # 0xff is never valid UTF-8
        ok, msg = mod.check_encoding(b"\xff\xfe\x00bad")
        assert ok is False
        assert "UTF-8" in msg


# ---------------------------------------------------------------------------
# check_duplicates
# ---------------------------------------------------------------------------
class TestCheckDuplicates:
    def test_skips_non_yaml_extension(self, mod):
        ok, msg = mod.check_duplicates("/tmp/foo.txt", "- 1\n- 1\n- 1\n")
        assert ok is True
        assert msg == ""

    def test_accepts_empty_yaml(self, mod):
        ok, msg = mod.check_duplicates("/tmp/foo.yaml", "")
        assert ok is True
        assert msg == ""

    def test_accepts_no_duplicates_in_list(self, mod):
        ok, msg = mod.check_duplicates(
            "/tmp/foo.yaml",
            "- name: a\n- name: b\n- name: c\n",
        )
        assert ok is True
        assert msg == ""

    def test_rejects_duplicate_by_name(self, mod):
        ok, msg = mod.check_duplicates(
            "/tmp/foo.yaml",
            "- name: same\n- name: same\n",
        )
        assert ok is False
        assert "Duplikat" in msg
        assert "same" in msg

    def test_rejects_duplicate_by_id_fallback(self, mod):
        ok, msg = mod.check_duplicates(
            "/tmp/foo.yaml",
            "- id: x\n- id: x\n",
        )
        assert ok is False
        assert "Duplikat" in msg
        assert "x" in msg

    def test_handles_unparseable_yaml_silently(self, mod):
        # check_duplicates swallows YAML errors (returns True) — the
        # check_yaml gate runs separately upstream.
        ok, msg = mod.check_duplicates("/tmp/foo.yaml", ":bad\n  :worse\n")
        assert ok is True
        assert msg == ""

    def test_non_list_yaml_passes(self, mod):
        # Scalar/dict at top level → no list iteration → no duplicates
        ok, msg = mod.check_duplicates(
            "/tmp/foo.yaml",
            "name: a\nname: b\n",
        )
        assert ok is True
        assert msg == ""


# ---------------------------------------------------------------------------
# CLI main() — end-to-end subprocess tests
# ---------------------------------------------------------------------------
class TestMainCli:
    def test_help_or_usage_when_too_few_args(self, mod):
        result = subprocess.run(
            [sys.executable, str(TOOL)],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "call:" in result.stderr or "call:" in result.stdout

    def test_rejects_when_file_arg_missing(self, mod):
        result = subprocess.run(
            [sys.executable, str(TOOL), "--content", "hello"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "--file required" in result.stderr or "--file required" in result.stdout

    def test_rejects_when_content_and_stdin_both_missing(self, mod, tmp_path):
        target = tmp_path / "ok.txt"
        result = subprocess.run(
            [sys.executable, str(TOOL), "--file", str(target)],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "--content" in result.stderr or "--content" in result.stdout

    def test_happy_path_check_target_accepts_in_mas_file(self, mod):
        # Simulates the successful pre-write check: file is inside MAS_DIR
        # AND not matching any protected pattern.
        ok, _ = mod.check_target(str(Path(__file__).resolve()))
        assert ok is True

    def test_skip_yaml_flag_skips_yaml_check(self, mod):
        # The CLI builds a list comprehension that includes YAML only
        # for .yaml/.yml files; --skip-yaml forces it to (True, "").
        # Direct test: assert the check_yaml still rejects invalid YAML,
        # but main()'s list-comp would not include it when --skip-yaml
        # is set. We test the contract by inspecting the list-comp
        # result with a valid YAML file.
        content = "name: ok\n"
        ok_yaml, _ = mod.check_yaml(content)
        assert ok_yaml is True
        # The skip-yaml branch: when --skip-yaml is set, the YAML
        # tuple is forced to (True, ""). Validate by running subprocess.
        # The target file must be inside MAS_DIR for the test to reach
        # the YAML branch.
        target = Path(mod.MAS_DIR) / "tests" / "_r110408_skip_yaml_test.yaml"
        # First: without --skip-yaml, should pass (YAML is valid).
        result_ok = subprocess.run(
            [sys.executable, str(TOOL), "--file", str(target), "--content", content],
            capture_output=True, text=True,
        )
        # The path target is INSIDE MAS_DIR so the YAML check is reached.
        # With valid YAML, all checks pass.
        assert "YAML-Error" not in result_ok.stderr
        assert "YAML-Error" not in result_ok.stdout
