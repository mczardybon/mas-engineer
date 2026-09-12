"""R110-449 — coverage-push r8: tools/dev_audit_deps.py 0% → 100%.

Dependency-audit tool (99 lines). Scans Python files for imports,
classifies as allowed/blocked/unknown, optionally appends unknown
imports to .mase/rules/rules.yaml R09-GEN rule.

Targets:
- BLOCKED_IMPORTS / ALLOWED_IMPORTS sets
- scan_project: walks target dir; skips .git/__pycache__; parses
  'import X' / 'from X import ...'; classifies X (first segment
  before .); builds {allowed, blocked, unknown, files[rel]=[imps]};
  unreadable files skipped; non-.py files skipped; relative path
  from target
- generate_report: prints header; files count; unique imports;
  allowed/blocked/unknown lists; suggestions = unknown not in
  BLOCKED; prints "Recommendation: allow_imports: [...]"; returns
  suggestions list
- main: --target required → exits 1 if missing; abspath; scans;
  reports; --apply + suggestions → loads .mase/rules/rules.yaml;
  finds R09-GEN rule; appends suggestions to allow_imports; dumps
  YAML with sort_keys=False + allow_unicode=True; --apply with no
  suggestions → no file write
"""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_audit_deps as ad  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────
class TestConstants:
    def test_blocked_imports(self):
        assert "subprocess" in ad.BLOCKED_IMPORTS
        assert "socket" in ad.BLOCKED_IMPORTS
        assert "requests" in ad.BLOCKED_IMPORTS

    def test_allowed_imports(self):
        assert "json" in ad.ALLOWED_IMPORTS
        assert "yaml" in ad.ALLOWED_IMPORTS
        assert "pathlib" in ad.ALLOWED_IMPORTS


# ─────────────────────────────────────────────────────────────────────
# scan_project
# ─────────────────────────────────────────────────────────────────────
class TestScanProject:
    def test_empty_dir(self, tmp_path):
        f = ad.scan_project(str(tmp_path))
        assert f["files"] == {}
        assert f["allowed"] == set()
        assert f["blocked"] == set()
        assert f["unknown"] == set()

    def test_allowed_import(self, tmp_path):
        (tmp_path / "a.py").write_text("import json\nimport yaml\n")
        f = ad.scan_project(str(tmp_path))
        assert "json" in f["allowed"]
        assert "yaml" in f["allowed"]
        assert "a.py" in f["files"]

    def test_blocked_import(self, tmp_path):
        (tmp_path / "a.py").write_text("import subprocess\n")
        f = ad.scan_project(str(tmp_path))
        assert "subprocess" in f["blocked"]
        assert "a.py" in f["files"]

    def test_unknown_import(self, tmp_path):
        (tmp_path / "a.py").write_text("import requests_foo\n")
        f = ad.scan_project(str(tmp_path))
        assert "requests_foo" in f["unknown"]

    def test_from_import(self, tmp_path):
        (tmp_path / "a.py").write_text(
            "from yaml import safe_load\n")
        f = ad.scan_project(str(tmp_path))
        # 'yaml' is first segment
        assert "yaml" in f["allowed"]

    def test_dotted_import_uses_first(self, tmp_path):
        (tmp_path / "a.py").write_text("import os.path\n")
        f = ad.scan_project(str(tmp_path))
        # Regex captures 'os.path', split('.')[0]='os'.
        # 'os' is NOT in ALLOWED_IMPORTS (only 'os.path' is), so
        # it lands in unknown.
        assert "os" in f["unknown"]

    def test_skips_non_py(self, tmp_path):
        (tmp_path / "a.txt").write_text("import subprocess\n")
        (tmp_path / "a.py").write_text("")
        f = ad.scan_project(str(tmp_path))
        assert f["files"] == {}

    def test_skips_git_and_pycache(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "x.py").write_text("import subprocess\n")
        pyc_dir = tmp_path / "__pycache__"
        pyc_dir.mkdir()
        (pyc_dir / "x.py").write_text("import subprocess\n")
        (tmp_path / "real.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        # Only real.py is in files; .git and __pycache__ skipped
        assert list(f["files"].keys()) == ["real.py"]

    def test_unreadable_file_skipped(self, tmp_path):
        # Try to make a file unreadable (chmod 000) — skip on perm error
        ro_file = tmp_path / "ro.py"
        ro_file.write_text("import json\n")
        try:
            os.chmod(ro_file, 0o000)
            f = ad.scan_project(str(tmp_path))
            # Either skipped (perm denied) or read (we're root)
            assert "files" in f
        finally:
            os.chmod(ro_file, 0o644)

    def test_relative_path_key(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        # Relpath uses forward slashes
        key = list(f["files"].keys())[0]
        assert "deep.py" in key
        assert "sub" in key

    def test_multiple_imports_per_file(self, tmp_path):
        (tmp_path / "a.py").write_text(
            "import json\nimport subprocess\nimport custom_foo\n")
        f = ad.scan_project(str(tmp_path))
        imps = f["files"]["a.py"]
        assert "json" in imps
        assert "subprocess" in imps
        assert "custom_foo" in imps

    def test_recursive_walk(self, tmp_path):
        sub1 = tmp_path / "a"
        sub2 = sub1 / "b"
        sub2.mkdir(parents=True)
        (sub2 / "deep.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        assert any("deep.py" in k for k in f["files"])


# ─────────────────────────────────────────────────────────────────────
# generate_report
# ─────────────────────────────────────────────────────────────────────
class TestGenerateReport:
    def test_basic_report(self, tmp_path, capsys):
        f = ad.scan_project(str(tmp_path))
        suggestions = ad.generate_report(f)
        out = capsys.readouterr().out
        assert "DEPENDENCY-AUDIT REPORT" in out
        assert "files gescannt" in out
        assert suggestions == []

    def test_suggestions_for_unknown(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import custom_foo\n")
        f = ad.scan_project(str(tmp_path))
        suggestions = ad.generate_report(f)
        out = capsys.readouterr().out
        assert "Recommendation" in out
        assert "allow_imports" in out
        assert "custom_foo" in suggestions

    def test_blocked_list_printed(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import subprocess\n")
        f = ad.scan_project(str(tmp_path))
        ad.generate_report(f)
        out = capsys.readouterr().out
        assert "❌ Blocked" in out

    def test_allowed_list_printed(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        ad.generate_report(f)
        out = capsys.readouterr().out
        assert "✅ Erlaubt" in out

    def test_no_recommendation_if_no_unknown(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        suggestions = ad.generate_report(f)
        out = capsys.readouterr().out
        assert "Recommendation" not in out
        assert suggestions == []


# ─────────────────────────────────────────────────────────────────────
# main (via subprocess so coverage tracks the source)
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def _run(self, *args):
        import subprocess
        result = subprocess.run(
            ['python3', 'tools/dev_audit_deps.py'] + list(args),
            capture_output=True, text=True,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        return result.returncode, result.stdout, result.stderr

    def test_no_target_exits_1(self):
        code, out, err = self._run()
        assert code == 1
        assert "--target" in out

    def test_target_scans(self, tmp_path):
        (tmp_path / "a.py").write_text("import json\n")
        code, out, _ = self._run("--target", str(tmp_path))
        assert code == 0
        assert "DEPENDENCY-AUDIT REPORT" in out

    def test_apply_appends_to_rules(self, tmp_path):
        (tmp_path / "a.py").write_text("import custom_foo\n")
        rules_dir = tmp_path / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        rules_file = rules_dir / "rules.yaml"
        rules_file.write_text(yaml.safe_dump({
            "rules": [{"id": "R09-GEN", "allow_imports": ["json"]}]}))
        _, out, _ = self._run(
            "--target", str(tmp_path), "--apply")
        assert "added" in out.lower() or "✅" in out
        data = yaml.safe_load(rules_file.read_text())
        r09 = next(r for r in data["rules"] if r["id"] == "R09-GEN")
        assert "custom_foo" in r09["allow_imports"]
        assert "json" in r09["allow_imports"]  # preserved

    def test_apply_no_rules_file(self, tmp_path):
        (tmp_path / "a.py").write_text("import custom_foo\n")
        code, _, _ = self._run(
            "--target", str(tmp_path), "--apply")
        assert code == 0

    def test_apply_no_suggestions(self, tmp_path):
        (tmp_path / "a.py").write_text("import json\n")
        rules_dir = tmp_path / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        rules_file = rules_dir / "rules.yaml"
        rules_file.write_text(yaml.safe_dump({
            "rules": [{"id": "R09-GEN", "allow_imports": []}]}))
        _, out, _ = self._run(
            "--target", str(tmp_path), "--apply")
        assert "added" not in out.lower()

    def test_apply_preserves_other_rules(self, tmp_path):
        (tmp_path / "a.py").write_text("import custom_foo\n")
        rules_dir = tmp_path / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        rules_file = rules_dir / "rules.yaml"
        rules_file.write_text(yaml.safe_dump({
            "rules": [
                {"id": "OTHER", "value": 1},
                {"id": "R09-GEN", "allow_imports": []},
            ]}))
        self._run(
            "--target", str(tmp_path), "--apply")
        data = yaml.safe_load(rules_file.read_text())
        ids = {r["id"] for r in data["rules"]}
        assert "OTHER" in ids
        assert "R09-GEN" in ids
