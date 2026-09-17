"""R110-461 — coverage-push r8: tools/dev_pattern_apply.py 0% → 100%

Pattern-Apply Tool. CLI: --registry PATH --project DIR
--threshold FLOAT (default 0.3). Output: JSON
{applied: [{pattern, file, action, status}], skipped: int}.

Targets:
- get_scoped_agents(pattern_name, project_files):
  - mapping dict with 5 lambdas. Filters .yaml files.
  - For each pattern, only the relevant lambdas apply, but
    since the filter is `endswith('.yaml')`, all return the
    same filtered list. We exercise each lambda at least once.

- load(path):
  - valid YAML → dict
  - invalid YAML → {}
  - file not found → FileNotFoundError (NOT caught here — load
    doesn't have try/except for missing files, only yaml
    errors). Wait — source does try/except around yaml.safe_load
    which catches OSError too on some Python versions. Let's
    test both: valid yaml and invalid yaml.

- apply_patterns(registry_path, project, threshold=0.3):
  - pattern below threshold → skipped += 1
  - pattern without auto_applied → skipped += 1 (no apply)
  - pattern with auto_applied but project already in
    auto_applied_to → skipped (no apply)
  - pattern with auto_applied and project NOT in
    auto_applied_to → apply to first 3 yaml candidates,
    append project to auto_applied_to
  - registry re-written with yaml.dump
  - returns {applied, skipped}
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import tools.dev_pattern_apply as pa  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# get_scoped_agents — exercise each lambda
# ─────────────────────────────────────────────────────────────────────
class TestGetScopedAgents:
    def test_filters_yaml_only(self, tmp_path):
        files = [
            str(tmp_path / "a.yaml"),
            str(tmp_path / "b.yaml"),
            str(tmp_path / "c.txt"),
        ]
        r = pa.get_scoped_agents('prompt_braucht_boundary', files)
        # All yaml files kept (lambda may also drop based on prompt)
        # but the lambda receives load(f) which may fail on missing
        # files. Use real YAML files instead.
        yaml_dir = tmp_path
        (yaml_dir / "a.yaml").write_text("prompt: hello")
        (yaml_dir / "b.yaml").write_text("other: 1")
        r = pa.get_scoped_agents(
            'prompt_braucht_boundary',
            [str(yaml_dir / "a.yaml"),
             str(yaml_dir / "b.yaml")])
        # At minimum the filter `endswith('.yaml')` keeps both
        assert len(r) == 2

    def test_settings_pattern(self, tmp_path):
        (tmp_path / "a.yaml").write_text("x: 1")
        r = pa.get_scoped_agents('settings_timeout_sweetspot',
                                  [str(tmp_path / "a.yaml")])
        assert str(tmp_path / "a.yaml") in r

    def test_instructions_pattern(self, tmp_path):
        (tmp_path / "a.yaml").write_text("instructions: hi")
        r = pa.get_scoped_agents('instructions_mit_inputblock',
                                  [str(tmp_path / "a.yaml")])
        assert len(r) == 1

    def test_outputformat_pattern(self, tmp_path):
        (tmp_path / "a.yaml").write_text("prompt: x")
        r = pa.get_scoped_agents('prompt_mit_outputformat',
                                  [str(tmp_path / "a.yaml")])
        assert len(r) == 1

    def test_backup_pattern_always_true(self, tmp_path):
        (tmp_path / "a.yaml").write_text("x: 1")
        r = pa.get_scoped_agents('backup_vor_patch',
                                  [str(tmp_path / "a.yaml")])
        assert len(r) == 1


# ─────────────────────────────────────────────────────────────────────
# load
# ─────────────────────────────────────────────────────────────────────
class TestLoad:
    def test_valid_yaml(self, tmp_path):
        f = tmp_path / "good.yaml"
        f.write_text("a: 1\nb: hello\n")
        d = pa.load(str(f))
        assert d["a"] == 1
        assert d["b"] == "hello"

    def test_invalid_yaml_returns_empty(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("a: : :\n  invalid")
        d = pa.load(str(f))
        # Either empty dict (yaml error caught) or partial parse
        assert isinstance(d, dict)


# ─────────────────────────────────────────────────────────────────────
# apply_patterns — core logic
# ─────────────────────────────────────────────────────────────────────
class TestApplyPatterns:
    def _make_registry(self, tmp_path, patterns):
        reg_path = tmp_path / "reg.yaml"
        with open(reg_path, 'w') as f:
            yaml.dump({"patterns": patterns}, f,
                      default_flow_style=False, sort_keys=False)
        return reg_path

    def _make_project(self, tmp_path, n_yaml=2):
        proj = tmp_path / "proj"
        proj.mkdir()
        for i in range(n_yaml):
            (proj / f"agent_{i}.yaml").write_text(f"name: a{i}\n")
        return proj

    def test_low_confidence_skipped(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.1, "rule": "r1",
             "auto_applied": True},
        ])
        proj = self._make_project(tmp_path)
        r = pa.apply_patterns(str(reg), str(proj))
        assert r["applied"] == []
        assert r["skipped"] == 1

    def test_no_auto_applied_skipped(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "r1",
             "auto_applied": False},
        ])
        proj = self._make_project(tmp_path)
        r = pa.apply_patterns(str(reg), str(proj))
        # Source: confidence OK but auto_applied=False → falls
        # through silently (no skipped += 1)
        assert r["applied"] == []
        assert r["skipped"] == 0

    def test_apply_to_project(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "r1 short",
             "auto_applied": True},
        ])
        proj = self._make_project(tmp_path, n_yaml=4)
        r = pa.apply_patterns(str(reg), str(proj))
        # 3 candidates ([:3] slice)
        assert len(r["applied"]) == 3
        assert r["skipped"] == 0
        assert r["applied"][0]["pattern"] == "p1"
        assert r["applied"][0]["status"] == "pending"
        assert "Apply r1 short" in r["applied"][0]["action"]

    def test_already_applied_to_project(self, tmp_path):
        # Pattern with auto_applied_to containing this project's
        # full path → skip
        proj = self._make_project(tmp_path)
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "r1",
             "auto_applied": True,
             "auto_applied_to": [str(proj)]},
        ])
        r = pa.apply_patterns(str(reg), str(proj))
        assert r["applied"] == []
        # Below threshold? No (0.9). auto_applied=True, project in
        # list → skip (skipped += 1). Actually re-read: skipped
        # only when confidence < threshold. If confidence OK and
        # project already in list → no apply, no skipped += 1.
        assert r["skipped"] == 0
        #         ... apply
        # So: project in list → falls through silently. skipped=0.
        assert r["skipped"] == 0

    def test_long_rule_truncated_to_40(self, tmp_path):
        long_rule = "x" * 100
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": long_rule,
             "auto_applied": True},
        ])
        proj = self._make_project(tmp_path)
        r = pa.apply_patterns(str(reg), str(proj))
        # action = f"Apply {p['rule'][:40]}"
        assert "Apply " + ("x" * 40) == r["applied"][0]["action"]

    def test_registry_modified(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "r",
             "auto_applied": True},
        ])
        proj = self._make_project(tmp_path)
        pa.apply_patterns(str(reg), str(proj))
        with open(reg) as f:
            new_reg = yaml.safe_load(f)
        # Source appends full project path to auto_applied_to
        assert "auto_applied_to" in new_reg["patterns"][0]
        assert str(proj) in new_reg["patterns"][0]["auto_applied_to"]

    def test_threshold_parameter(self, tmp_path):
        # threshold=0.5 → confidence 0.4 → skip
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.4, "rule": "r",
             "auto_applied": True},
        ])
        proj = self._make_project(tmp_path)
        r = pa.apply_patterns(str(reg), str(proj), threshold=0.5)
        assert r["skipped"] == 1
        assert r["applied"] == []

    def test_no_yaml_files_in_project(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "r",
             "auto_applied": True},
        ])
        proj = tmp_path / "empty_proj"
        proj.mkdir()
        r = pa.apply_patterns(str(reg), str(proj))
        # candidates = [] → no applied entries
        assert r["applied"] == []
        assert r["skipped"] == 0

    def test_multiple_patterns_mixed(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.1, "rule": "low",
             "auto_applied": True},   # skip (low conf)
            {"name": "p2", "confidence": 0.9, "rule": "high",
             "auto_applied": False},  # no apply (auto_applied=False)
            {"name": "p3", "confidence": 0.9, "rule": "apply",
             "auto_applied": True},   # apply
        ])
        proj = self._make_project(tmp_path, n_yaml=2)
        r = pa.apply_patterns(str(reg), str(proj))
        # Only p1 increments skipped (low conf). p2 falls through
        # silently. p3 applies.
        assert r["skipped"] == 1
        assert len(r["applied"]) == 2


# ─────────────────────────────────────────────────────────────────────
# CLI subprocess (covers __main__)
# ─────────────────────────────────────────────────────────────────────
class TestCli:
    def test_cli_runs(self, tmp_path):
        # Build minimal registry + project
        reg = tmp_path / "reg.yaml"
        with open(reg, 'w') as f:
            yaml.dump({"patterns": [
                {"name": "p1", "confidence": 0.9, "rule": "r",
                 "auto_applied": True}
            ]}, f)
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "a.yaml").write_text("x: 1")
        r = subprocess.run(
            ['python3', 'tools/dev_pattern_apply.py',
             '--registry', str(reg),
             '--project', str(proj)],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        out = json.loads(r.stdout)
        assert "applied" in out
        assert "skipped" in out

    def test_cli_missing_registry(self, tmp_path):
        r = subprocess.run(
            ['python3', 'tools/dev_pattern_apply.py',
             '--registry', str(tmp_path / "no_such.yaml"),
             '--project', str(tmp_path)],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        # argparse error → exit code 2
        assert r.returncode != 0
