"""R110-455 — coverage-push r8: tools/dev_yaml_generator_core.py 0% → 100%.

Gemeinsamer Kern for YAML-Generierung. Contains
generate_agent_yaml() and validate_generated() for both
generic/standard variants.

Targets:
- generate_agent_yaml(agent_name, agent_data, schema):
  - schema["standard_settings"] defaults to {}
  - schema["template_tags"] defaults to {}
  - emoji default "", title default f"SUB-MAS-{name.upper()}"
  - header from tags["HEADER"] default "{emoji} {title}"
  - if prompt and not startswith(header) → prepend header + "\n\n"
  - prompt_text.replace("'", "''")
  - instr_r01/r09 from tags defaults ""
  - tag_r01/r09: backslash + quote escaping
  - if instr_r01 and not in instr_text → append
  - if instr_r09 and not in instr_text → append
  - instr_text: backslash+quote escape + \x0c → \\n
  - desc default f"v1.0.0 | {title}"
  - settings = dict(std), then overlay non-None agent_settings
  - lines built: version "1.0.0", title, description '...',
    instructions "...", prompt '...', settings: + indented k:v
  - returns "\n".join(lines) + "\n"

- validate_generated(name, generated, current_path):
  - file not exists → (False, ["FEHLT"])
  - yaml.safe_load on both → on Exception → (False, [f"PARSE-ERROR: ..."])
  - diff keys: title/description/version
  - diff settings: timeout/max_steps/goose_provider/goose_model
  - returns (len(diffs)==0, diffs)
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_yaml_generator_core as ygc  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — base happy path
# ─────────────────────────────────────────────────────────────────────
class TestGenerateHappy:
    def test_minimal_inputs(self):
        # No schema, no agent_data beyond defaults
        out = ygc.generate_agent_yaml("foo", {}, {})
        assert out.startswith('version: "1.0.0"')
        assert "title: SUB-MAS-FOO" in out
        assert "description: 'v1.0.0 | SUB-MAS-FOO'" in out
        assert "settings:" in out

    def test_with_emoji_and_title(self):
        agent_data = {"emoji": "🤖", "title": "My-Agent",
                      "prompt": "body text"}
        out = ygc.generate_agent_yaml("foo", agent_data, {})
        # emoji appears in header → only added to prompt if non-empty
        assert "title: My-Agent" in out
        assert "🤖 My-Agent" in out

    def test_with_description(self):
        agent_data = {"description": "my desc"}
        out = ygc.generate_agent_yaml("foo", agent_data, {})
        assert "description: 'my desc'" in out

    def test_settings_from_schema(self):
        schema = {"standard_settings": {"timeout": 300,
                                          "max_steps": 50}}
        out = ygc.generate_agent_yaml("foo", {}, schema)
        assert "timeout: 300" in out
        assert "max_steps: 50" in out

    def test_settings_overlay_from_agent(self):
        schema = {"standard_settings": {"timeout": 300}}
        agent_data = {"settings": {"timeout": 600, "model": "x"}}
        out = ygc.generate_agent_yaml("foo", agent_data, schema)
        assert "timeout: 600" in out
        assert "model: x" in out

    def test_settings_skip_none(self):
        schema = {"standard_settings": {"timeout": 300}}
        agent_data = {"settings": {"timeout": None}}
        out = ygc.generate_agent_yaml("foo", agent_data, schema)
        # None means skip → standard kept
        assert "timeout: 300" in out

    def test_empty_agent_settings(self):
        agent_data = {"settings": {}}
        out = ygc.generate_agent_yaml("foo", agent_data, {})
        assert "settings:" in out


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — prompt handling
# ─────────────────────────────────────────────────────────────────────
class TestGeneratePrompt:
    def test_empty_prompt(self):
        out = ygc.generate_agent_yaml("foo", {}, {})
        assert "prompt:" in out

    def test_prompt_already_starts_with_header(self):
        # prompt already starts with header → not prepended again
        agent_data = {"prompt": "header-text\nbody"}
        schema = {"template_tags": {"HEADER": "header-text"}}
        out = ygc.generate_agent_yaml("foo", agent_data, schema)
        # Should not have "header-text\n\nheader-text" (double)
        assert "header-text\n\nheader-text" not in out

    def test_prompt_needs_header(self):
        agent_data = {"prompt": "body"}
        schema = {"template_tags": {"HEADER": "HDR"}}
        out = ygc.generate_agent_yaml("foo", agent_data, schema)
        # HDR prepended
        assert "HDR\n\nbody" in out

    def test_prompt_quote_escape(self):
        agent_data = {"prompt": "it's a test"}
        out = ygc.generate_agent_yaml("foo", agent_data, {})
        # Single quote escaped to '' in YAML single-quoted string
        assert "it''s a test" in out


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — instructions + R01/R09 tags
# ─────────────────────────────────────────────────────────────────────
class TestGenerateInstructions:
    def test_no_r_tags(self):
        out = ygc.generate_agent_yaml("foo", {}, {})
        assert 'instructions:' in out

    def test_r01_appended(self):
        schema = {"template_tags": {"R01": "[R01-content]"}}
        out = ygc.generate_agent_yaml("foo", {}, schema)
        assert "[R01-content]" in out

    def test_r09_appended(self):
        schema = {"template_tags": {"R09": "[R09-content]"}}
        out = ygc.generate_agent_yaml("foo", {}, schema)
        assert "[R09-content]" in out

    def test_r01_already_present_skipped(self):
        # If tag text already in instr_text → don't append again
        schema = {"template_tags": {"R01": "[R01]"}}
        agent_data = {"instructions": "[R01]"}
        out = ygc.generate_agent_yaml("foo", agent_data, schema)
        # Count "[R01]" occurrences — should be exactly 1
        # (in instructions, NOT duplicated)
        assert out.count("[R01]") == 1

    def test_r09_already_present_skipped(self):
        schema = {"template_tags": {"R09": "[R09]"}}
        agent_data = {"instructions": "[R09]"}
        out = ygc.generate_agent_yaml("foo", agent_data, schema)
        assert out.count("[R09]") == 1

    def test_r01_escape(self):
        # Backslash + quote in R01 → escaped
        schema = {"template_tags":
                  {"R01": 'has \\ and " quotes'}}
        out = ygc.generate_agent_yaml("foo", {}, schema)
        # Backslash doubled, quote escaped
        assert '\\\\' in out
        assert '\\"' in out

    def test_form_feed_replaced(self):
        # \x0c in instructions → \\n in output
        agent_data = {"instructions": "before\x0cafter"}
        out = ygc.generate_agent_yaml("foo", agent_data, {})
        assert "\\nbefore\\nafter" in out or "before\\nafter" in out


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — return format
# ─────────────────────────────────────────────────────────────────────
class TestGenerateReturn:
    def test_trailing_newline(self):
        out = ygc.generate_agent_yaml("foo", {}, {})
        assert out.endswith("\n")

    def test_returns_str(self):
        out = ygc.generate_agent_yaml("foo", {}, {})
        assert isinstance(out, str)

    def test_settings_indented(self):
        schema = {"standard_settings": {"a": 1}}
        out = ygc.generate_agent_yaml("foo", {}, schema)
        # Two-space indent before setting k:v
        assert "  a: 1" in out


# ─────────────────────────────────────────────────────────────────────
# validate_generated
# ─────────────────────────────────────────────────────────────────────
class TestValidate:
    def test_missing_file(self, tmp_path):
        ok, diffs = ygc.validate_generated(
            "x", "version: '1.0.0'", str(tmp_path / "no.yaml"))
        assert ok is False
        assert diffs == ["FEHLT"]

    def test_parse_error_generated(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("version: '1.0.0'\ntitle: a\n")
        ok, diffs = ygc.validate_generated(
            "x", "bad: yaml: ::", str(cur))
        assert ok is False
        assert "PARSE-ERROR" in diffs[0]

    def test_parse_error_current(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("bad: yaml: ::")
        ok, diffs = ygc.validate_generated(
            "x", "version: '1.0.0'\ntitle: a\n", str(cur))
        assert ok is False
        assert "PARSE-ERROR" in diffs[0]

    def test_no_diffs(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("version: '1.0.0'\ntitle: a\n"
                       "description: 'd'\n"
                       "settings:\n  timeout: 300\n"
                       "  max_steps: 50\n"
                       "  goose_provider: openai\n"
                       "  goose_model: gpt-4\n")
        gen = ("version: '1.0.0'\ntitle: a\n"
               "description: 'd'\n"
               "settings:\n  timeout: 300\n"
               "  max_steps: 50\n"
               "  goose_provider: openai\n"
               "  goose_model: gpt-4\n")
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert ok is True
        assert diffs == []

    def test_title_diff(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\n")
        gen = "title: b\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert ok is False
        assert any("title" in d for d in diffs)

    def test_description_diff(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\ndescription: 'd1'\n")
        gen = "title: a\ndescription: 'd2'\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert any("description" in d for d in diffs)

    def test_version_diff(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\nversion: '1.0.0'\n")
        gen = "title: a\nversion: '2.0.0'\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert any("version" in d for d in diffs)

    def test_settings_timeout_diff(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\nsettings:\n  timeout: 300\n")
        gen = "title: a\nsettings:\n  timeout: 600\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert any("settings.timeout" in d for d in diffs)

    def test_settings_max_steps_diff(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\nsettings:\n  max_steps: 50\n")
        gen = "title: a\nsettings:\n  max_steps: 99\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert any("settings.max_steps" in d for d in diffs)

    def test_settings_goose_provider_diff(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\nsettings:\n  goose_provider: openai\n")
        gen = "title: a\nsettings:\n  goose_provider: anthropic\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert any("goose_provider" in d for d in diffs)

    def test_settings_goose_model_diff(self, tmp_path):
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\nsettings:\n  goose_model: gpt-4\n")
        gen = "title: a\nsettings:\n  goose_model: claude\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert any("goose_model" in d for d in diffs)

    def test_other_setting_diff_ignored(self, tmp_path):
        # settings.foo differs but not in checked list → not in diffs
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\nsettings:\n  foo: 1\n")
        gen = "title: a\nsettings:\n  foo: 2\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert ok is True
        assert diffs == []

    def test_missing_key_in_current(self, tmp_path):
        # current has no "description" key
        cur = tmp_path / "cur.yaml"
        cur.write_text("title: a\n")
        gen = "title: a\ndescription: 'd'\n"
        ok, diffs = ygc.validate_generated("x", gen, str(cur))
        assert any("description" in d for d in diffs)
