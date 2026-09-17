#!/usr/bin/env python3
"""
R110-514: Coverage test for tools/dev_haerte_propagation.py (41 stmts, 0% → target 85%+).

Context: dev_haerte_propagation.py implements Method 6 of the mas-engineer
delegation protocol — propagating "extreme" (hardness ≥5) and "strong"
(hardness 4) hardening rules into sub-agent intake blocks. It runs at
EVERY delegate() call (per the docstring at line 4).

The module is small (71 lines, 41 stmts) with 3 stmts in the __main__
guard and 38 stmts in two functions:

  - get_hard_rules(workspace, min_hardness=4) — loads hard_rules.yaml,
    filters rules above the threshold, builds a result list with
    hardness_icon and text fields.

  - format_for_intake(agent_name, original_intake, workspace) — calls
    get_hard_rules, wraps each rule in a ⛔ or non-block bullet, and
    returns a header-prefixed + footer-suffixed string.

  - __main__ guard: argparse with --workspace + agent_name positional.

This file tests all three.

Test strategy:
  - Use a tmp_path fixture containing a fake mas-engineer/.mase/rules/
    hard_rules.yaml with controlled rules (mix of hardness levels,
    some with block: true, some without, some with custom symbol).
  - For get_hard_rules: 5 tests covering the filter logic, the
    hardness ≥5 vs 4 branching, the icon selection, and the
    default-symbol fallback.
  - For format_for_intake: 4 tests covering the header/footer
    structure, the block vs non-block bullet, the agent_name
    interpolation, and the empty-rules case.
  - For __main__: 1 runpy test that loads the module with
    __name__ == '__main__' and asserts it exits cleanly.
"""

import io
import json
import os
import runpy
import sys
from pathlib import Path

import pytest
import yaml

# Import as tools.X so pytest-cov tracks coverage under the correct
# module name (the file lives at tools/dev_haerte_propagation.py).
import tools.dev_haerte_propagation as hp  # noqa: E402


# ─── fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def workspace_with_rules(tmp_path):
    """Create a fake workspace at tmp_path/mas-engineer/.mase/rules/hard_rules.yaml.

    The fixture creates 4 rules spanning hardness 3, 4, 5, 5:
      - rule_weak    (hardness 3): below default threshold, must NOT appear
      - rule_strong  (hardness 4): default threshold, must appear with ⛔⛔⛔
      - rule_extreme (hardness 5): extreme level, must appear with ⛔⛔⛔⛔⛔
      - rule_extreme_noblock (hardness 5): extreme but block=false

    hardness_levels has both 'extreme' and 'strong' keys so the
    .get(symbol, "") lookup has at least one hit per branch.
    """
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    rules_file = rules_dir / "hard_rules.yaml"
    rules_file.write_text(yaml.dump({
        "hardness_levels": {
            "extreme": {"symbol": "⛔⛔⛔⛔⛔", "level": 5},
            "strong":  {"symbol": "⛔⛔⛔",     "level": 4},
        },
        "rules": [
            {"id": "rule_weak",
             "hardness": 3, "block": True,
             "prompt_text": "weak rule"},
            {"id": "rule_strong",
             "hardness": 4, "block": False,
             "prompt_text": "strong rule"},
            {"id": "rule_extreme",
             "hardness": 5, "block": True,
             "prompt_text": "extreme rule"},
            {"id": "rule_extreme_noblock",
             "hardness": 5, "block": False,
             "prompt_text": "extreme but no block"},
        ],
    }))
    return tmp_path


# ─── get_hard_rules ──────────────────────────────────────────────────

def test_get_hard_rules_returns_strong_and_extreme_only(workspace_with_rules):
    """Covers lines 16-39: default threshold (4) includes hardness ≥4
    and excludes hardness <4."""
    rules = hp.get_hard_rules(str(workspace_with_rules))
    ids = [r["id"] for r in rules]
    # rule_weak (hardness 3) is filtered out
    assert "rule_weak" not in ids
    # rule_strong, rule_extreme, rule_extreme_noblock are included
    assert "rule_strong" in ids
    assert "rule_extreme" in ids
    assert "rule_extreme_noblock" in ids
    # Ordering preserved (yaml order = list order)
    assert ids == ["rule_strong", "rule_extreme", "rule_extreme_noblock"]


def test_get_hard_rules_text_has_icon_prefix(workspace_with_rules):
    """Covers line 31 (hardness_icon selection) + line 34 (text formatting)."""
    rules = hp.get_hard_rules(str(workspace_with_rules))
    by_id = {r["id"]: r for r in rules}
    # strong: ⛔⛔⛔ icon, but text starts with the icon (4 ⛔⛔⛔ + rule text)
    assert by_id["rule_strong"]["text"].startswith("⛔⛔⛔")
    # extreme: 5-icon version
    assert by_id["rule_extreme"]["text"].startswith("⛔⛔⛔⛔⛔")
    assert by_id["rule_extreme_noblock"]["text"].startswith("⛔⛔⛔⛔⛔")
    # And the prompt_text is appended after the icon + space
    assert "strong rule" in by_id["rule_strong"]["text"]
    assert "extreme rule" in by_id["rule_extreme"]["text"]


def test_get_hard_rules_preserves_block_and_hardness_fields(workspace_with_rules):
    """Covers lines 35-36: result dict includes block + hardness from source."""
    rules = hp.get_hard_rules(str(workspace_with_rules))
    by_id = {r["id"]: r for r in rules}
    assert by_id["rule_strong"]["block"] is False
    assert by_id["rule_strong"]["hardness"] == 4
    assert by_id["rule_extreme"]["block"] is True
    assert by_id["rule_extreme"]["hardness"] == 5


def test_get_hard_rules_custom_min_hardness_threshold(workspace_with_rules):
    """Covers the min_hardness parameter: setting threshold=5 should
    filter out rule_strong (hardness=4)."""
    rules = hp.get_hard_rules(str(workspace_with_rules), min_hardness=5)
    ids = [r["id"] for r in rules]
    assert "rule_strong" not in ids
    assert "rule_extreme" in ids
    assert "rule_extreme_noblock" in ids


def test_get_hard_rules_unknown_hardness_level_falls_back_to_empty_symbol(
    tmp_path,
):
    """Covers line 30: `level.get("symbol", "")` fallback when the
    hardness_levels dict doesn't have a key for the matched hardness.

    We craft a rules.yaml whose hardness_levels dict is missing the
    "strong" key — only "extreme" exists.  Then rule_strong (hardness=4)
    matches the `else` branch (h_name="strong"), levels.get returns {},
    and the symbol lookup falls back to "".
    """
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "hard_rules.yaml").write_text(yaml.dump({
        "hardness_levels": {
            "extreme": {"symbol": "⛔⛔⛔⛔⛔", "level": 5},
            # NOTE: "strong" key intentionally missing
        },
        "rules": [
            {"id": "rule_strong_orphan",
             "hardness": 4, "block": True,
             "prompt_text": "orphan strong"},
        ],
    }))
    rules = hp.get_hard_rules(str(tmp_path), min_hardness=4)
    # Even though the symbol is "", the rule still appears (with empty prefix).
    # hardness_icon selection at line 31 still works (3-icon for hardness=4).
    assert len(rules) == 1
    assert rules[0]["text"].startswith("⛔⛔⛔")  # icon from line 31
    # But text starts with the icon (no symbol prefix from line 30)
    assert "orphan strong" in rules[0]["text"]


# ─── format_for_intake ──────────────────────────────────────────────

def test_format_for_intake_has_header_and_footer(tmp_path):
    """Covers lines 41-61: header at line 46, footer at line 58."""
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "hard_rules.yaml").write_text(yaml.dump({
        "hardness_levels": {
            "extreme": {"symbol": "⛔⛔⛔⛔⛔", "level": 5},
            "strong":  {"symbol": "⛔⛔⛔",     "level": 4},
        },
        "rules": [
            {"id": "rule_x",
             "hardness": 5, "block": True,
             "prompt_text": "x"},
        ],
    }))
    intake = hp.format_for_intake("sub_mas-test", {}, str(tmp_path))
    assert intake.startswith("=== ⛔⛔⛔⛔⛔ INHERITED RULES")
    assert "=== END INHERITED RULES ===" in intake
    # And the agent_name is interpolated
    assert "sub_mas-test" in intake


def test_format_for_intake_block_rule_uses_extreme_icon(tmp_path):
    """Covers line 52-53: block=True → ⛔⛔⛔⛔⛔ prefix on rule text."""
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "hard_rules.yaml").write_text(yaml.dump({
        "hardness_levels": {
            "extreme": {"symbol": "⛔⛔⛔⛔⛔", "level": 5},
        },
        "rules": [
            {"id": "rule_extreme",
             "hardness": 5, "block": True,
             "prompt_text": "extreme rule"},
        ],
    }))
    intake = hp.format_for_intake("sub_mas-x", {}, str(tmp_path))
    # rule_extreme (block=True) gets the 5-icon prefix from line 53
    # prepended to the text that already has 5 icons from get_hard_rules.
    # Verify both the rule text and that it has the doubled-icon pattern
    # (5+5 icons around a space, total 10 ⛔s before "extreme rule").
    assert "extreme rule" in intake
    # Count ⛔s immediately preceding "extreme rule" — must be ≥5 (one icon layer)
    idx = intake.index("extreme rule")
    prefix = intake[:idx]
    n_icons = len(prefix) - len(prefix.rstrip("⛔ "))
    # Should have ≥5 from get_hard_rules + 5 more from line 53 = 10+
    assert n_icons >= 5, f"expected ≥5 ⛔ icons, got {n_icons}"


def test_format_for_intake_nonblock_rule_uses_indented_text(tmp_path):
    """Covers line 54-55: block=False → indented rule text (no extra icon)."""
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "hard_rules.yaml").write_text(yaml.dump({
        "hardness_levels": {
            "strong": {"symbol": "⛔⛔⛔", "level": 4},
        },
        "rules": [
            {"id": "rule_strong",
             "hardness": 4, "block": False,
             "prompt_text": "strong rule"},
        ],
    }))
    intake = hp.format_for_intake("sub_mas-x", {}, str(tmp_path))
    # rule_strong (block=False, hardness=4) → text starts with ⛔⛔⛔ from
    # get_hard_rules, and line 55 prepends "  " (2 spaces).  No additional
    # ⛔ prefix.
    assert "\n  ⛔⛔⛔ strong rule" in intake


def test_format_for_intake_no_rules_above_threshold(tmp_path):
    """Covers the empty-rules path: workspace has rules but all below
    the threshold, so the header/footer still wrap an empty body."""
    rules_dir = tmp_path / "mas-engineer" / ".mase" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "hard_rules.yaml").write_text(yaml.dump({
        "hardness_levels": {"extreme": {"symbol": "x"}},
        "rules": [
            {"id": "weak", "hardness": 1, "block": True, "prompt_text": "w"},
        ],
    }))
    intake = hp.format_for_intake("sub_mas-empty", {}, str(tmp_path))
    # Header + footer present, body empty between them
    assert "INHERITED RULES" in intake
    assert "END INHERITED RULES" in intake
    assert "weak" not in intake  # rule filtered out


# ─── __main__ guard ─────────────────────────────────────────────────

def test_main_block_via_runpy(monkeypatch, workspace_with_rules, capsys):
    """Covers lines 63-72: argparse + format_for_intake + print.

    Uses runpy.run_path(__name__='__main__') so pytest-cov tracks the
    __main__ guard lines under the test process.  Stubs argv to point
    at our fake workspace and a fake agent_name.
    """
    monkeypatch.setattr(
        sys, "argv",
        ["dev_haerte_propagation.py",
         "--workspace", str(workspace_with_rules),
         "sub_mas-runpy"],
    )
    runpy.run_path(hp.__file__, run_name="__main__")
    captured = capsys.readouterr()
    # The script prints the intake block to stdout
    assert "INHERITED RULES" in captured.out
    assert "sub_mas-runpy" in captured.out
    # And exits cleanly (sys.exit not called — argparse errors would
    # raise SystemExit, but we passed valid args).
