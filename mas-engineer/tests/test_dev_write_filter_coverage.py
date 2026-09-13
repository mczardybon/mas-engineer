#!/usr/bin/env python3
"""
R110-521: Coverage test for tools/dev_write_filter.py (86 lines, 0% → 100%).

Context: dev_write_filter.py is the gatekeeper-side content check
that runs BEFORE writing a file. It validates:

  1. check_target(file) — file path is inside MAS_DIR and not in
     protected list (.git/, checkpoints/, audit.log.jsonl,
     .disziplin_lock, .last_confirmation, action.log).

  2. check_yaml(content) — content parses as YAML. Empty content is
     treated as valid.

  3. check_encoding(content) — content encodes/decodes as UTF-8
     (handles str and bytes).

  4. check_duplicates(file, content) — for .yaml/.yml files with a
     YAML list, checks no two dicts are JSON-canonical duplicates.
     Non-list YAML, non-yaml files, and YAML parse errors → OK.

__main__ dispatch:
  --file PATH [--content TEXT | --stdin] [--skip-yaml]
  Errors:
    - < 3 args → exit 1
    - no --file → exit 1
    - no --content and no --stdin → exit 1
  On success → exit 0; any check failure → exit 1 with detail.

Branch coverage strategy: every check's True/False path, every
protected substring, both content sources, --skip-yaml path, and
each main() error branch.
"""

import json
import os
import runpy
import sys

import pytest

import tools.dev_write_filter as wf  # noqa: E402

# MAS_DIR is the project root. Targets must be inside it.
MAS_DIR = wf.MAS_DIR

# A scratch dir inside MAS_DIR for file checks (won't be created
# unless a test writes to it; check_target only checks the path).
SCRATCH_SUBDIR = os.path.join(MAS_DIR, "tests", ".write_filter_scratch")


# ─── check_target ─────────────────────────────────────────────────

def test_check_target_inside_mas_dir_returns_ok():
    """Covers lines 18-23: path inside MAS_DIR, no protected
    substring → (True, '')."""
    ok, msg = wf.check_target(os.path.join(SCRATCH_SUBDIR, "ok.txt"))
    assert ok is True
    assert msg == ""


def test_check_target_outside_mas_dir_returns_error():
    """Covers line 19: abs_f doesn't start with MAS_DIR abspath →
    False with 'outside MAS' message."""
    ok, msg = wf.check_target("/tmp/somewhere_outside.txt")
    assert ok is False
    assert "outside MAS" in msg


def test_check_target_rejects_git_subdir():
    """Covers line 22: '.git/' substring → False."""
    ok, msg = wf.check_target(os.path.join(MAS_DIR, ".git", "config"))
    assert ok is False
    assert "Protected" in msg
    assert ".git/" in msg


def test_check_target_rejects_checkpoints_subdir():
    """Covers line 22: 'checkpoints/' substring → False."""
    ok, msg = wf.check_target(os.path.join(MAS_DIR, "checkpoints", "snap.json"))
    assert ok is False
    assert "checkpoints/" in msg


def test_check_target_rejects_audit_log_jsonl():
    """Covers line 22: 'audit.log.jsonl' substring → False."""
    ok, msg = wf.check_target(os.path.join(MAS_DIR, "audit.log.jsonl"))
    assert ok is False
    assert "audit.log.jsonl" in msg


def test_check_target_rejects_disziplin_lock():
    """Covers line 22: '.disziplin_lock' substring → False."""
    ok, msg = wf.check_target(os.path.join(MAS_DIR, ".disziplin_lock"))
    assert ok is False
    assert ".disziplin_lock" in msg


def test_check_target_rejects_last_confirmation():
    """Covers line 22: '.last_confirmation' substring → False."""
    ok, msg = wf.check_target(os.path.join(MAS_DIR, ".last_confirmation"))
    assert ok is False
    assert ".last_confirmation" in msg


def test_check_target_rejects_action_log():
    """Covers line 22: 'action.log' substring → False."""
    ok, msg = wf.check_target(os.path.join(MAS_DIR, "action.log"))
    assert ok is False
    assert "action.log" in msg


# ─── check_yaml ───────────────────────────────────────────────────

def test_check_yaml_empty_content_is_valid():
    """Covers line 26: content.strip() empty → True."""
    ok, msg = wf.check_yaml("")
    assert ok is True
    assert msg == ""


def test_check_yaml_whitespace_only_is_valid():
    """Covers line 26: whitespace-only treated as empty → True."""
    ok, msg = wf.check_yaml("   \n\t  \n")
    assert ok is True
    assert msg == ""


def test_check_yaml_valid_yaml_returns_ok():
    """Covers line 28: yaml.safe_load succeeds → True."""
    ok, msg = wf.check_yaml("a: 1\nb: 2\n")
    assert ok is True
    assert msg == ""


def test_check_yaml_invalid_yaml_returns_error():
    """Covers lines 29-30: yaml.safe_load raises → False."""
    ok, msg = wf.check_yaml("a: 1\n  bad: : :\n[unclosed")
    assert ok is False
    assert "YAML-Error" in msg


# ─── check_encoding ───────────────────────────────────────────────

def test_check_encoding_str_content_valid_utf8():
    """Covers line 34 True branch: isinstance(content, str) →
    encode('utf-8')."""
    ok, msg = wf.check_encoding("hello\nworld")
    assert ok is True
    assert msg == ""


def test_check_encoding_bytes_content_valid_utf8():
    """Covers line 35 False branch: not str → bytes decode('utf-8')."""
    ok, msg = wf.check_encoding("hello\nworld".encode("utf-8"))
    assert ok is True
    assert msg == ""


def test_check_encoding_str_with_unicode_valid():
    """Covers line 34: str with non-ASCII unicode chars → OK."""
    ok, msg = wf.check_encoding("über café 🎉")
    assert ok is True
    assert msg == ""


def test_check_encoding_bytes_invalid_utf8_returns_error():
    """Covers line 37-38: UnicodeError on decode → False."""
    ok, msg = wf.check_encoding(b"\xff\xfe\x00bad")
    assert ok is False
    assert "No valides UTF-8" in msg


# ─── check_duplicates ─────────────────────────────────────────────

def test_check_duplicates_non_yaml_file_returns_ok(tmp_path):
    """Covers line 41 True branch: file doesn't end with .yaml/.yml
    → (True, '')."""
    ok, msg = wf.check_duplicates(str(tmp_path / "file.txt"), "any content")
    assert ok is True
    assert msg == ""


def test_check_duplicates_yaml_with_no_dupes_returns_ok(tmp_path):
    """Covers lines 42-53: yaml list, all unique dicts → True."""
    content = "- name: a\n  v: 1\n- name: b\n  v: 2\n"
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yaml"), content)
    assert ok is True


def test_check_duplicates_yaml_with_duplicate_returns_error(tmp_path):
    """Covers line 49-51: duplicate json-canonical dict → False."""
    content = "- name: a\n  v: 1\n- name: a\n  v: 1\n"
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yaml"), content)
    assert ok is False
    assert "Duplikat" in msg
    assert "a" in msg


def test_check_duplicates_yaml_uses_name_field(tmp_path):
    """Covers line 50 True branch: item.get('name')."""
    content = "- id: 1\n- id: 1\n"
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yaml"), content)
    assert ok is False
    assert "1" in msg


def test_check_duplicates_yaml_uses_id_field_when_no_name(tmp_path):
    """Covers line 50 False branch: no name, falls back to 'id'."""
    content = "- id: 1\n- id: 1\n"
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yaml"), content)
    assert ok is False


def test_check_duplicates_yaml_no_name_no_id_returns_questionmark(tmp_path):
    """Covers line 50 '?' fallback: neither name nor id present."""
    content = "- x: 1\n- x: 1\n"
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yaml"), content)
    assert ok is False
    assert "?" in msg


def test_check_duplicates_yaml_not_a_list_returns_ok(tmp_path):
    """Covers line 44 False branch: parsed data is not a list (e.g.
    a dict)."""
    content = "a: 1\nb: 2\n"
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yaml"), content)
    assert ok is True


def test_check_duplicates_yaml_parse_error_returns_ok(tmp_path):
    """Covers line 54: yaml.safe_load raises → (True, '') via broad
    except."""
    content = "invalid: : : yaml\n"
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yaml"), content)
    assert ok is True


def test_check_duplicates_yaml_yml_extension_also_checked(tmp_path):
    """Covers line 41 False branch: .yml suffix → duplicate detection
    runs."""
    content = "- name: x\n- name: x\n"
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yml"), content)
    assert ok is False
    assert "Duplikat" in msg


def test_check_duplicates_yaml_skips_non_dict_items(tmp_path):
    """Covers line 47 False branch: item is not a dict → skip."""
    content = "- 1\n- 2\n- 3\n"  # list of scalars, not dicts
    ok, msg = wf.check_duplicates(str(tmp_path / "f.yaml"), content)
    assert ok is True


# ─── main() dispatch ──────────────────────────────────────────────

# All main() tests use SCRATCH_SUBDIR since the file path must be
# inside MAS_DIR or check_target fails. Tests don't actually create
# the file — check_target only validates the path string.

def _run_main(args, stdin_data=None, monkeypatch=None):
    """Helper: run dev_write_filter.py main() via runpy in-process
    so coverage is captured. monkeypatch is required to set sys.argv.
    """
    if monkeypatch is None:
        raise RuntimeError("monkeypatch required for in-process run")
    monkeypatch.setattr(sys, "argv", ["dev_write_filter.py", *args])
    if stdin_data is not None:
        import io
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))
    try:
        runpy.run_path(wf.__file__, run_name="__main__")
    except SystemExit as e:
        return e.code
    return 0


def test_main_no_args_exits_1(monkeypatch):
    """Covers line 57-58: len(argv) < 3 → exit 1."""
    rc = _run_main([], monkeypatch=monkeypatch)
    assert rc == 1


def test_main_no_file_flag_exits_1(monkeypatch):
    """Covers line 59-60: --file not in argv → exit 1."""
    rc = _run_main(["--content", "x"], monkeypatch=monkeypatch)
    assert rc == 1


def test_main_no_content_or_stdin_exits_1(monkeypatch):
    """Covers line 69-70: --content and --stdin both absent → exit 1."""
    rc = _run_main(["--file", os.path.join(SCRATCH_SUBDIR, "f.yaml")],
                   monkeypatch=monkeypatch)
    assert rc == 1


def test_main_content_valid_file_exits_0(monkeypatch, capsys):
    """Covers lines 62-66 + 72-83 success path: --content with valid
    YAML, --file inside MAS_DIR → exit 0."""
    target = os.path.join(SCRATCH_SUBDIR, "ok.yaml")
    rc = _run_main([
        "--file", target,
        "--content", "key: value\n",
    ], monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Write-Filter: OK" in out


def test_main_stdin_content_valid_file_exits_0(monkeypatch, capsys):
    """Covers line 67-68: --stdin path."""
    target = os.path.join(SCRATCH_SUBDIR, "ok.yaml")
    rc = _run_main([
        "--file", target,
        "--stdin",
    ], stdin_data="a: 1\n", monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert rc == 0


def test_main_collects_multi_arg_content(monkeypatch):
    """Covers lines 64-66: --content followed by multiple non-flag
    args are concatenated with ' '. Stops at next --flag."""
    target = os.path.join(SCRATCH_SUBDIR, "ok.yaml")
    rc = _run_main([
        "--file", target,
        "--content", "a:",
        "1",
        "b:", "2",
        "--skip-yaml",
    ], monkeypatch=monkeypatch)
    assert rc == 0


def test_main_skip_yaml_skips_yaml_check(monkeypatch):
    """Covers line 75 False branch (skip_yaml=True): YAML check is
    NOT run, even for .yaml files. We pass invalid YAML and expect
    success because we skip it."""
    target = os.path.join(SCRATCH_SUBDIR, "ok.yaml")
    rc = _run_main([
        "--file", target,
        "--content", "invalid: : : yaml\n",
        "--skip-yaml",
    ], monkeypatch=monkeypatch)
    assert rc == 0


def test_main_non_yaml_extension_no_yaml_check(monkeypatch):
    """Covers line 75 False branch: file doesn't end with .yaml/.yml
    → YAML check NOT run even without --skip-yaml."""
    target = os.path.join(SCRATCH_SUBDIR, "ok.txt")
    rc = _run_main([
        "--file", target,
        "--content", "this is not yaml but it's a .txt file",
    ], monkeypatch=monkeypatch)
    assert rc == 0


def test_main_target_outside_mas_exits_1(monkeypatch, capsys):
    """Covers line 73 check_target False branch: outside MAS_DIR →
    'Target-Path:' error, exit 1."""
    rc = _run_main([
        "--file", "/etc/passwd",
        "--content", "x",
    ], monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert rc == 1
    assert "Target-Path" in out


def test_main_yaml_syntax_error_exits_1(monkeypatch, capsys):
    """Covers line 75 + check_yaml False branch: invalid YAML →
    'YAML:' error, exit 1."""
    target = os.path.join(SCRATCH_SUBDIR, "bad.yaml")
    rc = _run_main([
        "--file", target,
        "--content", "invalid: : : yaml\n",
    ], monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert rc == 1
    assert "YAML" in out


def test_main_duplicate_in_yaml_exits_1(monkeypatch, capsys):
    """Covers line 76 check_duplicates False branch: list with dup
    → 'Duplikate:' error."""
    target = os.path.join(SCRATCH_SUBDIR, "dup.yaml")
    rc = _run_main([
        "--file", target,
        "--content", "- name: a\n- name: a\n",
    ], monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert rc == 1
    assert "Duplikate" in out


def test_main_multiple_errors_reported(monkeypatch, capsys):
    """Covers lines 77-81: multiple check failures → list of errors
    printed. Use invalid YAML with a file inside MAS_DIR to ensure
    check_target passes but YAML check fails."""
    target = os.path.join(SCRATCH_SUBDIR, "multi.yaml")
    rc = _run_main([
        "--file", target,
        "--content", "invalid: : : yaml\n",
    ], monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert rc == 1
    assert "YAML" in out
