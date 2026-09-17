"""R110-309: library function tests for tools/dev_workspace.py.

Covers pure logging helpers and the standalone cmd_init_recovery
early-return branch (which exercises lines 80-85).
"""
import sys
import os
from pathlib import Path
import pytest

TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def ws(monkeypatch):
    """Import dev_workspace with a sandboxed CWD.

    dev_workspace.py does NOT have a sandbox-aware init, so we just
    import it with /tools/ in sys.path. The logging helpers (log,
    info, ok, warn, error) are pure wrappers around print().
    """
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_workspace", None)
    try:
        import dev_workspace
        return dev_workspace
    finally:
        sys.path.pop(0)


# ────────────────────────────────────────────────────────────
# log/info/ok/warn/error (the 5 logging helpers)
# ────────────────────────────────────────────────────────────

def test_log_prints_msg(ws, capsys):
    """log() prints the message verbatim (no prefix)."""
    ws.log("hello plain")
    captured = capsys.readouterr()
    assert captured.out.strip() == "hello plain"


def test_info_prints_emoji_prefix(ws, capsys):
    """info() prefixes the message with the info-emoji."""
    ws.info("info message")
    captured = capsys.readouterr()
    assert "info message" in captured.out
    # The info-emoji is U+1F4E2 (megaphone) which appears as "📢"
    assert "📢" in captured.out


def test_ok_prints_check_prefix(ws, capsys):
    """ok() prefixes the message with the check-emoji."""
    ws.ok("done")
    captured = capsys.readouterr()
    assert "done" in captured.out
    assert "✅" in captured.out


def test_warn_prints_warn_prefix(ws, capsys):
    """warn() prefixes the message with the warn-emoji."""
    ws.warn("careful")
    captured = capsys.readouterr()
    assert "careful" in captured.out
    assert "⚠️" in captured.out


def test_error_prints_error_prefix(ws, capsys):
    """error() prefixes the message with the error-emoji."""
    ws.error("boom")
    captured = capsys.readouterr()
    assert "boom" in captured.out
    assert "❌" in captured.out


# ────────────────────────────────────────────────────────────
# count_files
# ────────────────────────────────────────────────────────────

def test_count_files_missing_dir_returns_zero(ws, tmp_path):
    """count_files on a non-existent dir returns 0 (no exception)."""
    assert ws.count_files(tmp_path / "does-not-exist") == 0


def test_count_files_empty_dir(ws, tmp_path):
    """count_files on an empty dir returns 0."""
    d = tmp_path / "empty"
    d.mkdir()
    assert ws.count_files(d) == 0


def test_count_files_default_pattern(ws, tmp_path):
    """count_files with default '*' pattern matches all files."""
    d = tmp_path / "mixed"
    d.mkdir()
    (d / "a.txt").write_text("1")
    (d / "b.txt").write_text("2")
    (d / "c.py").write_text("3")
    assert ws.count_files(d) == 3


def test_count_files_glob_pattern(ws, tmp_path):
    """count_files with a glob pattern only counts matching files."""
    d = tmp_path / "mixed"
    d.mkdir()
    (d / "a.txt").write_text("1")
    (d / "b.txt").write_text("2")
    (d / "c.py").write_text("3")
    assert ws.count_files(d, "*.txt") == 2
    assert ws.count_files(d, "*.py") == 1
    assert ws.count_files(d, "*.md") == 0


# ────────────────────────────────────────────────────────────
# cmd_init_recovery — early-return path (no template dir)
# ────────────────────────────────────────────────────────────

def test_cmd_init_recovery_no_template_returns_early(ws, tmp_path, monkeypatch, capsys):
    """cmd_init_recovery with a non-existent template dir returns early.

    The function resolves the recovery template from:
      Path(__file__).parent.parent / "recipe" / "template" / "recovery"

    We patch Path.exists() so that any "recovery" path returns False,
    triggering the early-return at line 83-85 (warn + return).
    """
    real_exists = Path.exists

    def fake_exists(self):
        # Any path under .../recipe/template/recovery/ should NOT exist
        if "recipe" in str(self) and "recovery" in str(self):
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    ws.cmd_init_recovery(str(tmp_path / "ws"))
    captured = capsys.readouterr()
    # We expect a "Recovery-Template not found" warning
    assert "Recovery-Template" in captured.out or "not found" in captured.out.lower()
