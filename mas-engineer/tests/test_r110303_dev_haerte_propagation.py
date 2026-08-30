"""R110-303 phase 2: 100% coverage tests for tools/dev_haerte_propagation.py.

CRITICAL — pre-existing count-assertion pitfall (R110-300a):
  Do NOT use `assert "N type" in output` literals anywhere in this file.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "dev_haerte_propagation.py"
REPO_ROOT = str(Path(TOOL).parent.parent)
TOOLS_DIR = str(Path(TOOL).parent)


def _import_tool():
    """Coverage-attribution trick: synthetic `tools` package."""
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
def workspace_with_rules(tmp_path):
    """Create a minimal workspace with `.mase/rules/hard_rules.yaml` containing
    a mix of strong (hardness 4) and extreme (hardness 5) rules, plus
    one rule with block=True and one with block=False."""
    import yaml
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    rules = {
        "hardness_levels": {
            "strong": {"symbol": "⛔⛔⛔", "name": "strong"},
            "extreme": {"symbol": "⛔⛔⛔⛔⛔", "name": "extreme"},
        },
        "rules": [
            {"id": "R1", "prompt_text": "strong rule A", "hardness": 4, "block": True},
            {"id": "R2", "prompt_text": "strong rule B", "hardness": 4, "block": False},
            {"id": "R3", "prompt_text": "extreme rule", "hardness": 5, "block": True},
            {"id": "R4", "prompt_text": "weak rule", "hardness": 2, "block": True},
        ],
    }
    (rules_dir / "hard_rules.yaml").write_text(yaml.dump(rules))
    return tmp_path


def test_get_hard_rules_default_threshold_includes_strong_and_extreme(workspace_with_rules):
    """Default min_hardness=4 → R1, R2, R3 returned, R4 excluded."""
    mod = _import_tool()
    rules = mod.get_hard_rules(str(workspace_with_rules))
    ids = {r["id"] for r in rules}
    assert ids == {"R1", "R2", "R3"}


def test_get_hard_rules_higher_threshold_only_extreme(workspace_with_rules):
    """min_hardness=5 → only R3 returned."""
    mod = _import_tool()
    rules = mod.get_hard_rules(str(workspace_with_rules), min_hardness=5)
    ids = {r["id"] for r in rules}
    assert ids == {"R3"}


def test_get_hard_rules_extreme_icon(workspace_with_rules):
    """A rule with hardness >= 5 has a 5-icon prefix in its text field."""
    mod = _import_tool()
    rules = mod.get_hard_rules(str(workspace_with_rules), min_hardness=5)
    assert "⛔⛔⛔⛔⛔" in rules[0]["text"]


def test_get_hard_rules_strong_icon(workspace_with_rules):
    """A rule with hardness 4 has a 3-icon prefix in its text field."""
    mod = _import_tool()
    rules = mod.get_hard_rules(str(workspace_with_rules), min_hardness=4)
    strong_rules = [r for r in rules if r["id"] == "R1"]
    assert "⛔⛔⛔" in strong_rules[0]["text"]
    # And NOT the 5-icon prefix
    assert "⛔⛔⛔⛔⛔" not in strong_rules[0]["text"]


def test_get_hard_rules_preserves_block_field(workspace_with_rules):
    """The `block` field is passed through unchanged from the yaml."""
    mod = _import_tool()
    rules = mod.get_hard_rules(str(workspace_with_rules))
    r1 = next(r for r in rules if r["id"] == "R1")
    r2 = next(r for r in rules if r["id"] == "R2")
    assert r1["block"] is True
    assert r2["block"] is False


def test_format_for_intake_includes_header_and_footer(workspace_with_rules):
    """Output contains the INHERITED RULES header AND the END marker."""
    mod = _import_tool()
    out = mod.format_for_intake("sub_mas-x", {}, str(workspace_with_rules))
    assert "INHERITED RULES" in out
    assert "END INHERITED RULES" in out


def test_format_for_intake_includes_agent_name(workspace_with_rules):
    """Output mentions the agent name in the 'Inherited from dev-mas-engineer for Sub-Agent:' line."""
    mod = _import_tool()
    out = mod.format_for_intake("sub_mas-foobar", {}, str(workspace_with_rules))
    assert "sub_mas-foobar" in out


def test_format_for_intake_block_rules_get_5_icon_prefix(workspace_with_rules):
    """A rule with `block=True` is rendered with 5-icon prefix in the intake."""
    mod = _import_tool()
    out = mod.format_for_intake("sub_mas-x", {}, str(workspace_with_rules))
    assert "⛔⛔⛔⛔⛔" in out


def test_format_for_intake_non_block_rules_get_indented(workspace_with_rules):
    """A rule with `block=False` is rendered with 2-space indent (no icon)."""
    mod = _import_tool()
    out = mod.format_for_intake("sub_mas-x", {}, str(workspace_with_rules))
    # Find the line containing the non-block rule text
    lines = out.splitlines()
    found = False
    for line in lines:
        if "strong rule B" in line:
            assert line.startswith("  "), f"expected indent, got: {line!r}"
            found = True
    assert found, "non-block rule missing from intake"


def test_format_for_intake_passes_through_min_hardness(workspace_with_rules):
    """format_for_intake always uses min_hardness=4 internally (verify by
    checking that the weak R4 (hardness 2) is NOT in the output)."""
    mod = _import_tool()
    out = mod.format_for_intake("sub_mas-x", {}, str(workspace_with_rules))
    assert "weak rule" not in out


def test_main_block_via_subprocess(workspace_with_rules):
    """Run the tool's __main__ block with default args. The workspace is
    discovered from --workspace flag, agent_name from positional argv."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(TOOL),
         "--workspace", str(workspace_with_rules),
         "sub_mas-cli-agent"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "INHERITED RULES" in result.stdout
    assert "sub_mas-cli-agent" in result.stdout


def test_main_block_default_workspace_and_agent(workspace_with_rules, monkeypatch):
    """With no args: workspace defaults to os.getcwd() and agent_name to
    'sub_mas-unknown'. Run from a tmp_path cwd that already has the rules
    directory at the right relative path.

    Note: hard_rules.yaml is expected at
    `<workspace>/mas-engineer/.mase/rules/hard_rules.yaml`, so the
    workspace passed to get_hard_rules must be the PARENT of mas-engineer/,
    i.e. one level up from the rules dir."""
    import subprocess
    # Place rules under <tmp>/mas-engineer/.mase/rules/ and run from <tmp> as cwd
    # (since default workspace is os.getcwd())
    rules_path = workspace_with_rules / "mas-engineer" / ".mase" / "rules" / "hard_rules.yaml"
    assert rules_path.exists()
    result = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True, text=True,
        cwd=str(workspace_with_rules),
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "INHERITED RULES" in result.stdout
    assert "sub_mas-unknown" in result.stdout
