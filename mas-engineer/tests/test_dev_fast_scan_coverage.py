"""Targeted coverage push for tools/dev_fast_scan.py — R110-524.

Module: 89 lines, ~63 stmts, ~18 branches. Goal: 100% line+branch.

Strategy (R110-521-523 lessons applied):
  - Pure functions scan_prompts/scan_settings/scan_structure →
    direct calls against tmp dirs with crafted YAMLs.
  - __main__: subprocess (no argparse, just sys.argv slicing —
    runpy would also work but subprocess is simpler here).

Coverage plan:

  scan_prompts (line 6-27):
    - empty dir → score=0, count=0 (line 27 True branch)
    - file with empty prompt → A1 finding + score=0 (line 17-19)
    - file with empty yaml (0-byte) → skipped (line 14-15)
    - file with invalid yaml → skipped via except (line 11)
    - file with all-good prompt → score=10 (line 26)
    - file missing emoji, version, NUR, long, short → score=1 (lines
      21-25 all True branches)
    - file with version missing → score=8 (line 22 True)
    - file with NUR missing → score=8 (line 23 True)
    - file with len>500 → score=8 (line 24 True)
    - file with len<30 → score=9 (line 25 True)
    - file with `or ''` fallback when d.get('prompt') is None → A1

  scan_settings (line 29-65):
    - empty dir → score=10 (line 65 True branch: `total else 10`)
    - file with no settings → skipped (line 49)
    - file with timeout<300 → B1 finding
    - file with timeout>900 → B2 finding
    - file with max_turns<30 → B3 finding
    - file with max_turns>300 → B4 finding
    - file with both ok → ok+=1
    - file with max_steps fallback (line 51: max_turns gets max_steps)
    - file with empty yaml → skipped (line 46-47)
    - file with invalid yaml → skipped via except (line 43)

  scan_structure (line 67-78):
    - empty dir → C1 finding + score=0 + count=0 (line 70)
    - file with invalid yaml → C2 finding + score-=2 (line 74)
    - file with no version → C3 finding + score-=1 (line 76)
    - file with no instructions → C4 finding + score-=3 (line 77)
    - file with all required → no findings
    - file with empty yaml → skipped via isinstance check (line 75)

  __main__ (line 80-89):
    - with arg → JSON output of all scans (line 85-89)
    - with arg + --validate → JSON {valid, score} (line 82-84)
    - without arg → default path = os.getcwd() (line 81 True branch)
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import tools.dev_fast_scan as fs


REPO_ROOT = Path(__file__).parent.parent.resolve()


# ─── scan_prompts ────────────────────────────────────────────────

def _write(path, content):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_scan_prompts_empty_dir():
    """Covers line 27 True branch: empty scores → score=0."""
    with tempfile.TemporaryDirectory() as tmp:
        findings, score, count = fs.scan_prompts(tmp)
    assert findings == []
    assert score == 0
    assert count == 0


def test_scan_prompts_no_prompt_finding():
    """Covers line 17-19: p empty (None or '') → A1 finding + score=0."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml", "version: 1\ninstructions: y\n")
        findings, score, count = fs.scan_prompts(tmp)
    assert len(findings) == 1
    assert findings[0]["type"] == "A1"
    assert findings[0]["agent"] == "x.yaml"
    assert findings[0]["severity"] == "hoch"
    assert score == 0
    assert count == 1


def test_scan_prompts_prompt_none_uses_fallback():
    """Covers line 16: d.get('prompt', '') or '' — when prompt=None,
    the `or ''` makes p truthy-falsy empty."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml", "version: 1\ninstructions: y\nprompt: null\n")
        findings, score, count = fs.scan_prompts(tmp)
    assert findings[0]["type"] == "A1"
    assert score == 0


def test_scan_prompts_perfect_prompt_score_10():
    """Covers line 26: full-pass → max(0, 10)."""
    with tempfile.TemporaryDirectory() as tmp:
        # Has ©, (v1.0.0), NUR, len between 30-500
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR do the test task'\n")
        findings, score, count = fs.scan_prompts(tmp)
    assert findings == []
    assert score == 10
    assert count == 1


def test_scan_prompts_missing_emoji():
    """Covers line 21 True: '\U000000a9' not in p → s -= 2."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nprompt: 'plain (v1.0.0) NUR do the test task here'\n")
        _, score, _ = fs.scan_prompts(tmp)
    # 10 - 2 = 8
    assert score == 8


def test_scan_prompts_missing_version_tag():
    """Covers line 22 True: '(v1.0.0)' not in p → s -= 2."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nprompt: '© plain NUR do the test task here'\n")
        _, score, _ = fs.scan_prompts(tmp)
    assert score == 8


def test_scan_prompts_missing_nur():
    """Covers line 23 True: 'NUR' not in p → s -= 2."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) plain do the test task here'\n")
        _, score, _ = fs.scan_prompts(tmp)
    assert score == 8


def test_scan_prompts_long_prompt():
    """Covers line 24 True: len(p) > 500 → s -= 2."""
    with tempfile.TemporaryDirectory() as tmp:
        long_p = "x" * 600
        _write(Path(tmp) / "x.yaml",
               f"version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR {long_p}'\n")
        _, score, _ = fs.scan_prompts(tmp)
    assert score == 8


def test_scan_prompts_short_prompt():
    """Covers line 25 True: len(p) < 30 → s -= 1."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR x'\n")
        _, score, _ = fs.scan_prompts(tmp)
    # 10 - 1 = 9 (len is 17 < 30)
    assert score == 9


def test_scan_prompts_skips_invalid_yaml():
    """Covers line 11: except → continue."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "bad.yaml", "invalid: : : yaml\n")
        _write(Path(tmp) / "good.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR do the test task'\n")
        findings, score, count = fs.scan_prompts(tmp)
    assert count == 1
    assert all(f["type"] != "A1" for f in findings)


def test_scan_prompts_skips_empty_yaml():
    """Covers line 14-15: not isinstance(d, dict) → skip (R110-491)."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "empty.yaml", "")  # 0-byte
        findings, score, count = fs.scan_prompts(tmp)
    assert count == 0
    assert findings == []


def test_scan_prompts_avg_calculation():
    """Covers line 27: round(sum/count, 1)."""
    with tempfile.TemporaryDirectory() as tmp:
        # 2 files: one perfect (10), one with no prompt (0)
        _write(Path(tmp) / "a.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR do the test task'\n")
        _write(Path(tmp) / "b.yaml", "version: 1\ninstructions: y\n")
        findings, score, count = fs.scan_prompts(tmp)
    # avg = (10+0)/2 = 5.0
    assert score == 5.0
    assert count == 2


def test_scan_prompts_all_conditions_fail():
    """Covers all 5 conditions on lines 21-25 failing → s=10-2-2-2-2-1=1."""
    with tempfile.TemporaryDirectory() as tmp:
        # len=600, no emoji, no version, no NUR (also len>500 already)
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nprompt: '" + "x" * 600 + "'\n")
        _, score, _ = fs.scan_prompts(tmp)
    # 10 - 2 (no emoji) - 2 (no version) - 2 (no NUR) - 2 (len>500) - 1 (no, len>500 not <30) = 2
    # Actually len>500 makes s-=2 (line 24); len<30 doesn't apply.
    # Score = 10 - 2 - 2 - 2 - 2 = 2
    assert score == 2


# ─── scan_settings ───────────────────────────────────────────────

def test_scan_settings_empty_dir_returns_10():
    """Covers line 65 True branch: total=0 → score=10."""
    with tempfile.TemporaryDirectory() as tmp:
        findings, score, count = fs.scan_settings(tmp)
    assert findings == []
    assert score == 10
    assert count == 0


def test_scan_settings_no_settings_skipped():
    """Covers line 49 True: not s → continue (no total++)."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml", "version: 1\ninstructions: y\n")
        findings, score, count = fs.scan_settings(tmp)
    assert findings == []
    assert count == 0


def test_scan_settings_timeout_too_low():
    """Covers line 56-57 True: t < 300 → B1 finding."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 100, max_turns: 100}\n")
        findings, _, count = fs.scan_settings(tmp)
    assert any(f["type"] == "B1" for f in findings)
    assert count == 1


def test_scan_settings_timeout_too_high():
    """Covers line 58 True: t > 900 → B2 finding."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 1000, max_turns: 100}\n")
        findings, _, _ = fs.scan_settings(tmp)
    assert any(f["type"] == "B2" for f in findings)


def test_scan_settings_max_turns_too_low():
    """Covers line 59-60 True: m < 30 → B3 finding."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 600, max_turns: 10}\n")
        findings, _, _ = fs.scan_settings(tmp)
    assert any(f["type"] == "B3" for f in findings)


def test_scan_settings_max_turns_too_high():
    """Covers line 61 True: m > 300 → B4 finding."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 600, max_turns: 500}\n")
        findings, _, _ = fs.scan_settings(tmp)
    assert any(f["type"] == "B4" for f in findings)


def test_scan_settings_max_steps_fallback():
    """Covers line 51: max_turns falls back to max_steps."""
    with tempfile.TemporaryDirectory() as tmp:
        # Use max_steps=100 (in range), no max_turns
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 600, max_steps: 100}\n")
        findings, score, count = fs.scan_settings(tmp)
    assert count == 1
    # Both conditions pass → score=10 (1/1*10)
    assert score == 10
    assert findings == []


def test_scan_settings_both_ok_increments():
    """Covers line 62-63: both ok → ok += 1."""
    with tempfile.TemporaryDirectory() as tmp:
        # 2 good files, 1 bad
        _write(Path(tmp) / "a.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 600, max_turns: 100}\n")
        _write(Path(tmp) / "b.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 600, max_turns: 100}\n")
        _write(Path(tmp) / "c.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 100, max_turns: 100}\n")
        findings, score, count = fs.scan_settings(tmp)
    # 2 ok / 3 total = 0.667 * 10 = 6.7
    assert score == 6.7
    assert count == 3


def test_scan_settings_skips_invalid_yaml():
    """Covers line 43: except → continue."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "bad.yaml", "invalid: : : yaml\n")
        _write(Path(tmp) / "good.yaml",
               "version: 1\ninstructions: y\nsettings: {timeout: 600, max_turns: 100}\n")
        _, score, count = fs.scan_settings(tmp)
    assert count == 1
    assert score == 10


def test_scan_settings_skips_empty_yaml():
    """Covers line 46-47: not isinstance(d, dict) → continue."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "empty.yaml", "")
        _, _, count = fs.scan_settings(tmp)
    assert count == 0


def test_scan_settings_capped_at_10():
    """Covers line 65: min(10.0, round(ok/total*10, 1)) caps."""
    with tempfile.TemporaryDirectory() as tmp:
        # 5 good files → 5/5*10 = 10
        for i in range(5):
            _write(Path(tmp) / f"a{i}.yaml",
                   "version: 1\ninstructions: y\nsettings: {timeout: 600, max_turns: 100}\n")
        _, score, _ = fs.scan_settings(tmp)
    assert score == 10


# ─── scan_structure ──────────────────────────────────────────────

def test_scan_structure_empty_dir():
    """Covers line 70: no files → C1 finding + score=0."""
    with tempfile.TemporaryDirectory() as tmp:
        findings, score, count = fs.scan_structure(tmp)
    assert len(findings) == 1
    assert findings[0]["type"] == "C1"
    assert score == 0
    assert count == 0


def test_scan_structure_all_good():
    """Covers line 76-77 False branches (no findings)."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml", "version: 1\ninstructions: y\n")
        findings, score, count = fs.scan_structure(tmp)
    assert findings == []
    assert score == 10
    assert count == 1


def test_scan_structure_invalid_yaml():
    """Covers line 73-74: yaml error → C2 finding + score-=2."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "bad.yaml", "invalid: : : yaml\n")
        findings, score, count = fs.scan_structure(tmp)
    assert any(f["type"] == "C2" for f in findings)
    assert score == 8
    assert count == 1


def test_scan_structure_missing_version():
    """Covers line 76 True: 'version' not in d → C3 finding + score-=1."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml", "instructions: y\n")
        findings, score, _ = fs.scan_structure(tmp)
    assert any(f["type"] == "C3" for f in findings)
    assert score == 9


def test_scan_structure_missing_instructions():
    """Covers line 77 True: 'instructions' not in d → C4 + score-=3."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml", "version: 1\n")
        findings, score, _ = fs.scan_structure(tmp)
    assert any(f["type"] == "C4" for f in findings)
    assert score == 7


def test_scan_structure_missing_both():
    """Covers both line 76 + 77 True: score-=4."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml", "other: 1\n")
        findings, score, _ = fs.scan_structure(tmp)
    assert any(f["type"] == "C3" for f in findings)
    assert any(f["type"] == "C4" for f in findings)
    assert score == 6


def test_scan_structure_skips_empty_yaml():
    """Covers line 75 True: not isinstance(d, dict) → continue."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "empty.yaml", "")
        findings, score, count = fs.scan_structure(tmp)
    assert findings == []
    assert score == 10
    assert count == 1  # file still listed (line 69)


def test_scan_structure_score_capped_at_zero():
    """Covers line 78: max(0, score)."""
    with tempfile.TemporaryDirectory() as tmp:
        # 5 invalid files: score = 10 - 2*5 = 0
        for i in range(5):
            _write(Path(tmp) / f"b{i}.yaml", "invalid: : : yaml\n")
        _, score, _ = fs.scan_structure(tmp)
    assert score == 0


# ─── __main__ ────────────────────────────────────────────────────

def test_main_no_arg_uses_cwd():
    """Covers line 81 True branch: len(sys.argv)==1 → use os.getcwd().

    R110-566 fix: explicitly `os.chdir(tmp)` so the scan reads from tmp,
    NOT from whatever cwd some other test left behind via monkeypatch.chdir.
    Also pop the module from sys.modules before re-running via runpy to
    silence the RuntimeWarning + prevent stale-module state pollution.
    """
    import runpy
    import io
    from contextlib import redirect_stdout
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR do the test task here'\nsettings: {timeout: 600, max_turns: 100}\n")
        old_cwd = os.getcwd()
        old_argv = sys.argv
        old_modules = sys.modules.pop("tools.dev_fast_scan", None)
        try:
            os.chdir(tmp)
            sys.argv = ["dev_fast_scan.py"]  # len==1
            buf = io.StringIO()
            with redirect_stdout(buf):
                runpy.run_module("tools.dev_fast_scan", run_name="__main__")
            data = json.loads(buf.getvalue())
        finally:
            sys.argv = old_argv
            os.chdir(old_cwd)
            if old_modules is not None:
                sys.modules["tools.dev_fast_scan"] = old_modules
    assert "findings" in data
    assert "scores" in data


def test_main_with_path_arg():
    """Covers line 81 False branch: sys.argv[1] used as path.

    R110-566-extra: pop sys.modules entry before runpy to silence
    RuntimeWarning ('module found in sys.modules after import').
    """
    import runpy
    import io
    from contextlib import redirect_stdout
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR do the test task here'\nsettings: {timeout: 600, max_turns: 100}\n")
        old_argv = sys.argv
        old_modules = sys.modules.pop("tools.dev_fast_scan", None)
        try:
            sys.argv = ["dev_fast_scan.py", tmp]
            buf = io.StringIO()
            with redirect_stdout(buf):
                runpy.run_module("tools.dev_fast_scan", run_name="__main__")
            data = json.loads(buf.getvalue())
        finally:
            sys.argv = old_argv
            if old_modules is not None:
                sys.modules["tools.dev_fast_scan"] = old_modules
    assert data["agents_scanned"] == 1


def test_main_with_validate_flag():
    """Covers line 82-84: --validate → sys.exit(0) with valid+score.

    R110-566-extra: pop sys.modules entry before runpy.
    """
    import runpy
    import io
    from contextlib import redirect_stdout
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "x.yaml", "version: 1\ninstructions: y\n")
        old_argv = sys.argv
        old_modules = sys.modules.pop("tools.dev_fast_scan", None)
        try:
            sys.argv = ["dev_fast_scan.py", tmp, "--validate"]
            buf = io.StringIO()
            with redirect_stdout(buf):
                with pytest.raises(SystemExit) as exc:
                    runpy.run_module("tools.dev_fast_scan", run_name="__main__")
            assert exc.value.code == 0
            data = json.loads(buf.getvalue())
        finally:
            sys.argv = old_argv
            if old_modules is not None:
                sys.modules["tools.dev_fast_scan"] = old_modules
    assert "valid" in data
    assert "score" in data
    assert data["valid"] is True
    assert data["score"] == 10


def test_main_aggregate_scores():
    """Covers line 86-88: aggregate JSON with structure_score, scan_duration.

    R110-566-extra: pop sys.modules entry before runpy.
    """
    import runpy
    import io
    from contextlib import redirect_stdout
    with tempfile.TemporaryDirectory() as tmp:
        _write(Path(tmp) / "a.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR do the test task here'\nsettings: {timeout: 600, max_turns: 100}\n")
        _write(Path(tmp) / "b.yaml", "version: 1\ninstructions: y\n")  # no prompt
        old_argv = sys.argv
        old_modules = sys.modules.pop("tools.dev_fast_scan", None)
        try:
            sys.argv = ["dev_fast_scan.py", tmp]
            buf = io.StringIO()
            with redirect_stdout(buf):
                runpy.run_module("tools.dev_fast_scan", run_name="__main__")
            data = json.loads(buf.getvalue())
        finally:
            sys.argv = old_argv
            if old_modules is not None:
                sys.modules["tools.dev_fast_scan"] = old_modules
    assert "structure_score" in data
    assert "scan_duration" in data
    # structure_score = avg of (10, 10, 10) = 10
    # scan_duration = count of findings
    assert data["scan_duration"] >= 1
    assert data["agents_scanned"] == 2


def test_main_dunder_name_guard():
    """Covers line 80: __main__ guard via import."""
    import importlib
    importlib.reload(fs)
    assert hasattr(fs, "scan_prompts")


# ─── cross-cutting ───────────────────────────────────────────────

def test_nested_yaml_discovery():
    """Covers recursive=True glob behavior at lines 8, 40, 69."""
    with tempfile.TemporaryDirectory() as tmp:
        nested = Path(tmp) / "deep" / "nested"
        nested.mkdir(parents=True)
        _write(nested / "deep.yaml",
               "version: 1\ninstructions: y\nprompt: '© (v1.0.0) NUR do the test task'\n")
        _, _, count = fs.scan_prompts(tmp)
    assert count == 1
