"""R110-462 — coverage-push r8: tools/dev_haerte_propagation.py 0% → 100%

Hardening propagation tool. CLI:
  [--workspace PATH] <agent_name>  (agent_name default:
  "sub_mas-unknown")

Loads mas-engineer/.mase/rules/hard_rules.yaml from workspace,
filters rules by hardness >= min_hardness (default 4),
classifies as extreme (>=5) or strong (<5), formats as
intake block for sub-agents.

Targets:
- get_hard_rules(workspace, min_hardness=4):
  - load yaml, get hardness_levels + rules
  - iterate rules, filter by hardness >= min_hardness
  - hardness >= 5 → h_name="extreme", icon="⛔⛔⛔⛔⛔"
  - hardness 4 → h_name="strong", icon="⛔⛔⛔"
  - symbol from levels[extreme|strong]
  - return list of {id, text, block, hardness}
  - text = "{icon} {prompt_text}"

- format_for_intake(agent_name, original_intake, workspace):
  - get rules
  - header lines (4)
  - for each rule: block=True → prefix "⛔⛔⛔⛔⛔",
    else → prefix "  "
  - footer lines (3: empty, END, empty)
  - return joined string

- CLI: parse args, call format_for_intake, print
"""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import tools.dev_haerte_propagation as hp  # noqa: E402


def _write_rules(tmp_path, rules_data):
    """Write hard_rules.yaml in workspace/mas-engineer/.mase/rules/."""
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    rules_file = rules_dir / "hard_rules.yaml"
    with open(rules_file, 'w') as f:
        yaml.safe_dump(rules_data, f, sort_keys=False)
    return tmp_path


# ─────────────────────────────────────────────────────────────────────
# get_hard_rules
# ─────────────────────────────────────────────────────────────────────
class TestGetHardRules:
    def _fixture(self, tmp_path):
        return _write_rules(tmp_path, {
            "hardness_levels": {
                "extreme": {"symbol": "⛔", "priority": 1},
                "strong": {"symbol": "⚠️", "priority": 2},
            },
            "rules": [
                {"id": "R1", "prompt_text": "rule one",
                 "block": True, "hardness": 5},
                {"id": "R2", "prompt_text": "rule two",
                 "block": False, "hardness": 4},
                {"id": "R3", "prompt_text": "rule three",
                 "block": True, "hardness": 3},   # below default
                {"id": "R4", "prompt_text": "rule four",
                 "block": False, "hardness": 5},
            ],
        })

    def test_filters_by_min_hardness(self, tmp_path):
        ws = self._fixture(tmp_path)
        rules = hp.get_hard_rules(str(ws))
        # min=4 → R1 (5), R2 (4), R4 (5); R3 (3) excluded
        ids = [r["id"] for r in rules]
        assert ids == ["R1", "R2", "R4"]

    def test_extreme_vs_strong_icon(self, tmp_path):
        ws = self._fixture(tmp_path)
        rules = hp.get_hard_rules(str(ws))
        r1 = next(r for r in rules if r["id"] == "R1")
        r2 = next(r for r in rules if r["id"] == "R2")
        assert "⛔⛔⛔⛔⛔" in r1["text"]
        assert "⛔⛔⛔" in r2["text"]
        assert "⛔⛔⛔⛔⛔" not in r2["text"]

    def test_custom_min_hardness(self, tmp_path):
        ws = self._fixture(tmp_path)
        rules = hp.get_hard_rules(str(ws), min_hardness=3)
        # min=3 → all 4 rules
        assert len(rules) == 4

    def test_extreme_min_hardness_5(self, tmp_path):
        ws = self._fixture(tmp_path)
        rules = hp.get_hard_rules(str(ws), min_hardness=5)
        # Only R1 and R4 (hardness 5)
        ids = [r["id"] for r in rules]
        assert ids == ["R1", "R4"]

    def test_includes_id_block_hardness(self, tmp_path):
        ws = self._fixture(tmp_path)
        rules = hp.get_hard_rules(str(ws))
        for r in rules:
            assert "id" in r
            assert "text" in r
            assert "block" in r
            assert "hardness" in r

    def test_block_field_preserved(self, tmp_path):
        ws = self._fixture(tmp_path)
        rules = hp.get_hard_rules(str(ws))
        r1 = next(r for r in rules if r["id"] == "R1")
        r2 = next(r for r in rules if r["id"] == "R2")
        assert r1["block"] is True
        assert r2["block"] is False

    def test_text_format(self, tmp_path):
        ws = self._fixture(tmp_path)
        rules = hp.get_hard_rules(str(ws))
        r1 = next(r for r in rules if r["id"] == "R1")
        assert r1["text"] == "⛔⛔⛔⛔⛔ rule one"

    def test_no_rules_returns_empty(self, tmp_path):
        ws = _write_rules(tmp_path, {
            "hardness_levels": {},
            "rules": [],
        })
        rules = hp.get_hard_rules(str(ws))
        assert rules == []


# ─────────────────────────────────────────────────────────────────────
# format_for_intake
# ─────────────────────────────────────────────────────────────────────
class TestFormatForIntake:
    def _fixture(self, tmp_path):
        return _write_rules(tmp_path, {
            "hardness_levels": {},
            "rules": [
                {"id": "R1", "prompt_text": "extreme rule",
                 "block": True, "hardness": 5},
                {"id": "R2", "prompt_text": "strong rule",
                 "block": False, "hardness": 4},
            ],
        })

    def test_header_present(self, tmp_path):
        ws = self._fixture(tmp_path)
        s = hp.format_for_intake("agent_x", {}, str(ws))
        assert "INHERITED RULES" in s
        assert "agent_x" in s
        assert "PRIORITY" in s

    def test_footer_present(self, tmp_path):
        ws = self._fixture(tmp_path)
        s = hp.format_for_intake("agent_x", {}, str(ws))
        assert "END INHERITED RULES" in s

    def test_block_true_prefix(self, tmp_path):
        ws = self._fixture(tmp_path)
        s = hp.format_for_intake("agent_x", {}, str(ws))
        # R1 has block=True → prefix "⛔⛔⛔⛔⛔ "
        assert "⛔⛔⛔⛔⛔ ⛔⛔⛔⛔⛔ extreme rule" in s

    def test_block_false_prefix(self, tmp_path):
        ws = self._fixture(tmp_path)
        s = hp.format_for_intake("agent_x", {}, str(ws))
        # R2 has block=False → prefix "  "
        assert "  ⛔⛔⛔ strong rule" in s

    def test_returns_string(self, tmp_path):
        ws = self._fixture(tmp_path)
        s = hp.format_for_intake("agent", {}, str(ws))
        assert isinstance(s, str)
        assert len(s) > 0


# ─────────────────────────────────────────────────────────────────────
# CLI subprocess (covers __main__)
# ─────────────────────────────────────────────────────────────────────
class TestCli:
    def test_cli_default_agent(self, tmp_path):
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        with open(rules_dir / "hard_rules.yaml", 'w') as f:
            yaml.safe_dump({
                "hardness_levels": {},
                "rules": [
                    {"id": "R1", "prompt_text": "x",
                     "block": True, "hardness": 5}
                ],
            }, f)
        r = subprocess.run(
            ['python3', 'tools/dev_haerte_propagation.py',
             '--workspace', str(tmp_path)],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        assert "sub_mas-unknown" in r.stdout

    def test_cli_custom_agent(self, tmp_path):
        rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
        rules_dir.mkdir(parents=True)
        with open(rules_dir / "hard_rules.yaml", 'w') as f:
            yaml.safe_dump({
                "hardness_levels": {},
                "rules": [],
            }, f)
        r = subprocess.run(
            ['python3', 'tools/dev_haerte_propagation.py',
             '--workspace', str(tmp_path),
             'my_agent'],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        assert "my_agent" in r.stdout
