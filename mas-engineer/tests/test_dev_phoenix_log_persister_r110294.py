"""
test_dev_phoenix_log_persister_r110294.py — R110-294

Coverage test for mas-engineer/tools/dev_phoenix_log_persister.py
(216 lines, R110-168+R110-169+R110-270 phase 3 processor:
phoenix.recovery.completed → .mase/phoenix_logs/<request_id>.json).

Was R110-293 nicht abdeckt:
  • _log_dir() with MAS_PHOENIX_LOG_DIR override + default
    + mkdir-parents + idempotency
  • _classify() with ok + degraded + unknown status +
    levels_total<levels_passed edge case
  • _digest_levels() with valid dict + non-dict result + ok=True/
    False paths
  • process_msg() happy path (ok status, no escalation) +
    degraded status (auto-escalation) + escalation success +
    escalation failure (Exception in _mq.enqueue) + missing
    payload + missing request_id (falls back to msg_id) +
    None levels + re-write of log with escalation_msg_id +
    non-REPO_ROOT log dir (relative_to ValueError fallback)
  • if __name__ == "__main__": guard (read from stdin + dump
    result to stdout)

A regression in process_msg() would silently lose phase-3 audit
logs (the dashboard reads .mase/phoenix_logs/<request_id>.json
for the phoenix-block badge) or break phase-4 auto-escalation
(when degraded, enqueue monitor.health.degraded so defib can
pick up the run).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Repo root is mas-engineer/, parent of tests/
MAS_ROOT = Path(__file__).resolve().parent.parent
TOOLS = MAS_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import dev_phoenix_log_persister as plp  # noqa: E402


# ---------------------------------------------------------------------------
# _log_dir
# ---------------------------------------------------------------------------

class TestLogDir:
    def test_default_creates_repo_phoenix_logs(self, monkeypatch, tmp_path):
        # The module evaluates REPO_ROOT/DEFAULT_LOG_DIR at import time.
        # Monkeypatch both module attributes to redirect the default.
        fake_repo = tmp_path / "fake-repo"
        fake_repo.mkdir()
        monkeypatch.setattr(plp, "REPO_ROOT", fake_repo)
        monkeypatch.setattr(plp, "DEFAULT_LOG_DIR",
                             fake_repo / ".mase" / "phoenix_logs")
        # Also unset the env override
        monkeypatch.delenv("MAS_PHOENIX_LOG_DIR", raising=False)
        result = plp._log_dir()
        assert result == fake_repo / ".mase" / "phoenix_logs"
        # mkdir-parents was called
        assert result.exists()
        assert result.is_dir()

    def test_env_override_wins(self, monkeypatch, tmp_path):
        custom = tmp_path / "custom-logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(custom))
        result = plp._log_dir()
        assert result == custom
        # The custom dir was created
        assert result.exists()

    def test_idempotent_mkdir(self, monkeypatch, tmp_path):
        # Calling twice doesn't raise
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path / "x"))
        a = plp._log_dir()
        b = plp._log_dir()
        assert a == b
        assert a.exists()


# ---------------------------------------------------------------------------
# _classify
# ---------------------------------------------------------------------------

class TestClassify:
    def test_ok_status_zero_failed(self):
        c = plp._classify("ok", levels_passed=5, levels_total=5)
        assert c["final_status"] == "ok"
        assert c["levels_passed"] == 5
        assert c["levels_failed"] == 0
        assert c["attention_required"] is False

    def test_degraded_status(self):
        c = plp._classify("degraded", levels_passed=3, levels_total=5)
        assert c["final_status"] == "degraded"
        assert c["levels_failed"] == 2
        assert c["attention_required"] is True

    def test_unknown_status_attention_required(self):
        # Anything other than "ok" is attention_required
        c = plp._classify("unknown", levels_passed=0, levels_total=0)
        assert c["attention_required"] is True

    def test_levels_passed_exceeds_total_clamped_to_zero(self):
        # Edge case: levels_passed > levels_total → max(0, negative) = 0
        c = plp._classify("ok", levels_passed=10, levels_total=5)
        # But the final_status is "ok" so attention_required is False
        assert c["levels_failed"] == 0
        assert c["attention_required"] is False


# ---------------------------------------------------------------------------
# _digest_levels
# ---------------------------------------------------------------------------

class TestDigestLevels:
    def test_empty_dict(self):
        assert plp._digest_levels({}) == []

    def test_valid_dict_with_ok_true(self):
        levels = {"immune": {"ok": True, "exit": 0, "log": "...",
                             "cmd": "echo immune"}}
        out = plp._digest_levels(levels)
        assert out == [{"level": "immune", "ok": True}]

    def test_valid_dict_with_ok_false(self):
        levels = {"checkpoint": {"ok": False, "exit": 1}}
        out = plp._digest_levels(levels)
        assert out == [{"level": "checkpoint", "ok": False}]

    def test_valid_dict_with_missing_ok_defaults_to_false(self):
        levels = {"hemisphere": {"exit": 0}}  # no "ok" key
        out = plp._digest_levels(levels)
        assert out == [{"level": "hemisphere", "ok": False}]

    def test_non_dict_result_marked_as_error(self):
        # A level result that's not a dict (e.g. None, str)
        levels = {"immune": None, "checkpoint": "broken"}
        out = plp._digest_levels(levels)
        assert out == [
            {"level": "immune", "ok": False, "error": "non-dict result"},
            {"level": "checkpoint", "ok": False, "error": "non-dict result"},
        ]

    def test_multiple_levels_preserves_input_order(self):
        levels = {
            "immune":     {"ok": True},
            "checkpoint": {"ok": False},
            "hemisphere": {"ok": True},
        }
        out = plp._digest_levels(levels)
        assert [d["level"] for d in out] == ["immune", "checkpoint", "hemisphere"]


# ---------------------------------------------------------------------------
# process_msg (the main entry point)
# ---------------------------------------------------------------------------

def _ok_msg(request_id: str = "req-001") -> dict:
    return {
        "msg_id": "msg-001",
        "topic": "phoenix.recovery.completed",
        "payload": {
            "request_id": request_id,
            "from": "alice",
            "to": "bob",
            "timestamp": "2026-08-15T12:00:00+00:00",
            "levels": {
                "immune":     {"ok": True, "exit": 0, "log": "i.log", "cmd": "x"},
                "checkpoint": {"ok": True, "exit": 0, "log": "c.log", "cmd": "y"},
            },
            "levels_passed": 2,
            "levels_total": 2,
            "final_status": "ok",
            "duration_ms": 1234,
        },
    }


class TestProcessMsg:
    def test_ok_status_writes_log(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        result = plp.process_msg(_ok_msg())
        assert result["final_status"] == "ok"
        assert result["levels_passed"] == 2
        assert result["attention_required"] is False
        assert result["escalation_msg_id"] is None
        # log_written is a string path
        assert "req-001.json" in result["log_written"]
        # File was created
        log_file = log_dir / "req-001.json"
        assert log_file.exists()
        # Content sanity
        data = json.loads(log_file.read_text())
        assert data["schema_version"] == 1
        assert data["request_id"] == "req-001"
        assert data["final_status"] == "ok"
        assert data["source_msg_id"] == "msg-001"
        assert data["source_topic"] == "phoenix.recovery.completed"
        assert data["from"] == "alice"
        assert data["to"] == "bob"
        assert data["timestamp"] == "2026-08-15T12:00:00+00:00"
        assert data["levels_passed"] == 2
        assert data["levels_total"] == 2
        assert data["duration_ms"] == 1234
        assert data["classification"]["levels_failed"] == 0
        assert data["classification"]["attention_required"] is False
        assert data["escalation_msg_id"] is None
        # level_digest has 2 entries
        assert len(data["level_digest"]) == 2
        assert data["level_digest"][0] == {"level": "immune", "ok": True}

    def test_degraded_status_no_escalation_when_mq_unavailable(
        self, tmp_path, monkeypatch
    ):
        # If escalation fails (ImportError because MQ module not
        # importable in test env, or _mq.enqueue raises), the
        # log is still written AND result.escalation_error is set.
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        msg = _ok_msg()
        msg["payload"]["final_status"] = "degraded"
        msg["payload"]["levels_passed"] = 1
        msg["payload"]["levels_total"] = 2
        msg["payload"]["levels"] = {
            "immune":     {"ok": True, "exit": 0},
            "checkpoint": {"ok": False, "exit": 1},
        }
        result = plp.process_msg(msg)
        # The MQ import will fail in the test env (no MAS_MQ_ROOT)
        # → escalation_error is in the result, log was still written
        assert result["attention_required"] is True
        log_file = log_dir / "req-001.json"
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert data["classification"]["attention_required"] is True
        # Either escalation_error is set OR (if MQ happens to be
        # importable) escalation_msg_id is set
        if "escalation_error" in result:
            assert "escalation_msg_id" not in result
            # Original log was written before escalation failed
            assert data["escalation_msg_id"] is None
        else:
            assert result["escalation_msg_id"] is not None
            # Re-wrote log with escalation_msg_id
            assert data["escalation_msg_id"] == result["escalation_msg_id"]

    def test_missing_request_id_falls_back_to_msg_id(
        self, tmp_path, monkeypatch
    ):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        msg = _ok_msg()
        msg["payload"].pop("request_id")
        result = plp.process_msg(msg)
        # File name uses msg_id
        assert "msg-001.json" in result["log_written"]
        data = json.loads((log_dir / "msg-001.json").read_text())
        assert data["request_id"] == "msg-001"

    def test_missing_payload_uses_defaults(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        msg = {"msg_id": "msg-002", "topic": "phoenix.recovery.completed"}
        result = plp.process_msg(msg)
        data = json.loads((log_dir / "msg-002.json").read_text())
        # All payload fields defaulted
        assert data["request_id"] == "msg-002"
        assert data["final_status"] == "unknown"
        assert data["levels_passed"] == 0
        assert data["levels_total"] == 0
        assert data["duration_ms"] == 0
        assert data["from"] is None
        assert data["to"] is None
        assert data["timestamp"] is None
        # level_digest is empty
        assert data["level_digest"] == []

    def test_none_levels_treated_as_empty(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        msg = _ok_msg()
        msg["payload"]["levels"] = None
        result = plp.process_msg(msg)
        # final_status is "ok" so no escalation
        assert result["final_status"] == "ok"
        data = json.loads((log_dir / "req-001.json").read_text())
        assert data["level_digest"] == []

    def test_log_dir_outside_repo_root_uses_absolute_path(
        self, tmp_path, monkeypatch
    ):
        # log_dir is in /tmp → relative_to(REPO_ROOT) raises ValueError
        # → fall back to absolute path
        log_dir = tmp_path / "external-logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        result = plp.process_msg(_ok_msg())
        # log_written is the absolute path (no ".." or relative)
        assert result["log_written"].startswith("/")
        assert "req-001.json" in result["log_written"]

    def test_idempotent_overwrite_same_request_id(
        self, tmp_path, monkeypatch
    ):
        # R110-168 design principle: idempotent
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        plp.process_msg(_ok_msg())
        # 2nd call with same request_id overwrites
        result = plp.process_msg(_ok_msg())
        log_file = log_dir / "req-001.json"
        assert log_file.exists()
        # Only one file
        assert len(list(log_dir.glob("*.json"))) == 1

    def test_unicode_in_classification_preserved(
        self, tmp_path, monkeypatch
    ):
        # R110-270: ensure_ascii=False
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        msg = _ok_msg()
        msg["payload"]["from"] = "α-User-α"
        result = plp.process_msg(msg)
        log_file = log_dir / "req-001.json"
        raw = log_file.read_text()
        # Unicode preserved (not escaped as \u03b1)
        assert "α-User-α" in raw

    def test_escalation_with_mq_mocked(
        self, tmp_path, monkeypatch
    ):
        # Mock dev_message_queue.enqueue to verify escalation payload
        # shape and that log is re-written with escalation_msg_id
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))

        import importlib
        fake_mq = importlib.import_module("dev_message_queue")
        captured = {}

        def fake_enqueue(topic, payload):
            captured["topic"] = topic
            captured["payload"] = payload
            return "esc-msg-42"

        monkeypatch.setattr(fake_mq, "enqueue", fake_enqueue)
        msg = _ok_msg()
        msg["payload"]["final_status"] = "degraded"
        msg["payload"]["levels_passed"] = 1
        msg["payload"]["levels_total"] = 2
        msg["payload"]["levels"] = {
            "immune":     {"ok": True,  "exit": 0},
            "checkpoint": {"ok": False, "exit": 1},
        }
        result = plp.process_msg(msg)
        # Escalation was called
        assert captured.get("topic") == "monitor.health.degraded"
        assert result["escalation_msg_id"] == "esc-msg-42"
        # Payload shape (R110-169 contract)
        p = captured["payload"]
        assert p["request_id"] == "req-001"
        assert p["source"] == "dev_phoenix_log_persister"
        assert p["command"] == "PHOENIX_DEGRADED"
        assert p["has_problem"] is True
        assert p["issues_found"] == 1
        assert p["summary"]["phoenix_request_id"] == "req-001"
        assert p["summary"]["levels_passed"] == 1
        assert p["summary"]["levels_total"] == 2
        assert p["summary"]["final_status"] == "degraded"
        assert p["summary"]["degraded_levels"] == ["checkpoint"]
        # Log was re-written with escalation_msg_id
        data = json.loads((log_dir / "req-001.json").read_text())
        assert data["escalation_msg_id"] == "esc-msg-42"

    def test_escalation_failure_keeps_original_log(
        self, tmp_path, monkeypatch
    ):
        # When _mq.enqueue raises, the original log is still on disk
        # and result.escalation_error is set
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))

        import importlib
        fake_mq = importlib.import_module("dev_message_queue")

        def fake_enqueue(topic, payload):
            raise RuntimeError("MQ down")

        monkeypatch.setattr(fake_mq, "enqueue", fake_enqueue)
        msg = _ok_msg()
        msg["payload"]["final_status"] = "degraded"
        msg["payload"]["levels_passed"] = 1
        msg["payload"]["levels_total"] = 2
        result = plp.process_msg(msg)
        # Original log still on disk
        log_file = log_dir / "req-001.json"
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        # escalation_msg_id is None (re-write never happened)
        assert data["escalation_msg_id"] is None
        # Result carries the error
        assert "escalation_error" in result
        assert "RuntimeError" in result["escalation_error"]
        assert "MQ down" in result["escalation_error"]


# ---------------------------------------------------------------------------
# if __name__ == "__main__": guard
# ---------------------------------------------------------------------------

class TestMainGuard:
    def test_stdin_to_stdout(self, tmp_path, monkeypatch, capsys):
        # Replace the module's REPO_ROOT-derived default with tmp_path
        # by setting MAS_PHOENIX_LOG_DIR, then exec the module
        # body with runpy + run_name="__main__".
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        import runpy
        msg = _ok_msg()
        # We feed the msg via stdin by replacing sys.stdin
        import io
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(msg)))
        # The if-main block does NOT call sys.exit (just print)
        # so we wrap runpy in a try/except for SystemExit
        # (in case some inner code raises) and then check stdout.
        runpy.run_module("dev_phoenix_log_persister", run_name="__main__")
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["final_status"] == "ok"
        assert "log_written" in result
        # And the log file was created
        assert (log_dir / "req-001.json").exists()

    def test_stdin_empty_uses_default_msg(self, tmp_path, monkeypatch, capsys):
        # When stdin is empty, msg becomes {} (from `or "{}"`)
        # → all payload fields defaulted to "unknown" / 0
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(log_dir))
        import runpy
        import io
        # Empty stdin
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        runpy.run_module("dev_phoenix_log_persister", run_name="__main__")
        out = capsys.readouterr().out
        result = json.loads(out)
        # request_id fell back to msg_id (also "unknown")
        # final_status is "unknown" → attention_required True
        assert result["final_status"] == "unknown"
        assert result["attention_required"] is True
        # And a log file was created
        assert (log_dir / "unknown.json").exists()
