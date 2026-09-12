"""R110-469 — coverage-push r9: tools/dev_registry_merge.py 0% → 100%

Extracts patterns from findings JSON and merges into a YAML
registry. Idempotent: re-running same findings on same registry
increments counts.

Targets:
- generate_id(type, existing_ids): returns unique
  'BP-CF-<TYPE6>-NNN' ID, base used internally for increment.
- merge_findings(findings, registry_path, project):
  - loads registry (None-safe via 'or {}')
  - collects existing pattern IDs + existing_projects from
    repeated_in lists
  - for each finding dict: skip non-dicts, decide patch_type
    via PATTERN_NAMES or 'cross_generisch', extract agent+detail
  - existing pattern (matched by name): increment count,
    update last_seen, append project to repeated_in, recompute
    confidence=count/unique_projects, append evidence (max 5)
  - new pattern: generate id, severity (3 if 'hoch' in
    severity else 2), rule string, evidence list, confidence
    1/total_projects, auto_applied=False
  - post-loop: write registry with last_updated + pattern_stats
    (total_projects, total_runs=total_patterns=len(patterns),
    avg_confidence)
- __main__: argparse --findings --registry --project, prints
  json result.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_registry_merge as drm  # noqa: E402


def _make_registry(tmp_path, patterns=None):
    p = tmp_path / "registry.yaml"
    with open(p, 'w') as f:
        yaml.safe_dump({"patterns": patterns or []}, f)
    return p


def _finding(type_="A1", agent="agent-1", detail="missing prompt",
             severity="niedrig"):
    return {"type": type_, "agent": agent, "detail": detail,
            "severity": severity}


# ─────────────────────────────────────────────────────────────────────
# generate_id
# ─────────────────────────────────────────────────────────────────────
class TestGenerateId:
    def test_known_type(self):
        nid, base = drm.generate_id("A1", set())
        assert nid == "BP-CF-PROMPT-001"
        assert base == "BP-CF-PROMPT"

    def test_known_type_other(self):
        # E1 → 'hardcodierte_pathe' → upper[:6] → 'HARDCO'
        nid, base = drm.generate_id("E1", set())
        assert base == "BP-CF-HARDCO"
        assert nid == "BP-CF-HARDCO-001"

    def test_unknown_type_uses_generic(self):
        nid, base = drm.generate_id("X99", set())
        assert "BP-CF-GENERI" in nid
        assert base == "BP-CF-GENERI"

    def test_increments_past_existing(self):
        existing = {"BP-CF-PROMPT-001", "BP-CF-PROMPT-002",
                    "BP-CF-PROMPT-003"}
        nid, _ = drm.generate_id("A1", existing)
        assert nid == "BP-CF-PROMPT-004"

    def test_increments_until_free(self):
        # Existing has 001-004 → next is 005
        existing = {f"BP-CF-PROMPT-{i:03d}" for i in range(1, 5)}
        nid, _ = drm.generate_id("A1", existing)
        assert nid == "BP-CF-PROMPT-005"

    def test_empty_existing(self):
        nid, _ = drm.generate_id("A1", set())
        assert nid.endswith("-001")


# ─────────────────────────────────────────────────────────────────────
# merge_findings
# ─────────────────────────────────────────────────────────────────────
class TestMergeFindings:
    def test_no_findings(self, tmp_path):
        reg = _make_registry(tmp_path)
        result = drm.merge_findings([], reg, "proj-x")
        assert result["new_patterns"] == 0
        assert result["merged_count"] == 0
        # confidence_avg: 0/1 = 0
        assert result["confidence_avg"] == 0
        # File still updated with last_updated
        with open(reg) as f:
            r = yaml.safe_load(f)
        assert "last_updated" in r
        assert r["pattern_stats"]["total_patterns"] == 0
        assert r["pattern_stats"]["total_projects"] == 1

    def test_new_pattern(self, tmp_path):
        reg = _make_registry(tmp_path)
        findings = [_finding(type_="A1", detail="missing X")]
        result = drm.merge_findings(findings, reg, "proj-new")
        assert result["new_patterns"] == 1
        assert result["merged_count"] == 0
        with open(reg) as f:
            r = yaml.safe_load(f)
        p = r["patterns"][0]
        assert p["name"] == "prompt_missing_komplett"
        assert p["count"] == 1
        assert p["repeated_in"] == ["proj-new"]
        assert p["confidence"] == round(1.0 / 1, 2)
        assert p["severity"] == 2  # not 'hoch'
        assert p["auto_applied"] is False
        assert p["auto_applied_to"] == []
        assert "first_seen" in p
        assert "last_seen" in p
        assert "evidence" in p
        assert len(p["evidence"]) == 1

    def test_severity_hoch(self, tmp_path):
        reg = _make_registry(tmp_path)
        findings = [_finding(severity="hoch")]
        drm.merge_findings(findings, reg, "proj")
        with open(reg) as f:
            r = yaml.safe_load(f)
        assert r["patterns"][0]["severity"] == 3

    def test_merge_existing_pattern(self, tmp_path):
        # Pre-existing pattern with same name → merged, not new
        existing_pattern = {
            "id": "BP-CF-PROMPT-001",
            "name": "prompt_missing_komplett",
            "repeated_in": ["proj-old"],
            "count": 3,
            "confidence": 1.0,
            "evidence": [],
        }
        reg = _make_registry(tmp_path, [existing_pattern])
        findings = [_finding(type_="A1", detail="new incident")]
        result = drm.merge_findings(findings, reg, "proj-new")
        assert result["new_patterns"] == 0
        assert result["merged_count"] == 1
        with open(reg) as f:
            r = yaml.safe_load(f)
        p = r["patterns"][0]
        assert p["count"] == 4
        assert "proj-new" in p["repeated_in"]
        assert "proj-old" in p["repeated_in"]
        # confidence = count / unique_projects = 4/2 = 2.0
        assert p["confidence"] == 2.0

    def test_evidence_capped_at_5(self, tmp_path):
        existing_pattern = {
            "id": "BP-CF-PROMPT-001",
            "name": "prompt_missing_komplett",
            "repeated_in": ["p1"],
            "count": 3,
            "confidence": 1.0,
            "evidence": [
                {"project": f"e{i}", "run": "2026-01-01",
                 "patch": f"x{i}"} for i in range(5)
            ],
        }
        reg = _make_registry(tmp_path, [existing_pattern])
        drm.merge_findings([_finding(type_="A1")], reg, "p-new")
        with open(reg) as f:
            r = yaml.safe_load(f)
        # Evidence list stays at 5
        assert len(r["patterns"][0]["evidence"]) == 5

    def test_unknown_type_uses_cross_generisch(self, tmp_path):
        reg = _make_registry(tmp_path)
        drm.merge_findings([_finding(type_="X99")], reg, "p")
        with open(reg) as f:
            r = yaml.safe_load(f)
        assert r["patterns"][0]["name"] == "cross_generisch"

    def test_skip_non_dict_finding(self, tmp_path):
        reg = _make_registry(tmp_path)
        findings = [
            _finding(type_="A1"),
            "not a dict",   # ignored
            None,           # ignored
            42,             # ignored
            _finding(type_="E1"),
        ]
        result = drm.merge_findings(findings, reg, "p")
        assert result["new_patterns"] == 2

    def test_rule_field(self, tmp_path):
        reg = _make_registry(tmp_path)
        drm.merge_findings(
            [_finding(type_="A1", detail="my detail")], reg, "p")
        with open(reg) as f:
            r = yaml.safe_load(f)
        rule = r["patterns"][0]["rule"]
        assert "Prompt missing komplett: my detail" in rule \
            or "Prompt_missing_komplett: my detail" in rule \
            or "Prompt missing" in rule

    def test_existing_projects_aggregated(self, tmp_path):
        # Patterns have repeated_in lists → existing_projects populated
        existing = [
            {"id": "BP-CF-PROMPT-001", "name": "prompt_missing_komplett",
             "repeated_in": ["proj-a", "proj-b"], "count": 1,
             "confidence": 0.5, "evidence": []},
        ]
        reg = _make_registry(tmp_path, existing)
        drm.merge_findings([_finding(type_="A1")], reg, "proj-c")
        with open(reg) as f:
            r = yaml.safe_load(f)
        stats = r["pattern_stats"]
        # existing_projects = {a, b, c} = 3
        assert stats["total_projects"] == 3

    def test_repeated_in_missing_key(self, tmp_path):
        # No repeated_in key → existing.get(...) = [] → skipped
        existing = [{
            "id": "BP-CF-PROMPT-001", "name": "prompt_missing_komplett",
            "count": 1, "confidence": 0.5, "evidence": [],
        }]
        reg = _make_registry(tmp_path, existing)
        drm.merge_findings([_finding(type_="A1")], reg, "proj-x")
        with open(reg) as f:
            r = yaml.safe_load(f)
        assert r["pattern_stats"]["total_projects"] == 1

    def test_empty_registry_file(self, tmp_path):
        # Registry file exists but empty → yaml.safe_load returns None
        # → 'or {}' makes reg={}
        reg = tmp_path / "empty.yaml"
        reg.write_text("")
        result = drm.merge_findings([_finding()], reg, "p")
        assert result["new_patterns"] == 1
        with open(reg) as f:
            r = yaml.safe_load(f)
        assert r is not None
        assert "patterns" in r

    def test_avg_confidence(self, tmp_path):
        reg = _make_registry(tmp_path)
        findings = [
            _finding(type_="A1"),  # new, confidence 1.0
            _finding(type_="E1"),  # new, confidence 1.0
        ]
        result = drm.merge_findings(findings, reg, "p")
        # avg = (1.0 + 1.0) / 2 = 1.0
        assert result["confidence_avg"] == 1.0

    def test_evidence_appended_for_new(self, tmp_path):
        reg = _make_registry(tmp_path)
        drm.merge_findings(
            [_finding(agent="a1", detail="d1234567890abcdefg")],
            reg, "p")
        with open(reg) as f:
            r = yaml.safe_load(f)
        ev = r["patterns"][0]["evidence"][0]
        assert ev["project"] == "p"
        # detail truncated to 50 chars
        assert len(ev["patch"]) <= len("a1: ") + 50


# ─────────────────────────────────────────────────────────────────────
# __main__ CLI
# ─────────────────────────────────────────────────────────────────────
class TestCLI:
    def test_cli_runs(self, tmp_path):
        reg = _make_registry(tmp_path)
        findings = [_finding(type_="A1")]
        result = subprocess.run(
            [sys.executable,
             str(REPO_ROOT / "tools" / "dev_registry_merge.py"),
             "--findings", json.dumps(findings),
             "--registry", str(reg),
             "--project", "cli-proj"],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout)
        assert out["new_patterns"] == 1
        with open(reg) as f:
            r = yaml.safe_load(f)
        assert len(r["patterns"]) == 1
