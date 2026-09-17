"""R110-477 — coverage-push r14: tools/dev_fast_scan.py 94% → 100%

52 stmts. Missed lines: 11 (yaml.safe_load except in scan_prompts),
39 (yaml.safe_load except in scan_settings), 53 (max_turns > 300).

KEY OBSERVATIONS:
- Three pure-function scanners: scan_prompts, scan_settings,
  scan_structure. All read *.yaml under given path recursively.
- scan_prompts scores per-file:
  - s = 10 (start)
  - -2 if no © (\U000000a9) in prompt
  - -2 if no (v1.0.0) in prompt
  - -2 if no NUR keyword
  - -2 if prompt len > 500
  - -1 if prompt len < 30
  - returns (findings, avg_score, count)
  - if no yaml files: returns ([], 0, 0)
  - if NO prompt in file → finding + score=0
- scan_settings (R110-261a fix):
  - timeout in [300,900] is OK
  - max_turns (or max_steps) in [30,300] is OK
  - per-file pass/fail: ok += 1 only if BOTH in range
  - findings list gets separate entries for timeout_ok=False
    and max_turns_ok=False (can produce 2 findings per file)
  - if no yaml files: returns ([], 10, 0)  ← note: 10, not 0
  - cap at 10: min(10.0, round(ok/total*10, 1))
- scan_structure:
  - if no yaml files: returns ([C1 finding], 0, 0)
  - if yaml.safe_load fails: finding + score -= 2
  - if non-dict loaded (e.g. list): skip (continue)
  - if no 'version': score -= 1
  - if no 'instructions': score -= 3
  - returns (findings, max(0,score), len(files))
- __main__ CLI:
  - with --validate: calls scan_structure only, prints
    {valid: score>=5, score:score}
  - default: runs all 3 scans, prints combined JSON

PITFALLS:
- glob uses '**/*.yaml' (recursive=True) — test fixtures MUST
  be real files on disk (tmp_path). Symlinks work too.
- yaml.safe_load with bare except: — invalid YAML is silently
  skipped (continues to next file). Test by writing ':' or
  unbalanced braces.
- scan_settings uses 'max_turns' OR 'max_steps' (key fallback)
- The structure score is a sum across files (not avg), so
  many bad files → negative score → max(0,score) clamps it
"""

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_fast_scan as fs  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def write_yaml(path, content):
    path.write_text(content)


# ─────────────────────────────────────────────────────────────────────
# scan_prompts
# ─────────────────────────────────────────────────────────────────────
class TestScanPrompts:
    def test_no_yaml_files(self, tmp_path):
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert findings == []
        assert score == 0
        assert count == 0

    def test_file_with_no_prompt(self, tmp_path):
        write_yaml(tmp_path / "a.yaml", "version: 1\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert count == 1
        assert score == 0
        assert len(findings) == 1
        assert findings[0]["type"] == "A1"
        assert findings[0]["severity"] == "hoch"
        assert "NO prompt" in findings[0]["detail"]
        assert findings[0]["agent"] == "a.yaml"

    def test_file_with_null_prompt(self, tmp_path):
        write_yaml(tmp_path / "a.yaml", "prompt:\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert count == 1
        assert score == 0  # empty prompt → score=0

    def test_perfect_prompt_score_10(self, tmp_path):
        # Has ©, (v1.0.0), NUR, len 30-500
        prompt = "© 2024 NUR das hier (v1.0.0) und mehr text hier bitte."
        write_yaml(tmp_path / "a.yaml", f"prompt: {prompt}\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert count == 1
        assert score == 10
        assert findings == []

    def test_missing_copyright_dash_2(self, tmp_path):
        # No © → -2 (length kept >= 30 to isolate the -2)
        prompt = "NUR text (v1.0.0) und hier ist mehr text zum fuellen"
        write_yaml(tmp_path / "a.yaml", f"prompt: {prompt}\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert score == 8

    def test_missing_version_dash_2(self, tmp_path):
        # No (v1.0.0) → -2 (length kept >= 30)
        prompt = "© text NUR das hier und mehr text fuellen bitte"
        write_yaml(tmp_path / "a.yaml", f"prompt: {prompt}\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert score == 8

    def test_missing_nur_dash_2(self, tmp_path):
        # No NUR → -2
        prompt = "© text (v1.0.0) und mehr text hier bitte bitte"
        write_yaml(tmp_path / "a.yaml", f"prompt: {prompt}\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert score == 8

    def test_too_long_dash_2(self, tmp_path):
        # len > 500 → -2
        prompt = "© NUR " + "x" * 500 + " (v1.0.0)"
        write_yaml(tmp_path / "a.yaml", f"prompt: {prompt}\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert score == 8

    def test_too_short_dash_1(self, tmp_path):
        # len < 30 → -1
        prompt = "© (v1.0.0) NUR"
        write_yaml(tmp_path / "a.yaml", f"prompt: {prompt}\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert score == 9

    def test_all_missing_score_3(self, tmp_path):
        # Only 'too long' triggers (len > 500 with no keywords)
        # Missing © -2, missing version -2, missing NUR -2,
        # too long -2 → 10-8 = 2
        prompt = "x" * 600
        write_yaml(tmp_path / "a.yaml", f"prompt: {prompt}\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert score == 2

    def test_score_clamped_at_0(self, tmp_path):
        # Empty prompt → already at 0
        write_yaml(tmp_path / "a.yaml", "prompt:\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert score == 0  # clamped via max(0,s)

    def test_invalid_yaml_skipped(self, tmp_path):
        # Malformed YAML → bare except: → continue
        write_yaml(tmp_path / "bad.yaml", ":\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert count == 0  # bad file skipped

    def test_multiple_files_avg(self, tmp_path):
        # File 1: perfect → 10
        # File 2: no © → 8 (length kept >= 30 to avoid length penalty)
        # avg = 9.0
        write_yaml(tmp_path / "a.yaml", "prompt: © NUR text (v1.0.0) mehr text fuellen\n")
        write_yaml(tmp_path / "b.yaml", "prompt: NUR text (v1.0.0) mehr text fuellen\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert count == 2
        assert score == 9.0

    def test_recursive_glob(self, tmp_path):
        (tmp_path / "sub").mkdir()
        write_yaml(tmp_path / "sub" / "deep.yaml", "prompt: © NUR text (v1.0.0) mehr text fuellen\n")
        write_yaml(tmp_path / "shallow.yaml", "prompt: © NUR text (v1.0.0) mehr text fuellen\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert count == 2
        assert score == 10

    def test_score_rounded_to_one_decimal(self, tmp_path):
        # Two files: 10 and 8 → avg = 9.0
        write_yaml(tmp_path / "a.yaml", "prompt: © NUR text (v1.0.0) mehr text fuellen\n")
        write_yaml(tmp_path / "b.yaml", "prompt: NUR text (v1.0.0) mehr text fuellen\n")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        # round(9.0, 1) = 9.0
        assert score == 9.0


# ─────────────────────────────────────────────────────────────────────
# scan_settings
# ─────────────────────────────────────────────────────────────────────
class TestScanSettings:
    def test_no_yaml_files(self, tmp_path):
        findings, score, count = fs.scan_settings(str(tmp_path))
        # No yaml → returns ([], 10, 0) — score 10, NOT 0!
        assert findings == []
        assert score == 10
        assert count == 0

    def test_file_without_settings(self, tmp_path):
        # No 'settings' key → continue (not counted)
        write_yaml(tmp_path / "a.yaml", "version: 1\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert count == 0
        assert score == 10

    def test_perfect_settings(self, tmp_path):
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 600\n  max_turns: 100\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert count == 1
        assert score == 10
        assert findings == []

    def test_perfect_via_max_steps(self, tmp_path):
        # max_steps used when max_turns absent
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 500\n  max_steps: 150\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert count == 1
        assert score == 10

    def test_timeout_too_low_B1(self, tmp_path):
        # timeout < 300 → B1
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 100\n  max_turns: 100\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B1" for f in findings)
        assert any("timeout=100" in f["detail"] for f in findings)
        assert any(f["severity"] == "mittel" for f in findings)

    def test_timeout_too_high_B2(self, tmp_path):
        # timeout > 900 → B2
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 1000\n  max_turns: 100\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B2" for f in findings)
        assert any(f["severity"] == "niedrig" for f in findings)

    def test_max_turns_too_low_B3(self, tmp_path):
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 600\n  max_turns: 10\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B3" for f in findings)

    def test_max_turns_too_high_B4(self, tmp_path):
        # max_turns > 300 → B4 (line 53 was missed in coverage!)
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 600\n  max_turns: 400\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B4" for f in findings)
        assert any("max_turns=400" in f["detail"] for f in findings)

    def test_max_steps_too_high_B4(self, tmp_path):
        # max_steps > 300 → B4
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 600\n  max_steps: 500\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B4" for f in findings)

    def test_both_bad_two_findings(self, tmp_path):
        # Both timeout and max_turns bad → 2 findings
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 100\n  max_turns: 10\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        types = [f["type"] for f in findings]
        assert "B1" in types
        assert "B3" in types

    def test_score_zero_when_all_bad(self, tmp_path):
        # ok=0/total=1 → score = 0
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 100\n  max_turns: 10\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert score == 0

    def test_partial_score(self, tmp_path):
        # 1 good, 1 bad → ok=1, total=2 → score = 5.0
        write_yaml(tmp_path / "good.yaml", "settings:\n  timeout: 600\n  max_turns: 100\n")
        write_yaml(tmp_path / "bad.yaml", "settings:\n  timeout: 100\n  max_turns: 100\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert count == 2
        assert score == 5.0

    def test_score_capped_at_10(self, tmp_path):
        # 5 good, 0 bad → ok=5, total=5 → 5/5*10 = 10.0 (already capped)
        for i in range(5):
            write_yaml(tmp_path / f"g{i}.yaml", "settings:\n  timeout: 600\n  max_turns: 100\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert count == 5
        assert score == 10

    def test_invalid_yaml_skipped(self, tmp_path):
        # Bad YAML → continue
        write_yaml(tmp_path / "bad.yaml", ":\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert count == 0

    def test_max_turns_preferred_over_max_steps(self, tmp_path):
        # Both present → max_turns used (max_steps fallback skipped)
        write_yaml(tmp_path / "a.yaml", "settings:\n  timeout: 600\n  max_turns: 100\n  max_steps: 500\n")
        findings, score, count = fs.scan_settings(str(tmp_path))
        assert count == 1
        assert score == 10  # max_turns=100 is OK


# ─────────────────────────────────────────────────────────────────────
# scan_structure
# ─────────────────────────────────────────────────────────────────────
class TestScanStructure:
    def test_no_yaml_files(self, tmp_path):
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C1" for f in findings)
        assert any("NOE YAMLs" in f["detail"] for f in findings)
        assert score == 0
        assert count == 0

    def test_perfect_structure(self, tmp_path):
        write_yaml(tmp_path / "a.yaml", "version: 1\ninstructions: do stuff\n")
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert count == 1
        assert score == 10
        assert findings == []

    def test_missing_version_C3(self, tmp_path):
        write_yaml(tmp_path / "a.yaml", "instructions: do stuff\n")
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C3" for f in findings)
        assert any("NO version" in f["detail"] for f in findings)
        assert score == 9

    def test_missing_instructions_C4(self, tmp_path):
        write_yaml(tmp_path / "a.yaml", "version: 1\n")
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C4" for f in findings)
        assert any("NOE instructions" in f["detail"] for f in findings)
        assert score == 7  # -3

    def test_missing_both(self, tmp_path):
        write_yaml(tmp_path / "a.yaml", "random: stuff\n")
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C3" for f in findings)
        assert any(f["type"] == "C4" for f in findings)
        assert score == 6  # -1 -3

    def test_invalid_yaml_C2(self, tmp_path):
        write_yaml(tmp_path / "bad.yaml", ":\n")
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C2" for f in findings)
        assert any("YAML-Error" in f["detail"] for f in findings)
        assert any(f["severity"] == "hoch" for f in findings)
        # -2 for YAML error

    def test_score_clamped_at_0(self, tmp_path):
        # 10 invalid yamls → score = 10 - 20 = -10 → max(0,-10) = 0
        for i in range(10):
            write_yaml(tmp_path / f"b{i}.yaml", ":\n")
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert score == 0

    def test_non_dict_yaml_skipped(self, tmp_path):
        # YAML loads as a list, not dict → continue (not counted as missing)
        write_yaml(tmp_path / "list.yaml", "- item1\n- item2\n")
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert count == 1
        # Non-dict skipped → no version/instructions check
        assert findings == []
        assert score == 10


# ─────────────────────────────────────────────────────────────────────
# __main__ CLI
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_main_default_cwd(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["dev_fast_scan.py"])
        import runpy
        try:
            runpy.run_path("tools/dev_fast_scan.py", run_name="__main__")
        except SystemExit:
            pass
        out = capsys.readouterr().out
        # Should print combined JSON
        parsed = json.loads(out)
        assert "findings" in parsed
        assert "scores" in parsed
        assert "prompt" in parsed["scores"]
        assert "settings" in parsed["scores"]
        assert "structure" in parsed["scores"]
        assert "structure_score" in parsed

    def test_main_with_path(self, monkeypatch, capsys, tmp_path):
        write_yaml(tmp_path / "a.yaml", "version: 1\ninstructions: x\nsettings:\n  timeout: 600\n  max_turns: 100\nprompt: © NUR text (v1.0.0) more text here\n")
        monkeypatch.setattr(sys, "argv", ["dev_fast_scan.py", str(tmp_path)])
        import runpy
        try:
            runpy.run_path("tools/dev_fast_scan.py", run_name="__main__")
        except SystemExit:
            pass
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["scores"]["prompt"] == 10
        assert parsed["scores"]["settings"] == 10
        assert parsed["scores"]["structure"] == 10

    def test_main_validate_flag(self, monkeypatch, capsys, tmp_path):
        # --validate → scan_structure only, prints {valid, score}
        write_yaml(tmp_path / "a.yaml", "version: 1\ninstructions: x\n")
        monkeypatch.setattr(sys, "argv", ["dev_fast_scan.py", str(tmp_path), "--validate"])
        import runpy
        try:
            runpy.run_path("tools/dev_fast_scan.py", run_name="__main__")
        except SystemExit:
            pass
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "valid" in parsed
        assert "score" in parsed
        assert parsed["valid"] is True
        assert parsed["score"] == 10

    def test_main_validate_low_score(self, monkeypatch, capsys, tmp_path):
        # No YAMLs → structure score 0 → valid: False
        monkeypatch.setattr(sys, "argv", ["dev_fast_scan.py", str(tmp_path), "--validate"])
        import runpy
        try:
            runpy.run_path("tools/dev_fast_scan.py", run_name="__main__")
        except SystemExit:
            pass
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["valid"] is False
        assert parsed["score"] == 0
