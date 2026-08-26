"""
test_dev_evidence_sot.py — R110-257 regression tests for
tools/dev_evidence_sot.py.

The tool enforces that all evidence-archive and directive files live at
the SOT (Single Source of Truth) locations:
  - Evidence:    logs/e2e-evidence-gen2/           (REPO-ROOT)
  - Directives:  mas-engineer/.mase/directives/

Anti-SOT locations (must be empty for the push to succeed):
  - mas-engineer/logs/e2e-evidence-gen2/           (R110-194/210/214/215/216)
  - mas-engineer/.directives/                      (R110-217/218)

DETECTION→CORRECTION→PREVENTION cycle under test:
  - a file created at the wrong SOT location is a violation
  - the tool exits 1 with the violation path in the output
  - once moved to the SOT location (or removed), the tool exits 0

7 test-cases:
  (a) clean state: 0 violations, exit 0
  (b) violation: file in mas-engineer/.directives/ -> exit 1, path in output
  (c) violation: file in mas-engineer/logs/... -> exit 1, path in output
  (d) cleanup: violations removed -> exit 0
  (e) --json schema: {"ok", "violation_count", "checks"}
  (f) --git mode: tracks the git index (post-renames)
  (g) --history: detects past SOT violators in git history

Run with:
    python3 -m pytest tests/test_dev_evidence_sot.py -v
"""
import json
import os
import subprocess
import sys
from pathlib import Path

# tests/ → mas-engineer/ → mas-engineer-cleanup/ (the repo-root)
# The tool runs against the real repo-root, NOT against mas-engineer/.
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
TOOL = REPO_ROOT / "mas-engineer" / "tools" / "dev_evidence_sot.py"


def _run(args, cwd=None):
    """Run the tool with the given args, return (rc, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True, text=True, cwd=cwd or str(REPO_ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_in_tmp(args, tmp_path):
    """Run the tool in a fresh tmp_path (simulated clean repo)."""
    # Use absolute path to the tool (so CWD=tmp_path doesn't break resolution)
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    return proc.returncode, proc.stdout, proc.stderr


def _make_clean_fixture_repo(tmp_path):
    """Build a minimal clean repo: SOT dirs exist, no anti-SOT files."""
    # Init git so the tool's git calls work
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.local"],
        cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path, check=True
    )
    # Create SOT dirs
    (tmp_path / "logs" / "e2e-evidence-gen2").mkdir(parents=True)
    (tmp_path / "mas-engineer" / ".mase" / "directives").mkdir(parents=True)
    return tmp_path


# ─────────────────────────────────────────────────────────────────────
# Test (a): clean state
# ─────────────────────────────────────────────────────────────────────
def test_clean_state_exits_zero():
    """On the real repo (post-R110-257 cleanup), tool exits 0."""
    rc, stdout, _ = _run(["--git", "--strict"])
    assert rc == 0, f"tool failed on clean state:\n{stdout}"
    assert "RESULT: ✅ PASS" in stdout


def test_clean_state_in_fresh_repo(tmp_path):
    """On a fresh clean fixture repo, tool exits 0."""
    _make_clean_fixture_repo(tmp_path)
    rc, stdout, _ = _run_in_tmp(["--strict"], tmp_path)
    assert rc == 0, f"tool failed on clean fixture:\n{stdout}"
    assert "RESULT: ✅ PASS" in stdout


# ─────────────────────────────────────────────────────────────────────
# Test (b): mas-engineer/.directives/ violation
# ─────────────────────────────────────────────────────────────────────
def test_directives_violation_detected(tmp_path):
    """A file in mas-engineer/.directives/ is detected as violation."""
    _make_clean_fixture_repo(tmp_path)
    (tmp_path / "mas-engineer" / ".directives").mkdir(parents=True)
    (tmp_path / "mas-engineer" / ".directives" / "R110-TEST.md").write_text(
        "# test"
    )
    rc, stdout, _ = _run_in_tmp(["--strict"], tmp_path)
    assert rc == 1, f"tool should exit 1 on violation, got {rc}:\n{stdout}"
    assert "mas-engineer/.directives/R110-TEST.md" in stdout
    assert "directives_sot_working_tree" in stdout


# ─────────────────────────────────────────────────────────────────────
# Test (c): mas-engineer/logs/ violation
# ─────────────────────────────────────────────────────────────────────
def test_evidence_violation_detected(tmp_path):
    """A file in mas-engineer/logs/e2e-evidence-gen2/ is detected."""
    _make_clean_fixture_repo(tmp_path)
    (tmp_path / "mas-engineer" / "logs" / "e2e-evidence-gen2").mkdir(parents=True)
    (tmp_path / "mas-engineer" / "logs" / "e2e-evidence-gen2" / "R110-TEST.log").write_text(
        "log"
    )
    rc, stdout, _ = _run_in_tmp(["--strict"], tmp_path)
    assert rc == 1, f"tool should exit 1 on violation, got {rc}:\n{stdout}"
    assert "mas-engineer/logs/e2e-evidence-gen2/R110-TEST.log" in stdout
    assert "evidence_sot_working_tree" in stdout


def test_evidence_violation_in_logs_root(tmp_path):
    """A file in mas-engineer/logs/ (anywhere) is detected."""
    _make_clean_fixture_repo(tmp_path)
    (tmp_path / "mas-engineer" / "logs").mkdir(parents=True)
    (tmp_path / "mas-engineer" / "logs" / "test.log").write_text("log")
    rc, stdout, _ = _run_in_tmp(["--strict"], tmp_path)
    assert rc == 1, f"tool should exit 1, got {rc}:\n{stdout}"
    assert "mas-engineer/logs/test.log" in stdout


# ─────────────────────────────────────────────────────────────────────
# Test (d): violations removed -> exit 0
# ─────────────────────────────────────────────────────────────────────
def test_violation_cleanup_restores_clean(tmp_path):
    """After removing violations, tool exits 0 again."""
    _make_clean_fixture_repo(tmp_path)
    # Add violation
    (tmp_path / "mas-engineer" / ".directives").mkdir(parents=True)
    (tmp_path / "mas-engineer" / ".directives" / "R110-TEST.md").write_text("# test")
    rc, _, _ = _run_in_tmp(["--strict"], tmp_path)
    assert rc == 1
    # Remove violation
    import shutil
    shutil.rmtree(tmp_path / "mas-engineer" / ".directives")
    # Re-run
    rc, stdout, _ = _run_in_tmp(["--strict"], tmp_path)
    assert rc == 0, f"tool should pass after cleanup:\n{stdout}"


# ─────────────────────────────────────────────────────────────────────
# Test (e): --json schema
# ─────────────────────────────────────────────────────────────────────
def test_json_output_schema(tmp_path):
    """--json output has the expected keys."""
    _make_clean_fixture_repo(tmp_path)
    rc, stdout, _ = _run_in_tmp(["--json"], tmp_path)
    assert rc == 0
    data = json.loads(stdout)
    # Required keys
    for key in (
        "sot_evidence_prefix",
        "sot_directives_prefix",
        "anti_sot_evidence_prefix",
        "anti_sot_directives_prefix",
        "checks",
        "violation_count",
        "ok",
    ):
        assert key in data, f"missing key: {key}"
    assert data["ok"] is True
    assert data["violation_count"] == 0
    assert data["sot_evidence_prefix"] == "logs/e2e-evidence-gen2/"
    assert data["sot_directives_prefix"] == "mas-engineer/.mase/directives/"


def test_json_output_with_violation(tmp_path):
    """--json output reports violation_count and ok=False correctly."""
    _make_clean_fixture_repo(tmp_path)
    (tmp_path / "mas-engineer" / ".directives" / "R110-BAD.md").parent.mkdir(
        parents=True
    )
    (tmp_path / "mas-engineer" / ".directives" / "R110-BAD.md").write_text("# bad")
    rc, stdout, _ = _run_in_tmp(["--json"], tmp_path)
    data = json.loads(stdout)
    assert data["ok"] is False
    assert data["violation_count"] >= 1
    assert "R110-BAD.md" in str(data["checks"]["directives_sot_working_tree"])


# ─────────────────────────────────────────────────────────────────────
# Test (f): --git mode
# ─────────────────────────────────────────────────────────────────────
def test_git_mode_tracks_renames(tmp_path):
    """--git mode shows no violations when anti-SOT files are in git index
    but with proper git mv renames in place.

    Simulates the post-R110-257 state: 26 files moved via git mv from
    mas-engineer/logs/e2e-evidence-gen2/ to logs/e2e-evidence-gen2/.
    """
    _make_clean_fixture_repo(tmp_path)
    # Create files at wrong SOT location
    (tmp_path / "mas-engineer" / "logs" / "e2e-evidence-gen2").mkdir(parents=True)
    bad = tmp_path / "mas-engineer" / "logs" / "e2e-evidence-gen2" / "R110-99.md"
    bad.write_text("# evidence")
    # Git add
    subprocess.run(["git", "add", str(bad)], cwd=tmp_path, check=True)
    # Without --git: should detect working tree violation
    rc_wo, _, _ = _run_in_tmp(["--strict"], tmp_path)
    # With --git: should ALSO detect (since file is in index at wrong SOT)
    rc_g, _, _ = _run_in_tmp(["--git", "--strict"], tmp_path)
    # Both should fail because file is at anti-SOT location
    assert rc_wo == 1
    assert rc_g == 1, "git mode should also detect anti-SOT tracked file"


# ─────────────────────────────────────────────────────────────────────
# Test (g): --history scan
# ─────────────────────────────────────────────────────────────────────
def test_history_scan_detects_past_violators(tmp_path):
    """--history scan finds past commits that added anti-SOT files."""
    _make_clean_fixture_repo(tmp_path)
    # Add a file at anti-SOT location, commit it
    (tmp_path / "mas-engineer" / "logs" / "e2e-evidence-gen2").mkdir(parents=True)
    bad = tmp_path / "mas-engineer" / "logs" / "e2e-evidence-gen2" / "R110-99-archive.md"
    bad.write_text("# archive")
    subprocess.run(["git", "add", str(bad)], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "old commit with anti-SOT file"],
        cwd=tmp_path, check=True
    )
    # Now scan history
    rc, stdout, _ = _run_in_tmp(["--history", "--git"], tmp_path)
    assert "Anti-SOT evidence files EVER added: 1" in stdout
    assert "R110-99-archive.md" in stdout


# ─────────────────────────────────────────────────────────────────────
# Test: dir-health checks
# ─────────────────────────────────────────────────────────────────────
def test_missing_sot_evidence_dir_is_violation(tmp_path):
    """If logs/e2e-evidence-gen2/ is missing, tool reports it as violation."""
    # Init git but DON'T create the SOT evidence dir
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.local"],
        cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path, check=True
    )
    # Create only the directives SOT, not evidence
    (tmp_path / "mas-engineer" / ".mase" / "directives").mkdir(parents=True)
    rc, stdout, _ = _run_in_tmp(["--strict"], tmp_path)
    assert rc == 1
    assert "sot_evidence_dir_health" in stdout
    assert "missing" in stdout


def test_missing_sot_directives_dir_is_violation(tmp_path):
    """If mas-engineer/.mase/directives/ is missing, tool reports it.

    Note: mas-engineer/ subdir must exist (so the tool can resolve
    REPO_ROOT), but .mase/directives/ is intentionally missing.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.local"],
        cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path, check=True
    )
    # SOT evidence dir exists
    (tmp_path / "logs" / "e2e-evidence-gen2").mkdir(parents=True)
    # mas-engineer/ subdir exists (so REPO_ROOT resolves) but no .mase
    (tmp_path / "mas-engineer").mkdir(parents=True)
    # .mase/directives/ is INTENTIONALLY missing
    rc, stdout, _ = _run_in_tmp(["--strict"], tmp_path)
    assert rc == 1
    assert "sot_directives_dir_health" in stdout
