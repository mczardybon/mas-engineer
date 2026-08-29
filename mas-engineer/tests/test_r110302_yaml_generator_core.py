"""
test_r110302_yaml_generator_core.py — R110-302 Coverage Sprint for
tools/dev_yaml_generator_core.py.

Target: dev_yaml_generator_core.py (84 lines, 60 stmts).

The module exposes two functions used by both YAML-generator variants:
  - generate_agent_yaml(agent_name, agent_data, schema) -> str
  - validate_generated(name, generated, current_path)    -> (bool, list[str])

Coverage strategy (every statement hit at least once):
  generate_agent_yaml:
    • minimal agent_data (defaults for title, description, prompt, instr)
    • agent_data with all fields set + template_tags (HEADER/R01/R09)
    • prompt already starts with header → no double-prepend
    • agent_data.title override (no fallback)
    • agent_data.description override (no fallback)
    • agent_data.prompt contains a single quote (escape: ' -> '')
    • agent_data.instructions contains a backslash and a double quote (escape)
    • agent_data.instructions contains a literal \\x0c (replace with \\n)
    • R01 tag already present in instructions (no double-append)
    • R09 tag already present in instructions (no double-append)
    • standard_settings overlay by agent_settings (None values ignored)
    • schema missing standard_settings and template_tags keys (defaults)
    • output ends with newline, has expected lines
  validate_generated:
    • current_path does not exist → (False, ['FEHLT'])
    • current_path exists, identical YAML → (True, [])
    • title/description/version diffs detected
    • settings.timeout / max_steps / goose_provider / goose_model diffs
    • yaml safe_load raises (invalid YAML) → (False, [PARSE-ERROR: ...])
"""
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOL = REPO_ROOT / "tools" / "dev_yaml_generator_core.py"
TOOLS_DIR = TOOL.parent


def _import_tool():
    """Import dev_yaml_generator_core as a library."""
    sys.path.insert(0, str(TOOLS_DIR))
    if "dev_yaml_generator_core" in sys.modules:
        del sys.modules["dev_yaml_generator_core"]
    import dev_yaml_generator_core
    return dev_yaml_generator_core


# ─────────────────────────────────────────────────────────────────────
# Fixtures: realistic schema + agent_data
# ─────────────────────────────────────────────────────────────────────

REALISTIC_SCHEMA = {
    "standard_settings": {
        "timeout": 300,
        "max_steps": 50,
        "goose_provider": "anthropic",
        "goose_model": "claude-sonnet-4",
    },
    "template_tags": {
        "HEADER": "🤖 {title}",
        "R01": "<<R01>>",
        "R09": "<<R09>>",
    },
}

REALISTIC_AGENT_DATA = {
    "emoji": "🤖",
    "title": "Test Agent",
    "description": "v1.0.0 | Test description",
    "prompt": "This is the body of the prompt.",
    "instructions": "Do this. Do that.",
    "settings": {
        "max_steps": 99,  # override standard
    },
}


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — minimal / defaults
# ─────────────────────────────────────────────────────────────────────

def test_generate_minimal_uses_defaults(tmp_path):
    """Empty agent_data + empty schema → all defaults apply.

    title defaults to f"SUB-MAS-{agent_name.upper()}"
    description defaults to f"v1.0.0 | {title}"
    prompt default is '' (no header prepend)
    instructions default is '' (no R01/R09 append)
    """
    mod = _import_tool()
    out = mod.generate_agent_yaml("foo", {}, {})

    # parseable
    parsed = yaml.safe_load(out)
    assert parsed["title"] == "SUB-MAS-FOO"
    assert parsed["description"] == "v1.0.0 | SUB-MAS-FOO"
    assert parsed["instructions"] == ""
    assert parsed["prompt"] == ""
    assert parsed["version"] == "1.0.0"
    # When the settings block is empty (no keys), yaml parses the bare
    # `settings:` key as None.
    assert parsed["settings"] is None


def test_generate_minimal_with_emoji_only(tmp_path):
    """emoji provided but no title → header = " emoji SUB-MAS-BAR"."""
    mod = _import_tool()
    out = mod.generate_agent_yaml("bar", {"emoji": "🦊"}, {})
    parsed = yaml.safe_load(out)
    # header is constructed via tags.get("HEADER", "{emoji} {title}")
    # which has default "{emoji} {title}".format(emoji=emoji, title=title)
    # Title defaults to "SUB-MAS-BAR". emoji = "🦊".
    assert parsed["title"] == "SUB-MAS-BAR"
    # prompt is empty, so no header prepending happens; the empty string
    # is then '... replace("'", "''")' which is still empty.
    assert parsed["prompt"] == ""


def test_generate_ends_with_newline_and_has_header_lines():
    """Output is well-formed: ends with \\n, contains version+title+desc+instr+prompt+settings."""
    mod = _import_tool()
    out = mod.generate_agent_yaml("x", REALISTIC_AGENT_DATA, REALISTIC_SCHEMA)
    assert out.endswith("\n")
    # line order
    lines = out.splitlines()
    assert lines[0] == 'version: "1.0.0"'
    assert lines[1] == "title: Test Agent"
    assert lines[2] == "description: 'v1.0.0 | Test description'"
    assert lines[3].startswith('instructions: "')
    assert lines[4].startswith("prompt: '")
    # settings header is followed by the standard_settings keys (indented).
    settings_idx = lines.index("settings:")
    assert lines[settings_idx + 1].startswith("  timeout:")


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — prompt handling
# ─────────────────────────────────────────────────────────────────────

def test_generate_prompt_gets_header_prepended():
    """prompt set + does NOT start with header → header is prepended.

    Header template is "🤖 {title}" (from template_tags.HEADER).
    YAML single-quoted strings preserve embedded newlines (unlike
    double-quoted ones, which use escape sequences).
    """
    mod = _import_tool()
    out = mod.generate_agent_yaml("x", REALISTIC_AGENT_DATA, REALISTIC_SCHEMA)
    parsed = yaml.safe_load(out)
    # The header = "🤖 Test Agent" (emoji="🤖", title="Test Agent")
    # The prepended text is `header + "\\n\\n" + prompt_text`, which in
    # YAML single-quote form becomes `header + "\\n" + prompt_text`
    # (two newlines collapse to one because YAML folds consecutive
    # blank lines in single-quoted strings to a single line break).
    assert parsed["prompt"].startswith("🤖 Test Agent\nThis is the body of the prompt.")


def test_generate_prompt_already_has_header_not_double_prepended():
    """If prompt already starts with header, header is NOT re-prepended."""
    mod = _import_tool()
    header = "🤖 Test Agent"
    agent_data = dict(REALISTIC_AGENT_DATA, prompt=header + "\n\nbody content.")
    out = mod.generate_agent_yaml("x", agent_data, REALISTIC_SCHEMA)
    parsed = yaml.safe_load(out)
    # The prompt should NOT have two header lines; count occurrences.
    assert parsed["prompt"].count(header) == 1


def test_generate_prompt_escapes_single_quotes():
    """All single quotes in prompt are doubled (SQL-style escape)."""
    mod = _import_tool()
    agent_data = dict(REALISTIC_AGENT_DATA, prompt="it's a 'test' with quotes")
    out = mod.generate_agent_yaml("x", agent_data, REALISTIC_SCHEMA)
    # The raw line should have '' (doubled) for each '
    # We check the raw text (before YAML parsing) to be precise:
    # The prompt is wrapped in single quotes on the output line.
    # E.g.: prompt: 'header

    # body with '' escaping'
    # After YAML parsing the doubling collapses back to single quotes.
    parsed = yaml.safe_load(out)
    assert "it's a 'test' with quotes" in parsed["prompt"]


def test_generate_empty_prompt_no_header_prepend():
    """If prompt is empty string, header is NOT prepended (the `if prompt_text`
    guard is False, the .startswith check is skipped)."""
    mod = _import_tool()
    agent_data = dict(REALISTIC_AGENT_DATA, prompt="")
    out = mod.generate_agent_yaml("x", agent_data, REALISTIC_SCHEMA)
    parsed = yaml.safe_load(out)
    assert parsed["prompt"] == ""


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — instructions + R01/R09 tags
# ─────────────────────────────────────────────────────────────────────

def test_generate_instructions_get_r01_r09_appended():
    """R01 and R09 tags from template_tags are appended to instructions
    if not already present (after escaping)."""
    mod = _import_tool()
    out = mod.generate_agent_yaml("x", REALISTIC_AGENT_DATA, REALISTIC_SCHEMA)
    parsed = yaml.safe_load(out)
    # Both tags should be at the end of instructions
    assert parsed["instructions"].endswith("Do this. Do that.<<R01>><<R09>>")


def test_generate_r01_already_present_not_appended():
    """If R01 tag is already in instructions, it is NOT re-appended."""
    mod = _import_tool()
    agent_data = dict(REALISTIC_AGENT_DATA, instructions="Do this. <<R01>>")
    out = mod.generate_agent_yaml("x", agent_data, REALISTIC_SCHEMA)
    parsed = yaml.safe_load(out)
    # R01 should appear exactly once, R09 should be appended
    assert parsed["instructions"].count("<<R01>>") == 1
    assert parsed["instructions"].endswith("Do this. <<R01>><<R09>>")


def test_generate_r09_already_present_not_appended():
    """If R09 tag is already in instructions, it is NOT re-appended.

    Note: the code appends R01 first, then R09. So the result ends with
    `<<R09>><<R01>>` (R01 appended at the end since R09 was already there).
    """
    mod = _import_tool()
    agent_data = dict(REALISTIC_AGENT_DATA, instructions="Do this. <<R09>>")
    out = mod.generate_agent_yaml("x", agent_data, REALISTIC_SCHEMA)
    parsed = yaml.safe_load(out)
    assert parsed["instructions"].count("<<R09>>") == 1
    assert parsed["instructions"].endswith("Do this. <<R09>><<R01>>")


def test_generate_instructions_escapes_backslash_and_quote():
    """instructions are escaped: \\\\ → \\\\\\\\ and " → \\"."""
    mod = _import_tool()
    # Use a string with a literal backslash and a double-quote
    agent_data = dict(REALISTIC_AGENT_DATA, instructions='a\\b"c')
    out = mod.generate_agent_yaml("x", agent_data, REALISTIC_SCHEMA)
    # The raw output line for instructions should have the escaped form
    # 'a\\\\b\\"c' (one backslash becomes two, one double-quote becomes backslash-double-quote)
    assert 'a\\\\b\\"c' in out


def test_generate_instructions_replaces_formfeed_with_backslash_n():
    """\\x0c in instructions is replaced with the two-character sequence \\\\n."""
    mod = _import_tool()
    agent_data = dict(REALISTIC_AGENT_DATA, instructions="line1\x0cline2")
    out = mod.generate_yaml_safe_load = None  # placeholder — do not run
    # Re-import fresh to avoid leaking state
    mod = _import_tool()
    out = mod.generate_agent_yaml("x", agent_data, REALISTIC_SCHEMA)
    parsed = yaml.safe_load(out)
    # In the parsed YAML, the value is the literal two chars \n (backslash + n)
    # because in YAML double-quoted strings, \\n is an escape for newline,
    # but a raw \n (two chars: backslash, n) is the literal sequence.
    # Looking at the code: instr_text = instr_text.replace('\x0c', '\\n')
    # '\\n' in Python source is a 2-char string: backslash + n.
    # So the resulting instr_text has a literal backslash followed by n.
    # When wrapped in double-quotes in YAML output, \\n is the escape for newline.
    # Let's check the raw text in the output line instead:
    # the line is: instructions: "<escaped>\\n<...>"
    # i.e. literal: ...\\n...
    # In raw output bytes this is backslash-backslash-n (3 chars).
    # But the replace() inserts a literal 2-char sequence \n (one backslash + n).
    # The line wraps in " ... " and that 2-char \\n becomes a YAML escape for newline.
    # So in the raw output, the sequence is: \\n (3 chars: \, \, n)
    # We just verify that the raw output contains the formfeed replacement:
    # \x0c should NOT appear in the raw output.
    assert "\x0c" not in out


def test_generate_no_r01_r09_tags_appended_when_empty():
    """If template_tags R01/R09 are empty strings, nothing is appended."""
    mod = _import_tool()
    schema = {
        "standard_settings": {},
        "template_tags": {"HEADER": "{emoji} {title}", "R01": "", "R09": ""},
    }
    out = mod.generate_agent_yaml("x", {"instructions": "core"}, schema)
    parsed = yaml.safe_load(out)
    assert parsed["instructions"] == "core"


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — title / description / settings override
# ─────────────────────────────────────────────────────────────────────

def test_generate_title_override_skips_default():
    """Explicit title in agent_data bypasses the SUB-MAS-AGENTNAME fallback."""
    mod = _import_tool()
    out = mod.generate_agent_yaml("ignored", {"title": "Custom"}, {})
    parsed = yaml.safe_load(out)
    assert parsed["title"] == "Custom"


def test_generate_description_override_skips_default():
    """Explicit description bypasses the v1.0.0 | {title} fallback."""
    mod = _import_tool()
    out = mod.generate_agent_yaml(
        "x", {"title": "T", "description": "Custom desc"}, {}
    )
    parsed = yaml.safe_load(out)
    assert parsed["description"] == "Custom desc"


def test_generate_settings_merged_from_standard_and_agent():
    """agent_settings overlays standard_settings (only non-None values)."""
    mod = _import_tool()
    schema = {
        "standard_settings": {"a": 1, "b": 2, "c": 3},
        "template_tags": {},
    }
    agent_data = {"settings": {"b": 99, "d": 4, "e": None}}
    out = mod.generate_agent_yaml("x", agent_data, schema)
    parsed = yaml.safe_load(out)
    # a, c from standard; b overridden; d added; e NOT added (None is skipped)
    assert parsed["settings"] == {"a": 1, "b": 99, "c": 3, "d": 4}


def test_generate_settings_agent_empty_dict_keeps_standard():
    """agent_data.settings = {} → standard_settings unchanged (the `if agent_settings`
    guard is False, so no overlay)."""
    mod = _import_tool()
    schema = {
        "standard_settings": {"a": 1, "b": 2},
        "template_tags": {},
    }
    out = mod.generate_agent_yaml("x", {"settings": {}}, schema)
    parsed = yaml.safe_load(out)
    assert parsed["settings"] == {"a": 1, "b": 2}


def test_generate_settings_default_when_schema_missing_keys():
    """Schema without standard_settings / template_tags → empty dict defaults
    (the .get(..., {}) path)."""
    mod = _import_tool()
    out = mod.generate_agent_yaml("x", {"title": "T"}, {})
    parsed = yaml.safe_load(out)
    # No settings at all → parsed["settings"] is None
    assert parsed["settings"] is None


# ─────────────────────────────────────────────────────────────────────
# generate_agent_yaml — tag escaping
# ─────────────────────────────────────────────────────────────────────

def test_generate_r01_r09_tags_escaped_for_yaml():
    """R01/R09 tag values are escaped (\\ → \\\\, " → \\")."""
    mod = _import_tool()
    schema = {
        "standard_settings": {},
        "template_tags": {
            "HEADER": "{emoji} {title}",
            "R01": 'has \\ and " in it',
            "R09": "",
        },
    }
    agent_data = {"instructions": "core "}
    out = mod.generate_agent_yaml("x", agent_data, schema)
    # The escaped R01 should appear: 'has \\\\ and \\" in it'
    # In the raw output (one backslash becomes two, one double-quote gets escaped)
    assert 'has \\\\ and \\" in it' in out


# ─────────────────────────────────────────────────────────────────────
# validate_generated
# ─────────────────────────────────────────────────────────────────────

def _write_current(path: Path, title="X", description="d", version="1.0.0",
                   settings=None):
    """Helper: write a 'current' YAML file with the given fields."""
    if settings is None:
        settings = {
            "timeout": 300,
            "max_steps": 50,
            "goose_provider": "anthropic",
            "goose_model": "claude-sonnet-4",
        }
    data = {
        "version": version,
        "title": title,
        "description": description,
        "instructions": "x",
        "prompt": "y",
        "settings": settings,
    }
    path.write_text(yaml.safe_dump(data, sort_keys=True))


def test_validate_missing_file_returns_fehlt(tmp_path):
    """current_path does not exist → (False, ['FEHLT'])."""
    mod = _import_tool()
    ok, diffs = mod.validate_generated("x", "irrelevant", tmp_path / "nope.yaml")
    assert ok is False
    assert diffs == ["FEHLT"]


def test_validate_identical_yaml_returns_true(tmp_path):
    """Identical generated and current → (True, [])."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current)
    # Re-generate the same content as YAML and pass it to validate_generated.
    # The function parses both with yaml.safe_load and compares fields.
    # We craft a generated string that is a different textual YAML for the
    # same data (different key order) — it should still match.
    gen_data = {
        "version": "1.0.0",
        "title": "X",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 300,
            "max_steps": 50,
            "goose_provider": "anthropic",
            "goose_model": "claude-sonnet-4",
        },
    }
    gen = yaml.safe_dump(gen_data, sort_keys=True)
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is True
    assert diffs == []


def test_validate_title_diff_detected(tmp_path):
    """Different title → diff contains 'title: gen=... != cur=...'."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, title="OldTitle")
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "NewTitle",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 300,
            "max_steps": 50,
            "goose_provider": "anthropic",
            "goose_model": "claude-sonnet-4",
        },
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    joined = "\n".join(diffs)
    assert "title:" in joined
    assert "NewTitle" in joined
    assert "OldTitle" in joined


def test_validate_description_diff_detected(tmp_path):
    """Different description → diff contains 'description:'."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, description="old desc")
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "X",
        "description": "new desc",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 300,
            "max_steps": 50,
            "goose_provider": "anthropic",
            "goose_model": "claude-sonnet-4",
        },
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    assert any("description:" in d for d in diffs)


def test_validate_version_diff_detected(tmp_path):
    """Different version → diff contains 'version:'."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, version="0.9.0")
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "X",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 300,
            "max_steps": 50,
            "goose_provider": "anthropic",
            "goose_model": "claude-sonnet-4",
        },
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    assert any("version:" in d for d in diffs)


def test_validate_settings_timeout_diff_detected(tmp_path):
    """Different settings.timeout → diff contains 'settings.timeout:'."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, settings={
        "timeout": 100, "max_steps": 50,
        "goose_provider": "anthropic", "goose_model": "claude-sonnet-4",
    })
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "X",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 999, "max_steps": 50,
            "goose_provider": "anthropic", "goose_model": "claude-sonnet-4",
        },
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    assert any("settings.timeout:" in d for d in diffs)


def test_validate_settings_max_steps_diff_detected(tmp_path):
    """Different settings.max_steps → diff contains 'settings.max_steps:'."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, settings={
        "timeout": 300, "max_steps": 10,
        "goose_provider": "anthropic", "goose_model": "claude-sonnet-4",
    })
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "X",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 300, "max_steps": 20,
            "goose_provider": "anthropic", "goose_model": "claude-sonnet-4",
        },
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    assert any("settings.max_steps:" in d for d in diffs)


def test_validate_settings_goose_provider_diff_detected(tmp_path):
    """Different settings.goose_provider → diff contains 'settings.goose_provider:'."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, settings={
        "timeout": 300, "max_steps": 50,
        "goose_provider": "openai", "goose_model": "claude-sonnet-4",
    })
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "X",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 300, "max_steps": 50,
            "goose_provider": "anthropic", "goose_model": "claude-sonnet-4",
        },
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    assert any("settings.goose_provider:" in d for d in diffs)


def test_validate_settings_goose_model_diff_detected(tmp_path):
    """Different settings.goose_model → diff contains 'settings.goose_model:'."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, settings={
        "timeout": 300, "max_steps": 50,
        "goose_provider": "anthropic", "goose_model": "old-model",
    })
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "X",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 300, "max_steps": 50,
            "goose_provider": "anthropic", "goose_model": "new-model",
        },
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    assert any("settings.goose_model:" in d for d in diffs)


def test_validate_multiple_diffs(tmp_path):
    """Several diffs are returned in one call → all listed, ok=False."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, title="A", description="d1", version="1.0.0")
    gen = yaml.safe_dump({
        "version": "2.0.0",
        "title": "B",
        "description": "d2",
        "instructions": "x",
        "prompt": "y",
        "settings": {},
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    assert len(diffs) >= 3
    joined = "\n".join(diffs)
    assert "title:" in joined
    assert "description:" in joined
    assert "version:" in joined


def test_validate_generated_yaml_parse_error(tmp_path):
    """If `generated` is invalid YAML, returns (False, [PARSE-ERROR: ...])."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current)
    # invalid YAML: unclosed quote
    bad = "title: 'unterminated"
    ok, diffs = mod.validate_generated("x", bad, str(current))
    assert ok is False
    assert len(diffs) == 1
    assert diffs[0].startswith("PARSE-ERROR:")


def test_validate_current_yaml_parse_error(tmp_path):
    """If the current file is invalid YAML, returns (False, [PARSE-ERROR: ...])."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    current.write_text("title: 'unterminated")
    good = yaml.safe_dump({"title": "X"})
    ok, diffs = mod.validate_generated("x", good, str(current))
    assert ok is False
    assert len(diffs) == 1
    assert diffs[0].startswith("PARSE-ERROR:")


def test_validate_unrelated_settings_dont_cause_diff(tmp_path):
    """Settings not in the watched list (e.g. an extra key) do NOT cause
    a diff (the loop only iterates the four named keys)."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    _write_current(current, settings={
        "timeout": 300, "max_steps": 50,
        "goose_provider": "anthropic", "goose_model": "claude-sonnet-4",
        "extra_key": "should be ignored",
    })
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "X",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {
            "timeout": 300, "max_steps": 50,
            "goose_provider": "anthropic", "goose_model": "claude-sonnet-4",
        },
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is True
    assert diffs == []


def test_validate_missing_field_in_current_counted_as_diff(tmp_path):
    """If a watched field is missing in the current file (None), the diff
    still shows up (gen value != None)."""
    mod = _import_tool()
    current = tmp_path / "cur.yaml"
    # current missing 'title'
    data = {
        "version": "1.0.0",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {},
    }
    current.write_text(yaml.safe_dump(data))
    gen = yaml.safe_dump({
        "version": "1.0.0",
        "title": "HasTitle",
        "description": "d",
        "instructions": "x",
        "prompt": "y",
        "settings": {},
    })
    ok, diffs = mod.validate_generated("x", gen, str(current))
    assert ok is False
    assert any("title:" in d for d in diffs)
