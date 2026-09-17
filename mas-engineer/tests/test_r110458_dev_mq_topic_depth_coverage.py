"""R110-458 — coverage-push r8: tools/dev_mq_topic_depth.py 0% → 100%.

Tiny utility: print depth of a MQ topic's NDJSON file.

Targets:
- topic_to_filename: sanitize topic to safe filename
- main():
  - no argv → usage to stderr + return 1
  - topic, file doesn't exist → print 0, return 0
  - topic, file exists with N lines → print N
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import tools.dev_mq_topic_depth as td  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# topic_to_filename
# ─────────────────────────────────────────────────────────────────────
class TestSanitize:
    def test_alphanumeric(self):
        assert td.topic_to_filename("abc123") == "abc123.ndjson"

    def test_with_underscore(self):
        assert td.topic_to_filename("foo_bar") == "foo_bar.ndjson"

    def test_with_dash(self):
        assert td.topic_to_filename("foo-bar") == "foo-bar.ndjson"

    def test_with_special(self):
        # /, ., spaces → all become _
        r = td.topic_to_filename("foo/bar.baz qux")
        assert r == "foo_bar_baz_qux.ndjson"

    def test_empty(self):
        assert td.topic_to_filename("") == ".ndjson"

    def test_unicode(self):
        # Greek β is alphanumeric in Python, only `.` is replaced
        r = td.topic_to_filename("foo.βar")
        assert r == "foo_βar.ndjson"


# ─────────────────────────────────────────────────────────────────────
# main — direct call
# ─────────────────────────────────────────────────────────────────────
class TestMainDirect:
    def test_no_argv(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["x"])
        rc = td.main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "usage:" in err

    def test_topic_no_file(self, monkeypatch, tmp_path,
                              capsys):
        # Patch MQ_ROOT to empty tmp_path
        monkeypatch.setattr(td, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["x", "ghost"])
        rc = td.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "0" in out

    def test_topic_with_file(self, monkeypatch, tmp_path,
                              capsys):
        # Create NDJSON file with 3 lines
        f = tmp_path / "foo.ndjson"
        f.write_text('{"a":1}\n{"b":2}\n{"c":3}\n')
        monkeypatch.setattr(td, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["x", "foo"])
        rc = td.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "3" in out

    def test_topic_with_empty_file(self, monkeypatch, tmp_path,
                                     capsys):
        f = tmp_path / "empty.ndjson"
        f.write_text("")
        monkeypatch.setattr(td, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["x", "empty"])
        rc = td.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "0" in out

    def test_topic_filename_sanitized(self, monkeypatch, tmp_path,
                                        capsys):
        # Topic with / and . gets sanitized to .ndjson file
        f = tmp_path / "foo_bar_baz.ndjson"
        f.write_text("line1\nline2\n")
        monkeypatch.setattr(td, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["x", "foo/bar.baz"])
        rc = td.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "2" in out


# ─────────────────────────────────────────────────────────────────────
# main — CLI subprocess (covers __main__ block)
# ─────────────────────────────────────────────────────────────────────
class TestMainCli:
    def test_cli_no_argv_exits_1(self):
        r = subprocess.run(
            ['python3', 'tools/dev_mq_topic_depth.py'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 1
        assert "usage:" in r.stderr

    def test_cli_ghost_topic_exits_0(self):
        r = subprocess.run(
            ['python3', 'tools/dev_mq_topic_depth.py',
             'nonexistent_topic_xyz'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        assert r.stdout.strip() == "0"
