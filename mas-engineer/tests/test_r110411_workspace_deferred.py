"""
test_r110411_workspace_deferred.py — R110-266 deferral aufheben.

Targets the 7 R110-266-deferred cmd_* functions in tools/dev_workspace.py
using the existing `isolated_workspace` fixture (R110-266) that
monkeypatches all 6 GOOSE_* constants to tmp_path subdirs.

Strategy: same pattern as R110-266 (cmd_status) — fixture + sys.exit
catch + subprocess mock where needed. NOT touching real GOOSE paths,
NOT removing the `# pragma: no cover` markers (those are R110-266's
deferral declaration, kept for documentation even when tests cover
the lines). Coverage is achieved via `no cover` pragma REMOVAL, not
by mocking the pragma away — see R110-411 follow-up.

The 7 deferred functions:
  - cmd_init(ws_dir)              framework+MAS workspace scaffold
  - cmd_install(ws_dir)           subprocess install_framework.py
  - cmd_install_mas(ws_dir)       MAS-only install via _install_mas_from_workspace
  - cmd_uninstall()               framework uninstall, MAS bleibt
  - cmd_uninstall_mas()           MAS uninstall, framework bleibt
  - cmd_rollback(ws_dir)          git log + interactive rollback
  - cmd_add_recipe(ws, name)      single-recipe install with backup
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ─── Module path setup ───────────────────────────────────────
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "tools"))

import dev_workspace as mod  # noqa: E402

# ─── Fixtures ───────────────────────────────────────────────
@pytest.fixture
def ws_with_framework(tmp_path, monkeypatch):
    """Build workspace + isolated goose paths. Pre-populate GOOSE_RECIPES
    with a framework-starter.yaml and dev-mas-engineer.yaml so safety
    checks pass."""
    goose_recipes = tmp_path / "goose" / "recipes"
    goose_framework = tmp_path / "goose" / "_framework"
    goose_docs = tmp_path / "goose" / "docs"
    goose_config = tmp_path / "goose" / "config.yaml"
    tools_dir = goose_recipes / "mas-engineer-tools"
    for p in (goose_recipes, goose_framework, goose_docs, tools_dir):
        p.mkdir(parents=True, exist_ok=True)
    goose_config.write_text("version: 1.0.0\n")

    # Pre-populate framework so cmd_uninstall safety check passes
    (goose_recipes / "framework-starter.yaml").write_text("version: 1.0.0\n")
    (goose_recipes / "dev-mas-engineer.yaml").write_text("version: 1.0.0\n")
    goose_framework.mkdir(exist_ok=True)
    (goose_framework / "framework.yaml").write_text("version: 1.0.0\n")

    monkeypatch.setattr(mod, "GOOSE_RECIPES", goose_recipes)
    monkeypatch.setattr(mod, "GOOSE_FRAMEWORK_DIR", goose_framework)
    monkeypatch.setattr(mod, "GOOSE_DOCS", goose_docs)
    monkeypatch.setattr(mod, "GOOSE_CONFIG", goose_config)
    monkeypatch.setattr(mod, "TOOLS_DIR", tools_dir)
    monkeypatch.setattr(mod, "AGENT_REPO", goose_recipes)

    return {
        "tmp": tmp_path,
        "ws": tmp_path / "workspace",
        "goose_recipes": goose_recipes,
        "goose_framework": goose_framework,
        "goose_docs": goose_docs,
        "goose_config": goose_config,
    }


@pytest.fixture
def catch_exit(monkeypatch):
    """Catch sys.exit() calls and raise SystemExit instead."""
    def fake_exit(code=0):
        raise SystemExit(code)
    monkeypatch.setattr(mod.sys, "exit", fake_exit)


# ─── cmd_uninstall tests ────────────────────────────────────
class TestCmdUninstall:
    def test_refuses_when_mas_missing(self, ws_with_framework, catch_exit, monkeypatch):
        """Safety check: if dev-mas-engineer.yaml is missing, refuse."""
        (ws_with_framework["goose_recipes"] / "dev-mas-engineer.yaml").unlink()
        with pytest.raises(SystemExit) as exc:
            mod.cmd_uninstall()
        assert exc.value.code == 1

    def test_removes_top_level_yaml_except_mas(self, ws_with_framework, catch_exit):
        """Removes all top-level yamls except dev-mas-engineer.yaml."""
        recipes = ws_with_framework["goose_recipes"]
        (recipes / "extra-recipe.yaml").write_text("version: 1\n")
        n_before = len(list(recipes.glob("*.yaml")))
        mod.cmd_uninstall()
        remaining = list(recipes.glob("*.yaml"))
        # dev-mas-engineer.yaml must remain
        assert any(p.name == "dev-mas-engineer.yaml" for p in remaining)
        # extra-recipe.yaml must be gone
        assert not any(p.name == "extra-recipe.yaml" for p in remaining)
        assert len(remaining) == 1
        assert n_before == 3  # mas + framework-starter + extra

    def test_removes_recipes_framework_dir(self, ws_with_framework, catch_exit):
        """Removes GOOSE_RECIPES/_framework/ directory (sub-dir of recipes)."""
        recipes = ws_with_framework["goose_recipes"]
        # cmd_uninstall L572: fw_dir = GOOSE_RECIPES / "_framework"
        fw_dir = recipes / "_framework"
        fw_dir.mkdir(exist_ok=True)
        (fw_dir / "sub.yaml").write_text("v: 1\n")
        mod.cmd_uninstall()
        assert not fw_dir.exists()

    def test_removes_docs_except_mas(self, ws_with_framework, catch_exit):
        """Removes GOOSE_DOCS/* except mas-engineer/."""
        docs = ws_with_framework["goose_docs"]
        (docs / "mas-engineer").mkdir(exist_ok=True)
        (docs / "other-docs").mkdir()
        (docs / "extra.md").write_text("# extra")
        mod.cmd_uninstall()
        assert (docs / "mas-engineer").exists()
        assert not (docs / "other-docs").exists()
        assert not (docs / "extra.md").exists()


# ─── cmd_uninstall_mas tests ────────────────────────────────
class TestCmdUninstallMas:
    def test_refuses_when_framework_missing(self, ws_with_framework, catch_exit, monkeypatch):
        """Safety: if framework-starter.yaml or _framework/ missing, refuse."""
        (ws_with_framework["goose_recipes"] / "framework-starter.yaml").unlink()
        with pytest.raises(SystemExit) as exc:
            mod.cmd_uninstall_mas()
        assert exc.value.code == 1

    def test_removes_mas_files(self, ws_with_framework, catch_exit):
        """Removes dev-mas-engineer.yaml, mas-engineer-tools/, mas-engineer docs/."""
        recipes = ws_with_framework["goose_recipes"]
        docs = ws_with_framework["goose_docs"]
        (docs / "mas-engineer").mkdir()
        (docs / "mas-engineer" / "index.md").write_text("# MAS")
        # framework must remain
        (recipes / "framework-starter.yaml").write_text("v: 1\n")
        (recipes / "_framework").mkdir(exist_ok=True)
        (recipes / "_framework" / "fw.yaml").write_text("v: 1\n")

        mod.cmd_uninstall_mas()

        # MAS files gone
        assert not (recipes / "dev-mas-engineer.yaml").exists()
        assert not (recipes / "mas-engineer-tools").exists()
        assert not (docs / "mas-engineer").exists()
        # Framework remains
        assert (recipes / "framework-starter.yaml").exists()
        assert (recipes / "_framework" / "fw.yaml").exists()

    def test_removes_sub_agents(self, ws_with_framework, catch_exit):
        """Removes sub_mas-*.yaml from GOOSE_RECIPES."""
        recipes = ws_with_framework["goose_recipes"]
        # cmd_uninstall_mas requires framework-starter.yaml + _framework/ IN recipes/
        (recipes / "framework-starter.yaml").write_text("v: 1\n")
        (recipes / "_framework").mkdir(exist_ok=True)
        (recipes / "sub_mas-foo.yaml").write_text("v: 1\n")
        (recipes / "sub_mas-bar.yaml").write_text("v: 1\n")
        mod.cmd_uninstall_mas()
        assert not list(recipes.glob("sub_mas-*.yaml"))


# ─── cmd_init tests ─────────────────────────────────────────
class TestCmdInit:
    def test_creates_framework_dir(self, ws_with_framework, catch_exit, monkeypatch):
        """Creates ws/framework/{recipes,docs}/."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        # Pre-create sub dir so cmd_init_recovery doesn't fail (L95)
        (ws / "mas-engineer" / "recipe" / "sub").mkdir(parents=True, exist_ok=True)
        # cmd_init reads sys.argv[3] for dev_mode
        monkeypatch.setattr(mod.sys, "argv", ["dev_workspace", "--init", str(ws)])
        mod.cmd_init(str(ws))
        assert (ws / "framework" / "recipes").exists()
        assert (ws / "framework" / "docs").exists()

    def test_copies_framework_recipes(self, ws_with_framework, catch_exit, monkeypatch):
        """Copies top-level recipes from GOOSE_RECIPES to ws/framework/recipes/."""
        recipes = ws_with_framework["goose_recipes"]
        (recipes / "framework-starter.yaml").write_text("v: 1\n")
        (recipes / "extra.yaml").write_text("v: 1\n")
        ws = ws_with_framework["ws"]
        ws.mkdir()
        # Pre-create sub dir so cmd_init_recovery doesn't fail
        (ws / "mas-engineer" / "recipe" / "sub").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(mod.sys, "argv", ["dev_workspace", "--init", str(ws)])
        mod.cmd_init(str(ws))
        ws_recipes = list((ws / "framework" / "recipes").glob("*.yaml"))
        # framework-starter copied; dev-mas-engineer.yaml is in EXCLUDE_RECIPES → not copied
        assert any(p.name == "framework-starter.yaml" for p in ws_recipes)
        assert any(p.name == "extra.yaml" for p in ws_recipes)
        assert not any(p.name == "dev-mas-engineer.yaml" for p in ws_recipes)

    def test_dev_mode_copies_mas(self, ws_with_framework, catch_exit, monkeypatch):
        """With 'dev' arg, copies MAS-Engineer recipe + tools + docs."""
        recipes = ws_with_framework["goose_recipes"]
        docs = ws_with_framework["goose_docs"]
        # Pre-populate MAS in goose paths
        (recipes / "dev-mas-engineer.yaml").write_text("v: 1\n")
        mas_tools = recipes / "mas-engineer-tools"
        (mas_tools / "dev_x.py").write_text("# tool")
        (docs / "mas-engineer").mkdir()
        (docs / "mas-engineer" / "index.md").write_text("# MAS")

        ws = ws_with_framework["ws"]
        ws.mkdir()
        monkeypatch.setattr(mod.sys, "argv", ["dev_workspace", "--init", str(ws), "dev"])
        mod.cmd_init(str(ws))
        # MAS recipe + tools + docs copied
        assert (ws / "mas-engineer" / "recipe" / "dev-mas-engineer.yaml").exists()
        assert (ws / "mas-engineer" / "tools" / "dev_x.py").exists()
        assert (ws / "mas-engineer" / "docs" / "index.md").exists()


# ─── cmd_install tests ──────────────────────────────────────
class TestCmdInstall:
    def test_refuses_when_no_framework_recipes(self, ws_with_framework, catch_exit, monkeypatch):
        """Errors out if ws/framework/recipes/ doesn't exist."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        with pytest.raises(SystemExit) as exc:
            mod.cmd_install(str(ws))
        assert exc.value.code == 1

    def test_refuses_when_no_installr(self, ws_with_framework, catch_exit, monkeypatch):
        """Errors if install_framework.py missing in workspace."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        (ws / "framework" / "recipes").mkdir(parents=True)
        with pytest.raises(SystemExit) as exc:
            mod.cmd_install(str(ws))
        assert exc.value.code == 1

    def test_runs_install_framework_script(self, ws_with_framework, catch_exit, monkeypatch):
        """Calls subprocess.run with the install_framework.py script."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        (ws / "framework" / "recipes").mkdir(parents=True)
        installr = ws / "framework" / "python" / "install_framework.py"
        installr.parent.mkdir(parents=True)
        installr.write_text("# installer")

        # subprocess is imported inside cmd_install as `import subprocess`
        # Patch via sys.modules so the inner import resolves to our mock.
        import subprocess as real_subprocess
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        fake_module = MagicMock()
        fake_module.run = mock_run
        monkeypatch.setitem(sys.modules, "subprocess", fake_module)
        mod.cmd_install(str(ws))
        # Verify subprocess was called with the installr
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "install_framework.py" in str(call_args)


# ─── cmd_install_mas tests ──────────────────────────────────
class TestCmdInstallMas:
    def test_refuses_when_no_mas_recipe(self, ws_with_framework, catch_exit, monkeypatch):
        """Errors if ws/mas-engineer/recipe/dev-mas-engineer.yaml missing."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        with pytest.raises(SystemExit) as exc:
            mod.cmd_install_mas(str(ws))
        assert exc.value.code == 1

    def test_copies_mas_files(self, ws_with_framework, catch_exit, monkeypatch):
        """Copies MAS files from workspace to GOOSE_RECIPES + GOOSE_DOCS."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        (ws / "mas-engineer" / "recipe").mkdir(parents=True)
        (ws / "mas-engineer" / "recipe" / "dev-mas-engineer.yaml").write_text("v: 1\n")
        (ws / "mas-engineer" / "tools").mkdir()
        (ws / "mas-engineer" / "tools" / "dev_x.py").write_text("# tool")

        mod.cmd_install_mas(str(ws))
        recipes = ws_with_framework["goose_recipes"]
        assert (recipes / "dev-mas-engineer.yaml").exists()
        assert (recipes / "mas-engineer-tools" / "dev_x.py").exists()


# ─── cmd_rollback tests ─────────────────────────────────────
class TestCmdRollback:
    def test_refuses_when_no_git(self, ws_with_framework, catch_exit, monkeypatch):
        """Errors if no .git in workspace."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        with pytest.raises(SystemExit) as exc:
            mod.cmd_rollback(str(ws))
        assert exc.value.code == 1

    def test_runs_git_log(self, ws_with_framework, catch_exit, monkeypatch):
        """Calls git log with --oneline."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        (ws / ".git").mkdir()

        # subprocess is imported inside cmd_rollback as `import subprocess`
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stderr=""))
        fake_module = MagicMock()
        fake_module.run = mock_run
        monkeypatch.setitem(sys.modules, "subprocess", fake_module)
        # Bypass interactive input() call
        monkeypatch.setattr("builtins.input", lambda *a, **k: "")
        mod.cmd_rollback(str(ws))
        # First call: git log
        first_call = mock_run.call_args_list[0][0][0]
        assert "git" in first_call
        assert "log" in first_call
        assert "--oneline" in first_call


# ─── cmd_add_recipe tests ───────────────────────────────────
class TestCmdAddRecipe:
    def test_refuses_when_recipe_not_in_workspace(self, ws_with_framework, catch_exit, monkeypatch):
        """Errors if recipe not in ws/framework/recipes/."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        with pytest.raises(SystemExit) as exc:
            mod.cmd_add_recipe(str(ws), "missing.yaml")
        assert exc.value.code == 1

    def test_copies_recipe_to_goose_recipes(self, ws_with_framework, catch_exit, monkeypatch):
        """Copies recipe from ws/framework/recipes/ to GOOSE_RECIPES/."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        (ws / "framework" / "recipes").mkdir(parents=True)
        recipe_src = ws / "framework" / "recipes" / "test-recipe.yaml"
        recipe_src.write_text("title: Test\nversion: 1.0.0\n")

        mod.cmd_add_recipe(str(ws), "test-recipe.yaml")
        recipes = ws_with_framework["goose_recipes"]
        # Recipe copied to _framework/ (it's not a "kept" name)
        assert (recipes / "_framework" / "test-recipe.yaml").exists()

    def test_creates_backup_if_already_exists(self, ws_with_framework, catch_exit, monkeypatch):
        """If recipe already in GOOSE_RECIPES root, creates .bak-TIMESTAMP backup."""
        ws = ws_with_framework["ws"]
        ws.mkdir()
        (ws / "framework" / "recipes").mkdir(parents=True)
        recipe_src = ws / "framework" / "recipes" / "test-recipe.yaml"
        recipe_src.write_text("NEW: v2\n")
        # Pre-existing in GOOSE_RECIPES root (not _framework/) — see cmd_add_recipe L666
        recipes = ws_with_framework["goose_recipes"]
        (recipes / "test-recipe.yaml").write_text("OLD: v1\n")

        mod.cmd_add_recipe(str(ws), "test-recipe.yaml")
        # Backup should exist
        backups = list(recipes.glob("test-recipe.yaml.bak-*"))
        assert len(backups) == 1
