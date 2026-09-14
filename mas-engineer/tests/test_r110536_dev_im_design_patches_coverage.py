"""R110-536 coverage tests for tools/dev_im_design_patches.py.

Module: 158 LOC, ~59 stmts, 1 main function + helper, 0% covered.

Functions tested:
  - _patches_dir()               lines 35-48
  - process_msg(msg)             lines 51-134
  - _suggest_action(finding)     lines 137-150
  - __main__ smoke test          lines 153-158

Strategy: Direct function calls with tmp_path fixture.
Use MAS_PATCHES_DIR env var to redirect patch output to tmp dir.

Key paths to cover:
  - _patches_dir() (35-48):
    - MAS_PATCHES_DIR set → uses override (43-44)
    - default → uses DEFAULT_PATCHES_DIR (46)
    - makedirs parents=True exist_ok (47)
  - process_msg() (51-134):
    - payload.get('request_id') (65)
    - msg_id fallback (65)
    - findings_total default 0 (66)
    - by_severity, by_type, findings_top default empty (67-69)
    - has_blocker, has_high (72-73)
    - patch_type/priority branches (74-85): blocker, high, low/medium, no_findings
    - actions list (88-96)
    - patch dict (98-117)
    - yaml.safe_dump (121)
    - relative_to path (126)
    - ValueError path (127)
    - return dict (129-134)
  - _suggest_action() (137-150):
    - yaml in type → fix_yaml_syntax
    - secret/leak → rotate
    - drift → align_with_pre_push_validator
    - test → add_or_fix_test
    - doc → update_documentation
    - default → review_and_manually_fix
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.dev_im_design_patches as dp  # noqa: E402


# ====================== helpers ==================================

@pytest.fixture
def patches_dir(tmp_path, monkeypatch):
    """Redirect MAS_PATCHES_DIR to tmp_path; auto-cleans env after test."""
    monkeypatch.setenv("MAS_PATCHES_DIR", str(tmp_path))
    yield tmp_path


def _make_msg(*, request_id="req-001", findings_total=5,
              findings_by_severity=None, findings_by_type=None,
              findings_top=None, msg_id="msg-001", topic="im.finding.created",
              source="im-finder-scan"):
    return {
        "msg_id": msg_id,
        "status": "pending",
        "topic": topic,
        "payload": {
            "request_id": request_id,
            "source": source,
            "findings_total": findings_total,
            "findings_by_severity": findings_by_severity or {},
            "findings_by_type": findings_by_type or {},
            "findings_top": findings_top or [],
        },
    }


# ====================== _patches_dir =============================

def test_patches_dir_uses_override(patches_dir, monkeypatch):
    """Covers lines 43-44: MAS_PATCHES_DIR set → use override."""
    result = dp._patches_dir()
    assert result == patches_dir
    assert result.exists()


def test_patches_dir_default_path(monkeypatch, tmp_path):
    """Covers line 46: no override → DEFAULT_PATCHES_DIR.

    We can't actually let DEFAULT_PATCHES_DIR be created, so we
    unset env var and monkeypatch REPO_ROOT to a tmp dir.
    """
    monkeypatch.delenv("MAS_PATCHES_DIR", raising=False)
    # Monkeypatch DEFAULT_PATCHES_DIR via module attribute
    fake_default = tmp_path / "default_patches"
    monkeypatch.setattr(dp, "DEFAULT_PATCHES_DIR", fake_default)
    result = dp._patches_dir()
    assert result == fake_default
    assert result.exists()


def test_patches_dir_mkdir_parents(patches_dir):
    """Covers line 47: makedirs(parents=True, exist_ok=True).

    Pre-condition: patches_dir subdir doesn't exist yet.
    """
    nested = patches_dir / "nested" / "subdir"
    monkeypatch = None
    # Set override to nested path
    os.environ["MAS_PATCHES_DIR"] = str(nested)
    try:
        result = dp._patches_dir()
        assert result == nested
        assert nested.exists()
    finally:
        del os.environ["MAS_PATCHES_DIR"]


# ====================== process_msg ==============================

def test_process_msg_blocker_severity(patches_dir):
    """Covers lines 72-76: blocker severity → P0 blocker_remediation."""
    msg = _make_msg(
        request_id="r-blocker",
        findings_total=3,
        findings_by_severity={"blocker": 2, "high": 1},
        findings_top=[{"type": "yaml-syntax", "severity": "blocker",
                       "location": "recipe/x.yaml", "description": "broken"}],
    )
    result = dp.process_msg(msg)
    assert result["patch_type"] == "blocker_remediation"
    assert result["priority"] == "P0"
    assert result["actions_count"] == 1
    assert (patches_dir / "r-blocker.yaml").exists()


def test_process_msg_high_severity(patches_dir):
    """Covers lines 77-79: high (no blocker) → P1 high_remediation."""
    msg = _make_msg(
        request_id="r-high",
        findings_total=2,
        findings_by_severity={"high": 2},
    )
    result = dp.process_msg(msg)
    assert result["patch_type"] == "high_remediation"
    assert result["priority"] == "P1"


def test_process_msg_low_medium(patches_dir):
    """Covers lines 80-82: findings_total>0, no high/blocker → P2."""
    msg = _make_msg(
        request_id="r-low",
        findings_total=1,
        findings_by_severity={"medium": 1},
    )
    result = dp.process_msg(msg)
    assert result["patch_type"] == "low_medium_cleanup"
    assert result["priority"] == "P2"


def test_process_msg_no_findings(patches_dir):
    """Covers lines 83-85: findings_total=0 → P4 no_findings."""
    msg = _make_msg(request_id="r-empty", findings_total=0)
    result = dp.process_msg(msg)
    assert result["patch_type"] == "no_findings"
    assert result["priority"] == "P4"


def test_process_msg_request_id_fallback(patches_dir):
    """Covers line 65: payload.request_id missing → msg.msg_id fallback."""
    msg = _make_msg(msg_id="msg-fallback", request_id=None)
    msg["payload"].pop("request_id", None)  # ensure missing
    msg["payload"]["findings_total"] = 1
    result = dp.process_msg(msg)
    assert "msg-fallback" in result["patch_written"]


def test_process_msg_request_id_default_unknown(patches_dir):
    """Covers line 65: msg_id missing entirely → 'unknown'.

    Note: msg_id=None (key exists, value None) makes request_id
    literal None because `get(key, default)` only applies default
    when key is MISSING, not when value is None. We test the
    intended fallback (msg_id key absent entirely).
    """
    msg = {"topic": "t", "payload": {"findings_total": 0}}  # no msg_id
    result = dp.process_msg(msg)
    assert "unknown.yaml" in result["patch_written"]


def test_process_msg_findings_defaults(patches_dir):
    """Covers lines 66-69: missing fields default to 0/{}/[]."""
    msg = {"topic": "t", "payload": {}}  # no msg_id, no request_id
    result = dp.process_msg(msg)
    assert result["patch_type"] == "no_findings"
    # Patch file should exist and have default fields
    patch = yaml.safe_load(open(patches_dir / "unknown.yaml"))
    assert patch["findings_total"] == 0
    assert patch["findings_by_severity"] == {}
    assert patch["actions"] == []


def test_process_msg_actions_capped_at_3(patches_dir):
    """Covers line 89: actions = findings_top[:3]."""
    findings_top = [
        {"type": f"type-{i}", "severity": "high",
         "location": f"file-{i}.yaml", "description": f"d{i}"}
        for i in range(10)
    ]
    msg = _make_msg(
        request_id="r-cap",
        findings_total=10,
        findings_by_severity={"high": 10},
        findings_top=findings_top,
    )
    result = dp.process_msg(msg)
    assert result["actions_count"] == 3
    patch = yaml.safe_load(open(patches_dir / "r-cap.yaml"))
    assert len(patch["actions"]) == 3
    assert patch["actions"][0]["type"] == "type-0"


def test_process_msg_action_default_fields(patches_dir):
    """Covers lines 91-94: missing fields in finding → defaults."""
    msg = _make_msg(
        request_id="r-def",
        findings_total=1,
        findings_by_severity={"high": 1},
        findings_top=[{}],  # empty finding
    )
    dp.process_msg(msg)
    patch = yaml.safe_load(open(patches_dir / "r-def.yaml"))
    a = patch["actions"][0]
    assert a["type"] == "?"
    assert a["severity"] == "?"
    assert a["location"] == "?"
    assert a["description"] == ""


def test_process_msg_action_suggested(patches_dir):
    """Covers line 95: action comes from _suggest_action."""
    msg = _make_msg(
        request_id="r-sug",
        findings_total=1,
        findings_by_severity={"high": 1},
        findings_top=[{"type": "yaml-syntax-error", "severity": "high",
                       "location": "x", "description": "d"}],
    )
    dp.process_msg(msg)
    patch = yaml.safe_load(open(patches_dir / "r-sug.yaml"))
    assert patch["actions"][0]["action"] == "fix_yaml_syntax"


def test_process_msg_patch_fields(patches_dir):
    """Covers lines 98-117: all patch fields populated correctly."""
    msg = _make_msg(
        request_id="r-fields",
        msg_id="src-msg-1",
        topic="im.finding.created",
        source="im-finder-scan-v2",
        findings_total=7,
        findings_by_severity={"high": 3, "medium": 4},
        findings_by_type={"yaml": 5, "drift": 2},
    )
    dp.process_msg(msg)
    patch = yaml.safe_load(open(patches_dir / "r-fields.yaml"))
    assert patch["schema_version"] == 1
    assert patch["request_id"] == "r-fields"
    assert patch["source_msg_id"] == "src-msg-1"
    assert patch["source_topic"] == "im.finding.created"
    assert patch["generated_from"] == "im-finder-scan-v2"
    assert patch["findings_total"] == 7
    assert patch["findings_by_severity"] == {"high": 3, "medium": 4}
    assert patch["findings_by_type"] == {"yaml": 5, "drift": 2}
    assert patch["apply_status"] == "pending"
    assert "Auto-generated" in patch["notes"]


def test_process_msg_yaml_dump_format(patches_dir):
    """Covers line 121: yaml.safe_dump writes valid YAML."""
    msg = _make_msg(request_id="r-yaml", findings_total=1,
                    findings_by_severity={"high": 1})
    dp.process_msg(msg)
    p = patches_dir / "r-yaml.yaml"
    assert p.exists()
    # Valid YAML, parses
    loaded = yaml.safe_load(open(p))
    assert isinstance(loaded, dict)


def test_process_msg_relative_path_in_repo(patches_dir):
    """Covers lines 125-128: relative_to REPO_ROOT path returned.

    patches_dir (tmp_path) is NOT under REPO_ROOT, so the
    ValueError fallback (line 127) is taken: rel = str(out_path).
    patch_written should equal the absolute out_path string.
    """
    msg = _make_msg(request_id="r-rel", findings_total=0)
    result = dp.process_msg(msg)
    expected = str(patches_dir / "r-rel.yaml")
    assert result["patch_written"] == expected


def test_process_msg_returns_status_dict(patches_dir):
    """Covers lines 129-134: return dict shape."""
    msg = _make_msg(request_id="r-ret", findings_total=2,
                    findings_by_severity={"high": 2},
                    findings_top=[{"type": "test"}])
    result = dp.process_msg(msg)
    assert set(result.keys()) == {"patch_written", "patch_type", "priority", "actions_count"}
    assert isinstance(result["actions_count"], int)


# ====================== _suggest_action ==========================

def test_suggest_action_yaml():
    """Covers line 140-141: 'yaml' in type → fix_yaml_syntax."""
    assert dp._suggest_action({"type": "yaml-syntax"}) == "fix_yaml_syntax"


def test_suggest_action_secret():
    """Covers line 142-143: 'secret' or 'leak' → rotate."""
    assert dp._suggest_action({"type": "secret-leak"}) == "rotate_secret_and_remove_from_history"
    assert dp._suggest_action({"type": "API-leak"}) == "rotate_secret_and_remove_from_history"


def test_suggest_action_drift():
    """Covers line 144-145: 'drift' → align_with_pre_push_validator."""
    assert dp._suggest_action({"type": "category-drift"}) == "align_with_pre_push_validator"


def test_suggest_action_test():
    """Covers line 146-147: 'test' → add_or_fix_test."""
    assert dp._suggest_action({"type": "missing-test"}) == "add_or_fix_test"


def test_suggest_action_doc():
    """Covers line 148-149: 'doc' → update_documentation."""
    assert dp._suggest_action({"type": "doc-typo"}) == "update_documentation"


def test_suggest_action_default():
    """Covers line 150: default → review_and_manually_fix."""
    assert dp._suggest_action({"type": "weird-unknown-type"}) == "review_and_manually_fix"
    assert dp._suggest_action({}) == "review_and_manually_fix"


def test_suggest_action_case_insensitive():
    """Covers line 140: 'yaml' check uses .lower()."""
    assert dp._suggest_action({"type": "YAML-SYNTAX"}) == "fix_yaml_syntax"


# ====================== __main__ smoke ===========================

def _run_cli(payload_dict):
    """Run the module as a script with stdin = JSON payload."""
    proc = subprocess.run(
        [sys.executable, "-m", "tools.dev_im_design_patches"],
        input=json.dumps(payload_dict),
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_main_smoke_runs(monkeypatch, tmp_path):
    """Covers lines 153-158: __main__ smoke reads stdin and prints result."""
    monkeypatch.setenv("MAS_PATCHES_DIR", str(tmp_path))
    msg = _make_msg(request_id="smoke-1", findings_total=1,
                    findings_by_severity={"high": 1})
    code, out, err = _run_cli(msg)
    # Smoke doesn't exit with explicit code; just prints result
    assert "patch_written" in out
    parsed = json.loads(out)
    assert parsed["patch_type"] == "high_remediation"
