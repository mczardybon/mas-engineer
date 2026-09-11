"""R110-430 — coverage-push r6: tools/dev_architecture_checker.py 0% → 100%.

Architecture-change detector (R15). Determines whether an action+file
combination is an architecture change requiring user approval.

Targets:
- ist_architektur_change: each of the 6 branches
  1. CREATE new sub_mas/dev_ (architecture), new .md (not),
     new .bak (not), new unknown type (architecture),
     'clone' action (architecture when sub_mas/dev_), 'new' fallback
  2. workflows.yaml edit/write/add/remove/delete
  3. master-constitution.yaml edit/write
  4. ARCHITEKTUR_DATEIEN match (each entry), any of the actions
  5. ALLOWED_PATTERNS match (each pattern), e.g. tools/dev_*.py
  6. dev-mas-engineer.yaml sub_recipes/add sub/remove sub
  - non-architecture fallback
- check_architecture: architektur_change=True (action=ABSEGNEN),
  architektur_change=False (action=OK)
- __main__ exec via in-process exec(): --action + --file
"""

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_architecture_checker as arc  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# ist_architektur_change — branch 1: CREATE/NEW/CLONE
# ─────────────────────────────────────────────────────────────────────
class TestBranch1Create:
    def test_create_sub_mas_arch(self):
        ok, reason = arc.ist_architektur_change("create",
                                                  "recipe/sub/sub_mas-foo.yaml")
        assert ok is True
        assert "agent/tool" in reason.lower() or "architecture" in reason.lower()

    def test_create_dev_tool_arch(self):
        ok, _ = arc.ist_architektur_change("create",
                                            "tools/dev_foo.py")
        assert ok is True

    def test_new_sub_mas_arch(self):
        ok, _ = arc.ist_architektur_change("new",
                                            "recipe/sub/sub_mas-foo.yaml")
        assert ok is True

    def test_new_agent_sub_mas_arch(self):
        # "new agent" contains "new" so triggers branch 1
        ok, _ = arc.ist_architektur_change("new agent",
                                            "recipe/sub/sub_mas-foo.yaml")
        assert ok is True

    def test_new_tool_arch(self):
        ok, _ = arc.ist_architektur_change("new tool",
                                            "tools/dev_foo.py")
        assert ok is True

    def test_clone_sub_mas_arch(self):
        ok, _ = arc.ist_architektur_change("clone",
                                            "recipe/sub/sub_mas-foo.yaml")
        assert ok is True

    def test_create_md_not_arch(self):
        # "new .md" file → branch 1 returns False
        ok, reason = arc.ist_architektur_change("create",
                                                  "docs/foo.md")
        assert ok is False
        assert reason == ""

    def test_create_changes_json_not_arch(self):
        ok, _ = arc.ist_architektur_change("create",
                                            ".mase/changes.json")
        assert ok is False

    def test_create_bak_not_arch(self):
        ok, _ = arc.ist_architektur_change("create",
                                            "some/file.bak")
        assert ok is False

    def test_create_unknown_type_arch(self):
        # New file, no sub_mas/dev_ in d, no .md/changes.json/.bak
        ok, reason = arc.ist_architektur_change("create",
                                                  "foo/bar.unknown")
        assert ok is True
        assert "unknown" in reason.lower()


# ─────────────────────────────────────────────────────────────────────
# ist_architektur_change — branch 2: workflows.yaml
# ─────────────────────────────────────────────────────────────────────
class TestBranch2Workflows:
    def test_workflows_edit(self):
        ok, reason = arc.ist_architektur_change("edit",
                                                  ".mase/workflows.yaml")
        assert ok is True
        assert "workflows.yaml" in reason

    def test_workflows_write(self):
        ok, _ = arc.ist_architektur_change("write",
                                            ".mase/workflows.yaml")
        assert ok is True

    def test_workflows_add(self):
        ok, _ = arc.ist_architektur_change("add",
                                            ".mase/workflows.yaml")
        assert ok is True

    def test_workflows_remove(self):
        ok, _ = arc.ist_architektur_change("remove",
                                            ".mase/workflows.yaml")
        assert ok is True

    def test_workflows_delete(self):
        ok, _ = arc.ist_architektur_change("delete",
                                            ".mase/workflows.yaml")
        assert ok is True

    def test_workflows_create_not_triggered(self):
        # "create" → branch 1 fires first, not branch 2
        # The d doesn't contain sub_mas/dev_ so → True unknown
        ok, reason = arc.ist_architektur_change("create",
                                                  ".mase/workflows.yaml")
        # branch 1: "create" in akt, d="...workflows.yaml"
        # sub_mas/dev_ not in d → falls through to "unknown type"
        # (workflows.yaml doesn't have .md, changes.json, .bak)
        assert ok is True


# ─────────────────────────────────────────────────────────────────────
# ist_architektur_change — branch 3: master-constitution.yaml
# ─────────────────────────────────────────────────────────────────────
class TestBranch3Constitution:
    def test_constitution_edit(self):
        ok, reason = arc.ist_architektur_change("edit",
                                                  "recipe/sub/sub_mas-master-constitution.yaml")
        assert ok is True
        assert "constitution" in reason

    def test_constitution_write(self):
        ok, _ = arc.ist_architektur_change("write",
                                            "recipe/sub/sub_mas-master-constitution.yaml")
        assert ok is True

    def test_constitution_create_branch1_fires(self):
        # "create" → branch 1 fires first; "sub_mas-" in d → True
        ok, reason = arc.ist_architektur_change("create",
                                                  "recipe/sub/sub_mas-master-constitution.yaml")
        assert ok is True
        # branch 1: "create" in akt, "sub_mas-" in d → True arch
        assert "agent/tool" in reason.lower() or "architecture" in reason.lower()


# ─────────────────────────────────────────────────────────────────────
# ist_architektur_change — branch 4: ARCHITEKTUR_DATEIEN
# ─────────────────────────────────────────────────────────────────────
class TestBranch4ArchFiles:
    def test_workflows_yaml(self):
        ok, _ = arc.ist_architektur_change("edit",
                                            ".mase/workflows.yaml")
        assert ok is True

    def test_registry_yaml(self):
        ok, reason = arc.ist_architektur_change("edit",
                                                  ".mase/domains/registry.yaml")
        assert ok is True
        assert "registry.yaml" in reason

    def test_dev_mas_engineer_yaml(self):
        # Branch 6 fires for sub_recipes actions on dev-mas-engineer.yaml
        # Branch 4 for "edit"/"write"/"delete"/"add" actions
        ok, reason = arc.ist_architektur_change("edit",
                                                  "recipe/dev-mas-engineer.yaml")
        assert ok is True

    def test_sub_mas_master_constitution_yaml(self):
        ok, _ = arc.ist_architektur_change("delete",
                                            "recipe/sub/sub_mas-master-constitution.yaml")
        assert ok is True

    def test_agent_template_yaml(self):
        ok, reason = arc.ist_architektur_change("add",
                                                  "recipe/template/agent_template.yaml")
        assert ok is True
        assert "agent_template.yaml" in reason

    def test_arch_file_create_branch1_fires(self):
        # "create" → branch 1 fires; d contains ".yaml" but
        # .yaml doesn't match .md/changes.json/.bak
        # → True unknown type
        ok, _ = arc.ist_architektur_change("create",
                                            "recipe/template/agent_template.yaml")
        assert ok is True


# ─────────────────────────────────────────────────────────────────────
# ist_architektur_change — branch 5: ALLOWED_PATTERNS
# ─────────────────────────────────────────────────────────────────────
class TestBranch5Allowed:
    def test_sub_mas_yaml_edit(self):
        # Sub-agent edit pattern → NOT architecture
        ok, reason = arc.ist_architektur_change("edit",
                                                  "recipe/sub/sub_mas-foo.yaml")
        assert ok is False
        assert reason == ""

    def test_dev_tool_py_edit(self):
        ok, _ = arc.ist_architektur_change("edit",
                                            "tools/dev_foo.py")
        assert ok is False

    def test_knowledge_md(self):
        ok, _ = arc.ist_architektur_change("write",
                                            ".mase/knowledge/some.md")
        assert ok is False

    def test_changes_json(self):
        ok, _ = arc.ist_architektur_change("add",
                                            ".mase/changes.json")
        assert ok is False

    def test_docs_md(self):
        ok, _ = arc.ist_architektur_change("edit",
                                            "docs/foo.md")
        assert ok is False

    def test_user_info(self):
        ok, _ = arc.ist_architektur_change("write",
                                            "user_info/x.json")
        assert ok is False

    def test_backups(self):
        ok, _ = arc.ist_architektur_change("delete",
                                            ".backups/foo.bak")
        assert ok is False

    def test_checkpoints(self):
        ok, _ = arc.ist_architektur_change("add",
                                            ".mase/checkpoints/x.json")
        assert ok is False


# ─────────────────────────────────────────────────────────────────────
# ist_architektur_change — branch 6: sub_recipes-list
# ─────────────────────────────────────────────────────────────────────
class TestBranch6SubRecipes:
    def test_sub_recipes_action(self):
        ok, reason = arc.ist_architektur_change("sub_recipes",
                                                  "recipe/dev-mas-engineer.yaml")
        assert ok is True
        assert "sub_recipes" in reason

    def test_add_sub_action(self):
        ok, _ = arc.ist_architektur_change("add sub",
                                            "recipe/dev-mas-engineer.yaml")
        assert ok is True

    def test_remove_sub_action(self):
        ok, _ = arc.ist_architektur_change("remove sub",
                                            "recipe/dev-mas-engineer.yaml")
        assert ok is True

    def test_sub_recipes_other_file_not_arch(self):
        # "sub_recipes" action but on a non-dev-mas-engineer file
        # → branch 5 might match if it's a sub_mas yaml edit
        ok, _ = arc.ist_architektur_change("sub_recipes",
                                            "recipe/sub/sub_mas-foo.yaml")
        assert ok is False


# ─────────────────────────────────────────────────────────────────────
# ist_architektur_change — non-architecture fallback
# ─────────────────────────────────────────────────────────────────────
class TestNonArchitecture:
    def test_boring_edit(self):
        ok, reason = arc.ist_architektur_change("edit", "x/y.txt")
        assert ok is False
        assert reason == ""

    def test_empty_action_and_file(self):
        ok, _ = arc.ist_architektur_change("", "")
        assert ok is False

    def test_file_with_substring_workflows_but_not_match(self):
        # d="xworkflows.yaml" still contains "workflows.yaml"
        # → branch 2 fires
        ok, _ = arc.ist_architektur_change("edit", "xworkflows.yaml")
        assert ok is True


# ─────────────────────────────────────────────────────────────────────
# check_architecture
# ─────────────────────────────────────────────────────────────────────
class TestCheckArchitecture:
    def test_arch_true(self):
        r = arc.check_architecture("edit", ".mase/workflows.yaml")
        assert r["architektur_change"] is True
        assert r["action"] == "ABSEGNEN"
        assert r["grund"]  # non-empty
        assert "user must approve" in r["detail"].lower()

    def test_arch_false(self):
        r = arc.check_architecture("edit", "tools/dev_foo.py")
        assert r["architektur_change"] is False
        assert r["action"] == "OK"
        assert r["grund"] == ""
        assert r["detail"] == "No architecture change"


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_arch_true(self, monkeypatch):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_architecture_checker.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_architecture_checker.py",
                        "--action", "edit",
                        "--file", ".mase/workflows.yaml"]
            buf = io.StringIO()
            with redirect_stdout(buf):
                try:
                    exec(compile(script, "dev_architecture_checker.py",
                                 "exec"),
                         {"__name__": "__main__",
                          "__file__": "dev_architecture_checker.py"})
                except SystemExit as e:
                    assert e.code == 1
            out = buf.getvalue()
            r = json.loads(out)
            assert r["architektur_change"] is True
        finally:
            sys.argv = old_argv

    def test_exec_arch_false(self, monkeypatch):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_architecture_checker.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_architecture_checker.py",
                        "--action", "edit",
                        "--file", "tools/dev_foo.py"]
            buf = io.StringIO()
            with redirect_stdout(buf):
                try:
                    exec(compile(script, "dev_architecture_checker.py",
                                 "exec"),
                         {"__name__": "__main__",
                          "__file__": "dev_architecture_checker.py"})
                except SystemExit as e:
                    assert e.code == 0
            out = buf.getvalue()
            r = json.loads(out)
            assert r["architektur_change"] is False
        finally:
            sys.argv = old_argv
