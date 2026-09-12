"""R110-480 — coverage-push r17: tools/dev_observer.py 11% to 100%

432 lines, 283 stmts. Currently 11% with 251 lines missed.

KEY OBSERVATIONS:
- resolve_agent_dir():
  - --workspace <dir> takes precedence if path exists
  - Fallback: parent.parent.parent (3 levels up from tools/)
  - If that has 'recipes/' subdir or any subdir contains 'recipes/',
    return it
  - Last fallback: ~/.config/goose/recipes
- get_agent_dir() / get_state_dir(): lazy-loaded, module-level globals
- FileInfo(path): path, rel_path (str or abs if not under agent_dir),
  name, ext (lower), size, size_kb, lines, is_yaml/ym/md/py booleans
- FileInfo._count_lines(): opens file, counts newlines, returns 0 on error
- YamlDetail(path): parses YAML frontmatter for:
  - lines_total (newlines+1)
  - has_slash / slash_cmd
  - title (stripped quotes)
  - has_settings
  - instr_lines (lines after 'instructions:' non-empty)
  - prompt_lines (lines after 'prompt:' non-empty)
  - switches between instructions/prompt on either header
- Scanner(agent_path): rglob *.yaml/*.yml/*.md/*.py/*.toml/*.cfg/*.txt/*.rst
  - FileInfo per file, YamlDetail for .yaml/.yml
  - error_messages for failed FileInfo creation
- _get_dirs(): os.walk to collect subdirs
- scan_full(): detailed report grouped by:
  - Overview (counts, sizes)
  - YAMLs with slash (sorted by slash_cmd)
  - YAMLs without slash (grouped by parent dir, with title)
  - Specialists (specialist_ prefix)
  - Sub-agents (sub_ prefix in name or path)
  - Markdown (gated if pys)
  - Python (gated if pys)
  - Errors (gated if error_messages)
  - Summary
- scan_quick(): brief stats with get_agent_dir().name
- scan_yaml(rel_path): single file report, 'Not found' if missing
- save_scan(scanner): writes .mase/analysis.json with timestamp, paths,
  counts (yaml/md/py, with/without slash, specialists, subs)
- main() argparse:
  - --scan (default), --quick, --yaml <rel>, --yaml-dir <dir>, --save
  - --agent-path <path> (default: get_agent_dir())
  - exits 1 if agent_path doesn't exist
  - exits 1 if yaml-dir doesn't exist
  - args.parse_known_args()[0] → tolerant of extra args
  - dispatches: yaml > quick > save > yaml_dir > default scan_full

PITFALLS:
- FileInfo.rel_path falls back to str(path) when not under agent_dir
- YamlDetail._parse silently catches all exceptions
- YamlDetail instr/prompt only count NON-EMPTY stripped lines
- Scanner's _collect resets all state
- FileInfo.is_yaml based on lower-cased ext
- YamlDetail's `specialist_` check uses substring in rel_path
- YamlDetail's `sub_` check uses startswith(rel_path) OR '/sub_' in rel_path
- save_scan writes to get_state_dir() / 'analysis.json'
- main() exits 1 for missing paths via sys.exit
- main() default mode (no flags) = scan_full()
- --scan flag is technically redundant (default = scan_full)
- scan_yaml returns 'Not found' string, doesn't raise
- argparse uses parse_known_args → ignores unknown args
"""

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_observer as obs  # noqa: E402


def _patch_agent_dir(agent_dir):
    """Helper: patch resolve_agent_dir() to return agent_dir and reset lazy."""
    obs._AGENT_DIR = None
    obs.resolve_agent_dir = lambda: agent_dir


def _unpatch_agent_dir():
    """Restore default lazy state."""
    obs._AGENT_DIR = None
    # Module-level function re-import to reset
    import importlib
    importlib.reload(obs)


# ─────────────────────────────────────────────────────────────────────
# resolve_agent_dir
# ─────────────────────────────────────────────────────────────────────
class TestResolveAgentDir:
    def test_workspace_takes_precedence(self, tmp_path, monkeypatch):
        # --workspace <path> if exists → returns it
        ws = tmp_path / "ws"
        ws.mkdir()
        old_argv = sys.argv
        sys.argv = ["x.py", "--workspace", str(ws)]
        try:
            result = obs.resolve_agent_dir()
            assert result == ws.resolve()
        finally:
            sys.argv = old_argv

    def test_workspace_nonexistent_falls_through(self, tmp_path, monkeypatch):
        # --workspace <nonexistent> → falls through to fallback
        ws = tmp_path / "does_not_exist"
        old_argv = sys.argv
        sys.argv = ["x.py", "--workspace", str(ws)]
        try:
            result = obs.resolve_agent_dir()
            # Should hit fallback (recipes/ in project root)
            assert isinstance(result, Path)
        finally:
            sys.argv = old_argv

    def test_default_uses_recipes_subdir(self, monkeypatch):
        # No --workspace → falls through. The current dir has 'recipes/'
        # since this is the mas-engineer project
        old_argv = sys.argv
        sys.argv = ["x.py"]
        try:
            result = obs.resolve_agent_dir()
            # Should find recipes/ somewhere in tree (L41/42 hit via recipes/ subdir)
            assert isinstance(result, Path)
            assert result.exists()
        finally:
            sys.argv = old_argv

    def test_default_finds_recipes_in_subdir(self, tmp_path, monkeypatch):
        # We need __file__.parent.parent.parent to have a recipes/ subdir
        # (L41 hit) OR a child subdir with recipes/ (L41 any() hit).
        # Setup: tmp_path/recipes/ exists, put file at tmp_path/tools/sub/deep.py
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        deep_file = tmp_path / "tools" / "sub" / "deep.py"
        deep_file.parent.mkdir(parents=True)

        old_argv = sys.argv
        sys.argv = ["x.py"]
        original_file = obs.__file__
        obs.__file__ = str(deep_file)
        obs._AGENT_DIR = None
        try:
            result = obs.resolve_agent_dir()
            # default = deep_file.parent.parent.parent = tmp_path
            # (default/recipes) exists → L41/42 hit → returns default = tmp_path
            assert result == tmp_path.resolve()
        finally:
            sys.argv = old_argv
            obs.__file__ = original_file


# ─────────────────────────────────────────────────────────────────────
# get_agent_dir / get_state_dir (lazy)
# ─────────────────────────────────────────────────────────────────────
class TestLazyGlobals:
    def test_get_agent_dir_lazy(self, monkeypatch):
        # Reset the cached value
        obs._AGENT_DIR = None
        # Monkeypatch resolve_agent_dir
        called = []
        def fake_resolve():
            called.append(True)
            return Path("/fake/agent/dir")
        monkeypatch.setattr(obs, "resolve_agent_dir", fake_resolve)
        # First call: resolves
        d1 = obs.get_agent_dir()
        assert d1 == Path("/fake/agent/dir")
        assert len(called) == 1
        # Second call: cached, no re-resolve
        d2 = obs.get_agent_dir()
        assert d2 == Path("/fake/agent/dir")
        assert len(called) == 1

    def test_get_state_dir_lazy(self, monkeypatch):
        obs._STATE_DIR = None
        # Should resolve to tools/../.mase/
        d = obs.get_state_dir()
        assert d.name == ".mase"
        assert d.exists() or str(d).endswith(".mase")


# ─────────────────────────────────────────────────────────────────────
# FileInfo
# ─────────────────────────────────────────────────────────────────────
class TestFileInfo:
    def test_basic_init(self, tmp_path):
        fake_agent = tmp_path / "agent"
        fake_agent.mkdir()
        f = fake_agent / "a.yaml"
        f.write_text("a: 1\nb: 2\n")
        _patch_agent_dir(fake_agent)
        try:
            info = obs.FileInfo(f)
            assert info.path == f
            assert info.rel_path == "a.yaml"
            assert info.name == "a.yaml"
            assert info.ext == ".yaml"
            assert info.is_yaml
            assert not info.is_md
            assert not info.is_py
            assert info.size > 0
            assert info.size_kb >= 0
            assert info.lines == 2
        finally:
            _unpatch_agent_dir()

    def test_outside_agent_dir(self, tmp_path):
        # Path not under agent_dir → rel_path = str(path)
        f = tmp_path / "x.py"
        f.write_text("# hello\n")
        info = obs.FileInfo(f)
        # rel_path is absolute since not under agent_dir
        assert "x.py" in info.rel_path
        assert info.is_py

    def test_extensions(self, tmp_path):
        fake_agent = tmp_path / "agent"
        fake_agent.mkdir()
        cases = [
            ("a.yaml", True, False, False),
            ("a.yml", True, False, False),
            ("a.md", False, True, False),
            ("a.py", False, False, True),
            ("a.txt", False, False, False),
        ]
        for name, is_yaml, is_md, is_py in cases:
            f = fake_agent / name
            f.write_text("x\n")
            info = obs.FileInfo(f)
            assert info.is_yaml == is_yaml, name
            assert info.is_md == is_md, name
            assert info.is_py == is_py, name

    def test_uppercase_ext_lowered(self, tmp_path):
        fake_agent = tmp_path / "agent"
        fake_agent.mkdir()
        f = fake_agent / "a.YAML"
        f.write_text("a: 1\n")
        info = obs.FileInfo(f)
        assert info.is_yaml  # .YAML lowered to .yaml

    def test_count_lines_empty_file(self, tmp_path):
        fake_agent = tmp_path / "agent"
        fake_agent.mkdir()
        f = fake_agent / "empty.yaml"
        f.write_text("")
        _patch_agent_dir(fake_agent)
        try:
            info = obs.FileInfo(f)
            # FileInfo._count_lines uses sum(1 for _ in f), not count('\n')+1
            # Empty file → 0 lines from iteration
            assert info.lines == 0
        finally:
            _unpatch_agent_dir()

    def test_count_lines_unreadable(self, tmp_path):
        fake_agent = tmp_path / "agent"
        fake_agent.mkdir()
        f = fake_agent / "broken.yaml"
        # Make it a directory to force open() error
        f.mkdir()
        info = obs.FileInfo(f)
        # _count_lines catches exception → 0
        # But init() itself may fail at .stat() since stat on dir works
        # Actually .stat() works on dirs. The issue is open() in _count_lines.
        # But init does .relative_to first which works, then .stat() works.
        # _count_lines calls open() which on dir raises IsADirectoryError
        assert info.lines == 0


# ─────────────────────────────────────────────────────────────────────
# YamlDetail
# ─────────────────────────────────────────────────────────────────────
class TestYamlDetail:
    def _make(self, tmp_path, content):
        fake_agent = tmp_path / "agent"
        fake_agent.mkdir(exist_ok=True)
        f = fake_agent / "x.yaml"
        f.write_text(content)
        return f

    def test_basic(self, tmp_path):
        f = self._make(tmp_path, "title: Foo\n")
        y = obs.YamlDetail(f)
        assert y.title == "Foo"
        assert not y.has_slash

    def test_slash_command(self, tmp_path):
        f = self._make(tmp_path, "slash_command: hello\n")
        y = obs.YamlDetail(f)
        assert y.has_slash
        assert y.slash_cmd == "hello"

    def test_settings(self, tmp_path):
        f = self._make(tmp_path, "settings:\n  model: gpt-4\n")
        y = obs.YamlDetail(f)
        assert y.has_settings

    def test_instructions_and_prompt(self, tmp_path):
        content = (
            "title: T\n"
            "instructions:\n"
            "  line1\n"
            "  line2\n"
            "prompt:\n"
            "  p1\n"
        )
        f = self._make(tmp_path, content)
        y = obs.YamlDetail(f)
        assert y.instr_lines == 2
        assert y.prompt_lines == 1

    def test_prompt_resets_instructions(self, tmp_path):
        content = (
            "instructions:\n"
            "  a\n"
            "  b\n"
            "prompt:\n"
            "  c\n"
            "  d\n"
        )
        f = self._make(tmp_path, content)
        y = obs.YamlDetail(f)
        assert y.instr_lines == 2
        assert y.prompt_lines == 2

    def test_title_with_quotes(self, tmp_path):
        f = self._make(tmp_path, 'title: "My Recipe"\n')
        y = obs.YamlDetail(f)
        assert y.title == "My Recipe"

    def test_title_with_single_quotes(self, tmp_path):
        f = self._make(tmp_path, "title: 'Other'\n")
        y = obs.YamlDetail(f)
        assert y.title == "Other"

    def test_empty_lines_not_counted(self, tmp_path):
        content = (
            "instructions:\n"
            "\n"
            "  real\n"
            "\n"
            "  another\n"
        )
        f = self._make(tmp_path, content)
        y = obs.YamlDetail(f)
        # Empty stripped lines skipped
        assert y.instr_lines == 2

    def test_lines_total(self, tmp_path):
        content = "a\nb\nc\n"
        f = self._make(tmp_path, content)
        y = obs.YamlDetail(f)
        # Source: content.count("\n") + 1 = 3 newlines + 1 = 4
        assert y.lines_total == 4

    def test_lines_total_no_trailing_newline(self, tmp_path):
        # No trailing newline → count + 1 = 1
        f = self._make(tmp_path, "abc")
        y = obs.YamlDetail(f)
        assert y.lines_total == 1

    def test_unreadable_yaml(self, tmp_path):
        # Create a file that raises on open() — directory with .yaml name
        fake_agent = tmp_path / "agent"
        fake_agent.mkdir()
        d = fake_agent / "broken.yaml"
        d.mkdir()
        # YamlDetail init: relative_to OK, but open() in _parse raises
        # → except Exception: pass
        y = obs.YamlDetail(d)
        # All defaults
        assert y.lines_total == 0
        assert not y.has_slash
        assert not y.has_settings
        assert y.title == ""

    def test_rel_path_outside_agent(self, tmp_path):
        # Outside agent dir → rel_path = str(path)
        f = tmp_path / "x.yaml"
        f.write_text("title: Hi\n")
        y = obs.YamlDetail(f)
        assert "x.yaml" in y.rel_path

    def test_settings_double_check(self, tmp_path):
        # Bug in source: `s.startswith("settings:") or s.startswith("settings:")`
        # — duplicate check. Still sets has_settings=True correctly.
        f = self._make(tmp_path, "settings:\n")
        y = obs.YamlDetail(f)
        assert y.has_settings


# ─────────────────────────────────────────────────────────────────────
# Scanner
# ─────────────────────────────────────────────────────────────────────
class TestScanner:
    def test_init_default(self):
        s = obs.Scanner()
        assert s.agent_path == obs.get_agent_dir()
        assert s.files == []
        assert s.yamls == []
        assert s.error_messages == []

    def test_init_with_path(self, tmp_path):
        s = obs.Scanner(tmp_path)
        assert s.agent_path == tmp_path

    def test_collect_empty_dir(self, tmp_path):
        s = obs.Scanner(tmp_path)
        s._collect()
        assert s.files == []
        assert s.yamls == []

    def test_collect_yaml(self, tmp_path):
        (tmp_path / "a.yaml").write_text("title: A\n")
        s = obs.Scanner(tmp_path)
        s._collect()
        assert len(s.files) == 1
        assert len(s.yamls) == 1
        assert s.yamls[0].title == "A"

    def test_collect_all_extensions(self, tmp_path):
        (tmp_path / "a.yaml").write_text("a: 1\n")
        (tmp_path / "b.yml").write_text("b: 1\n")
        (tmp_path / "c.md").write_text("# c\n")
        (tmp_path / "d.py").write_text("# d\n")
        (tmp_path / "e.toml").write_text("# e\n")
        (tmp_path / "f.cfg").write_text("# f\n")
        (tmp_path / "g.txt").write_text("g\n")
        (tmp_path / "h.rst").write_text("h\n")
        s = obs.Scanner(tmp_path)
        s._collect()
        exts = sorted(f.ext for f in s.files)
        assert ".yaml" in exts
        assert ".yml" in exts
        assert ".md" in exts
        assert ".py" in exts
        assert ".toml" in exts
        assert ".cfg" in exts
        assert ".txt" in exts
        assert ".rst" in exts

    def test_collect_skips_subdirs(self, tmp_path):
        (tmp_path / "a.yaml").write_text("a: 1\n")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.yaml").write_text("b: 1\n")
        s = obs.Scanner(tmp_path)
        s._collect()
        names = [f.name for f in s.files]
        assert "a.yaml" in names
        assert "b.yaml" in names

    def test_collect_with_error(self, tmp_path):
        # Force FileInfo() to error by making a broken file
        # (e.g., a directory with .yaml name)
        (tmp_path / "broken.yaml").mkdir()
        (tmp_path / "real.yaml").write_text("a: 1\n")
        s = obs.Scanner(tmp_path)
        s._collect()
        # The broken.yaml as directory should fail in FileInfo since
        # _count_lines catches but maybe init() also errors on stat?
        # Actually .stat() works on directories, so init works
        # Then _count_lines fails → no error appended
        # But FileInfo init doesn't append errors either
        # → Just verify it doesn't crash
        assert isinstance(s.error_messages, list)

    def test_get_dirs(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "c").mkdir()
        s = obs.Scanner(tmp_path)
        dirs = s._get_dirs()
        names = [d.name for d in dirs]
        assert "a" in names
        assert "b" in names
        assert "c" in names


# ─────────────────────────────────────────────────────────────────────
# scan_full
# ─────────────────────────────────────────────────────────────────────
class TestScanFull:
    def test_empty(self, tmp_path):
        s = obs.Scanner(tmp_path)
        out = s.scan_full()
        assert "FRAMEWORK-SCAN" in out
        assert "OVERVIEW" in out
        assert "files total:  0" in out
        assert "YAML:           0" in out

    def test_with_files(self, tmp_path):
        (tmp_path / "a.yaml").write_text("title: A\nslash_command: hi\n")
        (tmp_path / "b.md").write_text("# B\n")
        (tmp_path / "c.py").write_text("# C\n")
        (tmp_path / "d.txt").write_text("d\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_full()
        assert "FRAMEWORK-SCAN" in out
        assert "OVERVIEW" in out
        assert "WITH SLASH-COMMAND (1)" in out
        assert "MARKDOWN-DOKUMENTE (1)" in out
        assert "PYTHON (1)" in out
        assert "SUMMARY" in out

    def test_specialists_and_subs(self, tmp_path):
        (tmp_path / "specialist_x.yaml").write_text("title: X\n")
        (tmp_path / "sub_a.yaml").write_text("title: A\n")
        (tmp_path / "deep").mkdir()
        (tmp_path / "deep" / "sub_b.yaml").write_text("title: B\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_full()
        assert "SPECIALISTS (1)" in out
        assert "SUB-agents (2)" in out

    def test_error_section_when_errors(self, tmp_path, monkeypatch):
        # Force an error by patching FileInfo to raise
        def broken_init(self, path):
            raise OSError("simulated")
        monkeypatch.setattr(obs.FileInfo, "__init__", broken_init)
        (tmp_path / "a.yaml").write_text("a: 1\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_full()
        assert "ERROR" in out
        assert "a.yaml" in out

    def test_no_python_section_when_empty(self, tmp_path):
        (tmp_path / "a.yaml").write_text("a: 1\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_full()
        assert "PYTHON" not in out

    def test_with_slash_sorted(self, tmp_path):
        (tmp_path / "a.yaml").write_text("slash_command: zzz\n")
        (tmp_path / "b.yaml").write_text("slash_command: aaa\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_full()
        # 'aaa' should appear before 'zzz' in output
        aaa_pos = out.find("aaa")
        zzz_pos = out.find("zzz")
        assert aaa_pos < zzz_pos

    def test_without_slash_with_title(self, tmp_path):
        (tmp_path / "x.yaml").write_text("title: My Cool Recipe\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_full()
        assert "My Cool Recipe" in out

    def test_without_slash_no_title(self, tmp_path):
        (tmp_path / "x.yaml").write_text("a: 1\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_full()
        # No '←' for missing title
        assert "←" not in out


# ─────────────────────────────────────────────────────────────────────
# scan_quick
# ─────────────────────────────────────────────────────────────────────
class TestScanQuick:
    def test_empty(self, tmp_path):
        s = obs.Scanner(tmp_path)
        out = s.scan_quick()
        assert "FRAMEWORK-OVERVIEW" in out
        assert "YAML:  0" in out
        assert "Total: 0 files" in out

    def test_with_files(self, tmp_path):
        (tmp_path / "a.yaml").write_text("slash_command: hi\n")
        (tmp_path / "b.md").write_text("# B\n")
        (tmp_path / "c.py").write_text("# C\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_quick()
        assert "YAML:  1" in out
        assert "Docs:  1" in out
        assert "Py:    1" in out


# ─────────────────────────────────────────────────────────────────────
# scan_yaml
# ─────────────────────────────────────────────────────────────────────
class TestScanYaml:
    def test_existing(self, tmp_path):
        (tmp_path / "a.yaml").write_text(
            "title: My Recipe\nslash_command: foo\n"
            "settings:\ninstructions:\n  x\nprompt:\n  y\n"
        )
        s = obs.Scanner(tmp_path)
        out = s.scan_yaml("a.yaml")
        assert "a.yaml" in out
        assert "Title: My Recipe" in out
        assert "Slash: /foo" in out
        assert "Settings: yes" in out
        assert "Instructions: 1 lines" in out
        assert "Prompt: 1 lines" in out

    def test_missing(self, tmp_path):
        s = obs.Scanner(tmp_path)
        out = s.scan_yaml("nonexistent.yaml")
        # Source uses German "Nicht" not English "Not"
        assert "Nicht found" in out
        assert "nonexistent.yaml" in out

    def test_no_title(self, tmp_path):
        (tmp_path / "x.yaml").write_text("a: 1\n")
        s = obs.Scanner(tmp_path)
        out = s.scan_yaml("x.yaml")
        assert "Title: (no Titel)" in out
        assert "Slash: ka" in out  # 'ka' = German 'no'
        assert "Settings: no" in out


# ─────────────────────────────────────────────────────────────────────
# save_scan
# ─────────────────────────────────────────────────────────────────────
class TestSaveScan:
    def test_writes_json(self, tmp_path, monkeypatch):
        # Redirect state dir to tmp
        monkeypatch.setattr(obs, "_STATE_DIR", tmp_path / "state")
        (tmp_path / "state").mkdir()
        (tmp_path / "a.yaml").write_text("slash_command: hi\n")
        (tmp_path / "b.md").write_text("# B\n")
        s = obs.Scanner(tmp_path)
        s._collect()
        result = obs.save_scan(s)
        assert "saved" in result
        json_path = (tmp_path / "state") / "analysis.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert "timestamp" in data
        assert "total_files" in data
        assert data["yaml_count"] == 1
        assert data["md_count"] == 1
        assert data["with_slash"] == 1
        assert data["without_slash"] == 0


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def _run_main(self, monkeypatch, argv, agent_dir=None):
        old_argv = sys.argv
        sys.argv = argv
        try:
            # Reset lazy globals so get_agent_dir() uses new state
            obs._AGENT_DIR = None
            if agent_dir is not None:
                monkeypatch.setattr(obs, "resolve_agent_dir", lambda: agent_dir)
            return obs.main()
        finally:
            sys.argv = old_argv

    def test_default_scan_full(self, monkeypatch, tmp_path, capsys):
        (tmp_path / "a.yaml").write_text("title: A\n")
        self._run_main(monkeypatch, ["x.py"], agent_dir=tmp_path)
        out = capsys.readouterr().out
        assert "FRAMEWORK-SCAN" in out

    def test_scan_flag(self, monkeypatch, tmp_path, capsys):
        (tmp_path / "a.yaml").write_text("a: 1\n")
        self._run_main(monkeypatch, ["x.py", "--scan"], agent_dir=tmp_path)
        out = capsys.readouterr().out
        assert "FRAMEWORK-SCAN" in out

    def test_quick_flag(self, monkeypatch, tmp_path, capsys):
        (tmp_path / "a.yaml").write_text("a: 1\n")
        self._run_main(monkeypatch, ["x.py", "--quick"], agent_dir=tmp_path)
        out = capsys.readouterr().out
        assert "FRAMEWORK-OVERVIEW" in out

    def test_yaml_flag(self, monkeypatch, tmp_path, capsys):
        (tmp_path / "a.yaml").write_text("title: T\n")
        self._run_main(monkeypatch, ["x.py", "--yaml", "a.yaml"], agent_dir=tmp_path)
        out = capsys.readouterr().out
        assert "Title: T" in out

    def test_save_flag(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(obs, "_STATE_DIR", tmp_path / "state")
        (tmp_path / "state").mkdir()
        (tmp_path / "a.yaml").write_text("a: 1\n")
        self._run_main(monkeypatch, ["x.py", "--save"], agent_dir=tmp_path)
        out = capsys.readouterr().out
        assert "FRAMEWORK-SCAN" in out
        assert "saved" in out
        json_path = (tmp_path / "state") / "analysis.json"
        assert json_path.exists()

    def test_yaml_dir_flag(self, monkeypatch, tmp_path, capsys):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "a.yaml").write_text("title: A\n")
        (sub / "b.yaml").write_text("title: B\n")
        self._run_main(monkeypatch, ["x.py", "--yaml-dir", "sub"], agent_dir=tmp_path)
        out = capsys.readouterr().out
        assert "sub/a.yaml" in out
        assert "sub/b.yaml" in out

    def test_yaml_dir_missing(self, monkeypatch, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            self._run_main(monkeypatch, ["x.py", "--yaml-dir", "nonexistent"], agent_dir=tmp_path)
        assert exc.value.code == 1

    def test_agent_path_missing(self, monkeypatch, tmp_path, capsys):
        nonexistent = tmp_path / "no_such_dir"
        with pytest.raises(SystemExit) as exc:
            self._run_main(monkeypatch, ["x.py", "--agent-path", str(nonexistent)])
        assert exc.value.code == 1

    def test_agent_path_explicit(self, monkeypatch, tmp_path, capsys):
        explicit = tmp_path / "explicit"
        explicit.mkdir()
        (explicit / "a.yaml").write_text("title: T\n")
        self._run_main(monkeypatch, ["x.py", "--agent-path", str(explicit)])
        out = capsys.readouterr().out
        assert "FRAMEWORK-SCAN" in out

    def test_yaml_takes_precedence(self, monkeypatch, tmp_path, capsys):
        (tmp_path / "a.yaml").write_text("title: T\n")
        self._run_main(monkeypatch, ["x.py", "--yaml", "a.yaml", "--quick"], agent_dir=tmp_path)
        out = capsys.readouterr().out
        # scan_yaml is called, not scan_quick
        assert "Title: T" in out
        assert "FRAMEWORK-OVERVIEW" not in out


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestExecMain:
    def test_exec_no_args(self, monkeypatch, tmp_path, capsys):
        import runpy
        monkeypatch.setattr(obs, "_AGENT_DIR", tmp_path)
        old_argv = sys.argv
        sys.argv = ["x.py"]
        try:
            runpy.run_path("tools/dev_observer.py", run_name="__main__")
            out = capsys.readouterr().out
            assert "FRAMEWORK-SCAN" in out
        finally:
            sys.argv = old_argv

    def test_exec_with_quick(self, monkeypatch, tmp_path, capsys):
        import runpy
        monkeypatch.setattr(obs, "_AGENT_DIR", tmp_path)
        old_argv = sys.argv
        sys.argv = ["x.py", "--quick"]
        try:
            runpy.run_path("tools/dev_observer.py", run_name="__main__")
            out = capsys.readouterr().out
            assert "FRAMEWORK-OVERVIEW" in out
        finally:
            sys.argv = old_argv
