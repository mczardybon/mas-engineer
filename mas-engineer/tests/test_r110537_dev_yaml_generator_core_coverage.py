"""R110-537 coverage tests for tools/dev_yaml_generator_core.py.

Module: 84 LOC, ~58 stmts, 2 functions, 0% covered.

Functions tested:
  - generate_agent_yaml(agent_name, agent_data, schema)   lines 13-61
  - validate_generated(name, generated, current_path)     lines 64-84

Strategy: Direct function calls with crafted schema/agent_data dicts.

Key paths to cover:
  - generate_agent_yaml:
    - schema.standard_settings, template_tags (15-16)
    - agent_data.emoji, title, default title (18-19)
    - header from tags HEADER (20)
    - prompt_text from agent_data, prepend header (22-24)
    - replace ' with '' (25)
    - instr_text + R01/R09 tags (27-37)
    - escape backslashes + quotes (39)
    - replace \x0c with \n (40)
    - description default (42)
    - settings merge, skip None values (44-49)
    - lines construction (51-60)
    - return string (61)
  - validate_generated:
    - file not found → False, ['FEHLT'] (66-67)
    - read current (68-69)
    - yaml.safe_load on both (71-72)
    - parse error → False, [PARSE-ERROR: ...] (73-74)
    - diff check title/description/version (76-78)
    - diff check settings (79-83)
    - return (84)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.dev_yaml_generator_core as core  # noqa: E402


# ====================== helpers ==================================

def _schema():
    return {
        "version": "1.0.0",
        "standard_settings": {
            "timeout": 600,
            "max_steps": 100,
            "goose_provider": "openai",
            "goose_model": "deepseek",
        },
        "template_tags": {
            "HEADER": "{emoji} {title}",
            "R01": "\n\n  R01-CONFIRM",
            "R09": "\n\n  R09-ALIGN",
        },
    }


def _agent(**overrides):
    base = {
        "emoji": "🔧",
        "title": "Test Agent",
        "description": "A test agent",
        "prompt": "Do the thing.",
        "instructions": "Be helpful.",
        "settings": {},
    }
    base.update(overrides)
    return base


# ====================== generate_agent_yaml ======================

def test_basic_generation():
    """Covers lines 13-61: basic happy path."""
    out = core.generate_agent_yaml("test", _agent(), _schema())
    assert 'version: "1.0.0"' in out
    assert "title: Test Agent" in out
    assert "description:" in out
    assert "instructions:" in out
    assert "prompt:" in out
    assert "settings:" in out


def test_default_title_when_missing():
    """Covers line 19: title fallback to SUB-MAS-<NAME>."""
    agent = _agent()
    agent.pop("title")
    out = core.generate_agent_yaml("my_agent", agent, _schema())
    assert "title: SUB-MAS-MY_AGENT" in out


def test_default_emoji_empty():
    """Covers line 18: emoji default empty string."""
    agent = _agent(emoji="")
    out = core.generate_agent_yaml("x", agent, _schema())
    # Header "{emoji} {title}" with empty emoji → "  Test Agent"
    assert "title: Test Agent" in out


def test_default_description():
    """Covers line 42: description default 'v1.0.0 | <title>'."""
    agent = _agent()
    agent.pop("description")
    out = core.generate_agent_yaml("x", agent, _schema())
    assert "v1.0.0 | Test Agent" in out


def test_prompt_prepend_header_when_missing():
    """Covers lines 23-24: prompt without header prefix → prepend."""
    agent = _agent(prompt="Just do it.")
    out = core.generate_agent_yaml("x", agent, _schema())
    # Header should be at start of prompt field
    lines = out.split("\n")
    prompt_line = next(l for l in lines if l.startswith("prompt:"))
    # Prompt line should contain header "🔧 Test Agent"
    assert "🔧" in prompt_line
    assert "Test Agent" in prompt_line


def test_prompt_does_not_prepend_when_already_has_header():
    """Covers line 23 False: prompt starts with header → no prepend."""
    agent = _agent(prompt="🔧 Test Agent\n\nbody")
    out = core.generate_agent_yaml("x", agent, _schema())
    # Should have header ONCE, not duplicated
    assert out.count("🔧 Test Agent") == 1


def test_prompt_quote_doubling():
    """Covers line 25: replace ' with '' in prompt_text."""
    agent = _agent(prompt="Don't panic")
    out = core.generate_agent_yaml("x", agent, _schema())
    # The prompt field should have '' (doubled)
    assert "Don''t panic" in out


def test_r01_appended_when_missing():
    """Covers lines 34-35: instr_text without R01 → append."""
    agent = _agent(instructions="Just instructions.")
    out = core.generate_agent_yaml("x", agent, _schema())
    assert "R01-CONFIRM" in out


def test_r01_not_duplicated():
    """Covers line 34 False: instr_text already has R01 → skip."""
    agent = _agent(instructions="Has it.\n\n  R01-CONFIRM")
    out = core.generate_agent_yaml("x", agent, _schema())
    # R01-CONFIRM should appear once in the instructions
    assert out.count("R01-CONFIRM") == 1


def test_r09_appended_when_missing():
    """Covers lines 36-37: same for R09."""
    agent = _agent(instructions="Just instructions.")
    out = core.generate_agent_yaml("x", agent, _schema())
    assert "R09-ALIGN" in out


def test_tag_escape_backslash_and_quote():
    """Covers lines 31-32, 39: escape \\ → \\\\ and " → \\\".".
    In Python source, the escape is single \\ → double \\, and " → \\".
    In YAML output, a literal " becomes \" and \\ becomes \\\\.
    """
    # Schema with R01 that has literal " and \
    schema = _schema()
    schema["template_tags"]["R01"] = '\\begin"quote'
    agent = _agent(instructions="")
    out = core.generate_agent_yaml("x", agent, schema)
    # The instruction line should contain escaped version
    assert '\\begin\\"quote' in out or 'begin\\"quote' in out


def test_x0c_replaced_with_n():
    """Covers line 40: \\x0c → \\n in instr_text."""
    agent = _agent(instructions="before\x0cafter")
    out = core.generate_agent_yaml("x", agent, _schema())
    # \x0c should be gone, replaced by \n (literal in yaml)
    assert "\x0c" not in out


def test_settings_merge_with_none_skip():
    """Covers lines 44-49: settings merge, skip None values.

    Note: 'yes' would be parsed by YAML 1.1 as boolean True.
    Use a non-boolean string for the assertion.
    """
    agent = _agent(settings={"timeout": 300, "max_steps": None,
                              "extra_key": "explicit_str"})
    out = core.generate_agent_yaml("x", agent, _schema())
    parsed = yaml.safe_load(out)
    # timeout overridden to 300
    assert parsed["settings"]["timeout"] == 300
    # max_steps kept at default (None not merged)
    assert parsed["settings"]["max_steps"] == 100
    # extra_key added
    assert parsed["settings"]["extra_key"] == "explicit_str"


def test_settings_empty_dict_keeps_defaults():
    """Covers line 46 False: agent_settings empty → use defaults."""
    agent = _agent(settings={})
    out = core.generate_agent_yaml("x", agent, _schema())
    parsed = yaml.safe_load(out)
    assert parsed["settings"]["timeout"] == 600
    assert parsed["settings"]["max_steps"] == 100


def test_yaml_is_parseable():
    """Covers line 61: returned string is valid YAML."""
    out = core.generate_agent_yaml("x", _agent(), _schema())
    parsed = yaml.safe_load(out)
    assert isinstance(parsed, dict)
    assert parsed["title"] == "Test Agent"


# ====================== validate_generated =======================

def _write_existing(path, content):
    path.write_text(content)
    return path


def test_validate_file_missing(tmp_path):
    """Covers lines 66-67: file not found → False, ['FEHLT']."""
    valid, issues = core.validate_generated("x", "anything",
                                            str(tmp_path / "missing.yaml"))
    assert valid is False
    assert issues == ["FEHLT"]


def test_validate_match(tmp_path):
    """Covers line 84 True: no diffs → True, []."""
    gen = core.generate_agent_yaml("x", _agent(), _schema())
    existing = tmp_path / "x.yaml"
    _write_existing(existing, gen)
    valid, issues = core.validate_generated("x", gen, str(existing))
    assert valid is True
    assert issues == []


def test_validate_title_diff(tmp_path):
    """Covers lines 76-78: title differs → diff added."""
    gen = core.generate_agent_yaml("x", _agent(), _schema())
    # Create existing with different title
    bad = gen.replace("title: Test Agent", "title: Wrong")
    existing = tmp_path / "x.yaml"
    _write_existing(existing, bad)
    valid, issues = core.validate_generated("x", gen, str(existing))
    assert valid is False
    assert any("title:" in i for i in issues)


def test_validate_description_diff(tmp_path):
    """Covers lines 76-78: description differs → diff added."""
    gen = core.generate_agent_yaml("x", _agent(), _schema())
    bad = gen.replace("A test agent", "Wrong desc")
    existing = tmp_path / "x.yaml"
    _write_existing(existing, bad)
    valid, issues = core.validate_generated("x", gen, str(existing))
    assert any("description:" in i for i in issues)


def test_validate_version_diff(tmp_path):
    """Covers lines 76-78: version differs → diff added."""
    gen = core.generate_agent_yaml("x", _agent(), _schema())
    bad = gen.replace('version: "1.0.0"', 'version: "2.0.0"')
    existing = tmp_path / "x.yaml"
    _write_existing(existing, bad)
    valid, issues = core.validate_generated("x", gen, str(existing))
    assert any("version:" in i for i in issues)


def test_validate_settings_diff(tmp_path):
    """Covers lines 79-83: settings.timeout/max_steps/etc. differs → diff added."""
    gen = core.generate_agent_yaml("x", _agent(), _schema())
    bad = gen.replace("timeout: 600", "timeout: 999")
    existing = tmp_path / "x.yaml"
    _write_existing(existing, bad)
    valid, issues = core.validate_generated("x", gen, str(existing))
    assert any("settings.timeout:" in i for i in issues)


def test_validate_parse_error(tmp_path):
    """Covers lines 73-74: yaml.safe_load fails → False, [PARSE-ERROR: ...]."""
    # Generate valid YAML
    gen = core.generate_agent_yaml("x", _agent(), _schema())
    # Existing file with bad YAML
    existing = tmp_path / "x.yaml"
    _write_existing(existing, "broken: : :\n  - :\n -")
    valid, issues = core.validate_generated("x", gen, str(existing))
    assert valid is False
    assert any("PARSE-ERROR" in i for i in issues)


def test_validate_missing_settings_field(tmp_path):
    """Covers lines 79-80: g/c settings missing → defaults to {}.

    Build a YAML doc without 'settings:' field. Both gs and cs
    become {} (line 79-80), so no settings diffs are reported.
    """
    gen = core.generate_agent_yaml("x", _agent(), _schema())
    existing = tmp_path / "x.yaml"
    # Build minimal YAML with version/title/description only — no settings
    existing.write_text('version: "1.0.0"\ntitle: Test Agent\n'
                        'description: x\ninstructions: ""\nprompt: ""\n')
    valid, issues = core.validate_generated("x", gen, str(existing))
    # g has settings, c doesn't → diffs on settings.* keys
    assert any("settings." in i for i in issues)
    assert valid is False
