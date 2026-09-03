"""R110-324 regression tests: latent-bug fixes in dev_workspace.

R110-324 takes candidate #2 from the R110-321 cov-push queue
(dev_workspace.py, 1445 stmts) and probes it for latent bugs.
This file documents 2 bugs found, their fixes, and the
regression tests that lock them in.

Bug A — _ask_description() references undefined `name` (R110-324-BUG-A)
  LOCATION: tools/dev_workspace.py, line 823
  SYMPTOM: When called interactively, _ask_description() returns
        return desc or name.replace("-", " ").title(), emoji
    but `name` is not a parameter of _ask_description() and is
    not defined in the function scope. If the user enters an
    empty description (which is a valid input — the prompt
    says "Description (z.B. 'Database-Cleanup'):"), the
    short-circuit `desc or name.replace(...)` evaluates
    `name.replace(...)` and raises NameError.
  ROOT CAUSE: The function was originally written assuming a
    `name` variable would be in scope (because in the original
    prototype, the function was likely inlined in a larger
    closure where `name` WAS defined). When extracted to a
    standalone function, the reference to `name` was not
    removed.
  FIX: Make _ask_description() accept `name` as a parameter,
    so the caller (which DOES have `name` in scope at line
    1286) passes it explicitly. This is the same pattern as
    the other _ask_* helpers (_ask_type, _ask_name) which
    don't have this bug because they have explicit signatures.
  IMPACT: Rare-but-real crash for the interactive scaffolding
    flow. The non-interactive path (line 1284: args.quiet
    branch) computes desc inline so it never hits the bug.
    But the interactive path is the user-facing default.

Bug B — _generate_agent() YAML-injection via unsanitized description
  (R110-324-BUG-B)
  LOCATION: tools/dev_workspace.py, lines 858-887
  SYMPTOM: When generating a framework agent, the user-supplied
    `description` is interpolated directly into the YAML via
    f-string / .replace(), without escaping. A malicious or
    accidental description like
        x'\ntitle: 'INJECTED_TITLE'\nfoo: '
    breaks out of the single-quoted string and injects
    arbitrary YAML keys.
  ROOT CAUSE: The framework minimum-YAML at lines 871-887
    uses f-string with `description` in two places (title and
    description fields), both wrapped in single quotes. No
    escaping. The MAS_TEMPLATE path at lines 858-867 is safer
    only because the placeholders are pre-defined in the
    template; user input is still interpolated into those
    placeholders without escaping.
  FIX: Use yaml.safe_dump with proper escaping for the
    user-controlled fields. For the framework minimum-YAML,
    replace the f-string with a yaml.safe_dump call. For
    the MAS_TEMPLATE path, validate the user input is a
    "safe" string (no newlines + no quote chars), or use
    yaml.safe_dump for the title/description fields.
  IMPACT: YAML-injection is a real correctness bug (and a
    potential security issue if generated recipes are
    auto-validated and merged). The fix uses yaml.safe_dump
    which always produces valid YAML with proper escaping.

Test pattern (R110-310/R110-320/R110-322/R110-323 inheritance):
  Each test imports dev_workspace.py directly and calls the
  testable (non-# pragma: no cover) functions. The functions
  being tested don't need a GOOSE environment, so we can
  import them in-process. For _ask_description() we mock
  builtin input() via unittest.mock.patch.
"""
import io
import sys
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

# Import the module under test. dev_workspace has top-level
# constants (MAS_TEMPLATE) but no side effects on import.
TOOL_DIR = Path(__file__).resolve().parent.parent / 'tools'
sys.path.insert(0, str(TOOL_DIR))
import dev_workspace  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# --- Bug A regression: _ask_description() NameError ------------------------

class TestR110324BugADescriptionNameError:
    """R110-324-BUG-A: _ask_description() references undefined `name`
    when user enters empty description. The fix adds `name` as a
    parameter so the caller passes it explicitly.
    """

    def test_empty_description_no_longer_raises_NameError(self, monkeypatch):
        """The original bug: user enters empty description, function
        tries to evaluate `name.replace(...)` and raises NameError.
        After the fix, _ask_description(name='x') returns a sensible
        default derived from `name`."""
        # Simulate user pressing Enter for desc, then '🛡️' for emoji
        inputs = iter(['', '🛡️'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))

        # This MUST NOT raise NameError after the fix
        desc, emoji = dev_workspace._ask_description(name='my-cool-agent')

        assert desc == 'My Cool Agent'  # derived from name
        assert emoji == '🛡️'

    def test_nonempty_description_is_returned_as_is(self, monkeypatch):
        """If the user enters a description, it's returned unchanged."""
        inputs = iter(['My cool agent description', '🤖'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))

        desc, emoji = dev_workspace._ask_description(name='my-agent')
        assert desc == 'My cool agent description'
        assert emoji == '🤖'

    def test_default_emoji_when_user_skips(self, monkeypatch):
        """If user enters empty emoji, default '🤖' is used."""
        inputs = iter(['Some desc', ''])  # empty emoji
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))

        desc, emoji = dev_workspace._ask_description(name='x')
        assert desc == 'Some desc'
        assert emoji == '🤖'

    def test_EOF_returns_None(self, monkeypatch):
        """If user hits Ctrl-D, _ask_description returns (None, None)."""
        def _eof(_prompt):
            raise EOFError
        monkeypatch.setattr('builtins.input', _eof)

        result = dev_workspace._ask_description(name='x')
        assert result == (None, None)

    def test_keyboard_interrupt_returns_None(self, monkeypatch):
        """If user hits Ctrl-C, _ask_description returns (None, None)."""
        def _ctrl_c(_prompt):
            raise KeyboardInterrupt
        monkeypatch.setattr('builtins.input', _ctrl_c)

        result = dev_workspace._ask_description(name='x')
        assert result == (None, None)


# --- Bug B regression: _generate_agent YAML-injection ----------------------

class TestR110324BugBYAMLInjection:
    """R110-324-BUG-B: _generate_agent() interpolates user description
    into YAML without escaping. The fix uses yaml.safe_dump or
    explicit escaping for user-controlled fields.
    """

    def test_framework_minimum_yaml_is_valid(self, tmp_path, monkeypatch):
        """Generated YAML must be parseable, even with weird input."""
        monkeypatch.setattr('builtins.input', lambda _: 'n')  # don't overwrite

        # Use a "safe" description (no quotes / newlines) — but
        # the fix should handle unsafe input too.
        yaml_path = dev_workspace._generate_agent(
            agent_type='fw_specialist',
            name='my-specialist',
            description='A normal description',
            emoji='🛡️',
            workspace=str(tmp_path),
        )
        assert yaml_path is not None
        # Must be valid YAML
        data = yaml.safe_load(yaml_path.read_text())
        assert data is not None
        assert 'title' in data

    def test_unsafe_description_does_not_inject_yaml(self, tmp_path, monkeypatch):
        """THE BUG: a description with quote + newline chars could
        inject arbitrary YAML keys. After the fix, the description
        is either escaped or wrapped in yaml.safe_dump so the
        output is always valid YAML and the description is
        treated as a single field value, not a YAML structure."""
        monkeypatch.setattr('builtins.input', lambda _: 'n')  # don't overwrite

        # Malicious description: breaks out of single-quoted string
        evil_desc = "x'\ntitle: 'INJECTED'\nfoo: '"

        yaml_path = dev_workspace._generate_agent(
            agent_type='fw_specialist',
            name='my-specialist',
            description=evil_desc,
            emoji='🤖',
            workspace=str(tmp_path),
        )
        assert yaml_path is not None
        # Parse and verify no injection happened
        data = yaml.safe_load(yaml_path.read_text())
        # The 'foo' key must NOT be present
        assert 'foo' not in data, (
            f'YAML injection succeeded! data={data}')
        # The 'title' must NOT be the injected 'INJECTED'
        assert data.get('title') != 'INJECTED', (
            f'YAML title was hijacked! data={data}')
        # The description text is preserved (somewhere in the
        # generated YAML, escaped or wrapped)
        # (we don't assert exact text — different valid fixes
        # would handle this differently)

    def test_emoji_in_description_does_not_break_yaml(self, tmp_path, monkeypatch):
        """Emoji + colons in description must not break YAML."""
        monkeypatch.setattr('builtins.input', lambda _: 'n')

        yaml_path = dev_workspace._generate_agent(
            agent_type='fw_specialist',
            name='test',
            description='Database cleanup 🛡️: removes stale entries',
            emoji='🤖',
            workspace=str(tmp_path),
        )
        assert yaml_path is not None
        data = yaml.safe_load(yaml_path.read_text())
        assert data is not None
        assert 'title' in data

    def test_existing_file_overwrite_prompt(self, tmp_path, monkeypatch):
        """No-regression: existing file triggers overwrite prompt."""
        monkeypatch.setattr('builtins.input', lambda _: 'n')  # "no, don't overwrite"

        # First call creates the file
        first = dev_workspace._generate_agent(
            agent_type='fw_specialist',
            name='agent1',
            description='First',
            emoji='🤖',
            workspace=str(tmp_path),
        )
        assert first is not None

        # Second call: file exists, user says no → returns None
        second = dev_workspace._generate_agent(
            agent_type='fw_specialist',
            name='agent1',
            description='Second',
            emoji='🤖',
            workspace=str(tmp_path),
        )
        assert second is None

        # File content unchanged
        data = yaml.safe_load(first.read_text())
        assert 'First' in str(data)  # first description preserved
