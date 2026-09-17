"""Tests for mas-engineer/tools/dev_architecture_checker.py — R110-289.

Coverage target: dev_architecture_checker.py 50% → ~95% (114 lines,
2 funcs + CLI). This is R15 — the architecture-change detector. It
returns ABSEGNEN for changes that affect MAS architecture, OK otherwise.
Any regression would silently allow architecture-level changes without
user approval → R01 confirmation bypass.
"""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_architecture_checker as ac


# ─── ist_architektur_change ───────────────────────────────────────

class TestIstArchitekturChange:
    # --- CREATE / NEW cases ---

    def test_new_sub_agent_creation_is_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "CREATE", "recipe/sub/sub_mas-foo.yaml")
        assert ist is True
        assert "New agent" in grund or "architecture" in grund.lower()

    def test_new_tool_creation_is_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "CREATE", "mas-engineer/tools/dev_foo.py")
        assert ist is True
        assert "agent" in grund.lower() or "tool" in grund.lower()

    def test_create_markdown_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "CREATE", "docs/notes.md")
        assert ist is False
        assert grund == ""

    def test_create_changes_json_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "CREATE", ".mase/changes.json")
        assert ist is False

    def test_create_bak_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "CREATE", "something.bak")
        assert ist is False

    def test_create_unknown_file_type_is_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "CREATE", "random_file.xyz")
        assert ist is True
        # Falls into "unknown type" branch
        assert "unknown" in grund.lower() or "check" in grund.lower()

    def test_new_keyword_also_architecture(self):
        # "new" alone is treated as CREATE
        ist, grund = ac.ist_architektur_change(
            "new agent", "recipe/sub/sub_mas-bar.yaml")
        assert ist is True

    def test_clone_keyword_is_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "clone", "recipe/sub/sub_mas-baz.yaml")
        assert ist is True

    # --- SOT workflows.yaml change ---

    def test_workflows_yaml_edit_is_architecture(self):
        for verb in ["edit", "write", "add", "remove", "delete"]:
            ist, grund = ac.ist_architektur_change(
                verb, ".mase/workflows.yaml")
            assert ist is True, f"verb={verb}"
            assert "workflows.yaml" in grund

    def test_workflows_yaml_read_not_architecture(self):
        ist, grund = ac.ist_architektur_change("read", ".mase/workflows.yaml")
        assert ist is False

    # --- Constitution change ---

    def test_constitution_edit_is_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "edit", "recipe/sub/sub_mas-master-constitution.yaml")
        assert ist is True
        assert "constitution" in grund.lower()

    def test_constitution_write_is_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "write", "recipe/sub/sub_mas-master-constitution.yaml")
        assert ist is True

    def test_constitution_read_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "read", "recipe/sub/sub_mas-master-constitution.yaml")
        assert ist is False

    # --- Protected architecture files ---

    def test_architecture_file_edit_blocked(self):
        for arch_file in [
            ".mase/domains/registry.yaml",
            "recipe/dev-mas-engineer.yaml",
            "recipe/template/agent_template.yaml",
        ]:
            ist, grund = ac.ist_architektur_change("edit", arch_file)
            assert ist is True, f"file={arch_file}"
            assert arch_file in grund or "protected" in grund.lower()

    def test_architecture_file_delete_blocked(self):
        ist, grund = ac.ist_architektur_change(
            "delete", "recipe/dev-mas-engineer.yaml")
        assert ist is True

    def test_architecture_file_add_blocked(self):
        ist, grund = ac.ist_architektur_change(
            "add", ".mase/domains/registry.yaml")
        assert ist is True

    # --- Allowed patterns (NOT architecture) ---

    def test_sub_agent_edit_not_architecture(self):
        # ALLOWED_PATTERNS: recipe/sub/sub_mas-*.yaml$
        ist, grund = ac.ist_architektur_change(
            "edit", "recipe/sub/sub_mas-foo.yaml")
        assert ist is False

    def test_tool_edit_not_architecture(self):
        # ALLOWED_PATTERNS: tools/dev_*.py$
        ist, grund = ac.ist_architektur_change(
            "edit", "mas-engineer/tools/dev_foo.py")
        assert ist is False

    def test_knowledge_md_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "edit", ".mase/knowledge/conventions.md")
        assert ist is False

    def test_changes_json_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "write", ".mase/changes.json")
        assert ist is False

    def test_docs_md_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "write", "docs/README.md")
        assert ist is False

    def test_user_info_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "edit", "user_info/profile.json")
        assert ist is False

    def test_backups_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "write", ".backups/something.yaml")
        assert ist is False

    def test_checkpoints_not_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "write", ".mase/checkpoints/cp-2026.yaml")
        assert ist is False

    # --- dev-mas-engineer.yaml sub_recipes-list change ---

    def test_dev_mas_sub_recipes_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "sub_recipes", "recipe/dev-mas-engineer.yaml")
        assert ist is True
        assert "sub_recipes" in grund

    def test_dev_mas_add_sub_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "add sub", "recipe/dev-mas-engineer.yaml")
        assert ist is True

    def test_dev_mas_remove_sub_architecture(self):
        ist, grund = ac.ist_architektur_change(
            "remove sub", "recipe/dev-mas-engineer.yaml")
        assert ist is True

    def test_dev_mas_other_action_not_architecture(self):
        # Reading a dev-mas-engineer.yaml is fine (not in the action list)
        ist, grund = ac.ist_architektur_change(
            "read", "recipe/dev-mas-engineer.yaml")
        assert ist is False

    # --- Defaults / edge cases ---

    def test_empty_action_and_file_not_architecture(self):
        ist, grund = ac.ist_architektur_change("", "")
        assert ist is False

    def test_only_file_no_action(self):
        # File matches allowed pattern → not architecture
        ist, grund = ac.ist_architektur_change("", "docs/foo.md")
        assert ist is False

    def test_case_insensitive_action(self):
        # Action is lowercased, so uppercase CREATE also works
        ist, grund = ac.ist_architektur_change("CREATE", "sub_mas-x.yaml")
        assert ist is True

    def test_case_insensitive_file(self):
        # File is lowercased too
        ist, grund = ac.ist_architektur_change("edit", "WORKFLOWS.YAML")
        assert ist is True


# ─── check_architecture ───────────────────────────────────────────

class TestCheckArchitecture:
    def test_architecture_change_returns_absegnen(self):
        result = ac.check_architecture("CREATE", "recipe/sub/sub_mas-x.yaml")
        assert result["architektur_change"] is True
        assert result["action"] == "ABSEGNEN"
        assert result["grund"]  # non-empty
        assert "approve" in result["detail"].lower() or \
               "user" in result["detail"].lower()

    def test_no_architecture_change_returns_ok(self):
        result = ac.check_architecture("edit", "docs/notes.md")
        assert result["architektur_change"] is False
        assert result["action"] == "OK"
        assert result["grund"] == ""
        assert "no architecture" in result["detail"].lower()

    def test_result_is_dict_with_required_keys(self):
        result = ac.check_architecture("edit", "x.md")
        for key in ["architektur_change", "grund", "action", "detail"]:
            assert key in result


SCRIPT = Path(__file__).resolve().parent.parent / "tools" / \
    "dev_architecture_checker.py"


# ─── CLI / __main__ ────────────────────────────────────────────────

class TestCLI:
    def test_cli_no_architecture_change_exits_0(self, capsys):
        with patch.object(sys, "argv",
                          ["dev_architecture_checker.py",
                           "--action", "edit", "--file", "docs/notes.md"]):
            with pytest.raises(SystemExit) as exc:
                import runpy
                runpy.run_path(str(SCRIPT), run_name="__main__")
        assert exc.value.code == 0
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["architektur_change"] is False

    def test_cli_architecture_change_exits_1(self, capsys):
        with patch.object(sys, "argv",
                          ["dev_architecture_checker.py",
                           "--action", "CREATE",
                           "--file", "recipe/sub/sub_mas-x.yaml"]):
            import runpy
            with pytest.raises(SystemExit) as exc:
                runpy.run_path(str(SCRIPT), run_name="__main__")
        assert exc.value.code == 1
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["architektur_change"] is True
        assert result["action"] == "ABSEGNEN"

    def test_cli_defaults_to_empty(self, capsys):
        # No args → action="", file=""
        with patch.object(sys, "argv", ["dev_architecture_checker.py"]):
            import runpy
            with pytest.raises(SystemExit) as exc:
                runpy.run_path(str(SCRIPT), run_name="__main__")
        # Empty → not architecture → exit 0
        assert exc.value.code == 0
