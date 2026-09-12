"""R110-475 — coverage-push r12: tools/dev_architecture_checker.py 76% → 100%

Pure-function module (no I/O, no module-level side effects).
33 stmts, 8 missed in coverage-push r11 baseline:
  - L51: 'unknown type new file' branch
  - L66-67: ARCHITEKTUR_DATEIEN protected branch
  - L76: sub_recipes-list change branch
  - L83-93: check_architecture return-dict branches

KEY OBSERVATIONS:
- All functions are PURE: no I/O, no globals read, no env vars.
  Tests need zero monkeypatching or fixtures.
- ist_architektur_change uses BOTH action and file as input.
  Action keywords are matched in LOWER-CASE form (line 40:
  akt = action.lower()). File is also lowercased.
- Return shape: (bool, str) for ist_architektur_change,
  dict for check_architecture.
- "create" branch has 3 sub-branches:
  1. sub_mas- / dev_ in file → architecture (new agent/tool)
  2. .md / changes.json / .bak in file → NOT architecture
  3. else → architecture (unknown type)
- L66-67 triggers when:
  - file contains any ARCHITEKTUR_DATEIEN substring
  - AND action contains edit/write/delete/add
- L76 triggers when:
  - file contains 'dev-mas-engineer.yaml'
  - AND action contains sub_recipes / add sub / remove sub
- L83-93 (check_architecture) is just dict wrapping;
  each key tested via the helper.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_architecture_checker as ac  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# ist_architektur_change — pure function
# ─────────────────────────────────────────────────────────────────────
class TestIstArchitekturChange:
    # --- Branch 1: NEW file create ---
    def test_create_sub_agent(self):
        ist, grund = ac.ist_architektur_change("create", "recipe/sub/sub_mas-foo.yaml")
        assert ist is True
        assert "New agent/tool" in grund

    def test_create_dev_tool(self):
        ist, grund = ac.ist_architektur_change("create new", "tools/dev_x.py")
        assert ist is True
        assert "agent/tool" in grund

    def test_create_sub_mas_substring(self):
        # "new agent" with sub_mas- in file → still architecture
        ist, grund = ac.ist_architektur_change("new agent", "recipe/sub/sub_mas-x.yaml")
        assert ist is True

    def test_create_dev_in_path(self):
        ist, grund = ac.ist_architektur_change("clone", "tools/dev_y.py")
        assert ist is True

    def test_create_md_file_no_arch(self):
        # .md files in create branch → NOT architecture
        ist, grund = ac.ist_architektur_change("create", "docs/foo.md")
        assert ist is False
        assert grund == ""

    def test_create_changes_json_no_arch(self):
        ist, grund = ac.ist_architektur_change("create", ".mase/changes.json")
        assert ist is False
        assert grund == ""

    def test_create_bak_file_no_arch(self):
        ist, grund = ac.ist_architektur_change("create", "backup.bak")
        assert ist is False
        assert grund == ""

    def test_create_unknown_type_arch(self):
        # create + no .md/changes.json/.bak + no sub_mas-/dev_
        # → unknown type → architecture
        ist, grund = ac.ist_architektur_change("create", "random_file.xyz")
        assert ist is True
        assert "unknown" in grund.lower()

    def test_create_unknown_type_python(self):
        ist, grund = ac.ist_architektur_change("new", "src/main.py")
        assert ist is True
        assert "unknown" in grund.lower()

    # --- Branch 2: workflows.yaml change ---
    def test_workflows_yaml_edit(self):
        ist, grund = ac.ist_architektur_change("edit", ".mase/workflows.yaml")
        assert ist is True
        assert "workflows.yaml" in grund

    def test_workflows_yaml_write(self):
        ist, grund = ac.ist_architektur_change("write", "workflows.yaml")
        assert ist is True

    def test_workflows_yaml_add(self):
        ist, grund = ac.ist_architektur_change("add task", ".mase/workflows.yaml")
        assert ist is True

    def test_workflows_yaml_remove(self):
        ist, grund = ac.ist_architektur_change("remove section", "workflows.yaml")
        assert ist is True

    def test_workflows_yaml_delete(self):
        ist, grund = ac.ist_architektur_change("delete entry", "workflows.yaml")
        assert ist is True

    def test_workflows_yaml_create_not_sot(self):
        # "create" triggers branch 1 (create/new/clone keyword).
        # .mase/workflows.yaml doesn't match sub_mas-/dev_
        # nor .md/changes.json/.bak → unknown type → architecture.
        ist, grund = ac.ist_architektur_change("create", ".mase/workflows.yaml")
        assert ist is True
        assert "unknown" in grund.lower()

    # --- Branch 3: master-constitution.yaml ---
    def test_constitution_edit(self):
        ist, grund = ac.ist_architektur_change("edit", "recipe/sub/sub_mas-master-constitution.yaml")
        assert ist is True
        assert "constitution" in grund.lower()

    def test_constitution_write(self):
        ist, grund = ac.ist_architektur_change("write", "master-constitution.yaml")
        assert ist is True

    def test_constitution_delete_not_trigger(self):
        # branch 3 only checks edit/write — delete falls through
        ist, grund = ac.ist_architektur_change("delete", "master-constitution.yaml")
        # No branch matched → allowed check → .yaml is in sub_mas- pattern? no
        # sub_mas-master-constitution.yaml matches ALLOWED_PATTERNS:
        # r"recipe/sub/sub_mas-\w+\.yaml$" → NOT architecture
        assert ist is False

    # --- Branch 4: ARCHITEKTUR_DATEIEN protected ---
    def test_architektur_dateien_edit(self):
        ist, grund = ac.ist_architektur_change("edit", ".mase/domains/registry.yaml")
        assert ist is True
        assert "protected" in grund.lower()

    def test_architektur_dateien_write(self):
        ist, grund = ac.ist_architektur_change("write", "recipe/template/agent_template.yaml")
        assert ist is True

    def test_architektur_dateien_delete(self):
        ist, grund = ac.ist_architektur_change("delete", "recipe/dev-mas-engineer.yaml")
        assert ist is True

    def test_architektur_dateien_add(self):
        ist, grund = ac.ist_architektur_change("add entry", ".mase/workflows.yaml")
        assert ist is True

    def test_architektur_dateien_create_not_trigger(self):
        # "create" triggers branch 1 first (create keyword matches).
        # agent_template.yaml has no sub_mas-/dev_ and no .md/changes.json/.bak
        # → unknown type → architecture.
        ist, grund = ac.ist_architektur_change("create", "recipe/template/agent_template.yaml")
        assert ist is True
        assert "unknown" in grund.lower()

    # --- Branch 5: ALLOWED_PATTERNS ---
    def test_allowed_sub_agent_edit(self):
        ist, grund = ac.ist_architektur_change("edit", "recipe/sub/sub_mas-other.yaml")
        # Branch 1 doesn't trigger (no create/new/clone)
        # Branch 2 doesn't trigger (file doesn't contain workflows.yaml)
        # Branch 3 doesn't trigger (no master-constitution)
        # Branch 4 doesn't trigger (file not in ARCHITEKTUR_DATEIEN)
        # Branch 5: matches sub_mas-\w+\.yaml → NOT architecture
        assert ist is False
        assert grund == ""

    def test_allowed_tool_edit(self):
        ist, grund = ac.ist_architektur_change("edit", "tools/dev_z.py")
        assert ist is False

    def test_allowed_knowledge_md(self):
        ist, grund = ac.ist_architektur_change("edit", ".mase/knowledge/foo.md")
        assert ist is False

    def test_allowed_changes_json(self):
        ist, grund = ac.ist_architektur_change("write", ".mase/changes.json")
        assert ist is False

    def test_allowed_docs(self):
        ist, grund = ac.ist_architektur_change("edit", "docs/readme.md")
        assert ist is False

    def test_allowed_user_info(self):
        ist, grund = ac.ist_architektur_change("edit", "user_info/profile.yaml")
        assert ist is False

    def test_allowed_backups(self):
        ist, grund = ac.ist_architektur_change("delete", ".backups/foo.bak")
        assert ist is False

    def test_allowed_checkpoints(self):
        ist, grund = ac.ist_architektur_change("write", ".mase/checkpoints/x.json")
        assert ist is False

    # --- Branch 6: sub_recipes-list ---
    def test_sub_recipes_change(self):
        ist, grund = ac.ist_architektur_change("sub_recipes", "recipe/dev-mas-engineer.yaml")
        assert ist is True
        assert "sub_recipes" in grund.lower() or "agent architecture" in grund.lower()

    def test_add_sub(self):
        ist, grund = ac.ist_architektur_change("add sub", "recipe/dev-mas-engineer.yaml")
        assert ist is True

    def test_remove_sub(self):
        ist, grund = ac.ist_architektur_change("remove sub", "recipe/dev-mas-engineer.yaml")
        assert ist is True

    def test_sub_recipes_in_other_file(self):
        # sub_recipes keyword but not in dev-mas-engineer.yaml
        ist, grund = ac.ist_architektur_change("sub_recipes", "recipe/other.yaml")
        # branch 6 requires "dev-mas-engineer.yaml" in file
        # file doesn't match → falls through → no match → False
        # ALLOWED doesn't match "recipe/other.yaml"
        assert ist is False

    # --- Branch 7: default return (no match) ---
    def test_no_match_returns_false(self):
        ist, grund = ac.ist_architektur_change("view", "any/file.txt")
        assert ist is False
        assert grund == ""

    def test_empty_action_empty_file(self):
        ist, grund = ac.ist_architektur_change("", "")
        assert ist is False

    def test_action_lowercased(self):
        # "CREATE" should be lowercased to "create" → triggers branch 1
        ist, grund = ac.ist_architektur_change("CREATE", "tools/dev_x.py")
        assert ist is True

    def test_file_lowercased(self):
        ist, grund = ac.ist_architektur_change("edit", "WORKFLOWS.YAML")
        # file.lower() → "workflows.yaml" → triggers branch 2
        assert ist is True


# ─────────────────────────────────────────────────────────────────────
# check_architecture — dict wrapper
# ─────────────────────────────────────────────────────────────────────
class TestCheckArchitecture:
    def test_architecture_returns_absegnen(self):
        result = ac.check_architecture("create", "tools/dev_x.py")
        assert result["architektur_change"] is True
        assert result["grund"] != ""
        assert result["action"] == "ABSEGNEN"
        assert "Architecture change detected" in result["detail"]
        assert "User must approve" in result["detail"]

    def test_no_architecture_returns_ok(self):
        result = ac.check_architecture("edit", "tools/dev_y.py")
        assert result["architektur_change"] is False
        assert result["grund"] == ""
        assert result["action"] == "OK"
        assert result["detail"] == "No architecture change"

    def test_dict_has_all_keys(self):
        for action, file in [
            ("create", "tools/dev_x.py"),
            ("edit", "tools/dev_y.py"),
            ("view", "any.txt"),
        ]:
            r = ac.check_architecture(action, file)
            for k in ("architektur_change", "grund", "action", "detail"):
                assert k in r


# ─────────────────────────────────────────────────────────────────────
# CLI __main__ — smoke tests via runpy
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_main_no_arch_returns_0(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", [
            "dev_architecture_checker.py", "--action", "edit", "--file", "tools/dev_x.py"
        ])
        import runpy
        exit_code = 0
        try:
            runpy.run_path("tools/dev_architecture_checker.py", run_name="__main__")
        except SystemExit as e:
            exit_code = e.code
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["architektur_change"] is False
        assert exit_code == 0

    def test_main_arch_returns_1(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", [
            "dev_architecture_checker.py", "--action", "create", "--file", "tools/dev_x.py"
        ])
        import runpy
        exit_code = 0
        try:
            runpy.run_path("tools/dev_architecture_checker.py", run_name="__main__")
        except SystemExit as e:
            exit_code = e.code
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["architektur_change"] is True
        assert exit_code == 1

    def test_main_no_args(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_architecture_checker.py"])
        import runpy
        try:
            runpy.run_path("tools/dev_architecture_checker.py", run_name="__main__")
        except SystemExit:
            pass
        out = capsys.readouterr().out
        # Empty defaults → no architecture → JSON with False
        parsed = json.loads(out)
        assert parsed["architektur_change"] is False
