"""Tests for mas-engineer/tools/dev_template_generator.py — R110-288.

Coverage target: dev_template_generator.py 50-69% → ~85%.

Tests focus on the high-level data-flow rather than every helper:
- load_yaml/load_json/load_text: missing file, error, valid file
- load_all_sources: structure, missing sources handled
- build_rule_package: SOT/BP/improvement all extract
- fill_template: placeholder replacement, missing template fallback,
  extra placeholder cleanup
- build_yaml: schema structure, settings defaults, prompt truncation
- _format_dict_block: dict/list/scalar formatting
- write_agent: writes file, backup, SOT-update, no_sot
"""
import pytest
import sys
import os
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_template_generator as tg


# ─── load_yaml / load_json / load_text ───────────────────────────

class TestLoaders:
    def test_load_yaml_missing_file(self, tmp_path, capsys):
        result = tg.load_yaml(str(tmp_path / "nope.yaml"))
        assert result == {}
        assert "not found" in capsys.readouterr().out

    def test_load_yaml_valid(self, tmp_path):
        f = tmp_path / "x.yaml"
        f.write_text("a: 1\nb: hello\n")
        assert tg.load_yaml(str(f)) == {"a": 1, "b": "hello"}

    def test_load_yaml_empty_returns_empty_dict(self, tmp_path):
        f = tmp_path / "x.yaml"
        f.write_text("")
        assert tg.load_yaml(str(f)) == {}

    def test_load_yaml_invalid_yaml_returns_empty(self, tmp_path, capsys):
        f = tmp_path / "bad.yaml"
        f.write_text("a: : :\n  - broken: ]\n")
        result = tg.load_yaml(str(f))
        assert result == {}
        assert "YAML-Error" in capsys.readouterr().out

    def test_load_json_missing_file(self, tmp_path, capsys):
        result = tg.load_json(str(tmp_path / "nope.json"))
        assert result == {}
        assert "not found" in capsys.readouterr().out

    def test_load_json_valid(self, tmp_path):
        f = tmp_path / "x.json"
        f.write_text('{"plan": [{"id": "X1"}]}')
        assert tg.load_json(str(f)) == {"plan": [{"id": "X1"}]}

    def test_load_text_missing_returns_empty(self, tmp_path, capsys):
        assert tg.load_text(str(tmp_path / "nope.txt")) == ""


# ─── load_all_sources ─────────────────────────────────────────────

class TestLoadAllSources:
    def test_structure_with_minimal_workspace(self, tmp_path, capsys):
        # Empty workspace — all sources missing
        result = tg.load_all_sources(str(tmp_path))
        assert "sot" in result
        assert "bp" in result
        assert "improvement" in result
        assert "template" in result
        assert "schema" in result
        # Missing sources message printed
        assert "Fehlend" in capsys.readouterr().out

    def test_with_sot_and_bp(self, tmp_path):
        mase = tmp_path / ".mase"
        mase.mkdir()
        (mase / "workflows.yaml").write_text(yaml.dump({
            "configs": {"mas-self": {"restrictions": {"r01": "no x"}}}
        }))
        (mase / "best-practices.yaml").write_text(yaml.dump({
            "autonomie": [{"id": "A1", "auto_apply": True, "rule": "do x"}]
        }))
        result = tg.load_all_sources(str(tmp_path))
        assert "r01" in result["sot"]["restrictions"]
        assert len(result["bp"]["autonomie"]) == 1

    def test_with_improvement_plan(self, tmp_path):
        mase = tmp_path / ".mase"
        mase.mkdir()
        (mase / "improvement-plan.json").write_text(json.dumps({
            "plan": [{"id": "I1", "desc": "fix y"}]
        }))
        result = tg.load_all_sources(str(tmp_path))
        assert len(result["improvement"]) == 1
        assert result["improvement"][0]["id"] == "I1"

    def test_no_improvement_key_returns_empty_list(self, tmp_path):
        mase = tmp_path / ".mase"
        mase.mkdir()
        (mase / "improvement-plan.json").write_text(json.dumps({"other": 1}))
        result = tg.load_all_sources(str(tmp_path))
        assert result["improvement"] == []


# ─── build_rule_package ───────────────────────────────────────────

class TestBuildRulePackage:
    def test_returns_dict_with_expected_keys(self):
        sources = {
            "sot": {"restrictions": {}, "enforcement": {}, "recovery": {},
                    "signals": {}},
            "bp": {"autonomie": [], "separation": []},
            "improvement": [],
        }
        rules = tg.build_rule_package(sources)
        assert "sot_restrictions" in rules
        assert "sot_enforcement" in rules
        assert "sot_recovery" in rules
        assert "sot_signals" in rules
        assert "bp_autonomie" in rules
        assert "bp_separation" in rules

    def test_extracts_sot_restrictions(self):
        sources = {
            "sot": {"restrictions": {
                "r01_confirmation": {"level": "hard", "description": "ask first"},
            }},
            "bp": {},
            "improvement": [],
        }
        rules = tg.build_rule_package(sources)
        assert "r01_confirmation" in rules["sot_restrictions"]
        assert "hard" in rules["sot_restrictions"]

    def test_extracts_bp_auto_apply_rules(self):
        sources = {
            "sot": {},
            "bp": {"autonomie": [
                {"id": "A1", "auto_apply": True, "rule": "be autonomous"},
                {"id": "A2", "auto_apply": False, "rule": "should NOT show"},
            ]},
            "improvement": [],
        }
        rules = tg.build_rule_package(sources)
        # A1 has auto_apply=True → shown
        assert "A1" in rules["bp_autonomie"]
        # A2 has auto_apply=False → NOT shown
        assert "A2" not in rules["bp_autonomie"]

    def test_handles_nested_bp_keys(self):
        sources = {
            "sot": {},
            "bp": {"best_practices": {"prompt": [
                {"id": "P1", "auto_apply": True, "rule": "use markdown"}
            ]}},
            "improvement": [],
        }
        rules = tg.build_rule_package(sources)
        # Nested key "best_practices.prompt" → rule P1 found
        assert "P1" in rules["bp_prompt"]

    def test_empty_sources(self):
        rules = tg.build_rule_package({"sot": {}, "bp": {}, "improvement": []})
        # Both SOT and BP sections return default "No X defined" comments
        # when their source data is empty (not literal empty strings).
        assert "No SOT-restrictions defines" in rules["sot_restrictions"]
        assert "No BP-Autonomie" in rules["bp_autonomie"]


# ─── fill_template ────────────────────────────────────────────────

class TestFillTemplate:
    def test_replaces_basic_placeholders(self):
        sources = {"template": "Title: {TASK}\nAgent: {NAME}\nEmoji: {EMOJI}"}
        rules = {}
        result = tg.fill_template(sources, rules, "x", "🔧", "do stuff", "sub")
        assert "do stuff" in result
        assert "X" in result  # NAME uppercased
        assert "🔧" in result

    def test_replaces_dynamic_placeholders(self):
        sources = {"template": "R: {SOT_RESTRICTIONS}\nB: {BP_AUTONOMIE}"}
        rules = {
            "sot_restrictions": "no x",
            "bp_autonomie": "be free",
        }
        result = tg.fill_template(sources, rules, "a", "🔧", "t", "sub")
        assert "no x" in result
        assert "be free" in result

    def test_missing_template_uses_default(self, capsys):
        sources = {"template": ""}  # empty
        rules = {}
        result = tg.fill_template(sources, rules, "x", "🔧", "do x", "sub")
        # Default template has version, title, settings (task is lowercased)
        assert "version: 1.0.0" in result
        assert "do x" in result
        assert "Template loaded" in capsys.readouterr().out

    def test_unknown_placeholders_replaced_with_empty(self):
        sources = {"template": "x: {NAME} y: {UNKNOWN_PLACEHOLDER}"}
        rules = {}
        result = tg.fill_template(sources, rules, "a", "🔧", "t", "sub")
        # {UNKNOWN_PLACEHOLDER} is replaced with empty (not "{UNKNOWN_PLACEHOLDER}")
        assert "{UNKNOWN_PLACEHOLDER}" not in result
        # but {NAME} is replaced
        assert "A" in result

    def test_cleans_triple_newlines(self):
        sources = {"template": "a\n\n\n\nb"}
        rules = {}
        result = tg.fill_template(sources, rules, "x", "🔧", "t", "sub")
        # Triple-newline cleanup: \n\n\n\n → \n\n
        assert "\n\n\n\n" not in result


# ─── build_yaml ───────────────────────────────────────────────────

class TestBuildYaml:
    def test_returns_dict_with_core_keys(self):
        rules = {}
        result = tg.build_yaml("instructions here", rules, "x", "🔧", "do x")
        for k in ["version", "title", "description", "instructions",
                  "prompt", "settings"]:
            assert k in result

    def test_settings_have_defaults(self):
        rules = {}
        result = tg.build_yaml("x", rules, "x", "🔧", "t")
        s = result["settings"]
        assert s["timeout"] == 600
        assert s["max_turns"] == 100
        assert s["goose_provider"] == "openai"
        assert "deepseek" in s["goose_model"]

    def test_settings_override_via_rules(self):
        rules = {"standard_settings": {"timeout": 1200, "max_turns": 200}}
        result = tg.build_yaml("x", rules, "x", "🔧", "t")
        assert result["settings"]["timeout"] == 1200
        assert result["settings"]["max_turns"] == 200

    def test_prompt_truncated_at_500_chars(self):
        # The prompt is built from {emoji} {NAME} (v1.0.0)\n⛔ NUR {scope}...
        # `scope` is the FIRST word of task (so the prompt is short even
        # with a long task). To exceed 500 chars we need a really long
        # scope, not a long task. So construct an agent name + emoji
        # that pushes the total over 500.
        long_name = "x" * 600
        result = tg.build_yaml("instructions", {}, long_name, "🔧", "do x")
        # Either: prompt is truncated with "..." OR prompt stays under 500
        # because the code's len check runs on the post-scope-build text.
        # The actual behavior: scope = "do" (first word), so prompt_text
        # is "{emoji} {name} (v1.0.0)\n⛔ NUR do — ...". With a 600-char
        # name, the prompt is well over 500 → truncated.
        assert len(result["prompt"]) <= 510  # small slack for "..."
        # If it was truncated, it ends with "..."
        if len(result["prompt"]) > 500:
            assert result["prompt"].endswith("...")

    def test_prompt_first_word_is_scope(self):
        result = tg.build_yaml("x", {}, "x", "🔧", "analyze data files")
        # scope = first word "analyze"
        assert "analyze" in result["prompt"]


# ─── _format_dict_block ───────────────────────────────────────────

class TestFormatDictBlock:
    def test_scalar_values(self):
        result = tg._format_dict_block({"a": 1, "b": "hello"})
        assert "# a: 1" in result
        assert "# b: hello" in result

    def test_nested_dict(self):
        result = tg._format_dict_block({"outer": {"inner": "v"}})
        assert "# outer:" in result
        assert "# inner: v" in result

    def test_list_truncated_at_5(self):
        result = tg._format_dict_block({"items": list(range(10))})
        assert "+5" in result  # "more" indicator

    def test_value_truncated_at_120(self):
        long_value = "x" * 200
        result = tg._format_dict_block({"a": long_value})
        # 120 chars + "# a: " prefix
        assert "x" * 200 not in result
        assert "x" * 100 in result

    def test_custom_prefix_and_indent(self):
        result = tg._format_dict_block({"a": 1}, prefix="// ", indent="  ")
        assert "// a: 1" in result
        # 2-space indent present
        assert result.startswith("  //")


# ─── write_agent ──────────────────────────────────────────────────

class TestWriteAgent:
    def _sample_yaml(self):
        return {
            "version": "1.0.0",
            "title": "X",
            "description": "Y",
            "instructions": "Z",
            "prompt": "P",
            "settings": {"timeout": 600, "max_turns": 100,
                         "goose_provider": "openai",
                         "goose_model": "m"},
        }

    def test_creates_file_in_recipe_sub(self, tmp_path):
        data = self._sample_yaml()
        result = tg.write_agent(data, "x", "sub", str(tmp_path))
        out = Path(result["file"])
        assert out.exists()
        assert out.parent.name == "sub"
        assert result["yaml_valid"] is True

    def test_creates_recipe_sub_dir_if_missing(self, tmp_path):
        data = self._sample_yaml()
        # No recipe/sub dir exists yet
        assert not (tmp_path / "recipe" / "sub").exists()
        result = tg.write_agent(data, "x", "sub", str(tmp_path))
        assert (tmp_path / "recipe" / "sub").is_dir()

    def test_backup_when_file_exists(self, tmp_path):
        data = self._sample_yaml()
        # First write creates the file
        tg.write_agent(data, "x", "sub", str(tmp_path))
        # Second write should create a backup
        result = tg.write_agent(data, "x", "sub", str(tmp_path))
        backup_dir = tmp_path / ".mase" / "backups"
        assert backup_dir.is_dir()
        backups = list(backup_dir.iterdir())
        assert len(backups) == 1
        assert backups[0].name.endswith("_x.yaml")

    def test_no_sot_skips_sot_update(self, tmp_path):
        data = self._sample_yaml()
        result = tg.write_agent(data, "x", "sub", str(tmp_path),
                                 no_sot=True)
        # No SOT means no workflows.yaml needed
        assert result["yaml_valid"] is True
        assert not (tmp_path / ".mase" / "workflows.yaml").exists()

    def test_writes_changes_json(self, tmp_path):
        data = self._sample_yaml()
        # Pre-create .mase/ so the changes.json write doesn't fail
        (tmp_path / ".mase").mkdir()
        tg.write_agent(data, "x", "sub", str(tmp_path))
        changes_file = tmp_path / ".mase" / "changes.json"
        assert changes_file.exists()
        changes = json.loads(changes_file.read_text())
        assert any(c.get("action") == "CREATE" for c in changes)
        assert any("x" in c.get("description", "") for c in changes)

    def test_spaces_in_name_become_underscores(self, tmp_path):
        data = self._sample_yaml()
        result = tg.write_agent(data, "my agent", "sub", str(tmp_path))
        # File should be named sub_mas-my_agent.yaml
        assert "sub_mas-my_agent.yaml" in result["file"]


# ─── _check_field (helper, used by refresh) ───────────────────────

class TestCheckField:
    def test_simple_field_match(self):
        result = tg._check_field({"a": 1}, "a", 1, "label")
        assert result is None  # match → no issue

    def test_simple_field_mismatch(self):
        result = tg._check_field({"a": 1}, "a", 2, "label")
        assert result is not None
        assert result["field"] == "a"
        # `_check_field` returns {field, problem, fix, severity} — problem
        # contains the label.
        assert "label" in result["problem"]

    def test_nested_field_match(self):
        result = tg._check_field(
            {"settings": {"timeout": 600}}, "settings.timeout", 600, "lbl")
        assert result is None

    def test_nested_field_missing(self):
        result = tg._check_field(
            {"settings": {}}, "settings.timeout", 600, "lbl")
        assert result is not None
        assert result["field"] == "settings.timeout"
