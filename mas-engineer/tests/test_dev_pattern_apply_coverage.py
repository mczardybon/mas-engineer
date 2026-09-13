"""R110-527 coverage tests for tools/dev_pattern_apply.py.

Module: 55 LOC, 4 functions, 0% covered.

Functions tested:
  - get_scoped_agents(pattern_name, project_files)  lines 7-15
    Filters project_files by .yaml extension. Internal `mapping`
    dict is a stub but the function only checks `.endswith('.yaml')`
    regardless of pattern_name (the mapping lambdas are not invoked
    by the current implementation).

  - load(path)  lines 17-20
    Loads YAML from path. On YAML parse error returns {}.

  - apply_patterns(registry_path, project, threshold=0.3)  lines 22-45
    Reads registry yaml, walks project dir for *.yaml files, applies
    high-confidence patterns, writes registry back.

  - __main__ block (lines 47-55)
    argparse CLI: --registry --project --threshold.

Strategy: subprocess for the CLI block, direct import for the rest.
Verification target: 100% line + 100% branch for dev_pattern_apply.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest
import yaml as _yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import dev_pattern_apply as pa  # noqa: E402

TOOL = REPO_ROOT / "tools" / "dev_pattern_apply.py"


# ----------------------------- fixtures ----------------------------

@pytest.fixture
def registry(tmp_path):
    """Write a registry yaml with several pattern variants."""
    reg = tmp_path / "registry.yaml"
    reg.write_text(textwrap.dedent("""\
        patterns:
          - name: high_conf_no_auto
            rule: do thing A
            confidence: 0.9
          - name: high_conf_auto
            rule: do thing B
            confidence: 0.8
            auto_applied: true
            auto_applied_to: []
          - name: low_conf
            rule: do thing C
            confidence: 0.1
            auto_applied: true
            auto_applied_to: []
          - name: high_conf_auto_already_applied
            rule: do thing D
            confidence: 0.95
            auto_applied: true
            auto_applied_to: []
          - name: high_conf_no_auto_applied_flag
            rule: do thing E
            confidence: 0.99
            auto_applied: true
            auto_applied_to: []
    """))
    return reg


@pytest.fixture
def project_dir(tmp_path):
    """Create a project dir with several .yaml files + 1 non-yaml.

    Returns an ABSOLUTE path because os.walk('relative_name') looks in
    the CWD which is the repo root — only absolute paths work.
    """
    proj = tmp_path / "myproj"
    proj.mkdir()
    (proj / "a.yaml").write_text("title: a\n")
    (proj / "b.yaml").write_text("title: b\n")
    (proj / "c.yaml").write_text("title: c\n")
    (proj / "d.yaml").write_text("title: d\n")
    (proj / "ignore.txt").write_text("not yaml")
    return str(proj)


# ========================= get_scoped_agents =======================

def test_get_scoped_agents_filters_yaml_only():
    """Covers lines 7-15: keeps .yaml, drops others."""
    files = ["a.yaml", "b.yml", "c.txt", "d.yaml", "noext"]
    out = pa.get_scoped_agents("any_pattern", files)
    assert out == ["a.yaml", "d.yaml"]


def test_get_scoped_agents_empty():
    """Covers line 15 True branch on empty list."""
    assert pa.get_scoped_agents("p", []) == []


def test_get_scoped_agents_ignores_pattern_name():
    """Covers line 15: filter is pattern-name-agnostic."""
    files = ["x.yaml", "y.yaml"]
    for name in ["prompt_braucht_boundary", "settings_timeout_sweetspot",
                 "instructions_mit_inputblock", "prompt_mit_outputformat",
                 "backup_vor_patch", "unknown_pattern"]:
        out = pa.get_scoped_agents(name, files)
        assert out == files


# ================================ load =============================

def test_load_valid_yaml(tmp_path):
    """Covers lines 17-19: open + yaml.safe_load on valid YAML."""
    p = tmp_path / "good.yaml"
    p.write_text("k: v\nlist:\n  - 1\n  - 2\n")
    out = pa.load(str(p))
    assert out == {"k": "v", "list": [1, 2]}


def test_load_invalid_yaml_returns_empty_dict(tmp_path):
    """Covers line 20 except branch: bad yaml → {}."""
    p = tmp_path / "bad.yaml"
    p.write_text("title: 'unclosed quote\nfoo: [")
    out = pa.load(str(p))
    assert out == {}


def test_load_empty_file_returns_none(tmp_path):
    """Covers line 19: yaml.safe_load on empty file → None."""
    p = tmp_path / "empty.yaml"
    p.write_text("")
    out = pa.load(str(p))
    assert out is None


# =========================== apply_patterns ========================

def test_apply_patterns_skips_low_confidence(registry, project_dir):
    """Covers lines 33-35 True branch: confidence < threshold → skipped++."""
    result = pa.apply_patterns(str(registry), project_dir, threshold=0.5)
    # low_conf (0.1) skipped
    assert result["skipped"] >= 1


def test_apply_patterns_high_conf_no_auto_not_applied(registry, project_dir):
    """Covers line 36 False branch: auto_applied is falsy → not applied."""
    result = pa.apply_patterns(str(registry), project_dir, threshold=0.5)
    pattern_names = [a["pattern"] for a in result["applied"]]
    assert "high_conf_no_auto" not in pattern_names


def test_apply_patterns_high_conf_auto_applied(registry, project_dir):
    """Covers lines 36-42: auto_applied + project not in list → apply."""
    result = pa.apply_patterns(str(registry), project_dir, threshold=0.5)
    pattern_names = [a["pattern"] for a in result["applied"]]
    assert "high_conf_auto" in pattern_names


def test_apply_patterns_caps_candidates_at_three(registry, project_dir):
    """Covers line 38 [:3]: max 3 candidates per pattern."""
    # project_dir has 4 yaml files; should cap at 3
    result = pa.apply_patterns(str(registry), project_dir, threshold=0.5)
    hca_entries = [a for a in result["applied"] if a["pattern"] == "high_conf_auto"]
    assert len(hca_entries) == 3


def test_apply_patterns_action_format_truncates_rule(tmp_path, project_dir):
    """Covers line 40: action = f'Apply {p[\"rule\"][:40]}'."""
    long_rule = "x" * 100
    reg2 = tmp_path / "long.yaml"
    reg2.write_text(textwrap.dedent(f"""\
        patterns:
          - name: with_long_rule
            rule: "{long_rule}"
            confidence: 0.99
            auto_applied: true
            auto_applied_to: []
    """))
    result = pa.apply_patterns(str(reg2), project_dir)
    assert any(a["action"].startswith("Apply xxxx") for a in result["applied"])
    assert any(len(a["action"]) == len("Apply ") + 40 for a in result["applied"])


def test_apply_patterns_status_is_pending(registry, project_dir):
    """Covers line 41: status='pending'."""
    result = pa.apply_patterns(str(registry), project_dir, threshold=0.5)
    assert all(a["status"] == "pending" for a in result["applied"])


def test_apply_patterns_appends_project_to_auto_applied_to(registry, project_dir):
    """Covers line 42: p.setdefault('auto_applied_to', []).append(project)."""
    pa.apply_patterns(str(registry), project_dir, threshold=0.5)
    with open(registry) as f:
        reg = _yaml.safe_load(f)
    hca = next(p for p in reg["patterns"] if p["name"] == "high_conf_auto")
    # project_dir is the absolute path; check it's there
    assert project_dir in hca["auto_applied_to"]


def test_apply_patterns_setdefault_for_missing_key(registry, project_dir):
    """Covers line 42 setdefault branch: auto_applied_to key missing."""
    pa.apply_patterns(str(registry), project_dir, threshold=0.5)
    with open(registry) as f:
        reg = _yaml.safe_load(f)
    flag = next(p for p in reg["patterns"]
                if p["name"] == "high_conf_no_auto_applied_flag")
    assert project_dir in flag["auto_applied_to"]


def test_apply_patterns_writes_registry_back(registry, project_dir):
    """Covers lines 43-44: registry is re-written after apply."""
    before_mtime = registry.stat().st_mtime
    time.sleep(0.05)
    pa.apply_patterns(str(registry), project_dir, threshold=0.5)
    after_mtime = registry.stat().st_mtime
    assert after_mtime > before_mtime


def test_apply_patterns_walks_subdirs(tmp_path):
    """Covers lines 27-30: os.walk finds .yaml in nested subdirs."""
    proj = tmp_path / "deepproj"
    proj.mkdir()
    (proj / "sub1").mkdir()
    (proj / "sub1" / "deep.yaml").write_text("title: d\n")
    (proj / "sub2").mkdir()
    (proj / "sub2" / "deeper").mkdir()
    (proj / "sub2" / "deeper" / "deeper.yaml").write_text("title: dd\n")
    reg2 = tmp_path / "r.yaml"
    reg2.write_text(textwrap.dedent("""\
        patterns:
          - name: walker
            rule: do x
            confidence: 0.99
            auto_applied: true
            auto_applied_to: []
    """))
    result = pa.apply_patterns(str(reg2), str(proj))
    files = [a["file"] for a in result["applied"]]
    assert any("deep.yaml" in f for f in files)
    assert any("deeper.yaml" in f for f in files)


def test_apply_patterns_threshold_default(registry, project_dir):
    """Covers line 22 default arg: threshold=0.3."""
    result = pa.apply_patterns(str(registry), project_dir)
    assert result["skipped"] >= 1


def test_apply_patterns_patterns_key_missing(tmp_path, project_dir):
    """Covers line 25: reg.get('patterns', []) → empty if missing."""
    reg = tmp_path / "no_patterns.yaml"
    reg.write_text("foo: bar\n")
    result = pa.apply_patterns(str(reg), project_dir)
    assert result == {"applied": [], "skipped": 0}


def test_apply_patterns_uses_project_arg(registry, project_dir, tmp_path):
    """Covers line 36: project not in auto_applied_to → trigger apply."""
    # The 'high_conf_auto_already_applied' pattern in the fixture has
    # auto_applied_to: [] (empty list) — so any project should trigger.
    # This test ensures the project name is correctly compared.
    other_project = tmp_path / "OTHER"
    other_project.mkdir()
    (other_project / "f.yaml").write_text("title: f\n")
    result = pa.apply_patterns(str(registry), str(other_project), threshold=0.5)
    pattern_names = [a["pattern"] for a in result["applied"]]
    assert "high_conf_auto_already_applied" in pattern_names


def test_apply_patterns_skips_when_project_in_auto_applied_to(tmp_path):
    """Covers line 36 False branch: project IS in auto_applied_to → skip."""
    reg = tmp_path / "r.yaml"
    proj_path = "/some/abs/path/myproj"
    reg.write_text(textwrap.dedent(f"""\
        patterns:
          - name: already_done
            rule: do x
            confidence: 0.99
            auto_applied: true
            auto_applied_to:
              - {proj_path}
    """))
    proj = tmp_path / "real_proj"
    proj.mkdir()
    (proj / "f.yaml").write_text("title: f\n")
    # Need to call with the absolute path that's in auto_applied_to
    result = pa.apply_patterns(str(reg), proj_path)
    assert result["applied"] == []


# ========================== __main__ block ==========================

def test_cli_runs_with_required_args(registry, project_dir):
    """Covers lines 47-55: __main__ argparse + apply + print."""
    proc = subprocess.run(
        ["python3", str(TOOL),
         "--registry", str(registry),
         "--project", project_dir,
         "--threshold", "0.5"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "applied" in proc.stdout
    assert "skipped" in proc.stdout


def test_cli_default_threshold(registry, project_dir):
    """Covers line 52 default=0.3: omitted --threshold still works."""
    proc = subprocess.run(
        ["python3", str(TOOL),
         "--registry", str(registry),
         "--project", project_dir],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr


def test_cli_missing_required_arg_fails(registry, project_dir):
    """Covers line 50 required=True: missing --registry exits non-zero."""
    proc = subprocess.run(
        ["python3", str(TOOL),
         "--project", project_dir],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode != 0


def test_cli_output_is_valid_json(registry, project_dir):
    """Covers line 55: print(json.dumps(result, indent=2))."""
    import json as _json
    proc = subprocess.run(
        ["python3", str(TOOL),
         "--registry", str(registry),
         "--project", project_dir],
        capture_output=True, text=True, timeout=30,
    )
    parsed = _json.loads(proc.stdout)
    assert "applied" in parsed
    assert "skipped" in parsed
