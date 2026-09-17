"""
test_r110298_evidence_sot_library.py — R110-298 Coverage Sprint
for dev_evidence_sot.py.

Target: dev_evidence_sot.py (351 lines, 162 stmts).
R110-257 added 7 integration tests (test_dev_evidence_sot.py) that run
the tool as a subprocess — those cover main() + the high-level SOT
detection flow but exercise the 8 check_* helper functions only
indirectly via subprocess.

R110-298 imports the module as a library and tests the 8 check_*
functions + scan_history_for_violators + _is_evidence_file +
_is_any_file_in_anti_sot_logs DIRECTLY (no subprocess), so that
coverage.py can attribute hits to the right lines.

Library functions covered (8 helpers + main helpers):
  - _is_evidence_file                  (8 tests)
  - _is_any_file_in_anti_sot_logs      (4 tests)
  - check_evidence_sot_working_tree    (3 tests: empty, anti_sot file, mixed)
  - check_evidence_sot_git_index       (2 tests: empty, tracked anti_sot)
  - check_directives_sot_working_tree  (3 tests: empty, anti_sot, non-md)
  - check_directives_sot_git_index     (2 tests: empty, tracked anti_sot)
  - check_sot_evidence_dir_health      (3 tests: exists, missing, file)
  - check_sot_directives_dir_health    (3 tests: exists, missing, file)
  - scan_history_for_violators         (2 tests: success, git log error)
  - main() with --git + --history      (4 tests: end-to-end CLI)

Total: 34 new tests.

Pitfall (R110-78 cat-3): the tool reads REPO_ROOT at MODULE-IMPORT TIME
via _resolve_repo_root() — so this test file MUST be importable from
the correct cwd. The fixture monkeypatches cwd to a tmp_path that has
a mas-engineer/ subdir before importing the module.
"""
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
TOOL = REPO_ROOT / "mas-engineer" / "tools" / "dev_evidence_sot.py"


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Create a fake repo-root with mas-engineer/ subdir + empty SOT dirs.

    Returns the fake REPO_ROOT. Module re-import happens INSIDE each test
    because the module reads REPO_ROOT at import time.
    """
    fake = tmp_path / "fake_repo"
    fake.mkdir()
    (fake / "mas-engineer").mkdir()
    (fake / "mas-engineer" / ".mase" / "directives").mkdir(parents=True)
    (fake / "logs" / "e2e-evidence-gen2").mkdir(parents=True)
    # Init git so _git() works
    subprocess.run(["git", "init", "-q"], cwd=str(fake), check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=str(fake), check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(fake), check=True)
    # An initial commit so HEAD exists
    (fake / "README").write_text("init")
    subprocess.run(["git", "add", "README"], cwd=str(fake), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(fake), check=True)
    return fake


def _import_tool_from(cwd):
    """Import dev_evidence_sot as a library with REPO_ROOT pointing to cwd.

    The tool does REPO_ROOT = _resolve_repo_root() at module level, so
    cwd must contain a mas-engineer/ subdir. Returns the loaded module.
    """
    import os
    old = os.getcwd()
    try:
        os.chdir(cwd)
        if "dev_evidence_sot" in sys.modules:
            del sys.modules["dev_evidence_sot"]
        sys.path.insert(0, str(TOOL.parent))
        import dev_evidence_sot
        return dev_evidence_sot
    finally:
        os.chdir(old)


# ─────────────────────────────────────────────────────────────────────
# Pure-function tests (no fixture, no IO)
# ─────────────────────────────────────────────────────────────────────

def test_is_evidence_file_gen2_dir():
    """e2e-evidence-gen2 in path → True."""
    assert _import_tool_from(REPO_ROOT)._is_evidence_file("logs/e2e-evidence-gen2/R110-200.md")


def test_is_evidence_file_gen2_in_middle():
    """e2e-evidence-gen2 in middle of path → True."""
    assert _import_tool_from(REPO_ROOT)._is_evidence_file("foo/e2e-evidence-gen2/bar.md")


def test_is_evidence_file_evidence_md_suffix():
    """-EVIDENCE.md suffix → True (R110-257 convention)."""
    assert _import_tool_from(REPO_ROOT)._is_evidence_file("mas-engineer/logs/R110-X-EVIDENCE.md")


def test_is_evidence_file_session_report():
    """session-report substring → True."""
    assert _import_tool_from(REPO_ROOT)._is_evidence_file("logs/session-report-2026.md")


def test_is_evidence_file_random_md():
    """Regular .md file → False."""
    assert not _import_tool_from(REPO_ROOT)._is_evidence_file("mas-engineer/STATUS.md")


def test_is_evidence_file_random_log():
    """Regular .log file → False."""
    assert not _import_tool_from(REPO_ROOT)._is_evidence_file("logs/random.log")


def test_is_evidence_file_case_insensitive():
    """e2e-EVIDENCE-GEN2 (uppercase) → True (case-insensitive)."""
    assert _import_tool_from(REPO_ROOT)._is_evidence_file("logs/e2e-EVIDENCE-GEN2/x.md")


def test_is_evidence_file_evidence_in_name():
    """File with 'evidence' in name → True (R110-257 convention)."""
    assert _import_tool_from(REPO_ROOT)._is_evidence_file("logs/R110-evidence-archive.md")


def test_is_any_file_in_anti_sot_logs_true():
    """Path under mas-engineer/logs/ → True (FULLY forbidden)."""
    assert _import_tool_from(REPO_ROOT)._is_any_file_in_anti_sot_logs("mas-engineer/logs/foo.md")


def test_is_any_file_in_anti_sot_logs_nested():
    """Nested under mas-engineer/logs/ → True."""
    assert _import_tool_from(REPO_ROOT)._is_any_file_in_anti_sot_logs("mas-engineer/logs/sub/x.txt")


def test_is_any_file_in_anti_sot_logs_sot_false():
    """Path under REPO-ROOT logs/ → False (SOT location)."""
    assert not _import_tool_from(REPO_ROOT)._is_any_file_in_anti_sot_logs("logs/e2e-evidence-gen2/x.md")


def test_is_any_file_in_anti_sot_logs_random_false():
    """Random path → False."""
    assert not _import_tool_from(REPO_ROOT)._is_any_file_in_anti_sot_logs("mas-engineer/STATUS.md")


# ─────────────────────────────────────────────────────────────────────
# check_evidence_sot_working_tree
# ─────────────────────────────────────────────────────────────────────

def test_check_evidence_sot_working_tree_empty(fake_repo):
    """No untracked, staged, or unstaged files at anti-SOT paths → empty."""
    mod = _import_tool_from(fake_repo)
    assert mod.check_evidence_sot_working_tree() == []


def test_check_evidence_sot_working_tree_violation(fake_repo):
    """File at mas-engineer/logs/ → violation."""
    (fake_repo / "mas-engineer" / "logs").mkdir(exist_ok=True)
    (fake_repo / "mas-engineer" / "logs" / "bad.md").write_text("violation")
    mod = _import_tool_from(fake_repo)
    violations = mod.check_evidence_sot_working_tree()
    assert any("mas-engineer/logs/bad.md" in v for v in violations)


def test_check_evidence_sot_working_tree_sot_clean(fake_repo):
    """File at SOT location (REPO-ROOT logs/) → no violation."""
    (fake_repo / "logs" / "e2e-evidence-gen2" / "good.md").write_text("ok")
    mod = _import_tool_from(fake_repo)
    assert mod.check_evidence_sot_working_tree() == []


# ─────────────────────────────────────────────────────────────────────
# check_evidence_sot_git_index
# ─────────────────────────────────────────────────────────────────────

def test_check_evidence_sot_git_index_empty(fake_repo):
    """No tracked files at anti-SOT → empty."""
    mod = _import_tool_from(fake_repo)
    assert mod.check_evidence_sot_git_index() == []


def test_check_evidence_sot_git_index_tracked_violation(fake_repo):
    """Tracked file at mas-engineer/logs/ → violation (bypass scenario)."""
    (fake_repo / "mas-engineer" / "logs").mkdir(exist_ok=True)
    (fake_repo / "mas-engineer" / "logs" / "tracked-bad.md").write_text("violation")
    subprocess.run(["git", "add", "-f", "mas-engineer/logs/tracked-bad.md"],
                    cwd=str(fake_repo), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "test"],
                    cwd=str(fake_repo), check=True)
    mod = _import_tool_from(fake_repo)
    violations = mod.check_evidence_sot_git_index()
    assert any("mas-engineer/logs/tracked-bad.md" in v for v in violations)


# ─────────────────────────────────────────────────────────────────────
# check_directives_sot_working_tree
# ─────────────────────────────────────────────────────────────────────

def test_check_directives_sot_working_tree_empty(fake_repo):
    """No anti-SOT directives → empty."""
    mod = _import_tool_from(fake_repo)
    assert mod.check_directives_sot_working_tree() == []


def test_check_directives_sot_working_tree_md_violation(fake_repo):
    """File at mas-engineer/.directives/ (anti-SOT) → violation."""
    (fake_repo / "mas-engineer" / ".directives").mkdir(exist_ok=True)
    (fake_repo / "mas-engineer" / ".directives" / "R999.md").write_text("violation")
    mod = _import_tool_from(fake_repo)
    violations = mod.check_directives_sot_working_tree()
    assert any("mas-engineer/.directives/R999.md" in v for v in violations)


def test_check_directives_sot_working_tree_non_md_ignored(fake_repo):
    """Non-md file at anti-SOT directives path → not flagged (only .md counts)."""
    (fake_repo / "mas-engineer" / ".directives").mkdir(exist_ok=True)
    (fake_repo / "mas-engineer" / ".directives" / "ignore.txt").write_text("ok")
    mod = _import_tool_from(fake_repo)
    # Non-md files are NOT violations per R110-257 spec
    assert mod.check_directives_sot_working_tree() == []


# ─────────────────────────────────────────────────────────────────────
# check_directives_sot_git_index
# ─────────────────────────────────────────────────────────────────────

def test_check_directives_sot_git_index_empty(fake_repo):
    """No tracked anti-SOT directives → empty."""
    mod = _import_tool_from(fake_repo)
    assert mod.check_directives_sot_git_index() == []


def test_check_directives_sot_git_index_tracked_violation(fake_repo):
    """Tracked .md at anti-SOT directives → violation."""
    (fake_repo / "mas-engineer" / ".directives").mkdir(exist_ok=True)
    (fake_repo / "mas-engineer" / ".directives" / "tracked-bad.md").write_text("v")
    subprocess.run(["git", "add", "-f", "mas-engineer/.directives/tracked-bad.md"],
                    cwd=str(fake_repo), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "test"],
                    cwd=str(fake_repo), check=True)
    mod = _import_tool_from(fake_repo)
    violations = mod.check_directives_sot_git_index()
    assert any("mas-engineer/.directives/tracked-bad.md" in v for v in violations)


# ─────────────────────────────────────────────────────────────────────
# check_sot_evidence_dir_health
# ─────────────────────────────────────────────────────────────────────

def test_check_sot_evidence_dir_health_ok(fake_repo):
    """SOT evidence dir exists → empty (healthy)."""
    mod = _import_tool_from(fake_repo)
    assert mod.check_sot_evidence_dir_health() == []


def test_check_sot_evidence_dir_health_missing(fake_repo):
    """SOT evidence dir missing → 'missing' violation."""
    import shutil
    shutil.rmtree(fake_repo / "logs" / "e2e-evidence-gen2")
    mod = _import_tool_from(fake_repo)
    violations = mod.check_sot_evidence_dir_health()
    assert any("missing" in v for v in violations)


def test_check_sot_evidence_dir_health_not_a_dir(fake_repo):
    """SOT path exists as file (not dir) → 'not-a-dir' violation."""
    import shutil
    shutil.rmtree(fake_repo / "logs" / "e2e-evidence-gen2")
    (fake_repo / "logs" / "e2e-evidence-gen2").write_text("file")
    mod = _import_tool_from(fake_repo)
    violations = mod.check_sot_evidence_dir_health()
    assert any("not-a-dir" in v for v in violations)


# ─────────────────────────────────────────────────────────────────────
# check_sot_directives_dir_health
# ─────────────────────────────────────────────────────────────────────

def test_check_sot_directives_dir_health_ok(fake_repo):
    """SOT directives dir exists → empty (healthy)."""
    mod = _import_tool_from(fake_repo)
    assert mod.check_sot_directives_dir_health() == []


def test_check_sot_directives_dir_health_missing(fake_repo):
    """SOT directives dir missing → 'missing' violation."""
    import shutil
    shutil.rmtree(fake_repo / "mas-engineer" / ".mase" / "directives")
    mod = _import_tool_from(fake_repo)
    violations = mod.check_sot_directives_dir_health()
    assert any("missing" in v for v in violations)


def test_check_sot_directives_dir_health_not_a_dir(fake_repo):
    """SOT path exists as file (not dir) → 'not-a-dir' violation."""
    import shutil
    shutil.rmtree(fake_repo / "mas-engineer" / ".mase" / "directives")
    (fake_repo / "mas-engineer" / ".mase" / "directives").write_text("file")
    mod = _import_tool_from(fake_repo)
    violations = mod.check_sot_directives_dir_health()
    assert any("not-a-dir" in v for v in violations)


# ─────────────────────────────────────────────────────────────────────
# scan_history_for_violators
# ─────────────────────────────────────────────────────────────────────

def test_scan_history_no_violators(fake_repo):
    """Clean history → 0 counts, empty lists."""
    mod = _import_tool_from(fake_repo)
    result = mod.scan_history_for_violators()
    assert result["anti_sot_evidence_count"] == 0
    assert result["anti_sot_directives_count"] == 0
    assert result["anti_sot_evidence_files_ever_added"] == []
    assert result["anti_sot_directives_files_ever_added"] == []


def test_scan_history_with_violators(fake_repo):
    """History with anti-SOT files → those files reported."""
    (fake_repo / "mas-engineer" / "logs").mkdir(exist_ok=True)
    (fake_repo / "mas-engineer" / "logs" / "historical-bad.md").write_text("v")
    subprocess.run(["git", "add", "-f", "mas-engineer/logs/historical-bad.md"],
                    cwd=str(fake_repo), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "test"],
                    cwd=str(fake_repo), check=True)
    mod = _import_tool_from(fake_repo)
    result = mod.scan_history_for_violators()
    assert result["anti_sot_evidence_count"] >= 1
    assert any("historical-bad.md" in f for f in result["anti_sot_evidence_files_ever_added"])


# ─────────────────────────────────────────────────────────────────────
# main() CLI tests (--json, --git, --history)
# ─────────────────────────────────────────────────────────────────────

def test_main_json_clean(fake_repo, capsys, monkeypatch):
    """main() with --json + clean state → ok=True, violation_count=0."""
    monkeypatch.chdir(fake_repo)
    sys.path.insert(0, str(TOOL.parent))
    if "dev_evidence_sot" in sys.modules:
        del sys.modules["dev_evidence_sot"]
    import dev_evidence_sot
    monkeypatch.setattr(sys, "argv", ["dev_evidence_sot.py", "--json"])
    dev_evidence_sot.main()
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["ok"] is True
    assert out["violation_count"] == 0


def test_main_json_violation(fake_repo, capsys, monkeypatch):
    """main() with --json + violation → ok=False, violation_count>=1."""
    (fake_repo / "mas-engineer" / "logs").mkdir(exist_ok=True)
    (fake_repo / "mas-engineer" / "logs" / "bad.md").write_text("v")
    monkeypatch.chdir(fake_repo)
    sys.path.insert(0, str(TOOL.parent))
    if "dev_evidence_sot" in sys.modules:
        del sys.modules["dev_evidence_sot"]
    import dev_evidence_sot
    monkeypatch.setattr(sys, "argv", ["dev_evidence_sot.py", "--json"])
    dev_evidence_sot.main()
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["ok"] is False
    assert out["violation_count"] >= 1
    # checks schema is dict-of-lists, not list-of-dicts
    assert any("mas-engineer/logs/bad.md" in v
               for vl in out["checks"].values() if isinstance(vl, list)
               for v in vl)


def test_main_strict_violation_exit_1(fake_repo, monkeypatch):
    """main() with --strict + violation → returns 1 (SystemExit handled by __main__)."""
    (fake_repo / "mas-engineer" / "logs").mkdir(exist_ok=True)
    (fake_repo / "mas-engineer" / "logs" / "bad.md").write_text("v")
    monkeypatch.chdir(fake_repo)
    sys.path.insert(0, str(TOOL.parent))
    if "dev_evidence_sot" in sys.modules:
        del sys.modules["dev_evidence_sot"]
    import dev_evidence_sot
    monkeypatch.setattr(sys, "argv", ["dev_evidence_sot.py", "--strict"])
    rc = dev_evidence_sot.main()
    assert rc == 1


def test_main_history_mode(fake_repo, capsys, monkeypatch):
    """main() with --history → prints history block from scan_history_for_violators."""
    monkeypatch.chdir(fake_repo)
    sys.path.insert(0, str(TOOL.parent))
    if "dev_evidence_sot" in sys.modules:
        del sys.modules["dev_evidence_sot"]
    import dev_evidence_sot
    monkeypatch.setattr(sys, "argv", ["dev_evidence_sot.py", "--history"])
    dev_evidence_sot.main()
    captured = capsys.readouterr()
    # Non-JSON output uses "Anti-SOT evidence files EVER added: N" header
    assert "GIT HISTORY" in captured.out
    assert "Anti-SOT evidence files EVER added" in captured.out


def test_main_git_mode_clean(fake_repo, capsys, monkeypatch):
    """main() with --git + clean tracked tree → ok=True."""
    monkeypatch.chdir(fake_repo)
    sys.path.insert(0, str(TOOL.parent))
    if "dev_evidence_sot" in sys.modules:
        del sys.modules["dev_evidence_sot"]
    import dev_evidence_sot
    monkeypatch.setattr(sys, "argv", ["dev_evidence_sot.py", "--git", "--json"])
    dev_evidence_sot.main()
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert out["ok"] is True
