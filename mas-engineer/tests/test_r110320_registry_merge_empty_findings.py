"""
test_r110320_registry_merge_empty_findings.py — R110-320 regression test.

Bug: `tools/dev_registry_merge.py::merge_findings` referenced the
local variable `now` AFTER the `for f_item in findings:` loop that
assigned it. On empty-findings input (a valid per-API value), the
loop was skipped and the post-loop `reg['last_updated'] = now` raised
UnboundLocalError.

Repro (pre-fix):
  $ python3 tools/dev_registry_merge.py --findings '[]' \\
      --registry /tmp/empty.yaml --project r110320-test
  Traceback (most recent call last):
    File ".../dev_registry_merge.py", line 87, in merge_findings
      reg['last_updated'] = now
  UnboundLocalError: cannot access local variable 'now' where it
  is not associated with a value

Fix (R110-320): hoist `now = datetime.datetime.now().isoformat()`
out of the for-loop and assign `reg['last_updated'] = now` once,
before `reg['pattern_stats'] = {...}`. +5/-1 lines in
`tools/dev_registry_merge.py`.

Refs:
- R110-320 directive: mas-engineer/.mase/directives/R110-320-registry-merge-empty-fix.md
- R110-310 (commit 3523302): sitecustomize + COVERAGE_PROCESS_START
  pattern that makes subprocess smoke tests possible; this test
  uses the same subprocess pattern but is unique (R110-310 tested
  only --help, not the empty-findings path)
- Skill: `pre-push-body-claim-verification` (R110-174 + R110-305):
  4 rounds of `git diff --numstat` + `wc -l` re-verify
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# CWD-anchor: tools/ is sibling of tests/, both children of REPO_ROOT
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
TOOL = REPO_ROOT / "tools" / "dev_registry_merge.py"


def _run(findings_json: str, registry_path: Path, project: str = "r110320-test"):
    """Helper: invoke the tool with CWD=REPO_ROOT so relative paths resolve."""
    r = subprocess.run(
        [sys.executable, str(TOOL),
         "--findings", findings_json,
         "--registry", str(registry_path),
         "--project", project],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    return r


@pytest.fixture
def tmp_registry(tmp_path):
    """Empty registry fixture in tmpdir (cleaned up by pytest)."""
    p = tmp_path / "patterns.yaml"
    p.write_text("patterns: []\n")
    return p


class TestEmptyFindingsRegression:
    """R110-320: empty-findings must be a valid (no-op) merge path.

    Pre-fix this raised UnboundLocalError because `now` was assigned
    inside the for-loop over findings. Post-fix, the loop is
    allowed to be empty and `now` is computed once at the end.
    """

    def test_empty_findings_no_append(self, tmp_registry):
        """`--findings '[]'` with an empty registry returns exit 0 + valid JSON."""
        r = _run("[]", tmp_registry)
        assert r.returncode == 0, f"exit {r.returncode}, stderr={r.stderr}"
        data = json.loads(r.stdout)
        # No patterns to merge → 0 new, 0 merged, confidence 0
        assert data["new_patterns"] == 0
        assert data["merged_count"] == 0
        assert data["confidence_avg"] == 0.0

    def test_empty_findings_writes_registry(self, tmp_registry):
        """Empty merge still writes the registry file (with last_updated)."""
        r = _run("[]", tmp_registry)
        assert r.returncode == 0
        assert tmp_registry.exists()
        # The written registry must have last_updated set (proves
        # the post-loop assignment executed without crash)
        import yaml
        reg = yaml.safe_load(tmp_registry.read_text())
        assert "last_updated" in reg, f"missing last_updated in {tmp_registry}"
        assert reg["last_updated"], "last_updated is empty string"
        # No patterns added
        assert reg.get("patterns", []) == []
        assert reg.get("pattern_stats", {}).get("total_patterns", -1) == 0


class TestNonEmptyFindingsNoRegression:
    """R110-320: ensure the fix didn't break the happy path.

    The original code worked when findings was non-empty (the loop
    assigned `now` at least once). Post-fix, `now` is assigned
    unconditionally at the end. These tests verify the non-empty
    path still produces a sensible registry.
    """

    def test_one_finding_creates_one_pattern(self, tmp_registry):
        """A single finding adds exactly 1 new pattern."""
        finding = json.dumps([{
            "type": "Z1",
            "agent": "r110320-tester",
            "detail": "regression-test for empty-findings fix",
            "severity": "hoch",
        }])
        r = _run(finding, tmp_registry, project="r110320-np")
        assert r.returncode == 0, f"exit {r.returncode}, stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["new_patterns"] == 1
        assert data["merged_count"] == 0

        import yaml
        reg = yaml.safe_load(tmp_registry.read_text())
        assert len(reg["patterns"]) == 1
        # Pattern has rule + evidence fields; agent is stored in
        # evidence[0].patch, not as a top-level key
        p = reg["patterns"][0]
        assert p["name"]  # type-mapped name set
        assert p["count"] == 1
        assert "r110320-tester" in p["evidence"][0]["patch"]
        # last_updated still present
        assert "last_updated" in reg

    def test_repeated_finding_increments_count(self, tmp_registry):
        """Calling the tool twice with the same finding merges (count++) not appends (count=2)."""
        finding = json.dumps([{
            "type": "Z2",
            "agent": "r110320-tester",
            "detail": "merge path coverage",
            "severity": "mittel",
        }])
        r1 = _run(finding, tmp_registry, project="r110320-mp")
        assert r1.returncode == 0
        d1 = json.loads(r1.stdout)
        assert d1["new_patterns"] == 1
        assert d1["merged_count"] == 0

        # 2nd call: same finding, same project → existing pattern
        # gets count++ and last_seen update (not a new pattern)
        r2 = _run(finding, tmp_registry, project="r110320-mp")
        assert r2.returncode == 0
        d2 = json.loads(r2.stdout)
        assert d2["new_patterns"] == 0, f"got new_patterns={d2['new_patterns']}, expected 0 (merge)"
        assert d2["merged_count"] == 1, f"got merged_count={d2['merged_count']}, expected 1"

        import yaml
        reg = yaml.safe_load(tmp_registry.read_text())
        # Still only 1 pattern, but count==2
        assert len(reg["patterns"]) == 1
        assert reg["patterns"][0]["count"] == 2


class TestCollisionHandler:
    """R110-321: cover the `n += 1` line-23 collision handler.

    The 4 R110-320 tests use unique `type` values ('Z1', 'Z2'),
    so the `existing_ids` set never contains a collision with the
    `n=1` candidate. This test pre-seeds the registry with a
    "fake" pattern whose name != 'cross_generisch' (so it doesn't
    match by name in line 50-53) but whose id collides with what
    `generate_id('Z3', ...)` would return. This forces the
    collision branch to fire: `n=1` collides → `n=2` → ID `-002`.

    Real-world use: this only happens if a manual edit or
    out-of-band writer creates a registry pattern with a
    conflicting ID. Not a likely production path, but the
    defensive code (line 23) is still meaningful — without it,
    two patterns would share an ID and downstream tooling
    (lookup-by-id) would break.
    """

    def test_id_collision_uses_n2_id(self, tmp_registry):
        """Pre-seed with id='BP-CF-GENERI-001' (name='__fake__' so existing-by-name misses).

        Then a finding type='Z3' (which generates base='BP-CF-GENERI')
        finds existing_ids contains the base, n=1 collides, n=2 → ID '-002'.
        """
        import yaml
        # Pre-seed: pattern with ID matching what generate_id(Z3) would
        # produce, but name that DOESN'T match (so existing-by-name
        # in line 50-53 returns None, falling through to line 66
        # generate_id call where the collision fires).
        pre_seed = {
            'patterns': [
                {
                    'id': 'BP-CF-GENERI-001',
                    'name': '__fake_collision_seeder__',
                    'count': 1,
                }
            ]
        }
        tmp_registry.write_text(yaml.dump(pre_seed))

        finding = json.dumps([{
            "type": "Z3",  # → PATTERN_NAMES[Z3]='cross_generisch' → base='BP-CF-GENERI'
            "agent": "r110321-tester",
            "detail": "force line 23 collision path",
            "severity": "hoch",
        }])

        r = _run(finding, tmp_registry, project="r110321-collision")
        assert r.returncode == 0, f"exit {r.returncode}, stderr={r.stderr}"
        d = json.loads(r.stdout)
        assert d["new_patterns"] == 1, f"got new_patterns={d['new_patterns']}, expected 1 (collision was not duplicated)"
        assert d["merged_count"] == 0, f"got merged_count={d['merged_count']}, expected 0 (name mismatch, no merge)"

        reg = yaml.safe_load(tmp_registry.read_text())
        # 2 patterns: the pre-seed + the new one with id=-002
        assert len(reg["patterns"]) == 2, f"got {len(reg['patterns'])} patterns, expected 2"
        # Pre-seed untouched
        assert reg["patterns"][0]["id"] == "BP-CF-GENERI-001"
        assert reg["patterns"][0]["name"] == "__fake_collision_seeder__"
        # New pattern: ID must be -002 (n incremented after collision)
        new_pattern = reg["patterns"][1]
        assert new_pattern["id"] == "BP-CF-GENERI-002", (
            f"expected id='BP-CF-GENERI-002' (n=2 after collision), "
            f"got {new_pattern['id']!r} — line 23 collision path not taken"
        )
        assert new_pattern["name"] == "cross_generisch"
        assert new_pattern["count"] == 1
