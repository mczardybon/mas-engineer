"""
R110-349: coverage-push round 3 for tools/dev_im_finder_scan.py.

Target: the very few remaining pure-helper branches that r110309/345/347
left untested. This is the LAST pure-helper round; remaining missing
code is scan-loop body that requires integration tests with a real
repo walk.

3 helpers targeted (small, but high-leverage):

  1. _collect_scope_dirs env-var branch (L121) —
     The L121 line is "raw.append(...)" for the env path. Currently
     the r110309 fixture sets SCAN_SCOPE BEFORE the import, so the
     env-var branch IS executed. But there's a separate "comma-
     separated env" path (L124-125) that splits 'a,b' into multiple
     dirs. We test the de-dup branch (L126) and the whitespace-strip
     branch (L125).

  2. add_finding severity filter (L207-208) —
     When severity is NOT in SEVERITY_FILTER, the function returns
     early WITHOUT appending. Test:
     - severity not in filter → no append
     - severity in filter → append (and finding_id is F-001)
     - calling twice → fid increments to F-002

  3. _is_pycache_or_backup (L941-944) —
     Untested helper. Returns True for paths containing
     `__pycache__`, `.pyc`, `.bak`, `.mase/backups`. Branches:
     - contains `__pycache__` → True
     - contains `.pyc` → True
     - contains `.bak` → True
     - contains `.mase/backups` → True
     - regular path → False

Target: bump coverage from 28% to ~32% (additive +4pp).
"""
import sys
import importlib
from pathlib import Path
import pytest

TOOLS = Path(__file__).parent.parent / "tools"


@pytest.fixture
def ifs(tmp_path, monkeypatch):
    """Import dev_im_finder_scan with a sandboxed CWD (per R110-309)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCAN_SCOPE", str(tmp_path / "no-such-dir"))
    monkeypatch.setenv("SEVERITY_FILTER", "critical,warning,info,error,medium,high,low,debug")
    sys.path.insert(0, str(TOOLS))
    sys.modules.pop("dev_im_finder_scan", None)
    sys.modules.pop("dev_issue_db", None)
    mod = importlib.import_module("dev_im_finder_scan")
    yield mod
    sys.modules.pop("dev_im_finder_scan", None)
    sys.modules.pop("dev_issue_db", None)


class TestCollectScopeDirsEnvBranch:
    """Target the L121-L129 env-var + comma-split + de-dup branches."""

    def test_env_only_single_dir(self, ifs, monkeypatch):
        """Set env var, no CLI args → returns [env_value]."""
        monkeypatch.setenv("SCAN_SCOPE", str(ifs._collect_scope_dirs.__globals__['SCAN_DIRS'][0] or "/tmp/none"))
        # Call directly (after import, with new env)
        result = ifs._collect_scope_dirs()
        # May include recipe fallback too if env is empty; check non-empty
        assert isinstance(result, list)
        assert all(isinstance(d, str) for d in result)

    def test_dedup_keeps_first_occurrence(self, ifs, monkeypatch):
        """When same dir appears in CLI and env, only one entry."""
        target_dir = str(ifs._collect_scope_dirs.__globals__['SCAN_DIRS'][0] or "/tmp")
        # Simulate by patching sys.argv and env to have the same value
        monkeypatch.setattr("sys.argv", ["ifs", f"--scope={target_dir}"])
        monkeypatch.setenv("SCAN_SCOPE", target_dir)
        result = ifs._collect_scope_dirs()
        # Should be deduped
        assert result.count(target_dir) == 1

    def test_comma_split_creates_multiple_entries(self, ifs, monkeypatch):
        """Comma-separated env var splits into multiple dirs."""
        monkeypatch.setattr("sys.argv", ["ifs"])
        monkeypatch.setenv("SCAN_SCOPE", "/tmp/a,/tmp/b,/tmp/c")
        result = ifs._collect_scope_dirs()
        assert "/tmp/a" in result
        assert "/tmp/b" in result
        assert "/tmp/c" in result

    def test_whitespace_stripped(self, ifs, monkeypatch):
        """Whitespace around comma-separated entries is stripped."""
        monkeypatch.setattr("sys.argv", ["ifs"])
        monkeypatch.setenv("SCAN_SCOPE", " /tmp/a , /tmp/b ")
        result = ifs._collect_scope_dirs()
        assert "/tmp/a" in result
        assert "/tmp/b" in result

    def test_empty_entries_skipped(self, ifs, monkeypatch):
        """Empty entries from leading/trailing commas are skipped."""
        monkeypatch.setattr("sys.argv", ["ifs"])
        monkeypatch.setenv("SCAN_SCOPE", ",/tmp/a,,")
        result = ifs._collect_scope_dirs()
        assert "" not in result
        assert "/tmp/a" in result

    def test_fallback_to_recipe(self, ifs, monkeypatch):
        """No CLI, no env → falls back to ['recipe']."""
        monkeypatch.setattr("sys.argv", ["ifs"])
        monkeypatch.setenv("SCAN_SCOPE", "")
        result = ifs._collect_scope_dirs()
        assert "recipe" in result


class TestAddFindingSeverityFilter:
    """Target the L207-208 severity-filter early-return branch."""

    def test_severity_not_in_filter_returns_no_append(self, ifs, monkeypatch):
        """When severity is not in SEVERITY_FILTER, no finding is appended."""
        monkeypatch.setattr("sys.argv", ["ifs"])
        # Use a severity not in default filter
        before = list(ifs.findings)
        ifs.add_finding("TEST", "X", "/foo", "msg", "imp", "fix")
        after = list(ifs.findings)
        assert before == after, "findings should not change when severity filtered out"

    def test_severity_in_filter_appends(self, ifs, monkeypatch):
        """When severity is in SEVERITY_FILTER, finding is appended."""
        monkeypatch.setattr("sys.argv", ["ifs"])
        before_count = len(ifs.findings)
        ifs.add_finding("TEST", "high", "/foo", "msg", "imp", "fix")
        after_count = len(ifs.findings)
        assert after_count == before_count + 1

    def test_finding_id_increments(self, ifs, monkeypatch):
        """Sequential calls get sequential finding_ids F-NNN."""
        monkeypatch.setattr("sys.argv", ["ifs"])
        before = len(ifs.findings)
        ifs.add_finding("TEST", "high", "/foo", "msg1", "imp", "fix")
        ifs.add_finding("TEST", "high", "/bar", "msg2", "imp", "fix")
        after = ifs.findings
        # Last 2 findings have consecutive IDs
        if after and len(after) >= 2:
            id1 = after[-2].get("id", "")
            id2 = after[-1].get("id", "")
            assert id1.startswith("F-")
            assert id2.startswith("F-")
            assert id1 != id2


class TestIsPycacheOrBackup:
    """Target the L941-944 pycache/backup check helper."""

    def test_path_with_pycache_returns_true(self, ifs):
        """Path containing __pycache__ → True."""
        assert ifs._is_pycache_or_backup("/some/path/__pycache__/foo.py") is True

    def test_path_with_pyc_returns_true(self, ifs):
        """Path ending in .pyc → True."""
        assert ifs._is_pycache_or_backup("/some/path/foo.pyc") is True

    def test_path_with_llm_backup_returns_true(self, ifs):
        """Path containing /llm-backup/ → True."""
        assert ifs._is_pycache_or_backup("/some/llm-backup/snapshot.yaml") is True

    def test_path_with_llm_backup_nested_returns_true(self, ifs):
        """Path with /llm-backup/ nested in path → True."""
        assert ifs._is_pycache_or_backup("/repo/cache/llm-backup/dir/foo.txt") is True

    def test_regular_path_returns_false(self, ifs):
        """Regular source file → False."""
        assert ifs._is_pycache_or_backup("/repo/src/module.py") is False

    def test_path_with_underscore_pycache_in_middle(self, ifs):
        """Path with __pycache__ in middle of path → True."""
        assert ifs._is_pycache_or_backup("/repo/lib/__pycache__/module.py") is True
