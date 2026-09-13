#!/usr/bin/env python3
"""
R110-516: Coverage test for tools/dev_pattern_apply.py (39 stmts, 0% → 100%).

Context: dev_pattern_apply.py applies high-confidence patterns from a
registry file to YAML files in a project directory. It walks the project
recursively, filters .yaml files, and for each pattern above the
threshold and auto-applied to the project, it generates up to 3 "apply"
entries per pattern. Patterns below threshold are counted as skipped.
The registry is updated in-place to track auto_applied_to.

Module structure (55 lines, 39 stmts):
  - get_scoped_agents(pattern_name, project_files) — returns the first
    3 .yaml files in project_files (the dict mapping at lines 8-14 is
    declared but never used; the actual filter is line 15). 39 stmts
    includes the unused mapping lambdas.

  - load(path) — opens a YAML file, returns parsed dict or {} on parse
    error.

  - apply_patterns(registry_path, project, threshold=0.3) — main
    orchestrator: load registry, walk project, iterate patterns,
    filter by threshold, filter by auto_applied gate, generate
    applied entries, write registry back. Returns {applied, skipped}.

  - __main__ guard: argparse + call + print(json.dumps).

This file tests all kernel code paths and the unused-but-declared
mapping dict (which counts toward branch coverage even though it's
dead code).
"""

import json
import runpy
import sys
from pathlib import Path

import pytest
import yaml

import tools.dev_pattern_apply as pa  # noqa: E402


# ─── load() ─────────────────────────────────────────────────────────

def test_load_parses_valid_yaml(tmp_path):
    """Covers line 19: yaml.safe_load returns parsed dict on valid file."""
    p = tmp_path / "ok.yaml"
    p.write_text(yaml.dump({"a": 1, "b": [1, 2, 3]}))
    assert pa.load(str(p)) == {"a": 1, "b": [1, 2, 3]}


def test_load_returns_empty_dict_on_invalid_yaml(tmp_path):
    """Covers line 20: yaml.YAMLError → except branch returns {}."""
    p = tmp_path / "bad.yaml"
    p.write_text("key: [unclosed")  # malformed YAML
    result = pa.load(str(p))
    assert result == {}


# ─── get_scoped_agents ──────────────────────────────────────────────

def test_get_scoped_agents_filters_yaml_files():
    """Covers line 15: list comprehension over .yaml files only."""
    files = [
        "/p/a.yaml",
        "/p/b.yml",
        "/p/c.txt",
        "/p/d.yaml",
        "/p/e.json",
    ]
    result = pa.get_scoped_agents("any_pattern", files)
    assert result == ["/p/a.yaml", "/p/d.yaml"]


def test_get_scoped_agents_returns_empty_when_no_yaml_files():
    """Covers line 15: empty list when no .yaml files present."""
    assert pa.get_scoped_agents("any", ["/p/a.txt", "/p/b.json"]) == []


# ─── apply_patterns ─────────────────────────────────────────────────

def _write_registry(tmp_path, patterns):
    """Helper: write a registry file with the given patterns list."""
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.dump({"patterns": patterns}))
    return str(reg_path)


def _write_project(tmp_path, yamls):
    """Helper: create a project dir with the given list of YAML filenames."""
    proj = tmp_path / "project"
    proj.mkdir()
    for name in yamls:
        (proj / name).write_text("a: 1\n")
    return str(proj)


def test_apply_patterns_skips_below_threshold(tmp_path):
    """Covers lines 32-35: pattern with confidence < threshold → skipped."""
    reg = _write_registry(tmp_path, [
        {"name": "low", "confidence": 0.1, "auto_applied": True,
         "rule": "do X"},
    ])
    proj = _write_project(tmp_path, ["a.yaml", "b.yaml"])
    result = pa.apply_patterns(reg, proj, threshold=0.5)
    assert result == {"applied": [], "skipped": 1}


def test_apply_patterns_does_not_auto_apply_when_auto_applied_false(tmp_path):
    """Covers line 36: auto_applied gate — when False, skip even if
    confidence is high."""
    reg = _write_registry(tmp_path, [
        {"name": "manual_only", "confidence": 0.9,
         "auto_applied": False, "rule": "do Y"},
    ])
    proj = _write_project(tmp_path, ["a.yaml"])
    result = pa.apply_patterns(reg, proj, threshold=0.3)
    assert result["applied"] == []
    assert result["skipped"] == 0  # 0.9 >= 0.3, so threshold passes;
    # but auto_applied=False skips the apply step without incrementing skipped


def test_apply_patterns_caps_at_three_files_per_pattern(tmp_path):
    """Covers lines 38-41: candidates[:3] limits applied entries to 3."""
    reg = _write_registry(tmp_path, [
        {"name": "p1", "confidence": 0.9, "auto_applied": True,
         "rule": "Apply X"},
    ])
    proj = _write_project(tmp_path, ["a.yaml", "b.yaml", "c.yaml",
                                     "d.yaml", "e.yaml"])
    result = pa.apply_patterns(reg, proj, threshold=0.3)
    # Exactly 3 applied entries (candidates[:3])
    assert len(result["applied"]) == 3
    # All entries reference the pattern name and have status='pending'
    for entry in result["applied"]:
        assert entry["pattern"] == "p1"
        assert entry["status"] == "pending"
        assert "Apply X" in entry["action"]


def test_apply_patterns_writes_registry_back_with_auto_applied_to(tmp_path):
    """Covers lines 42-44: auto_applied_to updated + yaml.dump round-trip."""
    reg = _write_registry(tmp_path, [
        {"name": "p1", "confidence": 0.9, "auto_applied": True,
         "rule": "Apply Z"},
    ])
    proj = _write_project(tmp_path, ["a.yaml"])
    pa.apply_patterns(reg, proj, threshold=0.3)
    # Reload registry and verify auto_applied_to was appended
    reg_data = yaml.safe_load(Path(reg).read_text())
    pat = reg_data["patterns"][0]
    assert "auto_applied_to" in pat
    assert proj in pat["auto_applied_to"]


def test_apply_patterns_skips_pattern_already_applied_to_project(tmp_path):
    """Covers line 36 second clause: when project IS in auto_applied_to,
    skip without applying (idempotency guard)."""
    proj = _write_project(tmp_path, ["a.yaml"])
    reg = _write_registry(tmp_path, [
        {"name": "p1", "confidence": 0.9, "auto_applied": True,
         "auto_applied_to": [proj],  # already applied to this proj
         "rule": "Apply W"},
    ])
    result = pa.apply_patterns(reg, proj, threshold=0.3)
    # Project in auto_applied_to → skip (no applied entries, no skipped bump)
    assert result["applied"] == []
    assert result["skipped"] == 0


def test_apply_patterns_walks_subdirectories(tmp_path):
    """Covers lines 27-30: os.walk finds .yaml files in subdirectories,
    and the for-loop body runs at least once (branch 29->28 backward)."""
    reg = _write_registry(tmp_path, [
        {"name": "p1", "confidence": 0.9, "auto_applied": True,
         "rule": "Apply"},
    ])
    proj = tmp_path / "project"
    proj.mkdir()
    # Subdirectory with .yaml AND a .txt to exercise the
    # `if f.endswith('.yaml'):` False branch (29->28 backward edge).
    sub = proj / "subdir"
    sub.mkdir()
    (sub / "deep.yaml").write_text("x: 1\n")
    (sub / "ignored.txt").write_text("not yaml\n")
    (proj / "top.yaml").write_text("y: 2\n")
    result = pa.apply_patterns(reg, str(proj), threshold=0.3)
    # Both .yaml files should be in applied (capped at 3)
    applied_files = [e["file"] for e in result["applied"]]
    assert any("deep.yaml" in f for f in applied_files)
    assert any("top.yaml" in f for f in applied_files)
    # .txt file is NOT in applied
    assert not any("ignored.txt" in f for f in applied_files)


def test_apply_patterns_uses_default_threshold_when_not_specified(tmp_path):
    """Covers line 22 default threshold=0.3 + line 33 comparison."""
    reg = _write_registry(tmp_path, [
        {"name": "just_above", "confidence": 0.31, "auto_applied": True,
         "rule": "do something"},
    ])
    proj = _write_project(tmp_path, ["a.yaml"])
    result = pa.apply_patterns(reg, proj)  # no threshold arg
    # 0.31 > 0.3 (default), so applies
    assert len(result["applied"]) == 1


def test_apply_patterns_threshold_filters_at_exactly_threshold(tmp_path):
    """Covers line 33: p.get('confidence', 0) < threshold is strict,
    so confidence == threshold is kept (not skipped)."""
    reg = _write_registry(tmp_path, [
        {"name": "exact", "confidence": 0.3, "auto_applied": True,
         "rule": "exact match"},
    ])
    proj = _write_project(tmp_path, ["a.yaml"])
    result = pa.apply_patterns(reg, proj, threshold=0.3)
    assert len(result["applied"]) == 1  # kept, not skipped


def test_apply_patterns_missing_conf_defaults_to_zero_below_threshold(tmp_path):
    """Covers line 33: p.get('confidence', 0) — when key missing,
    defaults to 0 → skipped."""
    reg = _write_registry(tmp_path, [
        {"name": "no_conf", "auto_applied": True, "rule": "x"},
    ])
    proj = _write_project(tmp_path, ["a.yaml"])
    result = pa.apply_patterns(reg, proj, threshold=0.3)
    assert result == {"applied": [], "skipped": 1}


# ─── __main__ guard ─────────────────────────────────────────────────

def test_main_block_via_runpy(tmp_path, monkeypatch, capsys):
    """Covers lines 47-55: argparse + apply_patterns + json.dumps print."""
    reg = _write_registry(tmp_path, [
        {"name": "via_runpy", "confidence": 0.5, "auto_applied": True,
         "rule": "runpy test"},
    ])
    proj = _write_project(tmp_path, ["a.yaml"])
    monkeypatch.setattr(sys, "argv", [
        "dev_pattern_apply.py",
        "--registry", reg,
        "--project", proj,
        "--threshold", "0.3",
    ])
    # Source ends with `print(json.dumps(...))` — no sys.exit call.
    # runpy.run_path with __name__='__main__' will return cleanly.
    runpy.run_path(pa.__file__, run_name="__main__")
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "applied" in parsed
    assert "skipped" in parsed
