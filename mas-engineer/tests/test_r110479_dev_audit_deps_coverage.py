"""R110-479 — coverage-push r16: tools/dev_audit_deps.py 58% to 100%

99 lines, 73 stmts. Currently 96% with 3 lines missed:
  L24: except: continue (bare except for unreadable file)
  L35: findings["blocked"].add(imp)
  L51: '  ❌ Blocked (...)' print (only when blocked list non-empty)

KEY OBSERVATIONS:
- BLOCKED_IMPORTS: subprocess, shutil, socket, requests, urllib,
  multiprocessing, threading, ctypes, signal
- ALLOWED_IMPORTS: json, yaml, datetime, os.path, typeing (typo!),
  re, math, pathlib, collections, functools, itertools, enum
- scan_project:
  - os.walk target; skips .git, __pycache__
  - only .py files
  - relpath from target
  - bare except for unreadable
  - regex: r'^import (\\S+)|^from (\\S+) import'
  - dotted imports → use top-level (split('.')[0])
  - per-file import set → 'files' dict {rel: [list]}
  - each imp: blocked → blocked, allowed → allowed, else → unknown
- generate_report:
  - prints header + summary (3 lines)
  - allowed list always
  - blocked list ONLY if non-empty (L51 — gated by `if findings['blocked']:`)
  - unknown list always
  - returns suggestions = unknown (excluding blocked, but blocked
    are already in separate bucket — actually it's: unknown AND not
    in BLOCKED_IMPORTS, so practically just = unknown)
- main:
  - parses --target via sys.argv scan
  - no target → sys.exit(1)
  - resolves target to abs path
  - prints 'Scanning: ...'
  - calls scan_project + generate_report
  - if --apply AND suggestions: opens .mase/rules/rules.yaml,
    finds R09-GEN rule, unions existing allow_imports with
    suggestions, writes back

PITFALLS:
- 'typeing' is misspelled (typo preserved)
- 'os.path' is the full path string — NOT a bare 'os' (since
  split('.')[0] = 'os.path'... wait, 'os.path' has NO dot in
  the regex match: '^import (\\S+)' matches 'os.path' as one
  token since the regex doesn't strip parens. Actually with
  'import os.path' the (\\S+) matches 'os.path' literally, then
  split('.')[0] gives 'os.path' — that's why 'os.path' is in
  ALLOWED_IMPORTS as a literal string.)
- 'datetime' has dot in re, so 'datetime.datetime' splits to
  'datetime' which is allowed
- bare `except:` swallows ALL errors including KeyboardInterrupt
  (bad practice, but documented)
- generate_report's 'blocked' line is GATED on non-empty
- main writes YAML with sort_keys=False, allow_unicode=True,
  default_flow_style=False
- existing rules.yaml may not have R09-GEN rule → silent no-op
"""

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_audit_deps as ad  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────
class TestConstants:
    def test_blocked_imports(self):
        assert "subprocess" in ad.BLOCKED_IMPORTS
        assert "shutil" in ad.BLOCKED_IMPORTS
        assert "socket" in ad.BLOCKED_IMPORTS
        assert "requests" in ad.BLOCKED_IMPORTS
        assert "urllib" in ad.BLOCKED_IMPORTS
        assert "multiprocessing" in ad.BLOCKED_IMPORTS
        assert "threading" in ad.BLOCKED_IMPORTS
        assert "ctypes" in ad.BLOCKED_IMPORTS
        assert "signal" in ad.BLOCKED_IMPORTS
        assert len(ad.BLOCKED_IMPORTS) == 9

    def test_allowed_imports(self):
        assert "json" in ad.ALLOWED_IMPORTS
        assert "yaml" in ad.ALLOWED_IMPORTS
        assert "datetime" in ad.ALLOWED_IMPORTS
        assert "os.path" in ad.ALLOWED_IMPORTS
        assert "typeing" in ad.ALLOWED_IMPORTS  # typo preserved
        assert "re" in ad.ALLOWED_IMPORTS
        assert "math" in ad.ALLOWED_IMPORTS
        assert "pathlib" in ad.ALLOWED_IMPORTS


# ─────────────────────────────────────────────────────────────────────
# scan_project
# ─────────────────────────────────────────────────────────────────────
class TestScanProject:
    def test_empty_dir(self, tmp_path):
        f = ad.scan_project(str(tmp_path))
        assert f["allowed"] == set()
        assert f["blocked"] == set()
        assert f["unknown"] == set()
        assert f["files"] == {}

    def test_allowed_import(self, tmp_path):
        (tmp_path / "a.py").write_text("import json\nimport os\n")
        f = ad.scan_project(str(tmp_path))
        assert "json" in f["allowed"]
        # Note: 'import os.path' → regex matches 'os.path' as one token,
        # then split('.')[0] = 'os' → 'os' is unknown (not in ALLOWED)
        # The literal 'os.path' in ALLOWED_IMPORTS is a documented dead entry
        # Only 'import os' → 'os' is unknown

    def test_blocked_import(self, tmp_path):
        # L35: blocked import added to findings["blocked"]
        (tmp_path / "a.py").write_text("import subprocess\n")
        f = ad.scan_project(str(tmp_path))
        assert "subprocess" in f["blocked"]
        assert f["allowed"] == set()
        assert f["unknown"] == set()

    def test_unknown_import(self, tmp_path):
        (tmp_path / "a.py").write_text("import flask\nimport numpy\n")
        f = ad.scan_project(str(tmp_path))
        assert "flask" in f["unknown"]
        assert "numpy" in f["unknown"]

    def test_from_import(self, tmp_path):
        (tmp_path / "a.py").write_text("from yaml import safe_load\nfrom os import path\n")
        f = ad.scan_project(str(tmp_path))
        assert "yaml" in f["allowed"]
        assert "os" in f["unknown"]  # 'os' not in ALLOWED (only 'os.path')

    def test_dotted_import_uses_first(self, tmp_path):
        # 'from datetime.datetime import datetime' → top is 'datetime'
        # 'import datetime.datetime' → match 'datetime.datetime' then
        # split → 'datetime' (allowed)
        (tmp_path / "a.py").write_text(
            "import datetime.datetime\nfrom collections.abc import Mapping\n"
        )
        f = ad.scan_project(str(tmp_path))
        assert "datetime" in f["allowed"]
        assert "collections" in f["allowed"]

    def test_mixed(self, tmp_path):
        (tmp_path / "a.py").write_text(
            "import json\nimport subprocess\nimport flask\n"
        )
        f = ad.scan_project(str(tmp_path))
        assert "json" in f["allowed"]
        assert "subprocess" in f["blocked"]
        assert "flask" in f["unknown"]

    def test_skips_non_py(self, tmp_path):
        (tmp_path / "a.py").write_text("import json\n")
        (tmp_path / "b.txt").write_text("import flask\n")
        (tmp_path / "c.md").write_text("# import json\n")
        f = ad.scan_project(str(tmp_path))
        assert "a.py" in f["files"]
        assert "b.txt" not in f["files"]
        assert "c.md" not in f["files"]

    def test_skips_git_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "a.py").write_text("import flask\n")
        (tmp_path / "b.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        assert "b.py" in f["files"]
        assert ".git/a.py" not in f["files"]
        assert "flask" not in f["unknown"]

    def test_skips_pycache_dir(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "a.py").write_text("import flask\n")
        (tmp_path / "b.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        assert "b.py" in f["files"]
        assert "__pycache__/a.py" not in f["files"]

    def test_unreadable_file_skipped(self, tmp_path):
        # L24: bare except: continue
        # Use monkeypatch on builtins.open to force an OSError
        # (since tmp_path is writable as root, chmod 000 doesn't help)
        # and `dir.py` directory approach didn't register in coverage
        from unittest.mock import patch as mpatch
        # Build a fake directory with a .py file
        (tmp_path / "real.py").write_text("import json\n")
        (tmp_path / "bad.py").write_text("import flask\n")

        real_open = open
        def fake_open(p, *a, **kw):
            # Raise on bad.py
            if str(p).endswith("bad.py"):
                raise OSError("simulated unreadable")
            return real_open(p, *a, **kw)

        with mpatch("builtins.open", fake_open):
            f = ad.scan_project(str(tmp_path))

        # Only real.py should be in files; bad.py skipped via bare except
        assert "real.py" in f["files"]
        assert "bad.py" not in f["files"]
        # 'flask' not in unknown since bad.py was skipped
        assert "flask" not in f["unknown"]
        assert "json" in f["allowed"]

    def test_no_imports_in_file(self, tmp_path):
        # File with no imports → not added to 'files'
        (tmp_path / "a.py").write_text("x = 1\ny = 'hello'\n")
        f = ad.scan_project(str(tmp_path))
        assert f["files"] == {}

    def test_relative_path_key(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "a.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        # rel path is relative to target
        keys = list(f["files"].keys())
        assert any("sub" in k and "a.py" in k for k in keys)

    def test_multiple_imports_per_file(self, tmp_path):
        (tmp_path / "a.py").write_text(
            "import json\nimport yaml\nimport flask\nimport subprocess\n"
        )
        f = ad.scan_project(str(tmp_path))
        assert "a.py" in f["files"]
        file_imports = set(f["files"]["a.py"])
        assert "json" in file_imports
        assert "yaml" in file_imports
        assert "flask" in file_imports
        assert "subprocess" in file_imports

    def test_recursive_walk(self, tmp_path):
        (tmp_path / "a" / "b" / "c").mkdir(parents=True)
        (tmp_path / "a" / "b" / "c" / "deep.py").write_text("import json\n")
        f = ad.scan_project(str(tmp_path))
        assert any("deep.py" in k for k in f["files"])

    def test_blocked_imports_all_categories(self, tmp_path):
        # All 9 blocked imports
        for imp in ad.BLOCKED_IMPORTS:
            (tmp_path / f"{imp.replace('.','_')}.py").write_text(f"import {imp}\n")
        f = ad.scan_project(str(tmp_path))
        # 'os.path' is allowed (note: 'os.path' has no dot for split → kept as-is)
        # Actually all 9 should be in 'blocked'
        for imp in ad.BLOCKED_IMPORTS:
            assert imp in f["blocked"], f"{imp} should be blocked"


# ─────────────────────────────────────────────────────────────────────
# generate_report
# ─────────────────────────────────────────────────────────────────────
class TestGenerateReport:
    def test_empty_findings(self, capsys):
        findings = {"allowed": set(), "blocked": set(), "unknown": set(), "files": {}}
        suggestions = ad.generate_report(findings)
        out = capsys.readouterr().out
        assert "DEPENDENCY-AUDIT REPORT" in out
        assert "files gescannt: 0" in out
        assert "Erlaubt" in out
        # No 'Blocked' section when empty
        assert "❌ Blocked" not in out
        assert suggestions == []

    def test_blocked_section_only_when_nonempty(self, capsys):
        # L51: only printed when blocked set is non-empty
        findings = {"allowed": {"json"}, "blocked": {"subprocess"}, "unknown": set(), "files": {"a.py": ["json", "subprocess"]}}
        suggestions = ad.generate_report(findings)
        out = capsys.readouterr().out
        assert "❌ Blocked" in out
        assert "subprocess" in out

    def test_all_buckets_populated(self, capsys):
        findings = {
            "allowed": {"json", "yaml"},
            "blocked": {"subprocess"},
            "unknown": {"flask"},
            "files": {"a.py": ["json", "yaml", "subprocess", "flask"]},
        }
        suggestions = ad.generate_report(findings)
        out = capsys.readouterr().out
        assert "json" in out
        assert "yaml" in out
        assert "subprocess" in out
        assert "flask" in out
        assert "Erlaubt" in out
        assert "Blocked" in out
        assert "Unbekannt" in out

    def test_suggestions_for_unknown(self):
        findings = {"allowed": set(), "blocked": set(), "unknown": {"flask"}, "files": {}}
        suggestions = ad.generate_report(findings)
        assert "flask" in suggestions

    def test_suggestions_excludes_blocked(self):
        # 'subprocess' is blocked; shouldn't appear in suggestions
        findings = {"allowed": set(), "blocked": {"subprocess"}, "unknown": set(), "files": {}}
        suggestions = ad.generate_report(findings)
        assert "subprocess" not in suggestions

    def test_suggestions_with_mixed(self):
        findings = {
            "allowed": set(),
            "blocked": {"subprocess"},
            "unknown": {"flask", "numpy"},
            "files": {},
        }
        suggestions = ad.generate_report(findings)
        assert "flask" in suggestions
        assert "numpy" in suggestions
        assert "subprocess" not in suggestions

    def test_returns_list(self, capsys):
        findings = {"allowed": set(), "blocked": set(), "unknown": {"x"}, "files": {}}
        result = ad.generate_report(findings)
        assert isinstance(result, list)
        assert result == ["x"]


# ─────────────────────────────────────────────────────────────────────
# main (CLI) — test via direct invocation with patched sys.argv
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_no_target_exits_1(self, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py"]
        try:
            with pytest.raises(SystemExit) as exc:
                ad.main()
            assert exc.value.code == 1
            assert "--target" in capsys.readouterr().out
        finally:
            sys.argv = old_argv

    def test_with_target_no_py_files(self, tmp_path, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", str(tmp_path)]
        try:
            rc = ad.main()
            assert rc == 0
            out = capsys.readouterr().out
            assert "Scanning" in out
            assert "DEPENDENCY-AUDIT REPORT" in out
        finally:
            sys.argv = old_argv

    def test_with_target_and_py_files(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import json\n")
        (tmp_path / "b.py").write_text("import flask\n")
        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", str(tmp_path)]
        try:
            rc = ad.main()
            assert rc == 0
            out = capsys.readouterr().out
            assert "json" in out
            assert "flask" in out
        finally:
            sys.argv = old_argv

    def test_with_target_and_apply_no_rules_yaml(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import flask\n")
        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", str(tmp_path), "--apply"]
        try:
            rc = ad.main()
            assert rc == 0
            # No rules.yaml exists → silent no-op
            assert not (tmp_path / ".mase" / "rules" / "rules.yaml").exists()
        finally:
            sys.argv = old_argv

    def test_with_target_and_apply_existing_rules(self, tmp_path, capsys):
        # Set up project with rules.yaml containing R09-GEN
        (tmp_path / ".mase" / "rules").mkdir(parents=True)
        import yaml
        rules_data = {
            "version": 1,
            "rules": [
                {"id": "R09-GEN", "allow_imports": ["json"], "description": "test"},
                {"id": "OTHER", "description": "untouched"},
            ],
        }
        rules_path = tmp_path / ".mase" / "rules" / "rules.yaml"
        rules_path.write_text(yaml.dump(rules_data))
        # Add an unknown import
        (tmp_path / "a.py").write_text("import flask\n")

        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", str(tmp_path), "--apply"]
        try:
            rc = ad.main()
            assert rc == 0
            # R09-GEN should now have flask added
            new_data = yaml.safe_load(rules_path.read_text())
            r09 = next(r for r in new_data["rules"] if r["id"] == "R09-GEN")
            assert "flask" in r09["allow_imports"]
            assert "json" in r09["allow_imports"]  # existing preserved
            other = next(r for r in new_data["rules"] if r["id"] == "OTHER")
            assert other["description"] == "untouched"
        finally:
            sys.argv = old_argv

    def test_with_target_and_apply_no_suggestions(self, tmp_path, capsys):
        # Only allowed imports → no suggestions → --apply is no-op
        (tmp_path / ".mase" / "rules").mkdir(parents=True)
        import yaml
        rules_data = {"rules": [{"id": "R09-GEN", "allow_imports": []}]}
        rules_path = tmp_path / ".mase" / "rules" / "rules.yaml"
        rules_path.write_text(yaml.dump(rules_data))
        (tmp_path / "a.py").write_text("import json\n")

        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", str(tmp_path), "--apply"]
        try:
            rc = ad.main()
            assert rc == 0
            # File should be unchanged (no suggestions = no write)
            new_data = yaml.safe_load(rules_path.read_text())
            assert new_data["rules"][0]["allow_imports"] == []
        finally:
            sys.argv = old_argv

    def test_with_target_and_apply_no_r09_rule(self, tmp_path, capsys):
        # Rules.yaml exists but no R09-GEN rule → silent no-op
        (tmp_path / ".mase" / "rules").mkdir(parents=True)
        import yaml
        rules_data = {"rules": [{"id": "OTHER", "allow_imports": ["json"]}]}
        rules_path = tmp_path / ".mase" / "rules" / "rules.yaml"
        rules_path.write_text(yaml.dump(rules_data))
        (tmp_path / "a.py").write_text("import flask\n")

        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", str(tmp_path), "--apply"]
        try:
            rc = ad.main()
            assert rc == 0
            # No R09-GEN rule to update → file unchanged
            new_data = yaml.safe_load(rules_path.read_text())
            assert "R09-GEN" not in [r["id"] for r in new_data["rules"]]
        finally:
            sys.argv = old_argv

    def test_relative_target_resolved(self, tmp_path, capsys, monkeypatch):
        (tmp_path / "a.py").write_text("import json\n")
        monkeypatch.chdir(tmp_path)
        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", "."]
        try:
            rc = ad.main()
            assert rc == 0
            out = capsys.readouterr().out
            # Absolute path printed
            assert "Scanning:" in out
            assert str(tmp_path.resolve()) in out
        finally:
            sys.argv = old_argv

    def test_with_target_blocked_only(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("import subprocess\n")
        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", str(tmp_path)]
        try:
            rc = ad.main()
            assert rc == 0
            out = capsys.readouterr().out
            assert "Blocked" in out
            assert "subprocess" in out
        finally:
            sys.argv = old_argv


# ─────────────────────────────────────────────────────────────────────
# __main__ smoke (via runpy)
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_main_no_target(self, capsys):
        import runpy
        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py"]
        try:
            with pytest.raises(SystemExit) as exc:
                runpy.run_path("tools/dev_audit_deps.py", run_name="__main__")
            assert exc.value.code == 1
        finally:
            sys.argv = old_argv

    def test_exec_main_with_target(self, tmp_path, capsys):
        import runpy
        (tmp_path / "a.py").write_text("import json\n")
        old_argv = sys.argv
        sys.argv = ["dev_audit_deps.py", "--target", str(tmp_path)]
        try:
            runpy.run_path("tools/dev_audit_deps.py", run_name="__main__")
            out = capsys.readouterr().out
            assert "DEPENDENCY-AUDIT REPORT" in out
        finally:
            sys.argv = old_argv
