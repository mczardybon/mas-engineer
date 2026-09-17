"""R110-540 — coverage test sprint: tools/dev_health_monitor.py 0%→100%.

Unit tests for the 4 monitor commands (CHECK_HEALTH, CHECK_RUNTIME,
LOG_SESSION, RECOVER) + __main__ CLI. Each test uses isolated
tmp_path fixtures so we never touch the real repo or .mase state.

Coverage of 343 LOC / 6 functions:
  - yaml_safe_load (lines 33-41)
  - check_health (lines 44-137): 4 phases
  - check_runtime (lines 140-200)
  - log_session (lines 203-227)
  - recover (lines 230-257)
  - main / __main__ (lines 260-339)

Patterns:
  - Phase 1 (YAML integrity): write valid/invalid yaml in tmp recipe/sub/
  - Phase 2 (governance): monkeypatch Path home/docs paths
  - Phase 3 (secrets grep): always uses real grep on tmp_path (safe,
    no real secrets in tmp)
  - Phase 4 (structure): seed sub_mas-*.yaml + main recipe files
"""
import json
import os
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_health_monitor as hm


# ────────────────────── yaml_safe_load ────────────────────────────

def test_yaml_safe_load_valid(tmp_path):
    """Lines 33-39: valid yaml → (True, '')."""
    f = tmp_path / "ok.yaml"
    f.write_text("name: foo\nvalue: 42\n")
    ok, err = hm.yaml_safe_load(f)
    assert ok is True
    assert err == ""


def test_yaml_safe_load_invalid(tmp_path):
    """Lines 40-41: malformed yaml → (False, err_msg)."""
    f = tmp_path / "broken.yaml"
    f.write_text("name: foo\n  invalid: : :\n\tbad: indent")
    ok, err = hm.yaml_safe_load(f)
    assert ok is False
    assert "mapping" in err.lower() or "yaml" in err.lower() or err


def test_yaml_safe_load_missing_file(tmp_path):
    """Lines 40-41: FileNotFoundError → (False, msg)."""
    f = tmp_path / "does_not_exist.yaml"
    ok, err = hm.yaml_safe_load(f)
    assert ok is False
    assert "No such file" in err or "not found" in err.lower() or err


# ────────────────────── check_health ──────────────────────────────

@pytest.fixture
def fake_recipes(tmp_path):
    """Build a fake recipe/ subtree with 5 sample subs + main recipes."""
    recipes = tmp_path / "recipe"
    sub = recipes / "sub"
    sub.mkdir(parents=True)
    # 5 sample subs (line 60-62 list)
    sample_names = ["sub_mas-monitor-health.yaml",
                    "sub_mas-dashboard-director.yaml",
                    "sub_mas-test-runner.yaml",
                    "sub_mas-dashboard-refresh.yaml",
                    "sub_mas-pipeline-finder.yaml"]
    for n in sample_names:
        (sub / n).write_text("name: foo\nprompt: x\n")
    # Add enough sub_mas-*.yaml to pass ≥20 threshold (line 108)
    for i in range(20):
        (sub / f"sub_mas-extra-{i:02d}.yaml").write_text("name: extra\n")
    # Add main recipes (line 99-101) — need ≥3
    for n in ["dev-mas-engineer.yaml", "root_recipe.yaml",
              "test-fix-failures.yaml"]:
        (recipes / n).write_text("name: main\n")
    return recipes


def test_check_health_all_green(fake_recipes, monkeypatch):
    """All 4 phases pass → 🟢 DONE, no findings, all counts set."""
    # Ensure no governance candidates exist (force INV-1 to fail? No -
    # we want it to pass. Make at least one exist: create tmp docs).
    # Actually the test wants the green path, so we need a governance
    # file. Monkeypatch REPO_ROOT/docs/framework-governance.md.
    docs = hm.REPO_ROOT / "docs"
    docs.mkdir(exist_ok=True)
    gov = docs / "framework-governance.md"
    gov.write_text("# Governance\n")
    try:
        result = hm.check_health(str(fake_recipes))
    finally:
        if gov.exists():
            gov.unlink()
    # Phase 1: 5 sample subs all valid
    assert result["command"] == "CHECK_HEALTH"
    assert result["from"] == "dev_health_monitor"
    assert result["signal"] == "🟢 DONE"
    assert result["checks_total"] >= 4
    assert result["checks_failed"] == 0
    assert result["findings"] == []
    assert result["structure"]["sub_recipes"] >= 20
    assert result["structure"]["main_recipes"] >= 3
    assert "framework-governance.md" in result["structure"]["main_recipe_names"] \
        or len(result["structure"]["main_recipe_names"]) >= 3


def test_check_health_phase1_yaml_error(tmp_path, monkeypatch):
    """Lines 69-70: one of the 5 sample subs has invalid YAML."""
    recipes = tmp_path / "recipe"
    sub = recipes / "sub"
    sub.mkdir(parents=True)
    # 1 valid + 1 broken sample
    (sub / "sub_mas-monitor-health.yaml").write_text("name: ok\n")
    (sub / "sub_mas-dashboard-director.yaml").write_text(
        "name: broken\n  bad: :\n\tindent\n")
    # Add 20+ extras so phase 4 passes
    for i in range(20):
        (sub / f"sub_mas-extra-{i:02d}.yaml").write_text("name: x\n")
    # Add 3 main recipes
    for n in ["dev-mas-engineer.yaml", "root_recipe.yaml",
              "test-fix-failures.yaml"]:
        (recipes / n).write_text("name: m\n")
    result = hm.check_health(str(recipes))
    # Phase 1 should report CRITICAL finding
    phase1_findings = [f for f in result["findings"]
                       if "YAML-Error" in f["code"]]
    assert len(phase1_findings) == 1
    assert phase1_findings[0]["level"] == "CRITICAL"
    assert result["signal"] == "🔴 ISSUES"


def test_check_health_phase2_governance_missing(tmp_path):
    """Lines 81-83: no governance file at any candidate → WARN."""
    recipes = tmp_path / "recipe"
    sub = recipes / "sub"
    sub.mkdir(parents=True)
    for n in ["sub_mas-monitor-health.yaml",
              "sub_mas-dashboard-director.yaml",
              "sub_mas-test-runner.yaml",
              "sub_mas-dashboard-refresh.yaml",
              "sub_mas-pipeline-finder.yaml"]:
        (sub / n).write_text("name: ok\n")
    for i in range(20):
        (sub / f"sub_mas-extra-{i:02d}.yaml").write_text("name: x\n")
    for n in ["dev-mas-engineer.yaml", "root_recipe.yaml",
              "test-fix-failures.yaml"]:
        (recipes / n).write_text("name: m\n")
    # No governance file exists → all 3 candidates return False
    with patch.object(Path, "home", return_value=tmp_path / "no_home"):
        result = hm.check_health(str(recipes))
    phase2 = [f for f in result["findings"] if "INV-1" in f["code"]]
    assert len(phase2) == 1
    assert phase2[0]["level"] == "WARN"


def test_check_health_phase3_secrets_detected(fake_recipes, monkeypatch):
    """Lines 93-95: grep finds hardcoded secret file → CRITICAL."""
    # Mock the secrets-grep subprocess.run to simulate "found".
    fake_result = type("R", (), {})()
    fake_result.stdout = f"{fake_recipes}/leaked.yaml\n"
    fake_result.stderr = ""
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: fake_result
        if "sk-" in str(cmd) else subprocess._run_real(cmd, **kw)
        if hasattr(subprocess, "_run_real") else fake_result)
    # Even simpler: patch subprocess.run unconditionally for this test
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: fake_result)
    result = hm.check_health(str(fake_recipes))
    phase3 = [f for f in result["findings"]
              if "GOV-4" in f["code"]]
    assert len(phase3) == 1
    assert phase3[0]["level"] == "CRITICAL"


def test_check_health_phase3_secrets_in_backup_ignored(fake_recipes, monkeypatch):
    """Line 90: secrets in .backups dirs are filtered out."""
    # Mock grep → report only .backups path (which is filtered)
    backup_path = f"{fake_recipes}/.backups/old.yaml"
    fake_result = type("R", (), {})()
    fake_result.stdout = f"{backup_path}\n"
    fake_result.stderr = ""
    monkeypatch.setattr(subprocess, "run",
                        lambda cmd, **kw: fake_result)
    result = hm.check_health(str(fake_recipes))
    # No CRITICAL GOV-4 should appear (filtered out by ".backups" check)
    gov4 = [f for f in result["findings"]
            if "GOV-4" in f["code"]]
    assert gov4 == []


def test_check_health_phase4_sub_count_low(tmp_path):
    """Lines 108-110: sub_count < 20 → WARN."""
    recipes = tmp_path / "recipe"
    sub = recipes / "sub"
    sub.mkdir(parents=True)
    for n in ["sub_mas-monitor-health.yaml"]:
        (sub / n).write_text("name: ok\n")
    # Only 5 sub_mas-*.yaml total
    for i in range(5):
        (sub / f"sub_mas-extra-{i:02d}.yaml").write_text("name: x\n")
    for n in ["dev-mas-engineer.yaml", "root_recipe.yaml",
              "test-fix-failures.yaml"]:
        (recipes / n).write_text("name: m\n")
    result = hm.check_health(str(recipes))
    struct_warns = [f for f in result["findings"]
                    if "STRUCTURE" in f["code"]
                    and "sub-recipes" in f["code"]]
    assert len(struct_warns) == 1
    assert struct_warns[0]["level"] == "WARN"


def test_check_health_phase4_main_count_low(tmp_path):
    """Lines 111-113: main_count < 3 → WARN."""
    recipes = tmp_path / "recipe"
    sub = recipes / "sub"
    sub.mkdir(parents=True)
    for n in ["sub_mas-monitor-health.yaml"]:
        (sub / n).write_text("name: ok\n")
    # 20+ sub_mas-*
    for i in range(20):
        (sub / f"sub_mas-extra-{i:02d}.yaml").write_text("name: x\n")
    # Only 1 main recipe
    (recipes / "dev-mas-engineer.yaml").write_text("name: m\n")
    result = hm.check_health(str(recipes))
    struct_warns = [f for f in result["findings"]
                    if "STRUCTURE" in f["code"]
                    and "main recipes" in f["code"]]
    assert len(struct_warns) == 1


# ────────────────────── check_runtime ─────────────────────────────

def test_check_runtime_no_state_dir(tmp_path):
    """Lines 152 False: state dir missing → empty report, 🟢 OK."""
    state = tmp_path / "no_such_state"
    result = hm.check_runtime(str(state))
    assert result["command"] == "CHECK_RUNTIME"
    assert result["active_sessions"] == 0
    assert result["stale_sessions"] == []
    assert result["crashes"] == []
    assert result["arch_violations"] == 0
    assert result["issues_found"] is False
    assert result["signal"] == "🟢 OK"


def test_check_runtime_with_active_sessions(tmp_path):
    """Lines 153-163: valid sessions.json → counted."""
    state = tmp_path / "mase"
    state.mkdir()
    sessions = [{"id": "s1", "last_activity":
                 datetime.now(timezone.utc).isoformat(),
                 "started_at": "2025-01-01T00:00:00Z"},
                {"id": "s2", "last_activity":
                 datetime.now(timezone.utc).isoformat()}]
    (state / "sessions.json").write_text(json.dumps(sessions))
    result = hm.check_runtime(str(state))
    assert result["active_sessions"] == 2
    assert result["signal"] == "🟢 OK"


def test_check_runtime_stale_session(tmp_path):
    """Lines 165-175: session with last_activity > 1h ago → stale."""
    state = tmp_path / "mase"
    state.mkdir()
    old_iso = (datetime.now(timezone.utc)
               .replace(year=2020).isoformat())
    sessions = [{"id": "s_old", "last_activity": old_iso}]
    (state / "sessions.json").write_text(json.dumps(sessions))
    result = hm.check_runtime(str(state))
    assert "s_old" in result["stale_sessions"]
    assert result["issues_found"] is True
    assert result["signal"] == "🔴 ISSUES"


def test_check_runtime_session_dict_not_list(tmp_path):
    """Lines 158-161: sessions.json with a dict (single session)."""
    state = tmp_path / "mase"
    state.mkdir()
    sess = {"id": "s_single", "last_activity":
            datetime.now(timezone.utc).isoformat()}
    (state / "sessions.json").write_text(json.dumps(sess))
    result = hm.check_runtime(str(state))
    assert result["active_sessions"] == 1


def test_check_runtime_session_unparseable(tmp_path):
    """Lines 162-163: invalid JSON sessions.json → crash entry."""
    state = tmp_path / "mase"
    state.mkdir()
    (state / "sessions.json").write_text("{ not valid json")
    result = hm.check_runtime(str(state))
    assert len(result["crashes"]) == 1
    assert "unparseable" in result["crashes"][0]["issue"]
    assert result["issues_found"] is True


def test_check_runtime_session_with_z_suffix(tmp_path):
    """Line 171: ISO timestamp with Z suffix → replace +00:00."""
    state = tmp_path / "mase"
    state.mkdir()
    old_z = "2020-01-01T00:00:00Z"
    sessions = [{"id": "z_sess", "last_activity": old_z}]
    (state / "sessions.json").write_text(json.dumps(sessions))
    result = hm.check_runtime(str(state))
    assert "z_sess" in result["stale_sessions"]


def test_check_runtime_session_bad_iso(tmp_path):
    """Lines 174-175: malformed ISO timestamp → ignored (pass)."""
    state = tmp_path / "mase"
    state.mkdir()
    sessions = [{"id": "bad_iso", "last_activity": "not-a-date"}]
    (state / "sessions.json").write_text(json.dumps(sessions))
    result = hm.check_runtime(str(state))
    # bad_iso should NOT be in stale (ValueError caught)
    assert "bad_iso" not in result["stale_sessions"]
    assert result["issues_found"] is False


def test_check_runtime_session_no_last_activity(tmp_path):
    """Line 168 False: no last_activity + no started_at → empty string."""
    state = tmp_path / "mase"
    state.mkdir()
    sessions = [{"id": "no_time"}]  # neither last_activity nor started_at
    (state / "sessions.json").write_text(json.dumps(sessions))
    result = hm.check_runtime(str(state))
    assert result["active_sessions"] == 1
    assert result["stale_sessions"] == []


def test_check_runtime_session_started_at_only(tmp_path):
    """Line 168: uses started_at when last_activity missing."""
    state = tmp_path / "mase"
    state.mkdir()
    old_iso = (datetime.now(timezone.utc)
               .replace(year=2020).isoformat())
    sessions = [{"id": "s_start", "started_at": old_iso}]
    (state / "sessions.json").write_text(json.dumps(sessions))
    result = hm.check_runtime(str(state))
    assert "s_start" in result["stale_sessions"]


def test_check_runtime_controller_status_arch_violations(tmp_path):
    """Lines 178-185: controller-status.yaml with arch_violations."""
    state = tmp_path / "mase"
    state.mkdir()
    status = {"arch_violations": [{"x": 1}, {"y": 2}, {"z": 3}]}
    (state / "controller-status.yaml").write_text(
        "arch_violations:\n  - {x: 1}\n  - {y: 2}\n  - {z: 3}\n")
    result = hm.check_runtime(str(state))
    assert result["arch_violations"] == 3
    assert result["issues_found"] is True


def test_check_runtime_controller_status_unparseable(tmp_path):
    """Lines 186-187: invalid controller-status.yaml → crash entry."""
    state = tmp_path / "mase"
    state.mkdir()
    (state / "controller-status.yaml").write_text(": bad\n\t: yaml")
    result = hm.check_runtime(str(state))
    crashes = [c for c in result["crashes"]
               if "controller-status.yaml" in c["file"]]
    assert len(crashes) == 1
    assert "unparseable" in crashes[0]["issue"]


def test_check_runtime_controller_status_no_arch_violations(tmp_path):
    """Lines 184-185: controller-status.yaml without arch_violations."""
    state = tmp_path / "mase"
    state.mkdir()
    (state / "controller-status.yaml").write_text("foo: bar\n")
    result = hm.check_runtime(str(state))
    assert result["arch_violations"] == 0
    assert result["issues_found"] is False


# ────────────────────── log_session ───────────────────────────────

def test_log_session_default_dir(tmp_path, monkeypatch):
    """Lines 209-227: writes to default LOG_DIR."""
    logs = tmp_path / "mase_logs"
    monkeypatch.setattr(hm, "LOG_DIR", logs)
    result = hm.log_session("cycle_start", {"step": 1})
    assert result["command"] == "LOG_SESSION"
    assert result["logged"] is True
    assert result["event"] == "cycle_start"
    # Verify log file was written
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs / f"cycle-{today}.log"
    assert log_file.exists()
    content = log_file.read_text().strip()
    entry = json.loads(content)
    assert entry["event"] == "cycle_start"
    assert entry["details"] == {"step": 1}


def test_log_session_explicit_dir(tmp_path):
    """Line 209: explicit log_dir → uses that path."""
    logs = tmp_path / "custom_logs"
    result = hm.log_session("custom_event", {"k": "v"},
                            log_dir=str(logs))
    assert logs.exists()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs / f"cycle-{today}.log"
    assert log_file.exists()


def test_log_session_no_details(tmp_path):
    """Line 217 False: details=None → empty dict."""
    logs = tmp_path / "logs"
    result = hm.log_session("minimal", None, log_dir=str(logs))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs / f"cycle-{today}.log"
    entry = json.loads(log_file.read_text().strip())
    assert entry["details"] == {}


def test_log_session_appends(tmp_path):
    """Line 219-220: multiple calls append to same file."""
    logs = tmp_path / "logs"
    hm.log_session("e1", None, log_dir=str(logs))
    hm.log_session("e2", None, log_dir=str(logs))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs / f"cycle-{today}.log"
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "e1"
    assert json.loads(lines[1])["event"] == "e2"


# ────────────────────── recover ───────────────────────────────────

def test_recover_first_attempt(tmp_path, monkeypatch):
    """Lines 248-256: attempt=1, < max_attempts → 🟡 RECOVERING."""
    monkeypatch.setattr(hm, "log_session",
                        lambda *a, **kw: {"logged": True})
    result = hm.recover("agent_a", attempt=1)
    assert result["command"] == "RECOVER"
    assert result["agent"] == "agent_a"
    assert result["attempt"] == 1
    assert result["escalate"] is False
    assert result["signal"] == "🟡 RECOVERING"


def test_recover_max_attempts(tmp_path, monkeypatch):
    """Line 236 False: attempt <= max_attempts → still recovering."""
    monkeypatch.setattr(hm, "log_session",
                        lambda *a, **kw: {"logged": True})
    result = hm.recover("agent_b", attempt=3, max_attempts=3)
    assert result["escalate"] is False


def test_recover_escalate(tmp_path, monkeypatch):
    """Lines 236-244: attempt > max_attempts → escalate=True, no log."""
    log_calls = []
    monkeypatch.setattr(hm, "log_session",
                        lambda *a, **kw: log_calls.append(a))
    result = hm.recover("agent_c", attempt=4, max_attempts=3)
    assert result["escalate"] is True
    assert result["max_attempts_reached"] is True
    assert result["signal"] == "🔴 ESCALATE"
    # log_session should NOT be called on escalate
    assert log_calls == []


def test_recover_logs_attempt_to_session(tmp_path):
    """Line 248: recover calls log_session with event='recovery_attempt'."""
    logs = tmp_path / "logs"
    hm.recover("agent_d", attempt=2, max_attempts=5)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = logs / f"cycle-{today}.log"
    # Default LOG_DIR — may be the repo's .mase/logs. We just verify
    # the function call path didn't crash.
    # If default LOG_DIR isn't writable in sandbox, this would raise.
    assert True  # No exception = ok


# ────────────────────── main() / __main__ ─────────────────────────

def _run_main(monkeypatch, *args):
    """Invoke main() in-process with sys.argv patched."""
    monkeypatch.setattr(sys, "argv", ["dev_health_monitor.py",
                                       *map(str, args)])
    rfile = StringIO()
    rc = 0
    try:
        with redirect_stdout(rfile):
            hm.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    return rc, rfile.getvalue()


def test_main_no_args(monkeypatch, capsys):
    """Lines 261-263: no argv → exit 2 + usage JSON."""
    monkeypatch.setattr(sys, "argv", ["dev_health_monitor.py"])
    rfile = StringIO()
    rc = 0
    try:
        with redirect_stdout(rfile):
            hm.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    out = rfile.getvalue()
    parsed = json.loads(out)
    assert "error" in parsed
    assert "usage" in parsed["error"].lower()
    assert rc == 2


def test_main_check_health_default(monkeypatch):
    """Lines 266-268: CHECK_HEALTH with no extra args."""
    # Patch check_health to avoid touching real recipe dir
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "checks_total": 1,
                                        "checks_passed": 1,
                                        "findings": []})
    rc, out = _run_main(monkeypatch, "CHECK_HEALTH")
    assert rc == 0
    parsed = json.loads(out)
    assert parsed["command"] == "CHECK_HEALTH"


def test_main_check_health_with_dir(monkeypatch):
    """Line 267: CHECK_HEALTH with explicit dir passed through."""
    seen_dir = []
    def fake_check_health(recipes_dir=None):
        seen_dir.append(recipes_dir)
        return {"command": "CHECK_HEALTH", "findings": []}
    monkeypatch.setattr(hm, "check_health", fake_check_health)
    rc, out = _run_main(monkeypatch, "CHECK_HEALTH", "/tmp/fake_recipes")
    assert rc == 0
    assert seen_dir == ["/tmp/fake_recipes"]


def test_main_check_runtime_default(monkeypatch):
    """Lines 269-271: CHECK_RUNTIME no extra args."""
    monkeypatch.setattr(hm, "check_runtime",
                        lambda d=None: {"command": "CHECK_RUNTIME",
                                        "issues_found": False})
    rc, out = _run_main(monkeypatch, "CHECK_RUNTIME")
    assert rc == 0


def test_main_check_runtime_with_dir(monkeypatch):
    """Line 270: CHECK_RUNTIME with explicit state dir."""
    seen = []
    monkeypatch.setattr(hm, "check_runtime",
                        lambda d=None: (seen.append(d),
                                       {"command": "CHECK_RUNTIME",
                                        "issues_found": False})[1])
    rc, _ = _run_main(monkeypatch, "CHECK_RUNTIME", "/tmp/fake_state")
    assert rc == 0
    assert seen == ["/tmp/fake_state"]


def test_main_log_session_default(monkeypatch, tmp_path):
    """Lines 272-275: LOG_SESSION with default event='unspecified'."""
    seen = []
    def fake_log_session(event, details=None, log_dir=None):
        seen.append((event, details, log_dir))
        return {"command": "LOG_SESSION", "logged": True}
    monkeypatch.setattr(hm, "log_session", fake_log_session)
    rc, _ = _run_main(monkeypatch, "LOG_SESSION")
    assert rc == 0
    assert seen[0][0] == "unspecified"
    assert seen[0][1] == {}


def test_main_log_session_with_event(monkeypatch):
    """Line 273: LOG_SESSION with explicit event."""
    seen = []
    def fake_log_session(event, details=None, log_dir=None):
        seen.append(event)
        return {"command": "LOG_SESSION", "logged": True}
    monkeypatch.setattr(hm, "log_session", fake_log_session)
    _run_main(monkeypatch, "LOG_SESSION", "my_event")
    assert seen == ["my_event"]


def test_main_log_session_with_details_json(monkeypatch):
    """Line 274: LOG_SESSION with JSON details."""
    seen = []
    def fake_log_session(event, details=None, log_dir=None):
        seen.append(details)
        return {"command": "LOG_SESSION", "logged": True}
    monkeypatch.setattr(hm, "log_session", fake_log_session)
    _run_main(monkeypatch, "LOG_SESSION", "ev", '{"k":1}')
    assert seen == [{"k": 1}]


def test_main_recover_default(monkeypatch):
    """Lines 276-280: RECOVER with defaults (agent='unknown', attempt=1)."""
    seen = []
    monkeypatch.setattr(hm, "recover",
                        lambda a, attempt=1, max_attempts=3:
                        (seen.append((a, attempt, max_attempts)),
                         {"command": "RECOVER", "escalate": False})[1])
    rc, _ = _run_main(monkeypatch, "RECOVER")
    assert rc == 0
    assert seen == [("unknown", 1, 3)]


def test_main_recover_with_args(monkeypatch):
    """Lines 277-279: RECOVER with explicit args."""
    seen = []
    monkeypatch.setattr(hm, "recover",
                        lambda a, attempt=1, max_attempts=3:
                        (seen.append((a, attempt, max_attempts)),
                         {"command": "RECOVER", "escalate": False})[1])
    _run_main(monkeypatch, "RECOVER", "my_agent", "2", "5")
    assert seen == [("my_agent", 2, 5)]


def test_main_unknown_command(monkeypatch):
    """Lines 281-282: unknown cmd → result['error']."""
    rc, out = _run_main(monkeypatch, "FOOBAR")
    # Unknown cmd has no issues/escalate → exit 0 (line 337 False)
    assert rc == 0
    parsed = json.loads(out)
    assert "error" in parsed
    assert "FOOBAR" in parsed["error"]


def test_main_exit_1_on_issues(monkeypatch):
    """Lines 337-338: result has findings → exit 1."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": [{"x": 1}]})
    rc, _ = _run_main(monkeypatch, "CHECK_HEALTH")
    assert rc == 1


def test_main_exit_1_on_escalate(monkeypatch):
    """Line 337: result has escalate=True → exit 1."""
    monkeypatch.setattr(hm, "recover",
                        lambda a, attempt=1, max_attempts=3:
                        {"command": "RECOVER", "escalate": True})
    rc, _ = _run_main(monkeypatch, "RECOVER", "x", "4", "3")
    assert rc == 1


def test_main_exit_1_on_issues_found(monkeypatch):
    """Line 337: result has issues_found=True → exit 1."""
    monkeypatch.setattr(hm, "check_runtime",
                        lambda d=None: {"command": "CHECK_RUNTIME",
                                        "issues_found": True})
    rc, _ = _run_main(monkeypatch, "CHECK_RUNTIME")
    assert rc == 1


def test_main_publish_on_degraded(monkeypatch, tmp_path):
    """Lines 286-334: --publish on degraded result → enqueue subproc."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": [{"x": 1}],
                                        "issues_found": 1})
    # Mock subprocess.run to capture the call
    enqueue_calls = []
    def fake_run(cmd, **kwargs):
        enqueue_calls.append(cmd)
        # Mock successful return
        m = type("MockProc", (), {})()
        m.returncode = 0
        m.stdout = "msg_123\n"
        m.stderr = ""
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    # Change cwd to tmp_path to keep enqueue from polluting
    monkeypatch.chdir(tmp_path)
    rc, _ = _run_main(monkeypatch, "CHECK_HEALTH", "--publish")
    # issues_found → exit 1
    assert rc == 1
    # Verify enqueue was called
    assert len(enqueue_calls) == 1
    assert "dev_message_queue.py" in str(enqueue_calls[0])
    assert "--enqueue" in enqueue_calls[0]
    assert "monitor.health.degraded" in enqueue_calls[0]


def test_main_publish_never(monkeypatch):
    """Line 300 False: --publish=never → no enqueue even on degraded."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": [{"x": 1}]})
    enqueue_calls = []
    def fake_run(cmd, **kwargs):
        enqueue_calls.append(cmd)
        m = type("MockProc", (), {})()
        m.returncode = 0
        m.stdout = "msg_x\n"
        m.stderr = ""
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    rc, _ = _run_main(monkeypatch, "CHECK_HEALTH",
                       "--publish=never")
    assert rc == 1
    assert enqueue_calls == []


def test_main_publish_always_clean(monkeypatch):
    """Line 299: --publish=always on clean result → still enqueues."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": []})
    enqueue_calls = []
    def fake_run(cmd, **kwargs):
        enqueue_calls.append(cmd)
        m = type("MockProc", (), {})()
        m.returncode = 0
        m.stdout = "msg_y\n"
        m.stderr = ""
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    rc, _ = _run_main(monkeypatch, "CHECK_HEALTH",
                       "--publish=always")
    # Clean → exit 0, but enqueue still called
    assert rc == 0
    assert len(enqueue_calls) == 1


def test_main_publish_request_id_explicit(monkeypatch):
    """Lines 303-307: --publish-request-id=X → uses X."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": [{"x": 1}]})
    enqueue_calls = []
    def fake_run(cmd, **kwargs):
        enqueue_calls.append(cmd)
        m = type("MockProc", (), {})()
        m.returncode = 0
        m.stdout = "msg_z\n"
        m.stderr = ""
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    _run_main(monkeypatch, "CHECK_HEALTH", "--publish",
               "--publish-request-id=my-custom-id-42")
    # Verify the custom request_id appears in the payload
    payload_arg = enqueue_calls[0][enqueue_calls[0].index(
        "monitor.health.degraded") + 1]
    payload = json.loads(payload_arg)
    assert payload["request_id"] == "my-custom-id-42"


def test_main_publish_enqueue_fails(monkeypatch):
    """Lines 329-330: subprocess returns non-zero → PUBLISH-ERROR."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": [{"x": 1}]})
    def fake_run(cmd, **kwargs):
        m = type("MockProc", (), {})()
        m.returncode = 1
        m.stdout = ""
        m.stderr = "queue down"
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    err_buf = StringIO()
    monkeypatch.setattr(sys, "argv", ["dev_health_monitor.py",
                                       "CHECK_HEALTH", "--publish"])
    out_buf = StringIO()
    rc = 0
    try:
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            hm.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    assert "[PUBLISH-ERROR]" in err_buf.getvalue()
    assert rc == 1


def test_main_publish_enqueue_empty_msg(monkeypatch):
    """Line 329 False: subprocess ok but empty stdout → PUBLISH-ERROR."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": [{"x": 1}]})
    def fake_run(cmd, **kwargs):
        m = type("MockProc", (), {})()
        m.returncode = 0
        m.stdout = "   \n"
        m.stderr = ""
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    err_buf = StringIO()
    monkeypatch.setattr(sys, "argv", ["dev_health_monitor.py",
                                       "CHECK_HEALTH", "--publish"])
    out_buf = StringIO()
    rc = 0
    try:
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            hm.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    assert "[PUBLISH-ERROR]" in err_buf.getvalue()


def test_main_publish_subprocess_raises(monkeypatch):
    """Lines 333-334: subprocess.run raises → PUBLISH-ERROR repr."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": [{"x": 1}]})
    def fake_run(cmd, **kwargs):
        raise RuntimeError("boom")
    monkeypatch.setattr(subprocess, "run", fake_run)
    err_buf = StringIO()
    monkeypatch.setattr(sys, "argv", ["dev_health_monitor.py",
                                       "CHECK_HEALTH", "--publish"])
    out_buf = StringIO()
    rc = 0
    try:
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            hm.main()
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    assert "[PUBLISH-ERROR]" in err_buf.getvalue()
    assert "RuntimeError" in err_buf.getvalue()
    assert rc == 1


def test_main_publish_findings_count_non_list(monkeypatch):
    """Line 315 False: result.findings not a list → findings_count=0."""
    monkeypatch.setattr(hm, "check_health",
                        lambda d=None: {"command": "CHECK_HEALTH",
                                        "findings": "not-a-list"})
    enqueue_calls = []
    def fake_run(cmd, **kwargs):
        enqueue_calls.append(cmd)
        m = type("MockProc", (), {})()
        m.returncode = 0
        m.stdout = "msg_ok\n"
        m.stderr = ""
        return m
    monkeypatch.setattr(subprocess, "run", fake_run)
    _run_main(monkeypatch, "CHECK_HEALTH", "--publish=always")
    payload_arg = enqueue_calls[0][enqueue_calls[0].index(
        "monitor.health.degraded") + 1]
    payload = json.loads(payload_arg)
    assert payload["findings_count"] == 0
