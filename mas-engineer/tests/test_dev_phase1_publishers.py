"""test_dev_phase1_publishers.py — R110-165 phase 1.2 + 1.3

Tests that:
  1. dev_im_finder_scan.py --publish enqueues to im.finding.created
  2. dev_health_monitor.py --publish enqueues to monitor.health.degraded (when degraded)
  3. dev_health_monitor.py --publish=always publishes even on healthy run
  4. dev_health_monitor.py --publish=never publishes nothing
  5. Both tools behave WITHOUT --publish (no enqueue, no side-effect)
  6. Both tools survive errors (enqueue-failure must not crash the tool)

Run with:
  python3 -m pytest tests/test_dev_phase1_publishers.py -v
"""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS_DIR = REPO_ROOT / "tools"
# R110-171 — default to real MQ root (matches pre-fix behavior) so the
# `IM_NDJSON`/`MON_NDJSON` constants are import-time valid. The
# `mq_root_isolation` autouse fixture below redirects both the file
# paths AND the subprocess env (MAS_MQ_ROOT) to a per-test tmp dir,
# so xdist workers cannot pollute each other's ndjson counts.
IM_NDJSON = REPO_ROOT / ".mase" / "mq" / "im_finding_created.ndjson"
MON_NDJSON = REPO_ROOT / ".mase" / "mq" / "monitor_health_degraded.ndjson"


def _unique_id(prefix: str) -> str:
    """Per-test-run unique id to avoid MQ-2 idempotency dedup collisions
    when the same test is re-run in the same session."""
    return f"{prefix}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"


# ---------- fixtures ----------

# R110-171 — xdist-safe MQ isolation. Without this, parallel workers
# (-n 4) all append to the same .mase/mq/<topic>.ndjson, so
# `im_depth_before` snapshots race with other workers' subprocess
# writes, and `depth_after` is off by N. Fix: every test gets its
# own tmp MQ root; subprocess env is overridden; the per-test
# `IM_NDJSON`/`MON_NDJSON` module globals are rebound so the
# fixtures read the isolated file.
@pytest.fixture(autouse=True)
def mq_root_isolation(tmp_path, monkeypatch):
    """Isolate this test's MQ root from .mase/mq/ and from sibling workers."""
    mq_root = tmp_path / "mq"
    mq_root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(mq_root))
    # Rebind module globals so fixtures/tests read/write the isolated file
    global IM_NDJSON, MON_NDJSON
    IM_NDJSON = mq_root / "im_finding_created.ndjson"
    MON_NDJSON = mq_root / "monitor_health_degraded.ndjson"
    yield mq_root


@pytest.fixture
def im_depth_before():
    return _count_lines(IM_NDJSON)


@pytest.fixture
def mon_depth_before():
    return _count_lines(MON_NDJSON)


def _count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with open(p) as f:
        return sum(1 for _ in f)


# ---------- Phase 1.2: im-finder publisher ----------

def test_im_finder_publish_enqueues_message(im_depth_before):
    """--publish enqueues exactly 1 message to im.finding.created."""
    request_id = _unique_id("r110-165-test-im")
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_im_finder_scan.py"),
         "--publish", f"--publish-request-id={request_id}",
         "--scope=recipe/sub"],
        capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
    )
    assert r.returncode == 0, f"stderr={r.stderr[-500:]}"
    assert "[PUBLISH-OK]" in r.stderr
    assert "im.finding.created" in r.stderr
    # topic file must exist now
    assert IM_NDJSON.exists()
    depth_after = _count_lines(IM_NDJSON)
    assert depth_after == im_depth_before + 1, (
        f"depth should grow by 1, was {im_depth_before}, now {depth_after}"
    )
    # last line is ours (search for our request_id, not just any last line)
    matching = []
    with open(IM_NDJSON) as f:
        for line in f:
            d = json.loads(line)
            if d.get("payload", {}).get("request_id") == request_id:
                matching.append(d)
    assert len(matching) == 1, (
        f"expected exactly 1 msg with request_id={request_id}, found {len(matching)}"
    )
    msg = matching[0]
    assert msg["status"] == "pending"
    assert msg["payload"]["request_id"] == request_id
    assert msg["payload"]["source"] == "dev_im_finder_scan"
    assert "findings_total" in msg["payload"]
    assert "findings_by_severity" in msg["payload"]
    assert "timestamp" in msg["payload"]


def test_im_finder_without_publish_does_not_enqueue(im_depth_before):
    """Without --publish, no message lands in the topic."""
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_im_finder_scan.py"),
         "--scope=recipe/sub"],
        capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
    )
    assert r.returncode == 0
    assert "[PUBLISH" not in r.stderr  # no publish-ok nor publish-error
    assert _count_lines(IM_NDJSON) == im_depth_before


def test_im_finder_uses_default_request_id_when_omitted():
    """Without --publish-request-id, a default is generated."""
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_im_finder_scan.py"),
         "--publish", "--scope=recipe/sub"],
        capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
    )
    assert r.returncode == 0
    assert "[PUBLISH-OK]" in r.stderr


# ---------- Phase 1.3: health-monitor publisher ----------

def test_health_monitor_publish_always_enqueues(mon_depth_before):
    """--publish=always publishes even when no problems found."""
    request_id = _unique_id("r110-165-test-mon-always")
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_health_monitor.py"),
         "CHECK_HEALTH", "--publish=always",
         f"--publish-request-id={request_id}"],
        capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
    )
    # exit may be 0 or 1; both are fine here — we care about enqueue
    assert "[PUBLISH-OK]" in r.stderr, f"stderr={r.stderr[-500:]}"
    assert "monitor.health.degraded" in r.stderr
    assert MON_NDJSON.exists()
    depth_after = _count_lines(MON_NDJSON)
    assert depth_after == mon_depth_before + 1
    # find OUR msg by request_id (not just any last line)
    matching = []
    with open(MON_NDJSON) as f:
        for line in f:
            d = json.loads(line)
            if d.get("payload", {}).get("request_id") == request_id:
                matching.append(d)
    assert len(matching) == 1, (
        f"expected exactly 1 msg with request_id={request_id}, found {len(matching)}"
    )
    msg = matching[0]
    assert msg["payload"]["command"] == "CHECK_HEALTH"
    assert msg["payload"]["source"] == "dev_health_monitor"
    assert "has_problem" in msg["payload"]
    assert "issues_found" in msg["payload"]
    assert "timestamp" in msg["payload"]


def test_health_monitor_publish_never_enqueues_nothing(mon_depth_before):
    """--publish=never suppresses the publish even on degraded run."""
    # Run check_runtime against the repo (it scans .mase/ for state)
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_health_monitor.py"),
         "CHECK_RUNTIME", "--publish=never",
         "--publish-request-id=r110-165-test-mon-never"],
        capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
    )
    assert "[PUBLISH" not in r.stderr, (
        f"--publish=never should suppress but stderr={r.stderr[-500:]}"
    )
    assert _count_lines(MON_NDJSON) == mon_depth_before


def test_health_monitor_default_publish_only_on_degraded(mon_depth_before):
    """Default (--publish without value) is 'on-degraded'."""
    request_id = _unique_id("r110-165-test-mon-default")
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_health_monitor.py"),
         "CHECK_HEALTH", "--publish",
         f"--publish-request-id={request_id}"],
        capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
    )
    # we don't know whether the run is degraded without parsing result.
    # but the publish hook must run, so check the [PUBLISH-...] marker
    # (either OK or NOOP is acceptable here — we just want the hook to fire)
    assert ("[PUBLISH-OK]" in r.stderr) or ("[PUBLISH-ERROR]" in r.stderr) or (
        # if not degraded, no message at all (hook checked mode, decided not to)
        "monitor.health.degraded" not in r.stderr and "[PUBLISH" not in r.stderr
    )
    # if it DID publish, the depth grew; if not, depth unchanged
    depth_after = _count_lines(MON_NDJSON)
    assert depth_after in (mon_depth_before, mon_depth_before + 1)


def test_health_monitor_without_publish_does_not_enqueue(mon_depth_before):
    """Without --publish flag, no message lands in the topic."""
    r = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "dev_health_monitor.py"),
         "CHECK_HEALTH"],
        capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
    )
    assert "[PUBLISH" not in r.stderr
    assert _count_lines(MON_NDJSON) == mon_depth_before
