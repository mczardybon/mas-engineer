"""R110-542 — coverage test sprint: tools/dev_app_builder.py 0%→100%.

Unit tests for the dashboard status generator that builds
mas-dashboard-status.json from a workspace. Tests use a full
fake_workspace fixture with all expected sub-dirs, so the SUT
runs end-to-end without touching the real repo.

Coverage of 428 LOC / 6 functions:
  - shell (lines 14-18): subprocess wrapper, fallback on exception
  - get_git_log (lines 21-27): git log parser with optional path filter
  - build_status (lines 30-352): the massive aggregator (~10 sections)
  - update_history (lines 355-384): append to bounded history
  - generate_status (lines 387-392): build + history + write json
  - __main__ block (lines 398-428): --workspace, --generate, --init, default

SUT mode switches (line 253 has `or True` which always fires) mean
the user-framework path is always explored. We mock subprocess to
avoid spawning real processes.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_app_builder as ab


# ────────────────────── shell() ───────────────────────────────────

def test_shell_returns_stdout():
    """Lines 14-18: r.stdout.strip() returned."""
    fake = MagicMock()
    fake.stdout = "  hello world\n  "
    with patch.object(subprocess, "run", return_value=fake):
        assert ab.shell("echo hi") == "hello world"


def test_shell_fallback_on_exception():
    """Line 18: subprocess raises → ''."""
    with patch.object(subprocess, "run", side_effect=OSError("boom")):
        assert ab.shell("false") == ""


def test_shell_fallback_on_timeout():
    """Line 18: TimeoutExpired → ''."""
    with patch.object(subprocess, "run",
                      side_effect=subprocess.TimeoutExpired("x", 1)):
        assert ab.shell("sleep 99", timeout=1) == ""


# ────────────────────── get_git_log() ────────────────────────────

def test_get_git_log_basic():
    """Lines 21-27: parses newlines, skips empty."""
    fake = MagicMock()
    fake.stdout = "abc123 commit one\ndef456 commit two\n\n"
    with patch.object(subprocess, "run", return_value=fake) as rmock:
        result = ab.get_git_log("/tmp", 5)
    assert result == ["abc123 commit one", "def456 commit two"]
    # Verify command construction
    args, kwargs = rmock.call_args
    cmd = args[0]
    assert cmd[0:3] == ["git", "log", "--oneline"]
    assert "--no-decorate" in cmd
    assert "-5" in cmd
    assert kwargs["cwd"] == "/tmp"
    assert kwargs["timeout"] == 5


def test_get_git_log_with_filter_path():
    """Line 23: filter_path adds '-- <path>' to git log."""
    fake = MagicMock()
    fake.stdout = "x commit\n"
    with patch.object(subprocess, "run", return_value=fake) as rmock:
        ab.get_git_log("/tmp", 3, filter_path="framework/")
    cmd = rmock.call_args[0][0]
    assert cmd[-2:] == ["--", "framework/"]


def test_get_git_log_exception_fallback():
    """Line 27: subprocess error → []."""
    with patch.object(subprocess, "run", side_effect=OSError("not a repo")):
        assert ab.get_git_log("/nonexistent") == []


def test_get_git_log_empty_output():
    """Empty stdout → split('\n') gives [''] → filtered → []."""
    fake = MagicMock()
    fake.stdout = ""
    with patch.object(subprocess, "run", return_value=fake):
        assert ab.get_git_log("/tmp", 5) == []


# ────────────────────── fake_workspace fixture ────────────────────

@pytest.fixture
def fake_workspace(tmp_path, monkeypatch):
    """Build a complete workspace dir tree that build_status() expects:

      <ws>/mas-engineer/.mase/guardian.yaml
      <ws>/mas-engineer/.mase/changes.json
      <ws>/mas-engineer/.mase/checkpoints/  (with subdirs)
      <ws>/mas-engineer/tools/dev_*.py  (incl. dev_dispatch_tracker.py)
      <ws>/mas-engineer/tools/dev_paralll.py
      <ws>/mas-engineer/recipe/sub/sub_mas-*.yaml
      <ws>/mas-engineer/docs/improve-log.md
      <ws>/mas-engineer/docs/session-analysis-report.md
      <ws>/framework/dev-team/recipes/specialist_*.yaml
      <ws>/framework/dev-team/config.yaml
      <ws>/framework/<user_folder>/recipes/foo.yaml
      <ws>/framework/<user_folder>/config.yaml
      <ws>/dist/mas-framework-*.zip
      <ws>/.mas-mode (optional)
    """
    ws = tmp_path
    mas = ws / "mas-engineer"
    mas.mkdir()
    state = mas / ".mase"
    state.mkdir()
    ckpt = state / "checkpoints"
    ckpt.mkdir()
    (ckpt / "ckpt-old").mkdir()
    (ckpt / "ckpt-new").mkdir()
    (ckpt / "lost+found.txt").write_text("x")  # non-dir entry ignored

    tools = mas / "tools"
    tools.mkdir()
    (tools / "dev_dispatch_tracker.py").write_text("# tracker")
    (tools / "dev_paralll.py").write_text(
        "max_paralll = 12\nfoo = 'max 12'")
    (tools / "dev_health.py").write_text("# tool1")
    (tools / "dev_audit.sh").write_text("# shell tool")
    (tools / "dev_sec.py").write_text("# tool2")

    sub = mas / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-foo.yaml").write_text(
        "name: foo\nversion: '1.0'\ndescription: foo agent\n")
    (sub / "sub_mas-bar.yaml").write_text(
        "name: bar\nversion: '2.0'\ndescription: bar agent\n")
    (sub / "sub_mas-bad.yaml").write_text(
        "name: bad\n  invalid: : :\n\tindent\n")  # yaml-broken

    docs = mas / "docs"
    docs.mkdir()
    (docs / "improve-log.md").write_text(
        "# Improve Log\n"
        "\n## Run 1 — first\n"
        "line1\nline2\n"
        "\n## Run 2 — second\n"
        "line3\n"
    )
    (docs / "session-analysis-report.md").write_text(
        "| Metrik | Wert | Extra |\n"
        "|---|---|---|\n"
        "| Gesamtsessions | 42 | x |\n"
        "| Total-Tokens | 1000 | x |\n"
        "| Gesamtkosten | $5.00 | x |\n"
        "| Activitysdauer | 24h | x |\n"
    )

    # Framework dev-team
    fw = ws / "framework"
    fw.mkdir()
    recipes = fw / "dev-team" / "recipes"
    recipes.mkdir(parents=True)
    (recipes / "specialist_researcher.yaml").write_text("name: r\n")
    (recipes / "specialist_writer.yaml").write_text("name: w\n")
    (recipes / "sub_helper.yaml").write_text("name: h\n")
    (recipes / "core_main.yaml").write_text("name: m\n")
    (recipes / "old_recipe.bak").write_text("name: skip\n")
    (fw / "dev-team" / "config.yaml").write_text(
        "active_provider: openai\n"
        "providers:\n"
        "  openai:\n"
        "    model: gpt-4\n"
        "extensions:\n"
        "  knowledge:\n"
        "    enabled: true\n"
        "  unused:\n"
        "    enabled: false\n"
    )

    # User framework folder
    user_fw = fw / "user-proj"
    user_fw.mkdir()
    user_recipes = user_fw / "recipes"
    user_recipes.mkdir()
    (user_recipes / "a.yaml").write_text("x")
    (user_recipes / "b.yaml").write_text("x")
    (user_recipes / "c.yaml").write_text("x")
    (user_fw / "config.yaml").write_text(
        "active_provider: anthropic\n"
        "providers:\n"
        "  anthropic:\n"
        "    model: claude-3\n"
    )

    # Mode file
    (ws / ".mas-mode").write_text("mas\n")

    # dist zips
    dist = ws / "dist"
    dist.mkdir()
    (dist / "mas-framework-0.1.zip").write_bytes(b"x" * 1024)
    (dist / "mas-framework-0.2.zip").write_bytes(b"x" * 2048)
    (dist / "mas-framework-0.3.zip").write_bytes(b"x" * 4096)

    # Guardian yaml (so guardian_data gets populated)
    (state / "guardian.yaml").write_text(
        "guardian:\n"
        "  agents:\n"
        "    sub_mas-foo:\n"
        "      status: healthy\n"
        "      prompt_score: 9.8\n"
        "      last_ok: '2026-09-14T10:00:00Z'\n"
        "    sub_mas-bar:\n"
        "      status: degraded\n"
        "      prompt_score: 7.2\n"
        "      last_ok: '2026-09-13T08:00:00Z'\n"
    )

    # Changes json
    (state / "changes.json").write_text(json.dumps([
        {"action": "SI-RUN on agents", "timestamp": "2026-09-14T10:00:00Z"},
        {"action": "PROMPT-OPTIMIZE", "timestamp": "2026-09-13T10:00:00Z"},
        {"action": "REGEL update", "timestamp": "2026-09-12T10:00:00Z"},
        {"action": "APP build", "timestamp": "2026-09-11T10:00:00Z"},
        {"action": "MASTER-CONSTITUTION v2", "timestamp": "2026-09-10T10:00:00Z"},
        {"action": "FLEET run", "timestamp": "2026-09-09T10:00:00Z"},
        {"action": "FIX bug", "timestamp": "2026-09-08T10:00:00Z"},
        {"action": "CHECKPOINT save", "timestamp": "2026-09-07T10:00:00Z"},
        {"action": "FW- update", "timestamp": "2026-09-06T10:00:00Z"},
        {"action": "random other", "timestamp": "2026-09-05T10:00:00Z"},
    ]))

    # Redirect HISTORY_FILE to a per-test tmp path
    hist = tmp_path / "history.json"
    monkeypatch.setattr(ab, "HISTORY_FILE", str(hist))
    return ws


# ────────────────────── build_status() ───────────────────────────

def test_build_status_happy_path(fake_workspace):
    """Lines 30-352: full aggregator produces a complete result dict."""
    r = ab.build_status(str(fake_workspace))
    assert r["version"] == "1.0.0"
    assert r["mode"] == "mas"
    assert r["timestamp"].endswith("Z")
    # mas section
    mas = r["mas"]
    assert mas["agents"] == 3  # foo, bar, bad (still listed)
    assert mas["agent_health"]["total"] == 2  # only foo+bar in guardian
    assert mas["agent_health"]["healthy"] == 1
    assert mas["agent_health"]["degraded"] == 1
    assert mas["changes"] == 10
    assert mas["checkpoints"] == 2
    assert mas["tools"] == 5  # dev_dispatch_tracker.py + dev_paralll.py
                               # + dev_health.py + dev_audit.sh + dev_sec.py
    assert mas["fleet_active"] is True
    assert mas["fleet_max_paralll"] == 12
    assert mas["general_improve"]["total_runs"] == 2
    assert "Run 2" in mas["general_improve"]["last_run"]
    # Session stats extracted
    assert mas["session_stats"]["total_sessions"] == "42"
    assert mas["session_stats"]["total_tokens"] == "1000"
    assert mas["session_stats"]["total_cost"] == "$5.00"
    assert mas["session_stats"]["active_hours"] == "24h"
    # Build info from dist zips
    assert mas["build"]["exists"] is True
    assert mas["build"]["count"] == 3
    assert mas["build"]["latest"]["name"] == "mas-framework-0.3.zip"
    assert mas["build"]["latest"]["size_kb"] >= 4
    assert "size_trend" in mas["build"]
    assert "weekly_count" in mas["build"]
    # Framework section
    fw = r["framework"]
    assert fw["recipes"]["total"] == 4  # 2 specialist + 1 sub + 1 core
    assert fw["recipes"]["specialists"] == 2
    assert fw["recipes"]["subs"] == 1
    assert fw["recipes"]["core"] == 1
    assert fw["config"]["provider"] == "openai"
    assert fw["config"]["model"] == "gpt-4"
    assert fw["config"]["extensions"] == ["knowledge"]  # enabled only
    # User framework
    uf = r["user_framework"]
    assert uf["detected"] is True
    assert uf["name"] == "user-proj"
    assert uf["recipes"] == 3
    assert uf["config_provider"] == "anthropic"
    assert uf["config_model"] == "claude-3"
    # Actions menu
    assert len(r["actions"]) == 8
    assert any(a["id"] == "test" for a in r["actions"])


def test_build_status_no_mode_file_uses_default(tmp_path, monkeypatch):
    """Line 41: missing .mas-mode → default 'mas'."""
    ws = tmp_path
    (ws / "mas-engineer").mkdir()
    (ws / "framework").mkdir()
    monkeypatch.setattr(ab, "HISTORY_FILE",
                        str(tmp_path / "history.json"))
    r = ab.build_status(str(ws))
    assert r["mode"] == "mas"


def test_build_status_custom_mode(tmp_path, monkeypatch):
    """Line 41: .mas-mode contains 'dev' → mode='dev'."""
    ws = tmp_path
    (ws / ".mas-mode").write_text("dev\n")
    (ws / "mas-engineer").mkdir()
    (ws / "framework").mkdir()
    monkeypatch.setattr(ab, "HISTORY_FILE",
                        str(tmp_path / "history.json"))
    r = ab.build_status(str(ws))
    assert r["mode"] == "dev"


def test_build_status_no_agents(fake_workspace, monkeypatch):
    """Lines 44-47: empty recipe/sub → agents=[].

    Also remove guardian.yaml so no orphan health entries."""
    sub = fake_workspace / "mas-engineer" / "recipe" / "sub"
    for f in sub.glob("sub_mas-*.yaml"):
        f.unlink()
    (fake_workspace / "mas-engineer" / ".mase" / "guardian.yaml").unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["agents"] == 0
    # When agents=0, prompt_avg=0
    assert r["mas"]["prompt_score_avg"] == 0
    # guardian_data.total=0
    assert r["mas"]["agent_health"]["total"] == 0
    # No scores → no agents_at_10
    assert r["mas"]["agents_at_10"] == 0


def test_build_status_no_guardian_yaml(fake_workspace):
    """Lines 49-65: no guardian.yaml → empty guardian_data."""
    gf = fake_workspace / "mas-engineer" / ".mase" / "guardian.yaml"
    gf.unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["agent_health"]["total"] == 0
    assert r["mas"]["agent_health"]["healthy"] == 0
    assert r["mas"]["agent_health"]["degraded"] == 0
    assert r["mas"]["agent_health"]["details"] == []


def test_build_status_no_changes_json(fake_workspace):
    """Lines 99-107: no changes.json → changes=[]."""
    cf = fake_workspace / "mas-engineer" / ".mase" / "changes.json"
    cf.unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["changes"] == 0
    assert r["mas"]["changes_last"] == []
    assert r["mas"]["changes_by_type"] == {}


def test_build_status_no_checkpoints_dir(fake_workspace):
    """Lines 137-140: no checkpoints/ → cp_count=0."""
    cp = fake_workspace / "mas-engineer" / ".mase" / "checkpoints"
    # Empty + remove
    for f in cp.iterdir():
        if f.is_dir():
            f.rmdir()
        else:
            f.unlink()
    cp.rmdir()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["checkpoints"] == 0


def test_build_status_no_tools_dir(fake_workspace):
    """Lines 143-144: no tools dir → tool_count=0."""
    tools = fake_workspace / "mas-engineer" / "tools"
    for f in tools.glob("*"):
        f.unlink()
    tools.rmdir()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["tools"] == 0


def test_build_status_fleet_max12_text(fake_workspace):
    """Line 151: fleet_active=True when 'max 12' in dev_paralll.py."""
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["fleet_active"] is True


def test_build_status_fleet_inactive(fake_workspace):
    """Line 151 False: no max 12 → fleet_active=False."""
    pp = fake_workspace / "mas-engineer" / "tools" / "dev_paralll.py"
    pp.write_text("max_paralll = 6\nfoo = 'bar'\n")
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["fleet_active"] is False


def test_build_status_no_paralll_tool(fake_workspace):
    """Lines 147-148: no dev_paralll.py → fleet_active=False (no crash)."""
    pp = fake_workspace / "mas-engineer" / "tools" / "dev_paralll.py"
    pp.unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["fleet_active"] is False


def test_build_status_no_improve_log(fake_workspace):
    """Lines 154-167: no improve-log.md → si_run_count=0."""
    il = fake_workspace / "mas-engineer" / "docs" / "improve-log.md"
    il.unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["general_improve"]["total_runs"] == 0
    assert r["mas"]["general_improve"]["last_run"] == "No SI-RUN"
    assert r["mas"]["general_improve"]["log_entries"] == []


def test_build_status_no_session_analysis(fake_workspace):
    """Lines 170-184: no session-analysis-report.md → empty stats."""
    sa = fake_workspace / "mas-engineer" / "docs" / "session-analysis-report.md"
    sa.unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["session_stats"] == {}


def test_build_status_session_stats_no_pipe(monkeypatch, fake_workspace):
    """Lines 178,180,182,184: '|' not in line → '?' fallback.

    Need a line that contains the keyword but no '|' character."""
    sa = fake_workspace / "mas-engineer" / "docs" / "session-analysis-report.md"
    sa.write_text("Some Gesamtsessions text without pipe\n")
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["session_stats"]["total_sessions"] == "?"


def test_build_status_framework_recipes_dir_missing(fake_workspace):
    """Lines 192-201: no dev-team/recipes/ → fw_recipes=0."""
    recipes = fake_workspace / "framework" / "dev-team" / "recipes"
    for f in recipes.glob("*"):
        f.unlink()
    recipes.rmdir()
    r = ab.build_status(str(fake_workspace))
    assert r["framework"]["recipes"]["total"] == 0
    assert r["framework"]["recipes"]["list"] == []


def test_build_status_framework_config_missing(fake_workspace):
    """Lines 203-210: no config.yaml → fw_config={}."""
    cfg = fake_workspace / "framework" / "dev-team" / "config.yaml"
    cfg.unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["framework"]["config"]["provider"] == "?"
    assert r["framework"]["config"]["model"] == "?"


def test_build_status_framework_config_empty_yaml(fake_workspace):
    """Line 209: yaml.safe_load returns None → or {}."""
    cfg = fake_workspace / "framework" / "dev-team" / "config.yaml"
    cfg.write_text("")  # empty
    r = ab.build_status(str(fake_workspace))
    assert r["framework"]["config"]["provider"] == "?"


def test_build_status_dispatch_tracker_missing(fake_workspace):
    """Lines 213-223: no dev_dispatch_tracker.py → dispatch stays default."""
    dt = fake_workspace / "mas-engineer" / "tools" / "dev_dispatch_tracker.py"
    dt.unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["dispatch"]["total"] == 0
    assert r["dispatch"]["running"] == 0


def test_build_status_dispatch_tracker_success(fake_workspace):
    """Lines 217-222: subprocess returns valid JSON → dispatch populated."""
    dt = fake_workspace / "mas-engineer" / "tools" / "dev_dispatch_tracker.py"
    dt.write_text("# tracker\n")
    # Mock subprocess to return our JSON
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = json.dumps({
        "total": 42, "running": 2, "done": 38, "errors": 2,
        "avg_duration_ms": 150, "tree": [{"id": 1}]
    })
    with patch.object(subprocess, "run", return_value=fake):
        r = ab.build_status(str(fake_workspace))
    assert r["dispatch"]["total"] == 42
    assert r["dispatch"]["running"] == 2
    assert r["dispatch"]["done"] == 38
    assert r["dispatch"]["errors"] == 2
    assert r["dispatch"]["avg_duration_ms"] == 150
    assert r["dispatch"]["tree"] == [{"id": 1}]


def test_build_status_dispatch_tracker_nonzero_rc(fake_workspace):
    """Line 218: r.returncode != 0 → keep default dispatch."""
    dt = fake_workspace / "mas-engineer" / "tools" / "dev_dispatch_tracker.py"
    dt.write_text("# tracker\n")
    fake = MagicMock()
    fake.returncode = 1
    fake.stdout = ""
    with patch.object(subprocess, "run", return_value=fake):
        r = ab.build_status(str(fake_workspace))
    assert r["dispatch"]["total"] == 0


def test_build_status_dispatch_tracker_raises(fake_workspace):
    """Lines 223: subprocess raises → keep default dispatch."""
    dt = fake_workspace / "mas-engineer" / "tools" / "dev_dispatch_tracker.py"
    dt.write_text("# tracker\n")
    with patch.object(subprocess, "run", side_effect=OSError("boom")):
        r = ab.build_status(str(fake_workspace))
    assert r["dispatch"]["total"] == 0


def test_build_status_no_dist_dir(fake_workspace):
    """Lines 226-228: no dist/ → build_info['exists']=False."""
    dist = fake_workspace / "dist"
    for f in dist.glob("*"):
        f.unlink()
    dist.rmdir()
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["build"]["exists"] is False
    assert r["mas"]["build"]["count"] == 0


def test_build_status_user_framework_no_recipes_dir(fake_workspace):
    """Lines 262-266: user folder exists but no recipes/ → count=0."""
    user = fake_workspace / "framework" / "user-proj"
    recipes = user / "recipes"
    for f in recipes.iterdir():
        f.unlink()
    recipes.rmdir()
    r = ab.build_status(str(fake_workspace))
    assert r["user_framework"]["detected"] is True
    assert r["user_framework"]["recipes"] == 0
    assert r["user_framework"]["recipe_list"] == []


def test_build_status_user_framework_no_config(fake_workspace):
    """Lines 267-271: no user config.yaml → provider='?'."""
    cfg = fake_workspace / "framework" / "user-proj" / "config.yaml"
    cfg.unlink()
    r = ab.build_status(str(fake_workspace))
    assert r["user_framework"]["config_provider"] == "?"
    assert r["user_framework"]["config_model"] == "?"


def test_build_status_no_user_framework(fake_workspace):
    """Lines 285-286: no user folder → user_fw.detected=False."""
    fw = fake_workspace / "framework" / "user-proj"
    for child in fw.rglob("*"):
        if child.is_file():
            child.unlink()
    # Remove subdirs
    for d in sorted(fw.rglob("*"), reverse=True):
        if d.is_dir():
            d.rmdir()
    fw.rmdir()
    r = ab.build_status(str(fake_workspace))
    assert r["user_framework"]["detected"] is False
    assert r["user_framework"]["workspace"] is None


def test_build_status_no_framework_dir(tmp_path, monkeypatch):
    """Line 254: no framework/ → user_fw.detected=False."""
    ws = tmp_path
    (ws / "mas-engineer").mkdir()
    monkeypatch.setattr(ab, "HISTORY_FILE",
                        str(tmp_path / "history.json"))
    r = ab.build_status(str(ws))
    assert r["user_framework"]["detected"] is False


def test_build_status_changes_categorization(fake_workspace):
    """Lines 110-134: all 9 change-type branches exercised."""
    r = ab.build_status(str(fake_workspace))
    by_type = r["mas"]["changes_by_type"]
    # 1 SI-RUN, 1 PROMPT-OPTIMIZE, 1 REGEL, 1 APP, 1 CONSTITUTION,
    # 1 FLEET, 1 FIX, 1 CHECKPOINT, 1 FW, 1 Other
    assert by_type.get("SI-RUN / Self-Improve") == 1
    assert by_type.get("Prompt-Optimierung") == 1
    assert by_type.get("Rule-Changes") == 1
    assert by_type.get("Dashboard / App") == 1
    assert by_type.get("Constitution") == 1
    assert by_type.get("Fleet mode") == 1
    assert by_type.get("Fixes") == 1
    assert by_type.get("Checkpoints") == 1
    assert by_type.get("Framework") == 1
    assert by_type.get("Other") == 1


def test_build_status_changes_last_truncates_to_15(fake_workspace):
    """Line 107: changes_last = changes[-15:]."""
    # Add 20 entries → should only see last 15
    cf = fake_workspace / "mas-engineer" / ".mase" / "changes.json"
    changes = [{"action": f"action-{i:02d}",
                "timestamp": f"2026-09-{i+1:02d}T10:00:00Z"}
               for i in range(20)]
    cf.write_text(json.dumps(changes))
    r = ab.build_status(str(fake_workspace))
    assert r["mas"]["changes"] == 20
    assert len(r["mas"]["changes_last"]) == 15
    # First entry is action-05 (index 5)
    assert r["mas"]["changes_last"][0]["action"] == "action-05"


def test_build_status_prompt_score_avg_and_at_10(fake_workspace):
    """Lines 96-97: average + count of scores >= 9.5.

    Note: SUT has a known key-mismatch (L73 strips 'sub_mas-', L78 keeps
    it), so all scores fall back to 0. Tests reflect actual behavior."""
    r = ab.build_status(str(fake_workspace))
    # avg of [0, 0, 0] = 0.0
    assert r["mas"]["prompt_score_avg"] == 0.0
    # No scores >= 9.5
    assert r["mas"]["agents_at_10"] == 0


def test_build_status_agent_scores_list(fake_workspace):
    """Lines 86-94: agent_scores list with name/score/version/description.

    Note: SUT has a known key-mismatch (L73 strips 'sub_mas-', L78 keeps
    it), so all scores fall back to 0 even for healthy agents."""
    r = ab.build_status(str(fake_workspace))
    scores = r["mas"]["agent_scores"]
    assert len(scores) == 3
    foo = next(s for s in scores if s["name"] == "sub_mas-foo")
    assert foo["version"] == "1.0"
    # description is parsed from yaml correctly
    assert foo["description"] == "foo agent"
    # But score falls back to 0 (key-mismatch bug)
    assert foo["score"] == 0
    # bad yaml fails to parse → version='?' description=''
    bad = next(s for s in scores if s["name"] == "sub_mas-bad")
    assert bad["version"] == "?"
    assert bad["description"] == ""
    assert bad["score"] == 0


def test_build_status_git_logs_mas_and_framework(fake_workspace):
    """Lines 187-188: get_git_log called twice (general + framework)."""
    fake = MagicMock()
    fake.stdout = "abc commit1\n"
    with patch.object(subprocess, "run", return_value=fake) as rmock:
        r = ab.build_status(str(fake_workspace))
    # 4 calls expected: get_git_log x2 + dispatch_tracker
    assert rmock.call_count >= 2
    mas_git = r["mas"]["git"]
    fw_git = r["framework"]["git"]
    assert mas_git == ["abc commit1"]
    assert fw_git == ["abc commit1"]


def test_build_status_user_fw_git(fake_workspace):
    """Line 272: user_fw git log uses framework/<folder>/ path."""
    fake = MagicMock()
    fake.stdout = "x y\n"
    with patch.object(subprocess, "run", return_value=fake) as rmock:
        r = ab.build_status(str(fake_workspace))
    uf_git_cmd = [c for c in rmock.call_args_list
                  if "framework/user-proj/" in str(c)]
    assert len(uf_git_cmd) >= 1


def test_build_status_size_trend_bounded(fake_workspace):
    """Line 246: size_trend = last 10 zips."""
    dist = fake_workspace / "dist"
    # Already 3 zips, add 8 more to test the [-10:] slice
    for i in range(8):
        (dist / f"mas-framework-1.{i}.zip").write_bytes(b"x" * 100)
    r = ab.build_status(str(fake_workspace))
    assert len(r["mas"]["build"]["size_trend"]) <= 10


# ────────────────────── update_history() ─────────────────────────

def test_update_history_first_run(fake_workspace):
    """Lines 355-384: append first health_trend entry."""
    r = ab.build_status(str(fake_workspace))
    hist = ab.update_history(r)
    assert len(hist["health_trend"]) == 1
    assert hist["health_trend"][0]["mas"] == 70  # has degraded
    assert hist["health_trend"][0]["framework"] == 100
    assert hist["dispatch_volume"][0]["count"] == 0  # no tracker
    # No dist build initially (history not yet written) — actually
    # build exists but update_history only runs in generate_status
    # which writes to file. Here we call update_history directly.
    # We didn't call generate_status, so HISTORY_FILE is empty.
    assert "build_size" in hist


def test_update_history_no_agents_health_zero(fake_workspace):
    """Line 369: total=0 → mas_health=0."""
    # Remove all guardian agents by removing guardian.yaml
    gf = fake_workspace / "mas-engineer" / ".mase" / "guardian.yaml"
    gf.unlink()
    r = ab.build_status(str(fake_workspace))
    hist = ab.update_history(r)
    assert hist["health_trend"][-1]["mas"] == 0


def test_update_history_all_healthy(fake_workspace):
    """Line 367: no degraded → mas_health=100."""
    # Make all guardian agents healthy
    gf = fake_workspace / "mas-engineer" / ".mase" / "guardian.yaml"
    gf.write_text("guardian:\n  agents:\n"
                  "    sub_mas-foo: {status: healthy, prompt_score: 9.8}\n"
                  "    sub_mas-bar: {status: healthy, prompt_score: 9.5}\n")
    r = ab.build_status(str(fake_workspace))
    hist = ab.update_history(r)
    assert hist["health_trend"][-1]["mas"] == 100


def test_update_history_bounded_to_48(fake_workspace):
    """Line 372: trend trimmed to last 48."""
    r = ab.build_status(str(fake_workspace))
    # Pre-populate history with 50 entries
    hist_path = ab.HISTORY_FILE
    existing = {"health_trend": [{"time": f"{i:02d}:00", "mas": 100,
                                  "framework": 100}
                                 for i in range(50)],
                "dispatch_volume": [], "build_size": []}
    Path(hist_path).write_text(json.dumps(existing))
    hist = ab.update_history(r)
    assert len(hist["health_trend"]) == 48


def test_update_history_existing_missing_keys(fake_workspace):
    """Lines 361-362: existing history missing keys → empty list,
    then new entry appended (each list = 1 entry)."""
    hist_path = ab.HISTORY_FILE
    Path(hist_path).write_text(json.dumps({"old_key": "x"}))
    r = ab.build_status(str(fake_workspace))
    hist = ab.update_history(r)
    # Each list now has 1 entry (empty list → append one)
    assert len(hist["health_trend"]) == 1
    assert len(hist["dispatch_volume"]) == 1
    assert len(hist["build_size"]) == 1


def test_update_history_corrupted_file_fallback(fake_workspace):
    """Lines 363-364: json.load fails → default empty history,
    then new entry appended (so result has exactly 1 entry)."""
    hist_path = ab.HISTORY_FILE
    Path(hist_path).write_text("not json {{{")
    r = ab.build_status(str(fake_workspace))
    hist = ab.update_history(r)
    # After fallback + append: each list has 1 entry
    assert len(hist["health_trend"]) == 1
    assert len(hist["dispatch_volume"]) == 1
    # build_size: depends on data (zips exist → 1)
    assert len(hist["build_size"]) == 1


def test_update_history_with_build_size(fake_workspace):
    """Lines 378-380: build.exists → build_size entry appended."""
    # build already exists in fake_workspace (3 zips)
    r = ab.build_status(str(fake_workspace))
    hist = ab.update_history(r)
    assert len(hist["build_size"]) == 1
    assert hist["build_size"][0]["kb"] > 0


def test_update_history_dispatch_volume(fake_workspace):
    """Line 374: dispatch.total → dispatch_volume entry."""
    # Mock dispatch tracker to return total=5
    dt = fake_workspace / "mas-engineer" / "tools" / "dev_dispatch_tracker.py"
    dt.write_text("# tracker\n")
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = json.dumps({"total": 5, "running": 0, "done": 5,
                              "errors": 0, "avg_duration_ms": 0, "tree": []})
    with patch.object(subprocess, "run", return_value=fake):
        r = ab.build_status(str(fake_workspace))
    hist = ab.update_history(r)
    assert hist["dispatch_volume"][-1]["count"] == 5


def test_update_history_write_file(fake_workspace):
    """Line 383: json.dump writes to HISTORY_FILE."""
    r = ab.build_status(str(fake_workspace))
    ab.update_history(r)
    assert os.path.exists(ab.HISTORY_FILE)
    data = json.loads(Path(ab.HISTORY_FILE).read_text())
    assert "health_trend" in data


# ────────────────────── generate_status() ────────────────────────

def test_generate_status_writes_json(fake_workspace):
    """Lines 387-392: build + history + write mas-dashboard-status.json."""
    r = ab.generate_status(str(fake_workspace))
    out_path = os.path.join(tempfile.gettempdir(), "mas-dashboard-status.json")
    assert os.path.exists(out_path)
    data = json.loads(Path(out_path).read_text())
    assert data["mas"]["agents"] == 3
    assert "history" in data
    assert len(data["history"]["health_trend"]) >= 1


def test_generate_status_history_attached(fake_workspace):
    """Line 389: result['history'] = update_history(...)."""
    r = ab.generate_status(str(fake_workspace))
    assert "history" in r
    assert "health_trend" in r["history"]


# ────────────────────── CLI block ────────────────────────────────

def test_main_default_prints_summary(fake_workspace, monkeypatch, capsys):
    """Lines 423-428: no args → build_status + print summary."""
    monkeypatch.chdir(fake_workspace)
    monkeypatch.setattr(sys, "argv", ["dev_app_builder.py"])
    ab.__name__ = "__main__"  # trick to enter __main__ block
    # We need to actually run the if __name__ == '__main__' block
    # Easier: extract and run
    with patch.object(sys, "argv", ["dev_app_builder.py"]):
        # Simulate by exec the __main__ block via a direct call
        import importlib
        import runpy
        sys.modules.pop("tools.dev_app_builder", None)
        runpy.run_module("tools.dev_app_builder", run_name="__main__")
    captured = capsys.readouterr()
    assert "Dashboard:" in captured.out
    assert "Agents" in captured.out


def test_main_with_workspace_arg(fake_workspace, monkeypatch, capsys):
    """Line 404-405: positional ws arg."""
    monkeypatch.chdir(fake_workspace)
    monkeypatch.setattr(sys, "argv",
                        ["dev_app_builder.py", str(fake_workspace)])
    import runpy
    sys.modules.pop("tools.dev_app_builder", None)
    runpy.run_module("tools.dev_app_builder", run_name="__main__")
    captured = capsys.readouterr()
    assert "Dashboard:" in captured.out


def test_main_with_workspace_flag(fake_workspace, monkeypatch, capsys):
    """Lines 401-403: --workspace <path>."""
    monkeypatch.setattr(sys, "argv",
                        ["dev_app_builder.py", "--workspace",
                         str(fake_workspace)])
    import runpy
    sys.modules.pop("tools.dev_app_builder", None)
    runpy.run_module("tools.dev_app_builder", run_name="__main__")
    captured = capsys.readouterr()
    assert "Dashboard:" in captured.out


def test_main_generate_flag(fake_workspace, monkeypatch, capsys):
    """Lines 407-412: --generate → JSON summary."""
    monkeypatch.setattr(sys, "argv",
                        ["dev_app_builder.py", "--workspace",
                         str(fake_workspace), "--generate"])
    import runpy
    sys.modules.pop("tools.dev_app_builder", None)
    runpy.run_module("tools.dev_app_builder", run_name="__main__")
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["status"] == "ok"
    assert "agents" in data
    assert "recipes" in data
    assert "dispatch" in data
    assert "si_runs" in data


def test_main_init_flag(fake_workspace, monkeypatch, capsys):
    """Lines 414-421: --init → verbose init output."""
    monkeypatch.setattr(sys, "argv",
                        ["dev_app_builder.py", "--workspace",
                         str(fake_workspace), "--init"])
    import runpy
    sys.modules.pop("tools.dev_app_builder", None)
    runpy.run_module("tools.dev_app_builder", run_name="__main__")
    captured = capsys.readouterr()
    assert "Initialisiert" in captured.out
    assert "Agents:" in captured.out
    assert "Improve-Runs:" in captured.out
    assert "FW-Rezepte:" in captured.out
    assert "Dispatch:" in captured.out
    assert "Builds:" in captured.out
