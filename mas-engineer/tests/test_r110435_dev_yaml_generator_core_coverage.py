"""R110-435 — coverage-push r7: tools/dev_yaml_generator_core.py 0% → 100%.

YAML generator core (84 lines). Shared by dev_yaml_gen_standard
and dev_yaml_gen_sub_recipes. Provides generate_agent_yaml() +
validate_generated().

Targets:
- generate_agent_yaml: schema with standard_settings/template_tags,
  agent_data with full fields (emoji, title, prompt, instructions,
  description, settings), agent_data with empty prompt (no
  prepending), prompt already starting with header (no duplicate
  prepend), single-quote escaping in prompt (a'b → a''b), instr_text
  with R01/R09 tags appended when missing, instr_text already
  containing R01/R09 (not re-appended), instr_text with backslash +
  double-quote escaping, instr_text with form-feed replaced by
  \\n, default title fallback, default description fallback, empty
  agent_settings (no merge), non-empty agent_settings merged on top
  of std, agent_settings with None value (key NOT overwritten)
- validate_generated: missing current_path → (False, ['FEHLT']),
  matching files → (True, []), diff in title/description/version,
  diff in settings.timeout/max_steps/goose_provider/goose_model,
  parse error on generated → (False, [PARSE-ERROR]), parse error on
  current → (False, [PARSE-ERROR]), diffs list formatting
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_yaml_generator_core as ygc  # noqa: E402


SCHEMA_FULL = {
    "standard_settings": {"timeout": 60, "max_steps": 10,
                          "goose_provider": "openai",
                          "goose_model": "gpt-4"},
    "template_tags": {
        "HEADER": "{emoji} {title}",
        "R01": "R01: Be careful",
        "R09": "R09: Validate",
    },
}


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml
# ─────────────────────────────────────────────────────────────────────
class TestGenerateAgentYaml:
    def test_basic_generation(self):
        data = {"emoji": "🔧", "title": "Foo Agent",
                "prompt": "Do the thing",
                "instructions": "Follow rules",
                "description": "A test agent",
                "settings": {}}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        # Parses as YAML
        parsed = yaml.safe_load(out)
        assert parsed["title"] == "Foo Agent"
        assert parsed["description"] == "A test agent"
        assert parsed["version"] == "1.0.0"
        assert "Do the thing" in parsed["prompt"]

    def test_default_title_fallback(self):
        data = {"prompt": "p", "instructions": "i"}
        out = ygc.generate_agent_yaml("bar", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        assert parsed["title"] == "SUB-MAS-BAR"

    def test_default_description_fallback(self):
        data = {"title": "X", "prompt": "p", "instructions": "i"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        assert parsed["description"] == "v1.0.0 | X"

    def test_empty_prompt_not_prepended(self):
        data = {"title": "X", "prompt": "", "instructions": "i"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        # prompt empty → no header prepend
        parsed = yaml.safe_load(out)
        # prompt field should just be empty
        assert parsed["prompt"] == ""

    def test_prompt_with_header_not_double_prepended(self):
        data = {"emoji": "🔧", "title": "X",
                "prompt": "🔧 X\n\nAlready has header",
                "instructions": "i"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        # The prompt should NOT have "🔧 X" twice (no duplicate header)
        assert parsed["prompt"].count("🔧 X") == 1
        assert "Already has header" in parsed["prompt"]

    def test_single_quote_escape_in_prompt(self):
        data = {"title": "X",
                "prompt": "It's a test",
                "instructions": "i"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        # Single quotes doubled in raw output (before YAML parse)
        assert "It''s a test" in out

    def test_r01_appended_when_missing(self):
        data = {"title": "X", "prompt": "p", "instructions": "Follow X"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        assert "R01: Be careful" in parsed["instructions"]
        assert "R09: Validate" in parsed["instructions"]

    def test_r01_not_reappended_when_present(self):
        data = {"title": "X", "prompt": "p",
                "instructions": "Already contains R01: Be careful"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        # R01 should appear exactly once (not appended twice)
        assert parsed["instructions"].count("R01: Be careful") == 1

    def test_r09_not_reappended_when_present(self):
        data = {"title": "X", "prompt": "p",
                "instructions": "Already contains R09: Validate"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        assert parsed["instructions"].count("R09: Validate") == 1

    def test_instr_text_backslash_escape(self):
        data = {"title": "X", "prompt": "p",
                "instructions": "Path: C:\\temp"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        # backslash doubled to escape YAML
        assert "C:\\\\temp" in out or 'C:\\temp' in out

    def test_instr_text_double_quote_escape(self):
        data = {"title": "X", "prompt": "p",
                "instructions": 'Say "hello"'}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        # " escaped to \"
        assert '\\"hello\\"' in out

    def test_instr_text_form_feed_replaced(self):
        data = {"title": "X", "prompt": "p",
                "instructions": "Line1\x0cLine2"}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        # \x0c → \n
        assert "Line1\\nLine2" in out
        assert "\x0c" not in out

    def test_empty_settings_no_merge(self):
        data = {"title": "X", "prompt": "p", "instructions": "i",
                "settings": {}}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        # Settings should still have std defaults
        assert parsed["settings"]["timeout"] == 60
        assert parsed["settings"]["goose_provider"] == "openai"

    def test_agent_settings_merge_on_top_of_std(self):
        data = {"title": "X", "prompt": "p", "instructions": "i",
                "settings": {"timeout": 120, "new_key": "extra"}}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        assert parsed["settings"]["timeout"] == 120  # overridden
        assert parsed["settings"]["new_key"] == "extra"  # added
        # Other std kept
        assert parsed["settings"]["goose_provider"] == "openai"

    def test_agent_settings_none_value_not_overwrite(self):
        data = {"title": "X", "prompt": "p", "instructions": "i",
                "settings": {"timeout": None}}
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        # timeout should keep std default (60), not None
        assert parsed["settings"]["timeout"] == 60

    def test_no_settings_field_uses_std_only(self):
        data = {"title": "X", "prompt": "p", "instructions": "i"}
        # no "settings" key
        out = ygc.generate_agent_yaml("foo", data, SCHEMA_FULL)
        parsed = yaml.safe_load(out)
        assert parsed["settings"]["timeout"] == 60


# ─────────────────────────────────────────────────────────────────────
# validate_generated
# ─────────────────────────────────────────────────────────────────────
class TestValidateGenerated:
    def _write(self, tmp_path, name, data):
        p = tmp_path / name
        p.write_text(yaml.safe_dump(data))
        return str(p)

    def test_missing_current_path(self, tmp_path):
        ok, diffs = ygc.validate_generated(
            "foo", "version: 1.0.0\n", str(tmp_path / "nope.yaml"))
        assert ok is False
        assert diffs == ["FEHLT"]

    def test_matching_files(self, tmp_path):
        cur = self._write(tmp_path, "cur.yaml", {
            "version": "1.0.0", "title": "T", "description": "D",
            "settings": {"timeout": 60, "max_steps": 10,
                         "goose_provider": "openai",
                         "goose_model": "gpt-4"},
        })
        gen = yaml.safe_dump({
            "version": "1.0.0", "title": "T", "description": "D",
            "settings": {"timeout": 60, "max_steps": 10,
                         "goose_provider": "openai",
                         "goose_model": "gpt-4"},
        })
        ok, diffs = ygc.validate_generated("foo", gen, cur)
        assert ok is True
        assert diffs == []

    def test_diff_in_title(self, tmp_path):
        cur = self._write(tmp_path, "cur.yaml", {
            "version": "1.0.0", "title": "OLD", "description": "D",
            "settings": {"timeout": 60},
        })
        gen = yaml.safe_dump({
            "version": "1.0.0", "title": "NEW", "description": "D",
            "settings": {"timeout": 60},
        })
        ok, diffs = ygc.validate_generated("foo", gen, cur)
        assert ok is False
        assert any("title" in d for d in diffs)

    def test_diff_in_description(self, tmp_path):
        cur = self._write(tmp_path, "cur.yaml", {
            "version": "1.0.0", "title": "T", "description": "OLD",
            "settings": {"timeout": 60},
        })
        gen = yaml.safe_dump({
            "version": "1.0.0", "title": "T", "description": "NEW",
            "settings": {"timeout": 60},
        })
        ok, diffs = ygc.validate_generated("foo", gen, cur)
        assert any("description" in d for d in diffs)

    def test_diff_in_version(self, tmp_path):
        cur = self._write(tmp_path, "cur.yaml", {
            "version": "0.9.0", "title": "T", "description": "D",
            "settings": {"timeout": 60},
        })
        gen = yaml.safe_dump({
            "version": "1.0.0", "title": "T", "description": "D",
            "settings": {"timeout": 60},
        })
        ok, diffs = ygc.validate_generated("foo", gen, cur)
        assert any("version" in d for d in diffs)

    def test_diff_in_settings_timeout(self, tmp_path):
        cur = self._write(tmp_path, "cur.yaml", {
            "version": "1.0.0", "title": "T", "description": "D",
            "settings": {"timeout": 60},
        })
        gen = yaml.safe_dump({
            "version": "1.0.0", "title": "T", "description": "D",
            "settings": {"timeout": 120},
        })
        ok, diffs = ygc.validate_generated("foo", gen, cur)
        assert any("settings.timeout" in d for d in diffs)

    def test_diff_in_settings_goose_provider(self, tmp_path):
        cur = self._write(tmp_path, "cur.yaml", {
            "version": "1.0.0", "title": "T", "description": "D",
            "settings": {"goose_provider": "openai"},
        })
        gen = yaml.safe_dump({
            "version": "1.0.0", "title": "T", "description": "D",
            "settings": {"goose_provider": "anthropic"},
        })
        ok, diffs = ygc.validate_generated("foo", gen, cur)
        assert any("goose_provider" in d for d in diffs)

    def test_parse_error_on_generated(self, tmp_path):
        cur = self._write(tmp_path, "cur.yaml", {
            "version": "1.0.0", "title": "T",
        })
        ok, diffs = ygc.validate_generated(
            "foo", "a: [unterminated\n", cur)
        assert ok is False
        assert any("PARSE-ERROR" in d for d in diffs)

    def test_parse_error_on_current(self, tmp_path):
        p = tmp_path / "cur.yaml"
        p.write_text("a: [unterminated\n")
        ok, diffs = ygc.validate_generated(
            "foo", "version: 1.0.0\n", str(p))
        assert ok is False
        assert any("PARSE-ERROR" in d for d in diffs)

    def test_diffs_list_formatting(self, tmp_path):
        cur = self._write(tmp_path, "cur.yaml", {
            "version": "1.0.0", "title": "OLD", "description": "D",
            "settings": {"timeout": 60, "max_steps": 10},
        })
        gen = yaml.safe_dump({
            "version": "1.0.0", "title": "NEW", "description": "D",
            "settings": {"timeout": 60, "max_steps": 20},
        })
        ok, diffs = ygc.validate_generated("foo", gen, cur)
        # 2 diffs expected: title, settings.max_steps
        assert len(diffs) == 2
        assert all(d.startswith("  ") for d in diffs)
        assert all("gen=" in d and "cur=" in d for d in diffs)
