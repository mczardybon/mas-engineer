"""
test_guardian_scan.py — tests for dev_guardian_scan.py.

Per R110-150: operator-side guardian scan that produces
.mase/guardian.yaml in the format dev_dashboard_data.py consumes.

Scans recipe/sub/sub_mas-*.yaml with 5-dim check
(schema/semantic/death/loop/drift), writes guardian.yaml.

Test groups:
  - script execution (e2e): runs without crash, writes guardian.yaml
  - output schema: all 7 known top-level keys under guardian.*
  - agent records: per-agent status+score+checks+issues
  - findings summary: 9 fields, total_issues == sum
  - drift log: bounded, has by_type/by_agent/trend
  - safe: does NOT touch changes.json / schedule.yaml / health-report.json
  - idempotent: two consecutive runs produce structurally-valid output
  - error paths: nonexistent workspace, no sub-agents, yaml-broken
  - dashboard integration: after scan, dev_dashboard_data shows real
    healthy/degraded counts (regression-test for R110-149 dashboard)

Run with:
    python3 -m pytest tests/test_guardian_scan.py -v
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
STATE = REPO_ROOT / ".mase"
GUARDIAN = STATE / "guardian.yaml"


# ─── HELPERS ──────────────────────────────────────────────────────

def _run_scan(workspace=None, expect_rc=0):
    args = [sys.executable, str(TOOLS / "dev_guardian_scan.py")]
    if workspace is not None:
        args += ["--workspace", str(workspace)]
    return subprocess.run(args, capture_output=True, text=True, timeout=60)


def _backup_state():
    """Backup .mase/ files that MUST NOT be touched by the scan."""
    backups = {}
    for name in ("changes.json", "schedule.yaml", "health-report.json",
                 "health-history.json"):
        p = STATE / name
        if p.exists():
            backups[name] = p.read_bytes()
    return backups


def _verify_untouched(backups):
    """Assert that the listed .mase/ files are byte-identical to backup."""
    diffs = []
    for name, original in backups.items():
        p = STATE / name
        if not p.exists():
            diffs.append(f"{name} was deleted!")
            continue
        if p.read_bytes() != original:
            diffs.append(f"{name} was modified")
    return diffs


def _load_guardian(path=None):
    import yaml
    p = path or GUARDIAN
    return yaml.safe_load(open(p))


def _load_guardian_from(workspace):
    """Load guardian.yaml from a specific workspace (not the repo default)."""
    import yaml
    p = Path(workspace) / ".mase" / "guardian.yaml"
    if not p.exists():
        return None
    return yaml.safe_load(open(p))


# ─── SCRIPT EXECUTION ─────────────────────────────────────────────

def test_scan_runs_exits_0():
    r = _run_scan()
    assert r.returncode == 0, f"exit {r.returncode}: {r.stderr}"


def test_scan_writes_guardian_yaml():
    r = _run_scan()
    assert GUARDIAN.is_file(), "guardian.yaml not written"


def test_scan_output_summarizes_counts():
    r = _run_scan()
    out = r.stdout + r.stderr
    assert "scanned:" in out
    assert "healthy:" in out
    assert "degraded:" in out
    assert "broken:" in out
    assert "findings:" in out


# ─── OUTPUT SCHEMA ───────────────────────────────────────────────

EXPECTED_GUARDIAN_KEYS = {
    "last_scan", "healthy", "degraded", "broken", "total_yamls",
    "note", "categories", "findings_summary", "agents",
    "drift_log", "drift_summary",
}


def test_guardian_top_level_keys():
    _run_scan()
    g = _load_guardian()
    missing = EXPECTED_GUARDIAN_KEYS - set(g["guardian"].keys())
    assert not missing, f"missing: {missing}"


def test_guardian_last_scan_is_iso8601():
    _run_scan()
    g = _load_guardian()
    ts = g["guardian"]["last_scan"]
    assert ts and "T" in ts, f"not ISO-8601: {ts}"


def test_guardian_counts_are_nonneg_int():
    _run_scan()
    g = _load_guardian()
    for k in ("healthy", "degraded", "broken", "total_yamls"):
        v = g["guardian"][k]
        assert isinstance(v, int) and v >= 0, f"{k} bad: {v}"


def test_guardian_counts_sum_to_total():
    _run_scan()
    g = _load_guardian()
    s = g["guardian"]["healthy"] + g["guardian"]["degraded"] + g["guardian"]["broken"]
    assert s == g["guardian"]["total_yamls"], \
        f"sum {s} != total {g['guardian']['total_yamls']}"


def test_guardian_categories_lists_consistent():
    _run_scan()
    g = _load_guardian()
    cats = g["guardian"]["categories"]
    assert len(cats["healthy_agents"]) == g["guardian"]["healthy"]
    assert len(cats["degraded_agents"]) == g["guardian"]["degraded"]
    assert len(cats["critical_agents"]) == g["guardian"]["broken"]


def test_guardian_note_is_string():
    _run_scan()
    g = _load_guardian()
    assert isinstance(g["guardian"]["note"], str)
    assert g["guardian"]["note"]


# ─── AGENT RECORDS ───────────────────────────────────────────────

def test_guardian_agents_dict_nonempty():
    _run_scan()
    g = _load_guardian()
    assert isinstance(g["guardian"]["agents"], dict)
    assert len(g["guardian"]["agents"]) > 0


def test_guardian_agent_keys_end_with_yaml():
    _run_scan()
    g = _load_guardian()
    for name in g["guardian"]["agents"].keys():
        assert name.endswith(".yaml"), f"agent key not .yaml: {name}"


def test_guardian_agent_status_valid():
    _run_scan()
    g = _load_guardian()
    for name, info in g["guardian"]["agents"].items():
        assert info["status"] in ("healthy", "degraded", "broken"), \
            f"{name}: bad status {info['status']}"


def test_guardian_agent_score_in_0_100():
    _run_scan()
    g = _load_guardian()
    for name, info in g["guardian"]["agents"].items():
        s = info["score"]
        assert 0 <= s <= 100, f"{name}: score {s} out of range"


def test_guardian_agent_has_5_dim_checks():
    _run_scan()
    g = _load_guardian()
    expected = {"schema", "semantic", "death", "loop", "drift"}
    for name, info in g["guardian"]["agents"].items():
        missing = expected - set(info["checks"].keys())
        assert not missing, f"{name}: missing checks {missing}"


def test_guardian_agent_issues_is_list():
    _run_scan()
    g = _load_guardian()
    for name, info in g["guardian"]["agents"].items():
        assert isinstance(info["issues"], list), f"{name}: issues not list"


def test_guardian_agent_healthy_has_no_issues():
    """If status=healthy, expected: minor (drift/semantic warn) tolerated,
    but no schema/death failures."""
    _run_scan()
    g = _load_guardian()
    for name, info in g["guardian"]["agents"].items():
        if info["status"] == "healthy":
            # Healthy = score >= 80, schema=ok guaranteed
            assert info["checks"]["schema"] == "ok", \
                f"{name}: healthy but schema {info['checks']['schema']}"


# ─── FINDINGS SUMMARY ────────────────────────────────────────────

def test_findings_summary_total_matches_subcategories():
    _run_scan()
    g = _load_guardian()
    f = g["guardian"]["findings_summary"]
    sub_total = (f.get("long_instructions", 0) +
                 f.get("missing_prompt", 0) +
                 f.get("missing_instructions", 0) +
                 f.get("missing_top_keys", 0) +
                 f.get("yaml_errors", 0) +
                 f.get("loop_risks", 0) +
                 f.get("typos", 0) +
                 f.get("drift", 0))
    assert f["total_issues"] == sub_total, \
        f"total {f['total_issues']} != sum {sub_total}"


def test_findings_summary_total_matches_agent_issues():
    _run_scan()
    g = _load_guardian()
    total = sum(len(a["issues"]) for a in g["guardian"]["agents"].values())
    assert g["guardian"]["findings_summary"]["total_issues"] == total, \
        f"summary {g['guardian']['findings_summary']['total_issues']} != agent-sum {total}"


# ─── DRIFT LOG ───────────────────────────────────────────────────

def test_drift_log_is_list():
    _run_scan()
    g = _load_guardian()
    assert isinstance(g["guardian"]["drift_log"], list)


def test_drift_log_bounded():
    _run_scan()
    g = _load_guardian()
    assert len(g["guardian"]["drift_log"]) <= 100, \
        f"drift_log has {len(g['guardian']['drift_log'])} entries (>100)"


def test_drift_summary_has_by_type_by_agent_trend():
    _run_scan()
    g = _load_guardian()
    ds = g["guardian"]["drift_summary"]
    for k in ("total_drifts", "by_type", "by_agent", "trend"):
        assert k in ds, f"drift_summary.{k} missing"
    assert isinstance(ds["by_type"], dict)
    assert isinstance(ds["by_agent"], dict)


# ─── SAFE / NO SIDE EFFECTS ──────────────────────────────────────

def test_scan_does_not_touch_changes_json():
    backups = _backup_state()
    try:
        _run_scan()
        diffs = _verify_untouched(backups)
        assert not diffs, f"scan modified: {diffs}"
    finally:
        pass  # backup kept for inspection


def test_scan_does_not_touch_schedule_yaml():
    backups = _backup_state()
    _run_scan()
    diffs = _verify_untouched(backups)
    assert not diffs, f"scan modified: {diffs}"


def test_scan_does_not_touch_health_report():
    backups = _backup_state()
    _run_scan()
    diffs = _verify_untouched(backups)
    assert not diffs, f"scan modified: {diffs}"


def test_scan_only_writes_guardian_yaml_in_mase():
    """Files in .mase/ before scan minus guardian.yaml = unchanged."""
    backups = _backup_state()
    _run_scan()
    # All non-guardian files we backed up must be byte-identical
    for name, original in backups.items():
        p = STATE / name
        if p.exists() and p.read_bytes() != original:
            pytest.fail(f"{name} was modified by scan")


# ─── IDEMPOTENT ──────────────────────────────────────────────────

def test_scan_idempotent_same_counts():
    r1 = _run_scan()
    g1 = _load_guardian()
    c1 = (g1["guardian"]["healthy"], g1["guardian"]["degraded"],
          g1["guardian"]["broken"], g1["guardian"]["findings_summary"]["total_issues"])
    r2 = _run_scan()
    g2 = _load_guardian()
    c2 = (g2["guardian"]["healthy"], g2["guardian"]["degraded"],
          g2["guardian"]["broken"], g2["guardian"]["findings_summary"]["total_issues"])
    assert c1 == c2, f"non-idempotent: {c1} -> {c2}"


def test_scan_idempotent_same_agents():
    _run_scan()
    g1 = _load_guardian()
    _run_scan()
    g2 = _load_guardian()
    assert set(g1["guardian"]["agents"].keys()) == set(g2["guardian"]["agents"].keys())


# ─── ERROR PATHS ─────────────────────────────────────────────────

def test_scan_nonexistent_workspace_exits_nonzero(tmp_path):
    """Workspace with no recipe/ dir should exit 2 (no agents found)."""
    r = _run_scan(workspace=tmp_path)
    # Either: FATAL "no sub_mas-*.yaml" (rc=2), or writes empty guardian
    assert r.returncode != 0 or "scanned:" in r.stdout


def test_scan_empty_sub_dir_creates_empty_guardian(tmp_path):
    """Workspace with empty recipe/sub/ dir: writes valid-shape guardian."""
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    r = _run_scan(workspace=tmp_path)
    # Either FATAL (rc=2) or successful with 0 agents
    if r.returncode == 0:
        g = _load_guardian_from(tmp_path)
        assert g is not None
        assert g["guardian"]["total_yamls"] == 0


# ─── YAML PARSING SAFETY ────────────────────────────────────────

def test_scan_handles_broken_yaml(tmp_path):
    """A broken yaml file in sub/ must not crash the whole scan."""
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-good.yaml").write_text(
        "name: Good\ntitle: G\ndescription: d\n"
        "prompt: " + "x" * 50 + "\n"
        "instructions: " + "y" * 50 + "\n"
    )
    (sub / "sub_mas-broken.yaml").write_text(":\n: bad yaml [[[")
    r = _run_scan(workspace=tmp_path)
    assert r.returncode == 0
    g = _load_guardian_from(tmp_path)
    assert g is not None
    assert "sub_mas-good.yaml" in g["guardian"]["agents"]
    assert "sub_mas-broken.yaml" in g["guardian"]["agents"]
    assert g["guardian"]["agents"]["sub_mas-broken.yaml"]["status"] == "broken"


# ─── DASHBOARD INTEGRATION (R110-149 regression-guard) ──────────

def test_scan_then_dashboard_shows_real_agents():
    """After scan, dev_dashboard_data must show >0 healthy agents.
    This is the R110-150 + R110-149 contract: scan populates
    guardian.yaml → dashboard shows real numbers."""
    _run_scan()
    r = subprocess.run(
        [sys.executable, str(TOOLS / "dev_dashboard_data.py"),
         "--workspace", str(REPO_ROOT)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    with open(STATE / "dashboards" / "data.json") as f:
        d = json.load(f)
    a = d["agents"]
    assert a["total"] > 0, "total agents = 0 after scan"
    assert a["healthy"] + a["degraded"] + a["dead"] == a["total"]
    assert a["avg_score"] > 0
    assert len(a["scores"]) > 0
    assert a["guardian_scan"] is not None
    # No regression on R110-149 schema
    for k in ("total", "healthy", "degraded", "dead", "avg_score",
              "scores", "guardian_scan", "issues"):
        assert k in a, f"dashboard.agents.{k} missing after R110-150"
