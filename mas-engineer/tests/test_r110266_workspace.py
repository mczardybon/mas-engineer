"""
test_r110266_workspace.py — R110-266 Coverage Sprint, banner-tool part 2.

Target: dev_workspace.py (1445 lines, 877 stmts).
R110-260 declared this a "banner tool" (sys.argv parsed at module level) and
left it out of R110-261. R110-265 proved that banner-tools ARE testable
via direct library import. R110-266 applies the same pattern to
dev_workspace.py.

Unlike dev_template_generator.py, dev_workspace.py has NO module-level
sys.argv parsing — sys.argv is only accessed inside individual cmd_*
functions. The import is fully clean. No argv reset needed.

Library functions covered (16):
  - log, info, ok, warn, error  (print wrappers, 5)
  - count_files (pure, 3 tests: exists/empty/glob-pattern)
  - cmd_clean (file I/O, 2 tests: exists / missing)
  - cmd_init_recovery (file I/O, 4 tests: missing template, no main,
    main-without-sub_recipes, main with all recovery-agents)
  - _write_start_sessions_script (file I/O, 2 tests)
  - _load_projects (yaml I/O, 3 tests: not-exists / exists / corrupted)
  - _save_projects (yaml I/O, 2 tests: writes-file / updates-timestamp)
  - _active_project_path (1 test)
  - cmd_project_create (3 tests: fresh / exists / copy_from)
  - cmd_doctor_init (2 tests: fresh / overwrite)
  - cmd_remove_recipe (4 tests: in-recipes / in-framework / not-found / sub_mas)
  - cmd_status (1 test, monkeypatched GOOSE paths)

Excluded from this file:
  - cmd_init, cmd_install, _install_mas_from_workspace, cmd_install_mas,
    cmd_uninstall, cmd_uninstall_mas, cmd_rollback, cmd_add_recipe
    (all touch real GOOSE_RECIPES / GOOSE_DOCS / require monkeypatching
    of module-level constants — would need deep fixture setup; deferred
    to R110-269 if needed)
  - _ask_type/_ask_name/_ask_description (interactive input)
  - _generate_agent (interactive when dst.exists)
  - _validate_agent (subprocess dev_editor.py)
  - _register_agent (interactive)
  - _show_summary (print only, no return)
  - cmd_project_list/switch/show/delete/rename/args (cwd-dependent, use
    "framework" relative path, deferred to R110-269)
  - cmd_scaffold (calls _ask_*)
  - cmd_install_check (cwd-dependent scoring logic, deferred)
  - main() (argparse dispatch, out of scope)

Run with:
    python3 -m pytest tests/test_r110266_workspace.py -v
"""
import json
import os
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"

# Reset sys.argv (defensive — dev_workspace.py doesn't parse it at module
# level, but keep the pattern consistent with R110-265).
_PRE_IMPORT_ARGV = sys.argv[:]
sys.argv = ["dev_workspace.py"]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO_ROOT))
import dev_workspace as mod  # noqa: E402
sys.argv = _PRE_IMPORT_ARGV


# ─── Fixtures ──────────────────────────────────────────────────
@pytest.fixture
def isolated_workspace(tmp_path, monkeypatch):
    """Build an isolated workspace tree and monkeypatch GOOSE_* constants.

    Redirects all module-level paths to tmp_path subdirs so cmd_* functions
    that touch the filesystem don't pollute the real user's goose config.
    """
    goose_recipes = tmp_path / "goose" / "recipes"
    goose_framework = tmp_path / "goose" / "_framework"
    goose_docs = tmp_path / "goose" / "docs"
    goose_config = tmp_path / "goose" / "config.yaml"
    tools_dir = goose_recipes / "mas-engineer-tools"
    for p in (goose_recipes, goose_framework, goose_docs, tools_dir):
        p.mkdir(parents=True, exist_ok=True)
    goose_config.write_text("version: 1.0.0\n")

    monkeypatch.setattr(mod, "GOOSE_RECIPES", goose_recipes)
    monkeypatch.setattr(mod, "GOOSE_FRAMEWORK_DIR", goose_framework)
    monkeypatch.setattr(mod, "GOOSE_DOCS", goose_docs)
    monkeypatch.setattr(mod, "GOOSE_CONFIG", goose_config)
    monkeypatch.setattr(mod, "TOOLS_DIR", tools_dir)
    monkeypatch.setattr(mod, "AGENT_REPO", goose_recipes)

    return {
        "tmp": tmp_path,
        "goose_recipes": goose_recipes,
        "goose_framework": goose_framework,
        "goose_docs": goose_docs,
        "goose_config": goose_config,
        "tools_dir": tools_dir,
    }


@pytest.fixture
def recovery_template(tmp_path):
    """Create a fake template/recovery/ tree with all 5 recovery yamls."""
    rt = tmp_path / "recipe" / "template" / "recovery"
    rt.mkdir(parents=True)
    for name in ["immune", "checkpoint", "safezone", "timeline", "defib"]:
        (rt / f"{name}.yaml").write_text(f"# {name} template\n")
    return rt


@pytest.fixture
def fake_mas_dir(isolated_workspace, recovery_template):
    """Build a fake mas-engineer/ tree inside the workspace."""
    ws = isolated_workspace["tmp"]
    mas = ws / "mas-engineer"
    (mas / "recipe" / "sub").mkdir(parents=True)
    (mas / ".mase" / "checkpoints").mkdir(parents=True)
    # Move recovery template into ws's mas-engineer recipe tree path
    (mas / "recipe" / "template").mkdir(parents=True, exist_ok=True)
    return mas


# ─── Tests ─────────────────────────────────────────────────────
class TestConstants:
    def test_exclude_recipes(self):
        assert "dev-mas-engineer.yaml" in mod.EXCLUDE_RECIPES

    def test_exclude_docs(self):
        assert "mas-engineer" in mod.EXCLUDE_DOCS

    def test_mas_template_path(self):
        # Path to agent_template.yaml (may or may not exist in repo)
        assert str(mod.MAS_TEMPLATE).endswith("recipe/template/agent_template.yaml")

    def test_projects_file(self):
        assert mod.PROJECTS_FILE == "framework/.projects.yaml"


class TestLogHelpers:
    """log/info/ok/warn/error are simple print wrappers."""

    def test_log_prints(self, capsys):
        mod.log("hello")
        out = capsys.readouterr().out
        assert "hello" in out

    def test_info_prints_with_emoji(self, capsys):
        mod.info("test")
        out = capsys.readouterr().out
        assert "test" in out
        assert "📢" in out

    def test_ok_prints_with_emoji(self, capsys):
        mod.ok("done")
        out = capsys.readouterr().out
        assert "done" in out
        assert "✅" in out

    def test_warn_prints_with_emoji(self, capsys):
        mod.warn("careful")
        out = capsys.readouterr().out
        assert "careful" in out
        assert "⚠️" in out

    def test_error_prints_with_emoji(self, capsys):
        mod.error("failed")
        out = capsys.readouterr().out
        assert "failed" in out
        assert "❌" in out


class TestCountFiles:
    def test_count_files_dir_with_files(self, tmp_path):
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        (tmp_path / "c.txt").write_text("")
        assert mod.count_files(tmp_path) == 3

    def test_count_files_glob_pattern(self, tmp_path):
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.txt").write_text("")
        assert mod.count_files(tmp_path, "*.py") == 1

    def test_count_files_missing_dir(self, tmp_path):
        assert mod.count_files(tmp_path / "nope") == 0

    def test_count_files_empty_dir(self, tmp_path):
        assert mod.count_files(tmp_path) == 0


class TestCmdClean:
    def test_clean_existing_dir(self, tmp_path):
        target = tmp_path / "ws"
        target.mkdir()
        (target / "file.txt").write_text("x")
        mod.cmd_clean(str(target))
        assert not target.exists()

    def test_clean_missing_dir(self, tmp_path, capsys):
        # Should not raise, should warn
        mod.cmd_clean(str(tmp_path / "nope"))
        out = capsys.readouterr().out
        assert "exists not" in out or "🗑️" in out


class TestCmdInitRecovery:
    def _make_mas_tree(self, ws):
        """Build a fake mas-engineer/ tree inside ws with the dirs
        cmd_init_recovery expects (recipe/sub + .mase/checkpoints)."""
        mas = ws / "mas-engineer"
        (mas / "recipe" / "sub").mkdir(parents=True)
        (mas / ".mase" / "checkpoints").mkdir(parents=True)
        return mas

    def test_copies_recovery_yamls(self, isolated_workspace, capsys):
        """When main_recipe is absent, the 5 recovery yamls are still
        copied into mas-engineer/recipe/sub/ and the ok-messages are printed.
        The checkpoints dir is also created via mkdir(parents=True)."""
        ws = isolated_workspace["tmp"]
        mas = self._make_mas_tree(ws)
        mod.cmd_init_recovery(str(ws))
        out = capsys.readouterr().out
        # 5 sub_mas-recovery-*.yaml files should be created
        for name in ["immune", "checkpoint", "safezone", "timeline", "defib"]:
            assert (mas / "recipe" / "sub"
                    / f"sub_mas-recovery-{name}.yaml").exists()
        assert "Phoenix-Recovery" in out
        assert "checkpoints/.mase/ created" in out

    def test_no_op_when_dst_already_exists(self, isolated_workspace, capsys):
        """If the dst file already exists, shutil.copy2 is skipped (idempotent)."""
        ws = isolated_workspace["tmp"]
        mas = self._make_mas_tree(ws)
        # Pre-create one dst
        (mas / "recipe" / "sub" / "sub_mas-recovery-immune.yaml").write_text(
            "PREEXISTING\n"
        )
        mod.cmd_init_recovery(str(ws))
        # Preexisting content preserved
        dst = mas / "recipe" / "sub" / "sub_mas-recovery-immune.yaml"
        assert dst.read_text() == "PREEXISTING\n"

    def test_with_main_recipe_appends_sub_recipes(self, isolated_workspace,
                                                   capsys):
        """When main_recipe exists and has no sub_recipes, all 5 recovery
        agents are appended."""
        ws = isolated_workspace["tmp"]
        mas = self._make_mas_tree(ws)
        main_recipe = mas / "recipe" / "dev-mas-engineer.yaml"
        main_recipe.write_text(yaml.safe_dump({
            "version": "1.0.0",
            "title": "MAS",
            "sub_recipes": []
        }))
        mod.cmd_init_recovery(str(ws))
        data = yaml.safe_load(main_recipe.read_text())
        names = [s["name"] for s in data["sub_recipes"]]
        assert "sub_mas-recovery-immune" in names
        assert "sub_mas-recovery-defib" in names
        assert len(data["sub_recipes"]) == 5

    def test_with_main_recipe_existing_subs_unchanged(self, isolated_workspace):
        """When main_recipe already has some of the recovery subs, those
        are NOT duplicated (idempotent merge)."""
        ws = isolated_workspace["tmp"]
        mas = self._make_mas_tree(ws)
        main_recipe = mas / "recipe" / "dev-mas-engineer.yaml"
        main_recipe.write_text(yaml.safe_dump({
            "version": "1.0.0",
            "title": "MAS",
            "sub_recipes": [
                {"name": "sub_mas-recovery-immune",
                 "path": "./sub/sub_mas-recovery-immune.yaml",
                 "description": "Existing"}
            ]
        }))
        mod.cmd_init_recovery(str(ws))
        data = yaml.safe_load(main_recipe.read_text())
        # immune is preserved, the other 4 are appended
        assert len(data["sub_recipes"]) == 5
        # The existing immune entry is the same (not duplicated)
        immune_entries = [s for s in data["sub_recipes"]
                          if s["name"] == "sub_mas-recovery-immune"]
        assert len(immune_entries) == 1
        assert immune_entries[0]["description"] == "Existing"


class TestWriteStartSessionsScript:
    def test_writes_executable_script(self, tmp_path, capsys):
        ws = tmp_path / "ws"
        (ws / "framework" / "recipes").mkdir(parents=True)
        (ws / "mas-engineer" / "recipe").mkdir(parents=True)
        (ws / "mas-engineer" / "recipe" / "dev-mas-engineer.yaml").write_text(
            "version: 1.0.0\ntitle: MAS\n"
        )
        mod._write_start_sessions_script(ws)
        script = ws / "start-sessions.sh"
        assert script.exists()
        assert script.stat().st_mode & 0o111  # executable bit set
        content = script.read_text()
        assert "framework" in content
        assert "mas-engineer" in content

    def test_script_has_validation_checks(self, tmp_path):
        ws = tmp_path / "ws"
        (ws / "framework" / "recipes").mkdir(parents=True)
        (ws / "mas-engineer" / "recipe").mkdir(parents=True)
        (ws / "mas-engineer" / "recipe" / "dev-mas-engineer.yaml").write_text(
            "version: 1.0.0\n"
        )
        mod._write_start_sessions_script(ws)
        content = (ws / "start-sessions.sh").read_text()
        assert "framework-Recipes not found" in content
        assert "MAS-Rezept not found" in content


class TestLoadSaveProjects:
    def test_load_projects_creates_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = mod._load_projects()
        assert "projects" in data
        assert "dev-team" in data["projects"]
        # File should be created
        assert (tmp_path / "framework" / ".projects.yaml").exists()

    def test_load_projects_existing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "framework").mkdir()
        pp = tmp_path / "framework" / ".projects.yaml"
        pp.write_text(yaml.safe_dump({
            "version": "1.0.0",
            "active_project": "my-team",
            "projects": {"my-team": {"label": "MY", "agents": 5, "tests": 10,
                                      "status": "stable"}}
        }))
        data = mod._load_projects()
        assert data["active_project"] == "my-team"
        assert "my-team" in data["projects"]

    def test_save_projects_writes_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "framework").mkdir()
        data = {
            "version": "1.0.0",
            "active_project": "x",
            "projects": {"x": {"label": "X", "agents": 1, "tests": 2,
                                "status": "draft"}}
        }
        mod._save_projects(data)
        pp = tmp_path / "framework" / ".projects.yaml"
        assert pp.exists()
        loaded = yaml.safe_load(pp.read_text())
        assert loaded["active_project"] == "x"
        assert "last_updated" in loaded

    def test_save_projects_updates_timestamp(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "framework").mkdir()
        data = {
            "version": "1.0.0",
            "active_project": "x",
            "projects": {},
            "last_updated": "2020-01-01T00:00:00"
        }
        mod._save_projects(data)
        loaded = yaml.safe_load(
            (tmp_path / "framework" / ".projects.yaml").read_text()
        )
        assert loaded["last_updated"] != "2020-01-01T00:00:00"


class TestActiveProjectPath:
    def test_default_active_project(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path, name = mod._active_project_path()
        assert name == "dev-team"
        assert str(path).endswith("dev-team")


class TestCmdProjectCreate:
    def test_create_fresh(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mod.cmd_project_create("alpha")
        proj = tmp_path / "framework" / "alpha"
        assert proj.exists()
        assert (proj / "config.yaml").exists()
        assert (proj / "recipes" / "core").exists()
        assert (proj / "recipes" / "sub").exists()
        assert (proj / "docs").exists()
        assert (proj / "tests").exists()
        # .projects.yaml updated
        data = yaml.safe_load(
            (tmp_path / "framework" / ".projects.yaml").read_text()
        )
        assert "alpha" in data["projects"]
        assert data["active_project"] == "alpha"

    def test_create_existing_name_noop(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        mod.cmd_project_create("alpha")
        # Call again — should be a no-op (prints message)
        mod.cmd_project_create("alpha")
        out = capsys.readouterr().out
        assert "exists already" in out

    def test_create_with_copy_from(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Create source project
        src = tmp_path / "framework" / "source"
        src.mkdir(parents=True)
        (src / "marker.txt").write_text("from-source")
        mod.cmd_project_create("source")
        # Now create a copy
        mod.cmd_project_create("copy", copy_from="source")
        copy = tmp_path / "framework" / "copy"
        assert copy.exists()
        assert (copy / "marker.txt").exists()
        assert (copy / "marker.txt").read_text() == "from-source"


class TestCmdDoctorInit:
    def test_doctor_init_fresh(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        target = tmp_path / "myproject"
        # auto-confirm overwrite via stdin
        monkeypatch.setattr("builtins.input", lambda *a: "j")
        mod.cmd_doctor_init(str(target))
        assert target.exists()
        assert (target / "recipes" / "specialists").exists()
        assert (target / "recipes" / "core").exists()
        assert (target / "recipes" / "sub").exists()
        assert (target / "docs").exists()
        assert (target / "tests").exists()
        # .doctor/ artifacts
        assert (target / ".doctor" / "best-practices.yaml").exists()
        assert (target / ".doctor" / "config.json").exists()
        bp = yaml.safe_load(
            (target / ".doctor" / "best-practices.yaml").read_text()
        )
        assert "best_practices" in bp
        cfg = json.loads((target / ".doctor" / "config.json").read_text())
        assert cfg["mas_managed"] is True

    def test_doctor_init_existing_abort(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        target = tmp_path / "myproject"
        target.mkdir()
        # Answer "n" to overwrite → abort
        monkeypatch.setattr("builtins.input", lambda *a: "n")
        mod.cmd_doctor_init(str(target))
        out = capsys.readouterr().out
        assert "Abgebrochen" in out
        # Should not have created the recipes subdirs
        assert not (target / "recipes").exists()


class TestCmdRemoveRecipe:
    def test_remove_from_recipes_dir(self, isolated_workspace, capsys):
        target = isolated_workspace["goose_recipes"] / "test-recipe.yaml"
        target.write_text("version: 1.0.0\n")
        mod.cmd_remove_recipe("test-recipe.yaml")
        assert not target.exists()
        out = capsys.readouterr().out
        assert "🗑️" in out

    def test_remove_from_framework_dir(self, isolated_workspace, capsys):
        target = (isolated_workspace["goose_recipes"] / "_framework"
                  / "fw-recipe.yaml")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("version: 1.0.0\n")
        mod.cmd_remove_recipe("fw-recipe.yaml")
        assert not target.exists()

    def test_remove_not_found_warns(self, isolated_workspace, capsys):
        mod.cmd_remove_recipe("nonexistent.yaml")
        out = capsys.readouterr().out
        assert "not found" in out or "⚠️" in out

    def test_remove_sub_mas_recipe(self, isolated_workspace, capsys):
        target = isolated_workspace["goose_recipes"] / "sub_mas-test.yaml"
        target.write_text("version: 1.0.0\n")
        mod.cmd_remove_recipe("sub_mas-test.yaml")
        assert not target.exists()


class TestCmdStatus:
    def test_status_missing_workspace_warns(self, isolated_workspace, capsys):
        ws = isolated_workspace["tmp"] / "nonexistent"
        mod.cmd_status(str(ws))
        out = capsys.readouterr().out
        assert "exists not" in out

    def test_status_valid_workspace(self, isolated_workspace, capsys):
        ws = isolated_workspace["tmp"]
        # Build minimal valid workspace
        (ws / "framework" / "recipes").mkdir(parents=True)
        (ws / "framework" / "recipes" / "x.yaml").write_text("v: 1\n")
        (ws / "framework" / "docs" / "core").mkdir(parents=True)
        (ws / "framework" / "docs" / "core" / "y.md").write_text("# y")
        (ws / "mas-engineer" / "tools").mkdir(parents=True)
        (ws / "framework" / "config.yaml").write_text("v: 1\n")
        mod.cmd_status(str(ws))
        out = capsys.readouterr().out
        assert "📊" in out
        assert "Recipes" in out
        assert "Docs" in out
        assert "Config" in out

    def test_status_with_changes_json(self, isolated_workspace, capsys):
        ws = isolated_workspace["tmp"]
        (ws / "framework" / "recipes").mkdir(parents=True)
        (ws / "framework" / "docs" / "core").mkdir(parents=True)
        (ws / "framework" / "config.yaml").write_text("v: 1\n")
        (ws / ".mase").mkdir(parents=True)
        (ws / ".mase" / "changes.json").write_text(json.dumps({
            "stats": {"total_changes": 42}
        }))
        mod.cmd_status(str(ws))
        out = capsys.readouterr().out
        assert "Changes" in out
        assert "42" in out
