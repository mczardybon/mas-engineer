"""R110-470 — coverage-push r9: tools/dev_im_finder_scan.py 33% → high

Targets the testable surface of the CLI wrapper (302 stmts):
- _wrap_check_with_sync (decorator that syncs mod.findings/fid
  ↔ lib.findings/fid before AND after each check_* call)
- __getattr__ (PEP 562 module proxy for _PROXIED_ATTRS; reads
  mod.__dict__ first for 'findings'/'fid', falls back to lib)
- add_finding (thin wrapper: syncs findings/fid/SEVERITY_FILTER
  → lib, calls lib.add_finding, syncs back)
- main() end-to-end via subprocess (controlled cwd with minimal
  repo: no .mase/, no recipe/, no docs/, so YAML walker yields
  empty findings; JSON envelope always printed)

KEY OBSERVATIONS (verified via runtime probe):
- lib.SEVERITY_FILTER default = {'medium', 'blocker', 'high'}
  (NO 'low'). Low-severity findings are SILENTLY filtered out.
- lib.add_finding returns None (implicit), not the fid.
- lib.add_finding mutates lib.findings in-place via .append().
- cli.add_finding sync only runs for attrs in CLI globals
  ('findings'/'fid'/'SEVERITY_FILTER'); on fresh import, only
  findings and fid are populated in globals — SEVERITY_FILTER is
  proxied via __getattr__ but NOT synced to lib.
- cli module loads its LIB via importlib.util.spec_from_file_location
  with name 'dev_im_finder_scan_lib' (the bare name, registered in
  sys.modules). When test imports 'tools.dev_im_finder_scan_lib',
  Python creates a SEPARATE module instance. Therefore:
  - `lib` in this test is NOT cli._lib_mod
  - To verify cli.add_finding's effects, inspect cli._lib_mod
    directly, NOT `lib` (the tools.X namespace).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools import dev_im_finder_scan as cli  # noqa: E402
from tools import dev_im_finder_scan_lib as lib  # noqa: E402

# The actual LIB the CLI writes to (different from `lib` above!)
CLI_LIB = cli._lib_mod


# ─────────────────────────────────────────────────────────────────────
# _wrap_check_with_sync
# ─────────────────────────────────────────────────────────────────────
class TestWrapCheckWithSync:
    def test_no_globals_means_no_crash(self):
        # When 'findings'/'fid' are NOT in CLI globals, the wrapper
        # still runs the function (the in-globals guards are no-ops).
        @cli._wrap_check_with_sync
        def noop(findings):
            findings.append(1)
            return "ok"

        result = noop([])
        assert result == "ok"

    def test_sync_forwards_to_lib(self):
        # Set CLI globals → wrapper syncs them into CLI_LIB BEFORE call
        original_lib_findings = CLI_LIB.findings
        original_lib_fid = CLI_LIB.fid
        try:
            local_findings = []
            cli.findings = local_findings
            cli.fid = 999

            @cli._wrap_check_with_sync
            def capt(findings):
                # CLI_LIB should now see our local values
                assert CLI_LIB.findings is local_findings
                assert CLI_LIB.fid == 999
                findings.append("x")
                return 42

            result = capt(local_findings)
            assert result == 42
            # Sync back: cli.findings == CLI_LIB.findings (still same list)
            assert cli.findings is CLI_LIB.findings
        finally:
            cli.findings = original_lib_findings
            cli.fid = original_lib_fid

    def test_passes_args_and_kwargs(self):
        @cli._wrap_check_with_sync
        def echo(findings, a, b=10, *, k=None):
            return (a, b, k)

        assert echo([], 1, 2, k=3) == (1, 2, 3)

    def test_functools_wraps_preserves_name(self):
        @cli._wrap_check_with_sync
        def my_named_fn(findings):
            return findings

        assert my_named_fn.__name__ == "my_named_fn"


# ─────────────────────────────────────────────────────────────────────
# __getattr__ (PEP 562 proxy)
# ─────────────────────────────────────────────────────────────────────
class TestGetattr:
    def test_proxied_attr_from_cli_lib(self):
        # ALL_YAMLS lives in CLI_LIB → proxy returns it
        v = cli.ALL_YAMLS
        assert v is CLI_LIB.ALL_YAMLS

    def test_findings_returns_local_when_present(self):
        # If test sets cli.findings = [...], proxy returns that
        sentinel = ["local-marker-xyz"]
        cli.findings = sentinel
        try:
            assert cli.findings is sentinel
        finally:
            cli.findings = []

    def test_fid_returns_local_when_present(self):
        cli.fid = 12345
        try:
            assert cli.fid == 12345
        finally:
            cli.fid = 0

    def test_unproxied_attr_raises(self):
        with pytest.raises(AttributeError) as exc_info:
            cli.this_is_not_a_real_attr_name_xyz
        assert "no attribute" in str(exc_info.value)

    def test_severity_filter_proxied_default(self):
        # Default SEVERITY_FILTER does NOT include 'low'
        v = cli.SEVERITY_FILTER
        assert v is CLI_LIB.SEVERITY_FILTER
        assert "low" not in v
        assert "high" in v

    def test_run_yaml_scan_proxied(self):
        assert callable(cli.run_yaml_scan)


# ─────────────────────────────────────────────────────────────────────
# add_finding (CLI wrapper around CLI_LIB.add_finding)
# ─────────────────────────────────────────────────────────────────────
class TestAddFinding:
    def setup_method(self):
        # Snapshot CLI_LIB state (the one CLI writes to)
        self._orig_cli_lib_findings = CLI_LIB.findings
        self._orig_cli_lib_fid = CLI_LIB.fid
        self._orig_cli_lib_sev = CLI_LIB.SEVERITY_FILTER
        # Reset CLI_LIB
        CLI_LIB.findings = []
        CLI_LIB.fid = 0
        CLI_LIB.SEVERITY_FILTER = {"blocker", "high", "medium"}
        # Reset CLI globals
        if "findings" in cli.__dict__:
            cli.findings = []
        if "fid" in cli.__dict__:
            cli.fid = 0
        if "SEVERITY_FILTER" in cli.__dict__:
            cli.SEVERITY_FILTER = {"blocker", "high", "medium"}

    def teardown_method(self):
        CLI_LIB.findings = self._orig_cli_lib_findings
        CLI_LIB.fid = self._orig_cli_lib_fid
        CLI_LIB.SEVERITY_FILTER = self._orig_cli_lib_sev
        if "findings" in cli.__dict__:
            cli.findings = []
        if "fid" in cli.__dict__:
            cli.fid = 0

    def test_basic_finding_medium(self):
        # 'medium' is in default SEVERITY_FILTER
        result = cli.add_finding(
            "TST", "medium", "f.py", "issue", "impact", "fix")
        assert result is None
        assert len(CLI_LIB.findings) == 1
        f = CLI_LIB.findings[0]
        assert f["type"] == "TST"
        assert "id" in f
        assert f["severity"] == "medium"

    def test_syncs_back_to_cli(self):
        cli.add_finding("A", "medium", "f", "i", "im", "fx")
        # cli.findings (after sync) == CLI_LIB.findings
        assert "findings" in cli.__dict__
        assert cli.findings is CLI_LIB.findings

    def test_line_kwargs_dont_crash(self):
        # line_start/line_end are consumed by compute_structural_pattern
        # (lib.add_finding) and NOT stored in the finding dict. We just
        # verify the call doesn't raise and produces a finding.
        cli.add_finding("A", "medium", "f", "i", "im", "fx",
                        line_start=10, line_end=12)
        assert len(CLI_LIB.findings) == 1
        f = CLI_LIB.findings[0]
        assert f["type"] == "A"
        # structural_pattern was computed (uses line_start/line_end)
        assert "structural_pattern" in f

    def test_pattern_kwargs_dont_crash(self):
        # pattern/severity_override kwargs are passed through
        # to compute_structural_pattern. We verify the call succeeds
        # and produces a finding with structural_pattern.
        cli.add_finding("A", "medium", "f", "i", "im", "fx",
                        pattern="p123", severity_override="high")
        assert len(CLI_LIB.findings) == 1
        f = CLI_LIB.findings[0]
        assert f["type"] == "A"
        # structural_pattern encodes the pattern kwarg
        assert "structural_pattern" in f
        assert f["structural_pattern"]  # non-empty string

    def test_extra_kwargs_accepted(self):
        # Unknown kwargs should not raise (they go to pattern_kwargs
        # and are consumed by compute_structural_pattern).
        cli.add_finding("A", "medium", "f", "i", "im", "fx",
                        context="ctx", line_count=42)
        assert len(CLI_LIB.findings) == 1

    def test_with_local_findings_override(self):
        local = []
        cli.findings = local
        cli.add_finding("X", "medium", "f", "i", "im", "fx")
        # CLI_LIB.findings now points to local (synced from CLI)
        assert CLI_LIB.findings is local
        assert len(local) == 1
        assert local[0]["type"] == "X"

    def test_low_severity_filtered_silently(self):
        # Default SEVERITY_FILTER = {medium, blocker, high}
        # 'low' → filtered, no finding, no fid increment
        cli.add_finding("LOW-1", "low", "f", "i", "im", "fx")
        assert len(CLI_LIB.findings) == 0
        assert CLI_LIB.fid == 0

    def test_high_severity_passes(self):
        cli.add_finding("HIGH", "high", "f", "i", "im", "fx")
        assert len(CLI_LIB.findings) == 1
        assert CLI_LIB.findings[0]["severity"] == "high"

    def test_blocker_severity_passes(self):
        cli.add_finding("BLK", "blocker", "f", "i", "im", "fx")
        assert len(CLI_LIB.findings) == 1
        assert CLI_LIB.findings[0]["severity"] == "blocker"

    def test_multiple_findings_increment_fid(self):
        cli.add_finding("A", "medium", "f", "i", "im", "fx")
        cli.add_finding("B", "high", "f", "i", "im", "fx")
        cli.add_finding("C", "blocker", "f", "i", "im", "fx")
        assert CLI_LIB.fid == 3
        assert len(CLI_LIB.findings) == 3


# ─────────────────────────────────────────────────────────────────────
# main() subprocess smoke test (minimal cwd)
# ─────────────────────────────────────────────────────────────────────
class TestMainSmoke:
    def test_main_runs_in_empty_dir(self, tmp_path):
        # tmp_path has no recipe/, docs/, .mase/ → empty findings
        script = REPO_ROOT / "tools" / "dev_im_finder_scan.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=60,
            cwd=str(tmp_path),
        )
        # Scanner should print JSON envelope even with empty repo
        assert "---JSON_START---" in result.stdout, \
            f"no JSON marker: stdout[:500]={result.stdout[:500]}"
        json_part = result.stdout.split("---JSON_START---", 1)[1]
        parsed = json.loads(json_part)
        assert "findings" in parsed
        assert "summary" in parsed


# ─────────────────────────────────────────────────────────────────────
# Module import side-effects (R110-411b guard)
# ─────────────────────────────────────────────────────────────────────
class TestImportGuards:
    def test_run_yaml_scan_callable(self):
        # After import, run_yaml_scan should be callable (gated
        # behind if __name__ == '__main__' now per R110-411b)
        assert callable(cli.run_yaml_scan)

    def test_findings_proxy_returns_list_after_reload(self):
        # Reload module → fresh state
        import importlib
        importlib.reload(cli)
        # After fresh import, cli.findings should still be readable
        f = cli.findings
        assert isinstance(f, list)
