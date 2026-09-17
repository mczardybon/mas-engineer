"""Targeted coverage push for tools/dev_mq_consumer.py — R110-507.

Target: dev_mq_consumer.py (299 lines, ~122 stmts, 0% → goal 70%).

Strategy:
- Use MAS_MQ_ROOT env var to redirect mq file storage to tmp_path
- Mock mq.consume/ack/nack/gc_stale_in_flight/_find_msg/_read_topic
  directly so we don't need full file-system dance
- Cover all CLI branches: ack-success, no-message, processor-exception,
  consume-error, ack-error, single-consumer-violation,
  processor-load-failed, max-messages loop, race condition
"""
import importlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"


@pytest.fixture
def lib(tmp_path, monkeypatch):
    """Import dev_mq_consumer inline, with MAS_MQ_ROOT redirected to tmp_path.

    Note: dev_mq_consumer.py at module-level imports `dev_message_queue as mq`
    and calls `mq._mq_root()` indirectly (via consume/ack/nack/etc.).
    Setting MAS_MQ_ROOT env var redirects that to tmp_path so any
    real file-system ops stay sandboxed.
    """
    # MAS_MQ_ROOT must be set BEFORE importing mq
    monkeypatch.setenv("MAS_MQ_ROOT", str(tmp_path / "mq"))
    monkeypatch.setenv("HOME", str(tmp_path))

    saved_dwm = sys.modules.get("dev_mq_consumer")
    saved_mq = sys.modules.get("dev_message_queue")
    for k in ("dev_mq_consumer", "dev_message_queue"):
        if k in sys.modules:
            del sys.modules[k]

    # Use importlib so coverage tracks under tools.dev_mq_consumer
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "tools.dev_mq_consumer", TOOLS_DIR / "dev_mq_consumer.py",
    )
    # mq must be imported FIRST (consumer does `import dev_message_queue as mq`)
    # Easiest: temporarily put tools/ on sys.path and import mq normally
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    # We need mq to be the same module consumer will use. Loading consumer via
    # importlib will trigger its top-level `import dev_message_queue as mq`
    # which uses the cached sys.modules entry (created by us pre-loading).
    import dev_message_queue as mq  # noqa: E402
    sys.modules["tools.dev_message_queue"] = mq

    lib = importlib.util.module_from_spec(spec)
    sys.modules["tools.dev_mq_consumer"] = lib
    sys.modules["dev_mq_consumer"] = lib
    spec.loader.exec_module(lib)
    yield lib

    for k in ("dev_mq_consumer", "tools.dev_mq_consumer", "tools.dev_message_queue"):
        if k in sys.modules:
            del sys.modules[k]
    if saved_dwm is not None:
        sys.modules["dev_mq_consumer"] = saved_dwm
    if saved_mq is not None:
        sys.modules["dev_message_queue"] = saved_mq


@pytest.fixture
def mq():
    """Get the dev_message_queue module."""
    return sys.modules["dev_message_queue"]


def run_main(lib, *args, monkeypatch):
    """Helper: run lib.main() with given CLI args + capture stdout JSON."""
    monkeypatch.setattr(sys, "argv", ["dev_mq_consumer", *args])
    rc = lib.main()
    return rc


# ─────────────────────────────────────────────────────────
# _handle_sigterm
# ─────────────────────────────────────────────────────────

def test_handle_sigterm_releases_lease(lib, monkeypatch, capsys):
    """SIGTERM handler: if lease held → nack + exit 0."""
    # Set the global lease to a fake msg_id
    lib._in_flight_lease["msg_id"] = "test-msg-1"
    with mock.patch.object(lib.mq, "nack") as m_nack:
        with mock.patch.object(sys, "exit") as m_exit:
            lib._handle_sigterm(signal.SIGTERM, None)
    m_nack.assert_called_once()
    args, kwargs = m_nack.call_args
    assert args[0] == "test-msg-1"
    assert "SIGTERM" in kwargs["reason"]
    m_exit.assert_called_once_with(0)


def test_handle_sigterm_no_lease(lib, monkeypatch, capsys):
    """SIGTERM handler: no lease → just exit 0."""
    lib._in_flight_lease["msg_id"] = None
    with mock.patch.object(lib.mq, "nack") as m_nack:
        with mock.patch.object(sys, "exit") as m_exit:
            lib._handle_sigterm(signal.SIGTERM, None)
    m_nack.assert_not_called()
    m_exit.assert_called_once_with(0)


def test_handle_sigterm_nack_exception_silenced(lib):
    """SIGTERM: nack raises → silenced, exit 0 still."""
    lib._in_flight_lease["msg_id"] = "x"
    with mock.patch.object(lib.mq, "nack", side_effect=Exception("boom")):
        with mock.patch.object(sys, "exit") as m_exit:
            lib._handle_sigterm(signal.SIGTERM, None)
    m_exit.assert_called_once_with(0)


# ─────────────────────────────────────────────────────────
# _check_single_consumer
# ─────────────────────────────────────────────────────────

def test_check_single_consumer_no_msgs(lib):
    """Empty topic → return None (no other consumer)."""
    with mock.patch.object(lib.mq, "_read_topic", return_value=[]):
        assert lib._check_single_consumer("t1", "me") is None


def test_check_single_consumer_other_holder(lib):
    """in_flight msg with different consumer_id → return that holder."""
    msgs = [{"status": "in_flight", "consumer_id": "other-consumer"}]
    with mock.patch.object(lib.mq, "_read_topic", return_value=msgs):
        assert lib._check_single_consumer("t1", "me") == "other-consumer"


def test_check_single_consumer_same_holder(lib):
    """in_flight msg with our consumer_id → return None."""
    msgs = [{"status": "in_flight", "consumer_id": "me"}]
    with mock.patch.object(lib.mq, "_read_topic", return_value=msgs):
        assert lib._check_single_consumer("t1", "me") is None


def test_check_single_consumer_no_holder_field(lib):
    """in_flight msg without consumer_id → return None."""
    msgs = [{"status": "in_flight"}]
    with mock.patch.object(lib.mq, "_read_topic", return_value=msgs):
        assert lib._check_single_consumer("t1", "me") is None


def test_check_single_consumer_pending_status(lib):
    """non-in_flight (pending) msg → return None."""
    msgs = [{"status": "pending", "consumer_id": "x"}]
    with mock.patch.object(lib.mq, "_read_topic", return_value=msgs):
        assert lib._check_single_consumer("t1", "me") is None


def test_check_single_consumer_read_exception(lib):
    """_read_topic raises → return None (no crash)."""
    with mock.patch.object(lib.mq, "_read_topic", side_effect=Exception("disk fail")):
        assert lib._check_single_consumer("t1", "me") is None


# ─────────────────────────────────────────────────────────
# _load_processor
# ─────────────────────────────────────────────────────────

def test_load_processor_no_colon(lib):
    """No ':' in spec → ValueError."""
    with pytest.raises(ValueError, match="--processor must be"):
        lib._load_processor("no_colon_here")


def test_load_processor_module_not_found(lib):
    """Module doesn't exist → ImportError."""
    with pytest.raises(ImportError):
        lib._load_processor("nonexistent_module_xyz:foo")


def test_load_processor_function_missing(lib):
    """Module exists but func doesn't → AttributeError."""
    # Use a real module (json is guaranteed), but a non-existent function
    with pytest.raises(AttributeError, match="has no function"):
        lib._load_processor("json:nonexistent_func_xyz")


def test_load_processor_success(lib):
    """Valid 'module:func' → returns the callable."""
    fn = lib._load_processor("json:dumps")
    assert callable(fn)
    assert fn({"a": 1}) == '{"a": 1}'


# ─────────────────────────────────────────────────────────
# _find_msg_full
# ─────────────────────────────────────────────────────────

def test_find_msg_full_not_found(lib):
    """mq._find_msg returns None → return None."""
    with mock.patch.object(lib.mq, "_find_msg", return_value=None):
        assert lib._find_msg_full("m1") is None


def test_find_msg_full_completed_skipped(lib):
    """msg with status='completed' → return None (already archived)."""
    msg = {"status": "completed"}
    with mock.patch.object(lib.mq, "_find_msg", return_value=("topic", (0, msg, [msg]))):
        assert lib._find_msg_full("m1") is None


def test_find_msg_full_in_flight_returns_msg(lib):
    """in_flight msg → return the dict."""
    msg = {"status": "in_flight", "payload": {"x": 1}}
    with mock.patch.object(lib.mq, "_find_msg", return_value=("topic", (0, msg, [msg]))):
        assert lib._find_msg_full("m1") == msg


def test_find_msg_full_pending_returns_msg(lib):
    """pending msg (not completed, not in_flight) → return the dict."""
    msg = {"status": "pending", "payload": {"x": 1}}
    with mock.patch.object(lib.mq, "_find_msg", return_value=("topic", (0, msg, [msg]))):
        assert lib._find_msg_full("m1") == msg


# ─────────────────────────────────────────────────────────
# main() — CLI branches
# ─────────────────────────────────────────────────────────

def test_main_ack_success(lib, monkeypatch, capsys):
    """Happy path: consume → processor → ack → exit 0 with 'acked' result."""
    msg = {"msg_id": "m1", "payload": {"x": 1}}
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", return_value=msg), \
         mock.patch.object(lib.mq, "_find_msg",
                            return_value=("t1", (0, msg, [msg]))), \
         mock.patch.object(lib.mq, "ack", return_value=True):
        rc = lib.main()
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["result"] == "acked"


def test_main_no_message_idle(lib, monkeypatch, capsys):
    """consume returns None → exit 1 with 'no-message' result."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", return_value=None):
        rc = lib.main()
    assert rc == 1
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["result"] == "no-message"


def test_main_processor_exception_nacks(lib, monkeypatch, capsys):
    """Processor raises → nack → exit 2 with 'nacked' result + traceback."""
    msg = {"msg_id": "m1", "payload": {"x": 1}}
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    def bad_proc(m):
        raise ValueError("intentional test failure")
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", return_value=msg), \
         mock.patch.object(lib.mq, "_find_msg",
                            return_value=("t1", (0, msg, [msg]))), \
         mock.patch.object(lib.mq, "nack") as m_nack, \
         mock.patch("dev_mq_consumer.importlib.import_module") as m_imp:
        # Make the loaded processor raise
        fake_mod = mock.Mock()
        fake_mod.dumps = bad_proc
        m_imp.return_value = fake_mod
        rc = lib.main()
    assert rc == 2
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["result"] == "nacked"
    assert "ValueError" in data["reason"]
    assert "traceback" in data
    m_nack.assert_called_once()


def test_main_processor_exception_nack_also_fails(lib, monkeypatch, capsys):
    """Processor raises AND nack raises → reason includes 'nack-failed'."""
    msg = {"msg_id": "m1"}
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    def bad_proc(m):
        raise RuntimeError("proc boom")
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", return_value=msg), \
         mock.patch.object(lib.mq, "_find_msg",
                            return_value=("t1", (0, msg, [msg]))), \
         mock.patch.object(lib.mq, "nack", side_effect=Exception("nack boom")), \
         mock.patch("dev_mq_consumer.importlib.import_module") as m_imp:
        fake_mod = mock.Mock()
        fake_mod.dumps = bad_proc
        m_imp.return_value = fake_mod
        rc = lib.main()
    assert rc == 2
    data = json.loads(capsys.readouterr().out)
    assert "nack-failed" in data["reason"]


def test_main_consume_exception_exits_3(lib, monkeypatch, capsys):
    """consume() raises → exit 3 with 'error' result + reason."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", side_effect=IOError("disk fail")):
        rc = lib.main()
    assert rc == 3
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "error"
    assert "consume-failed" in data["reason"]


def test_main_ack_exception_exits_3(lib, monkeypatch, capsys):
    """ack() raises → exit 3 with 'error' result."""
    msg = {"msg_id": "m1", "payload": {}}
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", return_value=msg), \
         mock.patch.object(lib.mq, "_find_msg",
                            return_value=("t1", (0, msg, [msg]))), \
         mock.patch.object(lib.mq, "ack", side_effect=Exception("ack boom")):
        rc = lib.main()
    assert rc == 3
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "error"
    assert "ack-failed" in data["reason"]
    assert "processor_result" in data


def test_main_ack_returns_false_exits_3(lib, monkeypatch, capsys):
    """ack() returns False → exit 3."""
    msg = {"msg_id": "m1", "payload": {}}
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", return_value=msg), \
         mock.patch.object(lib.mq, "_find_msg",
                            return_value=("t1", (0, msg, [msg]))), \
         mock.patch.object(lib.mq, "ack", return_value=False):
        rc = lib.main()
    assert rc == 3
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "error"
    assert "ack-returned-False" in data["reason"]


def test_main_single_consumer_violation_exits_3(lib, monkeypatch, capsys):
    """Other consumer holds in_flight lease → exit 3 with 'error'."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer",
                            return_value="other-consumer"):
        rc = lib.main()
    assert rc == 3
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "error"
    assert "single-consumer violation" in data["reason"]
    assert "other-consumer" in data["reason"]


def test_main_processor_load_value_error_exits_3(lib, monkeypatch, capsys):
    """Bad --processor spec (no colon) → exit 3 with processor-load-failed."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "no_colon_spec", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None):
        rc = lib.main()
    assert rc == 3
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "error"
    assert "processor-load-failed" in data["reason"]


def test_main_processor_load_import_error_exits_3(lib, monkeypatch, capsys):
    """--processor module doesn't exist → exit 3 with ImportError reason."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "nonexistent_xyz_module:foo", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None):
        rc = lib.main()
    assert rc == 3
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "error"
    assert "processor-load-failed" in data["reason"]


def test_main_processor_load_attribute_error_exits_3(lib, monkeypatch, capsys):
    """--processor func doesn't exist → exit 3 with AttributeError reason."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:nonexistent_xyz_func", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None):
        rc = lib.main()
    assert rc == 3
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "error"
    assert "processor-load-failed" in data["reason"]


def test_main_race_lost_msg_continues(lib, monkeypatch, capsys):
    """consume returns msg but _find_msg_full returns None → skip + next iter.

    Note: with max-messages=2, first iter skips (processed=1, no message processed),
    second iter: consume returns None → processed=1 != 0 so we hit the `else: break`
    branch and fall through to "max-messages reached" with acked-result exit 0.
    """
    msg = {"msg_id": "m1"}
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1", "--max-messages", "2",
    ])
    # First call: consume returns msg, but _find_msg_full returns None → skip
    # Second call: consume returns None → break → exit 0 with "acked" + count=1
    consume_results = [msg, None]
    def consume_side(*args, **kwargs):
        return consume_results.pop(0)
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", side_effect=consume_side), \
         mock.patch.object(lib, "_find_msg_full", return_value=None):
        rc = lib.main()
    assert rc == 0  # exits via "max-messages reached" branch
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "acked"
    assert data["count"] == 1  # only 1 actual skip-counted


def test_main_max_messages_drains_multiple(lib, monkeypatch, capsys):
    """--max-messages 3 → loop until 3 acked, then 'max-messages reached'."""
    msgs = [
        {"msg_id": f"m{i}", "payload": {"i": i}}
        for i in range(3)
    ]
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1", "--max-messages", "3",
    ])
    def find_msg_full(msg_id):
        msg = next(m for m in msgs if m["msg_id"] == msg_id)
        return msg
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", side_effect=msgs + [None]), \
         mock.patch.object(lib, "_find_msg_full", side_effect=find_msg_full), \
         mock.patch.object(lib.mq, "ack", return_value=True) as m_ack:
        rc = lib.main()
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "acked"
    assert data["count"] == 3
    assert m_ack.call_count == 3


def test_main_processor_returns_dict_to_merge(lib, monkeypatch, capsys):
    """Processor returns a dict → included as processor_result on ack."""
    msg = {"msg_id": "m1", "payload": {"x": 1}}
    def proc(m):
        return {"merged": True, "out": m["payload"]["x"] * 2}
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", return_value=msg), \
         mock.patch.object(lib.mq, "_find_msg",
                            return_value=("t1", (0, msg, [msg]))), \
         mock.patch.object(lib.mq, "ack", return_value=True), \
         mock.patch("dev_mq_consumer.importlib.import_module") as m_imp:
        fake_mod = mock.Mock()
        fake_mod.dumps = proc
        m_imp.return_value = fake_mod
        rc = lib.main()
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["result"] == "acked"
    # Note: processor_result is NOT printed on the success branch
    # (it's only printed on ack-error/ack-false branches).


def test_main_sigterm_handler_registered(lib, monkeypatch):
    """main() registers a SIGTERM handler (replacing pytest's default)."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight"), \
         mock.patch.object(lib.mq, "consume", return_value=None), \
         mock.patch.object(signal, "signal") as m_signal:
        lib.main()
    # SIGTERM should have been registered with _handle_sigterm
    sigterm_calls = [c for c in m_signal.call_args_list if c[0][0] == signal.SIGTERM]
    assert len(sigterm_calls) == 1
    assert sigterm_calls[0][0][1] == lib._handle_sigterm


def test_main_gc_stale_called(lib, monkeypatch):
    """mq.gc_stale_in_flight() is called on each iteration."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight") as m_gc, \
         mock.patch.object(lib.mq, "consume", return_value=None):
        lib.main()
    assert m_gc.call_count == 1
    # TTL arg matches IN_FLIGHT_LEASE_TTL_SEC (300)
    assert m_gc.call_args[1]["max_age_sec"] == lib.IN_FLIGHT_LEASE_TTL_SEC


def test_main_gc_stale_exception_silenced(lib, monkeypatch, capsys):
    """gc_stale_in_flight raises → silenced, continue normally."""
    monkeypatch.setattr(sys, "argv", [
        "dev_mq_consumer", "--topic", "t1", "--consumer-id", "c1",
        "--processor", "json:dumps", "--timeout", "0.1",
    ])
    with mock.patch.object(lib, "_check_single_consumer", return_value=None), \
         mock.patch.object(lib.mq, "gc_stale_in_flight", side_effect=Exception), \
         mock.patch.object(lib.mq, "consume", return_value=None):
        rc = lib.main()
    assert rc == 1  # no-message path still works
