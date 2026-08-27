"""
test_r110261_tools_coverage.py — R110-261 Coverage Sprint.

Target: bring mas-engineer's pytest coverage on the `tools/` directory from
~40% → ~100% by adding direct library-function tests for 10 small
single-purpose tools. Each test class covers one tool.

Strategy: test the library functions directly (not via subprocess CLI).
The CLI entry point is one-line `if __name__ == "__main__": main()` —
testing the library is what matters for coverage.

Tools covered in this file (Round 1, first 2 of 10):
  1. dev_evidence_sot       — SOT checker for evidence/directives
  2. dev_dashboard_data     — Dashboard data generator

Round 2 (4 more) → test_r110261_tools_coverage_round2.py
Round 3 (last 4) → test_r110261_tools_coverage_round3.py

Run with:
    python3 -m pytest tests/test_r110261_tools_coverage.py -v
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO_ROOT))


# ─── Tool 1: dev_evidence_sot.py ─────────────────────────────────────
class TestDevEvidenceSot:
    """Tests for tools/dev_evidence_sot.py library functions.

    Note: dev_evidence_sot resolves REPO_ROOT at IMPORT TIME (calls
    _resolve_repo_root() which uses os.getcwd()). Tests must therefore
    run from the actual mas-engineer repo root (conftest.py handles
    this — see R110-129). We monkeypatch REPO_ROOT for the
    check_*_working_tree tests that need an isolated fake tree.
    """

    @pytest.fixture(autouse=True)
    def _load_mod(self, request):
        """Import dev_evidence_sot from the PARENT directory (the repo-root
        that contains mas-engineer/), because _resolve_repo_root() requires
        that CWD layout.

        We temporarily chdir to the parent for the import + test, then
        restore. The actual REPO_ROOT in dev_evidence_sot is computed
        from os.getcwd() so this is the only way to make the import work.
        """
        import os as _os
        parent = REPO_ROOT.parent
        old_cwd = _os.getcwd()
        _os.chdir(str(parent))
        try:
            import dev_evidence_sot as mod
            request.instance.mod = mod
            yield mod
        finally:
            _os.chdir(old_cwd)

    def test_is_evidence_file_heuristic_true(self):
        """Files inside e2e-evidence-gen2/ are always evidence."""
        assert self.mod._is_evidence_file("logs/e2e-evidence-gen2/foo.md")
        assert self.mod._is_evidence_file("foo/logs/e2e-evidence-gen2/bar.log")

    def test_is_evidence_file_convention(self):
        """Files matching evidence naming conventions are flagged."""
        assert self.mod._is_evidence_file("mas-engineer/logs/R110-FOO-EVIDENCE.md")
        assert self.mod._is_evidence_file("mas-engineer/logs/session-report-X.md")

    def test_is_evidence_file_false(self):
        """Normal source files are not evidence."""
        assert not self.mod._is_evidence_file("tools/dev_foo.py")
        assert not self.mod._is_evidence_file("recipe/sub/sub_mas-bar.yaml")

    def test_is_any_file_in_anti_sot_logs(self):
        """ANY file under mas-engineer/logs/ is a violation (post-R110-257)."""
        assert self.mod._is_any_file_in_anti_sot_logs("mas-engineer/logs/anything.txt")
        assert self.mod._is_any_file_in_anti_sot_logs("mas-engineer/logs/sub/foo.md")
        # SOT location is fine
        assert not self.mod._is_any_file_in_anti_sot_logs("logs/e2e-evidence-gen2/x.md")

    def test_sot_constants(self):
        """The SOT prefixes are the post-R110-257 single source of truth."""
        assert self.mod.SOT_EVIDENCE_PREFIX == "logs/e2e-evidence-gen2/"
        assert self.mod.SOT_DIRECTIVES_PREFIX == "mas-engineer/.mase/directives/"
        assert self.mod.ANTI_SOT_DIRECTIVES == "mas-engineer/.directives/"
        assert self.mod.ANTI_SOT_EVIDENCE == "mas-engineer/logs/"

    def test_check_evidence_sot_working_tree_clean(self, tmp_path):
        """When no anti-SOT files exist, violations list is empty.

        Runs in parent-CWD (set by _load_mod fixture). Uses a tmp_path
        as the 'fake repo root' via monkeypatch on the mod's REPO_ROOT.
        """
        repo = tmp_path / "fake_repo"
        repo.mkdir()
        # The mod's REPO_ROOT was resolved at import time. We patch it.
        self.mod.REPO_ROOT = repo
        # _git also uses mod.REPO_ROOT via cwd default
        violations = self.mod.check_evidence_sot_working_tree()
        assert isinstance(violations, list)
        assert violations == []

    def test_check_directives_sot_working_tree_clean(self, tmp_path):
        """Clean tree → no directive violations."""
        repo = tmp_path / "fake_repo"
        repo.mkdir()
        self.mod.REPO_ROOT = repo
        violations = self.mod.check_directives_sot_working_tree()
        assert isinstance(violations, list)
        assert violations == []


# ─── Tool 2: dev_dashboard_data.py ───────────────────────────────────
class TestDevDashboardData:
    """Tests for tools/dev_dashboard_data.py library functions."""

    def setup_method(self):
        import dev_dashboard_data as mod
        self.mod = mod

    def test_load_json_existing(self, tmp_path):
        """load_json reads existing JSON file."""
        f = tmp_path / "data.json"
        f.write_text('{"a": 1, "b": [2, 3]}')
        result = self.mod.load_json(str(f))
        assert result == {"a": 1, "b": [2, 3]}

    def test_load_json_missing(self, tmp_path):
        """load_json returns default for missing file."""
        result = self.mod.load_json(str(tmp_path / "missing.json"), default={})
        assert result == {}

    def test_load_json_corrupt(self, tmp_path):
        """load_json returns default for corrupt JSON (graceful)."""
        f = tmp_path / "bad.json"
        f.write_text("not json {{{")
        result = self.mod.load_json(str(f), default={"fallback": True})
        assert result == {"fallback": True}

    def test_yaml_load_missing(self, tmp_path):
        """yaml_load returns empty dict when PyYAML not present or file missing."""
        result = self.mod.yaml_load(str(tmp_path / "missing.yaml"))
        assert result == {}

    def test_yaml_load_real(self, tmp_path):
        """yaml_load reads a real YAML file (if PyYAML is installed)."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("PyYAML not installed")
        f = tmp_path / "data.yaml"
        f.write_text("k1: v1\nk2:\n  - a\n  - b\n")
        result = self.mod.yaml_load(str(f))
        assert result == {"k1": "v1", "k2": ["a", "b"]}

    def test_get_git_log_returns_list(self, tmp_path):
        """get_git_log returns a list of strings (or [] outside a repo)."""
        # Run inside REPO_ROOT (which IS a git repo)
        result = self.mod.get_git_log(str(REPO_ROOT), count=3)
        assert isinstance(result, list)
        if result:  # if we have commits, verify shape
            assert all(isinstance(line, str) for line in result)
            assert len(result) <= 3

    def test_phase1_topics_summary_empty(self, tmp_path, monkeypatch):
        """_phase1_topics_summary with empty topics dict → all 3 keys, all zeros.

        R110-261 discovery: last_msg is NOT None if the live MQ root
        has real pending/done messages on those topics (the helper is
        best-effort and reads from disk). We isolate via MAS_MQ_ROOT to
        an empty tmp dir to make the test deterministic.
        """
        empty_mq = tmp_path / "empty_mq"
        empty_mq.mkdir()
        monkeypatch.setenv("MAS_MQ_ROOT", str(empty_mq))
        result = self.mod._phase1_topics_summary({})
        assert isinstance(result, dict)
        assert "im.finding.created" in result
        assert "monitor.health.degraded" in result
        assert "phoenix.recovery.completed" in result
        for topic_entry in result.values():
            assert topic_entry["depth"] == 0
            assert topic_entry["completed_total"] == 0
            assert topic_entry["last_msg"] is None

    def test_phase1_topics_summary_with_data(self):
        """_phase1_topics_summary surfaces depth/completed_total from mq.stats()."""
        # mq.stats() keys topics by sanitized name
        safe = lambda t: "".join(c if c.isalnum() or c in "_-" else "_" for c in t)
        fake_topics = {
            safe("im.finding.created"): {
                "depth": 5,
                "completed_total": 12,
                "current_p95_lag_ms": 200,
                "dlq_count_for_topic": 0,
            }
        }
        result = self.mod._phase1_topics_summary(fake_topics)
        assert result["im.finding.created"]["depth"] == 5
        assert result["im.finding.created"]["completed_total"] == 12
        # Others still default to 0
        assert result["monitor.health.degraded"]["depth"] == 0

    def test_shell_helper_safe(self):
        """shell() runs a safe command without raising."""
        result = self.mod.shell("echo hello")
        assert result == "hello"

    def test_shell_helper_timeout_safe(self):
        """shell() swallows errors on bad commands."""
        # Invalid command — shell returns '' instead of raising
        result = self.mod.shell("this_command_does_not_exist_xyz_12345", timeout=3)
        assert result == ""
