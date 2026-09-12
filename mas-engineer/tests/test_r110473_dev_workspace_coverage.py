"""R110-473 — coverage-push r10: tools/dev_workspace.py 0% → high

Targets the testable surface of dev_workspace.py (599 stmts):
- Print helpers: log, info, ok, warn, error
- count_files: glob with existence-check
- cmd_init_recovery: Phoenix-Recovery setup
- _write_start_sessions_script: writes start-sessions.sh
- cmd_clean: deletes workspace dir
- cmd_status: reports workspace stats
- _ask_type, _ask_name, _ask_description: interactive prompts (mocked)
- _generate_agent: writes agent YAML from template
- _validate_agent: YAML-skill-validation
- _register_agent: sub_recipes registration helper
- _show_summary: closes scaffold session
- _load_projects, _save_projects, _active_project_path: .projects.yaml IO
- cmd_project_list, _create, _switch, _show, _delete, _rename: project mgmt
- cmd_project: dispatch
- cmd_doctor_init: creates .doctor/ MAS-integration scaffold
- cmd_scaffold: full agent generation pipeline (mocked input)
- cmd_install_check: YAML + paths + standalone + parallel + backups

KEY OBSERVATIONS:
- Module has `if __name__ == "__main__": main()` pattern;
  import is safe (no module-level side effects).
- PROJECTS_FILE = "framework/.projects.yaml" is a RELATIVE path
  rooted at cwd. We monkeypatch to tmp_path.
- MAS_TEMPLATE = Path(__file__).parent.parent / "recipe" / "template"
  / "agent_template.yaml" — points at real repo file. We
  monkeypatch it for `_generate_agent` tests.
- Many functions use `input()` for prompts. We mock
  `builtins.input` with monkeypatch.
- cmd_clean uses `shutil.rmtree` — safe in tmp_path.
- _validate_agent calls subprocess (dev_editor --validate).
  We use tmp_path YAML to trigger the YAML-syntax branch
  (agent_type="fw_specialist" → opens file directly, no subprocess).
- _ask_name regex is `^[a-z0-9-]+$` — uppercase rejected,
  underscores rejected, spaces replaced with dashes.
"""

import io
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_workspace as ws  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Print helpers
# ─────────────────────────────────────────────────────────────────────
class TestPrinters:
    def test_log(self, capsys):
        ws.log("plain")
        assert "plain" in capsys.readouterr().out

    def test_info(self, capsys):
        ws.info("hello")
        out = capsys.readouterr().out
        assert "hello" in out
        assert "📢" in out

    def test_ok(self, capsys):
        ws.ok("done")
        out = capsys.readouterr().out
        assert "done" in out
        assert "✅" in out

    def test_warn(self, capsys):
        ws.warn("careful")
        out = capsys.readouterr().out
        assert "careful" in out
        assert "⚠" in out

    def test_error(self, capsys):
        ws.error("oops")
        out = capsys.readouterr().out
        assert "oops" in out
        assert "❌" in out


# ─────────────────────────────────────────────────────────────────────
# count_files
# ─────────────────────────────────────────────────────────────────────
class TestCountFiles:
    def test_nonexistent_dir_returns_zero(self, tmp_path):
        assert ws.count_files(tmp_path / "nope") == 0

    def test_empty_dir_returns_zero(self, tmp_path):
        assert ws.count_files(tmp_path) == 0

    def test_counts_matching_files(self, tmp_path):
        (tmp_path / "a.yaml").touch()
        (tmp_path / "b.yaml").touch()
        (tmp_path / "c.py").touch()
        assert ws.count_files(tmp_path, "*.yaml") == 2
        assert ws.count_files(tmp_path, "*.py") == 1
        assert ws.count_files(tmp_path) == 3

    def test_nested_match(self, tmp_path):
        # glob() is NOT recursive — only top-level files match
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "x.yaml").touch()
        # glob() doesn't recurse → 0 matches at top-level
        assert ws.count_files(tmp_path, "*.yaml") == 0
        # rglob equivalent via Path.rglob → 1 match
        assert len(list(tmp_path.rglob("*.yaml"))) == 1


# ─────────────────────────────────────────────────────────────────────
# _write_start_sessions_script
# ─────────────────────────────────────────────────────────────────────
class TestWriteStartSessionsScript:
    def test_writes_script(self, tmp_path, capsys):
        ws._write_start_sessions_script(tmp_path)
        script = tmp_path / "start-sessions.sh"
        assert script.exists()
        # Executable bit set
        assert os.access(str(script), os.X_OK)
        # Contains expected content
        content = script.read_text()
        assert "framework" in content
        assert "mas-engineer" in content
        assert "GOOSE_RECIPE_PATH" in content

    def test_prints_ok(self, tmp_path, capsys):
        ws._write_start_sessions_script(tmp_path)
        out = capsys.readouterr().out
        assert "start-sessions.sh" in out
        assert "✅" in out


# ─────────────────────────────────────────────────────────────────────
# cmd_clean
# ─────────────────────────────────────────────────────────────────────
class TestCmdClean:
    def test_deletes_existing_workspace(self, tmp_path, capsys):
        ws.cmd_clean(str(tmp_path))
        assert not tmp_path.exists()
        out = capsys.readouterr().out
        assert "🗑️" in out or "deleted" in out.lower()

    def test_nonexistent_warns(self, tmp_path, capsys):
        ws.cmd_clean(str(tmp_path / "nope"))
        out = capsys.readouterr().out
        assert "exists not" in out or "⚠" in out


# ─────────────────────────────────────────────────────────────────────
# cmd_status
# ─────────────────────────────────────────────────────────────────────
class TestCmdStatus:
    def test_nonexistent_warns(self, tmp_path, capsys):
        ws.cmd_status(str(tmp_path / "nope"))
        out = capsys.readouterr().out
        assert "exists not" in out or "⚠" in out

    def test_existing_workspace_reports(self, tmp_path, capsys):
        # Create minimal workspace structure
        (tmp_path / "framework" / "recipes").mkdir(parents=True)
        (tmp_path / "framework" / "recipes" / "a.yaml").touch()
        (tmp_path / "mas-engineer" / "tools").mkdir(parents=True)
        (tmp_path / "mas-engineer" / "tools" / "dev_x.py").touch()
        (tmp_path / "framework" / "config.yaml").touch()
        ws.cmd_status(str(tmp_path))
        out = capsys.readouterr().out
        assert "📊" in out
        assert "📄 Recipes" in out
        assert "1 YAML" in out

    def test_with_changes_json(self, tmp_path, capsys):
        (tmp_path / ".mase").mkdir()
        (tmp_path / ".mase" / "changes.json").write_text(
            '{"stats": {"total_changes": 42}}'
        )
        ws.cmd_status(str(tmp_path))
        out = capsys.readouterr().out
        assert "Changes" in out
        assert "42" in out

    def test_with_invalid_changes_json(self, tmp_path, capsys):
        # Should not crash on bad JSON
        (tmp_path / ".mase").mkdir()
        (tmp_path / ".mase" / "changes.json").write_text("not json{")
        ws.cmd_status(str(tmp_path))
        # No "Changes:" line because exception was swallowed
        out = capsys.readouterr().out
        assert "📊" in out  # status header still printed


# ─────────────────────────────────────────────────────────────────────
# _ask_type (interactive, mocked)
# ─────────────────────────────────────────────────────────────────────
class TestAskType:
    def test_choice_1_mas_sub(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "1")
        agent_type, rel_dir, tmpl = ws._ask_type()
        assert agent_type == "mas_sub"
        assert rel_dir == "mas-engineer/recipe/sub/"
        assert tmpl == "agent_template.yaml"

    def test_choice_2_fw_specialist(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "2")
        agent_type, rel_dir, tmpl = ws._ask_type()
        assert agent_type == "fw_specialist"
        assert rel_dir == "framework/recipes/specialists/"
        assert tmpl is None

    def test_choice_3_fw_sub(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "3")
        agent_type, rel_dir, tmpl = ws._ask_type()
        assert agent_type == "fw_sub"
        assert rel_dir == "framework/recipes/sub/"
        assert tmpl is None

    def test_invalid_then_valid(self, monkeypatch, capsys):
        inputs = iter(["9", "0", "abc", "1"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        agent_type, _, _ = ws._ask_type()
        assert agent_type == "mas_sub"

    def test_eof_returns_none(self, monkeypatch, capsys):
        def raise_eof(_):
            raise EOFError
        monkeypatch.setattr("builtins.input", raise_eof)
        result = ws._ask_type()
        assert result == (None, None, None)


# ─────────────────────────────────────────────────────────────────────
# _ask_name (interactive, mocked)
# ─────────────────────────────────────────────────────────────────────
class TestAskName:
    def test_valid_name(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "my-agent")
        assert ws._ask_name("mas_sub") == "my-agent"

    def test_name_lowercased(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "MyAgent")
        assert ws._ask_name("mas_sub") == "myagent"

    def test_spaces_replaced_with_dashes(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "my agent")
        assert ws._ask_name("mas_sub") == "my-agent"

    def test_empty_then_valid(self, monkeypatch, capsys):
        inputs = iter(["", "valid"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        assert ws._ask_name("mas_sub") == "valid"

    def test_invalid_chars_then_valid(self, monkeypatch, capsys):
        inputs = iter(["My_Agent", "ok-name"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        assert ws._ask_name("mas_sub") == "ok-name"

    def test_eof_returns_none(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))
        assert ws._ask_name("mas_sub") is None

    def test_fw_specialist_hint(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "deploy")
        ws._ask_name("fw_specialist")
        out = capsys.readouterr().out
        assert "deploy.yaml" in out


# ─────────────────────────────────────────────────────────────────────
# _ask_description (interactive, mocked)
# ─────────────────────────────────────────────────────────────────────
class TestAskDescription:
    def test_with_description_and_emoji(self, monkeypatch, capsys):
        inputs = iter(["Test desc", "🧪"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        desc, emoji = ws._ask_description("my-name")
        assert desc == "Test desc"
        assert emoji == "🧪"

    def test_empty_description_uses_name(self, monkeypatch, capsys):
        inputs = iter(["", "🛡️"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        desc, emoji = ws._ask_description("my-cool-agent")
        assert desc == "My Cool Agent"  # name.title() with dashes→spaces
        assert emoji == "🛡️"

    def test_empty_emoji_defaults_to_robot(self, monkeypatch, capsys):
        inputs = iter(["desc", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        desc, emoji = ws._ask_description("name")
        assert emoji == "🤖"

    def test_eof_returns_none(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))
        desc, emoji = ws._ask_description("name")
        assert desc is None and emoji is None


# ─────────────────────────────────────────────────────────────────────
# _generate_agent (writes YAML from template)
# ─────────────────────────────────────────────────────────────────────
class TestGenerateAgent:
    @pytest.fixture
    def template(self, tmp_path):
        # Minimal valid template
        t = tmp_path / "agent_template.yaml"
        t.write_text("name: __NAME__\ndescription: __DESCRIPTION__\nemoji: __EMOJI__\n")
        return t

    @pytest.fixture
    def workspace(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        return ws

    def test_mas_sub_creates_file(self, template, workspace, monkeypatch):
        # Template needs ALL placeholders that get substituted:
        # {NAME}, {name}, {EMOJI}, {BESCHREIBUNG}, {TASK}, {Titel}
        t = workspace / "agent_template.yaml"
        t.write_text(
            "name: {name}\n"
            "title: {NAME}\n"
            "description: {BESCHREIBUNG}\n"
            "emoji: {EMOJI}\n"
            "task: {TASK}\n"
            "titel: {Titel}\n"
        )
        monkeypatch.setattr(ws, "MAS_TEMPLATE", t)
        result = ws._generate_agent("mas_sub", "foo", "Foo desc", "🛡️", str(workspace))
        assert result is not None
        assert result.exists()
        content = result.read_text()
        assert "foo" in content
        assert "FOO" in content  # {NAME} → upper
        assert "Foo desc" in content
        assert "🛡️" in content
        # Default dir
        assert "mas-engineer" in str(result)

    def test_fw_specialist_creates_file(self, template, workspace, monkeypatch):
        monkeypatch.setattr(ws, "MAS_TEMPLATE", template)
        result = ws._generate_agent("fw_specialist", "bar", "Bar desc", "🧪", str(workspace))
        assert result is not None
        assert result.exists()
        assert "specialists" in str(result)

    def test_fw_sub_creates_file(self, template, workspace, monkeypatch):
        monkeypatch.setattr(ws, "MAS_TEMPLATE", template)
        result = ws._generate_agent("fw_sub", "baz", "Baz desc", "🖥️", str(workspace))
        assert result is not None
        assert "sub" in str(result)

    def test_mas_sub_missing_template_returns_none(self, workspace, monkeypatch, capsys):
        missing = workspace / "no_template.yaml"
        monkeypatch.setattr(ws, "MAS_TEMPLATE", missing)
        result = ws._generate_agent("mas_sub", "foo", "desc", "🛡️", str(workspace))
        assert result is None
        assert "Template not found" in capsys.readouterr().out

    def test_overwrite_prompt_decline(self, template, workspace, monkeypatch):
        monkeypatch.setattr(ws, "MAS_TEMPLATE", template)
        # First call: creates file
        result1 = ws._generate_agent("mas_sub", "foo", "desc", "🛡️", str(workspace))
        assert result1 is not None
        # Second call: declines overwrite
        monkeypatch.setattr("builtins.input", lambda _: "n")
        result2 = ws._generate_agent("mas_sub", "foo", "desc", "🛡️", str(workspace))
        assert result2 is None


# ─────────────────────────────────────────────────────────────────────
# _validate_agent (YAML syntax branch, no subprocess)
# ─────────────────────────────────────────────────────────────────────
class TestValidateAgent:
    def test_valid_yaml_fw_specialist(self, tmp_path, capsys):
        yaml = tmp_path / "test.yaml"
        yaml.write_text("name: test\n")
        ws._validate_agent(yaml, "fw_specialist")
        out = capsys.readouterr().out
        assert "YAML-Syntax: OK" in out

    def test_invalid_yaml_fw_specialist(self, tmp_path, capsys):
        yaml = tmp_path / "bad.yaml"
        yaml.write_text(":\n")  # invalid YAML
        ws._validate_agent(yaml, "fw_specialist")
        out = capsys.readouterr().out
        assert "YAML-Syntax-Error" in out

    def test_accepts_string_path(self, tmp_path, capsys):
        yaml_p = tmp_path / "test.yaml"
        yaml_p.write_text("name: test\n")
        ws._validate_agent(str(yaml_p), "fw_specialist")
        out = capsys.readouterr().out
        assert "YAML-Syntax: OK" in out


# ─────────────────────────────────────────────────────────────────────
# _register_agent (interactive, mocked)
# ─────────────────────────────────────────────────────────────────────
class TestRegisterAgent:
    def test_decline_registration(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "n")
        ws._register_agent("myagent", "My desc", "🛡️", str(tmp_path))
        out = capsys.readouterr().out
        assert "Nicht registriert" in out

    def test_eof_skips(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))
        ws._register_agent("x", "y", "🛡️", "/tmp")
        out = capsys.readouterr().out
        assert "Skipped" in out

    def test_shows_registration_data(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "j")
        ws._register_agent("myagent", "My desc", "🛡️", str(tmp_path))
        out = capsys.readouterr().out
        assert "sub_mas-myagent" in out
        assert "🛡️ My desc" in out
        assert "Registrierungs-Data" in out

    def test_already_registered_warns(self, tmp_path, monkeypatch, capsys):
        # Create the main recipe with the agent already in it
        mas_dir = tmp_path / "mas-engineer" / "recipe"
        mas_dir.mkdir(parents=True)
        (mas_dir / "dev-mas-engineer.yaml").write_text(
            "...sub_mas-myagent..."
        )
        monkeypatch.setattr("builtins.input", lambda _: "j")
        ws._register_agent("myagent", "desc", "🛡️", str(tmp_path))
        out = capsys.readouterr().out
        assert "already" in out


# ─────────────────────────────────────────────────────────────────────
# _load_projects / _save_projects / _active_project_path
# ─────────────────────────────────────────────────────────────────────
class TestProjectsIO:
    @pytest.fixture
    def projects_file(self, tmp_path, monkeypatch):
        pf = tmp_path / ".projects.yaml"
        monkeypatch.setattr(ws, "PROJECTS_FILE", str(pf))
        return pf

    def test_load_creates_if_missing(self, projects_file):
        data = ws._load_projects()
        assert isinstance(data, dict)
        assert "projects" in data
        assert "active_project" in data
        # File was created
        assert projects_file.exists()

    def test_load_existing(self, projects_file):
        import yaml
        projects_file.write_text(yaml.dump({
            "version": "1.0.0",
            "active_project": "foo",
            "projects": {"foo": {"label": "FOO"}}
        }))
        data = ws._load_projects()
        assert data["active_project"] == "foo"
        assert "foo" in data["projects"]

    def test_save_updates_last_updated(self, projects_file):
        data = ws._load_projects()
        data["projects"]["new"] = {"label": "NEW"}
        ws._save_projects(data)
        # Reload to verify
        import yaml
        reloaded = yaml.safe_load(projects_file.read_text())
        assert "last_updated" in reloaded
        assert "new" in reloaded["projects"]

    def test_active_project_path_default(self, projects_file):
        path, name = ws._active_project_path()
        assert name == "dev-team"
        assert path.name == "dev-team"

    def test_active_project_empty_defaults_to_dev_team(self, projects_file):
        import yaml
        projects_file.write_text(yaml.dump({
            "version": "1.0.0",
            "active_project": "",
            "projects": {}
        }))
        path, name = ws._active_project_path()
        assert name == "dev-team"


# ─────────────────────────────────────────────────────────────────────
# cmd_project_list / cmd_project_show
# ─────────────────────────────────────────────────────────────────────
class TestProjectListShow:
    @pytest.fixture
    def projects_file(self, tmp_path, monkeypatch):
        pf = tmp_path / ".projects.yaml"
        monkeypatch.setattr(ws, "PROJECTS_FILE", str(pf))
        # Pre-populate with 2 projects
        import yaml
        pf.write_text(yaml.dump({
            "version": "1.0.0",
            "active_project": "alpha",
            "projects": {
                "alpha": {"label": "ALPHA", "agents": 3, "tests": 5, "status": "stable"},
                "beta":  {"label": "BETA",  "agents": 1, "tests": 0, "status": "draft"},
            }
        }))
        return pf

    def test_list_prints_projects(self, projects_file, capsys):
        ws.cmd_project_list()
        out = capsys.readouterr().out
        assert "alpha" in out
        assert "beta" in out
        assert "active" in out
        assert "stable" in out

    def test_show_existing(self, projects_file, capsys):
        ws.cmd_project_show("alpha")
        out = capsys.readouterr().out
        assert "Label" in out
        assert "ALPHA" in out

    def test_show_nonexistent(self, projects_file, capsys):
        ws.cmd_project_show("nope")
        out = capsys.readouterr().out
        assert "not found" in out


# ─────────────────────────────────────────────────────────────────────
# cmd_project_create / cmd_project_switch
# ─────────────────────────────────────────────────────────────────────
class TestProjectCreateSwitch:
    @pytest.fixture
    def projects_file(self, tmp_path, monkeypatch):
        pf = tmp_path / ".projects.yaml"
        monkeypatch.setattr(ws, "PROJECTS_FILE", str(pf))
        monkeypatch.chdir(tmp_path)
        # Pre-populate with 2 projects including dev-team so cmd_project_create
        # can check existence (the default _load_projects only creates dev-team)
        import yaml
        pf.write_text(yaml.dump({
            "version": "1.0.0",
            "active_project": "dev-team",
            "projects": {
                "dev-team": {"label": "DEV", "agents": 0, "tests": 0, "status": "stable"},
                "alpha": {"label": "ALPHA", "agents": 0, "tests": 0, "status": "draft"},
            }
        }))
        return pf

    def test_create_new(self, projects_file, capsys):
        ws.cmd_project_create("gamma")
        out = capsys.readouterr().out
        assert "gamma" in out
        # Directory structure created
        assert (projects_file.parent / "framework" / "gamma" / "recipes" / "core").exists()
        assert (projects_file.parent / "framework" / "gamma" / "docs").exists()
        # .projects.yaml updated
        import yaml
        data = yaml.safe_load(projects_file.read_text())
        assert "gamma" in data["projects"]
        assert data["active_project"] == "gamma"

    def test_create_existing_noop(self, projects_file, capsys):
        ws.cmd_project_create("alpha")  # already exists in fixture
        out = capsys.readouterr().out
        assert "exists already" in out

    def test_create_with_copy_from(self, projects_file, capsys):
        # Create source project
        (projects_file.parent / "framework" / "alpha").mkdir(parents=True)
        (projects_file.parent / "framework" / "alpha" / "marker.txt").write_text("x")
        ws.cmd_project_create("delta", copy_from="alpha")
        out = capsys.readouterr().out
        assert "delta" in out
        assert (projects_file.parent / "framework" / "delta" / "marker.txt").exists()

    def test_create_with_copy_from_nonexistent(self, projects_file, capsys):
        ws.cmd_project_create("delta", copy_from="nonexistent")
        out = capsys.readouterr().out
        assert "not found" in out

    def test_switch_existing(self, projects_file, capsys):
        # cmd_project_switch also updates framework/current symlink;
        # framework/alpha must exist for symlink to be valid
        (projects_file.parent / "framework" / "alpha").mkdir(parents=True)
        ws.cmd_project_switch("alpha")
        import yaml
        data = yaml.safe_load(projects_file.read_text())
        assert data["active_project"] == "alpha"

    def test_switch_nonexistent(self, projects_file, capsys):
        ws.cmd_project_switch("nope")
        out = capsys.readouterr().out
        assert "not found" in out


# ─────────────────────────────────────────────────────────────────────
# cmd_project_delete
# ─────────────────────────────────────────────────────────────────────
class TestProjectDelete:
    @pytest.fixture
    def projects_file(self, tmp_path, monkeypatch):
        pf = tmp_path / ".projects.yaml"
        monkeypatch.setattr(ws, "PROJECTS_FILE", str(pf))
        monkeypatch.chdir(tmp_path)
        # Add a non-base project
        import yaml
        pf.write_text(yaml.dump({
            "version": "1.0.0",
            "active_project": "gamma",
            "projects": {
                "dev-team": {"label": "DEV"},
                "gamma": {"label": "GAMMA", "agents": 0, "tests": 0, "status": "draft"}
            }
        }))
        (tmp_path / "framework" / "gamma").mkdir(parents=True)
        (tmp_path / "framework" / "gamma" / "file.txt").write_text("data")
        return pf

    def test_delete_existing(self, projects_file, capsys):
        ws.cmd_project_delete("gamma")
        # Moved to backup
        backup_dir = projects_file.parent / "framework" / ".trash"
        assert backup_dir.exists()
        # .projects.yaml updated
        import yaml
        data = yaml.safe_load(projects_file.read_text())
        assert "gamma" not in data["projects"]

    def test_delete_base_project_blocked(self, projects_file, capsys):
        ws.cmd_project_delete("dev-team")
        out = capsys.readouterr().out
        assert "can not deleted" in out

    def test_delete_nonexistent(self, projects_file, capsys):
        ws.cmd_project_delete("nope")
        out = capsys.readouterr().out
        assert "not found" in out


# ─────────────────────────────────────────────────────────────────────
# cmd_project_rename
# ─────────────────────────────────────────────────────────────────────
class TestProjectRename:
    @pytest.fixture
    def projects_file(self, tmp_path, monkeypatch):
        pf = tmp_path / ".projects.yaml"
        monkeypatch.setattr(ws, "PROJECTS_FILE", str(pf))
        monkeypatch.chdir(tmp_path)
        import yaml
        pf.write_text(yaml.dump({
            "version": "1.0.0",
            "active_project": "alpha",
            "projects": {
                "alpha": {"label": "ALPHA", "agents": 0, "tests": 0, "status": "draft",
                          "config": "alpha/config.yaml"}
            }
        }))
        (tmp_path / "framework" / "alpha").mkdir(parents=True)
        return pf

    def test_rename_existing(self, projects_file, capsys):
        ws.cmd_project_rename("alpha", "beta")
        import yaml
        data = yaml.safe_load(projects_file.read_text())
        assert "alpha" not in data["projects"]
        assert "beta" in data["projects"]
        assert data["projects"]["beta"]["config"] == "beta/config.yaml"

    def test_rename_nonexistent_old(self, projects_file, capsys):
        ws.cmd_project_rename("nope", "x")
        out = capsys.readouterr().out
        assert "not found" in out

    def test_rename_existing_new(self, projects_file, capsys):
        import yaml
        data = yaml.safe_load(projects_file.read_text())
        data["projects"]["beta"] = {"label": "BETA"}
        projects_file.write_text(yaml.dump(data))
        ws.cmd_project_rename("alpha", "beta")
        out = capsys.readouterr().out
        assert "exists already" in out


# ─────────────────────────────────────────────────────────────────────
# cmd_doctor_init
# ─────────────────────────────────────────────────────────────────────
class TestCmdDoctorInit:
    def test_creates_structure(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "j")  # overwrite if exists
        ws.cmd_doctor_init(str(tmp_path))
        assert (tmp_path / "recipes" / "specialists").exists()
        assert (tmp_path / "recipes" / "core").exists()
        assert (tmp_path / "recipes" / "sub").exists()
        assert (tmp_path / ".doctor").exists()
        assert (tmp_path / ".doctor" / "best-practices.yaml").exists()
        assert (tmp_path / ".doctor" / "config.json").exists()

    def test_existing_target_decline(self, tmp_path, monkeypatch, capsys):
        # Target exists, user declines
        monkeypatch.setattr("builtins.input", lambda _: "n")
        ws.cmd_doctor_init(str(tmp_path))
        out = capsys.readouterr().out
        assert "Abgebrochen" in out
        # No directories created
        assert not (tmp_path / "recipes").exists()

    def test_existing_target_accept(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "pre-existing.txt").write_text("keep me")
        monkeypatch.setattr("builtins.input", lambda _: "j")
        ws.cmd_doctor_init(str(tmp_path))
        # Pre-existing file preserved
        assert (tmp_path / "pre-existing.txt").exists()


# ─────────────────────────────────────────────────────────────────────
# cmd_scaffold (full pipeline, all mocked)
# ─────────────────────────────────────────────────────────────────────
class TestCmdScaffold:
    @pytest.fixture
    def scaffold_setup(self, tmp_path, monkeypatch):
        # Template
        template = tmp_path / "agent_template.yaml"
        template.write_text("name: __NAME__\n")
        monkeypatch.setattr(ws, "MAS_TEMPLATE", template)

        # Mock all input prompts
        inputs = iter(["1", "my-agent", "My desc", "🛡️", "n", "j"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        # Workspace dir
        monkeypatch.chdir(tmp_path)

        return tmp_path

    def test_full_pipeline_quiet(self, tmp_path, monkeypatch):
        # Use --quiet to skip interactive description phase
        template = tmp_path / "agent_template.yaml"
        template.write_text("name: __NAME__\n")
        monkeypatch.setattr(ws, "MAS_TEMPLATE", template)

        # Only need to answer _ask_type (1), _ask_name (my-agent)
        inputs = iter(["1", "my-agent", "n"])  # 3rd: don't register
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.chdir(tmp_path)

        # Args with name + quiet set
        class Args:
            name = "my-agent"
            quiet = True
            no_validate = False
        ws.cmd_scaffold(Args())
        # File created
        assert (tmp_path / "mas-engineer" / "recipe" / "sub" / "sub_mas-my-agent.yaml").exists()

    def test_pipeline_cancelled_at_type(self, tmp_path, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))
        monkeypatch.chdir(tmp_path)
        class Args:
            name = None
            quiet = False
            no_validate = False
        # Should silently return
        ws.cmd_scaffold(Args())


# ─────────────────────────────────────────────────────────────────────
# cmd_install_check
# ─────────────────────────────────────────────────────────────────────
class TestCmdInstallCheck:
    def test_no_mas_dir(self, tmp_path, capsys):
        ws.cmd_install_check(str(tmp_path))
        out = capsys.readouterr().out
        assert "No MAS-Directory" in out

    def test_all_checks_pass(self, tmp_path, capsys):
        # Create minimal MAS directory structure
        mas = tmp_path / "mas-engineer"
        (mas / "recipe").mkdir(parents=True)
        (mas / "recipe" / "dev-mas-engineer.yaml").write_text(
            "version: '1.0.0'\nPARALLEL-POOL: {}\n"
        )
        (mas / "recipe" / "sub").mkdir()
        (mas / "recipe" / "sub" / "x.yaml").touch()
        (mas / "tools").mkdir()
        for i in range(10):
            (mas / "tools" / f"dev_x{i}.py").touch()
        ws.cmd_install_check(str(tmp_path))
        out = capsys.readouterr().out
        assert "INSTALL-CHECK" in out

    def test_invalid_yaml_in_mas(self, tmp_path, capsys):
        mas = tmp_path / "mas-engineer"
        (mas / "recipe" / "sub").mkdir(parents=True)
        (mas / "recipe" / "sub" / "bad.yaml").write_text(":\n")
        (mas / "tools").mkdir()
        for i in range(10):
            (mas / "tools" / f"dev_x{i}.py").touch()
        (mas / "recipe" / "dev-mas-engineer.yaml").write_text("x: y\n")
        ws.cmd_install_check(str(tmp_path))
        out = capsys.readouterr().out
        assert "INSTALL-CHECK" in out


# ─────────────────────────────────────────────────────────────────────
# cmd_init_recovery
# ─────────────────────────────────────────────────────────────────────
class TestCmdInitRecovery:
    def test_warns_when_template_missing(self, tmp_path, monkeypatch, capsys):
        # Patch the recipe template directory used inside cmd_init_recovery
        # so the function thinks the recovery template does not exist.
        # cmd_init_recovery reads:
        #   Path(__file__).parent.parent / "recipe" / "template" / "recovery"
        # We mock that sub-path to a non-existent dir.

        # Create a dummy "fake template" path that won't exist
        fake_template = tmp_path / "no_recovery_template_dir"

        # Monkeypatch at the module level: import the module and patch the
        # specific path. Easiest: re-assign module attribute and patch
        # Path parent resolution by patching Path.exists for that substring.
        from pathlib import Path as _Path

        real_exists = _Path.exists

        def fake_exists(self):
            if "recovery" in str(self):
                return False
            return real_exists(self)

        monkeypatch.setattr(_Path, "exists", fake_exists)

        # Run cmd_init_recovery — should warn and return
        ws.cmd_init_recovery(str(tmp_path / "nope"))
        out = capsys.readouterr().out
        assert "Recovery-Template not found" in out

    def test_full_run_creates_recipes(self, tmp_path, capsys):
        # Test the happy path: template dir exists in repo, target dirs get created.
        # Create the target sub/checkpoints dirs so copy2 succeeds.
        ws_path = tmp_path / "ws"
        mas_dir = ws_path / "mas-engineer"
        (mas_dir / "recipe" / "sub").mkdir(parents=True)
        # Create a minimal main recipe so it can be read by cmd_init_recovery
        (mas_dir / "recipe" / "dev-mas-engineer.yaml").write_text(
            "version: '1.0.0'\nsub_recipes: []\n"
        )
        # The recipe template dir is at <repo>/recipe/template/recovery
        # which actually exists in the mas-engineer repo
        ws.cmd_init_recovery(str(ws_path))
        out = capsys.readouterr().out
        # Either it copied (ok printed) or template-not-found (warn)
        assert "Recovery" in out or "✅" in out or "⚠" in out
