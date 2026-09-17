"""R110-432 — coverage-push r6: tools/dev_pattern_apply.py 0% → 100%.

Pattern applier (55 lines). Reads a registry YAML of high-confidence
patterns, walks a project dir for .yaml files, applies patterns whose
confidence ≥ threshold and auto_applied flag is set.

Targets:
- get_scoped_agents: only .yaml files returned
- load: valid YAML → dict, invalid YAML → {} (bare except), empty
- apply_patterns: empty patterns, low-confidence (skipped),
  high-confidence + auto_applied + not-yet-applied (candidates[:3]
  appended, auto_applied_to updated), high-confidence +
  auto_applied + already-applied (skipped), high-confidence +
  no-auto-applied flag (skipped), project dir with no yaml files
  (candidates empty → no applied), project dir non-existent
  (os.walk returns empty), registry without 'patterns' key,
  pattern with no 'confidence' key (treated as 0 → skipped),
  pattern with no 'auto_applied_to' key (created via setdefault),
  registry-write preserves registry file structure,
  candidates-limited-to-3, action-truncated-to-40,
  nested-project-dirs, multiple-patterns-mixed
- __main__ exec via in-process exec()
"""

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_pattern_apply as pa  # noqa: E402


def _write_yaml(path, data):
    path.write_text(yaml.safe_dump(data, default_flow_style=False,
                                    allow_unicode=True, sort_keys=False))


# ─────────────────────────────────────────────────────────────────────
# get_scoped_agents
# ─────────────────────────────────────────────────────────────────────
class TestGetScopedAgents:
    def test_only_yaml_files(self):
        files = ["a.yaml", "b.yml", "c.yaml", "d.txt", "e.py"]
        result = pa.get_scoped_agents("any_pattern", files)
        assert "a.yaml" in result
        assert "c.yaml" in result
        assert all(f.endswith(".yaml") for f in result)

    def test_empty_list(self):
        assert pa.get_scoped_agents("p", []) == []


# ─────────────────────────────────────────────────────────────────────
# load
# ─────────────────────────────────────────────────────────────────────
class TestLoad:
    def test_valid_yaml(self, tmp_path):
        (tmp_path / "x.yaml").write_text("a: 1\nb: hello\n")
        r = pa.load(str(tmp_path / "x.yaml"))
        assert r == {"a": 1, "b": "hello"}

    def test_invalid_yaml_returns_empty(self, tmp_path):
        (tmp_path / "bad.yaml").write_text("a: [unterminated\n")
        r = pa.load(str(tmp_path / "bad.yaml"))
        assert r == {}

    def test_empty_file_returns_none(self, tmp_path):
        # yaml.safe_load("") returns None (not {})
        (tmp_path / "empty.yaml").write_text("")
        r = pa.load(str(tmp_path / "empty.yaml"))
        assert r is None


# ─────────────────────────────────────────────────────────────────────
# apply_patterns
# ─────────────────────────────────────────────────────────────────────
class TestApplyPatterns:
    def _make_registry(self, tmp_path, patterns):
        reg = tmp_path / "reg.yaml"
        _write_yaml(reg, {"patterns": patterns})
        return str(reg)

    def _make_project(self, tmp_path, yaml_files):
        proj = tmp_path / "project"
        proj.mkdir()
        for f in yaml_files:
            (proj / f).write_text("agent: x\n")
        return str(proj)

    def test_empty_patterns(self, tmp_path):
        reg = self._make_registry(tmp_path, [])
        proj = self._make_project(tmp_path, [])
        r = pa.apply_patterns(reg, proj)
        assert r == {"applied": [], "skipped": 0}

    def test_low_confidence_skipped(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.1, "rule": "rule1"}
        ])
        proj = self._make_project(tmp_path, [])
        r = pa.apply_patterns(reg, proj, threshold=0.3)
        assert r["applied"] == []
        assert r["skipped"] == 1

    def test_high_confidence_auto_applied(self, tmp_path):
        proj_path = str(tmp_path / "project")
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1",
             "auto_applied": True, "auto_applied_to": []}
        ])
        proj = self._make_project(tmp_path, ["a.yaml"])
        r = pa.apply_patterns(reg, proj)
        assert len(r["applied"]) == 1
        assert r["applied"][0]["pattern"] == "p1"
        assert r["applied"][0]["file"].endswith("a.yaml")
        assert r["applied"][0]["status"] == "pending"
        assert r["skipped"] == 0
        updated = yaml.safe_load(Path(reg).read_text())
        assert proj_path in updated["patterns"][0]["auto_applied_to"]

    def test_high_confidence_already_applied_to_project(self, tmp_path):
        proj = self._make_project(tmp_path, ["a.yaml"])
        proj_str = str(proj)
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1",
             "auto_applied": True, "auto_applied_to": [proj_str]}
        ])
        r = pa.apply_patterns(reg, proj)
        # Project already in auto_applied_to → no work, no skipped-count
        # (skipped only increments on low-confidence)
        assert r["applied"] == []
        assert r["skipped"] == 0

    def test_high_confidence_no_auto_applied_flag(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1"}
        ])
        proj = self._make_project(tmp_path, ["a.yaml"])
        r = pa.apply_patterns(reg, proj)
        # No auto_applied → no-work, no skipped-count (skipped only
        # increments on low-confidence)
        assert r["applied"] == []
        assert r["skipped"] == 0

    def test_no_yaml_files_in_project(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1",
             "auto_applied": True, "auto_applied_to": []}
        ])
        proj = tmp_path / "project"
        proj.mkdir()
        (proj / "data.txt").write_text("nothing")
        r = pa.apply_patterns(reg, str(proj))
        assert r["applied"] == []
        assert r["skipped"] == 0

    def test_nonexistent_project_dir(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1",
             "auto_applied": True, "auto_applied_to": []}
        ])
        r = pa.apply_patterns(reg, str(tmp_path / "nope"))
        assert r["applied"] == []
        assert r["skipped"] == 0

    def test_registry_without_patterns_key(self, tmp_path):
        reg = tmp_path / "reg.yaml"
        _write_yaml(reg, {"other_key": []})  # no 'patterns'
        proj = self._make_project(tmp_path, [])
        r = pa.apply_patterns(str(reg), proj)
        assert r == {"applied": [], "skipped": 0}

    def test_pattern_without_confidence_key(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "rule": "rule1", "auto_applied": True}
        ])
        proj = self._make_project(tmp_path, ["a.yaml"])
        r = pa.apply_patterns(reg, proj)
        # No confidence → defaults to 0 → skipped
        assert r["applied"] == []
        assert r["skipped"] == 1

    def test_pattern_without_auto_applied_to_key(self, tmp_path):
        proj_path = str(tmp_path / "project")
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1",
             "auto_applied": True}
        ])
        proj = self._make_project(tmp_path, ["a.yaml"])
        r = pa.apply_patterns(reg, proj)
        assert len(r["applied"]) == 1
        updated = yaml.safe_load(Path(reg).read_text())
        assert proj_path in updated["patterns"][0]["auto_applied_to"]

    def test_candidates_limited_to_3(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1",
             "auto_applied": True, "auto_applied_to": []}
        ])
        proj = tmp_path / "project"
        proj.mkdir()
        for i in range(5):
            (proj / f"a{i}.yaml").write_text("a: 1\n")
        r = pa.apply_patterns(reg, str(proj))
        assert len(r["applied"]) == 3

    def test_action_truncated_to_40_chars(self, tmp_path):
        long_rule = "x" * 100
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": long_rule,
             "auto_applied": True, "auto_applied_to": []}
        ])
        proj = self._make_project(tmp_path, ["a.yaml"])
        r = pa.apply_patterns(reg, proj)
        # action = f'Apply {rule[:40]}' → "Apply " (6) + 40 = 46
        assert r["applied"][0]["action"] == "Apply " + "x" * 40

    def test_nested_project_dirs(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1",
             "auto_applied": True, "auto_applied_to": []}
        ])
        proj = tmp_path / "project"
        sub = proj / "sub"
        sub.mkdir(parents=True)
        (sub / "deep.yaml").write_text("a: 1\n")
        r = pa.apply_patterns(reg, str(proj))
        assert len(r["applied"]) == 1
        assert "deep.yaml" in r["applied"][0]["file"]

    def test_multiple_patterns_mixed(self, tmp_path):
        # Pre-compute proj path so we can put it in auto_applied_to
        proj = tmp_path / "project"
        proj_str = str(proj)
        reg = self._make_registry(tmp_path, [
            {"name": "low", "confidence": 0.1, "rule": "r1"},
            {"name": "high_no_auto", "confidence": 0.9, "rule": "r2"},
            {"name": "high_auto", "confidence": 0.9, "rule": "r3",
             "auto_applied": True, "auto_applied_to": []},
            {"name": "high_auto_already", "confidence": 0.9,
             "rule": "r4", "auto_applied": True,
             "auto_applied_to": [proj_str]},  # already applied
        ])
        proj.mkdir()
        (proj / "a.yaml").write_text("a: 1\n")
        r = pa.apply_patterns(reg, str(proj))
        # Only 'high_auto' applies; 'low' skipped (low confidence),
        # 'high_no_auto' no-work (no auto_applied flag), 'high_auto_already'
        # no-work (already in list) — only 'low' increments skipped
        assert len(r["applied"]) == 1
        assert r["applied"][0]["pattern"] == "high_auto"
        assert r["skipped"] == 1

    def test_registry_written_back(self, tmp_path):
        reg = self._make_registry(tmp_path, [
            {"name": "p1", "confidence": 0.9, "rule": "rule1",
             "auto_applied": True, "auto_applied_to": []}
        ])
        proj = self._make_project(tmp_path, ["a.yaml"])
        pa.apply_patterns(reg, proj)
        assert Path(reg).exists()
        content = Path(reg).read_text()
        assert "auto_applied_to" in content
        assert str(proj) in content


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_main(self, monkeypatch, tmp_path):
        reg = tmp_path / "reg.yaml"
        _write_yaml(reg, {"patterns": []})
        proj = tmp_path / "project"
        proj.mkdir()
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_pattern_apply.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_pattern_apply.py",
                        "--registry", str(reg),
                        "--project", str(proj),
                        "--threshold", "0.3"]
            buf = io.StringIO()
            with redirect_stdout(buf):
                exec(compile(script, "dev_pattern_apply.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_pattern_apply.py"})
            out = buf.getvalue()
            parsed = json.loads(out)
            assert parsed["applied"] == []
            assert parsed["skipped"] == 0
        finally:
            sys.argv = old_argv
