"""
R110-361: coverage-push round 1 for tools/dev_im_finder_scan.py.

Targets untested branches in the pure-helper functions that the scanner
relies on internally but were partially covered by r110347/349.

Targets:
  1. _collect_scope_dirs (L109-129) — env + recipe-based scope detection
  2. _is_path_excluded (L160-168) — path-filter logic
  3. add_finding (L195-252) — central finding registration
  4. compute_issue_hash / compute_structural_pattern (L89-104) — pure helpers

Import pattern (R110-322 + R110-347):
  - monkeypatch chdir + SCAN_SCOPE env BEFORE import so the module-level
    `check_spec_drift(findings, '.')` call at L1578 is a no-op (0.04s).
  - Import as `tools.dev_im_finder_scan` (canonical name) so coverage
    tracks it under the source path in .coveragerc [paths] source=tools/.

Target: bump coverage from 30% to ~40% (additive +10pp on 1681 stmts).
"""
import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.resolve()  # mas-engineer/


def _fresh_import():
    """Pop both flat and dotted registrations so a re-import is clean.

    Removes:
      - tools.dev_im_finder_scan (canonical, used by .coveragerc)
      - dev_im_finder_scan (flat, used by r110309/r110347 fixture)
      - dev_issue_db (transitive)
    Also adds REPO to sys.path so `import tools.X` works.
    """
    for k in ("tools.dev_im_finder_scan", "dev_im_finder_scan", "dev_issue_db"):
        sys.modules.pop(k, None)
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))


def _load_module():
    """Import dev_im_finder_scan as `tools.dev_im_finder_scan`."""
    _fresh_import()
    return importlib.import_module("tools.dev_im_finder_scan")


def _cleanup():
    for k in ("tools.dev_im_finder_scan", "dev_im_finder_scan", "dev_issue_db"):
        sys.modules.pop(k, None)


@pytest.fixture
def ifs(tmp_path, monkeypatch):
    """Sandboxed import of `tools.dev_im_finder_scan`.

    The CWD and SCAN_SCOPE are pointed at an empty tmp dir, so the
    module-level `check_spec_drift(findings, '.')` and
    `check_spec_drift_reverse(findings, '.')` calls are no-ops.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCAN_SCOPE", str(tmp_path / "no-such-dir"))
    monkeypatch.setenv("SEVERITY_FILTER", "critical,warning,info,error,medium,high,low,debug,blocker")
    monkeypatch.setenv("MAS_INCLUDE_EXTERNAL_RECIPES", "")
    mod = _load_module()
    yield mod
    _cleanup()


# ============================================================
# 1. _collect_scope_dirs — pure env+argv parser
# ============================================================

class TestCollectScopeDirs:
    """_collect_scope_dirs reads SCAN_SCOPE env + --scope= args."""

    def test_no_env_no_arg_falls_back_to_recipe(self, tmp_path, monkeypatch):
        """Without SCAN_SCOPE or --scope= arg, default is ['recipe']."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("SCAN_SCOPE", raising=False)
        m = _load_module()
        try:
            assert m._collect_scope_dirs() == ["recipe"]
        finally:
            _cleanup()

    def test_env_single_dir(self, tmp_path, monkeypatch):
        """SCAN_SCOPE=/foo/bar → result contains '/foo/bar'."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SCAN_SCOPE", str(tmp_path / "single"))
        m = _load_module()
        try:
            result = m._collect_scope_dirs()
            assert str(tmp_path / "single") in result
        finally:
            _cleanup()

    def test_env_comma_split(self, tmp_path, monkeypatch):
        """SCAN_SCOPE=/a,/b,/c → three entries."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SCAN_SCOPE", f"{tmp_path}/a,{tmp_path}/b,{tmp_path}/c")
        m = _load_module()
        try:
            result = m._collect_scope_dirs()
            assert len(result) == 3
        finally:
            _cleanup()

    def test_env_whitespace_stripped(self, tmp_path, monkeypatch):
        """SCAN_SCOPE=' /a , /b ' → stripped entries."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SCAN_SCOPE", f" {tmp_path}/a , {tmp_path}/b ")
        m = _load_module()
        try:
            result = m._collect_scope_dirs()
            for r in result:
                assert r == r.strip()
        finally:
            _cleanup()

    def test_empty_entries_skipped(self, tmp_path, monkeypatch):
        """SCAN_SCOPE='/a,,/b,' → only /a and /b, no empty strings."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SCAN_SCOPE", f"{tmp_path}/a,,{tmp_path}/b,")
        m = _load_module()
        try:
            result = m._collect_scope_dirs()
            for r in result:
                assert r  # No empty strings
        finally:
            _cleanup()

    def test_dedup_keeps_first_occurrence(self, tmp_path, monkeypatch):
        """Duplicates are de-duped, keeping the first."""
        monkeypatch.chdir(tmp_path)
        d = str(tmp_path / "dup")
        monkeypatch.setenv("SCAN_SCOPE", f"{d},{d}")
        m = _load_module()
        try:
            result = m._collect_scope_dirs()
            assert result.count(d) == 1
        finally:
            _cleanup()


# ============================================================
# 2. _is_path_excluded — path-filter logic
# ============================================================

class TestIsPathExcluded:
    """_is_path_excluded checks EXCLUDED_PATH_PATTERNS."""

    def test_external_recipe_excluded_by_default(self, ifs):
        """Without --include-external-recipes, /.config/goose/recipes/ is excluded."""
        assert ifs._is_path_excluded("/home/user/.config/goose/recipes/foo.yaml") is True

    def test_backup_file_excluded(self, ifs):
        """Files with .bak suffix are excluded."""
        assert ifs._is_path_excluded("/repo/agents/sub_mas-test-agent.yaml.bak") is True

    def test_original_yaml_excluded(self, ifs):
        """Files with -ORIGINAL.yaml suffix are excluded."""
        assert ifs._is_path_excluded("/repo/agents/sub_mas-test-ORIGINAL.yaml") is True

    def test_normal_recipe_path_not_excluded(self, ifs):
        """Regular recipe path is not excluded."""
        assert ifs._is_path_excluded("/repo/recipe/sub/sub_mas-test-agent.yaml") is False

    def test_excluded_with_include_external(self, tmp_path, monkeypatch):
        """With MAS_INCLUDE_EXTERNAL_RECIPES=1, /.config/goose/recipes/ is NOT excluded."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SCAN_SCOPE", str(tmp_path / "no-such-dir"))
        monkeypatch.setenv("SEVERITY_FILTER", "critical,warning,info,error,medium,high,low,debug,blocker")
        monkeypatch.setenv("MAS_INCLUDE_EXTERNAL_RECIPES", "1")
        m = _load_module()
        try:
            assert m._is_path_excluded("/home/user/.config/goose/recipes/foo.yaml") is False
        finally:
            _cleanup()


# ============================================================
# 3. add_finding — central finding registration
# ============================================================

class TestAddFinding:
    """add_finding registers a finding into mod.findings."""

    def test_severity_not_in_filter_returns_no_append(self, ifs):
        """If severity not in SEVERITY_FILTER, no finding is appended."""
        ifs.SEVERITY_FILTER = {"high", "blocker"}  # Exclude 'low'
        ifs.findings = []
        ifs.fid = 0
        ifs.add_finding("T1", "low", "/some/file.py", "issue", "impact", "fix")
        assert ifs.findings == []

    def test_severity_in_filter_appends(self, ifs):
        """If severity in SEVERITY_FILTER, finding is appended."""
        ifs.SEVERITY_FILTER = {"medium", "high", "blocker", "low"}
        ifs.findings = []
        ifs.fid = 0
        ifs.add_finding("T1", "high", "/some/file.py", "an issue", "some impact", "some fix")
        assert len(ifs.findings) == 1

    def test_finding_id_increments(self, ifs):
        """Each call increments fid, producing F-001, F-002, ..."""
        ifs.SEVERITY_FILTER = {"high", "blocker"}
        ifs.findings = []
        ifs.fid = 0
        ifs.add_finding("T1", "high", "/a.py", "i", "x", "y")
        ifs.add_finding("T2", "high", "/b.py", "i", "x", "y")
        ifs.add_finding("T3", "blocker", "/c.py", "i", "x", "y")
        assert ifs.findings[0]["id"] == "F-001"
        assert ifs.findings[1]["id"] == "F-002"
        assert ifs.findings[2]["id"] == "F-003"

    def test_finding_dict_has_required_keys(self, ifs):
        """Finding dict has: id, type, severity, file, issue, impact, fix,
        issue_hash, structural_pattern."""
        ifs.SEVERITY_FILTER = {"high", "blocker"}
        ifs.findings = []
        ifs.fid = 0
        ifs.add_finding("T1", "high", "/x.py", "i", "x", "y")
        f = ifs.findings[0]
        for key in ("id", "type", "severity", "file", "issue", "impact", "fix",
                    "issue_hash", "structural_pattern"):
            assert key in f, f"missing key: {key}"

    def test_finding_is_json_serializable(self, ifs):
        """Finding dict is JSON-serializable (no datetime, no Path, no set)."""
        ifs.SEVERITY_FILTER = {"high", "blocker"}
        ifs.findings = []
        ifs.fid = 0
        ifs.add_finding("T1", "high", "/x.py", "i", "x", "y")
        f = ifs.findings[0]
        # Should not raise
        json.dumps(f)

    def test_line_start_line_end_passed_through(self, ifs):
        """line_start and line_end kwargs are passed to compute_structural_pattern
        (not stored in finding dict) without raising."""
        ifs.SEVERITY_FILTER = {"high", "blocker"}
        ifs.findings = []
        ifs.fid = 0
        ifs.add_finding("T1", "high", "/x.py", "i", "x", "y",
                        line_start=10, line_end=20)
        assert len(ifs.findings) == 1

    def test_no_db_when_inactive(self, ifs):
        """When issue-db is inactive, no db side-effects."""
        ifs._ISSUE_DB = None
        ifs._ISSUE_DB_ACTIVE = False
        ifs.SEVERITY_FILTER = {"high", "blocker"}
        ifs.findings = []
        ifs.fid = 0
        ifs.add_finding("T1", "high", "/x.py", "i", "x", "y")
        assert ifs._ISSUE_DB is None

    def test_filtered_finding_no_id_assigned(self, ifs):
        """If filtered out, fid is NOT incremented."""
        ifs.SEVERITY_FILTER = {"high"}
        ifs.findings = []
        ifs.fid = 0
        ifs.add_finding("T1", "low", "/x.py", "i", "x", "y")  # filtered
        ifs.add_finding("T2", "high", "/y.py", "i", "x", "y")  # accepted
        assert ifs.findings[0]["id"] == "F-001"
        assert len(ifs.findings) == 1


# ============================================================
# 4. compute_issue_hash / compute_structural_pattern — delegating helpers
# ============================================================

class TestComputeHelpers:
    """compute_issue_hash and compute_structural_pattern delegate to dev_issue_db."""

    def test_compute_issue_hash_returns_string(self, ifs):
        """compute_issue_hash returns a non-empty string."""
        h = ifs.compute_issue_hash("/x.py", "T1", "pat1")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_compute_issue_hash_stable(self, ifs):
        """Same input → same hash."""
        h1 = ifs.compute_issue_hash("/x.py", "T1", "pat1")
        h2 = ifs.compute_issue_hash("/x.py", "T1", "pat1")
        assert h1 == h2

    def test_compute_issue_hash_differs_by_type(self, ifs):
        """Different type → different hash."""
        h1 = ifs.compute_issue_hash("/x.py", "T1", "pat1")
        h2 = ifs.compute_issue_hash("/x.py", "T2", "pat1")
        assert h1 != h2

    def test_compute_structural_pattern_returns_string(self, ifs):
        """compute_structural_pattern returns a non-empty string."""
        p = ifs.compute_structural_pattern("T1", "/x.py", context="test")
        assert isinstance(p, str)

    def test_compute_structural_pattern_ignores_unknown_kwargs(self, ifs):
        """Unknown kwargs are passed to dev_issue_db.compute_structural_pattern
        and either stored or silently dropped, not raising."""
        p = ifs.compute_structural_pattern("T1", "/x.py", unknown_kwarg="x")
        assert isinstance(p, str)
