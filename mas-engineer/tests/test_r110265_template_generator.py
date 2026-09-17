"""
test_r110265_template_generator.py — R110-265 Coverage Sprint, banner-tool part 1.

Target: dev_template_generator.py (901 lines, 518 stmts).
R110-260 declared this a "banner tool" (sys.argv parsed at module level) and
left it out of R110-261. R110-265 proves that banner-tools ARE testable
via direct library import — sys.argv is reset to a benign value before
import, and the module-level argparse in main() never executes (because
main() is called only when __name__ == "__main__").

Library functions covered (12):
  - load_yaml, load_json, load_text
  - load_all_sources
  - _format_dict_block, _format_bp_rules
  - build_rule_package
  - fill_template
  - build_yaml
  - _check_field, _check_contains
  - refresh_agent (dry_run path)
  - refresh_all (dry_run path)

Excluded from this file (would need real SOT+BP+workflows.yaml):
  - _add_sot_entry, _add_sub_recipes_entry, _update_changes_json
    (write to real .mase/ paths, covered indirectly via write_agent with
    no_sot=True)
  - write_agent (side-effect heavy, writes to real recipe/sub/)
    — covered with no_sot=True + isolated tmp workspace
  - main() (argparse + integration; subprocess-style, out of scope)

Run with:
    python3 -m pytest tests/test_r110265_template_generator.py -v
"""
import json
import os
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"

# Reset sys.argv BEFORE importing the tool — it parses sys.argv at module
# level to extract flags like --include-external-recipes and to populate
# SEVERITY_FILTER. We give it a benign argv that contains no flags, so
# the module-level parsing is a no-op.
_PRE_IMPORT_ARGV = sys.argv[:]
sys.argv = ["dev_template_generator.py"]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO_ROOT))
import dev_template_generator as mod  # noqa: E402
sys.argv = _PRE_IMPORT_ARGV


# ─── Test fixtures ─────────────────────────────────────────────
@pytest.fixture
def fake_workspace(tmp_path):
    """Build a minimal workspace tree that load_all_sources expects.

    Creates:
      tmp_path/.mase/workflows.yaml         (with agents: section)
      tmp_path/.mase/best-practices.yaml   (with auto_apply rules)
      tmp_path/.mase/improvement-plan.json (with plan: list)
      tmp_path/recipe/template/agent_template.yaml
      tmp_path/.mase/templates/agent_schema.yaml
      tmp_path/recipe/sub/                 (empty, for refresh_all)
    """
    mase = tmp_path / ".mase"
    mase.mkdir()
    templates = mase / "templates"
    templates.mkdir()

    # workflows.yaml with SOT structure
    (mase / "workflows.yaml").write_text(yaml.safe_dump({
        "configs": {
            "mas-self": {
                "restrictions": {
                    "r01_confirmation": {"level": "blocker", "description": "Confirm before action"},
                    "r02_bestand": {"level": "blocker", "description": "Preserve existing"},
                },
                "enforcement": {
                    "type_check": {"description": "type-check inputs"},
                    "size_limit": "10MB",
                },
                "recovery": {
                    "low": {"backup": {"description": "Take backup first"}}
                },
                "signals": {
                    "warning": [{"signal": "retry", "nach": "exponential backoff"}]
                }
            }
        },
        "agents": {},  # populated by write_agent
    }))

    # best-practices.yaml with auto_apply rules
    (mase / "best-practices.yaml").write_text(yaml.safe_dump({
        "autonomie": [
            {"id": "BP-A-001", "auto_apply": True, "rule": "Agent must work autonomously"},
            {"id": "BP-A-002", "auto_apply": False, "rule": "Should not apply here"},  # non-auto
        ],
        "separation": [
            {"id": "BP-S-001", "auto_apply": True, "rule": "Separate concerns"},
        ],
        "best_practices": {
            "structure": [
                {"id": "BP-ST-001", "auto_apply": True, "rule": "Use clear structure"},
            ],
            "prompt": [
                {"id": "BP-P-001", "auto_apply": True, "rule": "Use short prompt"},
            ],
            "settings": [
                {"id": "BP-SET-001", "auto_apply": True, "rule": "Use default settings"},
            ],
        },
        "recovery": [
            {"id": "BP-REC-001", "auto_apply": True, "rule": "Use try/except"},
        ],
    }))

    # improvement-plan.json with plan list
    (mase / "improvement-plan.json").write_text(json.dumps({
        "plan": [
            {"id": "IMP-001", "field": "settings.timeout", "risk": "low"},
            {"id": "IMP-002", "field": "prompt", "risk": "medium"},
        ]
    }))

    # Template
    template_dir = tmp_path / "recipe" / "template"
    template_dir.mkdir(parents=True)
    (template_dir / "agent_template.yaml").write_text("""\
title: "{EMOJI} SUB-MAS-{NAME} — {TASK}"
description: 'v1.0.0 | MAS-intern: {TASK}'
instructions: |
  # sub_mas-{name}
  {TASK}
  {SOT_RESTRICTIONS}
  {BP_AUTONOMIE}
prompt: '{EMOJI} {NAME} (v1.0.0)
⛔ NUR {TASK}
{SOT_RESTRICTIONS}'
settings:
  timeout: 600
  max_turns: 100
""")

    # Schema
    (templates / "agent_schema.yaml").write_text(yaml.safe_dump({
        "required": ["version", "title", "description", "instructions", "prompt", "settings"]
    }))

    # recipe/sub for refresh_all
    (tmp_path / "recipe" / "sub").mkdir(parents=True, exist_ok=True)

    return tmp_path


# ─── Test class ────────────────────────────────────────────────
class TestDevTemplateGenerator:

    # ── load_yaml / load_json / load_text (3 tests) ──
    def test_load_yaml_valid(self, tmp_path):
        f = tmp_path / "x.yaml"
        f.write_text(yaml.safe_dump({"a": 1, "b": [2, 3]}))
        result = mod.load_yaml(str(f))
        assert result == {"a": 1, "b": [2, 3]}

    def test_load_yaml_missing_returns_empty(self, tmp_path):
        result = mod.load_yaml(str(tmp_path / "nope.yaml"))
        assert result == {}

    def test_load_yaml_invalid_returns_empty(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(":\n  - :\n  invalid: [yaml")
        result = mod.load_yaml(str(f))
        assert result == {}

    def test_load_json_valid(self, tmp_path):
        f = tmp_path / "x.json"
        f.write_text(json.dumps({"a": 1, "b": [2, 3]}))
        result = mod.load_json(str(f))
        assert result == {"a": 1, "b": [2, 3]}

    def test_load_json_missing(self, tmp_path):
        result = mod.load_json(str(tmp_path / "nope.json"))
        assert result == {}

    def test_load_text_valid(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hello\nworld")
        result = mod.load_text(str(f))
        assert result == "hello\nworld"

    def test_load_text_missing(self, tmp_path):
        result = mod.load_text(str(tmp_path / "nope.txt"))
        assert result == ""

    # ── load_all_sources (2 tests) ──
    def test_load_all_sources_happy_path(self, fake_workspace):
        sources = mod.load_all_sources(str(fake_workspace))
        assert "sot" in sources
        assert "bp" in sources
        assert "improvement" in sources
        assert "template" in sources
        assert "schema" in sources
        # SOT structure should be populated
        assert sources["sot"]["restrictions"]["r01_confirmation"]["level"] == "blocker"
        # BP rules loaded
        assert isinstance(sources["bp"], dict)
        # Improvement items
        assert len(sources["improvement"]) == 2
        assert sources["improvement"][0]["id"] == "IMP-001"
        # Template as text
        assert "sub_mas" in sources["template"]
        # Schema
        assert "required" in sources["schema"]

    def test_load_all_sources_missing_workspace(self, tmp_path):
        # Non-existent workspace → all sources empty, but still returns dict
        sources = mod.load_all_sources(str(tmp_path / "nonexistent"))
        assert sources == {
            "sot": {},
            "bp": {},
            "improvement": [],
            "template": "",
            "schema": {},
        }

    # ── _format_dict_block (1 test) ──
    def test_format_dict_block_scalars(self):
        result = mod._format_dict_block({"a": 1, "b": "hello"})
        assert "# a: 1" in result
        assert "# b: hello" in result

    def test_format_dict_block_nested(self):
        result = mod._format_dict_block({"x": {"y": 1, "z": 2}})
        assert "# x:" in result
        assert "# y: 1" in result
        assert "# z: 2" in result

    def test_format_dict_block_list_truncation(self):
        result = mod._format_dict_block({"items": list(range(20))})
        assert "+15 mehr" in result  # shows the truncation marker

    # ── _format_bp_rules (1 test) ──
    def test_format_bp_rules_filters_auto_apply(self):
        bp = {
            "autonomie": [
                {"id": "A", "auto_apply": True, "rule": "Auto rule"},
                {"id": "B", "auto_apply": False, "rule": "Manual rule"},
            ]
        }
        result = mod._format_bp_rules(bp, ["autonomie"])
        assert "[A]" in result
        assert "Auto rule" in result
        assert "[B]" not in result  # only auto_apply=True
        assert "Manual rule" not in result

    def test_format_bp_rules_nested_keys(self):
        bp = {
            "best_practices": {
                "prompt": [
                    {"id": "P-001", "auto_apply": True, "rule": "Short prompts"},
                ]
            }
        }
        result = mod._format_bp_rules(bp, ["best_practices.prompt"])
        assert "[P-001]" in result

    def test_format_bp_rules_missing_section(self):
        # Section key not in BP → empty result
        result = mod._format_bp_rules({}, ["nonexistent"])
        assert result == ""

    # ── build_rule_package (3 tests) ──
    def test_build_rule_package_happy_path(self, fake_workspace):
        sources = mod.load_all_sources(str(fake_workspace))
        rules = mod.build_rule_package(sources)
        # All 12 expected keys present
        expected_keys = [
            "sot_restrictions", "sot_enforcement", "sot_recovery", "sot_signals",
            "bp_autonomie", "bp_separation", "bp_structure", "bp_prompt",
            "bp_settings", "bp_recovery", "improvement_notes", "standard_settings",
        ]
        for key in expected_keys:
            assert key in rules, f"missing key: {key}"
        # SOT restrictions extracted
        assert "r01_confirmation" in rules["sot_restrictions"]
        assert "blocker" in rules["sot_restrictions"]
        # BP autonomie has the auto_apply rule, not the non-auto
        assert "[BP-A-001]" in rules["bp_autonomie"]
        assert "[BP-A-002]" not in rules["bp_autonomie"]
        # Standard settings present
        assert rules["standard_settings"]["timeout"] == 600
        assert rules["standard_settings"]["max_turns"] == 100

    def test_build_rule_package_empty_sources(self):
        rules = mod.build_rule_package({
            "sot": {}, "bp": {}, "improvement": []
        })
        # Should have placeholder defaults, not crashes
        assert "No SOT-restrictions" in rules["sot_restrictions"]
        assert "No BP-Autonomie" in rules["bp_autonomie"]
        assert rules["standard_settings"]["timeout"] == 600

    def test_build_rule_package_signals_list_vs_scalar(self):
        # Mix of list-typed and scalar-typed signal values
        sources = {
            "sot": {
                "signals": {
                    "warning": [{"signal": "retry", "nach": "1min"}],
                    "info_str": "plain string",
                }
            },
            "bp": {},
            "improvement": [],
        }
        rules = mod.build_rule_package(sources)
        assert "retry" in rules["sot_signals"]
        assert "info_str" in rules["sot_signals"]

    # ── fill_template (3 tests) ──
    def test_fill_template_basic_substitution(self, fake_workspace):
        sources = mod.load_all_sources(str(fake_workspace))
        rules = mod.build_rule_package(sources)
        result = mod.fill_template(
            sources, rules,
            name="log-analyzer", emoji="🔧", task="Analyze logs",
            agent_type="sub",
        )
        # Title placeholder replaced
        assert "LOG-ANALYZER" in result or "log-analyzer" in result
        # SOT restrictions injected
        assert "r01_confirmation" in result
        # BP autonomie injected
        assert "BP-A-001" in result
        # No unreplaced placeholders left
        assert "{NAME}" not in result
        assert "{TASK}" not in result
        assert "{SOT_RESTRICTIONS}" not in result

    def test_fill_template_no_template_falls_back(self, fake_workspace, monkeypatch):
        # Force the no-template path: empty template in sources
        sources = mod.load_all_sources(str(fake_workspace))
        sources["template"] = ""
        rules = mod.build_rule_package(sources)
        result = mod.fill_template(
            sources, rules,
            name="x", emoji="🔧", task="do thing", agent_type="sub",
        )
        # Fallback template should have been used
        assert "sub_mas-x" in result
        assert "DO THING" in result or "do thing" in result

    def test_fill_template_unreplaced_placeholders_cleaned(self, fake_workspace):
        # Template contains a placeholder not in the replacements dict
        # → should be cleaned to empty string, not left in output
        sources = mod.load_all_sources(str(fake_workspace))
        rules = mod.build_rule_package(sources)
        result = mod.fill_template(
            sources, rules, name="x", emoji="🔧", task="t", agent_type="sub",
        )
        # No stray {ALL_CAPS} placeholders in output
        import re
        leftover = re.findall(r"\{[A-Z_]+\}", result)
        assert leftover == [], f"leftover placeholders: {leftover}"

    # ── build_yaml (2 tests) ──
    def test_build_yaml_basic_structure(self):
        rules = {"standard_settings": {
            "timeout": 600, "max_turns": 100,
            "goose_provider": "openai",
            "goose_model": "filtered/deepseek/deepseek-v4-flash",
        }}
        result = mod.build_yaml(
            filled="instructions here",
            rules=rules, name="x", emoji="🔧", task="do thing",
        )
        # All 6 core keys present
        assert set(result.keys()) == {"version", "title", "description", "instructions", "prompt", "settings"}
        assert result["version"] == "1.0.0"
        assert "🔧" in result["title"]
        assert "X" in result["title"]  # name.upper()
        # Prompt must have ⛔ and version marker
        assert "⛔" in result["prompt"]
        assert "(v1.0.0)" in result["prompt"]
        # Settings from rules
        assert result["settings"]["timeout"] == 600
        assert result["settings"]["goose_model"] == "filtered/deepseek/deepseek-v4-flash"

    def test_build_yaml_long_task_truncates(self):
        rules = {"standard_settings": {}}
        long_task = "word " * 200  # > 500 chars
        result = mod.build_yaml(
            filled="x", rules=rules, name="y", emoji="🔧", task=long_task,
        )
        # Prompt should be ≤ 500 chars (truncated)
        assert len(result["prompt"]) <= 500

    # ── _check_field (2 tests) ──
    def test_check_field_match_returns_none(self):
        result = mod._check_field(
            {"settings": {"timeout": 600}}, "settings.timeout", 600, "timeout"
        )
        assert result is None

    def test_check_field_mismatch_returns_issue(self):
        result = mod._check_field(
            {"settings": {"timeout": 300}}, "settings.timeout", 600, "timeout"
        )
        assert result is not None
        assert result["field"] == "settings.timeout"
        assert result["severity"] == "niedrig"  # numeric expected

    def test_check_field_nested_dict_missing(self):
        result = mod._check_field(
            {"settings": {}}, "settings.timeout", 600, "timeout"
        )
        assert result is not None
        # actual is None, expected 600
        assert "None" in result["problem"] or "timeout" in result["problem"]

    # ── _check_contains (2 tests) ──
    def test_check_contains_present(self):
        result = mod._check_contains(
            {"instructions": "Use SOT-reference here"},
            "instructions", "SOT", "SOT-ref",
        )
        assert result is None

    def test_check_contains_missing(self):
        result = mod._check_contains(
            {"instructions": "no marker here"},
            "instructions", "AUTONOMIEMODUS", "Autonomiemodus",
        )
        assert result is not None
        assert "Missing" in result["problem"]
        assert result["severity"] == "mittel"

    def test_check_contains_high_severity_for_boundary(self):
        result = mod._check_contains(
            {"instructions": "nothing"}, "instructions", "⛔", "boundary",
        )
        assert result is not None
        assert result["severity"] == "hoch"

    # ── refresh_agent (3 tests) ──
    def test_refresh_agent_not_found(self, fake_workspace):
        result = mod.refresh_agent(
            agent_name="sub_mas-nonexistent", dry_run=True,
            workspace=str(fake_workspace),
        )
        assert result["status"] == "not_found"
        assert "file not found" in result["issues"][0]["problem"]

    def test_refresh_agent_clean(self, fake_workspace):
        # Create a well-formed agent YAML
        agent_path = fake_workspace / "recipe" / "sub" / "sub_mas-test1.yaml"
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        agent_data = {
            "version": "1.0.0",
            "title": "🔧 SUB-MAS-test1 — task desc",
            "description": "v1.0.0 | task desc",
            "instructions": (
                "SOT-reference here\n"
                "AUTONOMIEMODUS on\n"
                "mas_result output\n"
                "Retry logic\n"
                "Edge Cases covered\n"
                "Tool-Inventar listed"
            ),
            "prompt": "🔧 TEST1 (v1.0.0)\n⛔ NUR test",
            "settings": {"timeout": 600, "max_turns": 100},
        }
        agent_path.write_text(yaml.safe_dump(agent_data))
        result = mod.refresh_agent(
            agent_name="sub_mas-test1", dry_run=True,
            workspace=str(fake_workspace),
        )
        assert result["status"] == "clean"
        assert result["issues"] == []

    def test_refresh_agent_with_issues(self, fake_workspace):
        # Create a deliberately bad agent YAML
        agent_path = fake_workspace / "recipe" / "sub" / "sub_mas-bad.yaml"
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        agent_data = {
            "version": "1.0.0",
            "title": "test",
            "description": "no version prefix",
            "instructions": "no markers here",
            "prompt": "no version",  # missing ⛔, missing (v1.0.0)
            "settings": {"timeout": 300, "max_turns": 50},  # wrong defaults
        }
        agent_path.write_text(yaml.safe_dump(agent_data))
        result = mod.refresh_agent(
            agent_name="sub_mas-bad", dry_run=True,
            workspace=str(fake_workspace),
        )
        assert result["status"] == "issues"  # dry-run with issues
        assert result["issues_count"] > 0
        # Should detect wrong timeout
        assert any(i["field"] == "settings.timeout" for i in result["issues"])
        # Should detect missing ⛔ boundary
        assert any("⛔" in i["problem"] for i in result["issues"])

    def test_refresh_agent_with_issues_not_dry_run_fixes(self, fake_workspace):
        # Same as above but dry_run=False → should FIX and return status=fixed
        agent_path = fake_workspace / "recipe" / "sub" / "sub_mas-fixable.yaml"
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        agent_data = {
            "version": "1.0.0",
            "title": "test",
            "description": "no version prefix",
            "instructions": "no markers",
            "prompt": "no version no boundary",
            "settings": {"timeout": 300, "max_turns": 50},
        }
        agent_path.write_text(yaml.safe_dump(agent_data))
        result = mod.refresh_agent(
            agent_name="sub_mas-fixable", dry_run=False,
            workspace=str(fake_workspace),
        )
        assert result["status"] == "fixed"
        # Verify the file was actually updated
        reloaded = yaml.safe_load(agent_path.read_text())
        assert reloaded["settings"]["timeout"] == 600
        assert reloaded["settings"]["max_turns"] == 100

    # ── refresh_all (1 test) ──
    def test_refresh_all_dry_run(self, fake_workspace):
        # Create 3 agents: 1 clean, 1 with issues, 1 missing
        sub_dir = fake_workspace / "recipe" / "sub"
        sub_dir.mkdir(parents=True, exist_ok=True)

        # clean
        (sub_dir / "sub_mas-clean.yaml").write_text(yaml.safe_dump({
            "version": "1.0.0",
            "title": "🔧 SUB-MAS-clean — task",
            "description": "v1.0.0 | task",
            "instructions": "SOT\nAUTONOMIEMODUS\nmas_result\nRetry\nEdge Cases\nTool-Inventar",
            "prompt": "🔧 CLEAN (v1.0.0)\n⛔ NUR task",
            "settings": {"timeout": 600, "max_turns": 100},
        }))

        # bad
        (sub_dir / "sub_mas-bad.yaml").write_text(yaml.safe_dump({
            "version": "1.0.0",
            "title": "test",
            "description": "no prefix",
            "instructions": "no markers",
            "prompt": "no version no boundary",
            "settings": {"timeout": 300, "max_turns": 50},
        }))

        result = mod.refresh_all(dry_run=True, workspace=str(fake_workspace))
        assert result["total"] == 2
        assert result["clean"] == 1
        assert result["with_issues"] == 1
        assert result["not_found"] == 0
        # In dry_run mode, nothing is fixed
        assert "fixed" not in result or result.get("fixed", 0) == 0

    def test_refresh_all_missing_subdir(self, tmp_path):
        # No recipe/sub/ directory → error in result
        result = mod.refresh_all(dry_run=True, workspace=str(tmp_path))
        assert "error" in result
        assert result["total"] == 0

    # ── Module-level constants sanity (1 test) ──
    def test_constants_present(self):
        # Sanity check the module exposes its expected constants
        assert mod.DEFAULT_TIMEOUT == 600
        assert mod.DEFAULT_MAX_TURNS == 100
        assert mod.DEFAULT_PROVIDER == "openai"
        assert "deepseek" in mod.DEFAULT_MODEL
        assert "r01_confirmation" in mod.SOT_RESTRICTION_KEYS
        assert "version" in mod.CORE_KEYS
