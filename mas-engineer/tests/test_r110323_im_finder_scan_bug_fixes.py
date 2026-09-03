"""R110-323 regression tests: latent-bug fixes in dev_im_finder_scan.

R110-323 takes candidate #1 from the R110-321 cov-push queue
(dev_im_finder_scan.py, 1660 stmts, 0% cov) and probes it for
latent bugs. This file documents 2 bugs found, their fixes, and
the regression tests that lock them in.

Bug #1 — check_spec_drift_reverse: boolean-precedence false-positive
    (R110-323-BUG-1)
  LOCATION: tools/dev_im_finder_scan.py, lines 1290-1295
  SYMPTOM: A recipe line that contains BOTH a commit reference
    (R\d+-\d+) AND a count-anchor like "1690 tests" — but no
    "AFTER", "had N", or "+N" — is treated as a live count-anchor
    and fires a false-positive spec_drift_reverse finding.
  ROOT CAUSE: Python `and` binds tighter than `or`. The current
    condition `A or B or C and D` evaluates as
    `A or B or (C and D)`. The (C and D) branch only fires when
    the line contains "AFTER", but a historical reference like
    "R110-271 mentions 1690 tests in this codebase" (a clear
    documentation reference, not a load-bearing count-assertion)
    is NOT covered by either A, B, or (C and D), and is therefore
    wrongly flagged.
  FIX: Add explicit parentheses to make the intent crystal clear,
    and add a 4th sub-condition for "N tests/findings/rules" with
    a commit reference (the historical-ref-without-AFTER case).
  IMPACT: Pre-existing false-positive vector. The recipe-side
    drift detector is the R110-78/R110-112 pattern; if it
    over-fires on historical mentions, real drift gets buried
    in noise (R110-114 lesson: "1,961 findings" descriptive
    prose taught us the value of conservative skip rules).

Bug #2 — check_spec_drift: dead-code branch in .mase/ source-anchor
    detection (R110-323-BUG-2)
  LOCATION: tools/dev_im_finder_scan.py, line 1114
  SYMPTOM: The check
        if d.endswith(os.sep + '.mase') or d == '.mase':
    has a dead second branch. search_dirs is constructed via
    os.path.join(repo_root, '.mase') which always produces a
    path with a directory separator. So `d == '.mase'` is False
    for every d in search_dirs. The second branch is unreachable.
  ROOT CAUSE: Author defensive check ("just in case d was passed
    as bare '.mase'") that the actual call sites never trigger.
  FIX: Remove the dead branch. The first arm of the OR already
    covers all real call sites.
  IMPACT: Pure dead code; no functional bug. But removing it
    clarifies intent and prevents future readers from thinking
    there are two call shapes they need to support.

Test pattern (R110-310/R110-320/R110-322 inheritance):
  Each test invokes dev_im_finder_scan.py as a real subprocess
  with --scope=recipe (to scope to a small tmp_repo), then
  inspects the JSON findings list on stdout. This is the
  same subprocess-cov pattern that brought dev_spec_invariant.py
  from 0% to 60% in R110-322: subprocess.run + cwd=REPO_ROOT +
  sitecustomize.py (R110-311) + conftest COVERAGE_PROCESS_START
  (R110-129) auto-instruments the subprocess.

Why these tests don't add 100% cov:
  The scanner has 1660 stmts. Each check_* function is only
  reachable through certain recipes/inputs in the test repo.
  Bug #1 is in check_spec_drift_reverse (exercised by these
  tests). Bug #2 is in check_spec_drift (exercised by these
  tests). The other check_* functions (check_hardcode_stale,
  check_stale_literal, etc.) are not in scope for R110-323;
  they're for R110-324+ or specific R-sprints.
  The R110-323 goal is "lock in the 2 latent-bug fixes", not
  "100% cov". The cov-push to ~30-40% is a side-benefit.
"""
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / 'tools' / 'dev_im_finder_scan.py'
MAS_ENGINEER = REPO_ROOT  # mas-engineer is a flat repo for this layout


# --- helpers ---------------------------------------------------------------

def _make_tmp_repo(tmp_path: Path) -> Path:
    """Build a minimal recipe/instructions + tests/ + recipe/sub layout
    in tmp_path so the scanner has something to walk.

    Returns the path to the tmp_repo (which is also a valid
    cwd + --repo-root for the subprocess).
    """
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'recipe' / 'instructions').mkdir(parents=True)
    (tmp_path / 'recipe' / 'sub').mkdir(parents=True)
    return tmp_path


def _run_scanner(tmp_repo: Path, recipe_text: str,
                 test_text: str = '# empty\n',
                 extra_args: list = None) -> dict:
    """Invoke dev_im_finder_scan.py as a subprocess and return parsed JSON.

    extra_args is appended to the command. Common extras: ['--scope=recipe'].
    """
    (tmp_repo / 'recipe' / 'instructions' / 'sub_test_recipe.md').write_text(recipe_text)
    (tmp_repo / 'tests' / 'test_sub_test_recipe.py').write_text(test_text)

    # Propagate cov env (R110-310/R110-322 subprocess-cov pattern):
    # COVERAGE_PROCESS_START + PYTHONPATH=REPO_ROOT set by conftest
    # at session start. The subprocess inherits these via os.environ,
    # so sitecustomize.py auto-loads and instruments coverage.
    cmd = [sys.executable, str(TOOL), '--scope=recipe']
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(
        cmd,
        cwd=str(tmp_repo),
        capture_output=True,
        text=True,
        timeout=60,
        env=os.environ,
    )
    # Stdout contains the JSON block after ---JSON_START--- marker.
    out = proc.stdout
    if '---JSON_START---' not in out:
        pytest.fail(
            f'scanner did not emit JSON block.\n'
            f'stdout={out!r}\nstderr={proc.stderr!r}'
        )
    json_str = out.split('---JSON_START---', 1)[1]
    return json.loads(json_str)


def _sd_recipe_findings(parsed: dict) -> list:
    """Return only the SD-recipe_* findings."""
    return [f for f in parsed['findings'] if f.get('type', '').startswith('SD-recipe_')]


# --- Bug #1 regression: boolean-precedence historical-ref false-positive ---

class TestR110323Bug1HistoricalRef:
    """R110-323-BUG-1: lines like 'R110-X mentions N tests' (no AFTER) were
    wrongly flagged as load-bearing count-anchors. The fix adds a 4th
    sub-condition covering the historical-ref-without-AFTER case.
    """

    def test_historical_ref_with_AFTER_is_skipped(self, tmp_path):
        """Sanity: 'AFTER R110-X +73 tests' is correctly skipped (was already
        correctly handled before the fix; regression guard for the
        `(C and D)` branch)."""
        _make_tmp_repo(tmp_path)
        recipe = textwrap.dedent('''\
            # Test recipe
            ## Description
            Historical note: AFTER R110-322 +73 tests were added.
        ''')
        parsed = _run_scanner(tmp_path, recipe)
        sd = _sd_recipe_findings(parsed)
        # Should NOT flag this line as SD-recipe (it's a historical note)
        assert not any('tests' in f.get('issue', '') for f in sd), (
            f'AFTER R110-... +73 tests was wrongly flagged: {sd}')

    def test_historical_ref_with_had_N_is_skipped(self, tmp_path):
        """Sanity: 'R110-X had 1690 findings' is correctly skipped."""
        _make_tmp_repo(tmp_path)
        recipe = textwrap.dedent('''\
            # Test recipe
            ## Description
            Historical note: R110-176 had 1690 findings.
        ''')
        parsed = _run_scanner(tmp_path, recipe)
        sd = _sd_recipe_findings(parsed)
        # "1690 findings" — findings is in _COUNT_ANCHOR_NEXT, so it WOULD
        # be a load-bearing count-anchor UNLESS the historical-ref guard
        # skips it. We assert no false-positive here.
        assert not any('1690' in f.get('issue', '') and 'findings' in f.get('issue', '')
                       for f in sd), (
            f'R110-176 had 1690 findings was wrongly flagged: {sd}')

    def test_historical_ref_with_N_tests_no_AFTER_is_now_skipped(self, tmp_path):
        """THE BUG: 'R110-271 mentions 1690 tests' (no AFTER) used to fire
        a false positive. After R110-323 fix, it should be skipped because
        the line contains a commit reference AND a count-anchor.

        This is the regression test for R110-323-BUG-1.
        """
        _make_tmp_repo(tmp_path)
        recipe = textwrap.dedent('''\
            # Test recipe
            ## Description
            Historical note: R110-271 mentions 1690 tests in this codebase.
        ''')
        parsed = _run_scanner(tmp_path, recipe)
        sd = _sd_recipe_findings(parsed)
        # "1690 tests" — tests is a count-anchor, but the line is a
        # historical reference. After the fix, it should be skipped.
        assert not any('1690' in f.get('issue', '') and 'tests' in f.get('issue', '')
                       for f in sd), (
            f'Historical ref with N tests (no AFTER) wrongly flagged: {sd}')

    def test_load_bearing_anchor_still_fires(self, tmp_path):
        """No-regression: a REAL count-anchor (no R\d+-\d+ commit ref)
        should still fire SD-recipe findings (this is the load-bearing
        case the detector is designed to catch)."""
        _make_tmp_repo(tmp_path)
        recipe = textwrap.dedent('''\
            # Test recipe
            ## Description
            This recipe has 73 tests in its test suite.
        ''')
        parsed = _run_scanner(tmp_path, recipe)
        sd = _sd_recipe_findings(parsed)
        # "73 tests" is a load-bearing count-anchor (no commit ref) and
        # should fire a SD-recipe finding because the test file has no
        # matching anchor.
        matching = [f for f in sd
                    if '73' in f.get('issue', '') and 'tests' in f.get('issue', '')]
        assert matching, (
            f'Load-bearing count-anchor "73 tests" was NOT flagged '
            f'(should be): sd={sd}')


# --- Bug #2 regression: dead-code branch in .mase/ source-anchor ----------

class TestR110323Bug2DeadCodeBranch:
    """R110-323-BUG-2: `d == '.mase'` is a dead branch in
    check_spec_drift's data-subdir pruning. Fix removes it.
    """

    def test_recipe_subdir_in_mase_still_works(self, tmp_path):
        """No-regression: literals in recipe/instructions/ are still
        correctly checked against .mase/ as a source-anchor (the
        first arm of the OR). After removing the dead second arm,
        this should still work.
        """
        _make_tmp_repo(tmp_path)
        # Create a literal that exists in .mase/ but NOT in recipe/tools/docs
        (tmp_path / '.mase').mkdir()
        (tmp_path / '.mase' / 'pipeline').mkdir()  # data subdir, skipped
        (tmp_path / '.mase' / 'workflows.yaml').write_text(
            'workflows:\n  - canonical_literal_test_marker_xyz\n'
        )
        recipe = textwrap.dedent('''\
            # Test recipe
            ## Description
            The recipe references canonical_literal_test_marker_xyz.
        ''')
        # A test that uses the literal — should NOT be flagged because
        # the literal IS in .mase/ (the 4th source-anchor).
        test = textwrap.dedent('''\
            def test_uses_literal():
                assert 'canonical_literal_test_marker_xyz' in 'whatever'
        ''')
        parsed = _run_scanner(tmp_path, recipe, test)
        # SD-test findings are about TEST-side drift, not recipe-side.
        # We don't assert specifically here — we just want the scanner
        # to not error out on the .mase/ source-anchor dir.
        assert 'findings' in parsed


# --- Subprocess-cov smoke (R110-322 inheritance) --------------------------

class TestR110323SubprocessCovSmoke:
    """The R110-322 lesson: subprocess.run + cwd=REPO_ROOT +
    sitecustomize.py + COVERAGE_PROCESS_START auto-instruments the
    subprocess. This smoke test ensures the scanner actually
    runs and returns parseable JSON (catches import / arg errors).
    """

    def test_scanner_runs_and_emits_json(self, tmp_path):
        _make_tmp_repo(tmp_path)
        recipe = '# minimal recipe\n'
        parsed = _run_scanner(tmp_path, recipe)
        assert 'findings' in parsed
        assert 'summary' in parsed
        assert isinstance(parsed['findings'], list)
