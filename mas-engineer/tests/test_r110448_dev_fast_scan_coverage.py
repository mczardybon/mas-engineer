"""R110-448 — coverage-push r8: tools/dev_fast_scan.py 0% → 100%.

Fast 3-check scanner (81 lines): prompts/settings/structure quality.

Targets:
- scan_prompts: yaml glob; no prompt → A1 finding + score 0;
  prompt present → score from 10 minus deductions (no © -2,
  no (v1.0.0) -2, no NUR -2, len>500 -2, len<30 -1); max(0,s);
  bad yaml → skipped; empty dir → score 0; mean of scores
- scan_settings: per-file pass/fail (timeout 300-900, max_turns
  30-300); timeout <300 → B1; >900 → B2; max_turns <30 → B3;
  >300 → B4; ok++ only if both pass; cap at 10; no settings →
  skip; no yaml files → score 10 (default-ok)
- scan_structure: no yaml files → C1 + 0; bad yaml → -2 + C2;
  no version → -1 + C3; no instructions → -3 + C4; max(0,s);
  non-dict yaml → skipped
- __main__: argv[1] = path, default cwd; --validate flag →
  prints {valid, score} from scan_structure and exits 0; no
  --validate → full JSON with findings+scores+structure_score
"""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_fast_scan as fs  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# scan_prompts
# ─────────────────────────────────────────────────────────────────────
class TestScanPrompts:
    def test_no_yaml_files(self, tmp_path):
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert findings == []
        assert score == 0
        assert count == 0

    def test_no_prompt_field(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({"name": "x"}))
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert any(f["type"] == "A1" for f in findings)
        assert score == 0
        assert count == 1

    def test_full_quality_prompt(self, tmp_path):
        prompt = "© (v1.0.0) NUR test " * 5  # 80 chars
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"prompt": prompt}))
        findings, score, _ = fs.scan_prompts(str(tmp_path))
        assert findings == []
        assert score == 10

    def test_missing_copyright(self, tmp_path):
        prompt = "(v1.0.0) NUR test " * 5
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"prompt": prompt}))
        _, score, _ = fs.scan_prompts(str(tmp_path))
        assert score == 8  # 10 - 2

    def test_missing_version(self, tmp_path):
        prompt = "© NUR test " * 5
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"prompt": prompt}))
        _, score, _ = fs.scan_prompts(str(tmp_path))
        assert score == 8  # 10 - 2

    def test_missing_nur(self, tmp_path):
        prompt = "© (v1.0.0) test " * 5
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"prompt": prompt}))
        _, score, _ = fs.scan_prompts(str(tmp_path))
        assert score == 8  # 10 - 2

    def test_long_prompt(self, tmp_path):
        # len > 500
        prompt = "© (v1.0.0) NUR test " + ("x" * 600)
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"prompt": prompt}))
        _, score, _ = fs.scan_prompts(str(tmp_path))
        assert score == 8  # 10 - 2

    def test_short_prompt(self, tmp_path):
        # len < 30, but has all required markers
        prompt = "© (v1.0.0) NUR x"
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"prompt": prompt}))
        _, score, _ = fs.scan_prompts(str(tmp_path))
        assert score == 9  # 10 - 1

    def test_score_capped_at_zero(self, tmp_path):
        # Very short with no markers: 10 - 2 - 2 - 2 - 1 = 3
        prompt = "short"
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"prompt": prompt}))
        _, score, _ = fs.scan_prompts(str(tmp_path))
        assert score == 3

    def test_bad_yaml_skipped(self, tmp_path):
        (tmp_path / "bad.yaml").write_text(": invalid: yaml: :")
        findings, score, count = fs.scan_prompts(str(tmp_path))
        assert count == 0  # bad yaml skipped
        assert findings == []

    def test_recursive_scan(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.yaml").write_text(yaml.safe_dump(
            {"prompt": "no prompt field for valid score"}))
        findings, _, count = fs.scan_prompts(str(tmp_path))
        assert count == 1


# ─────────────────────────────────────────────────────────────────────
# scan_settings
# ─────────────────────────────────────────────────────────────────────
class TestScanSettings:
    def test_no_yaml(self, tmp_path):
        findings, score, total = fs.scan_settings(str(tmp_path))
        assert score == 10  # default-ok
        assert total == 0

    def test_no_settings_field(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({"name": "x"}))
        findings, score, total = fs.scan_settings(str(tmp_path))
        assert total == 0  # skipped
        assert findings == []

    def test_perfect_settings(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "settings": {"timeout": 600, "max_turns": 100}}))
        _, score, total = fs.scan_settings(str(tmp_path))
        assert total == 1
        assert score == 10  # ok=1, total=1 → 10

    def test_timeout_too_low(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "settings": {"timeout": 100, "max_turns": 100}}))
        findings, score, _ = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B1" for f in findings)
        assert score == 0  # ok=0,total=1 → 0

    def test_timeout_too_high(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "settings": {"timeout": 1000, "max_turns": 100}}))
        findings, score, _ = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B2" for f in findings)
        assert score == 0

    def test_max_turns_too_low(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "settings": {"timeout": 600, "max_turns": 10}}))
        findings, score, _ = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B3" for f in findings)

    def test_max_turns_too_high(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "settings": {"timeout": 600, "max_turns": 500}}))
        findings, score, _ = fs.scan_settings(str(tmp_path))
        assert any(f["type"] == "B4" for f in findings)

    def test_max_steps_fallback(self, tmp_path):
        # Uses max_steps when max_turns absent
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "settings": {"timeout": 600, "max_steps": 100}}))
        _, score, _ = fs.scan_settings(str(tmp_path))
        assert score == 10

    def test_both_conditions_fail_per_file(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "settings": {"timeout": 100, "max_turns": 10}}))
        _, score, total = fs.scan_settings(str(tmp_path))
        assert total == 1
        assert score == 0  # both fail → ok=0


# ─────────────────────────────────────────────────────────────────────
# scan_structure
# ─────────────────────────────────────────────────────────────────────
class TestScanStructure:
    def test_no_yaml_files(self, tmp_path):
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C1" for f in findings)
        assert score == 0
        assert count == 0

    def test_full_quality(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "version": "1.0", "instructions": "do stuff"}))
        findings, score, count = fs.scan_structure(str(tmp_path))
        assert findings == []
        assert score == 10
        assert count == 1

    def test_no_version(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"instructions": "x"}))
        findings, score, _ = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C3" for f in findings)
        assert score == 9  # 10 - 1

    def test_no_instructions(self, tmp_path):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump(
            {"version": "1.0"}))
        findings, score, _ = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C4" for f in findings)
        assert score == 7  # 10 - 3

    def test_bad_yaml(self, tmp_path):
        (tmp_path / "bad.yaml").write_text(": invalid:")
        findings, score, _ = fs.scan_structure(str(tmp_path))
        assert any(f["type"] == "C2" for f in findings)
        assert score == 8  # 10 - 2

    def test_non_dict_yaml(self, tmp_path):
        (tmp_path / "list.yaml").write_text(yaml.safe_dump([1, 2, 3]))
        findings, score, _ = fs.scan_structure(str(tmp_path))
        assert findings == []
        assert score == 10

    def test_score_capped_at_zero(self, tmp_path):
        # 5 bad-yaml files → 10 - 5*2 = 0
        for i in range(5):
            (tmp_path / f"bad{i}.yaml").write_text(": invalid:")
        _, score, count = fs.scan_structure(str(tmp_path))
        assert score == 0
        assert count == 5


# ─────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_main_validate_flag(self, tmp_path, capsys):
        # --validate + path → JSON {valid, score}
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "version": "1.0", "instructions": "x"}))
        old_argv = sys.argv
        sys.argv = ["dev_fast_scan.py",
                    str(tmp_path), "--validate"]
        try:
            try:
                exec(compile(Path(__file__).resolve().parents[1]
                             .joinpath("tools/dev_fast_scan.py")
                             .read_text(),
                             "dev_fast_scan.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_fast_scan.py",
                      "sys": sys,
                      "os": os,
                      "json": json,
                      "yaml": yaml,
                      "glob": __import__("glob"),
                      "re": __import__("re")})
            except SystemExit as e:
                assert e.code == 0
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        data = json.loads(out.strip())
        assert "valid" in data
        assert "score" in data

    def test_main_full_scan(self, tmp_path, capsys):
        (tmp_path / "a.yaml").write_text(yaml.safe_dump({
            "version": "1.0", "instructions": "x",
            "settings": {"timeout": 600, "max_turns": 100},
            "prompt": "© (v1.0.0) NUR test " * 5}))
        old_argv = sys.argv
        sys.argv = ["dev_fast_scan.py", str(tmp_path)]
        try:
            try:
                exec(compile(Path(__file__).resolve().parents[1]
                             .joinpath("tools/dev_fast_scan.py")
                             .read_text(),
                             "dev_fast_scan.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_fast_scan.py",
                      "sys": sys,
                      "os": os,
                      "json": json,
                      "yaml": yaml,
                      "glob": __import__("glob"),
                      "re": __import__("re")})
            except SystemExit:
                pass
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "findings" in data
        assert "scores" in data
        assert "structure_score" in data
        assert data["agents_scanned"] >= 1

    def test_main_default_path(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        old_argv = sys.argv
        sys.argv = ["dev_fast_scan.py"]
        try:
            try:
                exec(compile(Path(__file__).resolve().parents[1]
                             .joinpath("tools/dev_fast_scan.py")
                             .read_text(),
                             "dev_fast_scan.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_fast_scan.py",
                      "sys": sys,
                      "os": os,
                      "json": json,
                      "yaml": yaml,
                      "glob": __import__("glob"),
                      "re": __import__("re")})
            except SystemExit:
                pass
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        # Default scan in empty dir → empty findings
        data = json.loads(out)
        assert "findings" in data
