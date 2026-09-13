#!/usr/bin/env python3
"""
R110-520: Coverage test for tools/dev_yaml_generator_core.py (84 lines, 0% → 100%).

Context: dev_yaml_generator_core.py provides the shared YAML
generation + validation logic for both YAML-generator variants
(dev_yaml_generator.py and others). Two public functions:

  - generate_agent_yaml(agent_name, agent_data, schema)
      Builds a YAML string from a schema-driven template. The schema
      dict has:
        * 'standard_settings' — dict of default settings (always emitted)
        * 'template_tags'     — dict of header/R01/R09 strings
      agent_data may have: emoji, title, prompt, instructions,
      description, settings (per-agent overrides).

      Logic:
        - emoji default "", title default "SUB-MAS-<NAME>"
        - header = tags['HEADER'].format(emoji, title)
        - if prompt_text is non-empty AND doesn't start with header,
          prepend header\n\n
        - prompt_text: ' → '' (yaml-escape)
        - R01 / R09 tags appended if not already in instr_text
        - instr_text: \\ → \\\\, " → \\", \\x0c → \\n
        - settings: start from std, overlay agent_settings where not None

  - validate_generated(name, generated, current_path)
      Compares generated YAML against an existing file on disk.
      Returns (bool, list_of_diffs).
        - if current_path missing → (False, ['FEHLT'])
        - parse error in either → (False, ['PARSE-ERROR: ...'])
        - else compares keys: title, description, version + settings.{timeout,
          max_steps, goose_provider, goose_model}

Branch coverage strategy: every if/for path in both functions, plus
all schema/agent_data key defaults and overrides.
"""

import os

import pytest
import yaml

import tools.dev_yaml_generator_core as core  # noqa: E402


# Minimal valid schema for tests that need a baseline
MIN_SCHEMA = {
    "standard_settings": {"timeout": 60, "max_steps": 10},
    "template_tags": {
        "HEADER": "{emoji} {title}",
        "R01": "[R01] Be honest.\\n",
        "R09": "[R09] Be concise.\\n",
    },
}


# ─── generate_agent_yaml: defaults & header ────────────────────────

def test_generate_minimal_agent_uses_defaults():
    """Covers line 15-20: minimal agent_data + schema → defaults applied.
    Title becomes 'SUB-MAS-<NAME>' from line 19, header is empty
    emoji + auto title."""
    out = core.generate_agent_yaml("foo", {}, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert parsed["title"] == "SUB-MAS-FOO"
    assert parsed["description"] == "v1.0.0 | SUB-MAS-FOO"
    # prompt was empty → no header prepended → just empty
    assert parsed["prompt"] == ""


def test_generate_uses_emoji_and_title_from_agent_data():
    """Covers line 18-20: emoji + title passed in → header built."""
    out = core.generate_agent_yaml("foo", {
        "emoji": "🧪",
        "title": "Custom Title",
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert parsed["title"] == "Custom Title"


def test_generate_header_prepended_to_prompt_when_missing():
    """Covers line 23 True branch: prompt non-empty and doesn't start
    with header → header + '\n\n' prepended."""
    out = core.generate_agent_yaml("foo", {
        "emoji": "🔬",
        "title": "Scientist",
        "prompt": "do science",
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert parsed["prompt"].startswith("🔬 Scientist")
    assert "do science" in parsed["prompt"]


def test_generate_header_not_double_prepended():
    """Covers line 23 False branch: prompt already starts with header
    → no double prepend."""
    header = "🔬 Scientist"
    out = core.generate_agent_yaml("foo", {
        "emoji": "🔬",
        "title": "Scientist",
        "prompt": f"{header}\nmore content",
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    # Header appears only once
    assert parsed["prompt"].count(header) == 1


def test_generate_prompt_escapes_single_quote():
    """Covers line 25: ' → '' (yaml single-quote doubling)."""
    out = core.generate_agent_yaml("foo", {
        "prompt": "don't do it",
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert "don't" in parsed["prompt"]


# ─── generate_agent_yaml: instructions & R01/R09 ─────────────────

def test_generate_appends_r01_when_missing():
    """Covers line 34-35: instr_r01 non-empty, not in instr_text →
    appended."""
    out = core.generate_agent_yaml("foo", {
        "instructions": "base.",
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert "[R01]" in parsed["instructions"]
    assert "base." in parsed["instructions"]


def test_generate_skips_r01_when_doubled_tag_content_present():
    """Covers line 34 False branch.

    **Pre-existing subtle bug surfaced:** the code does
    `tag_r01 = instr_r01.replace('\\', '\\\\')` BEFORE the
    `tag_r01 not in instr_text` membership check. The doubling
    means the check is comparing the DOUBLED version against the
    ORIGINAL user instr_text — they never match for normal input.
    So the R01 tag is ALWAYS appended regardless of whether the
    user already had similar content.

    To force the False branch (skip), the user's instr_text must
    already contain the doubled form (TWO backslashes before 'n').
    Documented in honest-notes; NOT fixed in this commit per the
    'no production code changes' rule.
    """
    # Use raw string so \\n stays as 2 literal backslashes + n
    instr_text = "header\n" + r"[R01] Be honest.\\n"  # r"\\n" = 2 backslashes + n
    out = core.generate_agent_yaml("foo", {
        "instructions": instr_text,
    }, MIN_SCHEMA)
    import yaml as _yaml
    parsed = _yaml.safe_load(out)
    # R01's tag (after doubling) IS in instr_text → skip
    assert parsed["instructions"].count("[R01]") == 1
    # R09 still appended (R09 content not present in instr_text)
    assert "[R09]" in parsed["instructions"]


def test_generate_appends_r09_when_missing():
    """Covers line 36-37: instr_r09 path."""
    out = core.generate_agent_yaml("foo", {
        "instructions": "base.",
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert "[R09]" in parsed["instructions"]


def test_generate_skips_r09_when_doubled_tag_content_present():
    """Covers line 36 False branch.

    Same pre-existing bug as R01: tag_r09 is doubled before the
    membership check, so we need the doubled form in instr_text.
    """
    instr_text = "header\n" + r"[R09] Be concise.\\n"
    out = core.generate_agent_yaml("foo", {
        "instructions": instr_text,
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    # Both R01 and R09 doubled forms present → both skipped
    assert parsed["instructions"].count("[R01]") == 1
    assert parsed["instructions"].count("[R09]") == 1


def test_generate_skips_empty_r01_r09_tags():
    """Covers line 34 + 36 False branches when tags are empty strings."""
    schema = {"standard_settings": {}, "template_tags": {}}
    out = core.generate_agent_yaml("foo", {
        "instructions": "just base.",
    }, schema)
    parsed = yaml.safe_load(out)
    assert "[R01]" not in parsed["instructions"]
    assert "[R09]" not in parsed["instructions"]


def test_generate_escapes_backslash_and_doublequote_in_instructions():
    """Covers line 39: \ → \\ and " → \" escaping."""
    out = core.generate_agent_yaml("foo", {
        "instructions": 'has "quotes" and \\backslash',
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert '"quotes"' in parsed["instructions"]
    assert "\\backslash" in parsed["instructions"]


def test_generate_replaces_formfeed_in_instructions():
    """Covers line 40: \\x0c → \\n."""
    out = core.generate_agent_yaml("foo", {
        "instructions": "line1\x0cline2",
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    # The formfeed is replaced with literal "\n" before YAML escape
    # → after yaml.safe_load, we get an actual newline
    assert "line2" in parsed["instructions"]


# ─── generate_agent_yaml: settings ────────────────────────────────

def test_generate_settings_includes_all_standard_settings():
    """Covers line 44 + 57-59: standard_settings all emitted when no
    agent_settings override."""
    out = core.generate_agent_yaml("foo", {}, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert parsed["settings"]["timeout"] == 60
    assert parsed["settings"]["max_steps"] == 10


def test_generate_settings_override_standard_with_agent_value():
    """Covers line 46 True branch + 48 True branch: agent_settings[k]
    not None → overrides standard."""
    out = core.generate_agent_yaml("foo", {
        "settings": {"timeout": 120},
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert parsed["settings"]["timeout"] == 120
    # max_steps still from standard
    assert parsed["settings"]["max_steps"] == 10


def test_generate_settings_none_value_does_not_override():
    """Covers line 48 False branch: agent_settings[k] is None →
    keep standard value."""
    out = core.generate_agent_yaml("foo", {
        "settings": {"timeout": None},
    }, MIN_SCHEMA)
    parsed = yaml.safe_load(out)
    assert parsed["settings"]["timeout"] == 60


def test_generate_no_standard_settings_uses_only_agent_settings():
    """Covers line 44 dict(std) with empty std, then agent-only."""
    schema = {"standard_settings": {}, "template_tags": {}}
    out = core.generate_agent_yaml("foo", {
        "settings": {"custom": "value"},
    }, schema)
    parsed = yaml.safe_load(out)
    assert parsed["settings"]["custom"] == "value"


# ─── generate_agent_yaml: edge cases ──────────────────────────────

def test_generate_returns_yaml_trailing_newline():
    """Covers line 61: '\\n'.join + trailing '\\n'."""
    out = core.generate_agent_yaml("foo", {}, MIN_SCHEMA)
    assert out.endswith("\n")
    # Round-trips
    parsed = yaml.safe_load(out)
    assert parsed["title"] == "SUB-MAS-FOO"


def test_generate_no_standard_no_agent_settings_empty_settings_dict():
    """Covers line 58-59 with empty settings: just 'settings:' line."""
    schema = {"standard_settings": {}, "template_tags": {}}
    out = core.generate_agent_yaml("foo", {}, schema)
    parsed = yaml.safe_load(out)
    assert parsed["settings"] is None or parsed["settings"] == {} or parsed["settings"] == {}


# ─── validate_generated ────────────────────────────────────────────

def test_validate_returns_false_FEHLT_when_current_missing(tmp_path):
    """Covers line 66-67: os.path.exists False branch → ('FEHLT',)."""
    gen_yaml = "version: '1.0.0'\ntitle: X\n"
    ok, diffs = core.validate_generated(
        "x", gen_yaml, str(tmp_path / "missing.yaml"))
    assert ok is False
    assert diffs == ["FEHLT"]


def test_validate_parses_error_returns_false_PARSE_ERROR(tmp_path):
    """Covers line 70-74: yaml.safe_load raises (e.g. unparseable
    input) → (False, ['PARSE-ERROR: ...'])."""
    cur = tmp_path / "cur.yaml"
    cur.write_text("valid: yaml\n")
    ok, diffs = core.validate_generated(
        "x", "this: is: not: valid: yaml:",
        str(cur))
    assert ok is False
    assert len(diffs) == 1
    assert diffs[0].startswith("PARSE-ERROR:")


def test_validate_matches_returns_true(tmp_path):
    """Covers line 76-83 fully-equal path → (True, [])."""
    gen = ("version: '1.0.0'\n"
           "title: Match\n"
           "description: 'd'\n"
           "settings:\n"
           "  timeout: 60\n"
           "  max_steps: 10\n"
           "  goose_provider: ollama\n"
           "  goose_model: x\n")
    cur = tmp_path / "cur.yaml"
    cur.write_text(gen)
    ok, diffs = core.validate_generated("x", gen, str(cur))
    assert ok is True
    assert diffs == []


def test_validate_diff_title(tmp_path):
    """Covers line 77 True branch + 78: title mismatch."""
    gen = "version: '1.0.0'\ntitle: GEN\ndescription: 'd'\nsettings: {}\n"
    cur = tmp_path / "cur.yaml"
    cur.write_text("version: '1.0.0'\ntitle: CUR\ndescription: 'd'\nsettings: {}\n")
    ok, diffs = core.validate_generated("x", gen, str(cur))
    assert ok is False
    assert any("title:" in d for d in diffs)


def test_validate_diff_settings_timeout(tmp_path):
    """Covers line 82 + 83: settings.timeout mismatch."""
    gen = ("version: '1.0.0'\ntitle: T\ndescription: 'd'\n"
           "settings:\n  timeout: 60\n")
    cur = tmp_path / "cur.yaml"
    cur.write_text("version: '1.0.0'\ntitle: T\ndescription: 'd'\n"
                   "settings:\n  timeout: 99\n")
    ok, diffs = core.validate_generated("x", gen, str(cur))
    assert ok is False
    assert any("settings.timeout" in d for d in diffs)


def test_validate_settings_get_or_empty_when_missing_key(tmp_path):
    """Covers line 79 + 81 .get(k) default {} path: either side
    missing settings key entirely."""
    gen = "version: '1.0.0'\ntitle: T\ndescription: 'd'\nsettings: {}\n"
    cur = tmp_path / "cur.yaml"
    # cur has no settings key
    cur.write_text("version: '1.0.0'\ntitle: T\ndescription: 'd'\n")
    ok, diffs = core.validate_generated("x", gen, str(cur))
    # No settings on cur, no settings.{timeout,...} diffs added for keys
    # that exist in gen but not cur → diffs is empty (cs={} has no timeout)
    # But the gen.settings.timeout=None differs from cs.timeout=None → no diff
    assert ok is True
    assert diffs == []


def test_validate_diff_multiple_keys(tmp_path):
    """Covers line 76-78 + 82-83 combined: multiple diffs accumulated."""
    gen = ("version: '1.0.0'\ntitle: A\ndescription: 'x'\n"
           "settings:\n  timeout: 60\n  max_steps: 10\n")
    cur = tmp_path / "cur.yaml"
    cur.write_text("version: '1.0.0'\ntitle: B\ndescription: 'y'\n"
                   "settings:\n  timeout: 99\n  max_steps: 99\n")
    ok, diffs = core.validate_generated("x", gen, str(cur))
    assert ok is False
    # title, description, settings.timeout, settings.max_steps all diff
    assert len(diffs) >= 4
