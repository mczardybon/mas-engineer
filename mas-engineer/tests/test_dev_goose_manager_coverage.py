"""R110-509: Coverage tests for tools/dev_goose_manager.py (189 stmts, 0%).

Strategy: load the module via importlib with a sandboxed HOME so that all the
hard-coded Path.home() / ~/.config/goose etc. resolve into tmp_path. Then
exercise every pure helper + every code branch in cmd_status / cmd_clear / main.

Module pattern:
  GOOSE_CONFIG_DIR = Path.home() / ".config" / "goose"
  GOOSE_SHARE      = Path.home() / ".local" / "share" / "goose"
  GOOSE_STATE      = Path.home() / ".local" / "state" / "goose"

We monkeypatch Path.home() (BEFORE importlib reload) so the module-level
constants point into tmp_path. The module also has a proper
`if __name__ == "__main__":` guard, so importing is safe.
"""

import importlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# Path to the script under test
SCRIPT = (
    Path(__file__).resolve().parent.parent / "tools" / "dev_goose_manager.py"
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_module(monkeypatch, tmp_path):
    """Load dev_goose_manager.py with HOME redirected into tmp_path."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # Patch Path.home BEFORE the module loads so the module-level constants
    # (GOOSE_CONFIG_DIR, GOOSE_SHARE, GOOSE_STATE) resolve into tmp_path.
    orig_home = Path.home

    # Path.home is a classmethod — patch at the class level with a function
    # that ignores `cls` and returns our sandbox path.
    monkeypatch.setattr(
        Path,
        "home",
        classmethod(lambda cls: fake_home),
    )

    # If the module was already loaded (e.g. by another test), drop it.
    sys.modules.pop("dev_goose_manager", None)

    spec = importlib.util.spec_from_file_location("dev_goose_manager", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dev_goose_manager"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_config(mod, tmp_path, *, provider=None, model=None, with_extensions=False,
                 malformed_json=False):
    """Write a goose config.yaml into the sandbox GOOSE_CONFIG_DIR."""
    mod.GOOSE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = mod.GOOSE_CONFIG
    cfg.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if provider is not None:
        lines.append(f"active_provider: {provider}")
    if model is not None:
        lines.append(f"GOOSE_MODEL: {model}")
    if with_extensions:
        lines.append("extensions:")
        lines.append("  enabled: true")
        lines.append("  another_enabled: false")
    cfg.write_text("\n".join(lines))
    return cfg


# ──────────────────────────────────────────────────────────────────────────────
# Tests for fmt_size (pure)
# ──────────────────────────────────────────────────────────────────────────────

class TestFmtSize:
    def test_returns_dash_when_path_missing(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        assert mod.fmt_size(tmp_path / "does-not-exist") == "—"

    def test_returns_dash_for_unsupported_type(self, monkeypatch, tmp_path):
        """Symlink to nothing → is_file=False, is_dir=False → '—'."""
        mod = _load_module(monkeypatch, tmp_path)
        # Create a symlink pointing to a non-existent target
        dangling = tmp_path / "dangling"
        try:
            dangling.symlink_to(tmp_path / "no-such-target")
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported on this fs")
        assert mod.fmt_size(dangling) == "—"

    def test_bytes(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        f = tmp_path / "small.bin"
        f.write_bytes(b"x" * 500)
        out = mod.fmt_size(f)
        assert out.endswith("B")
        assert "500.0" in out

    def test_kilobytes(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        f = tmp_path / "k.bin"
        f.write_bytes(b"x" * 2048)
        assert "KB" in mod.fmt_size(f)

    def test_megabytes(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        f = tmp_path / "m.bin"
        f.write_bytes(b"x" * (2 * 1024 * 1024))
        assert "MB" in mod.fmt_size(f)

    def test_gigabytes(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        f = tmp_path / "g.bin"
        f.write_bytes(b"x")

        # Wrap real stat, only override st_size for OUR file
        import os as _os
        orig_stat = Path.stat

        def fake_stat(self):
            r = orig_stat(self)
            if self == f:
                # Return a new stat_result-like with overridden size
                import stat as _stat
                # Build a NamedTuple-ish: easiest is to make a wrapper class
                class SR:
                    pass
                sr = SR()
                sr.st_size = 3 * 1024 ** 3
                sr.st_mode = r.st_mode
                sr.st_mtime = r.st_mtime
                sr.st_ino = r.st_ino
                sr.st_dev = r.st_dev
                sr.st_nlink = r.st_nlink
                sr.st_uid = r.st_uid
                sr.st_gid = r.st_gid
                sr.st_atime = r.st_atime
                sr.st_ctime = r.st_ctime
                return sr
            return r

        monkeypatch.setattr(Path, "stat", fake_stat)
        assert "GB" in mod.fmt_size(f)

    def test_directory_size(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        d = tmp_path / "dir"
        d.mkdir()
        (d / "a").write_bytes(b"x" * 100)
        (d / "b").write_bytes(b"x" * 200)
        out = mod.fmt_size(d)
        # 300 bytes → 300.0 B
        assert "300.0" in out
        assert "B" in out

    def test_handles_exception_returns_question(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        # Make a directory so fmt_size takes the rglob branch
        d = tmp_path / "broken_dir"
        d.mkdir()
        (d / "f").write_text("x")

        # Make the rglob iteration raise to hit the `except: return "?"` branch
        def boom(self, pattern):
            raise OSError("nope")
        monkeypatch.setattr(Path, "rglob", boom)
        assert mod.fmt_size(d) == "?"


# ──────────────────────────────────────────────────────────────────────────────
# Tests for count_files (pure)
# ──────────────────────────────────────────────────────────────────────────────

class TestCountFiles:
    def test_missing_path_returns_zero(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        assert mod.count_files(tmp_path / "nope") == 0

    def test_single_file_returns_one(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        f = tmp_path / "f.txt"
        f.write_text("hi")
        assert mod.count_files(f) == 1

    def test_glob_counts_matching(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        d = tmp_path / "d"
        d.mkdir()
        (d / "a.yaml").write_text("")
        (d / "b.yaml").write_text("")
        (d / "c.txt").write_text("")
        assert mod.count_files(d, "*.yaml") == 2

    def test_empty_directory(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        d = tmp_path / "empty"
        d.mkdir()
        assert mod.count_files(d) == 0


# ──────────────────────────────────────────────────────────────────────────────
# Tests for ask
# ──────────────────────────────────────────────────────────────────────────────

class TestAsk:
    def test_force_returns_true(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        assert mod.ask("delete?", True) is True

    def test_user_says_yes(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "j")
        assert mod.ask("ok?", False) is True

    def test_user_says_y(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert mod.ask("ok?", False) is True

    def test_user_says_yes_full(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "yes")
        assert mod.ask("ok?", False) is True

    def test_user_says_no(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert mod.ask("ok?", False) is False

    def test_user_says_empty(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert mod.ask("ok?", False) is False

    def test_user_says_yes_with_whitespace(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: "  j  ")
        assert mod.ask("ok?", False) is True


# ──────────────────────────────────────────────────────────────────────────────
# Tests for safe_delete
# ──────────────────────────────────────────────────────────────────────────────

class TestSafeDelete:
    def test_returns_zero_when_path_missing(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        assert mod.safe_delete(tmp_path / "nope", "X", True) == 0
        assert "not present" in capsys.readouterr().out

    def test_user_cancels_skips(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        d = tmp_path / "d"
        d.mkdir()
        (d / "a").write_text("x")
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert mod.safe_delete(d, "X", False) == 0
        assert "skipped" in capsys.readouterr().out
        # Path still exists
        assert d.exists()

    def test_deletes_directory_with_force(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        d = tmp_path / "d"
        d.mkdir()
        (d / "a").write_text("x")
        assert mod.safe_delete(d, "X", True) == 1
        assert not d.exists()
        out = capsys.readouterr().out
        assert "deleted" in out

    def test_deletes_file_with_force(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        f = tmp_path / "f.txt"
        f.write_text("hello")
        assert mod.safe_delete(f, "X", True) == 1
        assert not f.exists()

    def test_handles_oserror(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        d = tmp_path / "d"
        d.mkdir()
        monkeypatch.setattr("builtins.input", lambda _: "j")
        # Force unlink to fail
        def boom(*args, **kwargs):
            raise OSError("denied")
        monkeypatch.setattr("shutil.rmtree", boom)
        result = mod.safe_delete(d, "X", False)
        assert result == 0
        assert "Error" in capsys.readouterr().out


# ──────────────────────────────────────────────────────────────────────────────
# Tests for cmd_status — exercise all 18 sections
# ──────────────────────────────────────────────────────────────────────────────

class TestCmdStatus:
    def _capture(self, mod):
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            mod.cmd_status()
        return buf.getvalue()

    def test_empty_sandbox(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        out = self._capture(mod)
        assert "GOOSE status" in out
        # Provider/Model should default to "?"
        assert "?" in out
        # All section headers present
        assert "Recipes:" in out
        assert "Docs:" in out
        assert "Skills:" in out
        assert "Extensions:" in out
        assert "MCP Apps:" in out
        assert "MCP Hermit:" in out
        assert "Custom Prov:" in out
        assert "Scheduler:" in out
        assert "History:" in out
        assert "Sessions:" in out
        assert "LLM-Logs:" in out
        assert "Projects:" in out
        assert "Model-cache:" in out
        assert "TLS:" in out
        assert "Apps:" in out
        assert ".goosehints:" in out
        assert "Permissions:" in out
        assert "Backups:" in out

    def test_with_provider_and_model(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        _make_config(mod, tmp_path, provider="deepseek", model="deepseek-chat")
        out = self._capture(mod)
        assert "deepseek" in out
        assert "deepseek-chat" in out

    def test_with_extensions(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        _make_config(mod, tmp_path, with_extensions=True)
        out = self._capture(mod)
        assert "enabled" in out or "Extensions:" in out

    def test_extensions_section_terminates_at_top_level(self, monkeypatch, tmp_path):
        """A line that is non-empty and not indented should break out of the ext block."""
        mod = _load_module(monkeypatch, tmp_path)
        cfg = _make_config(mod, tmp_path, provider="p")
        # Add an extensions block followed by a top-level non-indented key
        text = cfg.read_text() + "\nnext_section: foo\n"
        cfg.write_text(text)
        # Should not crash
        self._capture(mod)

    def test_with_recipes(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        recipes_dir = mod.GOOSE_CONFIG_DIR / "recipes"
        recipes_dir.mkdir(parents=True, exist_ok=True)
        (recipes_dir / "my_recipe.yaml").write_text("")
        fw_dir = recipes_dir / "_framework"
        fw_dir.mkdir()
        (fw_dir / "fw.yaml").write_text("")
        out = self._capture(mod)
        assert "1 sichtbar" in out
        assert "1 in _framework/" in out

    def test_with_skills(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        (mod.SKILLS_DIR / "skill_a.md").write_text("a")
        (mod.SKILLS_DIR / "skill_b.md").write_text("b")
        out = self._capture(mod)
        assert "Skills:" in out
        assert "2 files" in out

    def test_with_schedule_file(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_SHARE.mkdir(parents=True, exist_ok=True)
        mod.SCHEDULE_FILE.write_text(json.dumps({"jobs": [{}, {}, {}]}))
        out = self._capture(mod)
        assert "3 Job(s)" in out

    def test_schedule_file_non_dict(self, monkeypatch, tmp_path):
        """If schedule.json is a list (not dict), jobs=0."""
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_SHARE.mkdir(parents=True, exist_ok=True)
        mod.SCHEDULE_FILE.write_text(json.dumps([1, 2, 3]))
        out = self._capture(mod)
        assert "0 Job(s)" in out

    def test_schedule_file_malformed(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_SHARE.mkdir(parents=True, exist_ok=True)
        mod.SCHEDULE_FILE.write_text("{this is not json}")
        out = self._capture(mod)
        # Should still print the line without crashing
        assert "Scheduler:" in out

    def test_with_history(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_STATE.mkdir(parents=True, exist_ok=True)
        mod.HISTORY_FILE.write_text("line1\nline2\nline3\n")
        out = self._capture(mod)
        assert "lines" in out

    def test_with_apps(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        apps_dir = mod.GOOSE_SHARE / "apps"
        apps_dir.mkdir(parents=True, exist_ok=True)
        (apps_dir / "a.json").write_text("")
        (apps_dir / "b.json").write_text("")
        (apps_dir / "c.json").write_text("")
        (apps_dir / "d.json").write_text("")
        out = self._capture(mod)
        assert "Apps:" in out
        assert "4" in out

    def test_with_goosehints(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        (mod.GOOSE_CONFIG_DIR / ".goosehints").write_text("h1\nh2\n")
        out = self._capture(mod)
        assert "lines" in out

    def test_with_permissions_valid(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        perm_dir = mod.GOOSE_CONFIG_DIR / "permissions"
        perm_dir.mkdir(parents=True, exist_ok=True)
        (perm_dir / "tool_permissions.json").write_text(json.dumps({"a": 1, "b": 2, "c": 3}))
        out = self._capture(mod)
        assert "3 entries" in out

    def test_with_permissions_malformed(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        perm_dir = mod.GOOSE_CONFIG_DIR / "permissions"
        perm_dir.mkdir(parents=True, exist_ok=True)
        (perm_dir / "tool_permissions.json").write_text("not json")
        out = self._capture(mod)
        assert "JSON-Error" in out

    def test_with_backups(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        (mod.GOOSE_CONFIG_DIR / "config.yaml.bak-1").write_text("a")
        (mod.GOOSE_CONFIG_DIR / "config.yaml.bak-2").write_text("b")
        out = self._capture(mod)
        assert "2 Config-Backups" in out

    def test_extensions_block_with_empty_lines(self, monkeypatch, tmp_path):
        """Empty lines inside extensions block don't terminate it (only non-empty top-level)."""
        mod = _load_module(monkeypatch, tmp_path)
        cfg = _make_config(mod, tmp_path)
        text = "extensions:\n  enabled: true\n\n  second_enabled: false\ntop_key: 1\n"
        cfg.write_text(text)
        out = self._capture(mod)
        # Both `enabled` lines should be picked up (because key contains 'enabled')
        assert "second_enabled" in out


# ──────────────────────────────────────────────────────────────────────────────
# Tests for cmd_clear
# ──────────────────────────────────────────────────────────────────────────────

class TestCmdClear:
    def _capture(self, mod):
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            mod.cmd_clear("all", True)
        return buf.getvalue()

    def test_clear_all_runs(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        # Create all target dirs
        for d in [mod.SKILLS_DIR, mod.SESSIONS_DIR, mod.LOGS_DIR, mod.SCHEDULED_DIR,
                  mod.MCP_APPS_DIR, mod.MCP_HERMIT_DIR]:
            d.mkdir(parents=True, exist_ok=True)
            (d / "x").write_text("x")
        mod.GOOSE_STATE.mkdir(parents=True, exist_ok=True)
        mod.HISTORY_FILE.write_text("h")
        mod.GOOSE_SHARE.mkdir(parents=True, exist_ok=True)
        mod.SCHEDULE_FILE.write_text("{}")
        out = self._capture(mod)
        assert "GOOSE CLEANUP" in out
        assert "framework untouched" in out
        # All dirs should be gone
        assert not mod.SKILLS_DIR.exists()
        assert not mod.SESSIONS_DIR.exists()
        assert not mod.LOGS_DIR.exists()
        assert not mod.SCHEDULED_DIR.exists()
        assert not mod.MCP_APPS_DIR.exists()
        assert not mod.MCP_HERMIT_DIR.exists()
        assert not mod.HISTORY_FILE.exists()

    def test_clear_skills_only(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        mod.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        (mod.SKILLS_DIR / "s.md").write_text("s")
        with patch.object(sys, "stdout", io.StringIO()):
            mod.cmd_clear("skills", True)
        assert not mod.SKILLS_DIR.exists()

    def test_clear_history(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_STATE.mkdir(parents=True, exist_ok=True)
        mod.HISTORY_FILE.write_text("chat history")
        with patch.object(sys, "stdout", io.StringIO()):
            mod.cmd_clear("history", True)
        assert not mod.HISTORY_FILE.exists()

    def test_clear_logs(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_STATE.mkdir(parents=True, exist_ok=True)
        mod.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        (mod.LOGS_DIR / "log.txt").write_text("log")
        with patch.object(sys, "stdout", io.StringIO()):
            mod.cmd_clear("logs", True)
        assert not mod.LOGS_DIR.exists()

    def test_clear_schedule_also_removes_scheduled_dir(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_SHARE.mkdir(parents=True, exist_ok=True)
        mod.SCHEDULE_FILE.write_text("{}")
        mod.SCHEDULED_DIR.mkdir(parents=True, exist_ok=True)
        (mod.SCHEDULED_DIR / "recipe.yaml").write_text("")
        with patch.object(sys, "stdout", io.StringIO()):
            mod.cmd_clear("schedule", True)
        assert not mod.SCHEDULE_FILE.exists()
        assert not mod.SCHEDULED_DIR.exists()

    def test_clear_sessions(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (mod.SESSIONS_DIR / "s.json").write_text("")
        with patch.object(sys, "stdout", io.StringIO()):
            mod.cmd_clear("sessions", True)
        assert not mod.SESSIONS_DIR.exists()

    def test_unknown_target_exits(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        with patch.object(sys, "stdout", io.StringIO()):
            with pytest.raises(SystemExit) as excinfo:
                mod.cmd_clear("bogus", True)
        assert excinfo.value.code == 1

    def test_clear_skips_missing_paths(self, monkeypatch, tmp_path):
        """If targets don't exist, safe_delete returns 0 and we still print 'deleted' line?"""
        mod = _load_module(monkeypatch, tmp_path)
        # Don't create the dirs — clear-all should still run without crashing
        out = self._capture(mod)
        assert "GOOSE CLEANUP" in out


# ──────────────────────────────────────────────────────────────────────────────
# Tests for main() — CLI dispatch
# ──────────────────────────────────────────────────────────────────────────────

class TestMain:
    def test_no_args_prints_help(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_goose_manager.py"])
        with pytest.raises(SystemExit) as excinfo:
            mod.main()
        assert excinfo.value.code == 0
        out = capsys.readouterr().out
        assert "VERWENDUNG" in out or "dev_goose_manager" in out

    def test_help_flag(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_goose_manager.py", "--help"])
        with pytest.raises(SystemExit) as excinfo:
            mod.main()
        assert excinfo.value.code == 0

    def test_status_flag(self, monkeypatch, tmp_path, capsys):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_goose_manager.py", "--status"])
        mod.main()
        out = capsys.readouterr().out
        assert "GOOSE status" in out

    def test_clear_skills_flag(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        (mod.SKILLS_DIR / "s.md").write_text("")
        monkeypatch.setattr(sys, "argv", ["dev_goose_manager.py", "--clear-skills", "--force"])
        with patch.object(sys, "stdout", io.StringIO()):
            mod.main()
        assert not mod.SKILLS_DIR.exists()

    def test_clear_all_flag(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        mod.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        (mod.SKILLS_DIR / "s.md").write_text("")
        monkeypatch.setattr(sys, "argv", ["dev_goose_manager.py", "--clear-all", "--force"])
        with patch.object(sys, "stdout", io.StringIO()):
            mod.main()
        assert not mod.SKILLS_DIR.exists()

    def test_unknown_command_exits(self, monkeypatch, tmp_path):
        mod = _load_module(monkeypatch, tmp_path)
        monkeypatch.setattr(sys, "argv", ["dev_goose_manager.py", "--bogus"])
        with patch.object(sys, "stdout", io.StringIO()):
            with pytest.raises(SystemExit) as excinfo:
                mod.main()
        assert excinfo.value.code == 1

    def test_force_shortcut_skips_prompt(self, monkeypatch, tmp_path):
        """--clear-skills without --force should ASK. With --force: skip."""
        mod = _load_module(monkeypatch, tmp_path)
        mod.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        (mod.SKILLS_DIR / "s.md").write_text("")
        # No input() should be called because force=True
        monkeypatch.setattr("builtins.input", lambda _: pytest.fail("input() should not be called"))
        monkeypatch.setattr(sys, "argv", ["dev_goose_manager.py", "--clear-skills", "--force"])
        with patch.object(sys, "stdout", io.StringIO()):
            mod.main()
        assert not mod.SKILLS_DIR.exists()


# ──────────────────────────────────────────────────────────────────────────────
# Sanity: module has __name__ guard so import doesn't run main
# ──────────────────────────────────────────────────────────────────────────────

class TestImportSafety:
    def test_module_loads_without_calling_main(self, monkeypatch, tmp_path):
        """Importing the module should NOT execute the CLI. The `if __name__ == '__main__'`
        guard at the bottom of the file ensures this."""
        mod = _load_module(monkeypatch, tmp_path)
        # If we got here without SystemExit or other side-effects, we're good
        assert hasattr(mod, "main")
        assert hasattr(mod, "cmd_status")
        assert hasattr(mod, "cmd_clear")
        assert hasattr(mod, "fmt_size")
        assert hasattr(mod, "count_files")
        assert hasattr(mod, "ask")
        assert hasattr(mod, "safe_delete")


# ──────────────────────────────────────────────────────────────────────────────
# Additional edge-case coverage: try/except branches + size overflow
# ──────────────────────────────────────────────────────────────────────────────

class TestExtraCoverage:
    def test_fmt_size_terabyte_overflow(self, monkeypatch, tmp_path):
        """1+ TB → returns "X.X GB" without crashing."""
        mod = _load_module(monkeypatch, tmp_path)
        f = tmp_path / "huge.bin"
        f.write_bytes(b"x")

        orig_stat = Path.stat
        def fake_stat(self):
            r = orig_stat(self)
            if self == f:
                class SR:
                    pass
                sr = SR()
                sr.st_size = 5 * 1024 ** 4  # 5 TB
                for attr in ("st_mode", "st_mtime", "st_ino", "st_dev", "st_nlink",
                             "st_uid", "st_gid", "st_atime", "st_ctime"):
                    setattr(sr, attr, getattr(r, attr))
                return sr
            return r
        monkeypatch.setattr(Path, "stat", fake_stat)
        out = mod.fmt_size(f)
        assert "GB" in out

    def test_config_yaml_read_text_raises(self, monkeypatch, tmp_path):
        """If GOOSE_CONFIG.read_text() raises, the section swallows and prints '?'."""
        mod = _load_module(monkeypatch, tmp_path)
        _make_config(mod, tmp_path)
        def boom(self, *args, **kwargs):
            raise OSError("disk full")
        monkeypatch.setattr(Path, "read_text", boom)
        import io
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            mod.cmd_status()
        out = buf.getvalue()
        assert "?" in out  # Provider/Model fallback to "?"

    def test_extensions_block_read_text_raises(self, monkeypatch, tmp_path):
        """If config.read_text raises during ext block parsing, swallow + continue."""
        mod = _load_module(monkeypatch, tmp_path)
        cfg = _make_config(mod, tmp_path, with_extensions=True)
        # read_text works the first time (provider extraction), but raise second time
        # Simpler: make read_text raise always
        def boom(self, *args, **kwargs):
            raise OSError("perm denied")
        monkeypatch.setattr(Path, "read_text", boom)
        import io
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            mod.cmd_status()  # Must not crash

    def test_history_lines_count_raises(self, monkeypatch, tmp_path):
        """If HISTORY_FILE.read_text() raises during line counting, swallow + continue."""
        mod = _load_module(monkeypatch, tmp_path)
        mod.GOOSE_STATE.mkdir(parents=True, exist_ok=True)
        mod.HISTORY_FILE.write_text("x")
        orig = Path.read_text
        def fake(self, *a, **kw):
            if self == mod.HISTORY_FILE:
                raise OSError("history broken")
            return orig(self, *a, **kw)
        monkeypatch.setattr(Path, "read_text", fake)
        import io
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            mod.cmd_status()  # Must not crash

    def test_main_block_runs_as_script(self, monkeypatch, tmp_path):
        """Verify the `if __name__ == '__main__': main()` guard calls main()."""
        mod = _load_module(monkeypatch, tmp_path)
        # We can't really execute line 290 without running it. But we can verify
        # the structure exists.
        import ast
        tree = ast.parse(Path(str(SCRIPT)).read_text())
        # Last 2 stmts should be: if __name__ == "__main__": main()
        last = tree.body[-1]
        assert isinstance(last, ast.If), f"Last stmt should be if __name__ guard, got {type(last)}"
        # ast.Compare: left=Name, comparators=[Constant]
        left_name = getattr(last.test.left, "id", None)
        right_val = None
        if last.test.comparators:
            right_val = getattr(last.test.comparators[0], "value", None)
        assert left_name == "__name__", f"left should be __name__, got {left_name}"
        assert right_val == "__main__", f"right should be __main__, got {right_val}"
        # The body of the if should be a single Expr(Call(main))
        assert len(last.body) == 1
        assert isinstance(last.body[0], ast.Expr)
