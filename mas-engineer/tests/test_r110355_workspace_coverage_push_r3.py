"""
R110-355: coverage-push round 3 for tools/dev_workspace.py.

Target: cmd_project_* functions (L1064-1242, ~178 lines of
project-list/create/switch/show/delete/rename logic). These
are pure functions that read/write framework/.projects.yaml
and create/delete/symlink framework/<name>/ directories.

dev_workspace.py round 1+2 (R110-351+353) brought coverage
from 0% to 31% on 595 testable stmts. Round 3 targets
6 cmd_project functions:

  1. cmd_project_list (L1064-1074) — print all projects.
     Tests:
     - empty projects → just prints header
     - 1 project → prints that project
     - 2 projects → both listed
     - active project marker appears

  2. cmd_project_create (L1077-1124) — create new project.
     Tests:
     - name exists already → no-op
     - create without copy_from → creates framework/<name>/ + subdirs + config.yaml
     - create with copy_from → shutil.copytree from existing
     - copy_from not found → no-op with error msg
     - sets active_project to new name
     - creates framework/current → <name> symlink

  3. cmd_project_switch (L1126-1144) — switch active.
     Tests:
     - name not found → no-op + shows list
     - name found → sets active + updates symlink

  4. cmd_project_show (L1146-1157) — show project details.
     Tests:
     - name not found → no-op
     - name found → prints label, type, agents, tests, status

  5. cmd_project_delete (L1159-1184) — delete project.
     Tests:
     - dev-team cannot be deleted (protected)
     - name not found → no-op
     - name found → moves to .trash + updates projects.yaml
     - if active was deleted, active becomes dev-team

  6. cmd_project_rename (L1186-1209) — rename project.
     Tests:
     - old not found → no-op
     - new exists already → no-op
     - rename ok → renames dir + updates projects.yaml
     - if active was old, active becomes new + symlink updates

Target: bump coverage from 31% to ~45% (+14pp on 595 stmts).
"""
import sys
import importlib
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


class TestCmdProjectList:
    """cmd_project_list (L1064-1074)."""

    def test_empty_projects_prints_header_only(self, ws_mod, tmp_path, capsys):
        """No projects → just header + footer with total=0."""
        # Create the projects file with no projects
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        ws_mod.cmd_project_list()
        captured = capsys.readouterr()
        assert "Total: 0" in captured.out or "0 project" in captured.out

    def test_single_project_listed(self, ws_mod, tmp_path, capsys):
        """1 project → listed with name, agents, tests, status."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "myproj": {"label": "MYPROJ", "agents": 5, "tests": 10, "status": "stable"}
            },
            "active_project": "myproj",
        }))
        ws_mod.cmd_project_list()
        captured = capsys.readouterr()
        assert "myproj" in captured.out
        assert "stable" in captured.out or "5" in captured.out
        assert "<- active" in captured.out or "active" in captured.out

    def test_multiple_projects_all_listed(self, ws_mod, tmp_path, capsys):
        """3 projects → all 3 listed, total=3."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "p1": {"label": "P1", "agents": 1, "tests": 2, "status": "stable"},
                "p2": {"label": "P2", "agents": 3, "tests": 4, "status": "draft"},
                "p3": {"label": "P3", "agents": 5, "tests": 6, "status": "archived"},
            },
            "active_project": "p2",
        }))
        ws_mod.cmd_project_list()
        captured = capsys.readouterr()
        assert "p1" in captured.out
        assert "p2" in captured.out
        assert "p3" in captured.out
        assert "Total: 3" in captured.out

    def test_active_marker_appears(self, ws_mod, tmp_path, capsys):
        """Active project gets '<- active' marker."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "p1": {"label": "P1", "agents": 0, "tests": 0, "status": "stable"},
                "p2": {"label": "P2", "agents": 0, "tests": 0, "status": "stable"},
            },
            "active_project": "p2",
        }))
        ws_mod.cmd_project_list()
        captured = capsys.readouterr()
        # Active marker should appear somewhere with p2
        assert "active" in captured.out

    def test_unknown_status_gets_weiss_marker(self, ws_mod, tmp_path, capsys):
        """Project with unknown status still gets listed."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "weird": {"label": "WEIRD", "agents": 0, "tests": 0, "status": "weird-status"}
            },
            "active_project": "",
        }))
        ws_mod.cmd_project_list()
        captured = capsys.readouterr()
        assert "weird" in captured.out


class TestCmdProjectCreate:
    """cmd_project_create (L1077-1124)."""

    def test_existing_name_no_op(self, ws_mod, tmp_path, capsys):
        """Project with same name exists → no-op, no overwrite."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / "myproj").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"myproj": {"label": "MYPROJ"}},
            "active_project": "myproj",
        }))
        ws_mod.cmd_project_create("myproj")
        # Should print "exists already"
        captured = capsys.readouterr()
        assert "exists" in captured.out

    def test_create_without_copy_from(self, ws_mod, tmp_path, capsys):
        """Create new project → creates framework/<name>/ with subdirs + config.yaml."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        ws_mod.cmd_project_create("newproj")
        proj_dir = tmp_path / "framework" / "newproj"
        assert proj_dir.exists()
        # Subdirs should exist
        assert (proj_dir / "recipes" / "core").exists()
        assert (proj_dir / "recipes" / "sub").exists()
        assert (proj_dir / "docs").exists()
        assert (proj_dir / "tests").exists()
        # config.yaml
        assert (proj_dir / "config.yaml").exists()
        cfg = yaml.safe_load((proj_dir / "config.yaml").read_text())
        assert cfg["project_name"] == "newproj"
        # Symlink
        assert (tmp_path / "framework" / "current").is_symlink()
        assert (tmp_path / "framework" / "current").readlink() == Path("newproj")

    def test_create_with_copy_from_existing(self, ws_mod, tmp_path):
        """Create with copy_from → shutil.copytree from existing source."""
        # Create source project
        (tmp_path / "framework" / "src").mkdir(parents=True)
        (tmp_path / "framework" / "src" / "marker.txt").write_text("source")
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        ws_mod.cmd_project_create("newproj", copy_from="src")
        new_dir = tmp_path / "framework" / "newproj"
        assert new_dir.exists()
        # marker.txt should be copied
        assert (new_dir / "marker.txt").exists()
        assert (new_dir / "marker.txt").read_text() == "source"

    def test_copy_from_not_found(self, ws_mod, tmp_path, capsys):
        """copy_from points to nonexistent dir → no-op, error msg."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        ws_mod.cmd_project_create("newproj", copy_from="nonexistent")
        captured = capsys.readouterr()
        assert "not found" in captured.out
        # Project should NOT have been created
        assert not (tmp_path / "framework" / "newproj").exists()

    def test_create_sets_active_project(self, ws_mod, tmp_path):
        """Newly created project becomes active."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(
            "version: 1.0.0\nprojects: {}\nactive_project: ''\n"
        )
        ws_mod.cmd_project_create("newproj")
        # Re-read projects file
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert data["active_project"] == "newproj"
        # projects dict should have newproj
        assert "newproj" in data["projects"]


class TestCmdProjectSwitch:
    """cmd_project_switch (L1126-1144)."""

    def test_name_not_found(self, ws_mod, tmp_path, capsys):
        """name not in projects → no-op + calls cmd_project_list."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"existing": {"label": "EXISTING"}},
            "active_project": "existing",
        }))
        ws_mod.cmd_project_switch("nonexistent")
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_switch_updates_active(self, ws_mod, tmp_path):
        """Switch to existing project → active_project updated + symlink updated."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / "p1").mkdir()
        (tmp_path / "framework" / "p2").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "p1": {"label": "P1", "agents": 0, "tests": 0, "status": "stable"},
                "p2": {"label": "P2", "agents": 0, "tests": 0, "status": "stable"},
            },
            "active_project": "p1",
        }))
        # Create initial symlink
        (tmp_path / "framework" / "current").symlink_to("p1")
        ws_mod.cmd_project_switch("p2")
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert data["active_project"] == "p2"
        # Symlink updated
        assert (tmp_path / "framework" / "current").readlink() == Path("p2")


class TestCmdProjectShow:
    """cmd_project_show (L1146-1157)."""

    def test_name_not_found(self, ws_mod, tmp_path, capsys):
        """name not in projects → no-op."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"existing": {"label": "EXISTING"}},
            "active_project": "",
        }))
        ws_mod.cmd_project_show("nonexistent")
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_show_prints_details(self, ws_mod, tmp_path, capsys):
        """Show existing project → prints label, type, agents, tests, status."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "myproj": {
                    "label": "MYPROJ",
                    "type": "multi_agent_system",
                    "agents": 7,
                    "tests": 13,
                    "status": "stable",
                }
            },
            "active_project": "myproj",
        }))
        ws_mod.cmd_project_show("myproj")
        captured = capsys.readouterr()
        assert "MYPROJ" in captured.out
        assert "multi_agent_system" in captured.out
        assert "7" in captured.out
        assert "13" in captured.out
        assert "stable" in captured.out


class TestCmdProjectDelete:
    """cmd_project_delete (L1159-1184)."""

    def test_dev_team_cannot_be_deleted(self, ws_mod, tmp_path, capsys):
        """dev-team is protected → no-op, prints message."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"dev-team": {"label": "DEV-TEAM"}},
            "active_project": "dev-team",
        }))
        ws_mod.cmd_project_delete("dev-team")
        captured = capsys.readouterr()
        assert "dev-team" in captured.out
        # Project should still exist
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert "dev-team" in data["projects"]

    def test_name_not_found(self, ws_mod, tmp_path, capsys):
        """name not in projects → no-op."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"existing": {"label": "EXISTING"}},
            "active_project": "existing",
        }))
        ws_mod.cmd_project_delete("nonexistent")
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_delete_moves_to_trash(self, ws_mod, tmp_path):
        """Existing project → moved to .trash/ + removed from projects.yaml."""
        (tmp_path / "framework" / "myproj").mkdir(parents=True)
        (tmp_path / "framework" / "myproj" / "file.txt").write_text("x")
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"myproj": {"label": "MYPROJ", "config": "myproj/config.yaml"}},
            "active_project": "other",
        }))
        ws_mod.cmd_project_delete("myproj")
        # Project dir should be moved to .trash/
        assert not (tmp_path / "framework" / "myproj").exists()
        trash_dir = tmp_path / "framework" / ".trash"
        assert trash_dir.exists()
        # Some backup dir should exist with myproj_ prefix
        backups = list(trash_dir.iterdir())
        assert len(backups) >= 1
        assert any(b.name.startswith("myproj_") for b in backups)
        # projects.yaml updated
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert "myproj" not in data["projects"]

    def test_delete_active_project_resets_to_dev_team(self, ws_mod, tmp_path):
        """Deleting the active project → active becomes dev-team + symlink updated."""
        (tmp_path / "framework" / "dev-team").mkdir(parents=True)
        (tmp_path / "framework" / "myproj").mkdir()
        (tmp_path / "framework" / "current").symlink_to("myproj")
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "dev-team": {"label": "DEV-TEAM"},
                "myproj": {"label": "MYPROJ"},
            },
            "active_project": "myproj",
        }))
        ws_mod.cmd_project_delete("myproj")
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert data["active_project"] == "dev-team"
        # Symlink should now point to dev-team
        assert (tmp_path / "framework" / "current").readlink() == Path("dev-team")


class TestCmdProjectRename:
    """cmd_project_rename (L1186-1209)."""

    def test_old_not_found(self, ws_mod, tmp_path, capsys):
        """old name not in projects → no-op."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {"existing": {"label": "EXISTING"}},
            "active_project": "existing",
        }))
        ws_mod.cmd_project_rename("nonexistent", "newname")
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_new_exists_already(self, ws_mod, tmp_path, capsys):
        """new name already exists → no-op."""
        (tmp_path / "framework").mkdir()
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "old": {"label": "OLD"},
                "new": {"label": "NEW"},
            },
            "active_project": "old",
        }))
        ws_mod.cmd_project_rename("old", "new")
        captured = capsys.readouterr()
        assert "exists" in captured.out

    def test_rename_ok(self, ws_mod, tmp_path):
        """Rename ok → dir renamed + projects.yaml updated."""
        (tmp_path / "framework" / "old").mkdir(parents=True)
        (tmp_path / "framework" / "old" / "data.txt").write_text("x")
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "old": {"label": "OLD", "config": "old/config.yaml"}
            },
            "active_project": "",
        }))
        ws_mod.cmd_project_rename("old", "new")
        # Dir renamed
        assert not (tmp_path / "framework" / "old").exists()
        assert (tmp_path / "framework" / "new").exists()
        # data.txt preserved
        assert (tmp_path / "framework" / "new" / "data.txt").read_text() == "x"
        # projects.yaml updated
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert "old" not in data["projects"]
        assert "new" in data["projects"]
        assert data["projects"]["new"]["config"] == "new/config.yaml"

    def test_rename_active_updates_symlink(self, ws_mod, tmp_path):
        """Renaming the active project → active becomes new + symlink updated."""
        (tmp_path / "framework" / "old").mkdir(parents=True)
        (tmp_path / "framework" / "current").symlink_to("old")
        # Only 'old' in projects.yaml — 'new' must not exist (rename is supposed to create it)
        (tmp_path / "framework" / ".projects.yaml").write_text(yaml.dump({
            "version": "1.0.0",
            "projects": {
                "old": {"label": "OLD", "config": "old/config.yaml"},
            },
            "active_project": "old",
        }))
        ws_mod.cmd_project_rename("old", "new")
        data = yaml.safe_load((tmp_path / "framework" / ".projects.yaml").read_text())
        assert data["active_project"] == "new"
        assert (tmp_path / "framework" / "current").readlink() == Path("new")
