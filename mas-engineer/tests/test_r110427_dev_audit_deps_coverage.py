"""R110-427 — coverage-push r6: tools/dev_audit_deps.py 0% → 100%.

Pure-stdlib dependency-scanner (99 lines). Walks a target dir,
parses Python imports, classifies into allowed/blocked/unknown,
prints a report, and optionally appends to a YAML whitelist.

Targets:
- scan_project: empty dir, single file w/ allowed imports, single file
  w/ blocked imports, single file w/ unknown imports, mixed, nested
  subdir, .git dir skipped, __pycache__ dir skipped, non-py file
  ignored, unreadable file (permission error → skip via bare except),
  import with dot-prefix (e.g. "from foo.bar import baz" → top-level
  is "foo"), `import x` line + `from x import` line both caught
- generate_report: empty findings, all-three-buckets populated,
  blocked section only prints when blocked non-empty, suggestions
  always (excludes blocked from unknown suggestions)
- main: no --target (exit 1), --target with findings, --apply
  creates/updates rules.yaml, --apply with no existing rules.yaml
  (skipped — reg_path doesn't exist), --apply with no suggestions
  (no-op)
- __main__ exec via in-process exec()
"""

import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_audit_deps as adep  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# scan_project
# ─────────────────────────────────────────────────────────────────────
class TestScanProject:
    def test_empty_dir(self, tmp_path):
        f = adep.scan_project(str(tmp_path))
        assert f["files"] == {}
        assert f["allowed"] == set()
        assert f["blocked"] == set()
        assert f["unknown"] == set()

    def test_allowed_imports(self, tmp_path):
        (tmp_path / "a.py").write_text("import json\nimport yaml\n")
        f = adep.scan_project(str(tmp_path))
        assert "json" in f["allowed"]
        assert "yaml" in f["allowed"]
        assert "a.py" in f["files"]

    def test_blocked_imports(self, tmp_path):
        (tmp_path / "b.py").write_text("import subprocess\nimport socket\n")
        f = adep.scan_project(str(tmp_path))
        assert "subprocess" in f["blocked"]
        assert "socket" in f["blocked"]

    def test_unknown_imports(self, tmp_path):
        (tmp_path / "c.py").write_text("import requests_custom\n")
        f = adep.scan_project(str(tmp_path))
        assert "requests_custom" in f["unknown"]

    def test_mixed(self, tmp_path):
        (tmp_path / "m.py").write_text(
            "import json\nimport subprocess\nimport totally_unknown\n"
        )
        f = adep.scan_project(str(tmp_path))
        assert "json" in f["allowed"]
        assert "subprocess" in f["blocked"]
        assert "totally_unknown" in f["unknown"]

    def test_from_import(self, tmp_path):
        (tmp_path / "f.py").write_text("from yaml import safe_load\n")
        f = adep.scan_project(str(tmp_path))
        assert "yaml" in f["allowed"]

    def test_dotted_import_top_module(self, tmp_path):
        # "from foo.bar import baz" → imp = "foo"
        (tmp_path / "d.py").write_text("from foo.bar import baz\n")
        f = adep.scan_project(str(tmp_path))
        assert "foo" in f["unknown"]

    def test_dotted_import_line(self, tmp_path):
        # "import foo.bar" → imp = "foo"
        (tmp_path / "i.py").write_text("import foo.bar\n")
        f = adep.scan_project(str(tmp_path))
        assert "foo" in f["unknown"]

    def test_subdir_recursion(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.py").write_text("import json\n")
        f = adep.scan_project(str(tmp_path))
        assert "json" in f["allowed"]
        # files dict contains relative path
        assert any("deep.py" in k for k in f["files"])

    def test_git_dir_skipped(self, tmp_path):
        git = tmp_path / ".git"
        git.mkdir()
        (git / "ignored.py").write_text("import subprocess\n")
        (tmp_path / "real.py").write_text("import json\n")
        f = adep.scan_project(str(tmp_path))
        assert "subprocess" not in f["blocked"]
        assert "json" in f["allowed"]

    def test_pycache_dir_skipped(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "ignored.py").write_text("import subprocess\n")
        (tmp_path / "real.py").write_text("import json\n")
        f = adep.scan_project(str(tmp_path))
        assert "subprocess" not in f["blocked"]

    def test_non_py_files_ignored(self, tmp_path):
        (tmp_path / "data.txt").write_text("import subprocess\n")
        (tmp_path / "real.py").write_text("import json\n")
        f = adep.scan_project(str(tmp_path))
        assert "subprocess" not in f["blocked"]
        assert "data.txt" not in f["files"]

    def test_unreadable_file_skipped(self, tmp_path, monkeypatch):
        # Force open() to raise OSError on this specific file
        bad = tmp_path / "bad.py"
        bad.write_text("import subprocess\n")
        real_open = open

        def fake_open(path, *a, **k):
            if str(path).endswith("bad.py"):
                raise OSError("permission denied")
            return real_open(path, *a, **k)

        monkeypatch.setattr("builtins.open", fake_open)
        # Also write a good file so we know scanning still works
        (tmp_path / "good.py").write_text("import json\n")
        f = adep.scan_project(str(tmp_path))
        assert "subprocess" not in f["blocked"]
        assert "json" in f["allowed"]

    def test_no_imports_in_file(self, tmp_path):
        (tmp_path / "noimp.py").write_text("# just a comment\nx = 1\n")
        f = adep.scan_project(str(tmp_path))
        # File with no imports not added to files dict
        assert "noimp.py" not in f["files"]


# ─────────────────────────────────────────────────────────────────────
# generate_report
# ─────────────────────────────────────────────────────────────────────
class TestGenerateReport:
    def test_empty_findings(self, capsys):
        findings = {"allowed": set(), "blocked": set(),
                    "unknown": set(), "files": {}}
        s = adep.generate_report(findings)
        out = capsys.readouterr().out
        assert "DEPENDENCY-AUDIT" in out
        assert "files gescannt: 0" in out
        assert s == []

    def test_all_buckets_populated(self, capsys):
        findings = {"allowed": {"json"}, "blocked": {"subprocess"},
                    "unknown": {"totally_unknown"}, "files": {"a.py": ["json"]}}
        s = adep.generate_report(findings)
        out = capsys.readouterr().out
        assert "json" in out
        assert "subprocess" in out
        assert "totally_unknown" in out
        assert "Blocked" in out  # the section header
        assert s == ["totally_unknown"]  # unknown suggestion excludes blocked

    def test_blocked_section_only_when_nonempty(self, capsys):
        findings = {"allowed": {"json"}, "blocked": set(),
                    "unknown": set(), "files": {"a.py": ["json"]}}
        adep.generate_report(findings)
        out = capsys.readouterr().out
        # No "Blocked" section when empty
        assert "Blocked (0)" not in out
        assert "Blocked (1)" not in out

    def test_suggestions_excludes_blocked(self, capsys):
        findings = {"allowed": set(),
                    "blocked": {"subprocess"},
                    "unknown": {"subprocess_lookalike"},
                    "files": {}}
        s = adep.generate_report(findings)
        # `subprocess` itself is in blocked — not in unknown so it
        # can't appear as suggestion. The `imp not in BLOCKED_IMPORTS`
        # guard inside generate_report is for defense-in-depth.
        assert "subprocess_lookalike" in s

    def test_unknown_includes_blocked_lookalike(self, capsys):
        # Force a name that's in BLOCKED_IMPORTS to land in unknown
        # by putting it through a hypothetical path (not natural via
        # scan_project, but the guard inside generate_report covers it)
        findings = {"allowed": set(),
                    "blocked": set(),
                    "unknown": {"subprocess"},  # already in BLOCKED_IMPORTS
                    "files": {}}
        s = adep.generate_report(findings)
        # The guard: `if imp not in BLOCKED_IMPORTS` filters it out
        assert "subprocess" not in s


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_target_exits_1(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_audit_deps.py"])
        with pytest.raises(SystemExit) as exc:
            adep.main()
        assert exc.value.code == 1

    def test_with_target_no_py_files(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(sys, "argv",
                            ["dev_audit_deps.py", "--target", str(tmp_path)])
        rc = adep.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "DEPENDENCY-AUDIT" in out

    def test_with_target_and_apply_no_rules_yaml(self, monkeypatch,
                                                   tmp_path, capsys):
        # Create a py file with unknown imports, --apply, but no
        # .mase/rules/rules.yaml exists → no-op (path doesn't exist)
        (tmp_path / "m.py").write_text("import totally_new\n")
        monkeypatch.setattr(sys, "argv",
                            ["dev_audit_deps.py", "--target",
                             str(tmp_path), "--apply"])
        adep.main()
        # No rules.yaml created
        assert not (tmp_path / ".mase" / "rules" / "rules.yaml").exists()

    def test_with_target_and_apply_existing_rules(self, monkeypatch,
                                                    tmp_path, capsys):
        # Create .mase/rules/rules.yaml with R09-GEN rule
        rules_dir = tmp_path / ".mase" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        rules_file = rules_dir / "rules.yaml"
        rules_file.write_text(
            "rules:\n"
            "  - id: R09-GEN\n"
            "    allow_imports: [existing_one]\n"
        )
        (tmp_path / "m.py").write_text("import totally_new\n")
        monkeypatch.setattr(sys, "argv",
                            ["dev_audit_deps.py", "--target",
                             str(tmp_path), "--apply"])
        adep.main()
        # rules.yaml updated
        content = rules_file.read_text()
        assert "totally_new" in content
        assert "existing_one" in content

    def test_with_target_and_apply_no_suggestions(self, monkeypatch,
                                                    tmp_path, capsys):
        # Only allowed imports → no suggestions → --apply no-op
        rules_dir = tmp_path / ".mase" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        rules_file = rules_dir / "rules.yaml"
        original = "rules:\n  - id: R09-GEN\n    allow_imports: [a]\n"
        rules_file.write_text(original)
        (tmp_path / "m.py").write_text("import json\n")
        monkeypatch.setattr(sys, "argv",
                            ["dev_audit_deps.py", "--target",
                             str(tmp_path), "--apply"])
        adep.main()
        # rules.yaml unchanged
        assert rules_file.read_text() == original

    def test_with_target_blocked_only(self, monkeypatch, tmp_path, capsys):
        # Blocked imports don't generate suggestions
        (tmp_path / "b.py").write_text("import subprocess\n")
        monkeypatch.setattr(sys, "argv",
                            ["dev_audit_deps.py", "--target", str(tmp_path)])
        adep.main()
        out = capsys.readouterr().out
        assert "subprocess" in out
        assert "Recommendation" not in out  # blocked not in suggestions

    def test_relative_target_resolved(self, monkeypatch, tmp_path, capsys):
        # --target with relative path → abspath resolves
        (tmp_path / "m.py").write_text("import json\n")
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            monkeypatch.setattr(sys, "argv",
                                ["dev_audit_deps.py", "--target", "."])
            adep.main()
        finally:
            os.chdir(cwd)
        out = capsys.readouterr().out
        assert str(tmp_path) in out


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_main_no_target(self, monkeypatch):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_audit_deps.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_audit_deps.py"]
            buf = io.StringIO()
            with redirect_stdout(buf):
                try:
                    exec(compile(script, "dev_audit_deps.py", "exec"),
                         {"__name__": "__main__",
                          "__file__": "dev_audit_deps.py"})
                except SystemExit as e:
                    assert e.code == 1
            assert "required" in buf.getvalue()
        finally:
            sys.argv = old_argv
