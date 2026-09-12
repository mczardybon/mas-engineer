"""R110-452 — coverage-push r8: tools/dev_phoenix_log_persister.py 0% → 100%.

R110-168 phase 3 processor for phoenix.recovery.completed.
Writes per-request audit log to .mase/phoenix_logs/<request_id>.json.
On degraded runs, auto-escalates by enqueuing
monitor.health.degraded.

Targets:
- _log_dir(): MAS_PHOENIX_LOG_DIR env → that path; else
  REPO_ROOT/.mase/phoenix_logs. mkdir(parents=True, exist_ok=True).
- _classify(final_status, levels_passed, levels_total): returns
  {final_status, levels_passed, levels_failed=max(0,t-p),
  attention_required=final_status != "ok"}.
- _digest_levels(levels): iterates items; non-dict → {level,
  ok:False, error:"non-dict result"}; dict → {level, ok=bool(
  level.get("ok", False))}.
- process_msg(msg): gets payload/request_id/final_status/levels;
  builds log_entry {schema_version:1, request_id, source_msg_id,
  source_topic, from, to, timestamp, levels_passed, levels_total,
  final_status, duration_ms, level_digest, classification,
  escalation_msg_id:None}; writes JSON (ensure_ascii=False); if
  attention_required → import dev_message_queue → enqueue
  monitor.health.degraded → update log; on MQ error → return
  with escalation_error (and rel path); else return {log_written,
  final_status, levels_passed, attention_required,
  escalation_msg_id}.
- __main__: stdin → JSON msg → process_msg → print JSON.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools.dev_phoenix_log_persister as plp  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# _log_dir
# ─────────────────────────────────────────────────────────────────────
class TestLogDir:
    def test_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        d = plp._log_dir()
        assert d == tmp_path
        assert d.exists()

    def test_default_creates_dir(self, monkeypatch):
        monkeypatch.delenv("MAS_PHOENIX_LOG_DIR", raising=False)
        d = plp._log_dir()
        assert d == plp.DEFAULT_LOG_DIR
        assert d.exists()

    def test_existing_dir_ok(self, tmp_path, monkeypatch):
        # mkdir(exist_ok=True) on existing dir → no error
        tmp_path.mkdir(exist_ok=True)
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        d = plp._log_dir()
        assert d.exists()


# ─────────────────────────────────────────────────────────────────────
# _classify
# ─────────────────────────────────────────────────────────────────────
class TestClassify:
    def test_ok_run(self):
        c = plp._classify("ok", 5, 5)
        assert c["final_status"] == "ok"
        assert c["levels_passed"] == 5
        assert c["levels_failed"] == 0
        assert c["attention_required"] is False

    def test_degraded_run(self):
        c = plp._classify("degraded", 3, 5)
        assert c["levels_failed"] == 2
        assert c["attention_required"] is True

    def test_levels_passed_exceeds_total(self):
        # Should not produce negative levels_failed
        c = plp._classify("degraded", 7, 5)
        assert c["levels_failed"] == 0  # max(0, 5-7)=0
        assert c["attention_required"] is True

    def test_unknown_status(self):
        c = plp._classify("unknown", 0, 5)
        assert c["attention_required"] is True


# ─────────────────────────────────────────────────────────────────────
# _digest_levels
# ─────────────────────────────────────────────────────────────────────
class TestDigestLevels:
    def test_empty(self):
        assert plp._digest_levels({}) == []

    def test_all_ok(self):
        levels = {
            "immune": {"ok": True, "exit": 0, "log": "x", "cmd": "y"},
            "checkpoint": {"ok": True, "exit": 0, "log": "x", "cmd": "y"},
        }
        d = plp._digest_levels(levels)
        assert len(d) == 2
        assert all(x["ok"] is True for x in d)

    def test_some_failed(self):
        levels = {
            "immune": {"ok": True},
            "checkpoint": {"ok": False},
        }
        d = plp._digest_levels(levels)
        assert d[0]["ok"] is True
        assert d[1]["ok"] is False

    def test_non_dict_level(self):
        levels = {"weird": "string not dict"}
        d = plp._digest_levels(levels)
        assert d[0]["level"] == "weird"
        assert d[0]["ok"] is False
        assert "non-dict result" in d[0]["error"]

    def test_missing_ok_defaults_false(self):
        levels = {"immune": {"exit": 1}}
        d = plp._digest_levels(levels)
        assert d[0]["ok"] is False

    def test_level_name_coerced_to_str(self):
        d = plp._digest_levels({"1": {"ok": True}})
        assert d[0]["level"] == "1"


# ─────────────────────────────────────────────────────────────────────
# process_msg — basic (no MQ needed)
# ─────────────────────────────────────────────────────────────────────
class TestProcessMsgBasic:
    def _ok_payload(self, **overrides):
        p = {
            "request_id": "req-1",
            "from": "monitor.health",
            "to": "phoenix.recovery.completed",
            "timestamp": "2026-01-01T00:00:00Z",
            "levels": {
                "immune": {"ok": True, "exit": 0},
                "checkpoint": {"ok": True, "exit": 0},
            },
            "levels_passed": 2,
            "levels_total": 2,
            "final_status": "ok",
            "duration_ms": 1234,
        }
        p.update(overrides)
        return p

    def _msg(self, **payload_overrides):
        return {
            "msg_id": "msg-1",
            "status": "received",
            "topic": "phoenix.recovery.completed",
            "payload": self._ok_payload(**payload_overrides),
        }

    def test_ok_run_no_escalation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        result = plp.process_msg(self._msg())
        assert "log_written" in result
        assert result["final_status"] == "ok"
        assert result["levels_passed"] == 2
        assert result["attention_required"] is False
        assert result["escalation_msg_id"] is None
        # Log file was written
        log_path = tmp_path / "req-1.json"
        assert log_path.exists()
        entry = json.loads(log_path.read_text())
        assert entry["request_id"] == "req-1"
        assert entry["schema_version"] == 1
        assert entry["source_msg_id"] == "msg-1"
        assert entry["source_topic"] == "phoenix.recovery.completed"
        assert entry["from"] == "monitor.health"
        assert entry["to"] == "phoenix.recovery.completed"
        assert entry["duration_ms"] == 1234
        assert entry["levels_passed"] == 2
        assert entry["levels_total"] == 2
        assert entry["final_status"] == "ok"
        assert len(entry["level_digest"]) == 2
        assert entry["classification"]["attention_required"] is False
        assert entry["escalation_msg_id"] is None

    def test_payload_fallback_request_id(self, tmp_path, monkeypatch):
        # No request_id in payload → fallback to msg_id
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        msg = {
            "msg_id": "msg-x",
            "topic": "phoenix.recovery.completed",
            "payload": self._ok_payload(request_id=None),
        }
        result = plp.process_msg(msg)
        assert "msg-x.json" in result["log_written"]
        entry = json.loads((tmp_path / "msg-x.json").read_text())
        assert entry["request_id"] == "msg-x"

    def test_unknown_request_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        msg = {
            # No msg_id at all → triggers "unknown" default
            "topic": "phoenix.recovery.completed",
            "payload": self._ok_payload(request_id=None),
        }
        result = plp.process_msg(msg)
        assert "unknown.json" in result["log_written"]

    def test_idempotent_overwrite(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        plp.process_msg(self._msg())
        # Second call overwrites
        plp.process_msg(self._msg())
        log_path = tmp_path / "req-1.json"
        assert log_path.exists()


# ─────────────────────────────────────────────────────────────────────
# process_msg — degraded (escalation path)
# ─────────────────────────────────────────────────────────────────────
class TestProcessMsgDegraded:
    def _degraded_msg(self):
        return {
            "msg_id": "msg-2",
            "topic": "phoenix.recovery.completed",
            "payload": {
                "request_id": "req-2",
                "from": "x", "to": "y",
                "timestamp": "t",
                "levels": {
                    "immune": {"ok": True},
                    "checkpoint": {"ok": False},
                },
                "levels_passed": 1,
                "levels_total": 2,
                "final_status": "degraded",
                "duration_ms": 500,
            },
        }

    def test_escalation_enqueues(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        mock_mq = MagicMock()
        mock_mq.enqueue.return_value = "esc-msg-1"
        with patch.dict("sys.modules", {"dev_message_queue": mock_mq}):
            result = plp.process_msg(self._degraded_msg())
        assert result["attention_required"] is True
        assert result["escalation_msg_id"] == "esc-msg-1"
        # enqueue called with monitor.health.degraded
        mock_mq.enqueue.assert_called_once()
        args = mock_mq.enqueue.call_args[0]
        assert args[0] == "monitor.health.degraded"
        payload = args[1]
        assert payload["request_id"] == "req-2"
        assert payload["source"] == "dev_phoenix_log_persister"
        assert payload["command"] == "PHOENIX_DEGRADED"
        assert payload["has_problem"] is True
        assert payload["issues_found"] == 1  # 2 total - 1 passed
        assert "checkpoint" in payload["summary"]["degraded_levels"]
        # Log entry was updated with escalation msg id
        entry = json.loads((tmp_path / "req-2.json").read_text())
        assert entry["escalation_msg_id"] == "esc-msg-1"

    def test_escalation_failure_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        mock_mq = MagicMock()
        mock_mq.enqueue.side_effect = RuntimeError("mq down")
        with patch.dict("sys.modules", {"dev_message_queue": mock_mq}):
            result = plp.process_msg(self._degraded_msg())
        assert result["attention_required"] is True
        assert "escalation_error" in result
        assert "RuntimeError" in result["escalation_error"]
        # Original log was still written (first write, before MQ)
        log_path = tmp_path / "req-2.json"
        assert log_path.exists()

    def test_escalation_missing_module(self, tmp_path, monkeypatch):
        # dev_message_queue import fails → ImportError caught
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        # Simulate ImportError by removing the module from sys.modules
        with patch.dict("sys.modules", {"dev_message_queue": None}):
            result = plp.process_msg(self._degraded_msg())
        assert "escalation_error" in result


# ─────────────────────────────────────────────────────────────────────
# process_msg — relative path resolution
# ─────────────────────────────────────────────────────────────────────
class TestProcessMsgRelPath:
    def test_relpath_inside_repo(self, tmp_path, monkeypatch):
        # Default log dir is REPO_ROOT/.mase/phoenix_logs.
        # Monkeypatch env to point at a subdir of repo → relpath
        # resolves; outside → absolute path.
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR",
                           str(plp.REPO_ROOT / "subdir"))
        msg = {
            "msg_id": "x",
            "topic": "t",
            "payload": {"request_id": "y", "final_status": "ok",
                        "levels_passed": 1, "levels_total": 1,
                        "levels": {}},
        }
        result = plp.process_msg(msg)
        # The log_written path is relative to REPO_ROOT
        assert result["log_written"].endswith("y.json")

    def test_relpath_outside_repo(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        msg = {
            "msg_id": "x",
            "topic": "t",
            "payload": {"request_id": "y", "final_status": "ok",
                        "levels_passed": 1, "levels_total": 1,
                        "levels": {}},
        }
        result = plp.process_msg(msg)
        # Outside repo → ValueError caught → str(log_path)
        assert "y.json" in result["log_written"]


# ─────────────────────────────────────────────────────────────────────
# __main__  (subprocess)
# ─────────────────────────────────────────────────────────────────────
class TestMain:
    def test_stdin_empty(self):
        # Empty stdin → payload={} → unknown status
        r = subprocess.run(
            ['python3', 'tools/dev_phoenix_log_persister.py'],
            input="", capture_output=True, text=True,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "log_written" in data

    def test_stdin_ok_payload(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MAS_PHOENIX_LOG_DIR", str(tmp_path))
        payload = {
            "request_id": "req-stdin",
            "from": "x", "to": "y",
            "timestamp": "t",
            "levels": {"immune": {"ok": True}},
            "levels_passed": 1, "levels_total": 1,
            "final_status": "ok", "duration_ms": 100,
        }
        msg = {"msg_id": "m", "topic": "t", "payload": payload}
        r = subprocess.run(
            ['python3', 'tools/dev_phoenix_log_persister.py'],
            input=json.dumps(msg),
            capture_output=True, text=True,
            cwd='/workspace/dev-branch/mas-engineer-cleanup/mas-engineer')
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["final_status"] == "ok"
        # Log file written
        assert (tmp_path / "req-stdin.json").exists()
