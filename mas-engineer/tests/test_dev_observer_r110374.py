"""
test_dev_observer_r110374.py — coverage push for
tools/dev_observer.py (R110-374, 2026-09-08).

The python module tools/dev_observer.py is currently 0%-covered
(the existing tests/test_sub_mas_dev_observer.py only validates
the recipe YAML, not the python module). R110-374 adds direct
unit tests for every public function and class:

  - resolve_agent_dir()         — path resolution
  - get_agent_dir() / get_state_dir() — lazy loaders
  - FileInfo                    — class (file metadata)
  - YamlDetail                  — class (yaml field extraction)
  - Scanner                     — class (full/quick/yaml scans)
  - save_scan()                 — writes .mase/analysis.json
  - main()                      — argparse CLI entry point

dev_observer.py has no module-level side effects (no
check_spec_drift or SCAN_SCOPE calls), so the simpler import
pattern works (no r110347 sandbox needed).
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ═══════════════════════════════════════════════
#  Module-level import
# ═══════════════════════════════════════════════

TOOLS_DIR = Path(__file__).parent.parent / "tools"


def _import_dev_observer():
    """Import via sys.path so coverage.py tracks the module.
    (importlib.util.spec_from_file_location does NOT register
    the module in a way that pytest-cov can follow.)"""
    import sys
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import dev_observer
    return dev_observer


@pytest.fixture(scope="module")
def dobs():
    """Module fixture — import once for the whole test file."""
    return _import_dev_observer()


# ═══════════════════════════════════════════════
#  resolve_agent_dir()
# ═══════════════════════════════════════════════

class TestResolveAgentDir:
    def test_workspace_arg_takes_precedence(self, dobs, tmp_path):
        """--workspace <dir> returns that path if it exists."""
        # Create a fake workspace with recipes subdir
        recipes = tmp_path / "recipes"
        recipes.mkdir()
        with patch.object(sys, "argv", ["dev_observer.py", "--workspace", str(tmp_path)]):
            result = dobs.resolve_agent_dir()
        assert result == tmp_path.resolve()

    def test_workspace_nonexistent_falls_through(self, dobs, tmp_path):
        """--workspace <missing-dir> falls through to default."""
        missing = tmp_path / "no-such-dir"
        with patch.object(sys, "argv", ["dev_observer.py", "--workspace", str(missing)]):
            result = dobs.resolve_agent_dir()
        # Should fall through to the default path
        assert result is not None

    def test_no_args_returns_path(self, dobs):
        """No args → still returns a path (default)."""
        with patch.object(sys, "argv", ["dev_observer.py"]):
            result = dobs.resolve_agent_dir()
        assert isinstance(result, Path)


# ═══════════════════════════════════════════════
#  get_agent_dir() / get_state_dir()
# ═══════════════════════════════════════════════

class TestLazyLoaders:
    def test_get_agent_dir_returns_path(self, dobs):
        """get_agent_dir returns a Path object."""
        dobs._AGENT_DIR = None  # reset cache
        result = dobs.get_agent_dir()
        assert isinstance(result, Path)
        # Caching: second call returns same object
        assert dobs.get_agent_dir() is result

    def test_get_state_dir_returns_path(self, dobs):
        """get_state_dir returns a Path under .mase/."""
        dobs._STATE_DIR = None
        result = dobs.get_state_dir()
        assert isinstance(result, Path)
        # Path should end with .mase
        assert result.name == ".mase"


# ═══════════════════════════════════════════════
#  FileInfo class
# ═══════════════════════════════════════════════

class TestFileInfo:
    def test_yaml_file(self, dobs, tmp_path):
        """A .yaml file is detected as yaml."""
        f = tmp_path / "test.yaml"
        f.write_text("key: value\nline2: 2\n")
        info = dobs.FileInfo(f)
        assert info.is_yaml is True
        assert info.is_md is False
        assert info.is_py is False
        assert info.ext == ".yaml"
        assert info.size > 0
        # 2 content lines
        assert info.lines == 2

    def test_yml_file(self, dobs, tmp_path):
        """A .yml file is detected as yaml."""
        f = tmp_path / "test.yml"
        f.write_text("a: 1\n")
        info = dobs.FileInfo(f)
        assert info.is_yaml is True

    def test_md_file(self, dobs, tmp_path):
        """A .md file is detected as md."""
        f = tmp_path / "test.md"
        f.write_text("# Title\n\nBody.\n")
        info = dobs.FileInfo(f)
        assert info.is_md is True
        assert info.is_yaml is False

    def test_py_file(self, dobs, tmp_path):
        """A .py file is detected as py."""
        f = tmp_path / "test.py"
        f.write_text("print('hi')\n")
        info = dobs.FileInfo(f)
        assert info.is_py is True
        assert info.is_yaml is False
        assert info.is_md is False

    def test_size_kb_rounded(self, dobs, tmp_path):
        """size_kb is rounded to 1 decimal."""
        f = tmp_path / "big.yaml"
        f.write_text("x" * 2048)  # 2KB
        info = dobs.FileInfo(f)
        assert info.size_kb == 2.0

    def test_rel_path_relative_to_agent_dir(self, dobs, tmp_path):
        """rel_path is relative to agent_dir if file is under it."""
        # Create agent_dir and nested file
        agent = tmp_path / "agent"
        sub = agent / "sub"
        sub.mkdir(parents=True)
        f = sub / "test.yaml"
        f.write_text("k: v\n")
        with patch.object(dobs, "get_agent_dir", return_value=agent):
            info = dobs.FileInfo(f)
        assert info.rel_path == "sub/test.yaml"

    def test_rel_path_absolute_when_outside(self, dobs, tmp_path):
        """rel_path falls back to absolute if file is outside agent_dir."""
        f = tmp_path / "outside.yaml"
        f.write_text("k: v\n")
        # Use a different agent dir so relative_to fails
        with patch.object(dobs, "get_agent_dir", return_value=tmp_path / "different"):
            info = dobs.FileInfo(f)
        # Falls back to absolute str(path)
        assert info.rel_path == str(f)

    def test_count_lines_handles_binary(self, dobs, tmp_path):
        """_count_lines returns 0 on binary file (errors ignored)."""
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\xff")
        info = dobs.FileInfo(f)
        # Should not raise, returns a number
        assert isinstance(info.lines, int)
        assert info.lines >= 0


# ═══════════════════════════════════════════════
#  YamlDetail class
# ═══════════════════════════════════════════════

class TestYamlDetail:
    def test_empty_file(self, dobs, tmp_path):
        """Empty yaml file → defaults."""
        f = tmp_path / "empty.yaml"
        f.write_text("")
        d = dobs.YamlDetail(f)
        assert d.has_slash is False
        assert d.has_settings is False
        assert d.title == ""
        assert d.instr_lines == 0
        assert d.prompt_lines == 0
        # 0 newlines + 1
        assert d.lines_total == 1

    def test_slash_command_extracted(self, dobs, tmp_path):
        """slash_command: <name> → has_slash=True, slash_cmd=name."""
        f = tmp_path / "with-slash.yaml"
        f.write_text("slash_command: my-command\n")
        d = dobs.YamlDetail(f)
        assert d.has_slash is True
        assert d.slash_cmd == "my-command"

    def test_title_with_quotes(self, dobs, tmp_path):
        """title with double-quotes is stripped."""
        f = tmp_path / "titled.yaml"
        f.write_text('title: "My Agent"\n')
        d = dobs.YamlDetail(f)
        assert d.title == "My Agent"

    def test_title_with_single_quotes(self, dobs, tmp_path):
        """title with single-quotes is stripped."""
        f = tmp_path / "titled2.yaml"
        f.write_text("title: 'My Agent'\n")
        d = dobs.YamlDetail(f)
        assert d.title == "My Agent"

    def test_title_no_quotes(self, dobs, tmp_path):
        """title without quotes is taken as-is."""
        f = tmp_path / "titled3.yaml"
        f.write_text("title: MyAgent\n")
        d = dobs.YamlDetail(f)
        assert d.title == "MyAgent"

    def test_settings_detected(self, dobs, tmp_path):
        """settings: key → has_settings=True."""
        f = tmp_path / "with-settings.yaml"
        f.write_text("settings:\n  key1: val1\n  key2: val2\n")
        d = dobs.YamlDetail(f)
        assert d.has_settings is True

    def test_no_settings(self, dobs, tmp_path):
        """No settings: key → has_settings=False."""
        f = tmp_path / "no-settings.yaml"
        f.write_text("title: foo\ninstructions: bar\n")
        d = dobs.YamlDetail(f)
        assert d.has_settings is False

    def test_instructions_counted(self, dobs, tmp_path):
        """Lines under instructions: are counted (non-empty)."""
        f = tmp_path / "with-instr.yaml"
        f.write_text(
            "instructions:\n"
            "  This is line one.\n"
            "  This is line two.\n"
            "  This is line three.\n"
        )
        d = dobs.YamlDetail(f)
        assert d.instr_lines == 3
        assert d.prompt_lines == 0

    def test_prompt_counted(self, dobs, tmp_path):
        """Lines under prompt: are counted (non-empty)."""
        f = tmp_path / "with-prompt.yaml"
        f.write_text(
            "prompt:\n"
            "  Prompt line A.\n"
            "  Prompt line B.\n"
        )
        d = dobs.YamlDetail(f)
        assert d.prompt_lines == 2
        assert d.instr_lines == 0

    def test_instructions_then_prompt(self, dobs, tmp_path):
        """Switching from instructions to prompt resets the counter."""
        f = tmp_path / "both.yaml"
        f.write_text(
            "instructions:\n"
            "  One\n"
            "  Two\n"
            "prompt:\n"
            "  A\n"
            "  B\n"
            "  C\n"
        )
        d = dobs.YamlDetail(f)
        assert d.instr_lines == 2
        assert d.prompt_lines == 3


# ═══════════════════════════════════════════════
#  Scanner class
# ═══════════════════════════════════════════════

class TestScanner:
    def test_init_default_path(self, dobs, tmp_path):
        """Scanner() uses get_agent_dir() when no path given."""
        with patch.object(dobs, "get_agent_dir", return_value=tmp_path):
            scanner = dobs.Scanner()
        assert scanner.agent_path == tmp_path
        assert scanner.files == []
        assert scanner.yamls == []
        assert scanner.error_messages == []

    def test_init_explicit_path(self, dobs, tmp_path):
        """Scanner(path) uses the given path."""
        scanner = dobs.Scanner(tmp_path)
        assert scanner.agent_path == tmp_path

    def test_collect_empty_dir(self, dobs, tmp_path):
        """_collect on empty dir → no files."""
        scanner = dobs.Scanner(tmp_path)
        scanner._collect()
        assert scanner.files == []
        assert scanner.yamls == []

    def test_collect_finds_nested_files(self, dobs, tmp_path):
        """_collect uses rglob so it finds files in subdirs."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "a.yaml").write_text("k: v\n")
        (sub / "b.md").write_text("# x\n")
        (tmp_path / "top.py").write_text("x = 1\n")
        scanner = dobs.Scanner(tmp_path)
        scanner._collect()
        paths = {str(f.path.name) for f in scanner.files}
        assert paths == {"a.yaml", "b.md", "top.py"}

    def test_collect_picks_up_yaml_details(self, dobs, tmp_path):
        """_collect populates self.yamls for .yaml files."""
        (tmp_path / "x.yaml").write_text("title: foo\nslash_command: bar\n")
        scanner = dobs.Scanner(tmp_path)
        scanner._collect()
        assert len(scanner.yamls) == 1
        assert scanner.yamls[0].has_slash is True
        assert scanner.yamls[0].slash_cmd == "bar"

    def test_get_dirs_returns_sorted(self, dobs, tmp_path):
        """_get_dirs returns subdirs sorted by name."""
        (tmp_path / "zeta").mkdir()
        (tmp_path / "alpha").mkdir()
        (tmp_path / "middle").mkdir()
        scanner = dobs.Scanner(tmp_path)
        dirs = scanner._get_dirs()
        names = [d.name for d in dirs]
        assert names == sorted(names)

    def test_scan_full_returns_string(self, dobs, tmp_path):
        """scan_full returns a non-empty string with the header."""
        (tmp_path / "x.yaml").write_text("title: Test\n")
        scanner = dobs.Scanner(tmp_path)
        result = scanner.scan_full()
        assert isinstance(result, str)
        assert "FRAMEWORK-SCAN" in result
        assert "OVERVIEW" in result

    def test_scan_full_summary_section(self, dobs, tmp_path):
        """scan_full ends with a SUMMARY section."""
        (tmp_path / "a.yaml").write_text("title: A\n")
        (tmp_path / "b.md").write_text("# B\n")
        scanner = dobs.Scanner(tmp_path)
        result = scanner.scan_full()
        assert "SUMMARY" in result
        assert "YAMLs" in result

    def test_scan_quick_returns_overview(self, dobs, tmp_path):
        """scan_quick returns a short overview string."""
        (tmp_path / "x.yaml").write_text("title: foo\n")
        scanner = dobs.Scanner(tmp_path)
        result = scanner.scan_quick()
        assert "FRAMEWORK-OVERVIEW" in result
        assert "YAML" in result
        # scan_quick should be shorter than scan_full
        full = scanner.scan_full()
        assert len(result) < len(full)

    def test_scan_yaml_existing(self, dobs, tmp_path):
        """scan_yaml(<rel>) shows file details."""
        (tmp_path / "test.yaml").write_text(
            "title: 'Test Recipe'\n"
            "slash_command: do-thing\n"
            "settings:\n  model: foo\n"
        )
        scanner = dobs.Scanner(tmp_path)
        result = scanner.scan_yaml("test.yaml")
        assert "Test Recipe" in result
        assert "do-thing" in result

    def test_scan_yaml_missing(self, dobs, tmp_path):
        """scan_yaml(<missing>) returns an error message."""
        scanner = dobs.Scanner(tmp_path)
        result = scanner.scan_yaml("does-not-exist.yaml")
        assert "Nicht found" in result


# ═══════════════════════════════════════════════
#  save_scan()
# ═══════════════════════════════════════════════

class TestSaveScan:
    def test_writes_analysis_json(self, dobs, tmp_path):
        """save_scan writes analysis.json with expected keys."""
        # Set up scanner with known content
        agent = tmp_path / "agent"
        agent.mkdir()
        (agent / "a.yaml").write_text("title: A\nslash_command: cmd-a\n")
        (agent / "b.md").write_text("# B\n")
        state = tmp_path / ".mase"
        scanner = dobs.Scanner(agent)
        with patch.object(dobs, "get_state_dir", return_value=state):
            result = dobs.save_scan(scanner)
        # Verify file exists
        out = state / "analysis.json"
        assert out.exists()
        # Verify content
        with open(out) as f:
            data = json.load(f)
        assert "timestamp" in data
        assert "total_files" in data
        assert data["yaml_count"] == 1
        assert data["md_count"] == 1
        assert data["with_slash"] == 1
        assert "✅" in result

    def test_creates_parent_dirs(self, dobs, tmp_path):
        """save_scan creates .mase/ if it doesn't exist."""
        agent = tmp_path / "agent"
        agent.mkdir()
        (agent / "x.yaml").write_text("k: v\n")
        # State dir does not exist yet
        state = tmp_path / "deep" / "nested" / ".mase"
        assert not state.exists()
        scanner = dobs.Scanner(agent)
        with patch.object(dobs, "get_state_dir", return_value=state):
            dobs.save_scan(scanner)
        assert state.exists()
        assert (state / "analysis.json").exists()


# ═══════════════════════════════════════════════
#  main() — CLI smoke
# ═══════════════════════════════════════════════

class TestMainCli:
    def test_scan_flag_runs_scan_full(self, dobs, tmp_path, capsys):
        """--scan runs scan_full and prints result."""
        (tmp_path / "x.yaml").write_text("title: T\n")
        with patch.object(sys, "argv", ["dev_observer.py", "--scan", "--agent-path", str(tmp_path)]):
            dobs.main()
        captured = capsys.readouterr()
        assert "FRAMEWORK-SCAN" in captured.out

    def test_quick_flag_runs_scan_quick(self, dobs, tmp_path, capsys):
        """--quick runs scan_quick."""
        (tmp_path / "x.yaml").write_text("title: T\n")
        with patch.object(sys, "argv", ["dev_observer.py", "--quick", "--agent-path", str(tmp_path)]):
            dobs.main()
        captured = capsys.readouterr()
        assert "FRAMEWORK-OVERVIEW" in captured.out

    def test_yaml_flag_runs_scan_yaml(self, dobs, tmp_path, capsys):
        """--yaml <path> runs scan_yaml on a single file."""
        (tmp_path / "single.yaml").write_text("title: 'Single'\n")
        with patch.object(sys, "argv", ["dev_observer.py", "--yaml", "single.yaml", "--agent-path", str(tmp_path)]):
            dobs.main()
        captured = capsys.readouterr()
        assert "Single" in captured.out

    def test_missing_agent_path_exits(self, dobs, tmp_path, capsys):
        """--agent-path <missing> → sys.exit(1)."""
        missing = tmp_path / "no-such-agent"
        with patch.object(sys, "argv", ["dev_observer.py", "--scan", "--agent-path", str(missing)]):
            with pytest.raises(SystemExit) as exc:
                dobs.main()
            assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "❌" in captured.out

    def test_yaml_dir_flag_loops(self, dobs, tmp_path, capsys):
        """--yaml-dir <path> loops over yamls in that dir."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "a.yaml").write_text("title: A\n")
        (sub / "b.yaml").write_text("title: B\n")
        with patch.object(sys, "argv", ["dev_observer.py", "--yaml-dir", "subdir", "--agent-path", str(tmp_path)]):
            dobs.main()
        captured = capsys.readouterr()
        # Both should appear in output
        assert "A" in captured.out
        assert "B" in captured.out
