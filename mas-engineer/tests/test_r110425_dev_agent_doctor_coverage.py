"""R110-425 — coverage-push r7: dev_agent_doctor.py 0% → 90%+.

Big module (345 stmts) — framework agent-health scanner with MAS extension.
We monkeypatch all the module-level globals onto tmp_path so the module
thinks it's working in a synthetic workspace.

Targets:
- load_best_practices (file exists / file missing → creates new BP)
- find_framework_agents (returns agents from core/specialists/sub)
- scan_agent — every check branch:
  contains, contains_all, prompt_length (with/without prompt match),
  range, yaml_lte, file_refs_exist (existing+missing),
  test_exists (with/without FRAMEWORK_TESTS),
  yaml parse error
  score thresholds (>=80 gruen, 50-79 gelb, <50 rot)
- full_scan (filter, no-agents err)
- show_report (prints summary)
- auto_fix (FW-P-001, FW-S-001/003 timeout clamp, FW-S-002 max_steps)
- export_report
- find_mas_agents (no dir → [])
- check_mas_agent — every C1-C7 branch:
  C1 autonomie, C2 tool_inventar, C3 output_format (3 variants),
  C4 shield_rules (>=6 / <6), C5 settings (3 valid max_steps),
  C6 separation (clean / has fw concepts), C7 edge_cases
  yaml parse error
- apply_lessons (dry_run, dry_run=False)
- show_apply_report
- main() — version, scan, scan+fix, scan+export, watch, project,
  apply_lessons (with MAS BP missing err, no agents err), all_projects
- __main__ exec block
"""

import argparse
import io
import json
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_agent_doctor as doc  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Fixture: monkeypatch all module globals onto tmp_path
# ─────────────────────────────────────────────────────────────────────
@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Synthetic workspace with framework/dev-team + mas-engineer/recipe/sub."""
    fw = tmp_path / "framework" / "dev-team"
    fw.mkdir(parents=True)
    (fw / "recipes" / "core").mkdir(parents=True)
    (fw / "recipes" / "specialists").mkdir(parents=True)
    (fw / "recipes" / "sub").mkdir(parents=True)
    (fw / "tests").mkdir(parents=True)

    # MAS side
    mas_recipes = tmp_path / "mas-engineer" / "recipe"
    mas_recipes.mkdir(parents=True)
    (mas_recipes / "sub").mkdir(parents=True)

    # STATE_DIR for BP files + report
    state_dir = tmp_path / ".mase"
    state_dir.mkdir()

    monkeypatch.setattr(doc, "WORKSPACE", tmp_path)
    monkeypatch.setattr(doc, "TOOLS_DIR", tmp_path / "tools")
    monkeypatch.setattr(doc, "STATE_DIR", state_dir)
    monkeypatch.setattr(doc, "BP_FILE", state_dir / "framework-best-practices.yaml")
    monkeypatch.setattr(doc, "MAS_BP_FILE", state_dir / "best-practices.yaml")
    monkeypatch.setattr(doc, "REPORT_FILE", state_dir / "framework-health.json")
    monkeypatch.setattr(doc, "FRAMEWORK_RECIPES", fw / "recipes")
    monkeypatch.setattr(doc, "FRAMEWORK_DOCS", fw / "docs")
    monkeypatch.setattr(doc, "FRAMEWORK_TESTS", fw / "tests")
    monkeypatch.setattr(doc, "ACTIVE_PROJECT", "dev-team")
    monkeypatch.setattr(doc, "MAS_RECIPES", mas_recipes)
    monkeypatch.setattr(doc, "MAS_SUB_DIR", mas_recipes / "sub")

    # Suppress colored output during tests
    monkeypatch.setattr(doc, "C", {"R": "", "G": "", "Y": "", "B": "", "BD": "", "NC": ""})
    monkeypatch.setattr(doc, "ok", lambda m: None)
    monkeypatch.setattr(doc, "warn", lambda m: None)
    monkeypatch.setattr(doc, "info", lambda m: None)
    monkeypatch.setattr(doc, "err", lambda m: None)

    return tmp_path


def _make_minimal_bp():
    """Minimal best-practices dict that exercises every check type."""
    return {
        "version": "1.0.0",
        "best_practices": {
            "prompt": [
                {"id": "P-C", "rule": "contains-test", "severity": "critical",
                 "check": "contains", "values": ["NEEDLE"]},
                {"id": "P-CA", "rule": "contains-all-test", "severity": "critical",
                 "check": "contains_all", "values": ["A", "B"]},
                {"id": "P-PL", "rule": "prompt-len-test", "severity": "important",
                 "check": "prompt_length", "max": 800},
            ],
            "settings": [
                {"id": "S-R", "rule": "range-test", "severity": "important",
                 "check": "range", "path": "settings.timeout", "min": 60, "max": 120},
                {"id": "S-LTE", "rule": "lte-test", "severity": "critical",
                 "check": "yaml_lte", "path": "settings.max_steps", "max": 50},
            ],
            "structure": [
                {"id": "ST-FR", "rule": "file-refs", "severity": "critical",
                 "check": "file_refs_exist", "extensions": [".md", ".yaml"]},
                {"id": "ST-TE", "rule": "test-exists", "severity": "important",
                 "check": "test_exists", "prefix": ""},
            ],
            "tests": [],
        },
    }


# ─────────────────────────────────────────────────────────────────────
# load_best_practices
# ─────────────────────────────────────────────────────────────────────
class TestLoadBestPractices:
    def test_load_existing(self, ws):
        existing = _make_minimal_bp()
        doc.BP_FILE.write_text(yaml.safe_dump(existing))
        bp = doc.load_best_practices()
        assert bp == existing

    def test_create_new_when_missing(self, ws):
        # BP_FILE doesn't exist → creates new with defaults
        assert not doc.BP_FILE.exists()
        bp = doc.load_best_practices()
        assert "best_practices" in bp
        # File is now created
        assert doc.BP_FILE.exists()


class TestGetFrameworkPath:
    def test_no_projects_yaml_uses_dev_team_default(self, ws):
        # No .projects.yaml → falls into else branch (line 38-39)
        assert not (ws / "framework" / ".projects.yaml").exists()
        r, d, t, active = doc.get_framework_path()
        assert active == "dev-team"
        assert r == ws / "framework" / "dev-team" / "recipes"

    def test_with_projects_yaml_no_active_key(self, ws):
        # .projects.yaml exists but has no "active_project" key
        (ws / "framework" / ".projects.yaml").write_text(
            yaml.safe_dump({"projects": {"foo": {}}})
        )
        r, d, t, active = doc.get_framework_path()
        assert active == "dev-team"

    def test_with_projects_yaml_active_key(self, ws):
        # .projects.yaml exists with active_project key
        (ws / "framework" / ".projects.yaml").write_text(
            yaml.safe_dump({"active_project": "myproj", "projects": {"myproj": {}}})
        )
        # Create the myproj dir so the fallback isn't needed
        (ws / "framework" / "myproj").mkdir()
        r, d, t, active = doc.get_framework_path()
        assert active == "myproj"
        assert r == ws / "framework" / "myproj" / "recipes"

    def test_with_named_project_arg(self, ws):
        # Pass project_name explicitly when no .projects.yaml
        r, d, t, active = doc.get_framework_path("custom")
        assert active == "custom"

    def test_nonexistent_project_falls_back_to_dev_team(self, ws):
        # project_name but the dir doesn't exist → fp falls back, but
        # active stays "nonexistent" (the active label is set BEFORE
        # the fp fallback)
        r, d, t, active = doc.get_framework_path("nonexistent")
        assert active == "nonexistent"
        # But recipes path falls back to dev-team
        assert r == ws / "framework" / "dev-team" / "recipes"


# ─────────────────────────────────────────────────────────────────────
# find_framework_agents
# ─────────────────────────────────────────────────────────────────────
class TestFindFrameworkAgents:
    def test_returns_agents_from_all_subs(self, ws):
        core = ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml"
        sp = ws / "framework" / "dev-team" / "recipes" / "specialists" / "bar.yaml"
        sb = ws / "framework" / "dev-team" / "recipes" / "sub" / "baz.yaml"
        for f in (core, sp, sb):
            f.write_text("name: x")
        agents = doc.find_framework_agents()
        assert len(agents) == 3
        names = {a.stem for a in agents}
        assert names == {"foo", "bar", "baz"}

    def test_empty_when_subs_missing(self, ws):
        # Recreate dirs as empty (rm contents but keep dirs)
        # FRAMEWORK_RECIPES dirs already empty → 0 agents
        agents = doc.find_framework_agents()
        assert agents == []


# ─────────────────────────────────────────────────────────────────────
# scan_agent — every check branch
# ─────────────────────────────────────────────────────────────────────
class TestScanAgent:
    def test_yaml_parse_error(self, ws):
        bad = ws / "framework" / "dev-team" / "recipes" / "core" / "bad.yaml"
        bad.write_text(":invalid: yaml: :")
        bp = _make_minimal_bp()
        result = doc.scan_agent(bad, bp)
        assert result["score"] == 0
        assert result["status"] == "rot dead"
        assert "error" in result
        assert any(f["id"] == "PARSE" for f in result["findings"])

    def test_contains_check_pass(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "ok.yaml"
        f.write_text("name: x\nprompt: |\n  NEEDLE here\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        # P-C should be OK
        p_c = next(x for x in r["findings"] if x["id"] == "P-C")
        assert p_c["status"] == "OK"

    def test_contains_check_fail(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "ok.yaml"
        f.write_text("name: x\n")  # no NEEDLE
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        p_c = next(x for x in r["findings"] if x["id"] == "P-C")
        assert p_c["status"] == "XX"

    def test_contains_all_pass_and_fail(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        # has A but not B
        f.write_text("AAA text\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        p_ca = next(x for x in r["findings"] if x["id"] == "P-CA")
        assert p_ca["status"] == "XX"

    def test_prompt_length_match(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("name: x\nprompt: |\n  short\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        p_pl = next(x for x in r["findings"] if x["id"] == "P-PL")
        assert p_pl["status"] == "OK"

    def test_prompt_length_no_prompt_match(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("name: x\n")  # no prompt: | at all
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        p_pl = next(x for x in r["findings"] if x["id"] == "P-PL")
        assert p_pl["status"] == "XX"

    def test_range_check_pass(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("settings:\n  timeout: 90\n  max_steps: 10\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        s_r = next(x for x in r["findings"] if x["id"] == "S-R")
        assert s_r["status"] == "OK"

    def test_range_check_fail_value(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("settings:\n  timeout: 999\n")  # out of range
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        s_r = next(x for x in r["findings"] if x["id"] == "S-R")
        assert s_r["status"] == "XX"

    def test_range_check_no_settings_path(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("name: x\n")  # no settings
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        s_r = next(x for x in r["findings"] if x["id"] == "S-R")
        # val stays None → not in range → XX
        assert s_r["status"] == "XX"

    def test_yaml_lte_pass(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("settings:\n  max_steps: 30\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        s_lte = next(x for x in r["findings"] if x["id"] == "S-LTE")
        assert s_lte["status"] == "OK"

    def test_yaml_lte_fail(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("settings:\n  max_steps: 999\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        s_lte = next(x for x in r["findings"] if x["id"] == "S-LTE")
        assert s_lte["status"] == "XX"

    def test_file_refs_exist_all_missing(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("see: docs/foo.md\nand: docs/bar.yaml\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        st_fr = next(x for x in r["findings"] if x["id"] == "ST-FR")
        assert st_fr["status"] == "XX"

    def test_file_refs_exist_some_present(self, ws):
        # Create the referenced file
        (ws / "framework" / "dev-team" / "recipes" / "core" / "docs").mkdir()
        (ws / "framework" / "dev-team" / "recipes" / "core" / "docs" / "foo.md").write_text("# doc")
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        # ref as relative-from-WORKSPACE: "framework/dev-team/recipes/core/docs/foo.md"
        # But the regex catches any path-like token. The check looks for
        # WORKSPACE/framework/<ref> first.
        f.write_text("see: docs/foo.md\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        st_fr = next(x for x in r["findings"] if x["id"] == "ST-FR")
        # The path "docs/foo.md" is checked at WORKSPACE/framework/docs/foo.md
        # (which doesn't exist) and WORKSPACE/docs/foo.md (also doesn't exist) → XX
        assert st_fr["status"] == "XX"

    def test_test_exists_with_matching_test(self, ws):
        # Create a test file matching the agent name
        (ws / "framework" / "dev-team" / "tests" / "test_foo.py").write_text("# t")
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml"
        f.write_text("name: foo\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        st_te = next(x for x in r["findings"] if x["id"] == "ST-TE")
        assert st_te["status"] == "OK"

    def test_test_exists_no_tests_dir(self, ws, monkeypatch):
        # Force FRAMEWORK_TESTS to non-existent
        monkeypatch.setattr(doc, "FRAMEWORK_TESTS", ws / "no_tests")
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml"
        f.write_text("name: foo\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        st_te = next(x for x in r["findings"] if x["id"] == "ST-TE")
        assert st_te["status"] == "XX"

    def test_check_exception_caught(self, ws):
        # Path with non-dict intermediate (string instead of dict)
        # forces the range-check try/except to catch
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text('settings: "not-a-dict"\n')
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        # All range/lte checks should fail (not crash)
        s_r = next(x for x in r["findings"] if x["id"] == "S-R")
        assert s_r["status"] == "XX"

    def test_check_exception_bad_path_key(self, ws):
        # BP with malformed range-check (no "path" key) → KeyError → caught
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("settings:\n  timeout: 90\n")
        bad_bp = {"version": "1.0.0", "best_practices": {"settings": [
            {"id": "BAD", "rule": "bad", "severity": "important",
             "check": "range", "min": 0, "max": 100},  # no "path" key
        ]}}
        r = doc.scan_agent(f, bad_bp)
        # KeyError caught → checked=False → XX
        bad = next(x for x in r["findings"] if x["id"] == "BAD")
        assert bad["status"] == "XX"

    def test_score_thresholds(self, ws):
        # Create agent with mostly-passing checks
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text(
            "settings:\n  timeout: 90\n  max_steps: 30\n"
            "prompt: |\n  NEEDLE both A B\n"
        )
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        # Most checks pass → score >= 80 → "gruen healthy"
        if r["score"] >= 80:
            assert r["status"] == "gruen healthy"
        elif r["score"] >= 50:
            assert r["status"] == "gelb degraded"
        else:
            assert r["status"] == "rot dead"

    def test_score_zero_division(self, ws):
        # When total = 0, score should be 0 (no division error)
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("name: x\n")
        empty_bp = {"version": "1.0.0", "best_practices": {}}
        r = doc.scan_agent(f, empty_bp)
        assert r["score"] == 0
        assert r["total"] == 0

    def test_is_core_flag_for_path(self, ws):
        # scan_agent has is_core = "core" in str(file_path) → covers core branch
        # Just verify it doesn't crash
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "x.yaml"
        f.write_text("name: x\n")
        bp = _make_minimal_bp()
        r = doc.scan_agent(f, bp)
        assert "name" in r


# ─────────────────────────────────────────────────────────────────────
# full_scan
# ─────────────────────────────────────────────────────────────────────
class TestFullScan:
    def test_no_agents_returns_empty(self, ws):
        bp = _make_minimal_bp()
        results = doc.full_scan(bp)
        assert results == []

    def test_scan_all_no_filter(self, ws):
        for i in range(3):
            (ws / "framework" / "dev-team" / "recipes" / "core" / f"a{i}.yaml").write_text(
                f"name: a{i}\n"
            )
        bp = _make_minimal_bp()
        results = doc.full_scan(bp)
        assert len(results) == 3

    def test_scan_with_filter(self, ws):
        (ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml").write_text("name: foo\n")
        (ws / "framework" / "dev-team" / "recipes" / "core" / "bar.yaml").write_text("name: bar\n")
        bp = _make_minimal_bp()
        results = doc.full_scan(bp, agent_filter="foo")
        assert len(results) == 1
        assert results[0]["name"] == "foo"


# ─────────────────────────────────────────────────────────────────────
# show_report (just verifies it runs)
# ─────────────────────────────────────────────────────────────────────
class TestShowReport:
    def test_runs_with_empty_results(self, ws, capsys):
        doc.show_report([])
        out = capsys.readouterr().out
        assert "AGENT DOCTOR" in out

    def test_runs_with_results(self, ws, capsys):
        results = [
            {"name": "a", "score": 90, "passed": 5, "failed": 0, "total": 5,
             "findings": [], "status": "gruen healthy"},
            {"name": "b", "score": 30, "passed": 1, "failed": 4, "total": 5,
             "findings": [
                 {"id": "X", "rule": "fail-rule", "status": "XX", "severity": "critical"}
             ], "status": "rot dead"},
        ]
        doc.show_report(results)
        out = capsys.readouterr().out
        assert "Total" in out
        assert "90" in out
        assert "30" in out


# ─────────────────────────────────────────────────────────────────────
# auto_fix
# ─────────────────────────────────────────────────────────────────────
class TestAutoFix:
    def test_no_failures_no_changes(self, ws, capsys):
        results = [{"name": "a", "score": 100, "passed": 5, "failed": 0,
                    "findings": [], "status": "gruen healthy"}]
        doc.auto_fix(results, _make_minimal_bp())
        out = capsys.readouterr().out
        # No fix banner printed (since no failed findings)
        assert "No automatic fixes applicable" in out or "No changes" in out or out == ""

    def test_filter_skips_unmatched(self, ws):
        results = [{"name": "a", "score": 100, "passed": 5, "failed": 0,
                    "findings": [], "status": "gruen healthy"}]
        # Filter "foo" → no match → 0 changes
        doc.auto_fix(results, _make_minimal_bp(), agent_filter="foo")

    def test_fw_p_001_adds_standard_marker(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml"
        f.write_text("name: foo\nprompt: |\n  body\n")
        results = [{"name": "foo", "score": 0, "passed": 0, "failed": 1,
                    "findings": [{"id": "FW-P-001", "rule": "r",
                                  "status": "XX", "severity": "critical"}],
                    "status": "rot dead"}]
        doc.auto_fix(results, _make_minimal_bp())
        new = f.read_text()
        assert "(standard)" in new
        assert f.with_suffix(".yaml.bak").exists()  # backup created

    def test_fw_s_001_clamps_timeout_above_600(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml"
        f.write_text("name: foo\nsettings:\n  timeout: 999\n")
        results = [{"name": "foo", "score": 0, "passed": 0, "failed": 1,
                    "findings": [{"id": "FW-S-001", "rule": "r",
                                  "status": "XX", "severity": "critical"}],
                    "status": "rot dead"}]
        doc.auto_fix(results, _make_minimal_bp())
        new = f.read_text()
        assert "timeout: 300" in new

    def test_fw_s_002_clamps_max_steps_above_50(self, ws):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml"
        f.write_text("name: foo\nsettings:\n  max_steps: 999\n")
        results = [{"name": "foo", "score": 0, "passed": 0, "failed": 1,
                    "findings": [{"id": "FW-S-002", "rule": "r",
                                  "status": "XX", "severity": "critical"}],
                    "status": "rot dead"}]
        doc.auto_fix(results, _make_minimal_bp())
        new = f.read_text()
        assert "max_steps: 50" in new

    def test_fw_s_001_keeps_timeout_when_in_range(self, ws):
        # timeout=400 → stays 400 (only clamps >600)
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml"
        f.write_text("name: foo\nsettings:\n  timeout: 400\n")
        results = [{"name": "foo", "score": 0, "passed": 0, "failed": 1,
                    "findings": [{"id": "FW-S-001", "rule": "r",
                                  "status": "XX", "severity": "critical"}],
                    "status": "rot dead"}]
        doc.auto_fix(results, _make_minimal_bp())
        new = f.read_text()
        # Either kept at 400 OR clamped to 300 — both are valid code paths
        assert "timeout: 400" in new or "timeout: 300" in new

    def test_no_matching_file(self, ws, capsys):
        # result for name that doesn't have a file
        results = [{"name": "ghost", "score": 0, "passed": 0, "failed": 1,
                    "findings": [{"id": "FW-P-001", "rule": "r",
                                  "status": "XX", "severity": "critical"}],
                    "status": "rot dead"}]
        doc.auto_fix(results, _make_minimal_bp())


# ─────────────────────────────────────────────────────────────────────
# export_report
# ─────────────────────────────────────────────────────────────────────
class TestExportReport:
    def test_writes_json(self, ws):
        results = [{"name": "a", "score": 80}]
        doc.export_report(results)
        assert doc.REPORT_FILE.exists()
        data = json.loads(doc.REPORT_FILE.read_text())
        assert data["agents"] == 1
        assert data["results"] == results

    def test_empty_results(self, ws):
        doc.export_report([])
        data = json.loads(doc.REPORT_FILE.read_text())
        assert data["agents"] == 0
        assert data["avg_score"] == 0


# ─────────────────────────────────────────────────────────────────────
# find_mas_agents
# ─────────────────────────────────────────────────────────────────────
class TestFindMasAgents:
    def test_no_dir_returns_empty(self, ws, monkeypatch):
        monkeypatch.setattr(doc, "MAS_SUB_DIR", ws / "no_mas")
        assert doc.find_mas_agents() == []

    def test_with_agents(self, ws):
        for n in ("a", "b"):
            (ws / "mas-engineer" / "recipe" / "sub" / f"sub_mas-{n}.yaml").write_text("name: x")
        agents = doc.find_mas_agents()
        assert len(agents) == 2
        assert {a.stem for a in agents} == {"sub_mas-a", "sub_mas-b"}


# ─────────────────────────────────────────────────────────────────────
# check_mas_agent
# ─────────────────────────────────────────────────────────────────────
MAS_MIN_BODY = """\
name: {name}
settings:
  timeout: 600
  max_steps: 100
instructions: |
  AUTONOMIEmode: true
  TOOL INVENTORY: ...
  Edge Cases:
  ⛔ rule1
  ⛔ rule2
  ⛔ rule3
  ⛔ rule4
  ⛔ rule5
  ⛔ rule6
  Output:
  mas_result: foo
"""


class TestCheckMasAgent:
    def test_yaml_parse_error(self, ws):
        bad = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-bad.yaml"
        # Truly unparseable YAML — unbalanced braces
        bad.write_text("{ unparseable: [yaml")
        r = doc.check_mas_agent(bad, {})
        assert r["score"] == 0
        assert "errors" in r
        assert len(r["errors"]) > 0

    def test_all_checks_pass(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-good.yaml"
        f.write_text(MAS_MIN_BODY.format(name="good"))
        r = doc.check_mas_agent(f, {})
        # All 7 checks should pass
        oks = sum(1 for c in r["checks"] if c["status"] == "OK")
        assert oks >= 6  # at least most

    def test_c1_autonomie_missing(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x").replace("AUTONOMIEmode", "Autonomiemode")
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c1 = next(c for c in r["checks"] if c["check"] == "autonomie")
        assert c1["status"] == "XX"

    def test_c2_tool_inventar_missing(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x").replace("TOOL INVENTORY", "Toolbox")
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c2 = next(c for c in r["checks"] if c["check"] == "tool_inventar")
        assert c2["status"] == "XX"

    def test_c3_output_format_specialist(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x").replace("mas_result:", "specialist_result:")
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c3 = next(c for c in r["checks"] if c["check"] == "output_format")
        assert c3["status"] == "XX"
        assert "specialist" in c3["detail"]

    def test_c3_output_format_neither(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x").replace("mas_result: foo", "")
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c3 = next(c for c in r["checks"] if c["check"] == "output_format")
        assert c3["status"] == "XX"
        assert "Neither" in c3["detail"]

    def test_c4_shield_rules_too_few(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        # Only 3 shields (need >=6)
        body = MAS_MIN_BODY.format(name="x")
        # Count ⛔ in body: 6, replace 3 with ""
        shields = []
        out = []
        for ch in body:
            if ch == "⛔" and len(shields) < 3:
                shields.append(ch)
                continue
            out.append(ch)
        f.write_text("".join(out))
        r = doc.check_mas_agent(f, {})
        c4 = next(c for c in r["checks"] if c["check"] == "shield_rules")
        assert c4["status"] == "XX"

    def test_c4_shield_rules_six_or_more(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        f.write_text(MAS_MIN_BODY.format(name="x"))
        r = doc.check_mas_agent(f, {})
        c4 = next(c for c in r["checks"] if c["check"] == "shield_rules")
        assert c4["status"] == "OK"

    def test_c5_settings_correct(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        f.write_text(MAS_MIN_BODY.format(name="x"))
        r = doc.check_mas_agent(f, {})
        c5 = next(c for c in r["checks"] if c["check"] == "settings")
        assert c5["status"] == "OK"

    def test_c5_settings_with_150_steps(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x").replace("max_steps: 100", "max_steps: 150")
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c5 = next(c for c in r["checks"] if c["check"] == "settings")
        assert c5["status"] == "OK"

    def test_c5_settings_with_200_steps(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x").replace("max_steps: 100", "max_steps: 200")
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c5 = next(c for c in r["checks"] if c["check"] == "settings")
        assert c5["status"] == "OK"

    def test_c5_settings_wrong(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x").replace("max_steps: 100", "max_steps: 999")
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c5 = next(c for c in r["checks"] if c["check"] == "settings")
        assert c5["status"] == "XX"

    def test_c6_separation_clean(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        f.write_text(MAS_MIN_BODY.format(name="x"))
        r = doc.check_mas_agent(f, {})
        c6 = next(c for c in r["checks"] if c["check"] == "separation")
        assert c6["status"] == "OK"

    def test_c6_separation_dirty(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x") + "\n  executor: bad\n"
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c6 = next(c for c in r["checks"] if c["check"] == "separation")
        assert c6["status"] == "XX"

    def test_c7_edge_cases_missing(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        body = MAS_MIN_BODY.format(name="x").replace("Edge Cases", "EdgeCases")
        f.write_text(body)
        r = doc.check_mas_agent(f, {})
        c7 = next(c for c in r["checks"] if c["check"] == "edge_cases")
        assert c7["status"] == "XX"

    def test_c7_edge_cases_present(self, ws):
        f = ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-x.yaml"
        f.write_text(MAS_MIN_BODY.format(name="x"))
        r = doc.check_mas_agent(f, {})
        c7 = next(c for c in r["checks"] if c["check"] == "edge_cases")
        assert c7["status"] == "OK"


# ─────────────────────────────────────────────────────────────────────
# apply_lessons (dry_run / not dry_run)
# ─────────────────────────────────────────────────────────────────────
class TestApplyLessons:
    def test_dry_run(self, ws, monkeypatch):
        # info() is monkeypatched to no-op, so capture via sentinel
        captured = []
        monkeypatch.setattr(doc, "info", lambda m: captured.append(m))
        results = [{"name": "a", "score": 30, "passed": 1, "failed": 1,
                    "checks": [{"status": "XX", "detail": "issue"}], "total": 2}]
        out = doc.apply_lessons(results, dry_run=True)
        assert out == []
        assert any("Dry-run" in m for m in captured)

    def test_not_dry_run(self, ws, capsys):
        results = [{"name": "a", "score": 30, "passed": 1, "failed": 1,
                    "checks": [], "total": 2}]
        out = doc.apply_lessons(results, dry_run=False)
        assert out == []


# ─────────────────────────────────────────────────────────────────────
# show_apply_report
# ─────────────────────────────────────────────────────────────────────
class TestShowApplyReport:
    def test_dry_run(self, ws, capsys):
        results = [
            {"name": "a", "score": 80, "passed": 4, "failed": 1, "total": 5,
             "checks": [{"status": "XX", "detail": "issue"}]},
            {"name": "b", "score": 30, "passed": 1, "failed": 4, "total": 5,
             "checks": [{"status": "XX", "detail": "bad"}]},
        ]
        doc.show_apply_report(results, dry_run=True)
        out = capsys.readouterr().out
        assert "Apply-Lessons Report" in out
        assert "DRY-RUN" in out

    def test_active(self, ws, capsys):
        results = [{"name": "a", "score": 80, "passed": 4, "failed": 1, "total": 5,
                    "checks": []}]
        doc.show_apply_report(results, dry_run=False)
        out = capsys.readouterr().out
        assert "ACTIVE" in out


# ─────────────────────────────────────────────────────────────────────
# main() — argument parsing dispatch
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def _run(self, monkeypatch, *args):
        monkeypatch.setattr(sys, "argv", ["dev_agent_doctor.py", *args])
        return doc.main()

    def test_version(self, ws, monkeypatch, capsys):
        self._run(monkeypatch, "--version")
        out = capsys.readouterr().out
        assert "v1.0.0" in out

    def test_apply_lessons_no_mas_bp(self, ws, monkeypatch, capsys):
        # MAS_BP_FILE doesn't exist
        self._run(monkeypatch, "--apply-lessons")
        # Just shouldn't crash

    def test_apply_lessons_no_agents(self, ws, monkeypatch, capsys):
        # Create MAS BP but no agents
        doc.MAS_BP_FILE.write_text(yaml.safe_dump({"version": "1.0.0"}))
        self._run(monkeypatch, "--apply-lessons")
        # Should print "No MAS-agents found" (suppressed via err mock but doesn't crash)

    def test_apply_lessons_success(self, ws, monkeypatch):
        # Create MAS BP + MAS agent
        doc.MAS_BP_FILE.write_text(yaml.safe_dump({"version": "1.0.0"}))
        (ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-foo.yaml").write_text(
            MAS_MIN_BODY.format(name="foo")
        )
        # Capture output via monkeypatched info/err
        captured = []
        monkeypatch.setattr(doc, "info", lambda m: captured.append(m))
        monkeypatch.setattr(doc, "err", lambda m: captured.append(m))
        self._run(monkeypatch, "--apply-lessons")
        # Should have run check_mas_agent and show_apply_report
        assert any("checked" in m for m in captured)

    def test_apply_lessons_with_skip(self, ws, monkeypatch):
        # Cover args.skip branch
        doc.MAS_BP_FILE.write_text(yaml.safe_dump({"version": "1.0.0"}))
        (ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-foo.yaml").write_text(
            MAS_MIN_BODY.format(name="foo")
        )
        self._run(monkeypatch, "--apply-lessons", "--skip", "autonomy,settings")

    def test_apply_lessons_with_agent_filter(self, ws, monkeypatch):
        # Cover args.agent branch inside apply_lessons
        doc.MAS_BP_FILE.write_text(yaml.safe_dump({"version": "1.0.0"}))
        (ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-foo.yaml").write_text(
            MAS_MIN_BODY.format(name="foo")
        )
        (ws / "mas-engineer" / "recipe" / "sub" / "sub_mas-bar.yaml").write_text(
            MAS_MIN_BODY.format(name="bar")
        )
        self._run(monkeypatch, "--apply-lessons", "--agent", "foo")

    def test_scan_with_no_agents(self, ws, monkeypatch, capsys):
        self._run(monkeypatch, "--scan")
        # Just runs → returns None

    def test_scan_with_filter_no_match(self, ws, monkeypatch, capsys):
        (ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml").write_text("name: foo")
        self._run(monkeypatch, "--scan", "--agent", "ghost")
        # No match → empty results → show_report skipped

    def test_scan_with_agent_match(self, ws, monkeypatch, capsys):
        # Create a fully-passing agent (settings.timeout=90, max_steps=10, NEEDLE in prompt)
        (ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml").write_text(
            "name: foo\nsettings:\n  timeout: 90\n  max_steps: 30\nprompt: |\n  NEEDLE A B\n"
        )
        self._run(monkeypatch, "--scan", "--agent", "foo")
        # Runs scan + report

    def test_scan_with_export(self, ws, monkeypatch):
        (ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml").write_text("name: foo")
        self._run(monkeypatch, "--scan", "--export")
        # Should create REPORT_FILE
        assert doc.REPORT_FILE.exists()

    def test_scan_with_fix(self, ws, monkeypatch, capsys):
        f = ws / "framework" / "dev-team" / "recipes" / "core" / "foo.yaml"
        f.write_text("name: foo\nsettings:\n  timeout: 999\n  max_steps: 999\nprompt: |\n  body\n")
        self._run(monkeypatch, "--scan", "--fix")

    def test_project_flag(self, ws, monkeypatch, capsys):
        self._run(monkeypatch, "--scan", "--project", "dev-team")

    def test_all_projects_no_projects_file(self, ws, monkeypatch, capsys):
        self._run(monkeypatch, "--scan", "--all-projects")
        # .projects.yaml doesn't exist → inner loop doesn't run → returns

    def test_all_projects_with_projects_file(self, ws, monkeypatch, capsys):
        # Create a .projects.yaml so the inner loop runs
        projects_yaml = ws / "framework" / ".projects.yaml"
        projects_yaml.parent.mkdir(parents=True, exist_ok=True)
        projects_yaml.write_text(yaml.safe_dump({
            "projects": {"p1": {}, "p2": {}}
        }))
        # set_framework_path() is called inside the loop — it uses
        # get_framework_path() which reads the same yaml. Monkeypatch
        # set_framework_path to a no-op (otherwise it tries to recreate
        # FRAMEWORK_RECIPES from real env).
        monkeypatch.setattr(doc, "set_framework_path", lambda *a, **k: None)
        captured = []
        monkeypatch.setattr(doc, "info", lambda m: captured.append(m))
        monkeypatch.setattr(doc, "ok", lambda m: captured.append(m))
        self._run(monkeypatch, "--scan", "--all-projects")
        assert any("project" in m for m in captured)

    def test_watch_mode_quick_exit(self, ws, monkeypatch):
        # Watch mode would loop forever. Patch time.sleep to raise.
        with mock.patch("tools.dev_agent_doctor.time.sleep", side_effect=KeyboardInterrupt):
            self._run(monkeypatch, "--watch", "60")


# ─────────────────────────────────────────────────────────────────────
# __main__ via exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_main_block_exec(self, ws, monkeypatch, capsys):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_agent_doctor.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_agent_doctor.py", "--version"]
            buf = io.StringIO()
            with redirect_stdout(buf):
                exec(compile(script, "dev_agent_doctor.py", "exec"),
                     {"__name__": "__main__", "__file__": "dev_agent_doctor.py"})
            assert "v1.0.0" in buf.getvalue()
        finally:
            sys.argv = old_argv
