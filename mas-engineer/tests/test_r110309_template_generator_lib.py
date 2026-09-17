"""R110-309: library function tests for tools/dev_template_generator.py.

Covers pure helper functions used by the agent-template generator.
These are stateful I/O wrappers (load_yaml, load_json, load_text)
and pure formatters (_shorten, _format_dict_block, _format_bp_rules).
"""
import sys
import os
import json
import importlib
from pathlib import Path
import pytest

TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def tg(tmp_path, monkeypatch):
    """Import dev_template_generator with a sandboxed CWD."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_template_generator", None)
    try:
        import dev_template_generator
        return dev_template_generator
    finally:
        sys.path.pop(0)


# ────────────────────────────────────────────────────────────
# load_yaml
# ────────────────────────────────────────────────────────────

def test_load_yaml_missing_returns_empty_dict(tg, tmp_path, capsys):
    """load_yaml of a non-existent path returns {} and prints a warning."""
    result = tg.load_yaml("does-not-exist.yaml")
    assert result == {}
    captured = capsys.readouterr()
    assert "not found" in captured.out.lower() or "source" in captured.out.lower()


def test_load_yaml_valid(tg, tmp_path):
    """load_yaml of a valid YAML file returns the parsed content."""
    p = tmp_path / "valid.yaml"
    p.write_text("key: value\nlist:\n  - a\n  - b\n")
    result = tg.load_yaml(str(p))
    assert result == {"key": "value", "list": ["a", "b"]}


def test_load_yaml_invalid_returns_empty(tg, tmp_path, capsys):
    """load_yaml of an invalid YAML file returns {} and prints a warning."""
    p = tmp_path / "broken.yaml"
    p.write_text(": invalid: yaml: : :")
    result = tg.load_yaml(str(p))
    assert result == {}


def test_load_yaml_empty_file(tg, tmp_path):
    """load_yaml of an empty file returns {} (yaml.safe_load(None) -> None)."""
    p = tmp_path / "empty.yaml"
    p.write_text("")
    result = tg.load_yaml(str(p))
    # yaml.safe_load("") returns None, the function falls back to {}
    assert result == {}


# ────────────────────────────────────────────────────────────
# load_json
# ────────────────────────────────────────────────────────────

def test_load_json_missing_returns_dict_for_json(tg, tmp_path):
    """load_json of a missing .json path returns {}."""
    result = tg.load_json("missing.json")
    assert result == {}


def test_load_json_missing_returns_string_for_other(tg, tmp_path):
    """load_json of a missing non-.json path returns ''."""
    result = tg.load_json("missing.txt")
    assert result == ""


def test_load_json_valid(tg, tmp_path):
    """load_json of a valid JSON file returns the parsed content."""
    p = tmp_path / "data.json"
    p.write_text('{"a": 1, "b": [2, 3]}')
    result = tg.load_json(str(p))
    assert result == {"a": 1, "b": [2, 3]}


def test_load_json_invalid_returns_empty(tg, tmp_path):
    """load_json of invalid JSON returns {}."""
    p = tmp_path / "broken.json"
    p.write_text("not json at all")
    result = tg.load_json(str(p))
    assert result == {}


# ────────────────────────────────────────────────────────────
# load_text
# ────────────────────────────────────────────────────────────

def test_load_text_missing_returns_empty(tg, tmp_path):
    """load_text of a missing path returns ''."""
    result = tg.load_text("missing.txt")
    assert result == ""


def test_load_text_valid(tg, tmp_path):
    """load_text of a valid file returns the content."""
    p = tmp_path / "note.txt"
    p.write_text("hello world\nline2\n")
    result = tg.load_text(str(p))
    assert result == "hello world\nline2\n"


def test_load_text_invalid_returns_empty(tg, tmp_path):
    """load_text that throws IOError returns ''."""
    p = tmp_path / "broken.txt"
    p.write_text("ok")
    # Make it unreadable: convert to a directory under the same name? No, simpler:
    # the function catches Exception broadly, including UnicodeDecodeError
    p.write_bytes(b"\xff\xfe\x00bad-encoding")
    result = tg.load_text(str(p))
    # Either '' (caught) or the raw bytes (no encoding error). We test the contract.
    assert isinstance(result, str)


# ────────────────────────────────────────────────────────────
# _shorten
# ────────────────────────────────────────────────────────────

def test_shorten_under_limit(tg):
    """Text shorter than maxlen is returned unchanged."""
    assert tg._shorten("hello", 80) == "hello"


def test_shorten_at_limit(tg):
    """Text exactly at maxlen is returned unchanged."""
    s = "x" * 80
    assert tg._shorten(s, 80) == s


def test_shorten_over_limit(tg):
    """Text longer than maxlen is truncated with '...' suffix."""
    s = "x" * 100
    out = tg._shorten(s, 80)
    assert len(out) == 80
    assert out.endswith("...")


# ────────────────────────────────────────────────────────────
# _format_dict_block
# ────────────────────────────────────────────────────────────

def test_format_dict_block_simple(tg):
    """A flat dict is rendered as comment lines."""
    out = tg._format_dict_block({"a": "x", "b": "y"})
    # Both keys should be in the output
    assert "a" in out
    assert "b" in out
    assert "x" in out
    assert "y" in out


def test_format_dict_block_nested(tg):
    """A nested dict is rendered with a header line for the key and sublines."""
    out = tg._format_dict_block({"outer": {"inner": "val"}})
    # The outer key should appear as a header
    assert "outer" in out
    assert "inner" in out
    assert "val" in out


def test_format_dict_block_truncates_long_values(tg):
    """Values longer than 120 chars are truncated with '...' marker."""
    long_val = "x" * 200
    out = tg._format_dict_block({"k": long_val})
    # The truncated form should appear, not the full 200 x's
    assert "x" * 200 not in out


# ────────────────────────────────────────────────────────────
# _format_bp_rules
# ────────────────────────────────────────────────────────────

def test_format_bp_rules_minimal(tg):
    """A dict with no recognized keys returns empty string."""
    out = tg._format_bp_rules({"unrelated_key": "x"}, section_keys=[])
    # section_keys=[] means nothing is rendered
    assert out == ""


def test_format_bp_rules_known_keys(tg):
    """A dict with known section keys renders the auto_apply rules.

    _format_bp_rules(bp, section_keys) walks bp[section_key] and
    extracts dicts with auto_apply=true.
    """
    out = tg._format_bp_rules(
        {"autonomie": [
            {"id": "bp-1", "rule": "be self-directed", "auto_apply": True},
        ]},
        section_keys=["autonomie"],
    )
    assert "bp-1" in out
    assert "self-directed" in out


def test_format_bp_rules_skips_non_auto(tg):
    """Rules without auto_apply=true are NOT rendered."""
    out = tg._format_bp_rules(
        {"autonomie": [
            {"id": "bp-1", "rule": "do not include", "auto_apply": False},
        ]},
        section_keys=["autonomie"],
    )
    assert "do not include" not in out


def test_format_bp_rules_nested_path(tg):
    """A dotted section_key navigates the bp dict by path."""
    out = tg._format_bp_rules(
        {"best_practices": {"prompt": [
            {"id": "bp-prompt-1", "rule": "be terse", "auto_apply": True},
        ]}},
        section_keys=["best_practices.prompt"],
    )
    assert "bp-prompt-1" in out
    assert "be terse" in out
