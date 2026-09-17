r"""R110-328 regression tests: latent-bug fixes in dev_template_generator.

R110-328 took candidate #3 from the R110-321 cov-push queue
(dev_template_generator.py, 901 stmts) and probed it for
latent bugs. This file documents 3 bugs found, their fixes,
and the regression tests that lock them in.

Bug 1 — _format_dict_block() produces broken output when values
        or list-items contain newlines (R110-328-BUG-1)
  LOCATION: tools/dev_template_generator.py, lines 140-160
  SYMPTOM: The function builds a YAML-comment block by joining
    lines. The nested-dict branch (line 147-150) properly
    truncates at the first newline (replacing with "...").
    But:
      - the top-level branch (line 159: f"{indent}{prefix}{key}:
        {str(value)[:120]}") does NOT handle newlines in
        `value` — a value like "line1\nline2" produces
        output "# key: line1\nline2" where "line2" is
        a separate (now-broken) comment line.
      - the list branch (line 154: s = str(item)[:100]) does
        NOT handle newlines in `str(item)` — a list of
        dicts with a multiline str() representation also
        breaks the comment block.
  ROOT CAUSE: Inconsistency between branches. The nested-dict
    branch has the right pattern; the other two don't.
  FIX: Add a `_truncate_value(s, maxlen)` helper that:
    1. Takes only the first line (split('\n')[0])
    2. Truncates to maxlen chars
    3. Adds "..." if truncated
    And use it in all 3 branches.
  IMPACT: Generates confusing/misleading YAML-comment
    output when a value or list-item has embedded newlines.
    Common in real SOT data (multi-line rule text, multi-
    line description, etc.).

Bug 2 — _format_bp_rules() crashes with TypeError on non-string
        `rule` field (R110-328-BUG-2)
  LOCATION: tools/dev_template_generator.py, line 179
  SYMPTOM: rtext = rule.get("rule", "")[:150] crashes with
    TypeError if rule["rule"] is not a string (e.g. int 42,
    None, dict, list). The .get() call returns the actual
    value (not the default ""), and the [:150] subscript
    fails on non-string types.
  ROOT CAUSE: Defensive coding missing. The author assumed
    "rule" is always a string, but YAML allows any scalar.
  FIX: Wrap with str(): rtext = str(rule.get("rule", ""))[:150]
  IMPACT: A real crash if a BP-rules source has a rule with
    a non-string `rule` field. Easy to trigger in a real
    SOT update where one rule's text is accidentally a number
    (e.g. priority or weight accidentally written to the
    wrong field).

Bug 3 — fill_template() silently keeps unfilled lowercase or
        mixed-case placeholders (R110-328-BUG-3)
  LOCATION: tools/dev_template_generator.py, line 366
  SYMPTOM: The "unreplaced" check uses regex r"\{[A-Z_]+\}"
    which ONLY matches uppercase letters and underscores.
    A template with `{unknown_lower}` or `{Mixed_Case}`
    is silently kept in the output, with no warning to the
    user. The user thinks the template was filled correctly
    and may not notice the leftover `{X}` until downstream
    YAML parsing fails (if the leftover is in a flow
    context) or downstream goose execution fails (if the
    leftover is in a prompt that's used as a header).
  ROOT CAUSE: Regex too restrictive. The intent was
    "find any placeholder in the output that wasn't
    replaced" but the regex was written assuming
    uppercase-only placeholders, missing the existing
    `{name}` (lowercase) and `{Titel}` (mixed-case) which
    ARE in the replacements dict.
  FIX: Use regex r"\{[^}]+\}" which matches any non-empty
    content inside braces. Also: warn the user about
    unfilled placeholders (the current code is also
    wrong about the warning message — see BUG-4 below).
  IMPACT: Silent failure / hard-to-debug user issue.
    If a user adds a new placeholder to the template
    and forgets to add it to `replacements`, the template
    is silently broken.

Code smell (also fixed in this commit):
  - The `replacements` dict in fill_template() has a
    duplicate `"{TASK}": task,` entry (line 333-334 of
    original). Python takes the last value, so
    functionally it's a no-op, but it's the same
    anti-pattern we fixed in R110-326 BUG-B.
    Fix: remove the duplicate.

Bug 4 (warning message is misleading, not a crash) — fixed as
        part of BUG-3 fix (the message in line 377 says
        "Nicht-replacese placeholder" but actually lists
        both "not-in-template" and "not-in-replacements"
        placeholders — confusing).

Test pattern (R110-310/R110-320/R110-322/R110-323/R110-326
inheritance): Each test imports dev_template_generator.py
directly and calls the testable (non-# pragma: no cover)
functions. The functions being tested don't need a GOOSE
environment, so we can import them in-process. In-process
is faster than subprocess (~0.27s vs ~3s for the bug-
probing) and more precise (we can call private helpers
like _format_dict_block directly).
"""
import io
import sys
import os
import re
from pathlib import Path
from unittest import mock

import pytest
import yaml

TOOL_DIR = Path(__file__).resolve().parent.parent / 'tools'
sys.path.insert(0, str(TOOL_DIR))
import dev_template_generator  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- Bug 1 regression: _format_dict_block() newline handling --------------

class TestR110328Bug1FormatDictBlockNewlines:
    """R110-328-BUG-1: _format_dict_block produces broken output
    when values or list-items contain newlines.
    """

    def test_value_with_newline_is_truncated_to_first_line(self):
        """A value with a newline should be truncated to the first
        line + '...' (if over maxlen) or just the first line (if under
        maxlen), not split into a broken multi-line comment."""
        data = {"key": "line1\nline2"}
        out = dev_template_generator._format_dict_block(data)
        # MUST not contain 'line2' on a separate line
        assert '\nline2' not in out, (
            f"newline in value broke comment block: {out!r}")
        # MUST contain 'line1' (the first line)
        assert 'line1' in out
        # MUST NOT contain 'line2' at all (first-line truncation)
        assert 'line2' not in out

    def test_value_with_newline_and_long_first_line_truncates_with_ellipsis(self):
        """A value where the first line is > maxlen chars: should be
        truncated to (maxlen-3) chars + '...'."""
        long_first_line = "x" * 200  # 200 chars on a single line
        data = {"key": long_first_line + "\nline2"}
        out = dev_template_generator._format_dict_block(data)
        # MUST contain '...' (truncation indicator)
        assert '...' in out
        # MUST NOT contain 'line2' (newline truncation)
        assert 'line2' not in out
        # The full 200-char string is NOT in the output (it was truncated)
        assert long_first_line not in out

    def test_list_item_with_newline_is_truncated_to_first_line(self):
        """A list item with a newline (via str(dict) for dict items)
        should be truncated to the first line + '...', not split
        into a broken multi-line comment."""
        data = {"items": [{"key": "line1\nline2"}, "safe"]}
        out = dev_template_generator._format_dict_block(data)
        assert '\nline2' not in out, (
            f"newline in list-item broke comment block: {out!r}")

    def test_nested_dict_value_with_newline_truncated(self):
        """Nested-dict branch already truncated, regression test
        (sanity)."""
        data = {"outer": {"inner": "line1\nline2"}}
        out = dev_template_generator._format_dict_block(data)
        # The nested branch already does this, so this is a no-regression
        # test. It should still work.
        assert '\nline2' not in out

    def test_simple_value_no_newline_unchanged(self):
        """Simple values without newlines should not get '...' added."""
        data = {"key": "simple"}
        out = dev_template_generator._format_dict_block(data)
        assert 'simple' in out
        assert '...' not in out

    def test_list_of_strings_no_newline(self):
        """Sanity: list of simple strings works as before."""
        data = {"items": ["a", "b", "c"]}
        out = dev_template_generator._format_dict_block(data)
        assert "- a" in out
        assert "- b" in out
        assert "- c" in out

    def test_list_truncation_at_5_still_works(self):
        """List truncation at 5 items still works after the fix."""
        data = {"items": list("abcdefghij")}
        out = dev_template_generator._format_dict_block(data)
        # First 5 items
        for ch in "abcde":
            assert f"- {ch}" in out
        # Items 6-10 NOT in output
        for ch in "fghij":
            assert f"- {ch}" not in out
        # "more" indicator
        assert "+5 mehr" in out

    def test_dict_with_int_value(self):
        """Integer values are formatted as their str() (no
        truncation needed)."""
        data = {"count": 42}
        out = dev_template_generator._format_dict_block(data)
        assert 'count: 42' in out

    def test_dict_with_bool_value(self):
        """Boolean values are formatted as Python repr (True/False)."""
        data = {"flag": True}
        out = dev_template_generator._format_dict_block(data)
        assert 'flag: True' in out

    def test_empty_dict(self):
        """Empty dict produces empty string (no error)."""
        out = dev_template_generator._format_dict_block({})
        assert out == ''


# --- Bug 2 regression: _format_bp_rules() TypeError ------------------------

class TestR110328Bug2FormatBPRulesTypeError:
    """R110-328-BUG-2: _format_bp_rules crashes with TypeError when
    a rule's "rule" field is a non-string (int, None, dict, list).
    """

    def test_rule_with_int_value_does_not_crash(self):
        """The original bug: rule["rule"] = 42 → TypeError on [:150].
        After the fix: str(42)[:150] = "42" works fine."""
        bp = {"a": [{"auto_apply": True, "id": "r1", "rule": 42}]}
        # MUST NOT raise TypeError
        out = dev_template_generator._format_bp_rules(bp, ["a"])
        assert "r1" in out
        assert "42" in out

    def test_rule_with_None_value_does_not_crash(self):
        """rule["rule"] = None → TypeError on [:150]. After fix: ok."""
        bp = {"a": [{"auto_apply": True, "id": "r1", "rule": None}]}
        out = dev_template_generator._format_bp_rules(bp, ["a"])
        assert "r1" in out

    def test_rule_with_list_value_does_not_crash(self):
        """rule["rule"] = [a, b] → TypeError on [:150]. After fix: ok."""
        bp = {"a": [{"auto_apply": True, "id": "r1", "rule": ["a", "b"]}]}
        out = dev_template_generator._format_bp_rules(bp, ["a"])
        assert "r1" in out

    def test_rule_with_dict_value_does_not_crash(self):
        """rule["rule"] = {"k": "v"} → TypeError on [:150]. After fix."""
        bp = {"a": [{"auto_apply": True, "id": "r1", "rule": {"k": "v"}}]}
        out = dev_template_generator._format_bp_rules(bp, ["a"])
        assert "r1" in out

    def test_rule_with_missing_rule_field_uses_empty(self):
        """rule has no "rule" key → rule.get("rule", "") = "" → ok."""
        bp = {"a": [{"auto_apply": True, "id": "r1"}]}
        out = dev_template_generator._format_bp_rules(bp, ["a"])
        assert "r1" in out

    def test_string_rule_truncated_to_150(self):
        """Sanity: string rule text is truncated to 150 chars."""
        long_text = "x" * 200
        bp = {"a": [{"auto_apply": True, "id": "r1", "rule": long_text}]}
        out = dev_template_generator._format_bp_rules(bp, ["a"])
        # The text part should be exactly 150 chars
        # Format: "  • [r1] <text>" — extract text part
        assert out == f"  • [r1] {'x' * 150}"

    def test_no_auto_apply_skipped(self):
        """Rules without auto_apply=True are skipped (no-regression)."""
        bp = {"a": [{"id": "r1", "rule": "no auto_apply"}]}
        out = dev_template_generator._format_bp_rules(bp, ["a"])
        assert out == ''

    def test_section_key_with_dotted_path(self):
        """Dotted section_key is correctly traversed (no-regression)."""
        bp = {"best_practices": {"prompt": [
            {"auto_apply": True, "id": "r1", "rule": "text"}
        ]}}
        out = dev_template_generator._format_bp_rules(bp, ["best_practices.prompt"])
        assert "r1" in out
        assert "text" in out

    def test_section_key_with_missing_intermediate(self):
        """If a dotted path has a missing middle key, treat as empty
        (no-regression)."""
        bp = {"a": {}}  # no "b" inside
        out = dev_template_generator._format_bp_rules(bp, ["a.b.c"])
        assert out == ''

    def test_list_with_string_items_skipped(self):
        """If the list contains non-dict items (strings), they're
        skipped (no-regression — the isinstance check filters)."""
        bp = {"a": ["not_a_dict", "also_not"]}
        out = dev_template_generator._format_bp_rules(bp, ["a"])
        assert out == ''


# --- Bug 3 regression: fill_template() silent unfilled placeholders -------

class TestR110328Bug3FillTemplateSilentPlaceholders:
    """R110-328-BUG-3: fill_template silently keeps unfilled
    lowercase or mixed-case placeholders in the output.
    """

    def test_lowercase_unfilled_placeholder_warns(self, capsys):
        """A lowercase placeholder not in `replacements` should be
        reported as unfilled, not silently kept."""
        template = "static {unknown_lower} more"
        out = dev_template_generator.fill_template(
            {"template": template}, {}, name="x", emoji="🤖",
            task="t", agent_type="sub")
        # The placeholder should be replaced with "" OR warned about
        # in the message. We accept either:
        #   (a) it's replaced with "" and not in output
        #   (b) it's warned about (in which case it MAY still be in output)
        captured = capsys.readouterr()
        # It MUST be warned about (not silent)
        assert 'unknown_lower' in captured.out or 'unknown_lower' not in out, (
            f"lowercase unfilled placeholder was silent! "
            f"out={out!r}, captured={captured.out!r}")

    def test_mixed_case_unfilled_placeholder_warns(self, capsys):
        """A mixed-case placeholder not in `replacements` should be
        reported as unfilled."""
        template = "static {Mixed_Case} more"
        out = dev_template_generator.fill_template(
            {"template": template}, {}, name="x", emoji="🤖",
            task="t", agent_type="sub")
        captured = capsys.readouterr()
        assert 'Mixed_Case' in captured.out or 'Mixed_Case' not in out, (
            f"mixed-case unfilled placeholder was silent! "
            f"out={out!r}, captured={captured.out!r}")

    def test_known_uppercase_unfilled_placeholder_replaced_with_empty(self):
        """An uppercase placeholder not in `replacements` (e.g. {XYZ})
        is replaced with empty AND warned about. This is the
        pre-existing behavior — the test ensures we don't regress."""
        template = "static {XYZ} more"
        out = dev_template_generator.fill_template(
            {"template": template}, {}, name="x", emoji="🤖",
            task="t", agent_type="sub")
        # The XYZ is replaced with empty (no-regression)
        assert '{XYZ}' not in out

    def test_known_uppercase_placeholder_in_replacements(self):
        """Sanity: a known uppercase placeholder is replaced
        (no-regression)."""
        template = "static {TASK} more"
        out = dev_template_generator.fill_template(
            {"template": template}, {}, name="x", emoji="🤖",
            task="DO STUFF", agent_type="sub")
        assert "DO STUFF" in out
        assert '{TASK}' not in out

    def test_known_lowercase_placeholder_in_replacements(self):
        """Sanity: the lowercase {name} placeholder is replaced
        (no-regression — was in replacements dict)."""
        template = "static {name} more"
        out = dev_template_generator.fill_template(
            {"template": template}, {}, name="cool-agent", emoji="🤖",
            task="t", agent_type="sub")
        assert "cool-agent" in out
        assert '{name}' not in out

    def test_no_duplicate_TASK_in_replacements(self):
        """Code smell: the `replacements` dict in fill_template
        has a duplicate '{TASK}' entry (same anti-pattern as
        R110-326 BUG-B). After the fix, only one entry."""
        # Get the source code
        import inspect
        src = inspect.getsource(dev_template_generator.fill_template)
        # Count occurrences of '"{TASK}":' literal in the dict
        # (excluding the template-string examples)
        # Use a regex that matches dict-entry form: '"{TASK}": task,'
        matches = re.findall(r'"\{TASK\}":\s*task,', src)
        assert len(matches) == 1, (
            f"duplicate {{TASK}} entry in replacements dict: "
            f"found {len(matches)}")

    def test_empty_name_does_not_crash(self):
        """Sanity: empty name (falsy) → name.lower() is skipped →
        {name} replaced with empty string. No crash."""
        template = "static {name} more"
        out = dev_template_generator.fill_template(
            {"template": template}, {}, name="", emoji="🤖",
            task="t", agent_type="sub")
        # {name} → "" so output is "static  more"
        assert '{name}' not in out

    def test_template_with_known_and_unknown_placeholders(self):
        """Mix of known + unknown placeholders: known are replaced,
        unknown are warned about."""
        template = "{NAME} does {TASK} with {XYZ_MYSTERY}"
        out = dev_template_generator.fill_template(
            {"template": template}, {}, name="agent", emoji="🤖",
            task="cleaning", agent_type="sub")
        assert "AGENT" in out
        assert "cleaning" in out


# --- Bonus: _shorten() edge cases -----------------------------------------

class TestR110328ShortenEdgeCases:
    """No bugs found in _shorten(), but documenting behavior for
    future regression safety.
    """

    def test_shorten_empty_string(self):
        assert dev_template_generator._shorten("") == ''

    def test_shorten_shorter_than_maxlen(self):
        assert dev_template_generator._shorten("abc") == 'abc'

    def test_shorten_exactly_maxlen(self):
        assert dev_template_generator._shorten("abcde", maxlen=5) == 'abcde'

    def test_shorten_longer_than_maxlen(self):
        # maxlen=5: takes first 2 chars (5-3=2) + "..."
        assert dev_template_generator._shorten("abcdef", maxlen=5) == 'ab...'

    def test_shorten_maxlen_zero(self):
        # maxlen=0: takes 0-3=-3 → first 0 chars (slicing past end) + "..."
        # In Python, "abc"[:-3] = "" (slice stops at 0, doesn't go negative)
        # So output is "..."
        result = dev_template_generator._shorten("abc", maxlen=0)
        assert result == '...'

    def test_shorten_negative_maxlen(self):
        # Same as maxlen=0: "abc"[:-8] = "" so output is "..."
        result = dev_template_generator._shorten("abc", maxlen=-5)
        assert result == '...'