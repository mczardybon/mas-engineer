"""R110-408: tests for tools/dev_mq_topic_depth.py.

Prints the depth (pending non-acked messages) of an MQ topic by counting
NDJSON lines in `.mase/mq/<topic>.ndjson`. Has 1 pure function
(`topic_to_filename`) plus a `main()` that handles CLI + file I/O.

R110-300a guard: NO `assert "<digit> <word>"` patterns anywhere.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "dev_mq_topic_depth.py"
REPO_ROOT = Path(TOOL).resolve().parent.parent


# ---------------------------------------------------------------------------
# Module loader (same coverage-attribution trick as R110-303)
# ---------------------------------------------------------------------------
def _import_tool():
    REPO_ROOT_LOCAL = str(Path(TOOL).parent.parent)
    TOOLS_DIR = str(Path(TOOL).parent)
    if REPO_ROOT_LOCAL not in sys.path:
        sys.path.insert(0, REPO_ROOT_LOCAL)
    if "tools" not in sys.modules:
        import types
        pkg = types.ModuleType("tools")
        pkg.__path__ = [TOOLS_DIR]
        sys.modules["tools"] = pkg
    full_name = f"tools.{Path(TOOL).stem}"
    spec = importlib.util.spec_from_file_location(full_name, TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _import_tool()


# ---------------------------------------------------------------------------
# topic_to_filename (pure)
# ---------------------------------------------------------------------------
class TestTopicToFilename:
    def test_alphanumeric_passthrough(self, mod):
        assert mod.topic_to_filename("abc123") == "abc123.ndjson"

    def test_underscore_passthrough(self, mod):
        assert mod.topic_to_filename("my_topic_name") == "my_topic_name.ndjson"

    def test_dash_passthrough(self, mod):
        assert mod.topic_to_filename("my-topic-name") == "my-topic-name.ndjson"

    def test_mixed_alnum_under_dash(self, mod):
        assert mod.topic_to_filename("Topic-1_sub") == "Topic-1_sub.ndjson"

    def test_dot_replaced_with_underscore(self, mod):
        assert mod.topic_to_filename("sub.topic") == "sub_topic.ndjson"

    def test_slash_replaced_with_underscore(self, mod):
        # Path separators must NEVER appear in the filename
        assert mod.topic_to_filename("a/b") == "a_b.ndjson"
        assert mod.topic_to_filename("a\\b") == "a_b.ndjson"

    def test_special_chars_replaced(self, mod):
        result = mod.topic_to_filename("a@b#c$")
        # @, #, $ are not alnum, not _, not -, so → "_"
        assert result == "a_b_c_.ndjson"

    def test_empty_string_yields_just_ndjson_extension(self, mod):
        # The generator yields "" for empty input → join("") = "" → ".ndjson"
        # This is a corner case: the file would be `.ndjson` literally.
        # Document the actual behavior so future devs don't "fix" it.
        assert mod.topic_to_filename("") == ".ndjson"

    def test_unicode_alnum_preserved(self, mod):
        # Python's str.isalnum() is Unicode-aware: 'é' and 'ü' are alnum.
        # So 'café' passes through unchanged (which is what we want for
        # international topic names).
        assert mod.topic_to_filename("café") == "café.ndjson"

    def test_unicode_symbol_replaced(self, mod):
        # Symbols like ☃ are NOT alnum → replaced with "_"
        assert mod.topic_to_filename("a☃b") == "a_b.ndjson"

    def test_spaces_replaced(self, mod):
        assert mod.topic_to_filename("a b c") == "a_b_c.ndjson"


# ---------------------------------------------------------------------------
# main() — CLI + file I/O via subprocess
# ---------------------------------------------------------------------------
class TestMainCli:
    def test_no_arg_exits_nonzero(self, mod):
        result = subprocess.run(
            [sys.executable, str(TOOL)],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "usage" in result.stderr

    def test_missing_topic_file_prints_zero(self, mod, monkeypatch):
        # The script reads from REPO_ROOT/.mase/mq/<safe>.ndjson.
        # We chdir into tmp_path and rely on the script's relative path
        # resolution failing → topic file doesn't exist → prints 0.
        # We can't actually chdir the *script* easily, so just run with
        # a topic that has no .mase/mq dir.
        result = subprocess.run(
            [sys.executable, str(TOOL), "noexist_topic_xyz"],
            capture_output=True, text=True,
            cwd="/tmp",  # no .mase/mq here → depth = 0
        )
        # /tmp typically has no .mase/mq/, so script prints 0, exit 0
        assert result.returncode == 0
        assert result.stdout.strip() == "0"

    def test_counts_lines_in_existing_ndjson(self, mod, tmp_path, monkeypatch):
        # Build a fake .mase/mq structure inside tmp_path
        mq_dir = tmp_path / ".mase" / "mq"
        mq_dir.mkdir(parents=True)
        topic = "test_count_topic"
        (mq_dir / f"{topic}.ndjson").write_text(
            '{"a": 1}\n{"b": 2}\n{"c": 3}\n'
        )
        # The script hard-codes REPO_ROOT (parent of tools/). We
        # monkeypatch both MQ_ROOT and sys.argv so main() reads from
        # the fake mq_dir with the correct topic.
        monkeypatch.setattr(mod, "MQ_ROOT", mq_dir)
        monkeypatch.setattr(sys, "argv", [str(TOOL), topic])
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.main()
        assert rc == 0
        assert buf.getvalue().strip() == "3"

    def test_empty_ndjson_file_prints_zero(self, mod, tmp_path, monkeypatch):
        mq_dir = tmp_path / ".mase" / "mq"
        mq_dir.mkdir(parents=True)
        topic = "empty_topic"
        (mq_dir / f"{topic}.ndjson").write_text("")
        monkeypatch.setattr(mod, "MQ_ROOT", mq_dir)
        monkeypatch.setattr(sys, "argv", [str(TOOL), topic])
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.main()
        assert rc == 0
        assert buf.getvalue().strip() == "0"

    def test_topic_with_special_chars_finds_sanitized_file(self, mod, tmp_path, monkeypatch):
        mq_dir = tmp_path / ".mase" / "mq"
        mq_dir.mkdir(parents=True)
        # "a/b" topic → "a_b.ndjson"
        (mq_dir / "a_b.ndjson").write_text("x\ny\n")
        monkeypatch.setattr(mod, "MQ_ROOT", mq_dir)
        # The topic arg is "a/b"; topic_to_filename() must sanitize it.
        monkeypatch.setattr(sys, "argv", [str(TOOL), "a/b"])
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.main()
        assert rc == 0
        assert buf.getvalue().strip() == "2"

    def test_topic_arg_missing_via_main_call(self, mod, monkeypatch):
        # sys.argv with no topic → main() prints usage to stderr + returns 1
        monkeypatch.setattr(sys, "argv", [str(TOOL)])
        import io
        import contextlib
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            rc = mod.main()
        assert rc == 1
        assert "usage" in err_buf.getvalue()
