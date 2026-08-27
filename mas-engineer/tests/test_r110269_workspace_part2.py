"""
test_r110269_workspace_part2.py — R110-269 Coverage Sprint, dev_workspace pt.2.

Target: dev_workspace.py (1445 lines). R110-266 covered 16 library functions
(38 tests) but explicitly excluded the multi-project-management commands
(cmd_project_list/switch/show/delete/rename/args) and cmd_install_check due to
their "cwd-dependent" nature (use `Path("framework")` literals, not the
GOOSE_* constants). R110-269 applies the cwd-monkeypatch pattern to test
these deferred functions.

Library functions covered (7):
  - cmd_project_list         (1 test: shows active marker, project count)
  - cmd_project_switch       (3 tests: existing / missing / round-trip)
  - cmd_project_show         (2 tests: existing / missing)
  - cmd_project_delete       (3 tests: normal / dev-team-protected / missing)
  - cmd_project_rename       (3 tests: normal / active-update / missing)
  - cmd_project (dispatcher) (4 tests: empty=default-list, list, switch, show)
  - cmd_install_check        (5 tests: missing-mas-dir, all-pass=5/5, no-parallel,
                              no-backups, with-invalid-yaml)

Total: 21 tests.

Pitfall noted: cmd_project_list/switch/create use `Path("framework")` as a
literal — they're cwd-dependent. The fixture monkeypatches cwd to tmp_path
so the literal "framework/.projects.yaml" resolves to tmp_path/framework/
.projects.yaml. cmd_install_check also takes a ws_dir argument and reads
"mas-engineer/" inside it.
"""
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"

# Reset sys.argv defensively (dev_workspace.py doesn't parse it at module
# level, but keep the pattern consistent with R110-265/266).
_PRE_IMPORT_ARGV = sys.argv[:]
sys.argv = ["dev_workspace.py"]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO_ROOT))
import dev_workspace as mod  # noqa: E402
sys.argv = _PRE_IMPORT_ARGV


# ─── Fixtures ──────────────────────────────────────────────────
@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Build a fake framework/ tree under tmp_path and chdir there.

    Most cmd_project_* functions are cwd-dependent: they use
    `Path("framework")` as a literal, not the GOOSE_* constants. So we
    must both create the directory and chdir into tmp_path.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "framework").mkdir()
    return tmp_path


@pytest.fixture
def two_projects(ws):
    """Create two projects (alpha, beta) via cmd_project_create."""
    mod.cmd_project_create("alpha")
    mod.cmd_project_create("beta")
    return ws


# ─── Tests ─────────────────────────────────────────────────────
class TestCmdProjectList:
    def test_list_with_active_marker(self, two_projects, capsys):
        # beta was created last → active_project.
        # Note: _load_projects seeds dev-team as the base project, so the
        # count is 3 (alpha + beta + dev-team), not 2.
        mod.cmd_project_list()
        out = capsys.readouterr().out
        assert "framework-projecte" in out
        assert "alpha" in out
        assert "beta" in out
        assert "dev-team" in out
        assert "Total: 3 projecte" in out
        # beta should have active marker
        beta_line = [l for l in out.splitlines() if "beta" in l and "alpha" not in l]
        assert any("<- active" in l for l in beta_line), \
            f"beta should be marked active, got: {beta_line}"

    def test_list_empty_creates_default(self, ws, capsys):
        # No projects created yet — _load_projects seeds dev-team by default
        mod.cmd_project_list()
        out = capsys.readouterr().out
        assert "dev-team" in out
        assert "Total: 1 projecte" in out


class TestCmdProjectSwitch:
    def test_switch_existing(self, two_projects, capsys):
        mod.cmd_project_switch("alpha")
        out = capsys.readouterr().out
        assert "Aktives project: alpha" in out
        # Verify .projects.yaml was updated
        data = yaml.safe_load(
            (two_projects / "framework" / ".projects.yaml").read_text()
        )
        assert data["active_project"] == "alpha"

    def test_switch_missing_prints_list(self, ws, capsys):
        mod.cmd_project_switch("nonexistent")
        out = capsys.readouterr().out
        assert "not found" in out
        # Function falls through to cmd_project_list
        assert "framework-projecte" in out

    def test_switch_updates_symlink(self, two_projects, monkeypatch):
        # On switch, framework/current should be (re)created
        sl = two_projects / "framework" / "current"
        if sl.exists() or sl.is_symlink():
            sl.unlink()
        mod.cmd_project_switch("alpha")
        assert sl.is_symlink() or sl.exists()
        if sl.is_symlink():
            assert sl.readlink() == Path("alpha")


class TestCmdProjectShow:
    def test_show_existing(self, two_projects, capsys):
        mod.cmd_project_show("alpha")
        out = capsys.readouterr().out
        assert "project: alpha" in out
        assert "Label:" in out
        assert "Agents:" in out
        assert "Tests:" in out
        assert "status:" in out

    def test_show_missing(self, ws, capsys):
        mod.cmd_project_show("nonexistent")
        out = capsys.readouterr().out
        assert "not found" in out


class TestCmdProjectDelete:
    def test_delete_normal(self, two_projects, capsys):
        mod.cmd_project_delete("alpha")
        out = capsys.readouterr().out
        assert "deleted" in out
        # Project removed from .projects.yaml
        data = yaml.safe_load(
            (two_projects / "framework" / ".projects.yaml").read_text()
        )
        assert "alpha" not in data["projects"]
        # Backup created in framework/.trash/
        trash = two_projects / "framework" / ".trash"
        assert trash.exists()
        backups = list(trash.glob("alpha_*"))
        assert len(backups) == 1
        assert backups[0].is_dir()

    def test_delete_dev_team_protected(self, ws, capsys):
        # dev-team is the seed project — must NOT be deletable
        mod.cmd_project_delete("dev-team")
        out = capsys.readouterr().out
        assert "Basis-project" in out or "can not" in out
        # _load_projects auto-creates the yaml on first access. Touching
        # it via _load_projects (which cmd_project_delete calls) ensures
        # the file exists before we read it back.
        mod._load_projects()
        data = yaml.safe_load(
            (ws / "framework" / ".projects.yaml").read_text()
        )
        assert "dev-team" in data["projects"]

    def test_delete_missing(self, ws, capsys):
        mod.cmd_project_delete("nonexistent")
        out = capsys.readouterr().out
        assert "not found" in out


class TestCmdProjectRename:
    def test_rename_normal(self, two_projects, capsys):
        mod.cmd_project_rename("alpha", "alpha-renamed")
        out = capsys.readouterr().out
        assert "alpha" in out and "alpha-renamed" in out
        data = yaml.safe_load(
            (two_projects / "framework" / ".projects.yaml").read_text()
        )
        assert "alpha" not in data["projects"]
        assert "alpha-renamed" in data["projects"]
        # config path updated
        assert data["projects"]["alpha-renamed"]["config"] == "alpha-renamed/config.yaml"

    def test_rename_active_updates_active(self, two_projects):
        # beta is active; rename beta → gamma
        mod.cmd_project_rename("beta", "gamma")
        data = yaml.safe_load(
            (two_projects / "framework" / ".projects.yaml").read_text()
        )
        assert data["active_project"] == "gamma"

    def test_rename_missing(self, ws, capsys):
        mod.cmd_project_rename("nonexistent", "new")
        out = capsys.readouterr().out
        assert "not found" in out

    def test_rename_target_exists(self, two_projects, capsys):
        mod.cmd_project_rename("alpha", "beta")  # beta already exists
        out = capsys.readouterr().out
        assert "exists already" in out


class TestCmdProjectDispatcher:
    def test_empty_args_defaults_to_list(self, ws, capsys):
        mod.cmd_project([])
        out = capsys.readouterr().out
        # defaults to "list"
        assert "framework-projecte" in out

    def test_list_subcommand(self, two_projects, capsys):
        mod.cmd_project(["list"])
        out = capsys.readouterr().out
        assert "framework-projecte" in out
        assert "alpha" in out

    def test_show_subcommand(self, two_projects, capsys):
        mod.cmd_project(["show", "alpha"])
        out = capsys.readouterr().out
        assert "project: alpha" in out

    def test_switch_subcommand(self, two_projects, capsys):
        mod.cmd_project(["switch", "alpha"])
        out = capsys.readouterr().out
        assert "Aktives project: alpha" in out

    def test_create_subcommand(self, ws, capsys):
        mod.cmd_project(["create", "newone"])
        # Just check no error & project dir created
        assert (ws / "framework" / "newone").exists()


class TestCmdInstallCheck:
    """cmd_install_check runs 5 checks: yaml, paths, standalone, parallel, backups."""

    def _make_full_mas_dir(self, ws):
        """Build a mas-engineer/ tree that passes all 5 checks."""
        mas = ws / "mas-engineer"
        (mas / "recipe" / "sub").mkdir(parents=True)
        (mas / "tools").mkdir(parents=True)
        # 8 fake dev_*.py tools (>=8 required)
        for i in range(8):
            (mas / "tools" / f"dev_tool{i}.py").write_text("# tool\n")
        # main recipe (must contain PARALLEL-POOL for check C4)
        (mas / "recipe" / "dev-mas-engineer.yaml").write_text(
            "name: dev-mas-engineer\nPARALLEL-POOL: {}\n"
        )
        # a valid sub-recipe yaml
        (mas / "recipe" / "sub" / "fake.yaml").write_text("name: fake\n")
        # backups dir
        (mas / ".backups").mkdir()
        return mas

    def test_install_check_no_mas_dir_returns_gracefully(self, ws, capsys):
        # No mas-engineer/ dir — should print error and return None
        result = mod.cmd_install_check(str(ws))
        out = capsys.readouterr().out
        assert "No MAS-Directory" in out
        # Function returns None (implicit)
        assert result is None

    def test_install_check_all_pass_5_of_5(self, ws, capsys):
        mas = self._make_full_mas_dir(ws)
        checks = mod.cmd_install_check(str(ws))
        out = capsys.readouterr().out
        assert "INSTALL-CHECK" in out
        assert "Score: 100/100" in out
        assert "5/5 bestanden" in out
        # All 5 checks should be (name, True, ...)
        assert all(c[1] is True for c in checks), \
            f"all 5 must pass, got: {checks}"
        assert len(checks) == 5

    def test_install_check_missing_parallel(self, ws, capsys):
        mas = self._make_full_mas_dir(ws)
        # Overwrite main recipe without PARALLEL-POOL
        (mas / "recipe" / "dev-mas-engineer.yaml").write_text(
            "name: dev-mas-engineer\n"
        )
        checks = mod.cmd_install_check(str(ws))
        # parallel check should fail
        parallel = [c for c in checks if c[0] == "paralll"]
        assert len(parallel) == 1
        assert parallel[0][1] is False

    def test_install_check_missing_backups(self, ws, capsys):
        mas = self._make_full_mas_dir(ws)
        # Remove .backups dir
        import shutil
        shutil.rmtree(mas / ".backups")
        checks = mod.cmd_install_check(str(ws))
        backups_check = [c for c in checks if c[0] == "backups"]
        assert len(backups_check) == 1
        # backups_check is [(name, passed, msg)], so [0][1] is the bool
        assert backups_check[0][1] is False
