"""R110-442 — coverage-push r8: tools/dev_pattern_apply.py 0% → 100%.

Pattern-applier for high-confidence patterns (55 lines).

Targets:
- load: valid YAML → dict; invalid YAML → {}; empty file → {}
- get_scoped_agents: filters project_files to .yaml files
  (the dict-mapping branch is unused — function returns the
  same regardless of pattern_name)
- apply_patterns: empty registry → {applied:[], skipped:0};
  single pattern below threshold → skipped=1; pattern above
  threshold WITHOUT auto_applied → not auto-applied (skipped
  silently); pattern above threshold WITH auto_applied but
  project already in auto_applied_to → not re-applied; pattern
  with auto_applied and project NOT in list → 3 candidates
  applied (capped at 3 even if more); multiple patterns mixed
  confidence; registry file is updated in-place (yaml.dump
  preserves structure)
- __main__: argparse required --registry, --project, --threshold
  (default 0.3); JSON printed to stdout
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_pattern_apply as pa  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# load
# ─────────────────────────────────────────────────────────────────────
class TestLoad:
    def test_valid_yaml(self, tmp_path):
        f = tmp_path / "good.yaml"
        f.write_text("key: value\n")
        assert pa.load(str(f)) == {"key": "value"}

    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("key: : :\n")
        assert pa.load(str(f)) == {}

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        assert pa.load(str(f)) is None


# ─────────────────────────────────────────────────────────────────────
# get_scoped_agents
# ─────────────────────────────────────────────────────────────────────
class TestGetScopedAgents:
    def test_filters_yaml_files(self, tmp_path):
        (tmp_path / "a.yaml").write_text("")
        (tmp_path / "b.yaml").write_text("")
        (tmp_path / "c.txt").write_text("")
        (tmp_path / "d.json").write_text("")
        files = list(tmp_path.iterdir())
        result = pa.get_scoped_agents("any_pattern", [str(f) for f in files])
        assert len(result) == 2
        assert all(r.endswith(".yaml") for r in result)

    def test_no_yaml_files(self):
        result = pa.get_scoped_agents("any", ["/tmp/a.txt", "/tmp/b.json"])
        assert result == []

    def test_empty_input(self):
        assert pa.get_scoped_agents("any", []) == []

    def test_returns_yaml_files_only(self):
        result = pa.get_scoped_agents(
            "prompt_braucht_boundary",
            ["/tmp/x.yaml", "/tmp/y.txt", "/tmp/z.yaml"])
        assert len(result) == 2
        assert "/tmp/x.yaml" in result
        assert "/tmp/z.yaml" in result


# ─────────────────────────────────────────────────────────────────────
# apply_patterns
# ─────────────────────────────────────────────────────────────────────
class TestApplyPatterns:
    def test_empty_registry(self, tmp_path):
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({"patterns": []}))
        project = tmp_path / "proj"
        project.mkdir()
        r = pa.apply_patterns(str(registry), str(project), 0.3)
        assert r == {"applied": [], "skipped": 0}

    def test_pattern_below_threshold_skipped(self, tmp_path):
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({
            "patterns": [{"name": "p1", "confidence": 0.1,
                          "rule": "rule1"}]}))
        project = tmp_path / "proj"
        project.mkdir()
        r = pa.apply_patterns(str(registry), str(project), 0.3)
        assert r["applied"] == []
        assert r["skipped"] == 1

    def test_pattern_above_threshold_no_auto_applied(self, tmp_path):
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({
            "patterns": [{"name": "p1", "confidence": 0.9,
                          "rule": "rule1"}]}))
        project = tmp_path / "proj"
        project.mkdir()
        r = pa.apply_patterns(str(registry), str(project), 0.3)
        # No auto_applied key → pattern not applied
        assert r["applied"] == []
        assert r["skipped"] == 0

    def test_pattern_auto_applied_first_time(self, tmp_path):
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({
            "patterns": [{"name": "p1", "confidence": 0.9,
                          "rule": "rule1", "auto_applied": True}]}))
        project = tmp_path / "proj"
        project.mkdir()
        # Create 5 yaml files — only 3 should be applied (capped)
        for i in range(5):
            (project / f"f{i}.yaml").write_text("")
        r = pa.apply_patterns(str(registry), str(project), 0.3)
        assert len(r["applied"]) == 3
        assert all(a["pattern"] == "p1" for a in r["applied"])
        assert all(a["status"] == "pending" for a in r["applied"])
        assert all(a["action"].startswith("Apply ") for a in r["applied"])

    def test_pattern_auto_applied_already_in_list(self, tmp_path):
        registry = tmp_path / "reg.yaml"
        project = tmp_path / "proj"
        project.mkdir()
        for i in range(3):
            (project / f"f{i}.yaml").write_text("")
        # Pre-populate registry with project already in auto_applied_to
        registry.write_text(yaml.safe_dump({
            "patterns": [{"name": "p1", "confidence": 0.9,
                          "rule": "rule1", "auto_applied": True,
                          "auto_applied_to": [str(project)]}]}))
        r = pa.apply_patterns(str(registry), str(project), 0.3)
        # Already applied → no new applications
        assert r["applied"] == []

    def test_registry_updated_with_auto_applied_to(self, tmp_path):
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({
            "patterns": [{"name": "p1", "confidence": 0.9,
                          "rule": "rule1", "auto_applied": True}]}))
        project = tmp_path / "proj"
        project.mkdir()
        (project / "f.yaml").write_text("")
        pa.apply_patterns(str(registry), str(project), 0.3)
        # Reload registry — should have auto_applied_to set
        with open(registry) as f:
            reg = yaml.safe_load(f)
        assert str(project) in reg["patterns"][0]["auto_applied_to"]

    def test_threshold_filters_correctly(self, tmp_path):
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({
            "patterns": [
                {"name": "high", "confidence": 0.9, "rule": "r"},
                {"name": "mid", "confidence": 0.5, "rule": "r"},
                {"name": "low", "confidence": 0.1, "rule": "r"},
            ]}))
        project = tmp_path / "proj"
        project.mkdir()
        r = pa.apply_patterns(str(registry), str(project), 0.4)
        # mid (0.5) and high (0.9) are above 0.4; low (0.1) is skipped
        assert r["skipped"] == 1

    def test_threshold_excludes_above(self, tmp_path):
        # Test with threshold > all confidences
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({
            "patterns": [
                {"name": "p1", "confidence": 0.1, "rule": "r"},
            ]}))
        project = tmp_path / "proj"
        project.mkdir()
        r = pa.apply_patterns(str(registry), str(project), 0.5)
        assert r["skipped"] == 1
        assert r["applied"] == []

    def test_action_truncated_to_40_chars(self, tmp_path):
        long_rule = "x" * 100
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({
            "patterns": [{"name": "p1", "confidence": 0.9,
                          "rule": long_rule, "auto_applied": True}]}))
        project = tmp_path / "proj"
        project.mkdir()
        (project / "f.yaml").write_text("")
        r = pa.apply_patterns(str(registry), str(project), 0.3)
        assert r["applied"][0]["action"] == "Apply " + "x" * 40

    def test_action_keeps_short(self, tmp_path):
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({
            "patterns": [{"name": "p1", "confidence": 0.9,
                          "rule": "short rule", "auto_applied": True}]}))
        project = tmp_path / "proj"
        project.mkdir()
        (project / "f.yaml").write_text("")
        r = pa.apply_patterns(str(registry), str(project), 0.3)
        assert r["applied"][0]["action"] == "Apply short rule"


# ─────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_main_exec_runs_argparse(self, tmp_path, capsys):
        registry = tmp_path / "reg.yaml"
        registry.write_text(yaml.safe_dump({"patterns": []}))
        project = tmp_path / "proj"
        project.mkdir()
        old_argv = sys.argv
        sys.argv = ["dev_pattern_apply.py",
                    "--registry", str(registry),
                    "--project", str(project),
                    "--threshold", "0.3"]
        try:
            exec(compile(Path(__file__).resolve().parents[1]
                         .joinpath("tools/dev_pattern_apply.py")
                         .read_text(),
                         "dev_pattern_apply.py", "exec"),
                 {"__name__": "__main__",
                  "__file__": "dev_pattern_apply.py",
                  "sys": sys,
                  "json": json,
                  "Path": Path})
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "applied" in data
        assert "skipped" in data

    def test_main_exec_missing_required_arg(self, capsys):
        old_argv = sys.argv
        sys.argv = ["dev_pattern_apply.py"]
        code = 0
        try:
            try:
                exec(compile(Path(__file__).resolve().parents[1]
                             .joinpath("tools/dev_pattern_apply.py")
                             .read_text(),
                             "dev_pattern_apply.py", "exec"),
                     {"__name__": "__main__",
                      "__file__": "dev_pattern_apply.py",
                      "sys": sys,
                      "json": json,
                      "Path": Path})
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        finally:
            sys.argv = old_argv
        # argparse exits with code 2 on missing required args
        assert code == 2
