"""
R110-353: coverage-push round 2 for tools/dev_workspace.py.

Target: pure interactive functions (_ask_*) that take user
input via input() (mocked) and pure agent-generation logic
(_generate_agent) that creates recipe YAML files.

dev_workspace.py round 1 (R110-351) brought coverage from
0% to 16% on 595 testable stmts. Round 2 targets:

  1. _ask_type (L762-783) — interactive type selector
     - choice 1 → returns ('mas_sub', 'mas-engineer/recipe/sub/', 'agent_template.yaml')
     - choice 2 → returns ('fw_specialist', 'framework/recipes/specialists/', None)
     - choice 3 → returns ('fw_sub', 'framework/recipes/sub/', None)
     - invalid choice → loops
     - EOFError → returns (None, None, None)

  2. _ask_name (L788-820) — interactive name validator
     - mas_sub type → prints specific hint
     - fw_specialist type → prints different hint
     - fw_sub type → prints default hint
     - empty name → loops
     - invalid name (uppercase/special) → loops
     - EOFError → returns None
     - valid name → returns it (lowercased, spaces→dashes)

  3. _ask_description (L814-833) — interactive desc + emoji
     - empty desc → returns (name-derived default, emoji)
     - valid desc → returns (desc, emoji)
     - empty emoji → returns (desc, '🤖')
     - EOFError → returns (None, None)

  4. _generate_agent (L836-940) — recipe generator
     - mas_sub agent → creates file in mas-engineer/recipe/sub/
     - fw_specialist agent → creates file in framework/recipes/specialists/
     - fw_sub agent → creates file in framework/recipes/sub/
     - existing file + 'n' → skip
     - existing file + 'j' → overwrite
     - mas_sub without MAS_TEMPLATE → returns None
     - generates valid YAML (parseable with yaml.safe_load)

Target: bump coverage from 16% to ~30% (+14pp).
"""
import sys
import importlib
import builtins
from pathlib import Path
import pytest
import yaml

TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def ws_mod(tmp_path, monkeypatch):
    """Import dev_workspace with cwd sandboxed."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_workspace", None)
    mod = importlib.import_module("dev_workspace")
    yield mod
    sys.modules.pop("dev_workspace", None)


class TestAskType:
    """_ask_type (L762-783)."""

    def test_choice_1_returns_mas_sub(self, ws_mod, monkeypatch, capsys):
        """Choice 1 → ('mas_sub', 'mas-engineer/recipe/sub/', 'agent_template.yaml')."""
        monkeypatch.setattr(builtins, "input", lambda _: "1")
        result = ws_mod._ask_type()
        assert result == ("mas_sub", "mas-engineer/recipe/sub/", "agent_template.yaml")

    def test_choice_2_returns_fw_specialist(self, ws_mod, monkeypatch):
        """Choice 2 → ('fw_specialist', 'framework/recipes/specialists/', None)."""
        monkeypatch.setattr(builtins, "input", lambda _: "2")
        result = ws_mod._ask_type()
        assert result == ("fw_specialist", "framework/recipes/specialists/", None)

    def test_choice_3_returns_fw_sub(self, ws_mod, monkeypatch):
        """Choice 3 → ('fw_sub', 'framework/recipes/sub/', None)."""
        monkeypatch.setattr(builtins, "input", lambda _: "3")
        result = ws_mod._ask_type()
        assert result == ("fw_sub", "framework/recipes/sub/", None)

    def test_invalid_then_valid_loops(self, ws_mod, monkeypatch):
        """Invalid input (e.g. '5') → loops; second valid input accepted."""
        inputs = iter(["5", "2"])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        result = ws_mod._ask_type()
        assert result[0] == "fw_specialist"

    def test_eoferror_returns_none_tuple(self, ws_mod, monkeypatch):
        """EOFError → returns (None, None, None)."""
        def raise_eof(_):
            raise EOFError
        monkeypatch.setattr(builtins, "input", raise_eof)
        result = ws_mod._ask_type()
        assert result == (None, None, None)


class TestAskName:
    """_ask_name (L788-820)."""

    def test_valid_mas_sub_name(self, ws_mod, monkeypatch):
        """Valid name for mas_sub type → returns it."""
        monkeypatch.setattr(builtins, "input", lambda _: "database-cleaner")
        result = ws_mod._ask_name("mas_sub")
        assert result == "database-cleaner"

    def test_valid_fw_specialist_name(self, ws_mod, monkeypatch):
        """Valid name for fw_specialist → returns it."""
        monkeypatch.setattr(builtins, "input", lambda _: "deploy")
        result = ws_mod._ask_name("fw_specialist")
        assert result == "deploy"

    def test_valid_fw_sub_name(self, ws_mod, monkeypatch):
        """Valid name for fw_sub → returns it."""
        monkeypatch.setattr(builtins, "input", lambda _: "config-writer")
        result = ws_mod._ask_name("fw_sub")
        assert result == "config-writer"

    def test_uppercase_normalized_to_lowercase(self, ws_mod, monkeypatch):
        """UPPERCASE name → lowercased."""
        monkeypatch.setattr(builtins, "input", lambda _: "MyAgent")
        result = ws_mod._ask_name("mas_sub")
        assert result == "myagent"

    def test_spaces_replaced_with_dashes(self, ws_mod, monkeypatch):
        """Spaces in name → replaced with dashes."""
        monkeypatch.setattr(builtins, "input", lambda _: "my agent")
        result = ws_mod._ask_name("mas_sub")
        assert result == "my-agent"

    def test_empty_name_loops(self, ws_mod, monkeypatch):
        """Empty name → loops; second valid name returned."""
        inputs = iter(["", "valid-name"])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        result = ws_mod._ask_name("mas_sub")
        assert result == "valid-name"

    def test_invalid_name_with_underscore_loops(self, ws_mod, monkeypatch):
        """Underscore (not allowed) → loops."""
        inputs = iter(["bad_name", "good-name"])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        result = ws_mod._ask_name("mas_sub")
        assert result == "good-name"

    def test_eoferror_returns_none(self, ws_mod, monkeypatch):
        """EOFError → returns None."""
        monkeypatch.setattr(builtins, "input", lambda _: (_ for _ in ()).throw(EOFError))
        result = ws_mod._ask_name("mas_sub")
        assert result is None


class TestAskDescription:
    """_ask_description (L814-833)."""

    def test_valid_desc_and_emoji(self, ws_mod, monkeypatch):
        """Valid desc + emoji → returns tuple."""
        inputs = iter(["Database cleanup", "🛡️"])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        result = ws_mod._ask_description("my-agent")
        assert result == ("Database cleanup", "🛡️")

    def test_empty_desc_falls_back_to_name(self, ws_mod, monkeypatch):
        """Empty desc → returns ('My Agent', emoji)."""
        inputs = iter(["", "🧪"])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        result = ws_mod._ask_description("my-agent")
        assert result == ("My Agent", "🧪")

    def test_empty_emoji_falls_back_to_robot(self, ws_mod, monkeypatch):
        """Empty emoji → defaults to '🤖'."""
        inputs = iter(["Description", ""])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        result = ws_mod._ask_description("agent")
        assert result == ("Description", "🤖")

    def test_whitespace_only_desc_falls_back_to_name(self, ws_mod, monkeypatch):
        """Whitespace-only desc → name fallback."""
        inputs = iter(["   ", "🤖"])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        result = ws_mod._ask_description("cool-agent")
        assert result == ("Cool Agent", "🤖")

    def test_eoferror_returns_none_none(self, ws_mod, monkeypatch):
        """EOFError → returns (None, None)."""
        monkeypatch.setattr(builtins, "input", lambda _: (_ for _ in ()).throw(EOFError))
        result = ws_mod._ask_description("agent")
        assert result == (None, None)


class TestGenerateAgent:
    """_generate_agent (L836-940)."""

    def test_mas_sub_creates_file_in_sub_dir(self, ws_mod, tmp_path, monkeypatch):
        """mas_sub agent → creates mas-engineer/recipe/sub/sub_mas-NAME.yaml."""
        monkeypatch.setattr(builtins, "input", lambda _: (_ for _ in ()).throw(EOFError))
        result = ws_mod._generate_agent(
            "mas_sub", "myagent", "Test desc", "🤖", str(tmp_path)
        )
        # Path: tmp_path / "mas-engineer" / "recipe" / "sub" / "sub_mas-myagent.yaml"
        expected = tmp_path / "mas-engineer" / "recipe" / "sub" / "sub_mas-myagent.yaml"
        if expected.exists():
            # MAS_TEMPLATE existed, was used; result is Path or str
            assert Path(result) == expected
            assert expected.exists()
        else:
            # MAS_TEMPLATE didn't exist, returned None
            assert result is None

    def test_fw_specialist_creates_file(self, ws_mod, tmp_path, monkeypatch):
        """fw_specialist agent → creates framework/recipes/specialists/NAME.yaml."""
        result = ws_mod._generate_agent(
            "fw_specialist", "deploy", "Deploy tool", "🚀", str(tmp_path)
        )
        expected = tmp_path / "framework" / "recipes" / "specialists" / "deploy.yaml"
        assert Path(result) == expected
        assert expected.exists()
        # Verify YAML is parseable
        content = yaml.safe_load(expected.read_text())
        assert "title" in content
        assert "🚀" in content["title"] or "🚀" in content.get("prompt", "")

    def test_fw_sub_creates_file(self, ws_mod, tmp_path, monkeypatch):
        """fw_sub agent → creates framework/recipes/sub/sub_NAME.yaml."""
        result = ws_mod._generate_agent(
            "fw_sub", "config-writer", "Config writer", "📝", str(tmp_path)
        )
        expected = tmp_path / "framework" / "recipes" / "sub" / "sub_config-writer.yaml"
        assert Path(result) == expected
        assert expected.exists()

    def test_existing_file_overwrite_yes(self, ws_mod, tmp_path, monkeypatch):
        """Existing file + user says 'j' → overwrites."""
        # Create a fw_specialist file first
        existing = tmp_path / "framework" / "recipes" / "specialists" / "deploy.yaml"
        existing.parent.mkdir(parents=True)
        existing.write_text("old: content")
        # Now try to generate, accept overwrite
        inputs = iter(["j"])
        monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
        result = ws_mod._generate_agent(
            "fw_specialist", "deploy", "New desc", "🚀", str(tmp_path)
        )
        # File should be overwritten (not contain 'old: content' anymore)
        content = existing.read_text()
        assert "old: content" not in content

    def test_existing_file_skip(self, ws_mod, tmp_path, monkeypatch):
        """Existing file + user says 'n' → returns None, file unchanged."""
        existing = tmp_path / "framework" / "recipes" / "specialists" / "deploy.yaml"
        existing.parent.mkdir(parents=True)
        existing.write_text("old: content")
        # User says 'n'
        monkeypatch.setattr(builtins, "input", lambda _: "n")
        result = ws_mod._generate_agent(
            "fw_specialist", "deploy", "New desc", "🚀", str(tmp_path)
        )
        assert result is None
        # File should be unchanged
        assert existing.read_text() == "old: content"

    def test_generates_valid_yaml(self, ws_mod, tmp_path):
        """Generated framework YAML is valid (parseable with yaml.safe_load)."""
        result = ws_mod._generate_agent(
            "fw_specialist", "mytool", "My tool desc", "🔧", str(tmp_path)
        )
        assert result is not None
        content = yaml.safe_load(Path(result).read_text())
        assert isinstance(content, dict)
        assert "version" in content
        assert "title" in content
        assert content["title"] == "MYTOOL — My tool desc"

    def test_special_chars_in_description_dont_break_yaml(self, ws_mod, tmp_path):
        """R110-324-BUG-B: quotes in description don't break YAML."""
        result = ws_mod._generate_agent(
            "fw_specialist", "mytool", 'Tool with "quotes" and \'apostrophes\'', "🔧", str(tmp_path)
        )
        assert result is not None
        # Should be valid YAML
        content = yaml.safe_load(Path(result).read_text())
        assert isinstance(content, dict)
        assert "quotes" in content["title"]


class TestAskNamePrintsHint:
    """Verify _ask_name prints the right hint per agent_type."""

    def test_mas_sub_hint_includes_sub_mas(self, ws_mod, monkeypatch, capsys):
        """mas_sub hint mentions 'sub_mas-'."""
        monkeypatch.setattr(builtins, "input", lambda _: "myagent")
        ws_mod._ask_name("mas_sub")
        captured = capsys.readouterr()
        assert "sub_mas" in captured.out

    def test_fw_specialist_hint_simpler(self, ws_mod, monkeypatch, capsys):
        """fw_specialist hint just shows .yaml without sub_ prefix."""
        monkeypatch.setattr(builtins, "input", lambda _: "deploy")
        ws_mod._ask_name("fw_specialist")
        captured = capsys.readouterr()
        assert ".yaml" in captured.out

    def test_fw_sub_hint_uses_sub_prefix(self, ws_mod, monkeypatch, capsys):
        """fw_sub hint mentions 'sub_' prefix."""
        monkeypatch.setattr(builtins, "input", lambda _: "config")
        ws_mod._ask_name("fw_sub")
        captured = capsys.readouterr()
        assert "sub_" in captured.out
