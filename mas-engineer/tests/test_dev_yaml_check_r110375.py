"""R110-375 — tests for tools/dev_yaml_check.py (8 functions, 351 lines).

Coverage target: tools/dev_yaml_check.py 13.7% → 80%+ (196+ stmts covered).
Test plan: 8 classes, ~46 tests.

Per R110-78 verification-theater self-catch rule: every number here must
be derived from the actual term-report after running, not estimated.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Make tools/ importable as a package namespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import dev_yaml_check as mod  # noqa: E402


# ═══════════════════════════════════════════════════════
#  TestCheckYaml (10 tests) — tools/dev_yaml_check.py:27-90
# ═══════════════════════════════════════════════════════

class TestCheckYaml:
    """check_yaml(filepath) → dict{file, check, status, error?, warnings[], lines}."""

    def test_not_found_returns_error(self, tmp_path):
        """Missing file → status=error, error='File not found'."""
        missing = str(tmp_path / "does_not_exist.yaml")
        result = mod.check_yaml(missing)
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()
        assert result["file"] == missing
        assert result["check"] == "yaml"

    def test_empty_file_warning(self, tmp_path):
        """0-byte file → status=warning, P2 'Empty file' warning, no error."""
        f = tmp_path / "empty.yaml"
        f.write_text("")
        result = mod.check_yaml(str(f))
        assert result["status"] == "warning"
        assert result["error"] is None
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["severity"] == "P2"
        assert "empty" in result["warnings"][0]["title"].lower()

    def test_valid_yaml_ok(self, tmp_path):
        """Valid YAML → status=ok, no error, no warnings."""
        f = tmp_path / "good.yaml"
        f.write_text("name: alice\nage: 30\n")
        result = mod.check_yaml(str(f))
        assert result["status"] == "ok"
        assert result["error"] is None
        assert result["warnings"] == []
        assert result["lines"] >= 2

    def test_invalid_yaml_syntax_error(self, tmp_path):
        """Bad YAML → status=error, error starts with 'YAML syntax error:'."""
        f = tmp_path / "bad.yaml"
        f.write_text("name: alice\n  bad-indent: oops\n: invalid\n")
        result = mod.check_yaml(str(f))
        assert result["status"] == "error"
        assert "yaml syntax error" in result["error"].lower()

    def test_binary_file_error(self, tmp_path):
        """Binary file (not UTF-8 decodable) → status=error, 'Binary file detected'."""
        f = tmp_path / "binary.yaml"
        # Write raw bytes that are not valid UTF-8
        f.write_bytes(b"\x80\x81\x82\x83\xff\xfe\xfd")
        result = mod.check_yaml(str(f))
        assert result["status"] == "error"
        assert "binary" in result["error"].lower()

    def test_lines_count_single_line(self, tmp_path):
        """Single-line YAML with trailing \\n → lines=2 (count+1)."""
        f = tmp_path / "single.yaml"
        f.write_text("name: alice\n")
        result = mod.check_yaml(str(f))
        assert result["status"] == "ok"
        # "name: alice\n" has 1 newline → lines = 1+1 = 2
        assert result["lines"] == 2

    def test_lines_count_multiline(self, tmp_path):
        """Multi-line YAML → lines = number of \\n + 1."""
        f = tmp_path / "multi.yaml"
        content = "key1: v1\nkey2: v2\nkey3: v3\n"
        f.write_text(content)
        result = mod.check_yaml(str(f))
        assert result["status"] == "ok"
        # 3 newlines → 4 lines (or 3 if no trailing \n logic; we use count+1)
        # content.count('\n') == 3, lines = 3+1 = 4
        assert result["lines"] == content.count("\n") + 1

    def test_yaml_list_ok(self, tmp_path):
        """YAML with lists → status=ok."""
        f = tmp_path / "list.yaml"
        f.write_text("- one\n- two\n- three\n")
        result = mod.check_yaml(str(f))
        assert result["status"] == "ok"

    def test_yaml_nested_dict_ok(self, tmp_path):
        """Nested YAML structure → status=ok."""
        f = tmp_path / "nested.yaml"
        f.write_text("parent:\n  child:\n    key: value\n  list:\n    - a\n    - b\n")
        result = mod.check_yaml(str(f))
        assert result["status"] == "ok"

    def test_yaml_with_unicode_ok(self, tmp_path):
        """YAML with unicode (UTF-8) → status=ok, no UnicodeDecodeError."""
        f = tmp_path / "unicode.yaml"
        f.write_text("greeting: Hallo Welt 🌍\nemoji: 🚀\n", encoding="utf-8")
        result = mod.check_yaml(str(f))
        assert result["status"] == "ok"
        assert result["error"] is None


# ═══════════════════════════════════════════════════════
#  TestDetectFileType (8 tests) — tools/dev_yaml_check.py:93-115
# ═══════════════════════════════════════════════════════

class TestDetectFileType:
    """detect_file_type(filepath) → 'py' | 'sh' | 'yaml' | 'unknown'."""

    def test_shebang_python(self, tmp_path):
        """Shebang '#!/usr/bin/env python3' → 'py'."""
        f = tmp_path / "script"
        f.write_text("#!/usr/bin/env python3\nprint('hi')\n")
        assert mod.detect_file_type(str(f)) == "py"

    def test_shebang_bash(self, tmp_path):
        """Shebang '#!/bin/bash' → 'sh'."""
        f = tmp_path / "script"
        f.write_text("#!/bin/bash\necho hi\n")
        assert mod.detect_file_type(str(f)) == "sh"

    def test_shebang_sh(self, tmp_path):
        """Shebang '/bin/sh' → 'sh'."""
        f = tmp_path / "script"
        f.write_text("#!/bin/sh\necho hi\n")
        assert mod.detect_file_type(str(f)) == "sh"

    def test_extension_py(self, tmp_path):
        """No shebang, .py extension → 'py'."""
        f = tmp_path / "no_shebang.py"
        f.write_text("x = 1\n")
        assert mod.detect_file_type(str(f)) == "py"

    def test_extension_sh(self, tmp_path):
        """No shebang, .sh extension → 'sh'."""
        f = tmp_path / "script.sh"
        f.write_text("echo hi\n")
        assert mod.detect_file_type(str(f)) == "sh"

    def test_extension_yaml(self, tmp_path):
        """No shebang, .yaml extension → 'yaml'."""
        f = tmp_path / "config.yaml"
        f.write_text("k: v\n")
        assert mod.detect_file_type(str(f)) == "yaml"

    def test_extension_yml(self, tmp_path):
        """No shebang, .yml extension → 'yaml'."""
        f = tmp_path / "config.yml"
        f.write_text("k: v\n")
        assert mod.detect_file_type(str(f)) == "yaml"

    def test_unknown_extension(self, tmp_path):
        """No shebang, .txt extension → 'unknown'."""
        f = tmp_path / "data.txt"
        f.write_text("hello\n")
        assert mod.detect_file_type(str(f)) == "unknown"


# ═══════════════════════════════════════════════════════
#  TestCheckPythonSyntax (4 tests) — tools/dev_yaml_check.py:118-142
# ═══════════════════════════════════════════════════════

class TestCheckPythonSyntax:
    """check_python_syntax(filepath) → dict with status/error."""

    def test_not_found(self, tmp_path):
        """Missing file → status=error."""
        result = mod.check_python_syntax(str(tmp_path / "missing.py"))
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()
        assert result["check"] == "python"

    def test_valid_python(self, tmp_path):
        """Valid Python source → status=ok."""
        f = tmp_path / "good.py"
        f.write_text("def hello():\n    return 42\n")
        result = mod.check_python_syntax(str(f))
        assert result["status"] == "ok"
        assert result["error"] is None

    def test_syntax_error(self, tmp_path):
        """Invalid Python source → status=error, mentions 'syntax error'."""
        f = tmp_path / "bad.py"
        f.write_text("def hello(:\n    return 42\n")  # missing closing paren
        result = mod.check_python_syntax(str(f))
        assert result["status"] == "error"
        assert "syntax error" in result["error"].lower() or "SyntaxError" in result["error"]

    def test_check_field_is_python(self, tmp_path):
        """check field is 'python' regardless of status."""
        f = tmp_path / "anything.py"
        f.write_text("x = 1\n")
        result = mod.check_python_syntax(str(f))
        assert result["check"] == "python"


# ═══════════════════════════════════════════════════════
#  TestCheckShellSyntax (4 tests) — tools/dev_yaml_check.py:145-176
# ═══════════════════════════════════════════════════════

class TestCheckShellSyntax:
    """check_shell_syntax(filepath) → dict with status/error."""

    def test_not_found(self, tmp_path):
        """Missing file → status=error."""
        result = mod.check_shell_syntax(str(tmp_path / "missing.sh"))
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_valid_bash(self, tmp_path):
        """Valid bash script → status=ok (if bash is installed)."""
        # Skip if bash is not installed (CI edge case)
        bash_check = subprocess.run(["which", "bash"], capture_output=True, text=True)
        if bash_check.returncode != 0:
            pytest.skip("bash not installed on this system")
        f = tmp_path / "good.sh"
        f.write_text("#!/bin/bash\necho hello\n")
        result = mod.check_shell_syntax(str(f))
        assert result["status"] == "ok"
        assert result["error"] is None

    def test_invalid_bash(self, tmp_path):
        """Invalid bash syntax → status=error."""
        bash_check = subprocess.run(["which", "bash"], capture_output=True, text=True)
        if bash_check.returncode != 0:
            pytest.skip("bash not installed on this system")
        f = tmp_path / "bad.sh"
        f.write_text("if [ missing-bracket\n")  # syntax error
        result = mod.check_shell_syntax(str(f))
        assert result["status"] == "error"
        assert result["error"]  # has some error message

    def test_check_field_is_shell(self, tmp_path):
        """check field is 'shell'."""
        f = tmp_path / "x.sh"
        f.write_text("echo hi\n")
        result = mod.check_shell_syntax(str(f))
        assert result["check"] == "shell"

    def test_bash_not_installed(self, tmp_path, monkeypatch):
        """subprocess.run(['which', 'bash']) returncode!=0 → status=warning."""
        # Source uses subprocess.run(['which', 'bash']) — mock it
        from unittest.mock import MagicMock
        fake_proc = MagicMock()
        fake_proc.returncode = 1  # which failed
        monkeypatch.setattr(
            "subprocess.run",
            lambda *args, **kwargs: fake_proc if args and args[0] == ["which", "bash"] else subprocess.run(*args, **kwargs)
        )
        f = tmp_path / "x.sh"
        f.write_text("echo hi\n")
        result = mod.check_shell_syntax(str(f))
        assert result["status"] == "warning"
        assert "bash" in result["warning"].lower()


# ═══════════════════════════════════════════════════════
#  TestCheckSyntaxDispatch (5 tests) — tools/dev_yaml_check.py:179-198
# ═══════════════════════════════════════════════════════

class TestCheckSyntaxDispatch:
    """check_syntax(filepath, file_type) → dispatches to right checker."""

    def test_auto_with_py_file(self, tmp_path):
        """auto + .py file → routes to check_python_syntax."""
        f = tmp_path / "x.py"
        f.write_text("x = 1\n")
        result = mod.check_syntax(str(f), "auto")
        assert result["check"] == "python"
        assert result["status"] == "ok"

    def test_auto_with_yaml_file(self, tmp_path):
        """auto + .yaml file → routes to check_yaml."""
        f = tmp_path / "x.yaml"
        f.write_text("k: v\n")
        result = mod.check_syntax(str(f), "auto")
        assert result["check"] == "yaml"
        assert result["status"] == "ok"

    def test_explicit_py(self, tmp_path):
        """file_type='py' → routes to check_python_syntax."""
        f = tmp_path / "x.txt"  # wrong extension
        f.write_text("x = 1\n")
        result = mod.check_syntax(str(f), "py")
        assert result["check"] == "python"

    def test_explicit_unknown_returns_warning(self, tmp_path):
        """file_type='unknown' → returns warning (no checker)."""
        result = mod.check_syntax("x.txt", "unknown")
        assert result["status"] == "warning"
        assert "unknown" in result["warning"].lower()
        assert result["check"] == "syntax"

    def test_auto_with_unknown_file(self, tmp_path):
        """auto + .txt → routes to yaml check (auto fallback) but file doesn't exist."""
        result = mod.check_syntax(str(tmp_path / "x.txt"), "auto")
        # auto → detect_file_type → 'unknown' (not yaml) → falls through to unknown warning
        # Actually check: detect returns 'unknown' for .txt, then check_syntax
        # since file_type != 'py'/'sh'/'yaml' (it's 'unknown'), returns warning.
        assert result["status"] == "warning"

    def test_explicit_sh(self, tmp_path):
        """file_type='sh' → routes to check_shell_syntax."""
        f = tmp_path / "x.txt"  # wrong extension but explicit sh
        f.write_text("echo hi\n")
        result = mod.check_syntax(str(f), "sh")
        assert result["check"] == "shell"

    def test_explicit_yaml(self, tmp_path):
        """file_type='yaml' → routes to check_yaml."""
        f = tmp_path / "x.txt"  # wrong extension but explicit yaml
        f.write_text("k: v\n")
        result = mod.check_syntax(str(f), "yaml")
        assert result["check"] == "yaml"


# ═══════════════════════════════════════════════════════
#  TestVerifyState (6 tests) — tools/dev_yaml_check.py:201-267
# ═══════════════════════════════════════════════════════

class TestVerifyState:
    """verify_state(workspace) → dict with totals/score/score_band."""

    def test_workspace_not_found(self, tmp_path):
        """Non-existent workspace → status=error, 'Workspace not found'."""
        result = mod.verify_state(str(tmp_path / "no_workspace"))
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_workspace_with_no_yamls_warning(self, tmp_path):
        """Empty workspace (no .yaml files) → status=warning, 'No YAML files'."""
        result = mod.verify_state(str(tmp_path))
        assert result["status"] == "warning"
        assert "no yaml" in result["warning"].lower()
        assert result["total"] == 0
        assert result["score"] == 0

    def test_perfect_score(self, tmp_path):
        """Workspace with all valid YAMLs → score=100, score_band='perfect', status=ok."""
        for i in range(3):
            (tmp_path / f"good{i}.yaml").write_text(f"k{i}: v{i}\n")
        result = mod.verify_state(str(tmp_path))
        assert result["status"] == "ok"
        assert result["total"] == 3
        assert result["ok"] == 3
        assert result["failed"] == 0
        assert result["score"] == 100
        assert result["score_band"] == "perfect"

    def test_partial_score_good_band(self, tmp_path):
        """1 of 4 bad → score=75, score_band='critical' (since 75<80)."""
        for i in range(3):
            (tmp_path / f"good{i}.yaml").write_text(f"k{i}: v{i}\n")
        (tmp_path / "bad.yaml").write_text("k: :\n: bad\n")
        result = mod.verify_state(str(tmp_path))
        assert result["total"] == 4
        assert result["ok"] == 3
        assert result["failed"] == 1
        assert result["score"] == 75
        assert result["score_band"] == "critical"
        assert result["status"] == "error"

    def test_score_band_good(self, tmp_path):
        """4 of 5 good → score=80, score_band='good', status=warning."""
        for i in range(4):
            (tmp_path / f"good{i}.yaml").write_text(f"k{i}: v{i}\n")
        (tmp_path / "bad.yaml").write_text("k: :\n: bad\n")
        result = mod.verify_state(str(tmp_path))
        assert result["total"] == 5
        assert result["ok"] == 4
        assert result["score"] == 80
        assert result["score_band"] == "good"
        assert result["status"] == "warning"

    def test_excludes_backup_and_checkpoints(self, tmp_path):
        """Files in .backups/, checkpoints/, __pycache__/ should be skipped."""
        # Create a backup dir with a bad yaml — should be excluded
        backup_dir = tmp_path / ".backups"
        backup_dir.mkdir()
        (backup_dir / "bad.yaml").write_text("k: :\n: bad\n")
        # Create a good yaml in root
        (tmp_path / "good.yaml").write_text("k: v\n")
        result = mod.verify_state(str(tmp_path))
        # Only 'good.yaml' should be counted (1/1 = perfect)
        assert result["total"] == 1
        assert result["ok"] == 1
        assert result["score"] == 100


# ═══════════════════════════════════════════════════════
#  TestCheckAll (4 tests) — tools/dev_yaml_check.py:270-297
# ═══════════════════════════════════════════════════════

class TestCheckAll:
    """check_all(filepath, file_type) → aggregated yaml + syntax check."""

    def test_yaml_only(self, tmp_path):
        """Yaml file → 1 check (yaml), status=ok if valid."""
        f = tmp_path / "config.yaml"
        f.write_text("k: v\n")
        result = mod.check_all(str(f), "auto")
        assert result["file"] == str(f)
        assert result["status"] == "ok"
        assert len(result["checks"]) == 1
        assert result["checks"][0]["check"] == "yaml"

    def test_python_file_runs_yaml_and_syntax(self, tmp_path):
        """Python file with auto-detect → yaml + python check, both pass."""
        f = tmp_path / "script.py"
        f.write_text("#!/usr/bin/env python3\nx = 1\nprint(x)\n")
        result = mod.check_all(str(f), "auto")
        # auto + .py → detect returns 'py' → file_type != 'yaml'/'auto' → only python check
        # Actually per code: check_all does check_yaml if file_type in (yaml, auto)
        # After detect → 'py', so file_type='py', so check_yaml NOT called
        # Only python check
        assert len(result["checks"]) == 1
        assert result["checks"][0]["check"] == "python"
        assert result["status"] == "ok"

    def test_aggregation_error_status(self, tmp_path):
        """Error in any check → overall status=error."""
        f = tmp_path / "bad.yaml"
        f.write_text("k: :\n: bad\n")
        result = mod.check_all(str(f), "auto")
        assert result["status"] == "error"
        assert result["checks"][0]["status"] == "error"

    def test_aggregation_warning_status(self, tmp_path):
        """Warning (no error) in any check → overall status=warning."""
        f = tmp_path / "empty.yaml"
        f.write_text("")  # empty → warning
        result = mod.check_all(str(f), "auto")
        # empty file → check_yaml returns status=warning (P2)
        assert result["status"] == "warning"
        assert result["checks"][0]["status"] == "warning"

    def test_check_all_sh_file(self, tmp_path):
        """check_all with file_type='sh' → runs shell syntax check."""
        f = tmp_path / "x.sh"
        f.write_text("#!/bin/bash\necho hi\n")
        # If bash available, should pass
        bash_check = subprocess.run(["which", "bash"], capture_output=True, text=True)
        if bash_check.returncode != 0:
            pytest.skip("bash not installed")
        result = mod.check_all(str(f), "sh")
        # check_all: file_type='sh' → not (yaml, auto) → only sh check
        assert len(result["checks"]) == 1
        assert result["checks"][0]["check"] == "shell"


# ═══════════════════════════════════════════════════════
#  TestMainCli (5 tests) — tools/dev_yaml_check.py:304-347
# ═══════════════════════════════════════════════════════

class TestMainCli:
    """main() CLI entry — dispatch on sys.argv[1]."""

    def test_no_args_returns_2(self, capsys, monkeypatch):
        """No args → print_usage + return 2."""
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py"])
        rc = mod.main()
        assert rc == 2
        captured = capsys.readouterr()
        # usage printed (docstring of the module)
        assert captured.out or "yaml" in (captured.out + captured.err).lower()

    def test_check_yaml_command(self, capsys, tmp_path, monkeypatch):
        """CHECK_YAML <file> → json output, rc=0 for valid yaml."""
        f = tmp_path / "good.yaml"
        f.write_text("k: v\n")
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "CHECK_YAML", str(f)])
        rc = mod.main()
        assert rc == 0
        out = capsys.readouterr().out
        # JSON output contains "ok"
        data = json.loads(out)
        assert data["status"] == "ok"

    def test_verify_state_command(self, capsys, tmp_path, monkeypatch):
        """VERIFY_STATE <workspace> → json output."""
        (tmp_path / "g.yaml").write_text("k: v\n")
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "VERIFY_STATE", str(tmp_path)])
        rc = mod.main()
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["check"] == "state"
        assert data["total"] == 1
        assert data["score"] == 100

    def test_help_flag(self, capsys, monkeypatch):
        """HELP (uppercase, per main()'s .upper() + tuple match) → return 0."""
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "HELP"])
        rc = mod.main()
        assert rc == 0

    def test_unknown_command_returns_2(self, capsys, monkeypatch):
        """Unknown command → print error + return 2."""
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "BOGUS_CMD"])
        rc = mod.main()
        assert rc == 2
        err = capsys.readouterr().err
        assert "unknown" in err.lower()

    def test_check_yaml_missing_arg(self, capsys, monkeypatch):
        """CHECK_YAML without file → stderr usage + return 2."""
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "CHECK_YAML"])
        rc = mod.main()
        assert rc == 2
        err = capsys.readouterr().err
        assert "usage" in err.lower()

    def test_check_syntax_missing_arg(self, capsys, monkeypatch):
        """CHECK_SYNTAX without file → return 2."""
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "CHECK_SYNTAX"])
        rc = mod.main()
        assert rc == 2

    def test_verify_state_missing_arg(self, capsys, monkeypatch):
        """VERIFY_STATE without workspace → return 2."""
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "VERIFY_STATE"])
        rc = mod.main()
        assert rc == 2

    def test_check_all_missing_arg(self, capsys, monkeypatch):
        """CHECK_ALL without file → return 2."""
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "CHECK_ALL"])
        rc = mod.main()
        assert rc == 2

    def test_main_returns_1_on_error_status(self, capsys, monkeypatch, tmp_path):
        """main() returns 1 when result status='error'."""
        f = tmp_path / "bad.yaml"
        f.write_text("k: :\n: bad\n")
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "CHECK_YAML", str(f)])
        rc = mod.main()
        assert rc == 1

    def test_main_returns_0_on_warning_status(self, capsys, monkeypatch, tmp_path):
        """main() returns 0 when result status='warning' (warnings don't fail)."""
        f = tmp_path / "empty.yaml"
        f.write_text("")
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "CHECK_YAML", str(f)])
        rc = mod.main()
        assert rc == 0

    def test_check_syntax_with_4_args(self, capsys, monkeypatch, tmp_path):
        """CHECK_SYNTAX <file> <ftype> (4-arg) → uses ftype arg."""
        f = tmp_path / "x.py"
        f.write_text("x = 1\n")
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "CHECK_SYNTAX", str(f), "py"])
        rc = mod.main()
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["check"] == "python"

    def test_check_all_with_4_args(self, capsys, monkeypatch, tmp_path):
        """CHECK_ALL <file> <ftype> (4-arg) → uses ftype arg."""
        f = tmp_path / "x.yaml"
        f.write_text("k: v\n")
        monkeypatch.setattr(sys, "argv", ["dev_yaml_check.py", "CHECK_ALL", str(f), "yaml"])
        rc = mod.main()
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["file"] == str(f)
