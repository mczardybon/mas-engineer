"""
test_r110302_dev_write_filter.py — R110-302 Coverage Sprint for
tools/dev_write_filter.py.

Target: dev_write_filter.py (87 lines, 62 stmts).

R110-302 imports the tool as a library and tests:

  - check_target()      (3 branches:
                          • path OUTSIDE MAS_DIR → (False, "Target ... outside MAS")
                          • path INSIDE MAS_DIR but matches a protected
                            substring (.git/, checkpoints/, audit.log.jsonl,
                            .disziplin_lock, .last_confirmation, action.log)
                            → (False, "Protected: <v>")
                          • path inside MAS_DIR, no protected substr → (True, ""))
  - check_yaml()        (3 branches:
                          • empty / whitespace-only content → (True, "")
                          • valid yaml → (True, "")
                          • invalid yaml → (False, "YAML-Error: ..."))
  - check_encoding()    (3 branches:
                          • str content → (True, "")  (encode succeeds)
                          • bytes content → (True, "")  (decode succeeds)
                          • bytes with invalid UTF-8 → (False, "No valides UTF-8"))
  - check_duplicates()  (multiple branches:
                          • file not ending in .yaml/.yml → (True, "")
                          • yaml with duplicates in list-of-dicts → (False, "Duplikat: <name|id>")
                          • yaml with no duplicates → (True, "")
                          • yaml with list of non-dicts → (True, "")
                          • yaml non-list (mapping) → (True, "")
                          • yaml that fails to parse → (True, "")  [bare-except swallows])
  - main()              (full CLI test matrix:
                          • no argv (len < 3) → sys.exit(1) with usage msg
                          • no --file flag → sys.exit(1) with --file msg
                          • no --content/--stdin → sys.exit(1) with usage msg
                          • --content happy path (yaml file) → sys.exit(0)
                          • --content with trailing non-flag args (joins to content)
                          • --stdin path → sys.exit(0)
                          • --skip-yaml flag skips yaml check
                          • yaml error → sys.exit(1), "WRITE-FILTER: N Error" printed
                          • target-path error → sys.exit(1)
                          • encoding error → sys.exit(1)
                          • duplicates error → sys.exit(1)
                          • ok path with print success message
                          )
  - __main__ guard      (runpy test that hits `if __name__ == "__main__": main()`
                         in-process so coverage attributes the line)

Pitfall (R110-302 cat-2): `main()` ITSELF calls `sys.exit(...)` (lines 58,
60, 70, 81, 83). So tests that call `mod.main()` directly will get a
SystemExit raised. We wrap those calls in `pytest.raises(SystemExit)`.

Pitfall (R110-302 cat-3): `check_target()` resolves to an absolute path via
`os.path.abspath(MAS_DIR)`. The MAS_DIR is computed at module import time as
`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`, i.e. the
`mas-engineer/` repo root. For "outside MAS" tests we use `/tmp/...`. For
"protected substring" tests we use paths like
`<MAS_DIR>/.git/hooks/pre-commit` which starts with MAS_DIR (passes first
check) but contains `.git/` (fails second check).

Pitfall (R110-302 cat-4): the protected-substring list is checked via `if v in
abs_f`. So we need paths that actually contain `.git/`, `checkpoints/`,
`audit.log.jsonl`, `.disziplin_lock`, `.last_confirmation`, or `action.log`.
We exercise each one as a separate test.

Pitfall (R110-302 cat-5): `--content` arg-join logic (lines 64-66) appends
subsequent argv items to the content string as long as they don't start with
`--`. So `--content "a" b c --flag` → content = "a b c". We test this.

Pitfall (R110-302 cat-6): `check_encoding()` is the only place that takes
both str and bytes. We must test both code paths explicitly.

Total: ~25 new tests.
"""
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOL = REPO_ROOT / "tools" / "dev_write_filter.py"
TOOLS_DIR = TOOL.parent
MAS_DIR = str(REPO_ROOT)


def _import_tool():
    """Import dev_write_filter as a library.

    Returns the loaded module. The module is safe to import (no module-level
    sys.argv parsing — main() is only called from the __main__ guard).
    """
    sys.path.insert(0, str(TOOLS_DIR))
    if "dev_write_filter" in sys.modules:
        del sys.modules["dev_write_filter"]
    import dev_write_filter
    return dev_write_filter


# ─────────────────────────────────────────────────────────────────────
# check_target — path safety
# ─────────────────────────────────────────────────────────────────────

def test_check_target_inside_mas_ok():
    """A path inside MAS_DIR with no protected substring → (True, '')."""
    mod = _import_tool()
    ok, msg = mod.check_target(str(REPO_ROOT / "tools" / "dev_write_filter.py"))
    assert ok is True
    assert msg == ""


def test_check_target_outside_mas_rejected():
    """A path OUTSIDE MAS_DIR → (False, 'Target ... outside MAS')."""
    mod = _import_tool()
    ok, msg = mod.check_target("/tmp/outside-mas/whatever.yaml")
    assert ok is False
    assert "outside MAS" in msg
    assert "/tmp/outside-mas" in msg


def test_check_target_protected_dotgit():
    """`.git/` substring → (False, 'Protected: .git/')."""
    mod = _import_tool()
    ok, msg = mod.check_target(str(REPO_ROOT / ".git" / "config"))
    assert ok is False
    assert msg == "Protected: .git/"


def test_check_target_protected_checkpoints():
    """`checkpoints/` substring → (False, 'Protected: checkpoints/')."""
    mod = _import_tool()
    ok, msg = mod.check_target(str(REPO_ROOT / "checkpoints" / "foo.json"))
    assert ok is False
    assert msg == "Protected: checkpoints/"


def test_check_target_protected_audit_log():
    """`audit.log.jsonl` substring → (False, 'Protected: audit.log.jsonl')."""
    mod = _import_tool()
    ok, msg = mod.check_target(str(REPO_ROOT / "audit.log.jsonl"))
    assert ok is False
    assert msg == "Protected: audit.log.jsonl"


def test_check_target_protected_disziplin_lock():
    """`.disziplin_lock` substring → (False, 'Protected: .disziplin_lock')."""
    mod = _import_tool()
    ok, msg = mod.check_target(str(REPO_ROOT / ".disziplin_lock"))
    assert ok is False
    assert msg == "Protected: .disziplin_lock"


def test_check_target_protected_last_confirmation():
    """`.last_confirmation` substring → (False, 'Protected: .last_confirmation')."""
    mod = _import_tool()
    ok, msg = mod.check_target(str(REPO_ROOT / ".last_confirmation"))
    assert ok is False
    assert msg == "Protected: .last_confirmation"


def test_check_target_protected_action_log():
    """`action.log` substring → (False, 'Protected: action.log')."""
    mod = _import_tool()
    ok, msg = mod.check_target(str(REPO_ROOT / "action.log"))
    assert ok is False
    assert msg == "Protected: action.log"


# ─────────────────────────────────────────────────────────────────────
# check_yaml — YAML syntax validation
# ─────────────────────────────────────────────────────────────────────

def test_check_yaml_empty_content_ok():
    """Empty / whitespace-only content → (True, '') (no parsing attempted)."""
    mod = _import_tool()
    assert mod.check_yaml("") == (True, "")
    assert mod.check_yaml("   \n  \t\n") == (True, "")


def test_check_yaml_valid_yaml_ok():
    """Valid YAML → (True, '')."""
    mod = _import_tool()
    ok, msg = mod.check_yaml("foo: bar\nbaz: 1\n")
    assert ok is True
    assert msg == ""


def test_check_yaml_invalid_yaml_error():
    """Invalid YAML → (False, 'YAML-Error: ...')."""
    mod = _import_tool()
    # Unclosed flow mapping → YAML syntax error
    ok, msg = mod.check_yaml("foo: [unclosed\n")
    assert ok is False
    assert msg.startswith("YAML-Error:")


# ─────────────────────────────────────────────────────────────────────
# check_encoding — UTF-8 validation
# ─────────────────────────────────────────────────────────────────────

def test_check_encoding_str_ok():
    """str content (encode('utf-8') succeeds) → (True, '')."""
    mod = _import_tool()
    ok, msg = mod.check_encoding("hello world ä ö ü 🎉")
    assert ok is True
    assert msg == ""


def test_check_encoding_bytes_valid_utf8_ok():
    """bytes content that IS valid UTF-8 → (True, '')."""
    mod = _import_tool()
    ok, msg = mod.check_encoding("hello ä".encode("utf-8"))
    assert ok is True
    assert msg == ""


def test_check_encoding_bytes_invalid_utf8_error():
    """bytes content that is NOT valid UTF-8 → (False, 'No valides UTF-8')."""
    mod = _import_tool()
    # 0xff 0xfe is not a valid UTF-8 start byte sequence
    bad = b"\xff\xfe\x00bad"
    ok, msg = mod.check_encoding(bad)
    assert ok is False
    assert msg == "No valides UTF-8"


# ─────────────────────────────────────────────────────────────────────
# check_duplicates — list-of-dicts dup detection
# ─────────────────────────────────────────────────────────────────────

def test_check_duplicates_non_yaml_file_skipped():
    """File not ending in .yaml/.yml → (True, '') (no parsing attempted)."""
    mod = _import_tool()
    ok, msg = mod.check_duplicates("/tmp/foo.txt", "anything")
    assert ok is True
    assert msg == ""


def test_check_duplicates_yaml_with_dup_dicts_rejected():
    """YAML list containing duplicate dicts → (False, 'Duplikat: <name>')."""
    mod = _import_tool()
    content = "- name: foo\n  v: 1\n- name: bar\n  v: 2\n- name: foo\n  v: 1\n"
    ok, msg = mod.check_duplicates("recipe/x.yaml", content)
    assert ok is False
    assert msg.startswith("Duplikat:")
    assert "foo" in msg


def test_check_duplicates_yaml_no_dup_ok():
    """YAML list with no duplicate dicts → (True, '')."""
    mod = _import_tool()
    content = "- name: foo\n  v: 1\n- name: bar\n  v: 2\n"
    ok, msg = mod.check_duplicates("recipe/x.yaml", content)
    assert ok is True
    assert msg == ""


def test_check_duplicates_yaml_list_of_non_dicts_ok():
    """YAML list of scalars (non-dict items) → (True, '') (no name key to check)."""
    mod = _import_tool()
    content = "- foo\n- bar\n- baz\n"
    ok, msg = mod.check_duplicates("recipe/x.yaml", content)
    assert ok is True
    assert msg == ""


def test_check_duplicates_yaml_non_list_ok():
    """YAML that's a mapping (not a list) → (True, '') (skip dup scan)."""
    mod = _import_tool()
    content = "foo: bar\nbaz: 1\n"
    ok, msg = mod.check_duplicates("recipe/x.yaml", content)
    assert ok is True
    assert msg == ""


def test_check_duplicates_yaml_parse_error_silently_ok():
    """YAML that fails to parse → (True, '') (bare except swallows → ok)."""
    mod = _import_tool()
    # Same unclosed-flow input that check_yaml rejects
    content = "foo: [unclosed\n"
    ok, msg = mod.check_duplicates("recipe/x.yaml", content)
    assert ok is True
    assert msg == ""


def test_check_duplicates_yaml_dup_uses_id_fallback():
    """Duplicate dict without 'name' but with 'id' → 'Duplikat: <id>'."""
    mod = _import_tool()
    content = "- id: A1\n  v: 1\n- id: A1\n  v: 1\n"
    ok, msg = mod.check_duplicates("recipe/x.yaml", content)
    assert ok is False
    assert msg.startswith("Duplikat:")
    assert "A1" in msg


# ─────────────────────────────────────────────────────────────────────
# main() — CLI tests
# ─────────────────────────────────────────────────────────────────────

def test_main_no_argv_exits_1(capsys, monkeypatch):
    """main() with too few argv (len < 3) → SystemExit(1), usage msg on stdout."""
    mod = _import_tool()
    monkeypatch.setattr(sys, "argv", ["dev_write_filter.py"])
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "call:" in captured.out


def test_main_no_file_flag_exits_1(capsys, monkeypatch):
    """main() without --file flag → SystemExit(1), '--file required' on stdout."""
    mod = _import_tool()
    monkeypatch.setattr(sys, "argv", ["dev_write_filter.py", "--content", "x"])
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "--file required" in captured.out


def test_main_no_content_or_stdin_exits_1(capsys, monkeypatch):
    """main() with --file but no --content/--stdin → SystemExit(1)."""
    mod = _import_tool()
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", "/tmp/whatever.yaml"]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "--content" in captured.out or "--stdin" in captured.out


def _in_mas_yaml(tmp_path, name):
    """Return a path inside MAS_DIR ending in .yaml so check_target passes.

    tmp_path is created by pytest under /tmp/... which is outside MAS_DIR.
    We instead place the target under MAS_DIR/<tmp_subdir>/<name>.yaml.
    """
    subdir = REPO_ROOT / "tests" / "_r110302_dwf_tmp"
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir / name


def test_main_content_happy_path_exits_0(capsys, monkeypatch, tmp_path):
    """Happy path: --file yaml + --content valid yaml → SystemExit(0), success msg."""
    mod = _import_tool()
    target = _in_mas_yaml(tmp_path, "good.yaml")
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", str(target), "--content", "foo: bar"]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out
    assert str(target) in captured.out


def test_main_content_joins_trailing_args(capsys, monkeypatch, tmp_path):
    """`--content 'a' b c` joins 'a b c' (until a --flag)."""
    mod = _import_tool()
    target = _in_mas_yaml(tmp_path, "joined.yaml")
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", str(target),
         "--content", "alpha", "beta", "gamma", "--skip-yaml"]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 0


def test_main_stdin_happy_path(capsys, monkeypatch, tmp_path):
    """--stdin path reads from stdin, validates, exits 0."""
    mod = _import_tool()
    target = _in_mas_yaml(tmp_path, "stdin.yaml")
    monkeypatch.setattr(sys, "stdin", type("S", (), {
        "read": staticmethod(lambda: "foo: bar\n")
    })())
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", str(target), "--stdin"]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out


def test_main_yaml_error_reports_and_exits_1(capsys, monkeypatch, tmp_path):
    """Invalid yaml content → SystemExit(1), 'WRITE-FILTER: N Error' + YAML-Error line."""
    mod = _import_tool()
    target = _in_mas_yaml(tmp_path, "bad.yaml")
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", str(target),
         "--content", "foo: [unclosed"]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "WRITE-FILTER" in captured.out
    assert "YAML" in captured.out


def test_main_target_path_error_reports_and_exits_1(capsys, monkeypatch):
    """Path outside MAS_DIR → SystemExit(1), 'Target' error reported."""
    mod = _import_tool()
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", "/tmp/outside.yaml",
         "--content", "foo: bar"]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "WRITE-FILTER" in captured.out
    assert "Target" in captured.out


def test_main_skip_yaml_allows_invalid_yaml(capsys, monkeypatch, tmp_path):
    """--skip-yaml suppresses the yaml check, so invalid yaml content still passes."""
    mod = _import_tool()
    target = _in_mas_yaml(tmp_path, "skip.yaml")
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", str(target),
         "--content", "this is :: not :: yaml :: at :: all :::",
         "--skip-yaml"]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out


def test_main_duplicates_error_reports_and_exits_1(capsys, monkeypatch, tmp_path):
    """Duplicate dicts in YAML list → SystemExit(1), 'Duplikate' error reported."""
    mod = _import_tool()
    target = _in_mas_yaml(tmp_path, "dups.yaml")
    content = "- name: foo\n  v: 1\n- name: foo\n  v: 1\n"
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", str(target), "--content", content]
    )
    with pytest.raises(SystemExit) as excinfo:
        mod.main()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "WRITE-FILTER" in captured.out
    assert "Duplikate" in captured.out


# ─────────────────────────────────────────────────────────────────────
# __main__ guard — exercises the `if __name__ == "__main__": main()` line
# in-process so coverage attributes it.
# ─────────────────────────────────────────────────────────────────────

def test_main_runpy_under_dunder_main(monkeypatch, tmp_path, capsys):
    """Execute the script via `runpy.run_path(__name__='__main__')` to hit
    the `if __name__ == "__main__":` line IN-PROCESS, so coverage.py
    attributes it to this test. Use a valid yaml so main() exits 0.
    """
    target = _in_mas_yaml(tmp_path, "ok.yaml")
    monkeypatch.setattr(
        sys, "argv",
        ["dev_write_filter.py", "--file", str(target),
         "--content", "foo: bar"]
    )
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(TOOL), run_name="__main__")
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out
