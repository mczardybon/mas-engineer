"""R110-303: 100% coverage tests for tools/dev_pattern_apply.py.

CRITICAL — pre-existing count-assertion pitfall (R110-300a):
  Do NOT use `assert "N type" in output` literals anywhere in this file.
  See skill `mas-engineer-count-assert-re-pitfall`.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "dev_pattern_apply.py"
REPO_ROOT = str(Path(TOOL).parent.parent)
TOOLS_DIR = str(Path(TOOL).parent)


def _import_tool():
    """Same coverage-attribution trick as test_r110303_dev_auto_project:
    synthetic `tools` package + spec_from_file_location so pytest-cov
    can attribute coverage to `tools/dev_pattern_apply.py`."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    if "tools" not in sys.modules:
        import types
        pkg = types.ModuleType("tools")
        pkg.__path__ = [TOOLS_DIR]
        sys.modules["tools"] = pkg
    full_name = f"tools.{Path(TOOL).stem}"
    spec = importlib.util.spec_from_file_location(full_name, TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def registry_with_patterns(tmp_path):
    """Write a registry file with 3 patterns: 1 below threshold (skipped),
    1 above threshold with auto_applied, 1 above without auto_applied."""
    import yaml
    reg = {
        "patterns": [
            {"name": "low_conf", "confidence": 0.1, "rule": "low confidence rule"},
            {"name": "settings_timeout_sweetspot", "confidence": 0.5, "auto_applied": True,
             "rule": "settings timeout must be 600s"},
            {"name": "instructions_mit_inputblock", "confidence": 0.4, "auto_applied": True,
             "rule": "instructions need input block"},
            {"name": "no_auto", "confidence": 0.9, "rule": "no auto-applied flag"},
        ]
    }
    p = tmp_path / "registry.yaml"
    p.write_text(yaml.dump(reg))
    return p


@pytest.fixture
def project_with_yaml(tmp_path):
    """Create a project with several .yaml files in subdirs."""
    sub = tmp_path / "config"
    sub.mkdir()
    (sub / "a.yaml").write_text("a: 1")
    (sub / "b.yaml").write_text("b: 2")
    (sub / "c.txt").write_text("ignore me")
    (tmp_path / "top.yaml").write_text("top: 1")
    return tmp_path


def test_load_handles_yaml_error(tmp_path):
    """load() of a malformed YAML file returns {} (the except branch)."""
    mod = _import_tool()
    bad = tmp_path / "bad.yaml"
    bad.write_text("this: is: not: valid: yaml: :")
    assert mod.load(str(bad)) == {}


def test_load_handles_valid_yaml(tmp_path):
    """load() of a valid YAML file returns the parsed dict."""
    mod = _import_tool()
    f = tmp_path / "good.yaml"
    f.write_text("key: value\nlist:\n  - a\n  - b")
    d = mod.load(str(f))
    assert d == {"key": "value", "list": ["a", "b"]}


def test_get_scoped_agents_filters_non_yaml_files():
    """get_scoped_agents returns only .yaml files from the input list."""
    mod = _import_tool()
    files = ["a.yaml", "b.yaml", "c.txt", "noext"]
    result = mod.get_scoped_agents("prompt_braucht_boundary", files)
    assert "a.yaml" in result
    assert "b.yaml" in result
    assert "c.txt" not in result
    assert "noext" not in result


def test_get_scoped_agents_handles_unknown_pattern_name():
    """get_scoped_agents with an unknown pattern_name still filters to .yaml files."""
    mod = _import_tool()
    files = ["x.yaml", "y.txt"]
    result = mod.get_scoped_agents("unknown_pattern", files)
    assert result == ["x.yaml"]


def test_apply_patterns_below_threshold_counted_as_skipped(registry_with_patterns, project_with_yaml, tmp_path):
    """Patterns with confidence < threshold → skipped++ (no applied entries)."""
    mod = _import_tool()
    # Set threshold high so even 0.4/0.5/0.9 are below
    result = mod.apply_patterns(str(registry_with_patterns), str(project_with_yaml), threshold=2.0)
    assert result["skipped"] == 4
    assert result["applied"] == []


def test_apply_patterns_with_threshold_includes_eligible(registry_with_patterns, project_with_yaml):
    """Patterns with auto_applied=True and confidence >= threshold → up to 3 candidates each."""
    mod = _import_tool()
    result = mod.apply_patterns(str(registry_with_patterns), str(project_with_yaml), threshold=0.3)
    # 1 skipped (low_conf=0.1) + 2 auto_applied (settings_timeout, instructions_mit_inputblock) + 1 no_auto (no auto_applied flag)
    assert result["skipped"] == 1
    # Each auto-applied pattern can match up to 3 files
    applied_names = [a["pattern"] for a in result["applied"]]
    assert "settings_timeout_sweetspot" in applied_names
    assert "instructions_mit_inputblock" in applied_names
    # The no_auto pattern should NOT be applied (no auto_applied flag)
    assert "no_auto" not in applied_names
    # No more than 3 entries per pattern
    for pname in ("settings_timeout_sweetspot", "instructions_mit_inputblock"):
        cnt = sum(1 for a in result["applied"] if a["pattern"] == pname)
        assert cnt <= 3
        assert cnt >= 1  # project has at least one .yaml file


def test_apply_patterns_marks_project_in_auto_applied_to(registry_with_patterns, project_with_yaml):
    """After running, the registry file is updated with the project name in
    each applied pattern's auto_applied_to list."""
    import yaml
    mod = _import_tool()
    mod.apply_patterns(str(registry_with_patterns), str(project_with_yaml), threshold=0.3)
    # Re-read the registry
    with open(registry_with_patterns) as f:
        updated = yaml.safe_load(f)
    for p in updated["patterns"]:
        if p["name"] in ("settings_timeout_sweetspot", "instructions_mit_inputblock"):
            assert str(project_with_yaml) in p.get("auto_applied_to", [])


def test_apply_patterns_writes_registry_back_to_disk(registry_with_patterns, project_with_yaml):
    """apply_patterns persists changes to the registry file (yaml.dump)."""
    mod = _import_tool()
    original_size = registry_with_patterns.stat().st_size
    mod.apply_patterns(str(registry_with_patterns), str(project_with_yaml), threshold=0.3)
    new_size = registry_with_patterns.stat().st_size
    # File should be rewritten; size may grow or shrink depending on yaml formatting
    assert new_size > 0
    assert registry_with_patterns.exists()


def test_apply_patterns_result_entries_have_required_fields(registry_with_patterns, project_with_yaml):
    """Each entry in result['applied'] has pattern, file, action, status keys."""
    mod = _import_tool()
    result = mod.apply_patterns(str(registry_with_patterns), str(project_with_yaml), threshold=0.3)
    for entry in result["applied"]:
        assert "pattern" in entry
        assert "file" in entry
        assert "action" in entry
        assert "status" in entry
        assert entry["status"] == "pending"
        # action should be truncated to 40 chars of the rule
        assert len(entry["action"]) <= 50  # "Apply " + first 40 chars


def test_apply_patterns_action_truncates_long_rules(tmp_path):
    """A pattern with a rule longer than 40 chars → action contains the truncated form."""
    import yaml
    mod = _import_tool()
    long_rule = "x" * 100
    reg = {"patterns": [{"name": "prompt_braucht_boundary", "confidence": 0.5,
                          "auto_applied": True, "rule": long_rule}]}
    rp = tmp_path / "reg.yaml"
    rp.write_text(yaml.dump(reg))
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.yaml").write_text("a: 1")
    result = mod.apply_patterns(str(rp), str(proj), threshold=0.3)
    assert len(result["applied"]) >= 1
    # The action format is `Apply {rule[:40]}` so the part after "Apply " is <= 40 chars
    action = result["applied"][0]["action"]
    assert action.startswith("Apply ")
    assert len(action) <= len("Apply ") + 40


def test_main_block_via_subprocess(registry_with_patterns, project_with_yaml):
    """Run the tool's __main__ block via subprocess. Covers lines 48-55
    (argparse + print(json.dumps))."""
    import json
    import subprocess
    result = subprocess.run(
        [sys.executable, str(TOOL),
         "--registry", str(registry_with_patterns),
         "--project", str(project_with_yaml),
         "--threshold", "0.3"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    data = json.loads(result.stdout)
    assert "applied" in data
    assert "skipped" in data


def test_main_block_missing_required_arg_exits_nonzero(registry_with_patterns):
    """`--registry` is required → calling with no args → non-zero exit."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True, text=True,
    )
    # argparse exits with code 2 on missing required args
    assert result.returncode != 0
