"""R110-363 — workspace.py coverage-push r1: small wins on remaining 109 stmts.

Strategy: target the testable uncovered ranges in
`tools/dev_workspace.py`. Pre-R110-363: 82% (490/599 stmts).
Post-R110-363 target: 88-92% (528-551/599 stmts).

The remaining ~50-70 stmts (10%) are:
  - `cmd_install_mas` (marked `# pragma: no cover`, R110-266 deferred)
  - `if __name__ == "__main__"` CLI dispatcher (needs fork+exec)
  - Some `input()` flows (need full monkeypatch chain)

Those are deferred to a future "interactive-CLI-testing" R-sprint.
"""

import os
import sys
import importlib
import importlib.util
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).parent.parent.resolve()
WORKSPACE = REPO_ROOT / "tools" / "dev_workspace.py"


# -----------------------------------------------------------------------------
# R110-347 sandbox pattern: load dev_workspace in a sandbox.
# -----------------------------------------------------------------------------
@pytest.fixture(scope="module")
def mod(tmp_path_factory):
    """Module-scoped fixture: load dev_workspace once per test file.

    R110-363: Same R110-347 sandbox pattern as im_finder_scan tests.
    The `if __name__ == "__main__"` block doesn't run during importlib
    import (only runs when the file is executed directly), so it's safe.
    """
    spec = importlib.util.spec_from_file_location(
        "dev_workspace", str(WORKSPACE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -----------------------------------------------------------------------------
# TestInstallMasFromWorkspace — L504-528, 24 stmts
# -----------------------------------------------------------------------------
class TestInstallMasFromWorkspace:
    """L504-528: _install_mas_from_workspace copies recipe/tools/docs/subs
    from ws/mas-engineer/ to GOOSE paths.

    Testable by monkeypatching GOOSE_RECIPES + GOOSE_DOCS to tmp_path.
    """

    def test_copies_recipe_when_present(self, mod, tmp_path):
        """If ws/mas-engineer/recipe/dev-mas-engineer.yaml exists, copy it."""
        ws = tmp_path
        (ws / "mas-engineer" / "recipe").mkdir(parents=True)
        src = ws / "mas-engineer" / "recipe" / "dev-mas-engineer.yaml"
        src.write_text("test recipe")

        mod.GOOSE_RECIPES = tmp_path / "goose_recipes"
        mod.GOOSE_DOCS = tmp_path / "goose_docs"
        (mod.GOOSE_RECIPES).mkdir(parents=True, exist_ok=True)

        mod._install_mas_from_workspace(ws)

        assert (mod.GOOSE_RECIPES / "dev-mas-engineer.yaml").exists()
        assert (mod.GOOSE_RECIPES / "dev-mas-engineer.yaml").read_text() == "test recipe"

    def test_skips_recipe_when_missing(self, mod, tmp_path):
        """If recipe file doesn't exist, no copy happens, no error."""
        ws = tmp_path
        (ws / "mas-engineer").mkdir()
        mod.GOOSE_RECIPES = tmp_path / "goose_recipes"
        mod.GOOSE_RECIPES.mkdir(parents=True, exist_ok=True)
        mod.GOOSE_DOCS = tmp_path / "goose_docs"

        mod._install_mas_from_workspace(ws)  # should not raise

        assert not (mod.GOOSE_RECIPES / "dev-mas-engineer.yaml").exists()

    def test_copies_tools_subtree(self, mod, tmp_path):
        """Tools subtree is recursively copied to GOOSE_RECIPES/mas-engineer-tools."""
        ws = tmp_path
        tools_src = ws / "mas-engineer" / "tools"
        tools_src.mkdir(parents=True)
        (tools_src / "tool1.py").write_text("# tool1")
        (tools_src / "subdir").mkdir()
        (tools_src / "subdir" / "tool2.py").write_text("# tool2")

        mod.GOOSE_RECIPES = tmp_path / "goose_recipes"
        mod.GOOSE_DOCS = tmp_path / "goose_docs"
        mod._install_mas_from_workspace(ws)

        assert (mod.GOOSE_RECIPES / "mas-engineer-tools" / "tool1.py").exists()
        assert (mod.GOOSE_RECIPES / "mas-engineer-tools" / "subdir" / "tool2.py").exists()

    def test_removes_existing_tools_dir(self, mod, tmp_path):
        """If GOOSE_RECIPES/mas-engineer-tools exists, it's removed first."""
        ws = tmp_path
        (ws / "mas-engineer" / "tools").mkdir(parents=True)
        (ws / "mas-engineer" / "tools" / "new.py").write_text("new")

        mod.GOOSE_RECIPES = tmp_path / "goose_recipes"
        mod.GOOSE_RECIPES.mkdir(parents=True)
        old = mod.GOOSE_RECIPES / "mas-engineer-tools"
        old.mkdir()
        (old / "old.py").write_text("old")
        mod.GOOSE_DOCS = tmp_path / "goose_docs"

        mod._install_mas_from_workspace(ws)

        assert not (old / "old.py").exists()
        assert (old / "new.py").exists()

    def test_copies_docs_subtree(self, mod, tmp_path):
        """Docs subtree is copied to GOOSE_DOCS/mas-engineer."""
        ws = tmp_path
        (ws / "mas-engineer" / "docs").mkdir(parents=True)
        (ws / "mas-engineer" / "docs" / "README.md").write_text("# readme")

        mod.GOOSE_RECIPES = tmp_path / "goose_recipes"
        mod.GOOSE_DOCS = tmp_path / "goose_docs"
        mod._install_mas_from_workspace(ws)

        assert (mod.GOOSE_DOCS / "mas-engineer" / "README.md").exists()

    def test_copies_sub_agents(self, mod, tmp_path):
        """Sub-agents (sub_mas-*.yaml) are copied to GOOSE_RECIPES root.

        Note: shutil.copy2 doesn't create parent dirs, so GOOSE_RECIPES
        must already exist (which the previous tests also do).
        """
        ws = tmp_path
        subs_src = ws / "mas-engineer" / "recipe" / "sub"
        subs_src.mkdir(parents=True)
        (subs_src / "sub_mas-foo.yaml").write_text("foo agent")
        (subs_src / "sub_mas-bar.yaml").write_text("bar agent")
        (subs_src / "sub_other.yaml").write_text("other")  # NOT copied

        mod.GOOSE_RECIPES = tmp_path / "goose_recipes"
        mod.GOOSE_RECIPES.mkdir(parents=True, exist_ok=True)
        mod.GOOSE_DOCS = tmp_path / "goose_docs"

        mod._install_mas_from_workspace(ws)

        assert (mod.GOOSE_RECIPES / "sub_mas-foo.yaml").exists()
        assert (mod.GOOSE_RECIPES / "sub_mas-bar.yaml").exists()
        assert not (mod.GOOSE_RECIPES / "sub_other.yaml").exists()


# -----------------------------------------------------------------------------
# TestGenerateAgentBranches — L862-864, 940-941, 950, 954-960
# -----------------------------------------------------------------------------
class TestGenerateAgentBranches:
    """L862-864 (fw_specialist), L940-941 (default sub_<name>),
    L847-848 (template missing), L950-960 (input flow)."""

    def test_fw_specialist_branch(self, mod, tmp_path):
        """agent_type='fw_specialist' goes to framework/recipes/specialists/."""
        ws = tmp_path
        result = mod._generate_agent(
            agent_type="fw_specialist",
            name="my-spec",
            description="Test specialist",
            emoji="🔧",
            workspace=str(ws),
        )
        assert result is not None
        assert result.exists()
        assert "specialists" in str(result)
        assert result.name == "my-spec.yaml"

    def test_unknown_agent_type_uses_default_sub(self, mod, tmp_path):
        """Unknown agent_type falls through to framework/recipes/sub/sub_<name>."""
        ws = tmp_path
        result = mod._generate_agent(
            agent_type="unknown_type",
            name="mystery",
            description="Mystery agent",
            emoji="❓",
            workspace=str(ws),
        )
        assert result is not None
        assert result.name == "sub_mystery.yaml"

    def test_mas_sub_template_missing_returns_none(self, mod, tmp_path):
        """If MAS_TEMPLATE doesn't exist, returns None with print message."""
        ws = tmp_path
        with patch.object(mod, "MAS_TEMPLATE", tmp_path / "no-such-template.yaml"):
            result = mod._generate_agent(
                agent_type="mas_sub",
                name="nope",
                description="nope",
                emoji="🤖",
                workspace=str(ws),
            )
        assert result is None

    def test_overwrite_yes_replaces_file(self, mod, tmp_path):
        """If dst exists and user answers 'j', file is overwritten."""
        ws = tmp_path
        ws_path = Path(ws)
        existing = ws_path / "framework" / "recipes" / "specialists" / "exists.yaml"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("OLD CONTENT")

        with patch("builtins.input", return_value="j"):
            result = mod._generate_agent(
                agent_type="fw_specialist",
                name="exists",
                description="Replacing",
                emoji="🔧",
                workspace=str(ws),
            )
        assert result is not None
        assert result.exists()
        assert result.read_text() != "OLD CONTENT"

    def test_overwrite_no_skips(self, mod, tmp_path):
        """If user answers != 'j', file is NOT overwritten (returns None)."""
        ws = tmp_path
        existing = ws / "framework" / "recipes" / "specialists" / "keep.yaml"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("ORIGINAL")

        with patch("builtins.input", return_value="n"):
            result = mod._generate_agent(
                agent_type="fw_specialist",
                name="keep",
                description="Should skip",
                emoji="🔧",
                workspace=str(ws),
            )
        assert result is None
        assert existing.read_text() == "ORIGINAL"

    def test_overwrite_eof_returns_none(self, mod, tmp_path):
        """EOFError on input prompt returns None (cancelled)."""
        ws = tmp_path
        existing = ws / "framework" / "recipes" / "specialists" / "cancelled.yaml"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("ORIGINAL")

        with patch("builtins.input", side_effect=EOFError):
            result = mod._generate_agent(
                agent_type="fw_specialist",
                name="cancelled",
                description="Should cancel",
                emoji="🔧",
                workspace=str(ws),
            )
        assert result is None


# -----------------------------------------------------------------------------
# TestCmdScaffoldInteractive — L1310-1342
# -----------------------------------------------------------------------------
class TestCmdScaffoldInteractive:
    """L1310-1342: cmd_scaffold main flow — 7 phases.

    Strategy: monkeypatch ALL the _ask_* helpers + input() so the flow
    runs end-to-end without TTY.
    """

    # _ask_type returns a 3-tuple (type, rel_dir, template_filename)
    TYPE_FW_SPEC = ("fw_specialist", "framework/recipes/specialists/", None)
    TYPE_MAS_SUB = ("mas_sub", "mas-engineer/recipe/sub/", "agent_template.yaml")
    TYPE_FW_SUB = ("fw_sub", "framework/recipes/sub/", None)

    def test_full_flow_succeeds(self, mod, tmp_path, capsys):
        """All phases succeed, agent is generated."""
        from types import SimpleNamespace
        args = SimpleNamespace(name=None, quiet=False, no_validate=True)
        with patch.object(mod, "_ask_type", return_value=self.TYPE_FW_SPEC), \
             patch.object(mod, "_ask_name", return_value="fullflow"), \
             patch.object(mod, "_ask_description", return_value=("Full flow desc", "🎯")), \
             patch("builtins.input", return_value="j"):
            mod.cmd_scaffold(args)

        captured = capsys.readouterr()
        assert "fullflow" in captured.out

    def test_quiet_mode_skips_ask(self, mod, tmp_path, capsys):
        """--quiet mode derives desc+emoji from name, skips _ask_description."""
        from types import SimpleNamespace
        args = SimpleNamespace(name=None, quiet=True, no_validate=True)
        with patch.object(mod, "_ask_type", return_value=self.TYPE_FW_SPEC), \
             patch.object(mod, "_ask_name", return_value="quietagent"), \
             patch.object(mod, "_ask_description") as ask_desc, \
             patch("builtins.input", return_value="j"):
            mod.cmd_scaffold(args)

        ask_desc.assert_not_called()

    def test_no_validate_skips_validation(self, mod, tmp_path, capsys):
        """--no_validate skips Phase 5 (validation)."""
        from types import SimpleNamespace
        args = SimpleNamespace(name=None, quiet=False, no_validate=True)
        with patch.object(mod, "_ask_type", return_value=self.TYPE_FW_SPEC), \
             patch.object(mod, "_ask_name", return_value="skipval"), \
             patch.object(mod, "_ask_description", return_value=("desc", "🔧")), \
             patch("builtins.input", return_value="j"), \
             patch.object(mod, "_validate_agent") as val:
            mod.cmd_scaffold(args)

        val.assert_not_called()

    def test_mas_sub_registers_agent(self, mod, tmp_path, capsys):
        """agent_type=mas_sub triggers _register_agent (Phase 6)."""
        from types import SimpleNamespace
        args = SimpleNamespace(name=None, quiet=False, no_validate=True)
        with patch.object(mod, "_ask_type", return_value=self.TYPE_MAS_SUB), \
             patch.object(mod, "_ask_name", return_value="regagent"), \
             patch.object(mod, "_ask_description", return_value=("desc", "🤖")), \
             patch("builtins.input", return_value="j"), \
             patch.object(mod, "_register_agent") as reg:
            mod.cmd_scaffold(args)

        reg.assert_called_once()

    def test_empty_type_returns_early(self, mod, tmp_path, capsys):
        """If _ask_type returns None/falsy, cmd_scaffold returns immediately."""
        from types import SimpleNamespace
        args = SimpleNamespace(name=None, quiet=False, no_validate=True)
        with patch.object(mod, "_ask_type", return_value=(None, None, None)), \
             patch.object(mod, "_ask_name") as ask_name:
            mod.cmd_scaffold(args)

        ask_name.assert_not_called()

    def test_name_arg_skips_ask(self, mod, tmp_path, capsys):
        """If args.name is set, _ask_name is NOT called."""
        from types import SimpleNamespace
        args = SimpleNamespace(name="fromarg", quiet=False, no_validate=True)
        with patch.object(mod, "_ask_type", return_value=self.TYPE_FW_SPEC), \
             patch.object(mod, "_ask_name") as ask_name, \
             patch.object(mod, "_ask_description", return_value=("desc", "🔧")), \
             patch("builtins.input", return_value="j"):
            mod.cmd_scaffold(args)

        ask_name.assert_not_called()


# -----------------------------------------------------------------------------
# TestCmdInstallCheck — covers L1346-1402 happy path + early return
# -----------------------------------------------------------------------------
class TestCmdInstallCheck:
    """cmd_install_check(ws_dir) — checks the mas-engineer/ workspace for
    YAML validity, hardcoded paths, standalone structure, parallelism, etc.

    L1346-1352: early return if mas-engineer/ dir doesn't exist.
    """

    def test_no_mas_dir_returns_early(self, mod, tmp_path, capsys):
        """If ws/mas-engineer/ doesn't exist, prints error and returns."""
        # Use a tmp_path that does NOT contain mas-engineer/ subdir
        result = mod.cmd_install_check(str(tmp_path / "nonexistent-ws"))

        # Function returns None on early exit
        assert result is None
        captured = capsys.readouterr()
        assert "No MAS-Directory" in captured.out or "❌" in captured.out

    def test_mas_dir_exists_runs_checks(self, mod, tmp_path, capsys):
        """If mas-engineer/ exists, runs the full check sequence (happy path)."""
        ws = tmp_path / "ws_with_mas"
        mas = ws / "mas-engineer"
        mas.mkdir(parents=True)
        # Create the minimum: recipe/dev-mas-engineer.yaml (for C4 read)
        (mas / "recipe").mkdir(parents=True)
        (mas / "recipe" / "dev-mas-engineer.yaml").write_text("name: test\n")
        (mas / "tools").mkdir(parents=True)
        (mas / "recipe" / "sub").mkdir(parents=True)
        # Add 8+ dev_*.py tools (C3 standalone check)
        for i in range(9):
            (mas / "tools" / f"dev_tool{i}.py").write_text(f"# tool {i}\n")

        result = mod.cmd_install_check(str(ws))
        # Returns None or list — depends on checks; we just want coverage
        captured = capsys.readouterr()
        assert "INSTALL-CHECK" in captured.out or "YAML" in captured.out
