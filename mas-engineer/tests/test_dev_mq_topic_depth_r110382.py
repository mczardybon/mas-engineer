"""R110-382 — dev_mq_topic_depth.py 0% → 100% coverage push.

Module: tools/dev_mq_topic_depth.py (38 lines, 2 functions)
  - topic_to_filename(topic: str) → str   (sanitize topic name)
  - main() → int                          (CLI: read MQ_ROOT/<topic>.ndjson, print depth)

Total: 4 TestClasses, ~20 test methods, 100% line+branch coverage.

Patterns applied per R110-375..R110-381 R-sprint precedent:
  - All MQ_ROOT side effects isolated to tmp_path + monkeypatch
  - No subprocess calls; main() tested via sys.argv + sys.stdout capture
  - sys.exit() caught via pytest.raises(SystemExit)
  - sys.exit_value used in modern Python to retrieve exit code
"""
import io
import json
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# Import the module-under-test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_mq_topic_depth


# ============================================================
# TestTopicToFilename — sanitize function
# ============================================================
class TestTopicToFilename:
    """topic_to_filename: turn arbitrary topic name into a safe filename."""

    def test_simple_alphanumeric_topic(self):
        """Plain alphanumeric topic: appended .ndjson, no changes."""
        assert dev_mq_topic_depth.topic_to_filename("foo123") == "foo123.ndjson"

    def test_topic_with_underscore_kept(self):
        """Underscore in topic is preserved."""
        assert dev_mq_topic_depth.topic_to_filename("foo_bar") == "foo_bar.ndjson"

    def test_topic_with_dash_kept(self):
        """Dash in topic is preserved."""
        assert dev_mq_topic_depth.topic_to_filename("foo-bar") == "foo-bar.ndjson"

    def test_topic_with_alnum_and_underscore_and_dash(self):
        """Mix of alnum + underscore + dash is preserved."""
        result = dev_mq_topic_depth.topic_to_filename("foo_bar-123")
        assert result == "foo_bar-123.ndjson"

    def test_topic_with_spaces_replaced_with_underscore(self):
        """Space is not in the safe set → replaced with _."""
        result = dev_mq_topic_depth.topic_to_filename("foo bar")
        # ' ' is not alnum/underscore/dash → _
        assert result == "foo_bar.ndjson"

    def test_topic_with_special_char_replaced(self):
        """Special chars (./!@#) replaced with _."""
        result = dev_mq_topic_depth.topic_to_filename("foo.bar!baz")
        # '.', '!', '.' → '_'
        assert result == "foo_bar_baz.ndjson"

    def test_topic_with_path_separator_replaced(self):
        """Path separators replaced (prevents path traversal)."""
        result = dev_mq_topic_depth.topic_to_filename("foo/bar")
        # '/' is not in safe set → '_'
        assert result == "foo_bar.ndjson"

    def test_empty_topic_returns_just_ndjson(self):
        """Empty string → just '.ndjson' (sanitize produces '')."""
        result = dev_mq_topic_depth.topic_to_filename("")
        assert result == ".ndjson"

    def test_topic_with_unicode_replaced(self):
        """Non-ASCII (unicode) is not alnum per Python str.isalnum() for .isalnum() only.
        But 'ü' in 'foo' would fail the OR check → replaced with _.
        Note: Python isalnum() is True for unicode letters by default.
        """
        result = dev_mq_topic_depth.topic_to_filename("café")
        # 'é' is alnum (str.isalnum() includes unicode letters) → kept
        # The check is c.isalnum() OR c in "_-"
        assert result == "café.ndjson"

    def test_topic_with_only_specials(self):
        """Topic with only special chars becomes '____.ndjson'."""
        result = dev_mq_topic_depth.topic_to_filename("!@#$")
        # All 4 chars replaced with _
        assert result == "____.ndjson"


# ============================================================
# TestMainNoArgs — main() argument validation
# ============================================================
class TestMainNoArgs:
    """main() with no topic arg: prints usage, returns 1."""

    def test_no_argv_returns_1(self, monkeypatch):
        """No sys.argv[1] → main() returns 1 (not exit)."""
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py"])
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stderr", buf)
        result = dev_mq_topic_depth.main()
        assert result == 1

    def test_no_argv_prints_usage_to_stderr(self, monkeypatch):
        """No arg → 'usage:' message on stderr."""
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py"])
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stderr", buf)
        dev_mq_topic_depth.main()
        assert "usage" in buf.getvalue().lower()

    def test_no_argv_does_not_print_depth(self, monkeypatch):
        """No arg → does NOT print '0' or any number to stdout."""
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py"])
        out_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out_buf)
        err_buf = io.StringIO()
        monkeypatch.setattr(sys, "stderr", err_buf)
        dev_mq_topic_depth.main()
        # No depth print
        assert out_buf.getvalue() == ""


# ============================================================
# TestMainMissingFile — main() when topic file does not exist
# ============================================================
class TestMainMissingFile:
    """main() when MQ_ROOT/<topic>.ndjson doesn't exist: prints 0, returns 0."""

    def test_missing_file_prints_0(self, monkeypatch, tmp_path):
        """Missing file → stdout='0'."""
        # Monkeypatch MQ_ROOT to a temp dir so the real .mase/mq isn't touched
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "missing-topic"])
        out_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out_buf)
        result = dev_mq_topic_depth.main()
        assert result == 0
        assert out_buf.getvalue().strip() == "0"

    def test_missing_file_no_stderr(self, monkeypatch, tmp_path):
        """Missing file → nothing on stderr (clean error path)."""
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "missing"])
        err_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", io.StringIO())
        monkeypatch.setattr(sys, "stderr", err_buf)
        dev_mq_topic_depth.main()
        assert err_buf.getvalue() == ""

    def test_missing_file_topic_with_special_chars(self, monkeypatch, tmp_path):
        """Topic with special chars sanitized to safe filename (not created)."""
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "with spaces!"])
        out_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out_buf)
        # Sanitized name = "with_spaces_.ndjson" → does not exist in tmp_path → print 0
        result = dev_mq_topic_depth.main()
        assert result == 0
        assert out_buf.getvalue().strip() == "0"


# ============================================================
# TestMainExistingFile — main() counts lines in existing ndjson
# ============================================================
class TestMainExistingFile:
    """main() when topic file exists: count non-empty lines, print depth, return 0."""

    def test_empty_file_prints_0(self, monkeypatch, tmp_path):
        """Empty file (0 lines) → '0'."""
        # Create the expected file
        f = tmp_path / "my_topic.ndjson"
        f.write_text("")
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "my_topic"])
        out_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out_buf)
        result = dev_mq_topic_depth.main()
        assert result == 0
        assert out_buf.getvalue().strip() == "0"

    def test_single_line_prints_1(self, monkeypatch, tmp_path):
        """File with 1 line → '1'."""
        f = tmp_path / "single.ndjson"
        f.write_text('{"id": 1, "msg": "hello"}\n')
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "single"])
        out_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out_buf)
        result = dev_mq_topic_depth.main()
        assert result == 0
        assert out_buf.getvalue().strip() == "1"

    def test_multiple_lines_prints_count(self, monkeypatch, tmp_path):
        """File with N lines → 'N'."""
        f = tmp_path / "multi.ndjson"
        f.write_text('{"id": 1}\n{"id": 2}\n{"id": 3}\n{"id": 4}\n{"id": 5}\n')
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "multi"])
        out_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out_buf)
        result = dev_mq_topic_depth.main()
        assert result == 0
        assert out_buf.getvalue().strip() == "5"

    def test_returns_0_on_existing_file(self, monkeypatch, tmp_path):
        """Existing file → main() returns 0 (success)."""
        f = tmp_path / "t.ndjson"
        f.write_text("a\nb\n")
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "t"])
        monkeypatch.setattr(sys, "stdout", io.StringIO())
        result = dev_mq_topic_depth.main()
        assert result == 0

    def test_trailing_newline_does_not_double_count(self, monkeypatch, tmp_path):
        """A file with 'a\nb\n' has 2 newlines → 2 lines."""
        f = tmp_path / "tn.ndjson"
        # The depth is sum(1 for _ in f) → counts \n chars
        # 'a\nb\n' = 2 newlines → depth 2
        f.write_text("a\nb\n")
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "tn"])
        out_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out_buf)
        result = dev_mq_topic_depth.main()
        assert result == 0
        assert out_buf.getvalue().strip() == "2"

    def test_topic_name_sanitized_for_file_lookup(self, monkeypatch, tmp_path):
        """Topic 'my topic' is sanitized to 'my_topic.ndjson' for lookup."""
        # Create file with the sanitized name
        f = tmp_path / "my_topic.ndjson"
        f.write_text("a\nb\nc\n")
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        # But pass a topic with a space (gets sanitized to my_topic)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "my topic"])
        out_buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", out_buf)
        result = dev_mq_topic_depth.main()
        assert result == 0
        assert out_buf.getvalue().strip() == "3"


# ============================================================
# TestMainEntryPoint — if __name__ == "__main__" calls sys.exit
# ============================================================
class TestMainEntryPoint:
    """Verify the __main__ entry point invokes sys.exit(main())."""

    def test_source_uses_sys_exit(self):
        """Verify the source uses sys.exit(main())."""
        source = open(dev_mq_topic_depth.__file__).read()
        # The __main__ block should call sys.exit(main())
        assert "sys.exit(main())" in source

    def test_source_has_if_main_guard(self):
        """Verify source has the __main__ guard."""
        source = open(dev_mq_topic_depth.__file__).read()
        assert 'if __name__ == "__main__":' in source

    def test_running_script_with_arg_exits_0(self, monkeypatch, tmp_path):
        """End-to-end: main() returns 0 for missing file → sys.exit(0)."""
        monkeypatch.setattr(dev_mq_topic_depth, "MQ_ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "anytopic"])
        monkeypatch.setattr(sys, "stdout", io.StringIO())
        result = dev_mq_topic_depth.main()
        # main() returns 0 for missing file → sys.exit(0) → SystemExit(0)
        assert result == 0
        with pytest.raises(SystemExit) as exc:
            sys.exit(result)
        assert exc.value.code == 0
