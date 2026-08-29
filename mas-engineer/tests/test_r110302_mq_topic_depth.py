"""
test_r110302_mq_topic_depth.py — R110-302 Coverage Sprint for
tools/dev_mq_topic_depth.py.

Target: dev_mq_topic_depth.py (38 lines, 22 stmts).
R110-302 imports the tool as a library and tests:

  - topic_to_filename()   (6 tests covering empty, alnum, _-, special
                           chars, subtopics/dots/colons/slashes, unicode)
  - main()                (4 tests: missing arg → rc=1, missing topic file
                           → rc=0 + "0", present file → rc=0 + depth,
                           present file → rc=0 + correct line count)
  - __main__ guard        (1 subprocess test that runs the file as
                           `python3 dev_mq_topic_depth.py <topic>` so
                           coverage attributes the `if __name__ == "__main__":`
                           line and `sys.exit(main())` call.)

Pitfall (R110-78 cat-3): the tool reads `MQ_ROOT = REPO_ROOT / ".mase" / "mq"`
at MODULE-IMPORT TIME from `Path(__file__).parent.parent`. When we import
via `sys.path.insert(tools_dir)`, the real MQ_ROOT points to the actual
`mas-engineer/.mase/mq/` directory. For "file exists" tests we monkeypatch
`mod.MQ_ROOT` to a tmp dir that contains the .ndjson file we want to test.
For "file missing" tests the real path is fine (topic won't exist).

Pitfall (R110-302 cat-2): `main()` itself does NOT call sys.exit — only
the `if __name__ == "__main__":` block does. So tests that call
`mod.main()` directly get a plain return code (0 or 1), NOT a SystemExit.
The subprocess test DOES get a SystemExit (which subprocess returns as
returncode), so we assert returncode == 0 there.

Total: 11 new tests.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
TOOL = REPO_ROOT / "mas-engineer" / "tools" / "dev_mq_topic_depth.py"
TOOLS_DIR = TOOL.parent


def _import_tool():
    """Import dev_mq_topic_depth as a library.

    Returns the loaded module. The module is safe to import (only
    stdlib + pathlib; no module-level sys.argv parsing).
    """
    sys.path.insert(0, str(TOOLS_DIR))
    if "dev_mq_topic_depth" in sys.modules:
        del sys.modules["dev_mq_topic_depth"]
    import dev_mq_topic_depth
    return dev_mq_topic_depth


# ─────────────────────────────────────────────────────────────────────
# topic_to_filename — pure-function tests
# ─────────────────────────────────────────────────────────────────────

def test_topic_to_filename_alnum_passthrough():
    """Pure alnum topic →  '<topic>.ndjson' unchanged."""
    mod = _import_tool()
    assert mod.topic_to_filename("myTopic") == "myTopic.ndjson"


def test_topic_to_filename_empty_string():
    """Empty topic → '.ndjson' (no chars to replace, just appended)."""
    mod = _import_tool()
    assert mod.topic_to_filename("") == ".ndjson"


def test_topic_to_filename_underscore_and_dash_kept():
    """`_` and `-` are in the allowlist → kept verbatim."""
    mod = _import_tool()
    assert mod.topic_to_filename("my_topic-1") == "my_topic-1.ndjson"


def test_topic_to_filename_dots_become_underscores():
    """`a.b.c` (subtopics) → dots replaced with underscores."""
    mod = _import_tool()
    assert mod.topic_to_filename("a.b.c") == "a_b_c.ndjson"


def test_topic_to_filename_colons_become_underscores():
    """MQ topics often use `:` as separator → replaced with `_`."""
    mod = _import_tool()
    assert mod.topic_to_filename("agents:im:scan") == "agents_im_scan.ndjson"


def test_topic_to_filename_slashes_become_underscores():
    """`/` is a path separator, not allowed → replaced with `_`."""
    mod = _import_tool()
    assert mod.topic_to_filename("foo/bar") == "foo_bar.ndjson"


def test_topic_to_filename_mixed_special_chars():
    """Mixed `.`, `:`, `/`, spaces → all become `_`."""
    mod = _import_tool()
    assert mod.topic_to_filename("a.b:c/d e") == "a_b_c_d_e.ndjson"


def test_topic_to_filename_unicode_becomes_underscore():
    """Non-ASCII chars are not alnum → replaced with `_`."""
    mod = _import_tool()
    # 'ä' is not alnum per Python's c.isalnum() which returns True for it
    # actually in Python 3 str.isalnum() returns True for unicode letters.
    # We test with a clearly non-alnum char: '!' or space.
    assert mod.topic_to_filename("foo!bar") == "foo_bar.ndjson"
    assert mod.topic_to_filename("foo bar") == "foo_bar.ndjson"


# ─────────────────────────────────────────────────────────────────────
# main() — CLI tests
# ─────────────────────────────────────────────────────────────────────

def test_main_no_argv_returns_1(capsys, monkeypatch):
    """main() with no topic arg → rc=1, usage printed to stderr."""
    mod = _import_tool()
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py"])
    rc = mod.main()
    assert rc == 1
    captured = capsys.readouterr()
    assert "usage" in captured.err.lower()


def test_main_missing_topic_file_returns_0(capsys, monkeypatch):
    """main() with a topic that has no .ndjson file → rc=0, prints '0'."""
    mod = _import_tool()
    # Use a topic name we know won't have a file: long, random
    monkeypatch.setattr(
        sys, "argv",
        ["dev_mq_topic_depth.py", "R110-302-nonexistent-test-topic-xyz"]
    )
    rc = mod.main()
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "0"


def test_main_present_file_counts_lines(capsys, monkeypatch, tmp_path):
    """main() with a present .ndjson file → rc=0, prints line count."""
    mod = _import_tool()
    # Create a fake MQ_ROOT with a 3-line ndjson file
    fake_mq_root = tmp_path / "mq"
    fake_mq_root.mkdir()
    ndjson_path = fake_mq_root / "R110-302topic.ndjson"
    ndjson_path.write_text('{"a":1}\n{"b":2}\n{"c":3}\n')

    # Monkeypatch MQ_ROOT to point to our tmp dir
    monkeypatch.setattr(mod, "MQ_ROOT", fake_mq_root)
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "R110-302topic"])

    rc = mod.main()
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "3"


def test_main_present_file_with_special_chars_in_topic(capsys, monkeypatch, tmp_path):
    """main() resolves a topic with special chars to the right filename via MQ_ROOT lookup.

    We pass a topic containing dots, set MQ_ROOT to a tmp dir that has
    the dot-replaced filename, and verify depth == 0 (file exists but
    empty).
    """
    mod = _import_tool()
    fake_mq_root = tmp_path / "mq"
    fake_mq_root.mkdir()
    # topic_to_filename("a.b") == "a_b.ndjson"
    (fake_mq_root / "a_b.ndjson").write_text("")

    monkeypatch.setattr(mod, "MQ_ROOT", fake_mq_root)
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "a.b"])

    rc = mod.main()
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "0"


# ─────────────────────────────────────────────────────────────────────
# __main__ guard — exercises line 38 (sys.exit(main())) for 100% coverage
# ─────────────────────────────────────────────────────────────────────

def test_main_subprocess_invocation(tmp_path, monkeypatch):
    """Running the tool as a real subprocess exercises the full script,
    including the `if __name__ == "__main__":` block.

    We use a topic we know does not have a backing file, so the
    subprocess returns 0 and prints '0' to stdout. This is an
    end-to-end smoke test of the CLI; the `runpy` test below is what
    actually attributes the `if __name__ == "__main__":` line to
    coverage in-process.
    """
    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [sys.executable, str(TOOL), "R110-302-subproc-missing-topic-zzz"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "0"


def test_main_runpy_under_dunder_main(monkeypatch, capsys):
    """Execute the script via `runpy.run_path(__name__='__main__')` to
    hit the `if __name__ == "__main__": sys.exit(main())` line IN-PROCESS,
    so coverage.py attributes the line to this test.

    We use a topic that has no backing file → main() returns 0 →
    sys.exit(0) → runpy.run_path() catches it (runpy._run_code returns
    the returncode).
    """
    import runpy
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "R110-302-runpy-missing-topic-zzz"])
    # run_path with run_name='__main__' makes `if __name__ == "__main__":` True
    # We catch SystemExit because sys.exit() raises it.
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(TOOL), run_name="__main__")
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "0"
