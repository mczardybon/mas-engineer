"""
test_dashboard_data_schema.py — schema + e2e tests for dev_dashboard_data.py.

Per R110-149: dashboard data flow verification.
  - 12 top-level keys in data.json
  - agents/changes/improvement/dispatch/build/health sub-schemas
  - e2e: dev_dashboard_data.py --workspace <repo> writes data.json + history.json
  - history bounded (health_trend <= 24, build_size <= 24)
  - schema-stable: same generator → same shape (sorted sub-agents)
  - error paths: missing guardian.yaml/changes.json/schedule.yaml don't crash

Run with:
    python3 -m pytest tests/test_dashboard_data_schema.py -v
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
DASH_DIR = REPO_ROOT / ".mase" / "dashboards"

sys.path.insert(0, str(TOOLS))
import dev_dashboard_data  # noqa: E402


# ─── TOP-LEVEL SCHEMA ─────────────────────────────────────────────

EXPECTED_TOP_LEVEL_KEYS = {
    "version", "timestamp", "workspace", "mode", "project_name",
    "agents", "changes", "improvement", "dispatch", "build",
    "health", "health_trend",
}


def test_generate_data_returns_dict():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert isinstance(d, dict), f"expected dict, got {type(d)}"


def test_generate_data_has_all_top_level_keys():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    missing = EXPECTED_TOP_LEVEL_KEYS - set(d.keys())
    assert not missing, f"missing top-level keys: {missing}"


def test_generate_data_version_is_string():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert isinstance(d["version"], str)
    assert d["version"]  # non-empty


def test_generate_data_timestamp_is_iso8601():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    ts = d["timestamp"]
    assert "T" in ts and (ts.endswith("Z") or "+" in ts), f"not ISO-8601: {ts}"


def test_generate_data_workspace_is_absolute():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert os.path.isabs(d["workspace"]), f"not absolute: {d['workspace']}"


def test_generate_data_mode_is_mas_or_user():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert d["mode"] in ("mas", "user"), f"unknown mode: {d['mode']}"


def test_generate_data_project_name_nonempty():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert d["project_name"]
    assert isinstance(d["project_name"], str)


# ─── AGENTS SUB-SCHEMA ────────────────────────────────────────────

def test_agents_sub_schema_keys():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    ag = d["agents"]
    for k in ("total", "healthy", "degraded", "dead", "avg_score",
              "scores", "guardian_scan", "issues"):
        assert k in ag, f"agents.{k} missing"


def test_agents_total_is_int():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    ag = d["agents"]
    assert isinstance(ag["total"], int)
    assert ag["total"] >= 0


def test_agents_healthy_plus_degraded_plus_dead_lte_total():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    ag = d["agents"]
    s = ag["healthy"] + ag["degraded"] + ag["dead"]
    assert s <= ag["total"], \
        f"healthy+degraded+dead ({s}) > total ({ag['total']})"


def test_agents_scores_is_list():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    ag = d["agents"]
    assert isinstance(ag["scores"], list)
    if ag["scores"]:
        for entry in ag["scores"]:
            assert "name" in entry
            assert "score" in entry
            assert "status" in entry


def test_agents_scores_sorted_descending():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    scores = d["agents"]["scores"]
    if len(scores) >= 2:
        for i in range(len(scores) - 1):
            assert scores[i]["score"] >= scores[i+1]["score"], \
                f"scores not sorted desc at index {i}"


def test_agents_scores_max_15():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert len(d["agents"]["scores"]) <= 15, \
        f"scores has {len(d['agents']['scores'])} entries (>15)"


def test_agents_issues_has_total():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert "total" in d["agents"]["issues"]


# ─── CHANGES SUB-SCHEMA ───────────────────────────────────────────

def test_changes_sub_schema_keys():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    ch = d["changes"]
    for k in ("total", "last_10", "by_type"):
        assert k in ch, f"changes.{k} missing"


def test_changes_total_is_int():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert isinstance(d["changes"]["total"], int)
    assert d["changes"]["total"] >= 0


def test_changes_last_10_max_10():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert len(d["changes"]["last_10"]) <= 10


def test_changes_last_10_entries_have_ts_desc():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    for e in d["changes"]["last_10"]:
        assert "ts" in e
        assert "desc" in e


def test_changes_by_type_is_dict():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert isinstance(d["changes"]["by_type"], dict)


# ─── IMPROVEMENT SUB-SCHEMA ───────────────────────────────────────

def test_improvement_sub_schema_keys():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    im = d["improvement"]
    for k in ("total_runs", "last_run", "schedule_status", "next_round_after"):
        assert k in im, f"improvement.{k} missing"


def test_improvement_total_runs_is_int():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert isinstance(d["improvement"]["total_runs"], int)
    assert d["improvement"]["total_runs"] >= 0


# ─── DISPATCH SUB-SCHEMA ──────────────────────────────────────────

def test_dispatch_sub_schema_keys():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    dp = d["dispatch"]
    for k in ("total", "done", "failed", "active", "avg_duration_ms"):
        assert k in dp, f"dispatch.{k} missing"


def test_dispatch_all_int():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    dp = d["dispatch"]
    for k in ("total", "done", "failed", "active"):
        assert isinstance(dp[k], int), f"dispatch.{k} not int"
        assert dp[k] >= 0


# ─── BUILD SUB-SCHEMA ─────────────────────────────────────────────

def test_build_sub_schema_keys():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    b = d["build"]
    assert "exists" in b
    assert "total_count" in b
    assert isinstance(b["exists"], bool)
    assert isinstance(b["total_count"], int)


def test_build_latest_size_kb_if_exists():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    b = d["build"]
    if b["exists"]:
        assert "latest_name" in b
        assert "latest_date" in b
        assert "latest_size_kb" in b
        assert b["latest_size_kb"] > 0


# ─── HEALTH SUB-SCHEMA ────────────────────────────────────────────

def test_health_sub_schema_keys():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    h = d["health"]
    for k in ("score", "last_report", "checks"):
        assert k in h, f"health.{k} missing"


def test_health_checks_is_dict():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert isinstance(d["health"]["checks"], dict)


# ─── HEALTH TREND ─────────────────────────────────────────────────

def test_health_trend_is_list():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert isinstance(d["health_trend"], list)


def test_health_trend_max_24():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert len(d["health_trend"]) <= 24, \
        f"health_trend has {len(d['health_trend'])} entries (>24)"


def test_health_trend_entries_have_time_score():
    d = dev_dashboard_data.generate_data(str(REPO_ROOT))
    for e in d["health_trend"]:
        assert "time" in e
        assert "score" in e
        assert isinstance(e["score"], (int, float))
        assert 0 <= e["score"] <= 100


# ─── ERROR PATHS ──────────────────────────────────────────────────

def test_generate_data_with_nonexistent_workspace_does_not_crash(tmp_path):
    """Empty workspace: must not raise, must return valid shape."""
    d = dev_dashboard_data.generate_data(str(tmp_path))
    assert isinstance(d, dict)
    assert "agents" in d
    assert d["agents"]["total"] >= 0


def test_generate_data_workspace_auto_detect_mas_subdir():
    """If passed parent dir, must auto-detect mas-engineer/recipe subdir."""
    parent = REPO_ROOT.parent
    if (parent / "mas-engineer" / "recipe").is_dir():
        d = dev_dashboard_data.generate_data(str(parent))
        assert d["workspace"].endswith("mas-engineer") or d["workspace"] == str(parent)


# ─── E2E: SCRIPT EXECUTION ───────────────────────────────────────

def test_dev_dashboard_data_script_runs():
    """The script must exit 0, write data.json, write history.json."""
    result = subprocess.run(
        [sys.executable, str(TOOLS / "dev_dashboard_data.py"),
         "--workspace", str(REPO_ROOT)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, \
        f"script failed (exit {result.returncode}): {result.stderr}"
    assert DASH_DIR.is_dir(), ".mase/dashboards missing"
    assert (DASH_DIR / "data.json").is_file(), "data.json not written"
    assert (DASH_DIR / "history.json").is_file(), "history.json not written"


def test_data_json_after_script_is_valid_json():
    subprocess.run(
        [sys.executable, str(TOOLS / "dev_dashboard_data.py"),
         "--workspace", str(REPO_ROOT)],
        capture_output=True, text=True, timeout=30,
        check=True,
    )
    with open(DASH_DIR / "data.json") as f:
        d = json.load(f)
    assert isinstance(d, dict)
    assert EXPECTED_TOP_LEVEL_KEYS.issubset(d.keys())


def test_history_json_after_script_is_valid_json():
    subprocess.run(
        [sys.executable, str(TOOLS / "dev_dashboard_data.py"),
         "--workspace", str(REPO_ROOT)],
        capture_output=True, text=True, timeout=30,
        check=True,
    )
    with open(DASH_DIR / "history.json") as f:
        h = json.load(f)
    assert "health_trend" in h
    assert isinstance(h["health_trend"], list)


def test_notification_flag_file_written():
    """dev_dashboard_data.py writes .mase/dashboards/.updated as MCP-notify flag."""
    flag = DASH_DIR / ".updated"
    if not flag.exists():
        subprocess.run(
            [sys.executable, str(TOOLS / "dev_dashboard_data.py"),
             "--workspace", str(REPO_ROOT)],
            capture_output=True, text=True, timeout=30,
            check=True,
        )
    assert flag.is_file(), ".updated flag file missing"
    # content = unix timestamp (int)
    content = flag.read_text().strip()
    assert content.isdigit(), f".updated not numeric: {content!r}"
    ts = int(content)
    assert ts > 1_700_000_000, f"timestamp too old: {ts}"


# ─── DETERMINISM ──────────────────────────────────────────────────

def test_generate_data_is_deterministic_for_sub_agent_count():
    """Two calls must report same agent count (sorted glob is deterministic)."""
    a = dev_dashboard_data.generate_data(str(REPO_ROOT))
    b = dev_dashboard_data.generate_data(str(REPO_ROOT))
    assert a["agents"]["total"] == b["agents"]["total"]


def test_history_health_trend_grows_monotonically():
    """After a script run, history.health_trend should have at least one entry
    (or grow if called repeatedly). Bounded to 24."""
    subprocess.run(
        [sys.executable, str(TOOLS / "dev_dashboard_data.py"),
         "--workspace", str(REPO_ROOT)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    with open(DASH_DIR / "history.json") as f:
        h = json.load(f)
    assert len(h["health_trend"]) >= 1
    assert len(h["health_trend"]) <= 24


# ─── R110-312: LEGACY 'mas' KEY MIGRATION ────────────────────────

def test_health_trend_migrates_legacy_mas_key_to_score(tmp_path, monkeypatch):
    """R110-312: history.json entries from pre-R110-149 eras used the
    legacy 'mas' key (instead of 'score'). generate_data() must
    migrate on load so the schema assertion holds for all entries.
    """
    # Build a fake dashboard dir with a legacy-shape history.json
    fake_dash = tmp_path / "dashboards"
    fake_dash.mkdir()
    legacy_history = {
        "health_trend": [
            {"time": "10:00", "mas": 100},   # legacy shape
            {"time": "10:05", "mas": 70},    # legacy shape
            {"time": "10:10", "score": 50},  # current shape (must be kept)
        ],
        "build_size": [],
    }
    (fake_dash / "history.json").write_text(json.dumps(legacy_history))

    # Build a fake workspace with the minimal structure generate_data needs
    fake_ws = tmp_path / "ws"
    fake_ws.mkdir()
    (fake_ws / ".mase" / "dashboards").mkdir(parents=True)
    (fake_ws / ".mase" / "dashboards" / "history.json").write_text(
        json.dumps(legacy_history)
    )
    # Minimal recipe/sub dir
    (fake_ws / "recipe" / "sub").mkdir(parents=True)
    (fake_ws / "recipe" / "sub" / "sub_mas-test.yaml").write_text("name: test\nversion: 1\n")

    d = dev_dashboard_data.generate_data(str(fake_ws))
    scores = [e.get("score") for e in d["health_trend"]]
    # All entries must have a 'score' key (the legacy 'mas' was migrated)
    assert all("score" in e for e in d["health_trend"]), \
        f"legacy 'mas' entries not migrated: {d['health_trend']}"
    # Original 'mas' values preserved
    assert 100 in scores
    assert 70 in scores
    assert 50 in scores
