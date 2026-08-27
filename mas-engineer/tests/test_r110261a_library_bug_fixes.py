"""
test_r110261a_library_bug_fixes.py — R110-261a regression tests.

Locks in the two library-bugs that the R110-261 coverage-sprint tests
revealed but didn't fix. If a future commit breaks the post-fix
behavior, these tests will fail and force a follow-up R-code.

Bugs fixed (in R110-261a, library code only):
  1. dev_fast_scan.scan_settings: per-condition `ok` made 1 good file
     report score=20.0. Now per-file pass/fail, max score=10.0.
  2. dev_intention_parser.analyse_intention: `requires_confirmation`
     only existed at r["restrictions"][...]. Now also exposed at
     r["requires_confirmation"] (top-level alias).

Not a library-bug, just docstring already correct in source:
  3. dev_category_drift: commit shape IS {hash,date,subject} in source.
     The R110-261 tests use the correct shape; no regression risk.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))


class TestDevFastScanBugFix:
    """Lock in: scan_settings per-file pass/fail, max score=10.0."""

    def setup_method(self):
        import dev_fast_scan  # noqa
        self.mod = dev_fast_scan

    def _write_yaml(self, tmp_path, name, settings):
        path = tmp_path / name
        path.write_text(f"settings:\n  timeout: {settings['timeout']}\n  max_turns: {settings['max_turns']}\n")
        return path

    def test_score_capped_at_10_for_perfect_file(self, tmp_path):
        """1 file with both conditions in range → score=10.0 (was 20.0 pre-fix)."""
        self._write_yaml(tmp_path, "good.yaml", {"timeout": 600, "max_turns": 50})
        f, score, total = self.mod.scan_settings(str(tmp_path))
        assert total == 1
        assert f == []
        assert score == 10.0, f"score must be 10.0 (max), was {score} pre-fix"

    def test_score_zero_for_perfectly_bad_file(self, tmp_path):
        """1 file with BOTH conditions out of range → 2 findings, score=0.0."""
        self._write_yaml(tmp_path, "bad.yaml", {"timeout": 100, "max_turns": 10})
        f, score, total = self.mod.scan_settings(str(tmp_path))
        assert total == 1
        # 2 findings: B1 (timeout<300) + B3 (max_turns<30)
        assert len(f) == 2
        types = {finding["type"] for finding in f}
        assert "B1" in types
        assert "B3" in types
        assert score == 0.0

    def test_score_5_for_half_good_corpus(self, tmp_path):
        """2 files, 1 good + 1 bad → ok=1, total=2, score=5.0."""
        self._write_yaml(tmp_path, "good.yaml", {"timeout": 600, "max_turns": 50})
        self._write_yaml(tmp_path, "bad.yaml", {"timeout": 100, "max_turns": 10})
        f, score, total = self.mod.scan_settings(str(tmp_path))
        assert total == 2
        assert score == 5.0, f"half-good corpus must score 5.0, got {score}"

    def test_score_capped_at_10_with_many_good_files(self, tmp_path):
        """Many good files → score still 10.0 (no overflow above max)."""
        for i in range(20):
            self._write_yaml(tmp_path, f"g{i}.yaml", {"timeout": 600, "max_turns": 50})
        f, score, total = self.mod.scan_settings(str(tmp_path))
        assert total == 20
        assert score == 10.0, f"score must cap at 10.0 even with 20 perfect files, got {score}"

    def test_one_good_condition_still_counts_as_zero(self, tmp_path):
        """1 file with timeout OK but max_turns out of range → not a 'pass'."""
        # Pre-fix: this would have incremented ok=1 for timeout, score=10.0
        # (misleading — file is NOT fully compliant).
        # Post-fix: ok=0 because BOTH must pass.
        self._write_yaml(tmp_path, "half.yaml", {"timeout": 600, "max_turns": 10})
        f, score, total = self.mod.scan_settings(str(tmp_path))
        assert total == 1
        assert score == 0.0, f"file with only half the conditions passing must score 0, got {score}"
        # 1 finding (B3 only — timeout was fine)
        assert len(f) == 1
        assert f[0]["type"] == "B3"


class TestDevIntentionParserBugFix:
    """Lock in: requires_confirmation available at top-level too."""

    def setup_method(self):
        import dev_intention_parser  # noqa
        self.mod = dev_intention_parser

    def test_top_level_alias_default(self):
        """Default behaviour: top-level requires_confirmation == True."""
        r = self.mod.analyse_intention("something vague")
        assert r["requires_confirmation"] is True
        assert r["restrictions"]["requires_confirmation"] is True
        # Both must agree
        assert r["requires_confirmation"] == r["restrictions"]["requires_confirmation"]

    def test_top_level_alias_autonomous(self):
        """Autonomous prompt → still requires_confirmation=True at top level."""
        r = self.mod.analyse_intention("I need an autonomous agent for X")
        assert r["type"] == "voll"
        assert r["requires_confirmation"] is True

    def test_top_level_alias_function(self):
        """Function prompt → still requires_confirmation=True at top level."""
        r = self.mod.analyse_intention("Add a function that does X")
        assert r["type"] == "intern"
        assert r["requires_confirmation"] is True

    def test_both_paths_stay_in_sync(self):
        """Top-level and restrictions.requires_confirmation must always agree."""
        for prompt in [
            "make a tool",
            "I need a new agent",
            "agent der foo for X",
            "autonomous please",
        ]:
            r = self.mod.analyse_intention(prompt)
            assert r["requires_confirmation"] == r["restrictions"]["requires_confirmation"], (
                f"top-level alias out of sync for prompt {prompt!r}"
            )
