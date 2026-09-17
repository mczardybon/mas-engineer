"""
test_r110261_tools_coverage_round2.py — R110-261 Coverage Sprint, Round 2.

Covers 4 more simple tools (target: 6/10 done after this file):
  3. dev_architecture_checker  — R15 architecture-change detector
  4. dev_audit_deps            — Generic-project import-blocklist scanner
  5. dev_auto_project          — Framework auto-detector (recipe/prefix/mode)
  6. dev_editor_large          — Line-based file editor for large files

Each test class targets the library functions directly. CLI entry points
(one-line `if __name__ == "__main__": main()`) are out of scope; what
matters is library coverage.

Run with:
    python3 -m pytest tests/test_r110261_tools_coverage_round2.py -v
"""
import json
import os
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO_ROOT))


# ─── Tool 3: dev_architecture_checker.py ─────────────────────────────
class TestDevArchitectureChecker:
    """Tests for tools/dev_architecture_checker.py — ist_architektur_change()."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import dev_architecture_checker as mod
        self.mod = mod

    def test_architecture_files_constant(self):
        """The architecture file list contains the 5 expected SOT paths."""
        archs = self.mod.ARCHITEKTUR_DATEIEN
        assert ".mase/workflows.yaml" in archs
        assert "recipe/dev-mas-engineer.yaml" in archs
        assert any("master-constitution" in a for a in archs)
        assert any("agent_template" in a for a in archs)

    def test_allowed_patterns_constant(self):
        """Allowed patterns (NOT architecture) include sub_/tools/docs."""
        pats = self.mod.ALLOWED_PATTERNS
        assert any("sub_mas" in p for p in pats)
        assert any("dev_" in p for p in pats)
        assert any("docs" in p for p in pats)

    def test_new_sub_agent_is_architecture(self):
        """Creating a new sub_mas-*.yaml IS architecture."""
        is_arch, reason = self.mod.ist_architektur_change(
            "create new sub-agent", "recipe/sub/sub_mas-foo.yaml"
        )
        assert is_arch is True
        assert "architecture" in reason.lower()

    def test_new_tool_is_architecture(self):
        """Creating a new dev_*.py tool IS architecture."""
        is_arch, reason = self.mod.ist_architektur_change(
            "create new tool", "tools/dev_foo.py"
        )
        assert is_arch is True
        assert "architecture" in reason.lower()

    def test_new_md_file_is_not_architecture(self):
        """Creating a new .md file is NOT architecture."""
        is_arch, reason = self.mod.ist_architektur_change(
            "create new doc", "docs/R110-261-foo.md"
        )
        assert is_arch is False
        assert reason == ""

    def test_edit_sub_agent_is_not_architecture(self):
        """Editing an existing sub_mas-*.yaml is allowed (not architecture)."""
        is_arch, reason = self.mod.ist_architektur_change(
            "edit", "recipe/sub/sub_mas-foo.yaml"
        )
        assert is_arch is False

    def test_edit_workflows_is_architecture(self):
        """Editing .mase/workflows.yaml IS architecture."""
        is_arch, reason = self.mod.ist_architektur_change(
            "edit", ".mase/workflows.yaml"
        )
        assert is_arch is True
        assert "workflow" in reason.lower() or "architecture" in reason.lower()

    def test_edit_constitution_is_architecture(self):
        """Editing master-constitution IS architecture."""
        is_arch, reason = self.mod.ist_architektur_change(
            "edit", "recipe/sub/sub_mas-master-constitution.yaml"
        )
        assert is_arch is True

    def test_empty_inputs_no_crash(self):
        """Empty action + file returns gracefully."""
        is_arch, reason = self.mod.ist_architektur_change("", "")
        assert isinstance(is_arch, bool)
        assert isinstance(reason, str)


# ─── Tool 4: dev_audit_deps.py ────────────────────────────────────────
class TestDevAuditDeps:
    """Tests for tools/dev_audit_deps.py — scan_project() + report."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import dev_audit_deps as mod
        self.mod = mod

    def test_constants(self):
        """Blocklist + allowlist contain expected names."""
        assert "subprocess" in self.mod.BLOCKED_IMPORTS
        assert "socket" in self.mod.BLOCKED_IMPORTS
        assert "json" in self.mod.ALLOWED_IMPORTS
        assert "yaml" in self.mod.ALLOWED_IMPORTS
        assert "re" in self.mod.ALLOWED_IMPORTS

    def test_scan_clean_project(self, tmp_path):
        """A project with only allowed imports → blocked=∅, unknown=∅."""
        (tmp_path / "clean.py").write_text("import json\nimport re\nfrom pathlib import Path\n")
        findings = self.mod.scan_project(str(tmp_path))
        assert "json" in findings["allowed"]
        assert "re" in findings["allowed"]
        assert "pathlib" in findings["allowed"]
        assert findings["blocked"] == set()
        assert findings["unknown"] == set()
        assert "clean.py" in findings["files"]

    def test_scan_blocked_imports(self, tmp_path):
        """A project importing subprocess → appears in 'blocked' set."""
        (tmp_path / "bad.py").write_text("import subprocess\nimport json\n")
        findings = self.mod.scan_project(str(tmp_path))
        assert "subprocess" in findings["blocked"]
        assert "json" in findings["allowed"]
        assert "subprocess" in findings["files"]["bad.py"]

    def test_scan_skips_git_and_pycache(self, tmp_path):
        """Files under .git/ and __pycache__/ are ignored."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "x.py").write_text("import subprocess")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "y.py").write_text("import socket")
        (tmp_path / "ok.py").write_text("import json\n")
        findings = self.mod.scan_project(str(tmp_path))
        # No .git or __pycache__ files should be recorded
        assert ".git/x.py" not in findings["files"]
        assert "__pycache__/y.py" not in findings["files"]
        assert "ok.py" in findings["files"]

    def test_scan_handles_malformed_files(self, tmp_path):
        """Files with weird imports (e.g. relative) don't crash the scanner."""
        (tmp_path / "weird.py").write_text("from . import foo\nimport bar.baz.qux\n")
        findings = self.mod.scan_project(str(tmp_path))
        # bar is the top-level package, should be 'unknown'
        assert "bar" in findings["unknown"]

    def test_generate_report_runs(self, capsys, tmp_path):
        """generate_report() prints a report; exit 0 even on empty project."""
        findings = {"allowed": set(), "blocked": set(), "unknown": set(), "files": {}}
        # Should not raise
        self.mod.generate_report(findings)
        captured = capsys.readouterr()
        assert "DEPENDENCY-AUDIT" in captured.out or "files gescannt" in captured.out


# ─── Tool 5: dev_auto_project.py ──────────────────────────────────────
class TestDevAutoProject:
    """Tests for tools/dev_auto_project.py — detect() framework auto-detect."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import dev_auto_project as mod
        self.mod = mod

    def test_detect_mas_mode_marker(self, tmp_path):
        """If .mas-mode is present, mode is read from it."""
        (tmp_path / ".mas-mode").write_text("mas")
        result = self.mod.detect(str(tmp_path))
        assert result["mode"] == "mas"
        assert result["project_path"] == str(tmp_path.resolve()) or \
               result["project_path"] == os.path.realpath(str(tmp_path)) or \
               result["project_path"].endswith(tmp_path.name)

    def test_detect_mode_framework_marker(self, tmp_path):
        """.mas-mode='framework' → mode='framework'."""
        (tmp_path / ".mas-mode").write_text("framework")
        result = self.mod.detect(str(tmp_path))
        assert result["mode"] == "framework"

    def test_detect_no_marker_defaults_to_generic(self, tmp_path):
        """No .mas-mode → default 'generic'."""
        result = self.mod.detect(str(tmp_path))
        assert result["mode"] == "generic"

    def test_detect_invalid_mode_falls_back_to_generic(self, tmp_path):
        """.mas-mode with unknown value falls back to 'generic' (no exception)."""
        (tmp_path / ".mas-mode").write_text("garbage_mode_xyz")
        result = self.mod.detect(str(tmp_path))
        assert result["mode"] == "generic"

    def test_detect_finds_recipes_dir(self, tmp_path):
        """A recipes/ dir with non-sub_*.yaml is detected as the main recipe."""
        (tmp_path / "recipes").mkdir()
        (tmp_path / "recipes" / "my_recipe.yaml").write_text("name: x\n")
        (tmp_path / "recipes" / "sub_helper.yaml").write_text("name: y\n")
        result = self.mod.detect(str(tmp_path))
        assert result["main_recipe"] == "my_recipe.yaml"
        assert result["prefix"] == "ag-"

    def test_detect_skips_sub_recipes(self, tmp_path):
        """If only sub_*.yaml exists in recipes/, main_recipe stays None."""
        (tmp_path / "recipes").mkdir()
        (tmp_path / "recipes" / "sub_helper.yaml").write_text("name: y\n")
        result = self.mod.detect(str(tmp_path))
        assert result["main_recipe"] is None

    def test_detect_has_tests_and_docs(self, tmp_path):
        """has_tests/has_docs reflect directory presence."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        result = self.mod.detect(str(tmp_path))
        assert result["has_tests"] is True
        assert result["has_docs"] is True

    def test_detect_no_tests_no_docs(self, tmp_path):
        """has_tests/has_docs are False when dirs don't exist."""
        result = self.mod.detect(str(tmp_path))
        assert result["has_tests"] is False
        assert result["has_docs"] is False

    def test_detect_real_mas_engineer_repo(self):
        """Sanity: detect() on the real mas-engineer repo returns sensible fields."""
        result = self.mod.detect(str(REPO_ROOT))
        # REPO_ROOT itself doesn't have a .mas-mode (the inner mas-engineer/ does)
        assert result["mode"] in ("mas", "framework", "generic")
        assert result["has_tests"] is True
        assert result["has_docs"] is True


# ─── Tool 6: dev_editor_large.py ──────────────────────────────────────
class TestDevEditorLarge:
    """Tests for tools/dev_editor_large.py — line-based file editor."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import dev_editor_large as mod
        self.mod = mod

    def _make_file(self, tmp_path, n_lines=10):
        """Helper: create a file with n lines 'Line 1', 'Line 2', ..."""
        f = tmp_path / "file.txt"
        f.write_text("\n".join(f"Line {i}" for i in range(1, n_lines + 1)) + "\n")
        return str(f)

    def test_edit_between_lines_basic(self, tmp_path):
        """Replace lines 3..5 with new text → file shrinks by 2 lines net."""
        f = self._make_file(tmp_path, n_lines=10)
        result = self.mod.edit_between_lines(f, 3, 5, "REPLACED")
        assert result["ok"] is True
        assert result["alte_lines"] == 3
        assert result["neue_lines"] == 1
        content = Path(f).read_text()
        assert "REPLACED" in content
        assert "Line 3" not in content
        assert "Line 5" not in content
        # Line 1, 2 still there
        assert "Line 1" in content
        assert "Line 2" in content
        # Line 6+ still there
        assert "Line 6" in content

    def test_edit_between_lines_file_not_found(self, tmp_path):
        """Missing file returns error dict, doesn't crash."""
        f = str(tmp_path / "nonexistent.txt")
        result = self.mod.edit_between_lines(f, 1, 1, "x")
        assert "error" in result
        assert "not found" in result["error"]

    def test_edit_between_lines_out_of_range(self, tmp_path):
        """start..end outside the file returns error."""
        f = self._make_file(tmp_path, n_lines=3)
        result = self.mod.edit_between_lines(f, 1, 999, "x")
        assert "error" in result
        assert "outside" in result["error"]

    def test_edit_between_lines_strips_trailing_newline(self, tmp_path):
        """Replacement text's trailing newline is normalized."""
        f = self._make_file(tmp_path, n_lines=3)
        self.mod.edit_between_lines(f, 1, 1, "REPLACED\n\n\n")
        content = Path(f).read_text()
        # Should have exactly one trailing newline on the replacement line
        assert "REPLACED\n" in content
        assert "REPLACED\n\n\n" not in content

    def test_find_line_finds_match(self, tmp_path):
        """find_line returns 1-based line number of first match."""
        f = self._make_file(tmp_path, n_lines=5)
        line_no = self.mod.find_line(f, r"^Line 3$")
        assert line_no == 3

    def test_find_line_no_match(self, tmp_path):
        """find_line returns None when no line matches."""
        f = self._make_file(tmp_path, n_lines=5)
        line_no = self.mod.find_line(f, r"NONEXISTENT_PATTERN_XYZ")
        assert line_no is None

    def test_insert_after(self, tmp_path):
        """insert_after adds a new line after the given position."""
        f = self._make_file(tmp_path, n_lines=3)
        result = self.mod.insert_after(f, 2, "INSERTED")
        assert result["ok"] is True
        content = Path(f).read_text()
        lines = content.splitlines()
        # INSERTED should be the 3rd line (after Line 2)
        assert lines[2] == "INSERTED"
        assert lines[1] == "Line 2"
        assert lines[3] == "Line 3"

    def test_insert_after_out_of_range(self, tmp_path):
        """insert_after with invalid line returns error."""
        f = self._make_file(tmp_path, n_lines=3)
        result = self.mod.insert_after(f, 999, "x")
        assert "error" in result
        assert "outside" in result["error"]
