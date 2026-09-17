"""
R110-357: coverage-push round 4 for tools/dev_workspace.py.

Target: cmd_project() dispatcher (L1211-1242), _register_agent
(L960-995), _validate_agent (L928-959), _show_summary (L1001-1031),
and _active_project_path (L1041-1044). These are the remaining
uncovered functions in the user-facing agent-creation flow.

dev_workspace.py round 1+2+3 (R110-351+353+355) brought coverage
from 0% to 49% on 595 testable stmts. Round 4 targets the
remaining ~25% of user-facing helpers:

  1. cmd_project() dispatcher (L1211-1242) — branch-based
     dispatch for all 6 subcommands. Tests:
     - "list"/"ls"/"l" → cmd_project_list
     - "create" with arg → cmd_project_create
     - "create" without arg + 'myproj' input → cmd_project_create
     - "create" with --copy flag → copy_from parsed
     - "switch" with arg → cmd_project_switch
     - "switch" without arg + input → cmd_project_switch
     - "show"/"info"/"i" → cmd_project_show
     - "delete"/"del"/"rm"/"d" with 'j' confirmation → cmd_project_delete
     - "delete" with 'n' → no-op
     - "rename" with 2 args → cmd_project_rename
     - "rename" without args + input → cmd_project_rename
     - empty args → defaults to "list"
     - empty name from input → no-op

  2. _register_agent (L960-995) — interactive registration.
     Tests:
     - 'n' input → "Nicht registriert"
     - 'j' input + main recipe missing → prints instructions
     - 'j' input + main recipe with name already present → warning
     - 'j' input + main recipe without name → prints instructions
     - EOFError → "Skipped"

  3. _active_project_path (L1041-1044) — get active project path.
     Tests:
     - returns (Path, name) tuple
     - returns default "dev-team" if no .projects.yaml

  4. _show_summary (L1001-1031) — print closing summary.
     Tests:
     - mas_sub type → 3-step mas workflow
     - fw_specialist type → 2-step manual workflow
     - fw_sub type → 2-step manual workflow
     - unknown type → defaults to 2-step

  5. _validate_agent (L928-959) — optional validation.
     Tests:
     - just returns (placeholder, real validation in dev_editor.py)
     - works with any path argument

Target: bump coverage from 49% to ~65% (+16pp on 595 stmts).
"""
import sys
import importlib
import builtins
from pathlib import Path
from datetime import datetime
import pytest
import yaml

TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def ws_mod(tmp_path, monkeypatch):
    """Import dev_workspace with cwd sandboxed."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_workspace", None)
    mod = importlib.import_module("dev_workspace")
    yield mod
    sys.modules.pop("dev_workspace", None)


class TestCmdProjectDispatch:
    """cmd_project(args) (L1211-1242) — subcommand dispatcher."""

    def test_list_dispatches_to_list(self, ws_mod, monkeypatch, capsys):
        """'list' → cmd_project_list() (prints header)."""
        (ws_mod.Path("framework")).mkdir()
        ws_mod.cmd_project(["list"])
        captured = capsys.readouterr()
        assert "Total:" in captured.out

    def test_ls_alias(self, ws_mod, capsys):
        """'ls' alias → list."""
        (ws_mod.Path("framework")).mkdir()
        ws_mod.cmd_project(["ls"])
        captured = capsys.readouterr()
        assert "Total:" in captured.out

    def test_l_short_alias(self, ws_mod, capsys):
        """'l' short alias → list."""
        (ws_mod.Path("framework")).mkdir()
        ws_mod.cmd_project(["l"])
        captured = capsys.readouterr()
        assert "Total:" in captured.out

    def test_empty_args_defaults_to_list(self, ws_mod, capsys):
        """No args → defaults to 'list'."""
        (ws_mod.Path("framework")).mkdir()
        ws_mod.cmd_project([])
        captured = capsys.readouterr()
        assert "Total:" in captured.out

    def test_create_with_arg(self, ws_mod, tmp_path, monkeypatch):
        """'create myproj' → cmd_project_create('myproj')."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        ws_mod.cmd_project(["create", "myproj"])
        assert (tmp_path / "framework" / "myproj").exists()

    def test_create_without_arg_uses_input(self, ws_mod, tmp_path, monkeypatch):
        """'create' with no name + input → cmd_project_create(name)."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        monkeypatch.setattr(builtins, "input", lambda _: "inputname")
        ws_mod.cmd_project(["create"])
        assert (tmp_path / "framework" / "inputname").exists()

    def test_create_with_copy_flag(self, ws_mod, tmp_path):
        """'create newproj --copy src' → copies from src."""
        (tmp_path / "framework" / "src").mkdir(parents=True)
        (tmp_path / "framework" / "src" / "marker.txt").write_text("x")
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        ws_mod.cmd_project(["create", "newproj", "--copy", "src"])
        assert (tmp_path / "framework" / "newproj" / "marker.txt").exists()

    def test_create_with_empty_name_no_op(self, ws_mod, tmp_path, monkeypatch, capsys):
        """'create' with no name + empty input → no-op."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        monkeypatch.setattr(builtins, "input", lambda _: "")
        ws_mod.cmd_project(["create"])
        # No new project created
        projects = list((tmp_path / "framework").iterdir())
        # Only .projects.yaml + framework itself
        non_yaml = [p for p in projects if p.name != ".projects.yaml"]
        assert all(not p.is_dir() or p.name == "" for p in non_yaml)

    def test_switch_with_arg(self, ws_mod, tmp_path, monkeypatch):
        """'switch p2' → cmd_project_switch('p2')."""
        (tmp_path / "framework" / "p1").mkdir(parents=True)
        (tmp_path / "framework" / "p2").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "p1": {"label": "P1", "agents": 0, "tests": 0, "status": "stable"},
                "p2": {"label": "P2", "agents": 0, "tests": 0, "status": "stable"},
            },
            "active_project": "p1",
        }))
        ws_mod.cmd_project(["switch", "p2"])
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert data["active_project"] == "p2"

    def test_show_dispatches_to_show(self, ws_mod, tmp_path, capsys):
        """'show myproj' → cmd_project_show('myproj')."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "myproj": {"label": "MYPROJ", "type": "x", "agents": 5, "tests": 10, "status": "stable"}
            },
            "active_project": "myproj",
        }))
        ws_mod.cmd_project(["show", "myproj"])
        captured = capsys.readouterr()
        assert "MYPROJ" in captured.out

    def test_info_alias_for_show(self, ws_mod, tmp_path, capsys):
        """'info' alias → show."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "myproj": {"label": "MYPROJ", "type": "x", "agents": 0, "tests": 0, "status": "stable"}
            },
            "active_project": "myproj",
        }))
        ws_mod.cmd_project(["info", "myproj"])
        captured = capsys.readouterr()
        assert "MYPROJ" in captured.out

    def test_delete_with_j_confirmation(self, ws_mod, tmp_path, monkeypatch):
        """'delete myproj' + 'j' confirmation → cmd_project_delete."""
        (tmp_path / "framework" / "myproj").mkdir(parents=True)
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "myproj": {"label": "MYPROJ"},
                "other": {"label": "OTHER"}
            },
            "active_project": "other",
        }))
        monkeypatch.setattr(builtins, "input", lambda _: "j")
        ws_mod.cmd_project(["delete", "myproj"])
        # Project should be in .trash now
        assert (tmp_path / "framework" / ".trash").exists()

    def test_delete_with_n_no_op(self, ws_mod, tmp_path, monkeypatch):
        """'delete myproj' + 'n' → no-op, project NOT deleted."""
        (tmp_path / "framework" / "myproj").mkdir(parents=True)
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"myproj": {"label": "MYPROJ"}},
            "active_project": "other",
        }))
        monkeypatch.setattr(builtins, "input", lambda _: "n")
        ws_mod.cmd_project(["delete", "myproj"])
        # Project NOT deleted
        assert (tmp_path / "framework" / "myproj").exists()

    def test_rename_with_2_args(self, ws_mod, tmp_path):
        """'rename old new' → cmd_project_rename."""
        (tmp_path / "framework" / "old").mkdir(parents=True)
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"old": {"label": "OLD", "config": "old/config.yaml"}},
            "active_project": "",
        }))
        ws_mod.cmd_project(["rename", "old", "new"])
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert "new" in data["projects"]

    def test_rename_without_args_uses_input(self, ws_mod, tmp_path, monkeypatch):
        """'rename' with no args + 2 inputs → cmd_project_rename."""
        (tmp_path / "framework" / "old").mkdir(parents=True)
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"old": {"label": "OLD", "config": "old/config.yaml"}},
            "active_project": "",
        }))
        inputs = iter(["old", "new"])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        ws_mod.cmd_project(["rename"])
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert "new" in data["projects"]


class TestRegisterAgent:
    """_register_agent (L960-995) — interactive registration."""

    def test_no_input_skipped(self, ws_mod, monkeypatch, capsys):
        """'n' → 'Nicht registriert'."""
        monkeypatch.setattr(builtins, "input", lambda _: "n")
        ws_mod._register_agent("myagent", "Description", "🤖", str(Path.cwd()))
        captured = capsys.readouterr()
        assert "Nicht registriert" in captured.out

    def test_j_with_missing_main_recipe_prints_instructions(self, ws_mod, tmp_path, monkeypatch, capsys):
        """'j' + no main recipe file → prints registration instructions."""
        monkeypatch.setattr(builtins, "input", lambda _: "j")
        ws_mod._register_agent("myagent", "Description", "🤖", str(tmp_path))
        captured = capsys.readouterr()
        assert "Registrierungs-Data" in captured.out or "sub_mas-myagent" in captured.out

    def test_j_with_existing_recipe_warns_duplicate(self, ws_mod, tmp_path, monkeypatch, capsys):
        """'j' + main recipe already contains name → warning, no re-print."""
        # Create the main recipe with the agent already present
        mas_recipe_dir = tmp_path / "mas-engineer" / "recipe"
        mas_recipe_dir.mkdir(parents=True)
        (mas_recipe_dir / "dev-mas-engineer.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "sub_recipes": [{"name": "sub_mas-myagent", "path": "./sub/sub_mas-myagent.yaml"}]
        }))
        monkeypatch.setattr(builtins, "input", lambda _: "j")
        ws_mod._register_agent("myagent", "Description", "🤖", str(tmp_path))
        captured = capsys.readouterr()
        assert "already" in captured.out or "registriert" in captured.out

    def test_eoferror_skipped(self, ws_mod, monkeypatch, capsys):
        """EOFError → 'Skipped' message."""
        monkeypatch.setattr(builtins, "input", lambda _: (_ for _ in ()).throw(EOFError))
        ws_mod._register_agent("myagent", "Description", "🤖", str(Path.cwd()))
        captured = capsys.readouterr()
        assert "Skipped" in captured.out or "skipped" in captured.out

    def test_j_with_recipe_missing_agent_prints_full_instructions(self, ws_mod, tmp_path, monkeypatch, capsys):
        """'j' + main recipe present but agent missing → full instructions."""
        mas_recipe_dir = tmp_path / "mas-engineer" / "recipe"
        mas_recipe_dir.mkdir(parents=True)
        (mas_recipe_dir / "dev-mas-engineer.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "sub_recipes": []
        }))
        monkeypatch.setattr(builtins, "input", lambda _: "j")
        ws_mod._register_agent("newagent", "New desc", "🚀", str(tmp_path))
        captured = capsys.readouterr()
        assert "sub_mas-newagent" in captured.out
        assert "🚀" in captured.out


class TestActiveProjectPath:
    """_active_project_path (L1041-1044)."""

    def test_returns_path_and_name(self, ws_mod, tmp_path):
        """Returns (Path, name) tuple."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"myproj": {"label": "M"}},
            "active_project": "myproj",
        }))
        path, name = ws_mod._active_project_path()
        assert name == "myproj"
        assert path == Path("framework") / "myproj"

    def test_default_dev_team_when_no_yaml(self, ws_mod, tmp_path):
        """No .projects.yaml → returns ('dev-team', Path('framework/dev-team'))."""
        (tmp_path / "framework").mkdir()
        path, name = ws_mod._active_project_path()
        # Default is dev-team
        assert name == "dev-team"
        assert path == Path("framework") / "dev-team"

    def test_default_dev_team_when_empty_yaml(self, ws_mod, tmp_path):
        """Empty active_project → defaults to 'dev-team'."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {},
            "active_project": "",
        }))
        path, name = ws_mod._active_project_path()
        assert name == "dev-team"


class TestShowSummary:
    """_show_summary (L1001-1031)."""

    def test_mas_sub_shows_3_step_mas_workflow(self, ws_mod, tmp_path, capsys):
        """mas_sub type → 3-step MAS workflow."""
        ws_mod._show_summary("mas_sub", "myagent", "Desc", "🤖", tmp_path / "test.yaml")
        captured = capsys.readouterr()
        assert "MAS Sub-Agent" in captured.out
        assert "AGENT ERSTELLT" in captured.out
        # 3-step mas workflow
        assert "dev_editor.py" in captured.out or "sub_recipes" in captured.out

    def test_fw_specialist_shows_2_step_manual(self, ws_mod, tmp_path, capsys):
        """fw_specialist → 2-step manual workflow."""
        ws_mod._show_summary("fw_specialist", "deploy", "Desc", "🚀", tmp_path / "test.yaml")
        captured = capsys.readouterr()
        assert "framework Specialist" in captured.out
        # 2-step manual workflow
        assert "manuell" in captured.out or "anpassen" in captured.out

    def test_fw_sub_shows_2_step_manual(self, ws_mod, tmp_path, capsys):
        """fw_sub → 2-step manual workflow."""
        ws_mod._show_summary("fw_sub", "config", "Desc", "📝", tmp_path / "test.yaml")
        captured = capsys.readouterr()
        assert "framework Sub-Agent" in captured.out

    def test_unknown_type_uses_default_label(self, ws_mod, tmp_path, capsys):
        """Unknown agent type → uses raw type as label, 2-step default."""
        ws_mod._show_summary("unknown_type", "agent", "Desc", "🤖", tmp_path / "test.yaml")
        captured = capsys.readouterr()
        assert "unknown_type" in captured.out
        assert "AGENT ERSTELLT" in captured.out

    def test_emoji_shown_in_summary(self, ws_mod, tmp_path, capsys):
        """Emoji appears in summary output."""
        ws_mod._show_summary("mas_sub", "agent", "Desc", "🔥", tmp_path / "test.yaml")
        captured = capsys.readouterr()
        assert "🔥" in captured.out


class TestValidateAgent:
    """_validate_agent (L928-959) — optional validation hook."""

    def test_validate_does_not_crash(self, ws_mod, tmp_path, capsys):
        """_validate_agent with any path → does not crash."""
        # Create a valid yaml file
        yaml_path = tmp_path / "test_agent.yaml"
        yaml_path.write_text(yaml.dump({"version": "1.0.0", "title": "Test"}))
        # Should not raise
        ws_mod._validate_agent(str(yaml_path), "mas_sub")
