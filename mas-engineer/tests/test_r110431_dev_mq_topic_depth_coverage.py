"""R110-431 — coverage-push r6: tools/dev_mq_topic_depth.py 0% → 100%.

Tiny MQ topic depth printer (38 lines). Prints the line-count of the
NDJSON file backing the topic.

Targets:
- topic_to_filename: alphanumeric topic, topic with special chars
  (e.g. "foo/bar.baz" → "foo_bar_baz.ndjson"), underscores preserved,
  dashes preserved
- main: no-args (exit 1 + usage to stderr), missing file (print 0,
  exit 0), existing file empty (print 0), 3-line file (print 3),
  topic with special chars (file lookup uses sanitized name)
- __main__ exec via in-process exec()
"""

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_mq_topic_depth as mqd  # noqa: E402


@pytest.fixture
def mq_root(tmp_path, monkeypatch):
    """Re-point MQ_ROOT onto tmp_path/.mase/mq."""
    new_root = tmp_path / ".mase" / "mq"
    new_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mqd, "MQ_ROOT", new_root)
    monkeypatch.setattr(mqd, "REPO_ROOT", tmp_path)
    return new_root


# ─────────────────────────────────────────────────────────────────────
# topic_to_filename
# ─────────────────────────────────────────────────────────────────────
class TestTopicToFilename:
    def test_alphanumeric(self):
        assert mqd.topic_to_filename("abc123") == "abc123.ndjson"

    def test_underscores_preserved(self):
        assert mqd.topic_to_filename("foo_bar") == "foo_bar.ndjson"

    def test_dashes_preserved(self):
        assert mqd.topic_to_filename("foo-bar") == "foo-bar.ndjson"

    def test_slash_sanitized(self):
        assert mqd.topic_to_filename("foo/bar") == "foo_bar.ndjson"

    def test_dot_sanitized(self):
        assert mqd.topic_to_filename("foo.bar") == "foo_bar.ndjson"

    def test_space_sanitized(self):
        assert mqd.topic_to_filename("foo bar") == "foo_bar.ndjson"

    def test_special_chars(self):
        # All non-alphanumeric/underscore/dash → underscore
        assert mqd.topic_to_filename("foo!@#bar") == "foo___bar.ndjson"

    def test_already_clean(self):
        assert mqd.topic_to_filename("R110-test_topic") == "R110-test_topic.ndjson"


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_args(self, mq_root, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py"])
        rc = mqd.main()
        assert rc == 1
        out = capsys.readouterr()
        assert "usage" in out.err.lower()

    def test_missing_file_returns_zero(self, mq_root, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "missing"])
        rc = mqd.main()
        assert rc == 0
        out = capsys.readouterr()
        assert out.out.strip() == "0"

    def test_empty_file_returns_zero(self, mq_root, monkeypatch, capsys):
        (mq_root / "empty.ndjson").write_text("")
        monkeypatch.setattr(sys, "argv",
                            ["dev_mq_topic_depth.py", "empty"])
        rc = mqd.main()
        assert rc == 0
        out = capsys.readouterr()
        assert out.out.strip() == "0"

    def test_three_line_file(self, mq_root, monkeypatch, capsys):
        (mq_root / "three.ndjson").write_text(
            '{"a": 1}\n{"b": 2}\n{"c": 3}\n')
        monkeypatch.setattr(sys, "argv",
                            ["dev_mq_topic_depth.py", "three"])
        rc = mqd.main()
        assert rc == 0
        out = capsys.readouterr()
        assert out.out.strip() == "3"

    def test_topic_with_special_chars(self, mq_root, monkeypatch, capsys):
        # Topic "foo/bar" → file "foo_bar.ndjson"
        (mq_root / "foo_bar.ndjson").write_text('{"x":1}\n{"y":2}\n')
        monkeypatch.setattr(sys, "argv",
                            ["dev_mq_topic_depth.py", "foo/bar"])
        rc = mqd.main()
        assert rc == 0
        out = capsys.readouterr()
        assert out.out.strip() == "2"


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_no_args(self, monkeypatch, mq_root):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_mq_topic_depth.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_mq_topic_depth.py"]
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                try:
                    exec(compile(script, "dev_mq_topic_depth.py", "exec"),
                         {"__name__": "__main__",
                          "__file__": "dev_mq_topic_depth.py"})
                except SystemExit as e:
                    assert e.code == 1
            assert "usage" in buf_err.getvalue().lower()
        finally:
            sys.argv = old_argv
