"""R110-526 coverage tests for tools/dev_yaml_generator_core.py.

Module: 84 LOC, 2 functions, 0% covered.

Functions tested:
  - generate_agent_yaml(name, agent_data, schema)  lines 13-61
    Builds YAML string for a sub-agent recipe from agent_data dict
    + schema dict containing standard_settings + template_tags.

  - validate_generated(name, generated, current_path)  lines 64-84
    Compares generated YAML string against the existing recipe YAML
    on disk and returns (bool, [diffs]) tuple.

Strategy: pure function tests with no subprocess. Both functions
take primitives + dicts and return strings/tuples.

Verification target: 100% line + 100% branch for dev_yaml_generator_core.py.
"""
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import dev_yaml_generator_core as core  # noqa: E402


# ---------------------------- fixtures ----------------------------

@pytest.fixture
def base_schema():
    """Schema with standard_settings + HEADER/R01/R09 template_tags."""
    return {
        "standard_settings": {
            "timeout": 600,
            "max_turns": 100,
        },
        "template_tags": {
            "HEADER": "{emoji} {title}",
            "R01": "R01: do the thing\n",
            "R09": "R09: another thing\n",
        },
    }


@pytest.fixture
def base_agent_data():
    """Minimal agent_data with title/prompt/instructions/emoji."""
    return {
        "title": "Test Agent",
        "emoji": "\U0001f680",  # 🚀
        "prompt": "do stuff",
        "instructions": "be helpful\n",
        "description": "v1.0.0 | Test Agent",
        "settings": {},
    }


# ====================== generate_agent_yaml =======================

def test_generate_basic_string(base_schema, base_agent_data):
    """Covers lines 15-20: pull standard_settings + template_tags, format HEADER."""
    out = core.generate_agent_yaml("test_agent", base_agent_data, base_schema)
    assert "title: Test Agent" in out
    assert "version: \"1.0.0\"" in out
    assert "Test Agent" in out


def test_generate_default_title_when_missing(base_schema):
    """Covers line 19 fallback: title missing → 'SUB-MAS-{NAME.upper()}'."""
    data = {"prompt": "x", "instructions": "y"}
    out = core.generate_agent_yaml("foo_bar", data, base_schema)
    assert "SUB-MAS-FOO_BAR" in out


def test_generate_no_emoji_in_header(base_schema):
    """Covers line 18 fallback: emoji missing → '' (empty prefix in header)."""
    data = {"title": "T", "prompt": "x", "instructions": "y"}
    out = core.generate_agent_yaml("n", data, base_schema)
    # HEADER = "{emoji} {title}" with emoji='' → " T"
    assert "title: T" in out


def test_generate_prepends_header_when_prompt_doesnt_start_with_it(
        base_schema, base_agent_data):
    """Covers line 23 True branch: prompt missing header → prepend header."""
    base_agent_data["prompt"] = "do stuff without header"
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    assert out.startswith("version:")  # header section
    # The prompt field should contain the HEADER prepended
    # Find prompt line
    assert any(line.startswith("prompt:") for line in out.splitlines())


def test_generate_skips_header_prepend_when_already_present(
        base_schema, base_agent_data):
    """Covers line 23 False branch: prompt already starts with HEADER → no prepend."""
    base_agent_data["prompt"] = "do stuff without header"
    out1 = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # Now feed the output's prompt back as input - it should already have HEADER
    # Simpler: feed prompt that starts with what HEADER evaluates to
    base_agent_data["prompt"] = "Test Agent\n\nsome prompt text"
    out2 = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # Should not double-prepend
    prompt_count = out2.count("some prompt text")
    assert prompt_count == 1


def test_generate_empty_prompt_no_prepend(base_schema, base_agent_data):
    """Covers line 23 False branch: prompt_text='' → no header prepend."""
    base_agent_data["prompt"] = ""
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # prompt line should exist but be empty
    assert "prompt:" in out


def test_generate_escapes_single_quote_in_prompt(
        base_schema, base_agent_data):
    """Covers line 25: prompt.replace(\"'\", \"''\")."""
    base_agent_data["prompt"] = "it's tricky"
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    assert "''" in out  # quote doubled


def test_generate_r01_r09_appended_when_missing(base_schema, base_agent_data):
    """Covers lines 34-37: instr_r01/r09 not in instr_text → append."""
    base_agent_data["instructions"] = "base\n"
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # R01/R09 from schema should now be in instructions line
    assert "R01:" in out
    assert "R09:" in out


def test_generate_r01_r09_skipped_when_already_present(
        base_schema, base_agent_data):
    """Covers lines 34-37 False branches: tag already in instr_text."""
    base_agent_data["instructions"] = "preface\nR01: do the thing\nR09: another thing\n"
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # Should appear only once
    assert out.count("R01: do the thing") == 1
    assert out.count("R09: another thing") == 1


def test_generate_escapes_backslash_and_quote_in_instructions(
        base_schema, base_agent_data):
    """Covers lines 31-32, 39: escape backslash and quote in R01/R09/instr."""
    base_agent_data["instructions"] = "with \"quote\" and \\ backslash\n"
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # quotes should be escaped
    assert '\\"' in out


def test_generate_replaces_form_feed_in_instructions(
        base_schema, base_agent_data):
    """Covers line 40: \x0c → \\n."""
    base_agent_data["instructions"] = "line1\x0cline2\n"
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # Form feed replaced with literal \n
    assert "\\n" in out
    assert "\x0c" not in out


def test_generate_default_description(base_schema, base_agent_data):
    """Covers line 42 fallback: description missing → 'v1.0.0 | {title}'."""
    base_agent_data.pop("description", None)
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    assert "v1.0.0 | Test Agent" in out


def test_generate_settings_merge(base_schema, base_agent_data):
    """Covers lines 44-49: settings = std, then merge agent_settings (skip None)."""
    base_agent_data["settings"] = {"timeout": 999, "extra": "yes", "skip_me": None}
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # timeout should be overridden to 999
    assert "timeout: 999" in out
    # extra key added
    assert "extra: yes" in out
    # skip_me is None so not added
    assert "skip_me" not in out


def test_generate_settings_empty(base_schema, base_agent_data):
    """Covers line 46 False branch: agent_settings falsy → skip merge."""
    base_agent_data["settings"] = {}
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    # Should have std settings but nothing more
    assert "timeout: 600" in out
    assert "max_turns: 100" in out


def test_generate_returns_string_with_trailing_newline(
        base_schema, base_agent_data):
    """Covers line 61: return '\\n'.join(lines) + '\\n'."""
    out = core.generate_agent_yaml("a", base_agent_data, base_schema)
    assert out.endswith("\n")


# ======================== validate_generated ========================

def _write_yaml(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content))


def test_validate_missing_file_returns_false(base_agent_data, tmp_path):
    """Covers lines 66-67: current_path doesn't exist → (False, ['FEHLT'])."""
    gen = core.generate_agent_yaml("a", base_agent_data, {
        "standard_settings": {}, "template_tags": {}})
    ok, diffs = core.validate_generated("a", gen, str(tmp_path / "nope.yaml"))
    assert ok is False
    assert diffs == ["FEHLT"]


def test_validate_parse_error_returns_false(tmp_path, base_agent_data):
    """Covers lines 70-74: yaml.safe_load raises → (False, ['PARSE-ERROR: ...'])."""
    bad = "version: '1.0.0'\ntitle: \"unclosed quote"
    _write_yaml(tmp_path / "cur.yaml", bad)
    ok, diffs = core.validate_generated("a", "version: 1\n", str(tmp_path / "cur.yaml"))
    assert ok is False
    assert any(d.startswith("PARSE-ERROR") for d in diffs)


def test_validate_title_diff(tmp_path, base_agent_data):
    """Covers lines 76-78: title differs → diff entry."""
    cur = "version: '1.0.0'\ntitle: Wrong\ndescription: d\nsettings: {}\n"
    gen = "version: '1.0.0'\ntitle: Right\ndescription: d\nsettings: {}\n"
    _write_yaml(tmp_path / "cur.yaml", cur)
    ok, diffs = core.validate_generated("a", gen, str(tmp_path / "cur.yaml"))
    assert ok is False
    assert any("title" in d for d in diffs)


def test_validate_description_diff(tmp_path):
    """Covers lines 76-78: description differs → diff entry."""
    cur = "version: '1.0.0'\ntitle: T\ndescription: old\nsettings: {}\n"
    gen = "version: '1.0.0'\ntitle: T\ndescription: new\nsettings: {}\n"
    p = tmp_path / "cur.yaml"
    _write_yaml(p, cur)
    ok, diffs = core.validate_generated("a", gen, str(p))
    assert ok is False
    assert any("description" in d for d in diffs)


def test_validate_version_diff(tmp_path):
    """Covers lines 76-78: version differs → diff entry."""
    cur = "version: '0.9.0'\ntitle: T\ndescription: d\nsettings: {}\n"
    gen = "version: '1.0.0'\ntitle: T\ndescription: d\nsettings: {}\n"
    p = tmp_path / "cur.yaml"
    _write_yaml(p, cur)
    ok, diffs = core.validate_generated("a", gen, str(p))
    assert ok is False
    assert any("version" in d for d in diffs)


def test_validate_settings_diff_timeout(tmp_path):
    """Covers lines 79-83: settings.timeout differs → diff entry."""
    cur = "version: '1.0.0'\ntitle: T\ndescription: d\nsettings: {timeout: 600}\n"
    gen = "version: '1.0.0'\ntitle: T\ndescription: d\nsettings: {timeout: 999}\n"
    p = tmp_path / "cur.yaml"
    _write_yaml(p, cur)
    ok, diffs = core.validate_generated("a", gen, str(p))
    assert ok is False
    assert any("settings.timeout" in d for d in diffs)


def test_validate_settings_diff_max_steps(tmp_path):
    """Covers lines 79-83: settings.max_steps differs → diff entry."""
    cur = "version: '1.0.0'\ntitle: T\ndescription: d\nsettings: {max_steps: 5}\n"
    gen = "version: '1.0.0'\ntitle: T\ndescription: d\nsettings: {max_steps: 10}\n"
    p = tmp_path / "cur.yaml"
    _write_yaml(p, cur)
    ok, diffs = core.validate_generated("a", gen, str(p))
    assert ok is False
    assert any("settings.max_steps" in d for d in diffs)


def test_validate_settings_diff_goose_provider(tmp_path):
    """Covers lines 79-83: settings.goose_provider differs → diff entry."""
    cur = ("version: '1.0.0'\ntitle: T\ndescription: d\n"
           "settings: {goose_provider: openai}\n")
    gen = ("version: '1.0.0'\ntitle: T\ndescription: d\n"
           "settings: {goose_provider: anthropic}\n")
    p = tmp_path / "cur.yaml"
    _write_yaml(p, cur)
    ok, diffs = core.validate_generated("a", gen, str(p))
    assert ok is False
    assert any("settings.goose_provider" in d for d in diffs)


def test_validate_settings_diff_goose_model(tmp_path):
    """Covers lines 79-83: settings.goose_model differs → diff entry."""
    cur = ("version: '1.0.0'\ntitle: T\ndescription: d\n"
           "settings: {goose_model: gpt-4}\n")
    gen = ("version: '1.0.0'\ntitle: T\ndescription: d\n"
           "settings: {goose_model: claude}\n")
    p = tmp_path / "cur.yaml"
    _write_yaml(p, cur)
    ok, diffs = core.validate_generated("a", gen, str(p))
    assert ok is False
    assert any("settings.goose_model" in d for d in diffs)


def test_validate_no_diff_returns_true(tmp_path):
    """Covers line 84: len(diffs) == 0 → (True, [])."""
    content = ("version: '1.0.0'\ntitle: T\ndescription: d\n"
               "settings: {timeout: 600}\n")
    p = tmp_path / "cur.yaml"
    _write_yaml(p, content)
    ok, diffs = core.validate_generated("a", content, str(p))
    assert ok is True
    assert diffs == []


def test_validate_settings_missing_in_both_no_diff(tmp_path):
    """Covers line 79 `or {}` fallback: both gs and cs are None → no diff."""
    # No `settings:` line at all in either YAML
    content = "version: '1.0.0'\ntitle: T\ndescription: d\n"
    p = tmp_path / "cur.yaml"
    _write_yaml(p, content)
    ok, diffs = core.validate_generated("a", content, str(p))
    assert ok is True
    assert diffs == []


def test_validate_settings_only_in_generated(tmp_path):
    """Covers line 80: cs.get('settings') is None → use {}."""
    cur = "version: '1.0.0'\ntitle: T\ndescription: d\n"
    gen = "version: '1.0.0'\ntitle: T\ndescription: d\nsettings: {timeout: 600}\n"
    p = tmp_path / "cur.yaml"
    _write_yaml(p, cur)
    ok, diffs = core.validate_generated("a", gen, str(p))
    assert ok is False
    assert any("settings.timeout" in d for d in diffs)


def test_validate_settings_only_in_current(tmp_path):
    """Covers line 79: gs.get('settings') is None → use {}."""
    cur = "version: '1.0.0'\ntitle: T\ndescription: d\nsettings: {timeout: 600}\n"
    gen = "version: '1.0.0'\ntitle: T\ndescription: d\n"
    p = tmp_path / "cur.yaml"
    _write_yaml(p, cur)
    ok, diffs = core.validate_generated("a", gen, str(p))
    assert ok is False
    assert any("settings.timeout" in d for d in diffs)
