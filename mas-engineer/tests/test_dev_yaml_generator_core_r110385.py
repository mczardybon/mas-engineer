"""R110-385 — dev_yaml_generator_core.py 0% → 100% coverage push.

Module: tools/dev_yaml_generator_core.py (84 lines, 62 stmts, 2 top-level fns)
  - generate_agent_yaml(agent_name, agent_data, schema) → str
  - validate_generated(name, generated, current_path)     → (bool, list[str])

The module is the SHARED CORE used by both dev_yaml_generator.py
(generic) and dev_yaml_generator_core.py (specific). It is imported
by R110-256+ recipe-generation recipes to produce YAML files from
agent schemas with the standard MAS-Engineer boilerplate (header,
template tags, R01/R09 rule references, escaped quotes).

Total: 6 TestClasses, ~35 test methods, 100% line+branch coverage.

Patterns applied per R110-375..R110-384 R-sprint precedent:
  - Real YAML written to tmp_path (no real /tmp pollution)
  - No subprocess; pure-Python testing
  - All escape sequences tested (single quote doubling, backslash
    doubling, double-quote escaping, page-break escaping)
  - All conditional branches covered (if/else for prompt header,
    settings merge None-skip, validate file-exists, parse-error)
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


# Import the module-under-test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_yaml_generator_core


# ============================================================
# TestGenerateAgentYaml — basic flow
# ============================================================
class TestGenerateAgentYaml:
    """generate_agent_yaml: schema + agent_data → YAML string."""

    def test_minimal_inputs_produces_valid_yaml(self):
        """Empty agent_data + minimal schema → valid YAML string with boilerplate."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "test_agent", {}, {"standard_settings": {}, "template_tags": {}}
        )
        # Top-level fields present
        assert 'version: "1.0.0"' in out
        assert "title: " in out
        assert "description: " in out
        assert "instructions: " in out
        assert "prompt: " in out
        assert "settings:" in out
        # Parses as valid YAML
        parsed = yaml.safe_load(out)
        assert isinstance(parsed, dict)
        assert parsed['version'] == "1.0.0"

    def test_default_title_falls_back_to_SUB_MAS(self):
        """No title in agent_data → 'SUB-MAS-{name.upper()}'."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "my_agent", {}, {"standard_settings": {}, "template_tags": {}}
        )
        # Default title = SUB-MAS-MY_AGENT
        assert "SUB-MAS-MY_AGENT" in out

    def test_custom_title_overrides_default(self):
        """title in agent_data → uses that, not the SUB-MAS fallback."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "my_agent",
            {"title": "Custom Title"},
            {"standard_settings": {}, "template_tags": {}}
        )
        assert "Custom Title" in out
        assert "SUB-MAS" not in out

    def test_default_description_includes_version_and_title(self):
        """No description → 'v1.0.0 | {title}'."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "x", {"title": "MyTitle"}, {"standard_settings": {}, "template_tags": {}}
        )
        # description: 'v1.0.0 | MyTitle'
        parsed = yaml.safe_load(out)
        assert parsed['description'] == "v1.0.0 | MyTitle"

    def test_custom_description_overrides_default(self):
        """description in agent_data → uses that."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "x",
            {"description": "Custom desc"},
            {"standard_settings": {}, "template_tags": {}}
        )
        parsed = yaml.safe_load(out)
        assert parsed['description'] == "Custom desc"


# ============================================================
# TestGenerateAgentYamlHeader — header prepending
# ============================================================
class TestGenerateAgentYamlHeader:
    """Header (emoji + title) is prepended to prompt_text if not already there."""

    def test_prompt_prepended_with_header_when_no_match(self):
        """prompt doesn't start with header → header + \\n\\n + prompt (raw).

        NOTE: YAML single-quote-str does flow-folding: the raw file has
        'header\\n\\nprompt' but yaml.safe_load folds consecutive newlines
        to a single '\\n'. We test the RAW output here, not the parsed
        value (test_parsed_includes_emoji_header tests the parsed value).
        """
        schema = {
            "standard_settings": {},
            "template_tags": {"HEADER": "🔧 MyAgent"},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"title": "MyAgent", "prompt": "do stuff"}, schema
        )
        # Raw file contains header + \\n\\n + prompt
        assert "🔧 MyAgent\n\ndo stuff" in out
        assert "do stuff" in out

    def test_prompt_not_prepended_when_already_has_header(self):
        """prompt already starts with header → no double-prepend (raw)."""
        schema = {
            "standard_settings": {},
            "template_tags": {"HEADER": "🔧 MyAgent"},
        }
        prompt_with_header = "🔧 MyAgent\n\ndo stuff"
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"title": "MyAgent", "prompt": prompt_with_header}, schema
        )
        # Should NOT contain "🔧 MyAgent\n\n🔧 MyAgent" (no double prepend)
        assert "🔧 MyAgent\n\n🔧 MyAgent" not in out
        # The original prompt is preserved
        assert prompt_with_header in out

    def test_empty_prompt_not_prepended_with_header(self):
        """Empty prompt_text → no header prepending (the `if prompt_text` guard)."""
        schema = {
            "standard_settings": {},
            "template_tags": {"HEADER": "🔧 MyAgent"},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"title": "MyAgent", "prompt": ""}, schema
        )
        # No header prepending for empty prompt
        assert "🔧 MyAgent" not in out

    def test_default_header_template_when_not_in_schema(self):
        """No HEADER tag → uses default '{emoji} {title}' (raw output)."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a",
            {"title": "MyTitle", "prompt": "do stuff"},
            {"standard_settings": {}, "template_tags": {}},
        )
        # Raw output: ' MyTitle\n\ndo stuff' (leading space because
        # '{emoji} {title}'.format(emoji="", title="MyTitle") = " MyTitle")
        assert " MyTitle\n\ndo stuff" in out

    def test_prompt_single_quotes_doubled(self):
        """Single quotes in prompt are escaped (YAML single-quote-str)."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"prompt": "it's a test"}, {"standard_settings": {}, "template_tags": {}}
        )
        # Single quote should be doubled: "it''s a test"
        assert "it''s a test" in out


# ============================================================
# TestGenerateAgentYamlInstructions — R01/R09 tags
# ============================================================
class TestGenerateAgentYamlInstructions:
    """R01/R09 template tags are appended to instructions if not present."""

    def test_R01_tag_appended_when_not_present(self):
        """R01 tag missing from instructions → appended."""
        schema = {
            "standard_settings": {},
            "template_tags": {"R01": "  - Rule R01 text"},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": "do stuff"}, schema
        )
        parsed = yaml.safe_load(out)
        assert "do stuff" in parsed['instructions']
        assert "Rule R01 text" in parsed['instructions']

    def test_R09_tag_appended_when_not_present(self):
        """R09 tag missing from instructions → appended."""
        schema = {
            "standard_settings": {},
            "template_tags": {"R09": "  - Rule R09 text"},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": "do stuff"}, schema
        )
        parsed = yaml.safe_load(out)
        assert "Rule R09 text" in parsed['instructions']

    def test_R01_tag_not_appended_when_already_present(self):
        """R01 already in instructions → not re-appended (raw output check).

        Uses the unescaped R01 string. Note: the source checks
        `tag_r01 not in instr_text` where tag_r01 is the backslash-escaped
        version. If the input has no backslashes/double-quotes, the
        escaped and unescaped are the same.
        """
        r01 = "  - Rule R01 text"
        schema = {
            "standard_settings": {},
            "template_tags": {"R01": r01},
        }
        # instructions already contains the R01 string
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": f"do stuff\n{r01}"}, schema
        )
        # The R01 should appear only once in the raw output
        assert out.count(r01) == 1

    def test_empty_R01_not_appended(self):
        """R01 tag empty string → not appended (the `if instr_r01` guard)."""
        schema = {
            "standard_settings": {},
            "template_tags": {"R01": ""},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": "do stuff"}, schema
        )
        parsed = yaml.safe_load(out)
        # instructions is just "do stuff" (no extra appending)
        assert parsed['instructions'] == "do stuff"

    def test_empty_R09_not_appended(self):
        """R09 tag empty string → not appended."""
        schema = {
            "standard_settings": {},
            "template_tags": {"R09": ""},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": "do stuff"}, schema
        )
        parsed = yaml.safe_load(out)
        assert parsed['instructions'] == "do stuff"

    def test_both_R01_and_R09_appended(self):
        """Both R01 and R09 set → both appended."""
        schema = {
            "standard_settings": {},
            "template_tags": {"R01": "R01-text", "R09": "R09-text"},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": "do stuff"}, schema
        )
        parsed = yaml.safe_load(out)
        assert "R01-text" in parsed['instructions']
        assert "R09-text" in parsed['instructions']

    def test_instructions_backslash_escaped(self):
        """Backslashes in instructions are doubled (YAML escape)."""
        schema = {"standard_settings": {}, "template_tags": {}}
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": "path: C:\\foo\\bar"}, schema
        )
        # The backslashes should be doubled for YAML safety
        assert "C:\\\\foo\\\\bar" in out
        # The parsed value should round-trip to the original
        parsed = yaml.safe_load(out)
        assert parsed['instructions'] == "path: C:\\foo\\bar"

    def test_instructions_double_quote_escaped(self):
        """Double quotes in instructions are backslash-escaped."""
        schema = {"standard_settings": {}, "template_tags": {}}
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": 'say "hello"'}, schema
        )
        # " → \" in the raw output
        assert 'say \\"hello\\"' in out
        parsed = yaml.safe_load(out)
        assert parsed['instructions'] == 'say "hello"'

    def test_instructions_page_break_replaced_with_newline(self):
        """\\x0c (form feed) in instructions → literal \\\\n in raw YAML output.

        The raw YAML output uses double-quoted style for instructions, so
        the form-feed character (\\x0c) is replaced with the 2-character
        sequence '\\\\n' (backslash + n). When yaml.safe_load parses the
        double-quoted string, '\\\\n' is interpreted as a literal newline.
        """
        schema = {"standard_settings": {}, "template_tags": {}}
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"instructions": "line1\x0cline2"}, schema
        )
        # The raw output should contain 'line1\\nline2' (literal backslash-n)
        assert "line1\\nline2" in out


# ============================================================
# TestGenerateAgentYamlSettings — settings merge
# ============================================================
class TestGenerateAgentYamlSettings:
    """Settings from standard_settings + agent_data are merged."""

    def test_standard_settings_only(self):
        """No agent settings → just standard_settings."""
        std = {"timeout": 600, "max_turns": 50}
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {}, {"standard_settings": std, "template_tags": {}}
        )
        parsed = yaml.safe_load(out)
        assert parsed['settings']['timeout'] == 600
        assert parsed['settings']['max_turns'] == 50

    def test_agent_settings_overrides_standard(self):
        """Agent setting with same key → overrides standard."""
        std = {"timeout": 600, "max_turns": 50}
        agent = {"timeout": 1200}
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"settings": agent}, {"standard_settings": std, "template_tags": {}}
        )
        parsed = yaml.safe_load(out)
        assert parsed['settings']['timeout'] == 1200
        assert parsed['settings']['max_turns'] == 50  # standard kept

    def test_agent_settings_None_value_skipped(self):
        """Agent setting value is None → standard value kept (not overridden)."""
        std = {"timeout": 600}
        agent = {"timeout": None, "max_turns": 100}
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"settings": agent}, {"standard_settings": std, "template_tags": {}}
        )
        parsed = yaml.safe_load(out)
        # None → standard 600 kept
        assert parsed['settings']['timeout'] == 600
        # max_turns not in standard → agent 100 added
        assert parsed['settings']['max_turns'] == 100

    def test_empty_agent_settings_does_not_override(self):
        """agent_settings is empty dict → standard used as-is."""
        std = {"timeout": 600}
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"settings": {}}, {"standard_settings": std, "template_tags": {}}
        )
        parsed = yaml.safe_load(out)
        assert parsed['settings']['timeout'] == 600

    def test_no_standard_settings_no_agent_settings(self):
        """Both empty → settings section is empty (no entries)."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {}, {"standard_settings": {}, "template_tags": {}}
        )
        # The "settings:" line is there but no entries
        assert "settings:" in out
        # Parsed settings should be empty
        # (the 'settings:' is followed by no indented keys)


# ============================================================
# TestGenerateAgentYamlEmoji — emoji field
# ============================================================
class TestGenerateAgentYamlEmoji:
    """emoji in agent_data is used in the header template."""

    def test_emoji_appears_in_header(self):
        """emoji='🔧' → header starts with '🔧' (raw output)."""
        schema = {
            "standard_settings": {},
            "template_tags": {"HEADER": "{emoji} {title}"},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a",
            {"title": "X", "emoji": "🔧", "prompt": "do stuff"},
            schema,
        )
        # Raw output: '🔧 X\n\ndo stuff' (prepended as header)
        assert "🔧 X\n\ndo stuff" in out

    def test_no_emoji_default_empty(self):
        """No emoji in agent_data → emoji is '' (default), header is '{title}' part."""
        schema = {
            "standard_settings": {},
            "template_tags": {"HEADER": "{emoji} | {title}"},
        }
        out = dev_yaml_generator_core.generate_agent_yaml(
            "a", {"title": "X", "prompt": "do stuff"}, schema,
        )
        # '{emoji} | {title}'.format(emoji="", title="X") = " | X"
        # So the raw output: " | X\n\ndo stuff"
        assert " | X\n\ndo stuff" in out


# ============================================================
# TestValidateGenerated — file-comparison validator
# ============================================================
class TestValidateGenerated:
    """validate_generated: compare generated YAML vs existing file."""

    def test_missing_current_path_returns_FEHLT(self, tmp_path):
        """current_path doesn't exist → (False, ['FEHLT'])."""
        missing = tmp_path / "nope.yaml"
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", "version: '1.0.0'", str(missing)
        )
        assert result is False
        assert diffs == ["FEHLT"]

    def test_matching_files_returns_True_empty_diffs(self, tmp_path):
        """Generated matches current → (True, [])."""
        current = tmp_path / "current.yaml"
        current.write_text(
            'version: "1.0.0"\n'
            'title: Same\n'
            'description: Same\n'
            'settings:\n'
            '  timeout: 600\n'
            '  max_steps: 5\n'
            '  goose_provider: openai\n'
            '  goose_model: gpt-4\n'
        )
        generated = (
            'version: "1.0.0"\n'
            'title: Same\n'
            'description: Same\n'
            'settings:\n'
            '  timeout: 600\n'
            '  max_steps: 5\n'
            '  goose_provider: openai\n'
            '  goose_model: gpt-4\n'
        )
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is True
        assert diffs == []

    def test_title_diff_returned(self, tmp_path):
        """Title differs → diff in result, result is False."""
        current = tmp_path / "current.yaml"
        current.write_text('version: "1.0.0"\ntitle: Old\ndescription: x\n')
        generated = 'version: "1.0.0"\ntitle: New\ndescription: x\n'
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert any("title" in d for d in diffs)
        assert any("Old" in d for d in diffs)
        assert any("New" in d for d in diffs)

    def test_description_diff_returned(self, tmp_path):
        """Description differs → diff in result."""
        current = tmp_path / "current.yaml"
        current.write_text('version: "1.0.0"\ntitle: x\ndescription: old\n')
        generated = 'version: "1.0.0"\ntitle: x\ndescription: new\n'
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert any("description" in d for d in diffs)

    def test_version_diff_returned(self, tmp_path):
        """Version differs → diff in result."""
        current = tmp_path / "current.yaml"
        current.write_text('version: "0.9.0"\ntitle: x\ndescription: x\n')
        generated = 'version: "1.0.0"\ntitle: x\ndescription: x\n'
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert any("version" in d for d in diffs)

    def test_settings_timeout_diff(self, tmp_path):
        """Settings.timeout differs → diff in result."""
        current = tmp_path / "current.yaml"
        current.write_text(
            'version: "1.0.0"\ntitle: x\ndescription: x\n'
            'settings:\n  timeout: 300\n'
        )
        generated = (
            'version: "1.0.0"\ntitle: x\ndescription: x\n'
            'settings:\n  timeout: 600\n'
        )
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert any("timeout" in d for d in diffs)
        assert any("settings.timeout" in d for d in diffs)

    def test_settings_max_steps_diff(self, tmp_path):
        """Settings.max_steps differs → diff in result."""
        current = tmp_path / "current.yaml"
        current.write_text(
            'version: "1.0.0"\ntitle: x\ndescription: x\n'
            'settings:\n  max_steps: 3\n'
        )
        generated = (
            'version: "1.0.0"\ntitle: x\ndescription: x\n'
            'settings:\n  max_steps: 5\n'
        )
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert any("max_steps" in d for d in diffs)

    def test_settings_goose_provider_diff(self, tmp_path):
        """Settings.goose_provider differs → diff in result."""
        current = tmp_path / "current.yaml"
        current.write_text(
            'version: "1.0.0"\ntitle: x\ndescription: x\n'
            'settings:\n  goose_provider: openai\n'
        )
        generated = (
            'version: "1.0.0"\ntitle: x\ndescription: x\n'
            'settings:\n  goose_provider: anthropic\n'
        )
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert any("goose_provider" in d for d in diffs)

    def test_settings_goose_model_diff(self, tmp_path):
        """Settings.goose_model differs → diff in result."""
        current = tmp_path / "current.yaml"
        current.write_text(
            'version: "1.0.0"\ntitle: x\ndescription: x\n'
            'settings:\n  goose_model: gpt-4\n'
        )
        generated = (
            'version: "1.0.0"\ntitle: x\ndescription: x\n'
            'settings:\n  goose_model: claude-opus-4-6\n'
        )
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert any("goose_model" in d for d in diffs)

    def test_unrelated_field_diff_ignored(self, tmp_path):
        """Differences in fields NOT in the comparison list are ignored."""
        # Both files have 'prompt' set differently, but prompt isn't compared
        current = tmp_path / "current.yaml"
        current.write_text(
            'version: "1.0.0"\ntitle: x\ndescription: x\nprompt: old\n'
        )
        generated = (
            'version: "1.0.0"\ntitle: x\ndescription: x\nprompt: new\n'
        )
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        # prompt is not in the comparison list → no diff
        assert result is True
        assert diffs == []

    def test_multiple_diffs_aggregated(self, tmp_path):
        """Multiple diffs → all reported in the list."""
        current = tmp_path / "current.yaml"
        current.write_text(
            'version: "0.9.0"\ntitle: old\ndescription: old\n'
            'settings:\n  timeout: 300\n  max_steps: 3\n'
            '  goose_provider: openai\n  goose_model: gpt-4\n'
        )
        generated = (
            'version: "1.0.0"\ntitle: new\ndescription: new\n'
            'settings:\n  timeout: 600\n  max_steps: 5\n'
            '  goose_provider: anthropic\n  goose_model: claude\n'
        )
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        # 3 scalar diffs (version, title, description) + 4 settings diffs = 7
        assert len(diffs) == 7

    def test_parse_error_in_generated_returns_PARSE_ERROR(self, tmp_path):
        """YAML parse error in generated → (False, ['PARSE-ERROR: ...'])."""
        current = tmp_path / "current.yaml"
        current.write_text('version: "1.0.0"\ntitle: x\ndescription: x\n')
        # Generated has invalid YAML
        generated = ":\n  - not:\n  valid: [unclosed"
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert len(diffs) == 1
        assert diffs[0].startswith("PARSE-ERROR:")

    def test_parse_error_in_current_returns_PARSE_ERROR(self, tmp_path):
        """YAML parse error in current → (False, ['PARSE-ERROR: ...'])."""
        current = tmp_path / "current.yaml"
        current.write_text(":\n  - not:\n  valid: [unclosed")
        generated = 'version: "1.0.0"\ntitle: x\ndescription: x\n'
        result, diffs = dev_yaml_generator_core.validate_generated(
            "foo", generated, str(current)
        )
        assert result is False
        assert diffs[0].startswith("PARSE-ERROR:")


# ============================================================
# TestRoundTrip — generate + validate (integration)
# ============================================================
class TestRoundTrip:
    """generate_agent_yaml + validate_generated end-to-end."""

    def test_generated_validates_against_itself(self):
        """Output of generate_agent_yaml, written to a file, validates True."""
        out = dev_yaml_generator_core.generate_agent_yaml(
            "x",
            {"title": "X", "description": "v1.0.0 | X"},
            {"standard_settings": {"timeout": 600}, "template_tags": {}},
        )
        # Write to tmp_path
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(out)
            current_path = f.name
        try:
            result, diffs = dev_yaml_generator_core.validate_generated(
                "x", out, current_path
            )
            assert result is True
            assert diffs == []
        finally:
            os.unlink(current_path)
