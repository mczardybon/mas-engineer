"""R110-434 — coverage-push r6: tools/dev_haerte_propagation.py 0% → 100%.

Hardening-propagation for sub-agents (71 lines). Reads
.mase/rules/hard_rules.yaml and formats a block of strong/extreme
rules to prepend to sub-agent intake.

Targets:
- get_hard_rules: returns list of {id, text, block, hardness} for
  rules >= min_hardness; hardness>=5 → "extreme" + 5 icons, 4..4
  → "strong" + 3 icons (only >= 4 considered by default); uses
  hardness_levels[extreme/strong].symbol prefix; no rules → empty
  list; min_hardness=5 filters out level-4 rules; missing
  hardness_levels default to {}
- format_for_intake: builds the ⛔⛔⛔⛔⛔ INHERITED RULES block;
  block=True rules get ⛔⛔⛔⛔⛔ prefix, non-block get 2-space
  indent; agent_name substituted into header
- __main__ exec: with --workspace and agent_name prints the block
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_haerte_propagation as hp  # noqa: E402


@pytest.fixture
def rules_yaml(tmp_path):
    """Write a hard_rules.yaml under tmp_path/mas-engineer/.mase/rules."""
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    rules_file = rules_dir / "hard_rules.yaml"
    data = {
        "hardness_levels": {
            "extreme": {"symbol": "⛔⛔⛔⛔⛔", "description": "..."},
            "strong": {"symbol": "⛔⛔⛔", "description": "..."},
        },
        "rules": [
            {"id": "R1", "hardness": 5, "prompt_text": "extreme rule",
             "block": True},
            {"id": "R2", "hardness": 4, "prompt_text": "strong rule",
             "block": True},
            {"id": "R3", "hardness": 3, "prompt_text": "weak rule",
             "block": False},
            {"id": "R4", "hardness": 4, "prompt_text": "strong non-block",
             "block": False},
            {"id": "R5", "hardness": 5, "prompt_text": "extreme non-block",
             "block": False},
        ],
    }
    rules_file.write_text(yaml.safe_dump(data))
    return tmp_path  # workspace root


# ─────────────────────────────────────────────────────────────────────
# get_hard_rules
# ─────────────────────────────────────────────────────────────────────
class TestGetHardRules:
    def test_default_min_hardness_4(self, rules_yaml):
        rules = hp.get_hard_rules(str(rules_yaml))
        # Should include R1 (5), R2 (4), R4 (4), R5 (5); exclude R3 (3)
        ids = [r["id"] for r in rules]
        assert ids == ["R1", "R2", "R4", "R5"]

    def test_hardness_field(self, rules_yaml):
        rules = hp.get_hard_rules(str(rules_yaml))
        hardnesses = [r["hardness"] for r in rules]
        assert hardnesses == [5, 4, 4, 5]

    def test_text_contains_prompt(self, rules_yaml):
        rules = hp.get_hard_rules(str(rules_yaml))
        # Verify each rule's prompt_text is in its formatted text
        prompts_by_id = {r["id"]: r["text"] for r in rules}
        expected_prompts = {
            "R1": "extreme rule",
            "R2": "strong rule",
            "R4": "strong non-block",
            "R5": "extreme non-block",
        }
        for rid, expected in expected_prompts.items():
            assert expected in prompts_by_id[rid]

    def test_extreme_icon_5(self, rules_yaml):
        rules = hp.get_hard_rules(str(rules_yaml))
        extreme = [r for r in rules if r["hardness"] == 5]
        for r in extreme:
            assert "⛔⛔⛔⛔⛔" in r["text"]

    def test_strong_icon_3(self, rules_yaml):
        rules = hp.get_hard_rules(str(rules_yaml))
        strong = [r for r in rules if r["hardness"] == 4]
        for r in strong:
            assert "⛔⛔⛔" in r["text"]

    def test_block_field_preserved(self, rules_yaml):
        rules = hp.get_hard_rules(str(rules_yaml))
        blocks = {r["id"]: r["block"] for r in rules}
        assert blocks == {"R1": True, "R2": True, "R4": False, "R5": False}

    def test_min_hardness_5_filters_out_4(self, rules_yaml):
        rules = hp.get_hard_rules(str(rules_yaml), min_hardness=5)
        ids = [r["id"] for r in rules]
        assert ids == ["R1", "R5"]

    def test_no_rules_returns_empty(self, tmp_path):
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "hard_rules.yaml").write_text(
            yaml.safe_dump({"rules": []}))
        rules = hp.get_hard_rules(str(tmp_path))
        assert rules == []

    def test_missing_hardness_levels_uses_default(self, tmp_path):
        # No hardness_levels key → defaults to {}
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "hard_rules.yaml").write_text(yaml.safe_dump({
            "rules": [
                {"id": "X", "hardness": 4, "prompt_text": "rule",
                 "block": True}
            ]
        }))
        rules = hp.get_hard_rules(str(tmp_path))
        assert len(rules) == 1
        # symbol="" so text just has icons + prompt
        assert "rule" in rules[0]["text"]


# ─────────────────────────────────────────────────────────────────────
# format_for_intake
# ─────────────────────────────────────────────────────────────────────
class TestFormatForIntake:
    def test_header_contains_agent_name(self, rules_yaml):
        out = hp.format_for_intake("sub_mas-foo", {}, str(rules_yaml))
        assert "sub_mas-foo" in out

    def test_header_block_marker(self, rules_yaml):
        out = hp.format_for_intake("foo", {}, str(rules_yaml))
        assert "INHERITED RULES" in out
        assert "EXTREME + STRONG" in out

    def test_end_block_marker(self, rules_yaml):
        out = hp.format_for_intake("foo", {}, str(rules_yaml))
        assert "END INHERITED RULES" in out

    def test_block_rule_gets_5_icon_prefix(self, rules_yaml):
        out = hp.format_for_intake("foo", {}, str(rules_yaml))
        # R1 has block=True and hardness=5 → prefix line
        assert "⛔⛔⛔⛔⛔ ⛔⛔⛔⛔⛔ extreme rule" in out

    def test_non_block_rule_gets_2_space_indent(self, rules_yaml):
        out = hp.format_for_intake("foo", {}, str(rules_yaml))
        # R4 (strong non-block) → "  ⛔⛔⛔ strong non-block"
        assert "  ⛔⛔⛔ strong non-block" in out

    def test_priority_text(self, rules_yaml):
        out = hp.format_for_intake("foo", {}, str(rules_yaml))
        assert "PRIORITY" in out


# ─────────────────────────────────────────────────────────────────────
# __main__ exec
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_exec_with_workspace(self, rules_yaml, capsys):
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "dev_haerte_propagation.py").read_text()
        old_argv = sys.argv
        try:
            sys.argv = ["dev_haerte_propagation.py",
                        "--workspace", str(rules_yaml),
                        "sub_mas-test_agent"]
            exec(compile(script, "dev_haerte_propagation.py", "exec"),
                 {"__name__": "__main__",
                  "__file__": "dev_haerte_propagation.py"})
            out = capsys.readouterr().out
            assert "sub_mas-test_agent" in out
            assert "INHERITED RULES" in out
        finally:
            sys.argv = old_argv
