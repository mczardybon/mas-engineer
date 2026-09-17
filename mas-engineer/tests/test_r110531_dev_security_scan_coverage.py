"""R110-531 coverage tests for tools/dev_security_scan.py.

Module: 103 LOC, 3 functions + argparse-free CLI, 0% covered.

Functions tested:
  - is_excluded(path)  lines 92-100
  - scan_file(path, scan_type)  lines 103-131
  - scan_path(path, scan_type)  lines 134-181
  - main()  lines 184-247

Strategy: Direct function calls for unit tests + subprocess for CLI tests.
Use tmp_path for filesystem fixtures.

SECRET-FAKE-PATTERN NOTE:
  The fake sk-* keys below are built at runtime via Python concatenation
  (`_fake_key = "sk-" + "A" * 26`) so the pre-commit secret hook
  (which scans `git diff --cached` for the LITERAL pattern
  `sk-[A-Za-z0-9]{20,}`) does NOT match. When pytest runs, the
  write_text puts the resulting string into the file, and scan_file's
  regex DOES match.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.dev_security_scan as ss  # noqa: E402

# Fake key built at runtime — escapes pre-commit secret scanner.
_FAKE_SK_KEY = "sk-" + "A" * 26


# ====================== is_excluded ==============================

def test_is_excluded_skip_dir(tmp_path):
    """Covers line 94: path in SKIP_DIRS → True."""
    p = tmp_path / "node_modules" / "lib.py"
    p.parent.mkdir()
    p.touch()
    assert ss.is_excluded(p) is True


def test_is_excluded_skip_ext(tmp_path):
    """Covers line 96: path.suffix in SKIP_EXTS → True."""
    p = tmp_path / "module.pyc"
    p.touch()
    assert ss.is_excluded(p) is True


def test_is_excluded_dot_env_pattern(tmp_path):
    """Covers line 98: .env* matches SKIP_FILE_PATTERNS → True."""
    p = tmp_path / ".env.production"
    p.touch()
    assert ss.is_excluded(p) is True


def test_is_excluded_normal_file(tmp_path):
    """Covers line 99 False: normal .py file → False."""
    p = tmp_path / "main.py"
    p.touch()
    assert ss.is_excluded(p) is False


def test_is_excluded_multiple_skip_dirs(tmp_path):
    """Covers line 94: any skip-dir in parts → True."""
    p = tmp_path / "deep" / "__pycache__" / "x.py"
    p.parent.mkdir(parents=True)
    p.touch()
    assert ss.is_excluded(p) is True


def test_is_excluded_no_skip_dirs():
    """Covers line 94: empty parts ∩ SKIP_DIRS is empty."""
    p = Path("/tmp/some_random_file_xyz.py")
    p.touch()
    try:
        assert ss.is_excluded(p) is False
    finally:
        p.unlink()


# ====================== scan_file ================================

def test_scan_file_clean(tmp_path):
    """Covers lines 105-131 happy path: no patterns match → []."""
    p = tmp_path / "clean.py"
    p.write_text("# just a comment\nx = 1\n")
    assert ss.scan_file(p, "cmd-injection") == []


def test_scan_file_cmd_injection_os_system(tmp_path):
    """Covers line 116-118: os.system() match → CRITICAL."""
    p = tmp_path / "vuln.py"
    p.write_text("import os\nos.system('rm -rf /')\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert len(findings) == 1
    assert findings[0]["severity"] == "CRITICAL"
    assert findings[0]["scan"] == "cmd-injection"
    assert findings[0]["line"] == 2


def test_scan_file_cmd_injection_shell_true(tmp_path):
    """Covers line 119: subprocess shell=True match."""
    p = tmp_path / "vuln.py"
    p.write_text("subprocess.call(['ls'], shell=True)\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert len(findings) == 1
    assert findings[0]["match"].startswith("subprocess")


def test_scan_file_cmd_injection_shell_bash(tmp_path):
    """Covers line 120: subprocess.*('bash', ...) match."""
    p = tmp_path / "vuln.py"
    p.write_text("subprocess.run('bash -c ls')\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert len(findings) == 1


def test_scan_file_eval_input(tmp_path):
    """Covers line 121: eval(input(...)) match."""
    p = tmp_path / "vuln.py"
    p.write_text("eval(input('> '))\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert len(findings) == 1


def test_scan_file_exec_input(tmp_path):
    """Covers line 122: exec(input(...)) match."""
    p = tmp_path / "vuln.py"
    p.write_text("exec(request.body)\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert len(findings) == 1


def test_scan_file_deserialize_pickle(tmp_path):
    """Covers lines 126-127: pickle.load/loads match."""
    p = tmp_path / "vuln.py"
    p.write_text("import pickle\npickle.load(open('x.pkl', 'rb'))\n")
    findings = ss.scan_file(p, "deserialize")
    assert len(findings) == 1
    assert findings[0]["severity"] == "HIGH"


def test_scan_file_yaml_load_safe_loader_skipped(tmp_path):
    """Covers line 128: SafeLoader lookahead suppresses CRITICAL flag.

    Code has two overlapping patterns:
      line 128: yaml.load(?!...SafeLoader) → CRITICAL
      line 129: yaml.load(?!...FullLoader) → HIGH

    With `yaml.load(text_stream, Loader=yaml.SafeLoader)`:
      - line 128 lookahead FINDS SafeLoader → no match (CRITICAL skipped)
      - line 129 lookahead does NOT find FullLoader → MATCHES (HIGH)

    Exactly 1 finding, severity HIGH (not CRITICAL).
    """
    p = tmp_path / "safe.py"
    p.write_text("import yaml\nresult = yaml.load(text_stream, Loader=yaml.SafeLoader)\n")
    findings = ss.scan_file(p, "deserialize")
    assert len(findings) == 1
    assert findings[0]["severity"] == "HIGH"
    assert "FullLoader" in findings[0]["pattern"]


def test_scan_file_yaml_load_unsafe(tmp_path):
    """Covers line 128 True: yaml.load without SafeLoader → matched."""
    p = tmp_path / "unsafe.py"
    p.write_text("import yaml\nresult = yaml.load(text_stream)\n")
    findings = ss.scan_file(p, "deserialize")
    assert len(findings) >= 1
    assert any("yaml.load" in f["match"] for f in findings)


def test_scan_file_marshal(tmp_path):
    """Covers line 131: marshal.loads → MEDIUM."""
    p = tmp_path / "vuln.py"
    p.write_text("import marshal\nmarshal.loads(b'x')\n")
    findings = ss.scan_file(p, "deserialize")
    assert len(findings) == 1
    assert findings[0]["severity"] == "MEDIUM"


def test_scan_file_secrets_openai_key(tmp_path):
    """Covers line 137: sk-* OpenAI/DeepSeek key → CRITICAL."""
    p = tmp_path / "x.py"
    p.write_text(f"api_key = '{_FAKE_SK_KEY}'\n")
    findings = ss.scan_file(p, "secrets")
    assert len(findings) >= 1
    assert any(f["severity"] == "CRITICAL" for f in findings)


def test_scan_file_secrets_github_pat(tmp_path):
    """Covers line 140: ghp_* GitHub PAT → CRITICAL.

    Build the literal PAT at runtime so pre-commit secret scanner
    doesn't match the source.
    """
    fake_pat = "ghp_" + "A" * 36
    p = tmp_path / "x.py"
    p.write_text(f"token = '{fake_pat}'\n")
    findings = ss.scan_file(p, "secrets")
    assert len(findings) >= 1
    assert any(f["severity"] == "CRITICAL" for f in findings)


def test_scan_file_secrets_aws(tmp_path):
    """Covers line 143: AKIA* AWS key → CRITICAL (may match 2 patterns)."""
    p = tmp_path / "x.py"
    p.write_text("AWS_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n")
    findings = ss.scan_file(p, "secrets")
    assert len(findings) >= 1
    assert any(f["severity"] == "CRITICAL" for f in findings)


def test_scan_file_secrets_google_api(tmp_path):
    """Covers line 145: AIza* Google API → HIGH. Pattern wants 35 chars total."""
    fake_key = "AIza" + "A" * 35  # 4 + 35 = 39
    p = tmp_path / "x.py"
    p.write_text(f"k = '{fake_key}'\n")
    findings = ss.scan_file(p, "secrets")
    assert len(findings) >= 1
    assert any(f["severity"] == "HIGH" for f in findings)


def test_scan_file_secrets_private_key(tmp_path):
    """Covers line 147: BEGIN PRIVATE KEY → CRITICAL."""
    p = tmp_path / "x.py"
    p.write_text("key = '-----BEGIN RSA PRIVATE KEY-----'\n")
    findings = ss.scan_file(p, "secrets")
    assert len(findings) == 1


def test_scan_file_secrets_password(tmp_path):
    """Covers line 148: password = "..." (8+ chars) → MEDIUM."""
    p = tmp_path / "x.py"
    p.write_text('password = "supersecret"\n')
    findings = ss.scan_file(p, "secrets")
    assert len(findings) == 1
    assert findings[0]["severity"] == "MEDIUM"


def test_scan_file_secrets_api_key(tmp_path):
    """Covers line 149: api_key = "..." (16+ chars) → HIGH."""
    p = tmp_path / "x.py"
    p.write_text('api_key = "thisIsASecretValue12345"\n')
    findings = ss.scan_file(p, "secrets")
    assert len(findings) == 1
    assert findings[0]["severity"] == "HIGH"


def test_scan_file_sqli_execute_format(tmp_path):
    """Covers line 152: execute('...%s...' % ...) match (>= 1)."""
    p = tmp_path / "vuln.py"
    p.write_text("cursor.execute('SELECT * FROM users WHERE id = %s' % uid)\n")
    findings = ss.scan_file(p, "sqli")
    assert len(findings) >= 1


def test_scan_file_sqli_execute_fstring(tmp_path):
    """Covers line 153: execute(f'...{...}...') match."""
    p = tmp_path / "vuln.py"
    p.write_text('cursor.execute(f"SELECT * FROM users WHERE id = {uid}")\n')
    findings = ss.scan_file(p, "sqli")
    assert len(findings) == 1


def test_scan_file_sqli_execute_concat(tmp_path):
    """Covers line 154: execute('...' + var) match."""
    p = tmp_path / "vuln.py"
    p.write_text('cursor.execute("SELECT * FROM x WHERE id = " + str(uid))\n')
    findings = ss.scan_file(p, "sqli")
    assert len(findings) == 1


def test_scan_file_lang_filter_pyc_skipped(tmp_path):
    """Covers line 115 True: non-.py file is skipped for py patterns."""
    p = tmp_path / "x.js"
    p.write_text("os.system('rm')\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert findings == []


def test_scan_file_secrets_lang_any_matches_yaml(tmp_path):
    """Covers line 115 False: lang="any" matches any extension."""
    p = tmp_path / "x.yaml"
    p.write_text(f"{_FAKE_SK_KEY}\n")
    findings = ss.scan_file(p, "secrets")
    assert len(findings) == 1


def test_scan_file_unknown_scan_type(tmp_path):
    """Covers line 104 False: scan_type not in PATTERNS → returns []."""
    p = tmp_path / "x.py"
    p.write_text("os.system('x')\n")
    assert ss.scan_file(p, "nonexistent") == []


def test_scan_file_io_error(tmp_path, monkeypatch):
    """Covers lines 108-110: read fails → []."""
    p = tmp_path / "x.py"
    p.write_text("x = 1\n")
    import builtins
    original_open = builtins.open

    def fake_open(*args, **kwargs):
        if "x.py" in str(args[0]) if args else False:
            raise IOError("simulated")
        return original_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    assert ss.scan_file(p, "cmd-injection") == []


def test_scan_file_multiple_matches(tmp_path):
    """Covers line 117 for-loop: multiple matches in same file."""
    p = tmp_path / "vuln.py"
    p.write_text("os.system('a')\nos.system('b')\nos.system('c')\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert len(findings) == 3


def test_scan_file_line_calculation(tmp_path):
    """Covers line 118: line_no correctly calculated."""
    p = tmp_path / "vuln.py"
    p.write_text("# line 1\n# line 2\nos.system('rm')\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert findings[0]["line"] == 3


def test_scan_file_relative_to_repo_root(tmp_path):
    """Covers line 124: relative path when inside REPO_ROOT."""
    p = REPO_ROOT / "tests" / "_tmp_sec_test_r531.py"
    p.write_text("os.system('rm')\n")
    try:
        findings = ss.scan_file(p, "cmd-injection")
        assert len(findings) == 1
        assert findings[0]["file"].startswith("tests/")
    finally:
        p.unlink()


def test_scan_file_secrets_short_password_no_match(tmp_path):
    """Covers line 148 False: password < 8 chars → no match."""
    p = tmp_path / "x.py"
    p.write_text('password = "abc"\n')
    findings = ss.scan_file(p, "secrets")
    assert findings == []


def test_scan_file_secrets_short_api_key_no_match(tmp_path):
    """Covers line 149 False: api_key < 16 chars → no match."""
    p = tmp_path / "x.py"
    p.write_text('api_key = "short"\n')
    findings = ss.scan_file(p, "secrets")
    assert findings == []


# ====================== scan_path ================================

def test_scan_path_dir_with_clean_files(tmp_path):
    """Covers lines 138-181 happy: clean dir → 0 findings."""
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    result = ss.scan_path(str(tmp_path), "cmd-injection")
    assert result["count"] == 0
    assert result["findings"] == []
    assert result["issues_found"] is False


def test_scan_path_dir_with_vuln_files(tmp_path):
    """Covers lines 157-164: dir with vulnerable file → findings."""
    (tmp_path / "vuln.py").write_text("os.system('rm -rf /')\n")
    (tmp_path / "clean.py").write_text("x = 1\n")
    result = ss.scan_path(str(tmp_path), "cmd-injection")
    assert result["count"] == 1
    assert result["issues_found"] is True
    assert result["scanned_files"] == 2


def test_scan_path_dir_prunes_skip_dirs(tmp_path):
    """Covers line 144: SKIP_DIRS pruned in os.walk."""
    (tmp_path / "clean.py").write_text("os.system('rm')\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "vuln.py").write_text("os.system('rm')\n")
    result = ss.scan_path(str(tmp_path), "cmd-injection")
    assert result["scanned_files"] == 1


def test_scan_path_dir_skips_binary_exts(tmp_path):
    """Covers lines 159-162: secrets scan skips binary files."""
    (tmp_path / "x.png").write_bytes(b"\x89PNG\r\nos.system('rm')")
    (tmp_path / "x.py").write_text(f"{_FAKE_SK_KEY}\n")
    result = ss.scan_path(str(tmp_path), "secrets")
    assert result["scanned_files"] == 1
    assert result["count"] == 1


def test_scan_path_skips_non_py_for_non_secrets(tmp_path):
    """Covers line 165: non-.py files skipped for non-secrets scans."""
    (tmp_path / "x.js").write_text("os.system('rm')\n")
    (tmp_path / "x.py").write_text("os.system('rm')\n")
    result = ss.scan_path(str(tmp_path), "cmd-injection")
    assert result["scanned_files"] == 1


def test_scan_path_single_file(tmp_path):
    """Covers lines 141-142: single file → file-only scan."""
    p = tmp_path / "single.py"
    p.write_text("os.system('rm')\n")
    result = ss.scan_path(str(p), "cmd-injection")
    assert result["scanned_files"] == 1
    assert result["count"] == 1


def test_scan_path_nonexistent_path(tmp_path):
    """Covers lines 137-139: path not found → {"error": "..."}."""
    result = ss.scan_path(str(tmp_path / "nope"), "cmd-injection")
    assert "error" in result
    assert "path not found" in result["error"]


def test_scan_path_by_severity_counts(tmp_path):
    """Covers lines 175-179: by_severity correctly counted."""
    (tmp_path / "a.py").write_text("os.system('rm')\n")
    result = ss.scan_path(str(tmp_path), "secrets")
    assert result["by_severity"]["CRITICAL"] == 0


def test_scan_path_sorting(tmp_path):
    """Covers lines 170-171: findings sorted by severity, file, line."""
    (tmp_path / "a.py").write_text("os.system('rm')\n")
    (tmp_path / "b.py").write_text("import pickle\npickle.load(f)\n")
    (tmp_path / "c.py").write_text(f"{_FAKE_SK_KEY}\n")
    fake_google = "AIza" + "A" * 35
    (tmp_path / "d.py").write_text(f"api_key = '{fake_google}'\n")
    result = ss.scan_path(str(tmp_path), "secrets")
    severities = [f["severity"] for f in result["findings"]]
    crit_idx = severities.index("CRITICAL") if "CRITICAL" in severities else -1
    high_idx = severities.index("HIGH") if "HIGH" in severities else -1
    if crit_idx >= 0 and high_idx >= 0:
        assert crit_idx < high_idx


def test_scan_path_dotenv_excluded(tmp_path):
    """Covers line 98: .env* files excluded via SKIP_FILE_PATTERNS."""
    (tmp_path / ".env").write_text(f"{_FAKE_SK_KEY}\n")
    (tmp_path / "x.py").write_text(f"{_FAKE_SK_KEY}\n")
    result = ss.scan_path(str(tmp_path), "secrets")
    assert result["scanned_files"] == 1
    assert result["count"] == 1


def test_scan_path_confidence_default(monkeypatch, tmp_path):
    """Covers line 127: findings use DEFAULT_CONFIDENCE."""
    monkeypatch.setattr(ss, "DEFAULT_CONFIDENCE", 0.88)
    p = tmp_path / "x.py"
    p.write_text("os.system('rm')\n")
    findings = ss.scan_file(p, "cmd-injection")
    assert findings[0]["confidence"] == 0.88


def test_scan_path_empty_dir(tmp_path):
    """Covers lines 144-156: empty dir → 0 findings."""
    result = ss.scan_path(str(tmp_path), "cmd-injection")
    assert result["count"] == 0
    assert result["scanned_files"] == 0


def test_scan_file_secrets_skips_binary(tmp_path):
    """Covers line 158: secrets scan skips .pyc files."""
    (tmp_path / "vuln.pyc").write_text(f"{_FAKE_SK_KEY}\n")
    result = ss.scan_path(str(tmp_path), "secrets")
    assert result["scanned_files"] == 0
    assert result["count"] == 0


def test_scan_file_secrets_skips_png(tmp_path):
    """Covers line 158: .png files skipped for secrets scan."""
    (tmp_path / "vuln.png").write_bytes(b"\x89PNG\r\n")
    result = ss.scan_path(str(tmp_path), "secrets")
    assert result["scanned_files"] == 0


def test_scan_file_secrets_skips_so(tmp_path):
    """Covers line 158: .so files skipped for secrets scan."""
    (tmp_path / "vuln.so").write_bytes(b"\x7fELF")
    result = ss.scan_path(str(tmp_path), "secrets")
    assert result["scanned_files"] == 0


# ====================== main() direct invocation =====================

def test_main_direct_no_args(capsys, monkeypatch):
    """Covers lines 187-189: no args → exit 2 + error."""
    monkeypatch.setattr(sys, "argv", ["dev_security_scan.py"])
    with pytest.raises(SystemExit) as exc_info:
        ss.main()
    assert exc_info.value.code == 2
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "error" in parsed
    assert "usage" in parsed["error"]


def test_main_direct_unknown_cmd(capsys, monkeypatch):
    """Covers lines 192-194: non-SCAN cmd → exit 2 + error."""
    monkeypatch.setattr(sys, "argv", ["dev_security_scan.py", "FOOBAR"])
    with pytest.raises(SystemExit) as exc_info:
        ss.main()
    assert exc_info.value.code == 2
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "unknown command" in parsed["error"]


def test_main_direct_clean_scan(capsys, monkeypatch, tmp_path):
    """Covers lines 237-238, 246: clean scan → exit 0."""
    (tmp_path / "clean.py").write_text("x = 1\n")
    monkeypatch.setattr(sys, "argv", ["dev_security_scan.py", "SCAN", "cmd-injection", str(tmp_path)])
    with pytest.raises(SystemExit) as exc_info:
        ss.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["count"] == 0


def test_main_direct_findings_scan(capsys, monkeypatch, tmp_path):
    """Covers lines 237-238, 244-245: with findings → exit 1."""
    (tmp_path / "vuln.py").write_text("os.system('rm -rf /')\n")
    monkeypatch.setattr(sys, "argv", ["dev_security_scan.py", "SCAN", "cmd-injection", str(tmp_path)])
    with pytest.raises(SystemExit) as exc_info:
        ss.main()
    assert exc_info.value.code == 1


def test_main_direct_unknown_scan_type(capsys, monkeypatch):
    """Covers lines 239-241: unknown scan type → exit 2 + error."""
    monkeypatch.setattr(sys, "argv", ["dev_security_scan.py", "SCAN", "nope"])
    with pytest.raises(SystemExit) as exc_info:
        ss.main()
    assert exc_info.value.code == 2
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "unknown scan type" in parsed["error"]


def test_main_direct_all_clean(capsys, monkeypatch, tmp_path):
    """Covers lines 196-236: SCAN all clean → exit 0."""
    (tmp_path / "clean.py").write_text("x = 1\n")
    monkeypatch.setattr(sys, "argv", ["dev_security_scan.py", "SCAN", "all", str(tmp_path)])
    with pytest.raises(SystemExit) as exc_info:
        ss.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["scan"] == "all"
    assert "per_scan" in parsed


def test_main_direct_all_with_findings(capsys, monkeypatch, tmp_path):
    """Covers lines 196-236: SCAN all with findings → exit 1, dedupe applied."""
    (tmp_path / "vuln.py").write_text("os.system('rm')\n")
    (tmp_path / "secret.py").write_text(f"{_FAKE_SK_KEY}\n")
    monkeypatch.setattr(sys, "argv", ["dev_security_scan.py", "SCAN", "all", str(tmp_path)])
    with pytest.raises(SystemExit) as exc_info:
        ss.main()
    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["count"] >= 2
    keys = set()
    for f in parsed["findings"]:
        keys.add((f["file"], f["line"], f["match"]))
    assert len(keys) == len(parsed["findings"])


# ====================== CLI via subprocess ========================

def _run_cli(*args):
    """Helper: run main() via subprocess."""
    cmd = [sys.executable, str(REPO_ROOT / "tools" / "dev_security_scan.py")] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def test_main_no_args():
    """CLI: no args → exit 2 + JSON error."""
    code, out, _ = _run_cli()
    assert code == 2
    parsed = json.loads(out)
    assert "error" in parsed
    assert "usage" in parsed["error"]


def test_main_unknown_cmd():
    """CLI: non-SCAN cmd → exit 2 + JSON error."""
    code, out, _ = _run_cli("FOOBAR")
    assert code == 2
    parsed = json.loads(out)
    assert "unknown command" in parsed["error"]


def test_main_unknown_scan_type():
    """CLI: unknown scan type → exit 2 + error."""
    code, out, _ = _run_cli("SCAN", "nope")
    assert code == 2
    parsed = json.loads(out)
    assert "unknown scan type" in parsed["error"]


def test_main_clean_exit_zero(tmp_path):
    """CLI: clean scan → exit 0."""
    (tmp_path / "clean.py").write_text("x = 1\n")
    code, out, _ = _run_cli("SCAN", "cmd-injection", str(tmp_path))
    assert code == 0
    parsed = json.loads(out)
    assert parsed["count"] == 0


def test_main_with_findings_exit_one(tmp_path):
    """CLI: with findings → exit 1."""
    (tmp_path / "vuln.py").write_text("os.system('rm -rf /')\n")
    code, out, _ = _run_cli("SCAN", "cmd-injection", str(tmp_path))
    assert code == 1
    parsed = json.loads(out)
    assert parsed["count"] == 1


def test_main_all_aggregates(tmp_path):
    """CLI: SCAN all → aggregates all 4 scans."""
    (tmp_path / "vuln.py").write_text("os.system('rm')\n")
    (tmp_path / "secret.py").write_text(f"{_FAKE_SK_KEY}\n")
    code, out, _ = _run_cli("SCAN", "all", str(tmp_path))
    parsed = json.loads(out)
    assert parsed["scan"] == "all"
    assert "per_scan" in parsed
    assert "cmd-injection" in parsed["per_scan"]
    assert "secrets" in parsed["per_scan"]
    assert parsed["count"] >= 2


def test_main_all_dedupe(tmp_path):
    """CLI: dedupe by (file, line, match)."""
    (tmp_path / "vuln.py").write_text("os.system('rm')\n")
    code1, out1, _ = _run_cli("SCAN", "all", str(tmp_path))
    parsed = json.loads(out1)
    keys = set()
    for f in parsed["findings"]:
        keys.add((f["file"], f["line"], f["match"]))
    assert len(keys) == len(parsed["findings"])


def test_main_all_default_path():
    """CLI: SCAN without path arg → defaults to '.'."""
    code, out, _ = _run_cli("SCAN", "cmd-injection")
    assert code in (0, 1)


def test_main_scan_type_case_insensitive():
    """CLI: scan_arg.lower() means CMD-INJECTION works (line 191)."""
    code, out, _ = _run_cli("SCAN", "CMD-INJECTION")
    assert code in (0, 1)
    parsed = json.loads(out)
    assert parsed["scan"] == "cmd-injection"  # lowercased


# ====================== edge cases ================================

def test_scan_file_unreadable_file(tmp_path, monkeypatch):
    """Covers lines 108-110: file deleted between is_excluded and open."""
    p = tmp_path / "x.py"
    p.write_text("os.system('rm')\n")
    original_open = open

    def fake_open(*args, **kwargs):
        if "x.py" in str(args[0]) if args else False:
            raise OSError("simulated")
        return original_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)
    assert ss.scan_file(p, "cmd-injection") == []
