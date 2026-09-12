"""R110-440 — coverage-push r8: tools/dev_mq_topic_depth.py 0% → 100%.

MQ topic-depth tool (38 lines). Prints NDJSON line-count for a
topic, returns 0 if topic doesn't exist (depth=0).

Targets:
- topic_to_filename: alphanumeric/_/- kept, others → "_"
  * "my.topic" → "my_topic"
  * "my-topic" → "my-topic"
  * "my_topic" → "my_topic"
  * "weird/path" → "weird_path"
- main: no args → exit 1 + usage to stderr, existing topic
  (depth=3) → prints 3, non-existent topic → prints 0
- __main__: invokes main() via sys.exit()
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_mq_topic_depth as td  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# topic_to_filename
# ─────────────────────────────────────────────────────────────────────
class TestTopicToFilename:
    def test_simple_alphanumeric(self):
        assert td.topic_to_filename("simple") == "simple.ndjson"

    def test_dot_replaced(self):
        assert td.topic_to_filename("my.topic") == "my_topic.ndjson"

    def test_dash_kept(self):
        assert td.topic_to_filename("my-topic") == "my-topic.ndjson"

    def test_underscore_kept(self):
        assert td.topic_to_filename("my_topic") == "my_topic.ndjson"

    def test_slash_replaced(self):
        assert td.topic_to_filename("a/b") == "a_b.ndjson"

    def test_space_replaced(self):
        assert td.topic_to_filename("a b") == "a_b.ndjson"

    def test_unicode_letters_kept(self):
        # Python 3's isalnum() returns True for unicode letters,
        # so äöü are kept as-is.
        assert td.topic_to_filename("äöü") == "äöü.ndjson"

    def test_empty_topic(self):
        assert td.topic_to_filename("") == ".ndjson"

    def test_alphanumeric_kept(self):
        assert td.topic_to_filename("abc123") == "abc123.ndjson"


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_args_exits_1(self, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_mq_topic_depth.py"]
        try:
            code = td.main()
            assert code == 1
            err = capsys.readouterr().err
            assert "usage:" in err
        finally:
            sys.argv = old_argv

    def test_existing_topic(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(td, "MQ_ROOT", tmp_path)
        # Create a topic file with 3 lines
        topic_file = tmp_path / "test.ndjson"
        topic_file.write_text('{"a":1}\n{"b":2}\n{"c":3}\n')
        old_argv = sys.argv
        sys.argv = ["dev_mq_topic_depth.py", "test"]
        try:
            code = td.main()
            assert code == 0
            out = capsys.readouterr().out
            assert out.strip() == "3"
        finally:
            sys.argv = old_argv

    def test_non_existent_topic(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(td, "MQ_ROOT", tmp_path)
        old_argv = sys.argv
        sys.argv = ["dev_mq_topic_depth.py", "nonexistent"]
        try:
            code = td.main()
            assert code == 0
            out = capsys.readouterr().out
            assert out.strip() == "0"
        finally:
            sys.argv = old_argv

    def test_topic_with_special_chars(self, tmp_path, monkeypatch,
                                       capsys):
        monkeypatch.setattr(td, "MQ_ROOT", tmp_path)
        # Topic with slash → filename uses underscore
        topic_file = tmp_path / "weird_topic.ndjson"
        topic_file.write_text('{"a":1}\n')
        old_argv = sys.argv
        sys.argv = ["dev_mq_topic_depth.py", "weird/topic"]
        try:
            code = td.main()
            assert code == 0
            out = capsys.readouterr().out
            assert out.strip() == "1"
        finally:
            sys.argv = old_argv


# ─────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_main_exec_no_args_exits_1(self, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_mq_topic_depth.py"]
        code = 0
        try:
            exec(compile(Path(__file__).resolve().parents[1]
                         .joinpath("tools/dev_mq_topic_depth.py")
                         .read_text(),
                         "dev_mq_topic_depth.py", "exec"),
                 {"__name__": "__main__",
                  "__file__": "dev_mq_topic_depth.py"})
        except SystemExit as e:
            code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        assert code == 1
        err = capsys.readouterr().err
        assert "usage:" in err
