"""R110-468 — coverage-push r9: tools/dev_im_design_patches.py 0% → 100%

Phase-2.1 processor for im.finding.created MQ topic. Writes
deterministic design patches to .mase/im/patches/<request_id>.yaml.

Targets:
- _patches_dir(): reads MAS_PATCHES_DIR env override, else falls
  back to REPO_ROOT/.mase/im/patches; creates dir if missing.
- process_msg(msg): extracts payload, decides patch_type
  (blocker_remediation P0 / high_remediation P1 /
  low_medium_cleanup P2 / no_findings P4), builds top-3
  actions via _suggest_action, writes yaml to patches dir,
  returns {patch_written, patch_type, priority, actions_count}.
- _suggest_action(finding): heuristic on type-field lowercased.
  yaml→fix_yaml_syntax, secret/leak→rotate_secret_and_remove,
  drift→align_with_pre_push_validator, test→add_or_fix_test,
  doc→update_documentation, else→review_and_manually_fix.
- __main__: stdin json → process_msg → stdout result.
"""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_im_design_patches as dip  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# _patches_dir
# ─────────────────────────────────────────────────────────────────────
class TestPatchesDir:
    def test_default_path(self, monkeypatch, tmp_path):
        # No MAS_PATCHES_DIR override → uses REPO_ROOT/.mase/im/patches
        monkeypatch.delenv("MAS_PATCHES_DIR", raising=False)
        p = dip._patches_dir()
        assert p == dip.DEFAULT_PATCHES_DIR
        assert p.exists()

    def test_override_creates_dir(self, monkeypatch, tmp_path):
        override = tmp_path / "custom_patches"
        monkeypatch.setenv("MAS_PATCHES_DIR", str(override))
        p = dip._patches_dir()
        assert p == override
        assert p.exists()
        assert p.is_dir()

    def test_override_existing_dir(self, monkeypatch, tmp_path):
        override = tmp_path / "existing"
        override.mkdir()
        monkeypatch.setenv("MAS_PATCHES_DIR", str(override))
        p = dip._patches_dir()
        assert p == override
        # No exception — exists_ok=True


# ─────────────────────────────────────────────────────────────────────
# process_msg — patch_type decision branches
# ─────────────────────────────────────────────────────────────────────
def _base_payload(**overrides):
    p = {
        "request_id": "req-001",
        "source": "test-source",
        "timestamp": "2026-09-12T06:00:00Z",
        "findings_total": 0,
        "findings_by_severity": {},
        "findings_by_type": {},
        "findings_top": [],
    }
    p.update(overrides)
    return p


def _msg(payload=None, **msg_overrides):
    m = {
        "msg_id": "msg-001",
        "status": "pending",
        "topic": "im.finding.created",
        "payload": payload or _base_payload(),
    }
    m.update(msg_overrides)
    return m


@pytest.fixture(autouse=True)
def patches_dir(monkeypatch, tmp_path):
    """Auto-use MAS_PATCHES_DIR to isolate writes to tmp_path."""
    monkeypatch.setenv("MAS_PATCHES_DIR", str(tmp_path / "patches"))
    return tmp_path / "patches"


class TestProcessMsg:
    def test_no_findings(self, patches_dir):
        r = dip.process_msg(_msg())
        assert r["patch_type"] == "no_findings"
        assert r["priority"] == "P4"
        assert r["actions_count"] == 0
        # File written
        assert (patches_dir / "req-001.yaml").exists()
        # Patch content checks
        with open(patches_dir / "req-001.yaml") as f:
            patch = yaml.safe_load(f)
        assert patch["schema_version"] == 1
        assert patch["request_id"] == "req-001"
        assert patch["patch_type"] == "no_findings"
        assert patch["priority"] == "P4"
        assert patch["findings_total"] == 0
        assert patch["apply_status"] == "pending"
        assert "Auto-generated" in patch["notes"]
        assert patch["source_msg_id"] == "msg-001"
        assert patch["source_topic"] == "im.finding.created"

    def test_blocker_findings(self, patches_dir):
        msg = _msg(_base_payload(
            findings_total=2,
            findings_by_severity={"blocker": 2},
            findings_by_type={"yaml_typo": 2},
            findings_top=[
                {"type": "yaml_typo", "severity": "blocker",
                 "location": "tools/foo.py:1", "description": "bad yaml"},
            ],
        ))
        r = dip.process_msg(msg)
        assert r["patch_type"] == "blocker_remediation"
        assert r["priority"] == "P0"
        assert r["actions_count"] == 1

    def test_high_findings(self, patches_dir):
        msg = _msg(_base_payload(
            findings_total=1,
            findings_by_severity={"high": 1},
            findings_top=[
                {"type": "drift_check", "severity": "high",
                 "location": "tools/bar.py:5",
                 "description": "drift detected"},
            ],
        ))
        r = dip.process_msg(msg)
        assert r["patch_type"] == "high_remediation"
        assert r["priority"] == "P1"

    def test_low_medium_findings(self, patches_dir):
        # No blocker, no high → low_medium_cleanup P2
        msg = _msg(_base_payload(
            findings_total=3,
            findings_by_severity={"low": 2, "medium": 1},
            findings_top=[
                {"type": "doc_gap", "severity": "low",
                 "location": "x", "description": "y"},
            ],
        ))
        r = dip.process_msg(msg)
        assert r["patch_type"] == "low_medium_cleanup"
        assert r["priority"] == "P2"

    def test_blocker_takes_priority_over_high(self, patches_dir):
        # Both blocker and high present → P0
        msg = _msg(_base_payload(
            findings_total=5,
            findings_by_severity={"blocker": 1, "high": 4},
        ))
        r = dip.process_msg(msg)
        assert r["patch_type"] == "blocker_remediation"
        assert r["priority"] == "P0"

    def test_no_payload(self, patches_dir):
        # msg without 'payload' key → empty payload → no_findings
        msg = {"msg_id": "msg-x", "topic": "im.finding.created"}
        r = dip.process_msg(msg)
        assert r["patch_type"] == "no_findings"
        # request_id falls back to msg_id
        assert (patches_dir / "msg-x.yaml").exists()

    def test_no_request_id_uses_msg_id(self, patches_dir):
        # payload.request_id missing → fallback to msg.msg_id
        msg = {
            "msg_id": "fallback-id",
            "topic": "im.finding.created",
            "payload": _base_payload(request_id=None),
        }
        r = dip.process_msg(msg)
        # file written under fallback-id
        assert (patches_dir / "fallback-id.yaml").exists()

    def test_unknown_msg(self, patches_dir):
        # No msg_id, no payload.request_id → 'unknown'
        msg = {"topic": "im.finding.created", "payload": {}}
        r = dip.process_msg(msg)
        assert (patches_dir / "unknown.yaml").exists()

    def test_top_3_actions_capped(self, patches_dir):
        # findings_top has 5 items → only 3 actions in patch
        msg = _msg(_base_payload(
            findings_total=5,
            findings_by_severity={"high": 5},
            findings_top=[
                {"type": f"type_{i}", "severity": "high",
                 "location": f"f{i}:1", "description": f"d{i}"}
                for i in range(5)
            ],
        ))
        r = dip.process_msg(msg)
        assert r["actions_count"] == 3
        with open(patches_dir / "req-001.yaml") as f:
            patch = yaml.safe_load(f)
        assert len(patch["actions"]) == 3

    def test_idempotent_overwrite(self, patches_dir):
        # Re-running with same request_id overwrites
        msg = _msg(_base_payload(findings_total=1,
                                  findings_by_severity={"low": 1}))
        dip.process_msg(msg)
        first_path = patches_dir / "req-001.yaml"
        assert first_path.exists()

        # Re-run with different patch content
        msg2 = _msg(_base_payload(findings_total=2,
                                   findings_by_severity={"blocker": 2}))
        r2 = dip.process_msg(msg2)
        assert r2["patch_type"] == "blocker_remediation"
        with open(first_path) as f:
            patch = yaml.safe_load(f)
        # Second write overwrote with P0
        assert patch["patch_type"] == "blocker_remediation"

    def test_missing_findings_keys(self, patches_dir):
        # payload exists but lacks findings_* keys
        msg = {"msg_id": "m", "topic": "im.finding.created",
               "payload": {"request_id": "r"}}
        r = dip.process_msg(msg)
        assert r["patch_type"] == "no_findings"
        assert r["actions_count"] == 0

    def test_findings_top_none(self, patches_dir):
        # findings_top = None → list(None or []) = [] → no actions
        msg = _msg(_base_payload(
            findings_total=0,
            findings_top=None,
        ))
        r = dip.process_msg(msg)
        assert r["patch_type"] == "no_findings"
        assert r["actions_count"] == 0

    def test_relative_path_fallback(self, patches_dir):
        # patches dir is OUTSIDE REPO_ROOT → rel fallback to str(out_path)
        r = dip.process_msg(_msg())
        # patch_written is the file name (under tmp_path, not REPO_ROOT)
        assert "req-001.yaml" in r["patch_written"]


# ─────────────────────────────────────────────────────────────────────
# _suggest_action
# ─────────────────────────────────────────────────────────────────────
class TestSuggestAction:
    def test_yaml(self):
        assert dip._suggest_action({"type": "yaml_typo"}) == "fix_yaml_syntax"

    def test_yaml_uppercase(self):
        assert dip._suggest_action({"type": "YAML_DRIFT"}) == "fix_yaml_syntax"

    def test_secret(self):
        assert dip._suggest_action({"type": "secret_leak"}) == \
            "rotate_secret_and_remove_from_history"

    def test_leak(self):
        assert dip._suggest_action({"type": "leak_detected"}) == \
            "rotate_secret_and_remove_from_history"

    def test_drift(self):
        assert dip._suggest_action({"type": "category_drift"}) == \
            "align_with_pre_push_validator"

    def test_test(self):
        assert dip._suggest_action({"type": "test_gap"}) == \
            "add_or_fix_test"

    def test_doc(self):
        assert dip._suggest_action({"type": "doc_missing"}) == \
            "update_documentation"

    def test_default_review(self):
        assert dip._suggest_action({"type": "unknown_type"}) == \
            "review_and_manually_fix"

    def test_empty_type(self):
        # No 'type' key → "" → no match → review_and_manually_fix
        assert dip._suggest_action({}) == "review_and_manually_fix"

    def test_yaml_takes_priority_over_drift(self):
        # "yaml_drift" → yaml match first
        assert dip._suggest_action({"type": "yaml_drift"}) == \
            "fix_yaml_syntax"


# ─────────────────────────────────────────────────────────────────────
# __main__ (CLI)
# ─────────────────────────────────────────────────────────────────────
class TestCLI:
    def test_cli_invocation(self, monkeypatch, tmp_path):
        # Run as subprocess, feed stdin a JSON msg
        monkeypatch.setenv("MAS_PATCHES_DIR", str(tmp_path / "cli_patches"))
        payload = _base_payload(
            findings_total=1,
            findings_by_severity={"blocker": 1},
        )
        msg = _msg(payload)
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "dev_im_design_patches.py")],
            input=json.dumps(msg),
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout)
        assert out["patch_type"] == "blocker_remediation"
        assert out["priority"] == "P0"
        # File written under cli_patches
        assert (tmp_path / "cli_patches" / "req-001.yaml").exists()

    def test_cli_empty_stdin(self, monkeypatch, tmp_path):
        # Empty stdin → msg = {} → process_msg with empty dict
        monkeypatch.setenv("MAS_PATCHES_DIR", str(tmp_path / "empty_patches"))
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "dev_im_design_patches.py")],
            input="",
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT),
        )
        # Should print a result dict even with empty input
        assert result.returncode == 0
