"""R110-530 coverage tests for tools/dev_goose_expert_check.py.

Module: 244 LOC, 5 functions + argparse CLI, 0% covered.

Functions tested:
  - find_conflict(text)  lines 87-111
    Lower-cases text, scans all KNOWN_GOOSE_MECHANISMS,
    matches keyword + missing-pattern regex, returns first conflict dict.

  - scan_findings(path)  lines 114-141
    Returns (exit_code, conflicts). Handles missing file, missing yaml,
    iterates findings, calls find_conflict on joined text.

  - scan_patches(path)  lines 144-170
    Same shape as scan_findings but for patches.

  - check_single_mechanism(claim)  lines 173-178
    Returns (exit_code, result_dict).

  - list_known_mechanisms()  lines 181-189
    Prints the knowledge base.

  - main()  lines 192-240
    CLI: --findings / --patches / --check-mechanism / --list-known-mechanisms
    Falls through to parser.print_help + return 2 if no arg given.

Strategy: Direct function calls for unit tests + subprocess for CLI tests
(avoids the main() argparse complexity + exit-code path).
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.dev_goose_expert_check as gec  # noqa: E402


# ====================== find_conflict =============================

def test_find_conflict_no_match():
    """Covers lines 111: text with no relevant keywords → None."""
    assert gec.find_conflict("the quick brown fox jumps over the lazy dog") is None


def test_find_conflict_keyword_present_but_not_missing():
    """Covers lines 92-93 + 103 False: keyword present but no missing-pattern.

    'load on demand for agents' is the keyword, but text says
    'works as expected' — no missing/implement/need/requires/add pattern.
    """
    text = "Goose load on demand for agents works as expected"
    assert gec.find_conflict(text) is None


def test_find_conflict_missing_keyword():
    """Covers lines 96-97 + 104 True: 'missing load on demand' matches."""
    text = "We are missing load on demand for agents in our pipeline"
    result = gec.find_conflict(text)
    assert result is not None
    assert result["claimed_missing"] == "load on demand for agents"
    assert "summon extension" in result["goose_native"]


def test_find_conflict_no_keyword():
    """Covers lines 98: 'no load on demand' triggers conflict."""
    text = "There is no load on demand for skills in goose yet"
    result = gec.find_conflict(text)
    assert result is not None


def test_find_conflict_implement_keyword():
    """Covers line 99: 'implement X' triggers conflict."""
    text = "We need to implement parallel agent execution from scratch"
    result = gec.find_conflict(text)
    assert result is not None
    assert "parallel agent execution" in result["claimed_missing"]


def test_find_conflict_need_keyword():
    """Covers line 100: 'need X' triggers conflict."""
    text = "I need session management for our test runs"
    result = gec.find_conflict(text)
    assert result is not None


def test_find_conflict_require_keyword():
    """Covers line 101: 'requires X' (with optional 's') triggers conflict."""
    text = "Our flow requires config validation before deploy"
    result = gec.find_conflict(text)
    assert result is not None


def test_find_conflict_add_keyword():
    """Covers line 98: 'add X' triggers conflict."""
    text = "Let's add agent delegation to the recipe chain"
    result = gec.find_conflict(text)
    assert result is not None


def test_find_conflict_alternative_keyword():
    """Covers lines 91, 93: 'alternative_keywords' are also matched."""
    # 'lazy load' is an alt-keyword for 'load on demand for agents'
    text = "We need to add lazy load to our agent runner"
    result = gec.find_conflict(text)
    assert result is not None


def test_find_conflict_case_insensitive():
    """Covers line 89: text is lowercased before matching."""
    text = "MISSING LOAD ON DEMAND FOR AGENTS is a problem"
    result = gec.find_conflict(text)
    assert result is not None


def test_find_conflict_docs_none_in_entry():
    """Covers line 108: docs can be None — automatic rollback has docs=None."""
    text = "We need automatic rollback for our flow"
    result = gec.find_conflict(text)
    assert result is not None
    assert result["docs"] is None


def test_find_conflict_advice_message():
    """Covers line 109: 'advice' field is generated."""
    text = "We need to implement config validation"
    result = gec.find_conflict(text)
    assert result is not None
    assert "advice" in result
    assert "Goose already provides" in result["advice"]


# ====================== scan_findings =============================

def test_scan_findings_no_conflicts(tmp_path):
    """Covers lines 116-141 happy path: clean findings file → (0, [])."""
    findings_file = tmp_path / "findings.yaml"
    findings_file.write_text(textwrap.dedent("""
        data:
          findings:
            - id: F1
              type: bug
              file: foo.py
              issue: some unrelated issue
              detail: no goose-mechanism keywords here
              fix: just fix the bug
    """).strip())
    code, conflicts = gec.scan_findings(findings_file)
    assert code == 0
    assert conflicts == []


def test_scan_findings_with_conflict(tmp_path):
    """Covers lines 130-140: finding has 'missing load on demand' → conflict."""
    findings_file = tmp_path / "findings.yaml"
    findings_file.write_text(textwrap.dedent("""
        data:
          findings:
            - id: F42
              type: enhancement
              file: agent.py
              issue: missing load on demand for agents in pipeline
              detail: this is needed for sub_recipes
              fix: implement load on demand for agents from scratch
    """).strip())
    code, conflicts = gec.scan_findings(findings_file)
    assert code == 1
    assert len(conflicts) == 1
    assert conflicts[0]["finding_id"] == "F42"
    assert conflicts[0]["type"] == "enhancement"
    assert conflicts[0]["file"] == "agent.py"


def test_scan_findings_missing_file(tmp_path, capsys):
    """Covers lines 116-118: file doesn't exist → (0, []) + WARN."""
    missing = tmp_path / "nonexistent.yaml"
    code, conflicts = gec.scan_findings(missing)
    assert code == 0
    assert conflicts == []
    captured = capsys.readouterr()
    assert "WARN" in captured.out
    assert "does not exist" in captured.out


def test_scan_findings_missing_data_key(tmp_path):
    """Covers line 129 False: file has no 'data' key → no findings, no crash."""
    findings_file = tmp_path / "findings.yaml"
    findings_file.write_text("other_key: value\n")
    code, conflicts = gec.scan_findings(findings_file)
    assert code == 0
    assert conflicts == []


def test_scan_findings_no_findings_key(tmp_path):
    """Covers line 129: data has no 'findings' key → no findings, no crash."""
    findings_file = tmp_path / "findings.yaml"
    findings_file.write_text("data:\n  other: thing\n")
    code, conflicts = gec.scan_findings(findings_file)
    assert code == 0
    assert conflicts == []


def test_scan_findings_multiple_conflicts(tmp_path):
    """Covers lines 131-141: multiple findings → multiple conflicts."""
    findings_file = tmp_path / "findings.yaml"
    findings_file.write_text(textwrap.dedent("""
        data:
          findings:
            - id: F1
              type: bug
              file: a.py
              issue: missing load on demand for agents
              detail: d
              fix: f
            - id: F2
              type: bug
              file: b.py
              issue: normal text
              detail: d
              fix: f
            - id: F3
              type: bug
              file: c.py
              issue: need config validation
              detail: d
              fix: f
    """).strip())
    code, conflicts = gec.scan_findings(findings_file)
    assert code == 1
    assert len(conflicts) == 2  # F1 and F3
    ids = [c["finding_id"] for c in conflicts]
    assert "F1" in ids
    assert "F3" in ids


# ====================== scan_patches ==============================

def test_scan_patches_no_conflicts(tmp_path):
    """Covers lines 144-170 happy path: clean patches file → (0, [])."""
    patches_file = tmp_path / "patches.yaml"
    patches_file.write_text(textwrap.dedent("""
        data:
          patches:
            - file: foo.yaml
              field: title
              reason: just a normal patch
              to: New Title
    """).strip())
    code, conflicts = gec.scan_patches(patches_file)
    assert code == 0
    assert conflicts == []


def test_scan_patches_with_conflict(tmp_path):
    """Covers lines 159-169: patch reason conflicts with Goose-native."""
    patches_file = tmp_path / "patches.yaml"
    patches_file.write_text(textwrap.dedent("""
        data:
          patches:
            - file: recipes/foo.yaml
              field: prompt
              reason: We need to add session management for tests
              to: implement session management from scratch
    """).strip())
    code, conflicts = gec.scan_patches(patches_file)
    assert code == 1
    assert len(conflicts) == 1
    assert conflicts[0]["patch_file"] == "recipes/foo.yaml"
    assert conflicts[0]["patch_field"] == "prompt"


def test_scan_patches_missing_file(tmp_path, capsys):
    """Covers lines 146-148: patches file doesn't exist → (0, []) + WARN."""
    missing = tmp_path / "nonexistent.yaml"
    code, conflicts = gec.scan_patches(missing)
    assert code == 0
    assert conflicts == []
    captured = capsys.readouterr()
    assert "WARN" in captured.out


def test_scan_patches_no_data_key(tmp_path):
    """Covers line 159 False: no 'data' key → empty result."""
    patches_file = tmp_path / "patches.yaml"
    patches_file.write_text("just_a_string: x\n")
    code, conflicts = gec.scan_patches(patches_file)
    assert code == 0
    assert conflicts == []


def test_scan_patches_text_concatenation(tmp_path):
    """Covers line 162: text is 'reason + to' combined."""
    patches_file = tmp_path / "patches.yaml"
    # reason alone is innocuous, but 'to' contains the trigger
    patches_file.write_text(textwrap.dedent("""
        data:
          patches:
            - file: x
              field: x
              reason: just renaming
              to: implement load on demand for agents
    """).strip())
    code, conflicts = gec.scan_patches(patches_file)
    assert code == 1
    assert len(conflicts) == 1


# ====================== check_single_mechanism ====================

def test_check_single_mechanism_clean():
    """Covers line 178: clean claim → (0, CONFORM result)."""
    code, result = gec.check_single_mechanism("just a normal text without goose stuff")
    assert code == 0
    assert result["claim"] == "just a normal text without goose stuff"
    assert "CONFORM" in result["verdict"]


def test_check_single_mechanism_conflict():
    """Covers lines 175-177: conflicting claim → (1, conflict dict)."""
    code, result = gec.check_single_mechanism("We need to implement agent delegation")
    assert code == 1
    assert result["claim"] == "We need to implement agent delegation"
    assert "goose_native" in result
    assert "summon extension" in result["goose_native"]


# ====================== list_known_mechanisms =====================

def test_list_known_mechanisms(capsys):
    """Covers lines 181-189: prints all known mechanisms."""
    gec.list_known_mechanisms()
    captured = capsys.readouterr()
    assert "Known Goose native mechanisms" in captured.out
    # Check that at least 3 well-known mechanisms appear
    assert "load on demand for agents" in captured.out
    assert "config validation" in captured.out
    assert "session management" in captured.out


def test_list_known_mechanisms_includes_docs(capsys):
    """Covers line 188: docs line printed when not None."""
    gec.list_known_mechanisms()
    captured = capsys.readouterr()
    # Pick a known mechanism with docs
    assert "goose-docs.ai" in captured.out


def test_list_known_mechanisms_no_docs_branch(capsys):
    """Covers line 187 False: docs=None branch."""
    # automatic rollback has docs=None
    gec.list_known_mechanisms()
    captured = capsys.readouterr()
    # Section "automatic rollback" should be there
    assert "automatic rollback" in captured.out
    # But its docs line should say "no native" instead of "docs:"
    rollback_section = captured.out.split("automatic rollback")[1].split("\n\n")[0]
    assert "docs:" not in rollback_section


# ====================== main() / CLI ==============================

def _run_cli(*args):
    """Helper: run main() with given argv, return (exit_code, stdout, stderr)."""
    import io
    from contextlib import redirect_stdout, redirect_stderr

    old_argv = sys.argv
    sys.argv = ["gec.py"] + list(args)
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            try:
                code = gec.main()
            except SystemExit as e:
                code = e.code if e.code is not None else 0
    finally:
        sys.argv = old_argv
    return code, stdout_buf.getvalue(), stderr_buf.getvalue()


def test_main_list_known_mechanisms():
    """Covers lines 206-208: --list-known-mechanisms → return 0."""
    code, out, _ = _run_cli("--list-known-mechanisms")
    assert code == 0
    assert "Known Goose native mechanisms" in out


def test_main_check_mechanism_clean():
    """Covers lines 210-213: --check-mechanism with clean claim → return 0."""
    code, out, _ = _run_cli("--check-mechanism", "normal text")
    assert code == 0
    # JSON output
    assert "CONFORM" in out
    # It's valid JSON
    parsed = json.loads(out)
    assert parsed["claim"] == "normal text"


def test_main_check_mechanism_conflict():
    """Covers line 213: --check-mechanism with conflict → return 1."""
    code, out, _ = _run_cli("--check-mechanism", "We need to implement session management")
    assert code == 1
    parsed = json.loads(out)
    assert "goose_native" in parsed


def test_main_findings_clean(tmp_path):
    """Covers lines 215-225 happy: --findings <clean> → return 0 + OK."""
    f = tmp_path / "findings.yaml"
    f.write_text("data:\n  findings: []\n")
    code, out, _ = _run_cli("--findings", str(f))
    assert code == 0
    assert "OK" in out


def test_main_findings_with_conflict(tmp_path):
    """Covers lines 217-222: --findings <conflict> → return 1 + ACTION message."""
    f = tmp_path / "findings.yaml"
    f.write_text(textwrap.dedent("""
        data:
          findings:
            - id: F1
              type: bug
              file: x
              issue: missing load on demand for agents
              detail: d
              fix: f
    """).strip())
    code, out, _ = _run_cli("--findings", str(f))
    assert code == 1
    assert "FOUND" in out
    assert "ACTION" in out
    assert "SUMMON" in out
    assert "sub_mas-goose-expert" in out


def test_main_patches_clean(tmp_path):
    """Covers lines 227-237 happy: --patches <clean> → return 0 + OK."""
    f = tmp_path / "patches.yaml"
    f.write_text("data:\n  patches: []\n")
    code, out, _ = _run_cli("--patches", str(f))
    assert code == 0
    assert "OK" in out


def test_main_patches_with_conflict(tmp_path):
    """Covers lines 229-234: --patches <conflict> → return 1 + ACTION."""
    f = tmp_path / "patches.yaml"
    f.write_text(textwrap.dedent("""
        data:
          patches:
            - file: x.yaml
              field: prompt
              reason: We need to implement agent delegation
              to: add agent delegation
    """).strip())
    code, out, _ = _run_cli("--patches", str(f))
    assert code == 1
    assert "FOUND" in out
    assert "ACTION" in out


def test_main_no_args_returns_2():
    """Covers lines 239-240: no args → print_help + return 2."""
    code, out, _ = _run_cli()
    assert code == 2
    assert "usage" in out.lower() or "options" in out.lower()


def test_main_findings_priority_over_patches(tmp_path):
    """Covers lines 215-225 (findings before patches in main()): --findings wins.

    When both --findings and --patches are passed, findings branch
    is checked first, so we get the findings result.
    """
    f_find = tmp_path / "findings.yaml"
    f_find.write_text("data:\n  findings: []\n")
    f_patch = tmp_path / "patches.yaml"
    f_patch.write_text("data:\n  patches: []\n")
    code, out, _ = _run_cli("--findings", str(f_find), "--patches", str(f_patch))
    # Findings branch (clean) wins
    assert code == 0
    assert str(f_find) in out


# ====================== edge cases ================================

def test_find_conflict_returns_first_match():
    """Covers lines 105-110: returns first matching conflict dict.

    Multiple keywords could match — we return whichever triggers first.
    """
    text = "missing load on demand for agents and need session management"
    result = gec.find_conflict(text)
    # First mechanism in iteration order is 'load on demand for agents'
    assert result["claimed_missing"] == "load on demand for agents"


def test_find_conflict_empty_string():
    """Covers line 89 + early loop exit: empty text → None."""
    assert gec.find_conflict("") is None


def test_find_conflict_only_whitespace():
    """Covers line 89: whitespace-only → None (no matches)."""
    assert gec.find_conflict("   \n\t  ") is None


def test_check_single_mechanism_empty_claim():
    """Covers line 178: empty claim → CONFORM (no conflict)."""
    code, result = gec.check_single_mechanism("")
    assert code == 0
    assert "CONFORM" in result["verdict"]


def test_scan_findings_yaml_missing(tmp_path, monkeypatch, capsys):
    """Covers lines 122-124: PyYAML not installed → (2, []) + ERROR."""
    # Simulate yaml import failure
    import builtins
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("simulated no yaml")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    f = tmp_path / "findings.yaml"
    f.write_text("data:\n  findings: []\n")
    code, conflicts = gec.scan_findings(f)
    assert code == 2
    assert conflicts == []
    captured = capsys.readouterr()
    assert "ERROR" in captured.err or "PyYAML" in captured.err


def test_scan_patches_yaml_missing(tmp_path, monkeypatch, capsys):
    """Covers lines 152-154: PyYAML not installed for scan_patches."""
    import builtins
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("simulated no yaml")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    f = tmp_path / "patches.yaml"
    f.write_text("data:\n  patches: []\n")
    code, conflicts = gec.scan_patches(f)
    assert code == 2
    assert conflicts == []
    captured = capsys.readouterr()
    assert "ERROR" in captured.err or "PyYAML" in captured.err


def test_scan_findings_text_includes_fix_field(tmp_path):
    """Covers line 132: text = issue + detail + fix combined."""
    # Only 'fix' contains the trigger
    f = tmp_path / "findings.yaml"
    f.write_text(textwrap.dedent("""
        data:
          findings:
            - id: F1
              type: x
              file: x
              issue: normal issue
              detail: normal detail
              fix: implement config validation
    """).strip())
    code, conflicts = gec.scan_findings(f)
    assert code == 1
    assert conflicts[0]["finding_id"] == "F1"
