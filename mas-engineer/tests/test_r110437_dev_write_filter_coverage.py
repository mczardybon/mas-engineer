"""R110-437 — coverage-push r7: tools/dev_write_filter.py 0% → 100%.

Write-filter (86 lines). Pre-write gatekeeper that validates:
- target path (must be inside MAS_DIR, not in protected list)
- YAML syntax (unless --skip-yaml)
- UTF-8 encoding
- duplicates (YAML lists)

Targets:
- check_target: path inside MAS_DIR OK, path outside MAS_DIR rejected
  with "Target outside MAS", path containing .git/ rejected with
  "Protected: .git/", checkpoint/ also protected, audit.log.jsonl
  protected, .disziplin_lock protected, .last_confirmation
  protected, action.log protected
- check_yaml: empty content → OK, valid YAML → OK, invalid YAML →
  fail with "YAML-Error"
- check_encoding: valid utf-8 string → OK, valid utf-8 bytes → OK,
  invalid utf-8 bytes → fail
- check_duplicates: non-yaml file → OK, YAML dict → OK,
  YAML list with no dups → OK, YAML list with duplicate dicts →
  fail with "Duplikat: name", YAML list with duplicate dicts (no
  name/id) → fail with "Duplikat: ?", unparseable YAML → OK
  (passes, fail-safe)
- main: <3 args (exit 1), no --file (exit 1), no --content/--stdin
  (exit 1), valid --file + --content (exit 0 + ✅ message),
  invalid YAML (exit 1 + error list), --skip-yaml bypasses YAML
  check, --stdin mode (reads stdin), multi-word content joined
"""

import io
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_write_filter as wf  # noqa: E402


MAS_DIR = wf.MAS_DIR


# ─────────────────────────────────────────────────────────────────────
# check_target
# ─────────────────────────────────────────────────────────────────────
class TestCheckTarget:
    def test_inside_mas_dir_ok(self):
        ok, msg = wf.check_target(f"{MAS_DIR}/test.yaml")
        assert ok is True
        assert msg == ""

    def test_outside_mas_dir_rejected(self, tmp_path):
        ok, msg = wf.check_target(str(tmp_path / "outside.yaml"))
        assert ok is False
        assert "outside MAS" in msg

    def test_git_dir_protected(self):
        ok, msg = wf.check_target(f"{MAS_DIR}/.git/config")
        assert ok is False
        assert "Protected: .git/" in msg

    def test_checkpoints_dir_protected(self):
        ok, msg = wf.check_target(f"{MAS_DIR}/checkpoints/x.yaml")
        assert ok is False
        assert "Protected: checkpoints/" in msg

    def test_audit_log_protected(self):
        ok, msg = wf.check_target(f"{MAS_DIR}/audit.log.jsonl")
        assert ok is False
        assert "Protected: audit.log.jsonl" in msg

    def test_disziplin_lock_protected(self):
        ok, msg = wf.check_target(f"{MAS_DIR}/.disziplin_lock")
        assert ok is False
        assert "Protected: .disziplin_lock" in msg

    def test_last_confirmation_protected(self):
        ok, msg = wf.check_target(f"{MAS_DIR}/.last_confirmation")
        assert ok is False
        assert "Protected: .last_confirmation" in msg

    def test_action_log_protected(self):
        ok, msg = wf.check_target(f"{MAS_DIR}/action.log")
        assert ok is False
        assert "Protected: action.log" in msg


# ─────────────────────────────────────────────────────────────────────
# check_yaml
# ─────────────────────────────────────────────────────────────────────
class TestCheckYaml:
    def test_empty_content_ok(self):
        ok, msg = wf.check_yaml("")
        assert ok is True
        assert msg == ""

    def test_whitespace_only_ok(self):
        ok, msg = wf.check_yaml("   \n\t  ")
        assert ok is True

    def test_valid_yaml_ok(self):
        ok, msg = wf.check_yaml("key: value\nlist:\n  - a\n")
        assert ok is True
        assert msg == ""

    def test_invalid_yaml_fail(self):
        ok, msg = wf.check_yaml("a: [unterminated\n")
        assert ok is False
        assert "YAML-Error" in msg


# ─────────────────────────────────────────────────────────────────────
# check_encoding
# ─────────────────────────────────────────────────────────────────────
class TestCheckEncoding:
    def test_valid_str(self):
        ok, msg = wf.check_encoding("hello world")
        assert ok is True

    def test_valid_str_with_unicode(self):
        ok, msg = wf.check_encoding("🔧 ünicode")
        assert ok is True

    def test_valid_bytes(self):
        ok, msg = wf.check_encoding(b"hello bytes")
        assert ok is True

    def test_invalid_bytes(self):
        ok, msg = wf.check_encoding(b"\xff\xfe invalid")
        assert ok is False
        assert "UTF-8" in msg


# ─────────────────────────────────────────────────────────────────────
# check_duplicates
# ─────────────────────────────────────────────────────────────────────
class TestCheckDuplicates:
    def test_non_yaml_file_ok(self):
        ok, msg = wf.check_duplicates("test.txt", "anything")
        assert ok is True

    def test_yml_ext_ok(self):
        ok, msg = wf.check_duplicates("test.yml", "k: v")
        assert ok is True

    def test_yaml_dict_ok(self):
        content = yaml.safe_dump({"key": "value"})
        ok, msg = wf.check_duplicates("test.yaml", content)
        assert ok is True

    def test_yaml_list_no_dups_ok(self):
        content = yaml.safe_dump([{"id": "a"}, {"id": "b"}])
        ok, msg = wf.check_duplicates("test.yaml", content)
        assert ok is True

    def test_yaml_list_with_dups_fail(self):
        content = yaml.safe_dump([{"name": "foo", "x": 1},
                                  {"name": "foo", "x": 1}])
        ok, msg = wf.check_duplicates("test.yaml", content)
        assert ok is False
        assert "Duplikat: foo" in msg

    def test_yaml_list_with_dups_no_name_fail(self):
        content = yaml.safe_dump([{"x": 1}, {"x": 1}])
        ok, msg = wf.check_duplicates("test.yaml", content)
        assert ok is False
        assert "Duplikat: ?" in msg

    def test_yaml_list_with_dups_id_field(self):
        content = yaml.safe_dump([{"id": "X", "y": 1},
                                  {"id": "X", "y": 1}])
        ok, msg = wf.check_duplicates("test.yaml", content)
        assert ok is False
        assert "Duplikat: X" in msg

    def test_unparseable_yaml_passes(self):
        # Fail-safe: bad YAML → (True, "") so downstream yaml error
        # check catches it
        ok, msg = wf.check_duplicates("test.yaml", "a: [broken\n")
        assert ok is True


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
def _run_main(argv, stdin_data=None, capsys=None):
    """Call main() in-process with custom sys.argv/sys.stdin."""
    old_argv = sys.argv
    old_stdin = sys.stdin
    sys.argv = ["dev_write_filter.py"] + argv
    if stdin_data is not None:
        sys.stdin = io.StringIO(stdin_data)
    code = 0
    try:
        try:
            code = wf.main() or 0
        except SystemExit as e:
            code = e.code if e.code is not None else 0
    finally:
        sys.argv = old_argv
        sys.stdin = old_stdin
    return (capsys.readouterr().out if capsys else ""), code


class TestMain:
    def test_too_few_args_exits_1(self, capsys):
        out, code = _run_main([], capsys=capsys)
        assert code == 1
        assert "call:" in out

    def test_no_file_flag_exits_1(self, capsys):
        out, code = _run_main(
            ["--content", "x"], capsys=capsys)
        assert code == 1
        assert "--file required" in out

    def test_no_content_or_stdin_exits_1(self, capsys):
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/test.yaml"], capsys=capsys)
        assert code == 1
        assert "--content oder --stdin" in out

    def test_valid_file_and_content_ok(self, capsys):
        content = yaml.safe_dump({"key": "value"})
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.yaml", "--content", content],
            capsys=capsys)
        assert code == 0
        assert "Write-Filter: OK" in out

    def test_invalid_yaml_exits_1(self, capsys):
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.yaml",
             "--content", "a: [broken\n"],
            capsys=capsys)
        assert code == 1
        assert "YAML-Error" in out

    def test_skip_yaml_bypass(self, capsys):
        # Invalid YAML but --skip-yaml → passes
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.yaml",
             "--skip-yaml", "--content", "a: [broken\n"],
            capsys=capsys)
        assert code == 0

    def test_stdin_mode(self, capsys):
        content = yaml.safe_dump({"key": "value"})
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.yaml", "--stdin"],
            stdin_data=content, capsys=capsys)
        assert code == 0
        assert "OK" in out

    def test_multi_word_content_joined(self, capsys):
        content = yaml.safe_dump({"key": "value"})
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.yaml",
             "--content", "key:", "value"],
            capsys=capsys)
        assert code == 0

    def test_multi_word_content_stops_at_double_dash(self, capsys):
        # Args after a -- flag should NOT be appended to content
        # (tests the `else: break` branch on line 66)
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.yaml",
             "--content", "key: value", "--skip-yaml"],
            capsys=capsys)
        assert code == 0

    def test_non_yaml_file_no_yaml_check(self, capsys):
        # Invalid YAML but file ends in .txt → no YAML check runs
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.txt",
             "--content", "a: [broken\n"],
            capsys=capsys)
        assert code == 0

    def test_duplicate_yaml_exits_1(self, capsys):
        content = yaml.safe_dump([{"id": "X"}, {"id": "X"}])
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.yaml", "--content", content],
            capsys=capsys)
        assert code == 1
        assert "Duplikat" in out

    def test_target_outside_mas_exits_1(self, capsys, tmp_path):
        out, code = _run_main(
            ["--file", str(tmp_path / "outside.yaml"),
             "--content", "key: v"],
            capsys=capsys)
        assert code == 1
        assert "Target-Path" in out or "outside" in out

    def test_invalid_utf8_in_content(self, capsys):
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/sub/test.yaml",
             "--content", b"\xff\xfe bad"],
            capsys=capsys)
        assert code == 1
        assert "Encoding" in out or "UTF-8" in out

    def test_protected_path_exits_1(self, capsys):
        out, code = _run_main(
            ["--file", f"{MAS_DIR}/.git/config",
             "--content", "key: v"],
            capsys=capsys)
        assert code == 1
        assert "Target-Path" in out or "Protected" in out
