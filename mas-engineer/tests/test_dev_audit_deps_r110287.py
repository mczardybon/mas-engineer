"""Tests for mas-engineer/tools/dev_audit_deps.py — R110-287.

Coverage target: dev_audit_deps.py 50-69% → ~95%.

Tests:
- scan_project: empty dir, .py-only filter, .git/__pycache__ skip,
  import regex (top-level + from X import Y), blocked/allowed/unknown
  categorization, files dict structure, error in read skipped
- generate_report: prints header, allowed/blocked/unknown sections,
  whitelist suggestions, returns list
- main: --target required, scanning output, --apply modifies rules.yaml,
  --apply with no suggestions is a no-op
"""
import pytest
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_audit_deps as ad


class TestScanProject:
    def test_empty_dir_returns_empty_findings(self, tmp_path, capsys):
        # Empty project — but generate_report prints stuff, so test scan_project
        # directly first, then suppress generate_report
        findings = ad.scan_project(str(tmp_path))
        assert findings["files"] == {}
        assert findings["allowed"] == set()
        assert findings["blocked"] == set()
        assert findings["unknown"] == set()

    def test_python_files_only(self, tmp_path):
        (tmp_path / "a.py").write_text("import os\n")
        (tmp_path / "b.txt").write_text("import os\n")  # not a .py
        (tmp_path / "c.py").write_text("import json\n")
        findings = ad.scan_project(str(tmp_path))
        assert set(findings["files"].keys()) == {"a.py", "c.py"}
        assert "b.txt" not in findings["files"]

    def test_skips_git_and_pycache(self, tmp_path):
        (tmp_path / "top.py").write_text("import os\n")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "in_git.py").write_text("import os\n")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.py").write_text("import os\n")
        findings = ad.scan_project(str(tmp_path))
        assert "top.py" in findings["files"]
        # .git and __pycache__ are excluded by os.walk manipulation
        assert all("in_git" not in f and "cached" not in f
                   for f in findings["files"])

    def test_import_categorization(self, tmp_path):
        (tmp_path / "a.py").write_text("""
import json
import subprocess
import some_unknown_lib
import yaml
""")
        findings = ad.scan_project(str(tmp_path))
        # json + yaml are explicitly ALLOWED
        assert "json" in findings["allowed"]
        assert "yaml" in findings["allowed"]
        # subprocess is BLOCKED
        assert "subprocess" in findings["blocked"]
        # some_unknown_lib is in NEITHER set → unknown
        assert "some_unknown_lib" in findings["unknown"]

    def test_from_import_extraction(self, tmp_path):
        (tmp_path / "a.py").write_text("""
from yaml import safe_load
from pathlib import Path
from requests import get
""")
        findings = ad.scan_project(str(tmp_path))
        assert "yaml" in findings["allowed"]
        assert "pathlib" in findings["allowed"]
        assert "requests" in findings["blocked"]

    def test_dotted_imports_use_top_level(self, tmp_path):
        """`import yaml.safe_load` should record `yaml` (top-level only)."""
        (tmp_path / "a.py").write_text("import yaml.safe_load\nimport json.tool\n")
        findings = ad.scan_project(str(tmp_path))
        assert "yaml" in findings["allowed"]
        assert "json" in findings["allowed"]
        assert "safe" not in findings["allowed"]
        assert "tool" not in findings["allowed"]

    def test_files_dict_structure(self, tmp_path):
        # NOTE: scan_project's regex does not handle `import x, y` correctly
        # (a real-world parser-bug, outside R110-287 scope).
        # Use separate import lines so this test stays deterministic.
        (tmp_path / "a.py").write_text("import json\nimport yaml\n")
        findings = ad.scan_project(str(tmp_path))
        # a.py should be in files, value is list of imports
        assert "a.py" in findings["files"]
        assert set(findings["files"]["a.py"]) == {"json", "yaml"}

    def test_recursive_scan(self, tmp_path):
        sub = tmp_path / "sub" / "deeper"
        sub.mkdir(parents=True)
        (sub / "deep.py").write_text("import os\n")
        (tmp_path / "top.py").write_text("import json\n")
        findings = ad.scan_project(str(tmp_path))
        assert "top.py" in findings["files"]
        assert os.path.join("sub", "deeper", "deep.py") in findings["files"]

    def test_no_imports_means_no_entry(self, tmp_path):
        (tmp_path / "no_imports.py").write_text("x = 1\nprint('hi')\n")
        findings = ad.scan_project(str(tmp_path))
        # File has no imports → not in findings['files']
        assert "no_imports.py" not in findings["files"]

    def test_unreadable_file_skipped(self, tmp_path, monkeypatch):
        # Create a file then make open() fail for it
        (tmp_path / "a.py").write_text("import os\n")
        # Patch the open() inside scan_project to fail once
        import builtins
        real_open = builtins.open
        def mock_open(p, *a, **k):
            if "a.py" in str(p):
                raise IOError("permission denied")
            return real_open(p, *a, **k)
        monkeypatch.setattr("builtins.open", mock_open)
        findings = ad.scan_project(str(tmp_path))
        # The file that couldn't be read is skipped (no entry, no crash)
        assert "a.py" not in findings["files"]


class TestGenerateReport:
    def test_prints_header_and_summary(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import os\n")
        findings = ad.scan_project(str(tmp_path))
        ad.generate_report(findings)
        out = capsys.readouterr().out
        assert "DEPENDENCY-AUDIT REPORT" in out
        assert "files gescannt" in out
        assert "Einzigartige Imports" in out

    def test_prints_allowed_section(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import os\nimport json\n")
        findings = ad.scan_project(str(tmp_path))
        ad.generate_report(findings)
        out = capsys.readouterr().out
        assert "Erlaubt" in out
        assert "os" in out
        assert "json" in out

    def test_prints_blocked_section(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import subprocess\nimport requests\n")
        findings = ad.scan_project(str(tmp_path))
        ad.generate_report(findings)
        out = capsys.readouterr().out
        assert "Blocked" in out
        assert "subprocess" in out
        assert "requests" in out

    def test_prints_unknown_section(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import exotic_lib\n")
        findings = ad.scan_project(str(tmp_path))
        ad.generate_report(findings)
        out = capsys.readouterr().out
        assert "Unbekannt" in out
        assert "exotic_lib" in out

    def test_returns_suggestions_for_unknown(self, tmp_path):
        (tmp_path / "a.py").write_text("import exotic_lib\nimport another\n")
        findings = ad.scan_project(str(tmp_path))
        suggestions = ad.generate_report(findings)
        assert "exotic_lib" in suggestions
        assert "another" in suggestions

    def test_suggestions_exclude_blocked(self, tmp_path):
        (tmp_path / "a.py").write_text("import subprocess\nimport safe_lib\n")
        findings = ad.scan_project(str(tmp_path))
        suggestions = ad.generate_report(findings)
        # Only the unknown (safe_lib) — not the blocked (subprocess)
        assert suggestions == ["safe_lib"]

    def test_no_suggestions_when_all_allowed(self, tmp_path):
        (tmp_path / "a.py").write_text("import json\nimport yaml\n")
        findings = ad.scan_project(str(tmp_path))
        suggestions = ad.generate_report(findings)
        assert suggestions == []


class TestMain:
    def test_no_target_exits_with_error(self, capsys):
        # Don't provide --target
        with patch.object(sys, "argv", ["dev_audit_deps.py"]):
            with pytest.raises(SystemExit) as exc:
                ad.main()
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "--target" in out

    def test_scans_target(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import os\n")
        with patch.object(sys, "argv",
                          ["dev_audit_deps.py", "--target", str(tmp_path)]):
            ad.main()
        out = capsys.readouterr().out
        assert "Scanning" in out
        assert "Erlaubt" in out or "Unbekannt" in out

    def test_apply_modifies_existing_rules_yaml(self, tmp_path, capsys):
        # Create project with unknown import
        (tmp_path / "a.py").write_text("import my_custom_lib\n")
        # Pre-existing rules.yaml with R09-GEN rule
        rules_dir = tmp_path / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        rules_yaml = rules_dir / "rules.yaml"
        rules_yaml.write_text("""
rules:
  - id: R09-GEN
    description: Test
    allow_imports:
      - json
""")
        with patch.object(sys, "argv",
                          ["dev_audit_deps.py", "--target",
                           str(tmp_path), "--apply"]):
            ad.main()
        # Read the updated yaml
        import yaml
        with open(rules_yaml) as f:
            data = yaml.safe_load(f)
        rule = next(r for r in data["rules"] if r["id"] == "R09-GEN")
        assert "my_custom_lib" in rule["allow_imports"]
        assert "json" in rule["allow_imports"]  # existing preserved

    def test_apply_no_op_when_no_suggestions(self, tmp_path, capsys):
        # Only allowed imports → no suggestions → no yaml change
        (tmp_path / "a.py").write_text("import json\n")
        rules_dir = tmp_path / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        rules_yaml = rules_dir / "rules.yaml"
        original = "rules:\n  - id: R09-GEN\n    allow_imports: [json]\n"
        rules_yaml.write_text(original)
        with patch.object(sys, "argv",
                          ["dev_audit_deps.py", "--target",
                           str(tmp_path), "--apply"]):
            ad.main()
        # Unchanged
        assert rules_yaml.read_text() == original

    def test_apply_no_op_when_no_rules_file(self, tmp_path, capsys):
        # No .mase/rules/rules.yaml exists → --apply silently does nothing
        (tmp_path / "a.py").write_text("import my_lib\n")
        # No rules dir
        with patch.object(sys, "argv",
                          ["dev_audit_deps.py", "--target",
                           str(tmp_path), "--apply"]):
            ad.main()
        # Should not crash; should not create rules.yaml
        assert not (tmp_path / ".mase" / "rules" / "rules.yaml").exists()

    def test_target_path_resolved_to_absolute(self, tmp_path, capsys):
        # Use a relative path
        (tmp_path / "a.py").write_text("import os\n")
        rel = "."
        # cd into tmp_path
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch.object(sys, "argv",
                              ["dev_audit_deps.py", "--target", rel]):
                ad.main()
            out = capsys.readouterr().out
            # Should show the absolute path
            assert str(tmp_path) in out or os.path.abspath(rel) in out
        finally:
            os.chdir(old_cwd)
