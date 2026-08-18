"""
test_dev_im_design_patches.py — R110-195 (R110-194-B, MQ Full Adoption).

3-test pytest suite for the consume-and-design loop (the
DESIGN half). Verifies the end-to-end behavior of the
sub_recipe sub_mas-design-patches (R110-195) by driving it
through the public python kernel dev_im_design_patches.process_msg:

  1. happy path: 1 MQ msg → 1 patch file at
     .mase/im/patches/<request_id>.yaml with patch_type /
     priority / actions_count derived from the payload.
  2. zero-findings: msg with findings_total=0 → patch_type=
     "no_findings", priority="P4", actions=[] (still
     writes a file — design is always produced).
  3. kernel exception: process_msg raises → consumer's
     nack path is the correct response (we simulate this
     by passing a non-dict msg and asserting that the
     consumer-level integration would nack, not ack).

Run with:
    python3 -m pytest tests/test_dev_im_design_patches.py -v
"""
import json
import os
import sys
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"

sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent))

import dev_im_design_patches as design  # noqa: E402
import dev_message_queue as mq           # noqa: E402


# ─── Per-test isolated MAS_PATCHES_DIR + MAS_MQ_ROOT ─────────────

@pytest.fixture
def patches_dir(tmp_path, monkeypatch):
    """Isolated patch output dir (kernel writes here, not the real
    .mase/im/patches/).  The kernel resolves the dir at call-time
    from MAS_PATCHES_DIR, so monkeypatching the env var is enough."""
    d = tmp_path / "patches"
    monkeypatch.setenv("MAS_PATCHES_DIR", str(d))
    return d


@pytest.fixture
def mq_root(tmp_path, monkeypatch):
    """Isolated MQ root so process_msg can be called via the
    consumer's --processor integration (test #3 below) without
    touching the real .mase/mq."""
    root = tmp_path / "mq"
    root.mkdir()
    monkeypatch.setenv("MAS_MQ_ROOT", str(root))
    return root


def _finding_envelope(request_id: str, total: int, by_sev: dict,
                      top: list) -> dict:
    """Build the MQ message envelope the consumer would receive.

    Mirrors the shape produced by dev_im_finder_scan.py --publish
    and wrapped by dev_mq_consumer.consume() (msg_id + payload)."""
    return {
        "msg_id": f"msg-{request_id}",
        "topic": "im.finding.created",
        "status": "in_flight",
        "payload": {
            "request_id": request_id,
            "source": "dev_im_finder_scan",
            "timestamp": "2026-08-18T12:00:00Z",
            "findings_total": total,
            "findings_by_severity": by_sev,
            "findings_by_type": {"yaml_typo": by_sev.get("high", 0)},
            "findings_top": top,
        },
    }


# ─── Tests ───────────────────────────────────────────────────────

def test_happy_path_writes_patch_file(patches_dir, mq_root):
    """(1) Sub_recipe design loop: 1 MQ msg → 1 patch file with
    patch_type / priority / actions_count derived correctly from
    a payload that has 1 blocker + 2 high findings."""
    request_id = "rq-happy-001"
    envelope = _finding_envelope(
        request_id=request_id,
        total=3,
        by_sev={"blocker": 1, "high": 2, "medium": 0, "low": 0},
        top=[
            {"type": "yaml_typo", "severity": "blocker",
             "location": "recipe/dev.yaml:10", "description": "bad indent"},
            {"type": "secret_leak", "severity": "high",
             "location": "tools/dev_x.py:42", "description": "GH_PAT in code"},
            {"type": "test_gap", "severity": "high",
             "location": "tests/test_x.py:1", "description": "no test"},
        ],
    )

    result = design.process_msg(envelope)

    # 1. Returned dict has expected keys
    assert "patch_written" in result
    assert result["patch_type"] == "blocker_remediation", \
        f"expected blocker_remediation, got {result['patch_type']}"
    assert result["priority"] == "P0"
    assert result["actions_count"] == 3

    # 2. The patch file exists at MAS_PATCHES_DIR/<request_id>.yaml
    out = patches_dir / f"{request_id}.yaml"
    assert out.exists(), f"patch file not written: {out}"

    # 3. Patch YAML is well-formed and contains the expected fields
    with open(out) as f:
        body = yaml.safe_load(f)
    assert body["request_id"] == request_id
    assert body["source_msg_id"] == "msg-rq-happy-001"
    assert body["source_topic"] == "im.finding.created"
    assert body["findings_total"] == 3
    assert body["findings_by_severity"] == \
        {"blocker": 1, "high": 2, "medium": 0, "low": 0}
    assert body["apply_status"] == "pending"
    assert len(body["actions"]) == 3
    # Top-3 cap is enforced by the kernel
    assert all(a["action"] for a in body["actions"])


def test_zero_findings_writes_no_op_patch(patches_dir, mq_root):
    """(2) Even an empty-findings msg produces a design patch
    (patch_type='no_findings', priority='P4', actions=[]).
    Rationale: the apply-stage pipeline needs an explicit
    "we ran, there's nothing to do" record per scan, not
    silence.  The MQ-Full-Adoption invariant is: every ack
    has a corresponding .yaml file."""
    request_id = "rq-zero-002"
    envelope = _finding_envelope(
        request_id=request_id,
        total=0,
        by_sev={},
        top=[],
    )

    result = design.process_msg(envelope)

    assert result["patch_type"] == "no_findings"
    assert result["priority"] == "P4"
    assert result["actions_count"] == 0
    assert result["patch_written"].endswith(f"{request_id}.yaml")

    out = patches_dir / f"{request_id}.yaml"
    assert out.exists()
    with open(out) as f:
        body = yaml.safe_load(f)
    assert body["findings_total"] == 0
    assert body["actions"] == []
    assert body["apply_status"] == "pending"  # still pending — humans decide


def test_kernel_exception_propagates_to_caller(patches_dir, mq_root, monkeypatch):
    """(3) When process_msg raises, the exception MUST propagate
    to the caller (dev_mq_consumer's processor wrapper) so it
    nacks instead of acking.

    The consumer-level integration (nack on exception) is tested
    separately in tests/test_dev_mq_consumer.py.  Here we verify
    the kernel half: the exception is not swallowed inside
    process_msg — the caller's try/except actually has a chance
    to run.

    We simulate the failure by monkeypatching yaml.safe_dump
    to raise.  (A set-injected payload would NOT trigger
    yaml.safe_dump to raise on modern pyyaml — sets are dumped
    as !!set tags by default.  Direct monkeypatch is the
    reliable way to inject a controlled failure.)"""
    import yaml as _yaml

    request_id = "rq-bad-003"
    envelope = _finding_envelope(
        request_id=request_id,
        total=1,
        by_sev={"high": 1},
        top=[
            {"type": "yaml_typo", "severity": "high",
             "location": "x.yaml:1", "description": "ok"},
        ],
    )

    def _boom(*a, **kw):
        raise RuntimeError("simulated yaml.safe_dump failure")

    # Patch yaml.safe_dump in the design module's namespace
    # (it imported yaml at module load).  Also patch the yaml
    # module itself so any internal lookups there see the stub.
    monkeypatch.setattr(design.yaml, "safe_dump", _boom)
    monkeypatch.setattr(_yaml, "safe_dump", _boom)

    # The exception must propagate to the caller.  The
    # consumer's processor wrapper catches it and nacks;
    # any other caller (e.g. a manual run) gets the
    # exception and can decide what to do.
    with pytest.raises(RuntimeError, match="simulated yaml.safe_dump"):
        design.process_msg(envelope)
