"""R110-279: regression tests for the SD-test 'assert in runtime_var' skip-rule.

Background: pre-R110-279, the SD-test detector flagged 26 findings, all of
which were `assert "LITERAL" in <runtime_var>` patterns where the literal
is checked against captured output (capsys, file content, function return
values, parsed dicts). These are NOT static source-literal drift; they
test runtime behavior, which pytest already enforces. R110-279 adds
`_is_runtime_var_assert(line)` as a skip-rule, bringing SD-test findings
from 91 (R110-275) → 38 (R110-276) → 35 (R110-277) → 26 (R110-278) → 0
(R110-279). The 4 skip-rules in the chain are:
  - R110-271: identifier-style / fixture-path / module:function / dotted
  - R110-276: search-dir refinement (.mase as 4th source-anchor)
  - R110-277: short-comma-list / human-language skip
  - R110-278: skip .mase data-only subdirs (pipeline, workflow_runs, etc.)
  - R110-279: runtime-var assert skip (this rule)

These tests verify the new rule is correct: it should skip runtime-var
asserts AND NOT skip static-source-literal asserts.
"""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
sys.path.insert(0, TOOLS_DIR)
import dev_im_finder_scan as ds  # noqa: E402


# ---------- 1. RUNTIME-VAR ASSERTS (must be SKIPPED) ----------

RUNTIME_VAR_TEST_CASES = [
    # (line, expected_skip)
    # Captured stdout
    ('    assert "Total: 3 projecte" in out', True),
    ('    assert "Active project: alpha" in captured.out', True),
    # capsys.readouterr().out
    ('    captured = capsys.readouterr(); assert "warning message here" in captured.out', True),
    # function-returned content
    ('    content = file.read_text(); assert "literal pattern" in content', True),
    # subprocess result
    ('    result = subprocess.run(..., capture_output=True, text=True); assert "OK status" in result.stdout', True),
    # dict-lookup result
    ('    rules = load_rules(); assert "[BP-A-001]" in rules["bp_autonomie"]', True),
    # config / parsed / response
    ('    cfg = load_config(); assert "production" in cfg["env"]', True),
    # click/cli runner output
    ('    from click.testing import CliRunner; runner = CliRunner(); '
     'result = runner.invoke(cli, ["--help"]); assert "Usage:" in result.output', True),
    # intake
    ('    intake = gather(); assert "warning text" in intake', True),
    # stderr
    ('    assert "ERROR pattern" in stderr', True),
]


@pytest.mark.parametrize("line,expected_skip", RUNTIME_VAR_TEST_CASES)
def test_runtime_var_assert_is_skipped(line, expected_skip):
    """Lines asserting against a runtime value (out, result, content, etc.)
    are NOT static-source drift. The drift detector's purpose is to catch
    stale static literals, not runtime-behavior regressions (pytest
    enforces those). All these must be skipped (expected_skip=True).
    """
    assert ds._is_runtime_var_assert(line) is True, (
        f"_is_runtime_var_assert should skip runtime-var assert: {line!r}"
    )


# ---------- 2. STATIC-SOURCE-LITERAL ASSERTS (must NOT be skipped) ----------

STATIC_ASSERT_TEST_CASES = [
    # Asserting against a recipe/CLI arg
    '    assert "literal" in recipe_content',
    # Asserting against a hardcoded file path
    '    assert "literal" in path',
    # Asserting against a constant
    '    assert "literal" in CONST',
    # Asserting against a docstring/source fragment
    '    assert "literal" in doc',
    # Asserting against a string passed in as argument
    '    assert "literal" in arg',
]


@pytest.mark.parametrize("line", STATIC_ASSERT_TEST_CASES)
def test_static_source_assert_NOT_skipped(line):
    """Lines asserting against a non-runtime value (recipe_content, path,
    CONST, doc, arg) are POTENTIALLY drift and should NOT be skipped.
    The drift detector should at least reach the source-search step for
    these. (Some may still be skipped by R110-271 identifier rules if
    the literal is short, but the runtime-var skip must not fire.)
    """
    # The runtime-var check should not skip these
    assert ds._is_runtime_var_assert(line) is False, (
        f"_is_runtime_var_assert must NOT skip static-source assert: {line!r}"
    )


# ---------- 3. END-TO-END: detector finds drift when synth test is added ----------

def test_detector_finds_drift_for_synth_test(tmp_path, monkeypatch):
    """When a test file is added with an inline literal that is NOT in
    source AND is not asserted in a runtime-var context, the detector
    must flag it. This is the negative-space test that the R110-279
    skip-rule didn't accidentally suppress the detector's signal.
    """
    import subprocess
    # Use the existing test directory and write a new test
    test_path = os.path.join(REPO_ROOT, "tests", "test_zz_r110279_synth.py")
    # Build the literal via string concatenation so the detector's
    # string-extractor doesn't see it as a literal IN THIS file.
    # We further isolate it: the synth literal below is unique to
    # this test alone (it is NOT a substring of any other file,
    # including the docstring of this function — see R110-296).
    # _is_common_value() uses file-count > 1 to skip "common" values
    # so we must guarantee the literal appears in EXACTLY 1 source
    # location (the synth file) at scan-time.
    #
    # R110-279 original literal was 'ZOMBIEXYZ_FORTY_TWO_LITERAL_NOT_IN_ANY_SOURCE_R110279'
    # but it appeared in the docstring (Z.114), so _is_common_value
    # saw 2 file-matches (docstring + synth file) and skipped the
    # finding. R110-296 changed the literal to a unique value that
    # only appears in the synth file (no docstring, no other match).
    L1 = "R110296S" + "YNTH_LITERAL_ULTRA_UNIQUE_NO_OTHER_MATCH"
    synth_line = '    assert "' + L1 + '" in recipe'
    with open(test_path, "w") as f:
        f.write(f"def test_r110279_synth():\n{synth_line}\n")
    try:
        result = subprocess.run(
            ["python3", os.path.join(TOOLS_DIR, "dev_im_finder_scan.py")],
            capture_output=True, text=True, timeout=120,
        )
        # The detector must emit at least one SD-test finding for our synth
        assert L1 in result.stdout, (
            f"Detector should flag the synth literal but output:\n{result.stdout[-1000:]}"
        )
        # And the finding should reference the test file
        assert "test_zz_r110279_synth.py" in result.stdout
    finally:
        os.unlink(test_path)


# ---------- 4. END-TO-END: runtime-var assert is NOT flagged ----------

def test_detector_does_NOT_flag_runtime_var_assert(tmp_path):
    """When a test file asserts a literal against a runtime var, the
    detector must NOT flag it (R110-279 skip-rule). This is the
    positive-space test that the skip-rule works end-to-end.
    """
    import subprocess
    test_path = os.path.join(REPO_ROOT, "tests", "test_zz_r110279_runtime.py")
    with open(test_path, "w") as f:
        f.write(
            'def test_r110279_runtime():\n'
            '    captured = capsys.readouterr()\n'
            '    assert "ZOMBIEXYZ_FORTY_TWO_LITERAL_NOT_IN_ANY_SOURCE_R110279B" in captured.out\n'
        )
    try:
        result = subprocess.run(
            ["python3", os.path.join(TOOLS_DIR, "dev_im_finder_scan.py")],
            capture_output=True, text=True, timeout=120,
        )
        # The detector must NOT flag this literal (R110-279 skip)
        assert "ZOMBIEXYZ_FORTY_TWO_LITERAL_NOT_IN_ANY_SOURCE_R110279B" not in result.stdout, (
            f"Detector should NOT flag runtime-var assert but output:\n{result.stdout[-1000:]}"
        )
    finally:
        os.unlink(test_path)


# ---------- 5. INTEGRATION: no SD-test findings for the 26 known skip-cases ----------

def test_26_known_runtime_var_asserts_are_skipped():
    """The 26 SD-test findings pre-R110-279 were all runtime-var asserts.
    This test verifies the helper would skip each one — i.e. the
    skip-rule is correct across the full distribution of patterns.
    """
    KNOWN_RUNTIME_VAR_PATTERNS = [
        # 6 from test_r110265_template_generator.py
        '        assert "# a: 1" in result',
        '        assert "# b: hello" in result',
        '        assert "# x:" in result',
        '        assert "# y: 1" in result',
        '        assert "# z: 2" in result',
        '        assert "+15 mehr" in result',
        '        assert "Auto rule" in result',
        '        assert "[P-001]" in result',
        '        assert "[BP-A-001]" in rules["bp_autonomie"]',
        '        assert "LOG-ANALYZER" in result',
        # 7 from test_r110269_workspace_part2.py
        '        assert "Total: 3 projecte" in out',
        '        assert "Total: 1 projecte" in out',
        '        assert "Aktives project: alpha" in out',
        '        assert "project: alpha" in out',
        '        assert "Aktives project: alpha" in out',
        '        assert "Score: 100/100" in out',
        '        assert "5/5 bestanden" in out',
        # 1 from test_dev_evidence_sot.py
        '    assert "Anti-SOT evidence files EVER added: 1" in stdout',
        # 2 from test_r110261_tools_coverage_round2.py
        '    assert "Line 6" in content',
        '    assert "REPLACED\\n" in content',
        # 2 from test_r110261_tools_coverage_round3.py
        '        assert "⛔⛔⛔⛔⛔ NEVER do X" in intake',
        '        assert "Always do Y" in intake',
        # 3 from intentional SD-detector/recipe test files
        '    assert "ZOMBIE_LITERAL_XYZZY_FORTYTWO" in content, \\',
        '    assert "Content creation" in content or "content creation" in content.lower(), \\',
        '    assert "no direct file edits" in content or "no edits" in content, \\',
    ]
    for pattern in KNOWN_RUNTIME_VAR_PATTERNS:
        assert ds._is_runtime_var_assert(pattern) is True, (
            f"_is_runtime_var_assert must skip: {pattern!r}"
        )
