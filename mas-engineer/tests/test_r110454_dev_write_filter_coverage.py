"""R110-454 — coverage-push r8: tools/dev_write_filter.py 0% → 100%.

Write filter (content check before writing). Called from
gatekeeper. Checks: Target-Path, YAML-Syntax, Encoding,
Duplicates.

Targets:
- check_target(file): abspath must start with MAS_DIR; reject
  if ".git/", "checkpoints/", "audit.log.jsonl",
  ".disziplin_lock", ".last_confirmation", "action.log" in
  path. Returns (ok:bool, msg:str).
- check_yaml(content): empty/strip-empty → ok; else yaml.safe_load
  → ok; on Exception → (False, "YAML-Error: ...").
- check_encoding(content): str → encode utf-8; bytes → decode
  utf-8; UnicodeError → (False, "No valides UTF-8").
- check_duplicates(file, content): non-yaml → ok; yaml list with
  duplicate dict items (sorted_keys json) → (False, "Duplikat:
  <name>"). Non-list, yaml error, etc → ok.
- main(): missing args → exit 1; no --file → exit 1; --content
  multi-arg concat or --stdin; --skip-yaml; builds checks list
  (Target-Path, Encoding, YAML-if-yaml-and-not-skip, Duplikate);
  on any fail → print + exit 1; else → print OK + exit 0.
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_write_filter as wf  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# check_target
# ─────────────────────────────────────────────────────────────────────
class TestCheckTarget:
    def test_inside_repo(self, tmp_path):
        # MAS_DIR is repo root, so any path under repo → ok
        target = str(Path(wf.MAS_DIR) / "foo.yaml")
        ok, msg = wf.check_target(target)
        assert ok is True
        assert msg == ""

    def test_outside_repo(self, tmp_path):
        target = str(tmp_path / "outside.yaml")
        ok, msg = wf.check_target(target)
        assert ok is False
        assert "outside MAS" in msg

    def test_protected_git(self):
        target = str(Path(wf.MAS_DIR) / "x" / ".git" / "config")
        ok, msg = wf.check_target(target)
        assert ok is False
        assert "Protected" in msg
        assert ".git/" in msg

    def test_protected_checkpoints(self):
        target = str(Path(wf.MAS_DIR) / "x" / "checkpoints" / "x")
        ok, msg = wf.check_target(target)
        assert ok is False
        assert "checkpoints/" in msg

    def test_protected_audit_log(self):
        target = str(Path(wf.MAS_DIR) / "audit.log.jsonl")
        ok, msg = wf.check_target(target)
        assert ok is False
        assert "audit.log.jsonl" in msg

    def test_protected_disziplin_lock(self):
        target = str(Path(wf.MAS_DIR) / ".disziplin_lock")
        ok, msg = wf.check_target(target)
        assert ok is False

    def test_protected_last_confirmation(self):
        target = str(Path(wf.MAS_DIR) / ".last_confirmation")
        ok, msg = wf.check_target(target)
        assert ok is False

    def test_protected_action_log(self):
        target = str(Path(wf.MAS_DIR) / "action.log")
        ok, msg = wf.check_target(target)
        assert ok is False


# ─────────────────────────────────────────────────────────────────────
# check_yaml
# ─────────────────────────────────────────────────────────────────────
class TestCheckYaml:
    def test_empty_content(self):
        ok, msg = wf.check_yaml("")
        assert ok is True

    def test_whitespace_only(self):
        ok, msg = wf.check_yaml("   \n\t  ")
        assert ok is True

    def test_valid_yaml(self):
        ok, msg = wf.check_yaml("foo: bar\nbaz: 1")
        assert ok is True

    def test_valid_yaml_list(self):
        ok, msg = wf.check_yaml("- a\n- b")
        assert ok is True

    def test_invalid_yaml(self):
        ok, msg = wf.check_yaml("foo: bar\n  bad indent:\n- x")
        assert ok is False
        assert "YAML-Error" in msg


# ─────────────────────────────────────────────────────────────────────
# check_encoding
# ─────────────────────────────────────────────────────────────────────
class TestCheckEncoding:
    def test_str_ok(self):
        ok, msg = wf.check_encoding("hello äöü")
        assert ok is True

    def test_bytes_ok(self):
        ok, msg = wf.check_encoding(b"hello")
        assert ok is True

    def test_bad_utf8_bytes(self):
        ok, msg = wf.check_encoding(b"\xff\xfe invalid")
        assert ok is False
        assert "UTF-8" in msg


# ─────────────────────────────────────────────────────────────────────
# check_duplicates
# ─────────────────────────────────────────────────────────────────────
class TestCheckDuplicates:
    def test_non_yaml_file(self):
        ok, msg = wf.check_duplicates("foo.txt", "anything")
        assert ok is True

    def test_yaml_no_list(self):
        ok, msg = wf.check_duplicates("foo.yaml", "x: 1\ny: 2")
        assert ok is True

    def test_yaml_list_unique(self):
        ok, msg = wf.check_duplicates(
            "foo.yaml",
            "- name: a\n- name: b")
        assert ok is True

    def test_yaml_list_duplicate(self):
        content = ("- name: a\n  score: 1\n"
                   "- name: b\n  score: 2\n"
                   "- name: a\n  score: 1")
        ok, msg = wf.check_duplicates("foo.yaml", content)
        assert ok is False
        assert "Duplikat" in msg
        assert "a" in msg

    def test_yaml_invalid_silent_ok(self):
        # Bare except: returns ok
        ok, msg = wf.check_duplicates(
            "foo.yaml", "[unbalanced")
        assert ok is True

    def test_yaml_list_item_not_dict(self):
        # Items that aren't dicts → skipped
        ok, msg = wf.check_duplicates(
            "foo.yaml", "- a\n- b\n- c")
        assert ok is True

    def test_yaml_yml_extension(self):
        ok, msg = wf.check_duplicates(
            "foo.yml", "- name: x\n- name: x")
        assert ok is False


# ─────────────────────────────────────────────────────────────────────
# main  (subprocess for argparse path)
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_args(self):
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py'],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 1
        assert "call:" in r.stdout

    def test_no_file(self):
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--content', 'x'],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 1
        assert "--file required" in r.stdout

    def test_no_content_or_stdin(self, tmp_path):
        target = str(Path(wf.MAS_DIR) / "x.yaml")
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 1
        assert "--content oder --stdin" in r.stdout

    def test_success_yaml(self):
        target = str(Path(wf.MAS_DIR) / "x.yaml")
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target,
             '--content', 'foo: bar'],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_success_with_stdin(self):
        target = str(Path(wf.MAS_DIR) / "x.yaml")
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target,
             '--stdin'],
            input="foo: bar",
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_target_fails(self, tmp_path):
        target = str(tmp_path / "outside.yaml")
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target,
             '--content', 'foo: bar'],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 1
        assert "Target-Path" in r.stdout

    def test_invalid_yaml(self):
        target = str(Path(wf.MAS_DIR) / "x.yaml")
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target,
             '--content', 'foo: bar\n  bad: - x'],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 1
        assert "YAML" in r.stdout

    def test_skip_yaml(self):
        target = str(Path(wf.MAS_DIR) / "x.yaml")
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target,
             '--content', 'this is not yaml {{{}',
             '--skip-yaml'],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0

    def test_skip_yaml_non_yaml_file(self):
        # Non-yaml file doesn't trigger yaml check anyway
        target = str(Path(wf.MAS_DIR) / "x.txt")
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target,
             '--content', 'anything'],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0

    def test_duplicate_yaml(self):
        target = str(Path(wf.MAS_DIR) / "x.yaml")
        content = "- name: a\n- name: a"
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target,
             '--content', content],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 1
        assert "Duplikat" in r.stdout

    def test_multi_arg_content(self):
        # Content split across multiple argv entries (the
        # `for j in range(...)` loop concatenates them)
        target = str(Path(wf.MAS_DIR) / "x.yaml")
        r = subprocess.run(
            ['python3', 'tools/dev_write_filter.py',
             '--file', target,
             '--content', 'foo:', 'bar', '--skip-yaml'],
            capture_output=True, text=True, timeout=10,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        # Either ok (skip-yaml branch) or fail (yaml parse error on
        # combined "foo: bar"). Both cover the multi-arg concat path.
        # We expect OK because --skip-yaml is parsed.
        assert r.returncode == 0
