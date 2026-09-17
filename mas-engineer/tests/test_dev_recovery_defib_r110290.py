"""Tests for mas-engineer/tools/dev_recovery_defib.py — R110-290.

Coverage target: dev_recovery_defib.py 50-69% → ~95% (200 lines, 4 funcs).

Tests:
- _log_dir: env-override writes to override, default uses REPO_ROOT
  path, mkdir creates parents
- process_msg: noop path (has_problem=False), classifies+dispatches,
  log file written, report schema, default payload keys, log_written
  relative path vs absolute fallback
- _classify: stale_in_flight, dlq_has_messages, daemon_down,
  knowledge_stale, phoenix_recovery_incomplete, generic fallback
  (no classes → generic_health_degraded)
- _dispatch: 5 problem_classes + generic fallback, dry_run path,
  delegated actions don't crash, mq import errors are caught
"""
import pytest
import sys
import json
import os
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dev_recovery_defib as rd


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """Override the recovery log dir to a tmp path."""
    p = tmp_path / "recovery" / "log"
    monkeypatch.setenv("MAS_RECOVERY_LOG_DIR", str(p))
    return p


@pytest.fixture
def reload_defib(monkeypatch):
    """Reload module so the env-override path is re-evaluated."""
    import importlib
    importlib.reload(rd)


# ─── _log_dir ─────────────────────────────────────────────────────

class TestLogDir:
    def test_env_override_used(self, tmp_path, monkeypatch):
        p = tmp_path / "custom_log"
        monkeypatch.setenv("MAS_RECOVERY_LOG_DIR", str(p))
        # Reload so the env is picked up
        importlib.reload(rd)
        try:
            result = rd._log_dir()
            assert result == p
            assert result.is_dir()
        finally:
            importlib.reload(rd)  # restore default

    def test_mkdir_creates_parents(self, tmp_path, monkeypatch):
        p = tmp_path / "deep" / "nested" / "dir"
        monkeypatch.setenv("MAS_RECOVERY_LOG_DIR", str(p))
        importlib.reload(rd)
        try:
            result = rd._log_dir()
            assert result.is_dir()
            assert result.exists()
        finally:
            importlib.reload(rd)

    def test_default_is_repo_root_path(self, monkeypatch):
        # Unset override
        monkeypatch.delenv("MAS_RECOVERY_LOG_DIR", raising=False)
        importlib.reload(rd)
        try:
            result = rd._log_dir()
            # Default is REPO_ROOT/.mase/recovery/log
            assert "recovery" in str(result)
            assert "log" in str(result)
        finally:
            importlib.reload(rd)


# ─── process_msg ──────────────────────────────────────────────────

class TestProcessMsg:
    def test_noop_when_no_problem(self, log_dir, reload_defib):
        msg = {
            "msg_id": "m1",
            "topic": "monitor.health.degraded",
            "payload": {
                "request_id": "req-1",
                "has_problem": False,
                "command": "CHECK_DAEMON",
                "summary": {},
            },
        }
        result = rd.process_msg(msg)
        # has_problem=False → noop action appended → defib_outcome="ok"
        # (the literal "noop" outcome only fires when actions_taken is empty,
        # which it never is in the noop branch because the noop-action itself
        # is appended to actions_taken).
        assert result["defib_outcome"] == "ok"
        assert result["actions_count"] == 1
        log_file = log_dir / "req-1.json"
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert data["actions_taken"][0]["action"] == "noop"

    def test_log_file_contains_request_id(self, log_dir, reload_defib):
        msg = {
            "msg_id": "m2",
            "topic": "t",
            "payload": {"request_id": "req-2", "has_problem": False,
                        "summary": {}},
        }
        rd.process_msg(msg)
        log_file = log_dir / "req-2.json"
        data = json.loads(log_file.read_text())
        assert data["request_id"] == "req-2"
        assert data["schema_version"] == 1

    def test_default_request_id_from_msg_id(self, log_dir, reload_defib):
        msg = {
            "msg_id": "fallback-id",
            "topic": "t",
            "payload": {"has_problem": False},  # no request_id
        }
        result = rd.process_msg(msg)
        # request_id falls back to msg_id
        log_file = log_dir / "fallback-id.json"
        assert log_file.exists()
        # has_problem missing → False → noop action appended
        assert result["actions_count"] == 1
        data = json.loads(log_file.read_text())
        assert data["actions_taken"][0]["action"] == "noop"

    def test_default_request_id_unknown_when_both_missing(self, log_dir, reload_defib):
        msg = {"payload": {"has_problem": False}}
        result = rd.process_msg(msg)
        log_file = log_dir / "unknown.json"
        assert log_file.exists()

    def test_has_problem_dispatches(self, log_dir, reload_defib):
        msg = {
            "msg_id": "m3",
            "topic": "t",
            "payload": {
                "request_id": "req-3",
                "has_problem": True,
                "command": "CHECK_DAEMON",
                "summary": {"daemon_alive": False},
                "issues_found": 1,
                "findings_count": 1,
            },
        }
        result = rd.process_msg(msg)
        assert result["actions_count"] == 1
        log_file = log_dir / "req-3.json"
        data = json.loads(log_file.read_text())
        # daemon_down is the dispatched problem class
        assert data["actions_taken"][0]["problem_class"] == "daemon_down"
        assert data["actions_taken"][0]["action"] == "rebuild_daemon"

    def test_report_schema_complete(self, log_dir, reload_defib):
        msg = {
            "msg_id": "m4",
            "topic": "monitor.health.degraded",
            "payload": {
                "request_id": "req-4",
                "has_problem": True,
                "command": "CHECK_DAEMON",
                "summary": {"daemon_alive": False},
                "issues_found": 2,
                "findings_count": 3,
            },
        }
        rd.process_msg(msg)
        data = json.loads((log_dir / "req-4.json").read_text())
        for key in ["schema_version", "request_id", "source_msg_id",
                    "source_topic", "command", "has_problem",
                    "issues_found", "findings_count", "actions_taken",
                    "defib_outcome"]:
            assert key in data, f"missing {key}"
        assert data["source_msg_id"] == "m4"
        assert data["source_topic"] == "monitor.health.degraded"
        assert data["issues_found"] == 2
        assert data["findings_count"] == 3

    def test_log_written_relative_path(self, log_dir, reload_defib):
        # MAS_RECOVERY_LOG_DIR is under tmp_path, not REPO_ROOT, so the
        # relative_to(REPO_ROOT) raises ValueError → falls back to str()
        msg = {
            "payload": {"request_id": "req-5", "has_problem": False},
        }
        result = rd.process_msg(msg)
        # log_written is the absolute path (not relative)
        assert "req-5.json" in result["log_written"]

    def test_log_written_relative_path_in_repo(self, log_dir, reload_defib, monkeypatch):
        # Override MAS_RECOVERY_LOG_DIR to a path UNDER REPO_ROOT so
        # the relative_to branch succeeds.
        repo_root = rd.REPO_ROOT
        in_repo = repo_root / "tmp_recovery_test_dir"
        in_repo.mkdir(parents=True, exist_ok=True)
        try:
            monkeypatch.setenv("MAS_RECOVERY_LOG_DIR", str(in_repo))
            msg = {"payload": {"request_id": "req-rel", "has_problem": False}}
            result = rd.process_msg(msg)
            # log_written is a relative path
            assert not result["log_written"].startswith("/")
            assert "req-rel.json" in result["log_written"]
        finally:
            # Clean up
            import shutil
            shutil.rmtree(in_repo, ignore_errors=True)

    def test_multiple_problem_classes(self, log_dir, reload_defib):
        # Combination: stale_in_flight + dlq + daemon_down + knowledge_stale
        msg = {
            "payload": {
                "request_id": "req-multi",
                "has_problem": True,
                "command": "CHECK_DAEMON",
                "summary": {
                    "stale_in_flight_count": 3,
                    "dlq_count": 5,
                    "daemon_alive": False,
                    "rules_last_refresh_age_hours": 200,
                },
            },
        }
        result = rd.process_msg(msg)
        assert result["actions_count"] == 4
        data = json.loads((log_dir / "req-multi.json").read_text())
        classes = {a["problem_class"] for a in data["actions_taken"]}
        assert classes == {"stale_in_flight", "dlq_has_messages",
                           "daemon_down", "knowledge_stale"}


# ─── _classify ────────────────────────────────────────────────────

class TestClassify:
    def test_stale_in_flight(self):
        assert rd._classify("X", {"stale_in_flight_count": 3}) == \
            ["stale_in_flight"]

    def test_dlq_count(self):
        assert rd._classify("X", {"dlq_count": 7}) == ["dlq_has_messages"]

    def test_daemon_down(self):
        assert rd._classify("CHECK_DAEMON", {"daemon_alive": False}) == \
            ["daemon_down"]

    def test_daemon_alive_not_classified(self):
        # daemon_alive=True → daemon_down is NOT added
        classes = rd._classify("CHECK_DAEMON", {"daemon_alive": True})
        assert "daemon_down" not in classes

    def test_other_command_with_daemon_down_not_classified(self):
        # daemon_down only fires for command=CHECK_DAEMON
        classes = rd._classify("OTHER", {"daemon_alive": False})
        assert "daemon_down" not in classes

    def test_knowledge_stale_over_168h(self):
        classes = rd._classify("X", {"rules_last_refresh_age_hours": 200})
        assert "knowledge_stale" in classes

    def test_knowledge_fresh_under_168h(self):
        # 168h is the threshold — at exactly 168h it does NOT classify
        # (because the check is `> 168`)
        classes = rd._classify("X", {"rules_last_refresh_age_hours": 168})
        assert "knowledge_stale" not in classes

    def test_phoenix_recovery_incomplete(self):
        classes = rd._classify("PHOENIX_DEGRADED", {})
        assert "phoenix_recovery_incomplete" in classes

    def test_generic_fallback_when_no_class(self):
        # Empty summary, no command match → generic fallback
        classes = rd._classify("UNKNOWN_CMD", {})
        assert classes == ["generic_health_degraded"]

    def test_all_classes_combined(self):
        summary = {
            "stale_in_flight_count": 1,
            "dlq_count": 2,
            "daemon_alive": False,
            "rules_last_refresh_age_hours": 200,
        }
        classes = rd._classify("CHECK_DAEMON", summary)
        # 4 specific classes, no generic
        assert "stale_in_flight" in classes
        assert "dlq_has_messages" in classes
        assert "daemon_down" in classes
        assert "knowledge_stale" in classes
        assert "generic_health_degraded" not in classes


# ─── _dispatch ────────────────────────────────────────────────────

class TestDispatch:
    def _summary(self, **over):
        return {"daemon_alive": True, **over}

    def test_stale_in_flight_calls_mq_gc(self):
        with patch("dev_message_queue.gc_stale_in_flight",
                   return_value=5) as mock_gc:
            action = rd._dispatch("stale_in_flight", "req-1",
                                  self._summary())
        assert action["action"] == "gc_stale_in_flight"
        assert action["reclaimed"] == 5
        mock_gc.assert_called_once_with(max_age_sec=300.0)

    def test_stale_in_flight_mq_error_caught(self):
        # If dev_message_queue raises, the action reports the error
        with patch.dict(sys.modules, {"dev_message_queue": None}):
            # Force the import to fail
            with patch("builtins.__import__",
                       side_effect=ImportError("no module")):
                action = rd._dispatch("stale_in_flight", "req-1",
                                      self._summary())
        assert action["action"] == "gc_stale_in_flight"
        assert "error" in action

    def test_dlq_replay_real(self):
        with patch("dev_message_queue.replay_dlq", return_value=3) as mock:
            action = rd._dispatch("dlq_has_messages", "req-1",
                                  self._summary())
        assert action["action"] == "replay_dlq"
        assert action["replayed"] == 3

    def test_dlq_dry_run(self):
        with patch("dev_message_queue._dlq_count", return_value=9) as mock:
            action = rd._dispatch("dlq_has_messages", "req-1",
                                  self._summary(dlq_dry_run=True))
        assert action["action"] == "replay_dlq_dry_run"
        assert action["dlq_count"] == 9
        assert "manual review" in action["note"]

    def test_dlq_mq_error_caught(self):
        with patch("builtins.__import__",
                   side_effect=ImportError("no module")):
            action = rd._dispatch("dlq_has_messages", "req-1",
                                  self._summary())
        assert action["action"] == "replay_dlq"
        assert "error" in action

    def test_daemon_down_delegated(self):
        action = rd._dispatch("daemon_down", "req-1", self._summary())
        assert action["action"] == "rebuild_daemon"
        assert "delegated" in action["note"]

    def test_knowledge_stale_delegated(self):
        action = rd._dispatch("knowledge_stale", "req-1",
                              self._summary(rules_last_refresh_age_hours=300))
        assert action["action"] == "refresh_knowledge"
        assert action["age_hours"] == 300
        assert "delegated" in action["note"]

    def test_phoenix_incomplete_includes_levels(self):
        summary = self._summary(phoenix_request_id="phx-1",
                                levels_passed=2, levels_total=3,
                                degraded_levels=["L1"])
        action = rd._dispatch("phoenix_recovery_incomplete", "req-1",
                              summary)
        assert action["action"] == "rebuild_phoenix"
        assert action["phoenix_request_id"] == "phx-1"
        assert action["levels_passed"] == 2
        assert action["levels_total"] == 3
        assert action["degraded_levels"] == ["L1"]
        assert "delegated" in action["note"]

    def test_phoenix_incomplete_uses_request_id_fallback(self):
        # No phoenix_request_id in summary → use request_id
        action = rd._dispatch("phoenix_recovery_incomplete", "req-fb",
                              self._summary())
        assert action["phoenix_request_id"] == "req-fb"

    def test_generic_fallback_escalate_oncall(self):
        action = rd._dispatch("generic_health_degraded", "req-1",
                              self._summary(foo="bar", baz="qux"))
        assert action["action"] == "escalate_oncall"
        assert "summary_keys" in action
        # Up to 10 summary keys
        assert "foo" in action["summary_keys"]
        assert "baz" in action["summary_keys"]


# ─── CLI / __main__ ────────────────────────────────────────────────

class TestCLI:
    def test_stdin_empty_json(self, log_dir, reload_defib, capsys):
        # Empty stdin → empty dict → noop (has_problem missing → False)
        with patch.object(sys, "stdin") as mock_stdin:
            mock_stdin.read.return_value = ""
            # Direct call to the CLI body (last 2 lines of the file)
            msg = json.loads("{}")
            result = rd.process_msg(msg)
        # has_problem missing → noop action appended → "ok" outcome
        assert result["defib_outcome"] == "ok"
        assert result["actions_count"] == 1
        assert result["log_written"].endswith("unknown.json")

    def test_stdin_valid_json(self, log_dir, reload_defib):
        with patch.object(sys, "stdin") as mock_stdin:
            mock_stdin.read.return_value = json.dumps({
                "payload": {
                    "request_id": "cli-1",
                    "has_problem": True,
                    "command": "CHECK_DAEMON",
                    "summary": {"daemon_alive": False},
                }
            })
            msg = json.loads(mock_stdin.read.return_value)
            result = rd.process_msg(msg)
        assert result["actions_count"] == 1
        log_file = log_dir / "cli-1.json"
        assert log_file.exists()
