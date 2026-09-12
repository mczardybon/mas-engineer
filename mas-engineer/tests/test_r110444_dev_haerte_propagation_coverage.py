"""R110-444 — coverage-push r8: tools/dev_haerte_propagation.py 0% → 100%.

Hardening-propagation for sub-agents (71 lines).

Targets:
- get_hard_rules: reads mas-engineer/.mase/rules/hard_rules.yaml
  from workspace; filters rules by hardness >= min_hardness;
  hardness >= 5 → "extreme" (⛔⛔⛔⛔⛔), 4 → "strong" (⛔⛔⛔);
  builds {id, text, block, hardness}; missing hardness_levels
  key → empty dict (no crash)
- format_for_intake: builds multi-line block with header
  "INHERITED RULES" + agent name + rules (block=True → prefixed
  with ⛔⛔⛔⛔⛔, otherwise 2-space indent) + footer; calls
  get_hard_rules with default min_hardness=4
- __main__: argparse with --workspace (default: cwd) and
  positional agent_name (default "sub_mas-unknown"); prints
  intake_block to stdout; works without explicit args
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_haerte_propagation as hp  # noqa: E402


@pytest.fixture
def workspace_with_rules(tmp_path):
    """Create workspace with mas-engineer/.mase/rules/hard_rules.yaml."""
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    rules_file = rules_dir / "hard_rules.yaml"
    rules_file.write_text(yaml.safe_dump({
        "hardness_levels": {
            "extreme": {"symbol": "⛔⛔⛔⛔⛔"},
            "strong": {"symbol": "⛔⛔⛔"},
        },
        "rules": [
            {"id": "R1", "hardness": 5, "prompt_text": "no force push",
             "block": True},
            {"id": "R2", "hardness": 4, "prompt_text": "validate first",
             "block": True},
            {"id": "R3", "hardness": 3, "prompt_text": "low priority",
             "block": False},
        ]
    }))
    return tmp_path


# ─────────────────────────────────────────────────────────────────────
# get_hard_rules
# ─────────────────────────────────────────────────────────────────────
class TestGetHardRules:
    def test_default_min_hardness_4(self, workspace_with_rules):
        rules = hp.get_hard_rules(str(workspace_with_rules))
        # R1 (5) and R2 (4) are >= 4; R3 (3) is filtered
        assert len(rules) == 2
        ids = {r["id"] for r in rules}
        assert ids == {"R1", "R2"}

    def test_extreme_hardness_icon(self, workspace_with_rules):
        rules = hp.get_hard_rules(str(workspace_with_rules))
        # R1 has hardness=5 → 5 ⛔
        r1 = next(r for r in rules if r["id"] == "R1")
        assert r1["text"].startswith("⛔⛔⛔⛔⛔ ")

    def test_strong_hardness_icon(self, workspace_with_rules):
        rules = hp.get_hard_rules(str(workspace_with_rules))
        # R2 has hardness=4 → 3 ⛔
        r2 = next(r for r in rules if r["id"] == "R2")
        assert r2["text"].startswith("⛔⛔⛔ ")
        assert "⛔⛔⛔ " in r2["text"]

    def test_includes_block_field(self, workspace_with_rules):
        rules = hp.get_hard_rules(str(workspace_with_rules))
        assert all("block" in r for r in rules)

    def test_custom_min_hardness(self, workspace_with_rules):
        rules = hp.get_hard_rules(str(workspace_with_rules),
                                   min_hardness=3)
        # R1, R2, R3 all >= 3
        assert len(rules) == 3

    def test_empty_rules(self, tmp_path):
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "hard_rules.yaml").write_text(
            yaml.safe_dump({"rules": []}))
        rules = hp.get_hard_rules(str(tmp_path))
        assert rules == []

    def test_missing_levels_key(self, tmp_path):
        # No "hardness_levels" key → empty dict, no crash
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "hard_rules.yaml").write_text(
            yaml.safe_dump({"rules": [
                {"id": "R1", "hardness": 4, "prompt_text": "x",
                 "block": True}]}))
        rules = hp.get_hard_rules(str(tmp_path))
        assert len(rules) == 1


# ─────────────────────────────────────────────────────────────────────
# format_for_intake
# ─────────────────────────────────────────────────────────────────────
class TestFormatForIntake:
    def test_header_present(self, workspace_with_rules):
        result = hp.format_for_intake("agent1", {},
                                       str(workspace_with_rules))
        assert "INHERITED RULES" in result
        assert "agent1" in result
        assert "END INHERITED RULES" in result

    def test_includes_extreme_rule(self, workspace_with_rules):
        result = hp.format_for_intake("agent1", {},
                                       str(workspace_with_rules))
        assert "no force push" in result

    def test_includes_strong_rule(self, workspace_with_rules):
        result = hp.format_for_intake("agent1", {},
                                       str(workspace_with_rules))
        assert "validate first" in result

    def test_excludes_low_priority(self, workspace_with_rules):
        result = hp.format_for_intake("agent1", {},
                                       str(workspace_with_rules))
        assert "low priority" not in result

    def test_block_rule_prefixed(self, workspace_with_rules):
        result = hp.format_for_intake("agent1", {},
                                       str(workspace_with_rules))
        # Block=True rules are prefixed with ⛔⛔⛔⛔⛔
        assert "⛔⛔⛔⛔⛔" in result

    def test_non_block_rule_indented(self, tmp_path):
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "hard_rules.yaml").write_text(
            yaml.safe_dump({"rules": [
                {"id": "R1", "hardness": 4, "prompt_text": "advice",
                 "block": False}]}))
        result = hp.format_for_intake("agent", {}, str(tmp_path))
        # Non-block → "  text" (2 spaces)
        assert "  ⛔⛔⛔ advice" in result


# ─────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────
class TestMainExec:
    def test_main_exec_no_args_uses_defaults(self, tmp_path,
                                                monkeypatch, capsys):
        # Set up rules in cwd
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "hard_rules.yaml").write_text(
            yaml.safe_dump({"rules": [
                {"id": "R1", "hardness": 5, "prompt_text": "rule1",
                 "block": True}]}))
        monkeypatch.chdir(tmp_path)
        old_argv = sys.argv
        sys.argv = ["dev_haerte_propagation.py"]
        try:
            exec(compile(Path(__file__).resolve().parents[1]
                         .joinpath("tools/dev_haerte_propagation.py")
                         .read_text(),
                         "dev_haerte_propagation.py", "exec"),
                 {"__name__": "__main__",
                  "__file__": "dev_haerte_propagation.py",
                  "sys": sys,
                  "Path": Path,
                  "os": __import__("os")})
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "INHERITED RULES" in out

    def test_main_exec_with_workspace_and_agent(self, tmp_path, capsys):
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "hard_rules.yaml").write_text(
            yaml.safe_dump({"rules": [
                {"id": "R1", "hardness": 5, "prompt_text": "rule1",
                 "block": True}]}))
        old_argv = sys.argv
        sys.argv = ["dev_haerte_propagation.py",
                    "--workspace", str(tmp_path),
                    "my_agent"]
        try:
            exec(compile(Path(__file__).resolve().parents[1]
                         .joinpath("tools/dev_haerte_propagation.py")
                         .read_text(),
                         "dev_haerte_propagation.py", "exec"),
                 {"__name__": "__main__",
                  "__file__": "dev_haerte_propagation.py",
                  "sys": sys,
                  "Path": Path,
                  "os": __import__("os")})
        finally:
            sys.argv = old_argv
        out = capsys.readouterr().out
        assert "my_agent" in out
