#!/usr/bin/env python3
"""
R110-515: Coverage test for tools/dev_mq_topic_depth.py (22 stmts, 0% → 100%).

Context: dev_mq_topic_depth.py is a tiny CLI utility that prints the
current depth (number of pending non-acked messages) of a given
mas-engineer message-queue topic. The NDJSON file lives at
`<repo_root>/.mase/mq/<sanitized-topic>.ndjson`.

Module structure (38 lines, 22 stmts, 4 branches):
  - topic_to_filename(topic) — sanitize the topic name by replacing
    non-alphanumeric chars (except _ and -) with underscores.
  - main() — parse sys.argv[1] as the topic, compute the path,
    print "0" if file doesn't exist, otherwise print the line count.
    Returns 1 on usage error, 0 otherwise.
  - __main__ guard: sys.exit(main()).

This file covers every branch:
  - topic_to_filename: 2 tests (passthrough + special-char sanitization)
  - main: 5 tests (no-arg error, missing file → 0, 0 messages,
    3 messages, mixed-content file with trailing newline)
  - __main__ guard: 1 runpy test that exercises the full CLI.
"""

import runpy
import sys
from pathlib import Path

import pytest

# Import as tools.X for pytest-cov name tracking
import tools.dev_mq_topic_depth as mqd  # noqa: E402


# ─── topic_to_filename ──────────────────────────────────────────────

def test_topic_to_filename_passthrough_alphanumeric():
    """Covers line 18-19: alphanum + _ - characters pass through unchanged."""
    assert mqd.topic_to_filename("foo") == "foo.ndjson"
    assert mqd.topic_to_filename("foo_bar") == "foo_bar.ndjson"
    assert mqd.topic_to_filename("foo-bar") == "foo-bar.ndjson"
    assert mqd.topic_to_filename("Foo123") == "Foo123.ndjson"


def test_topic_to_filename_replaces_special_chars():
    """Covers line 18: special chars (/, ., :, space) replaced with _."""
    assert mqd.topic_to_filename("a/b") == "a_b.ndjson"
    assert mqd.topic_to_filename("a.b") == "a_b.ndjson"
    assert mqd.topic_to_filename("a:b") == "a_b.ndjson"
    assert mqd.topic_to_filename("a b") == "a_b.ndjson"
    # Mixed: alphanum + special preserved structure
    assert mqd.topic_to_filename("r110.491/test") == "r110_491_test.ndjson"


# ─── main() ─────────────────────────────────────────────────────────

def test_main_no_args_prints_usage_to_stderr_and_returns_1(capsys, monkeypatch):
    """Covers lines 23-25: missing sys.argv[1] → usage + return 1."""
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py"])
    rc = mqd.main()
    captured = capsys.readouterr()
    assert rc == 1
    assert "usage:" in captured.err
    assert captured.out == ""


def test_main_missing_topic_file_prints_zero(tmp_path, monkeypatch, capsys):
    """Covers lines 28-30: path.exists() == False → print 0, return 0.

    The module computes MQ_ROOT from its own __file__ (Path(__file__).resolve()
    .parent.parent/.mase/mq), so we monkeypatch the module's MQ_ROOT to
    point at our tmp_path."""
    monkeypatch.setattr(mqd, "MQ_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "nonexistent"])
    rc = mqd.main()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "0\n"


def test_main_empty_topic_file_prints_zero(tmp_path, monkeypatch, capsys):
    """Covers line 31-33: file exists but has 0 lines → print 0."""
    monkeypatch.setattr(mqd, "MQ_ROOT", tmp_path)
    topic_file = tmp_path / "empty.ndjson"
    topic_file.write_text("")
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "empty"])
    rc = mqd.main()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "0\n"


def test_main_topic_with_three_messages_prints_three(tmp_path, monkeypatch, capsys):
    """Covers lines 31-33: file with 3 valid NDJSON lines → print 3."""
    monkeypatch.setattr(mqd, "MQ_ROOT", tmp_path)
    topic_file = tmp_path / "three.ndjson"
    topic_file.write_text('{"a":1}\n{"b":2}\n{"c":3}\n')
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "three"])
    rc = mqd.main()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "3\n"


def test_main_topic_with_no_trailing_newline_uses_line_count(
    tmp_path, monkeypatch, capsys
):
    """Covers line 32: sum(1 for _ in f) counts logical lines, not
    physical. 3 lines without trailing newline → 3."""
    monkeypatch.setattr(mqd, "MQ_ROOT", tmp_path)
    topic_file = tmp_path / "no_newline.ndjson"
    topic_file.write_text('{"a":1}\n{"b":2}\n{"c":3}')  # no trailing \n
    monkeypatch.setattr(sys, "argv", ["dev_mq_topic_depth.py", "no_newline"])
    rc = mqd.main()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "3\n"


# ─── __main__ guard ─────────────────────────────────────────────────

def test_main_block_via_runpy(tmp_path, monkeypatch, capsys):
    """Covers lines 37-38: __main__ guard wraps sys.exit(main()).

    Sets MQ_ROOT to tmp_path (so the path resolves correctly), writes
    an empty file, then invokes runpy.run_path with __name__='__main__'
    so pytest-cov tracks the __main__ block.
    """
    monkeypatch.setattr(mqd, "MQ_ROOT", tmp_path)
    (tmp_path / "via_runpy.ndjson").write_text("")
    monkeypatch.setattr(
        sys, "argv", ["dev_mq_topic_depth.py", "via_runpy"]
    )
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(mqd.__file__, run_name="__main__")
    captured = capsys.readouterr()
    # Empty file → 0 printed, sys.exit(0) called (exit code 0)
    assert captured.out == "0\n"
    assert exc_info.value.code == 0
