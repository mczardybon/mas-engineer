"""
test_pre_push_check_18_spec_invariant.py — DIREKTIVE 3 (R110-118).

Check 18 (pre-push-validator v2.4.0) runs tools/dev_spec_invariant.py:
test count-assertions (pattern: assert, then a quoted "count type"
literal, then "in") MUST match the recipe count-declarations
(recipe/sub/*.yaml string scalars). Closes R110-78 PHASE 3
(R110-109 DIREKTIVE 2+3).

3 test-cases:
  (a) match passes
  (b) mismatch emits BLOCKER finding
  (c) recipe/sub/*.yaml excluded when empty

NOTE: fixture literals are built with f-strings (not literal
'assert "N type" in ...' lines) so this test file does not pollute the
real-repo invariant scan of tests/.

Run with:
    python3 -m pytest tests/test_pre_push_check_18_spec_invariant.py -v
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from dev_spec_invariant import (  # noqa: E402
    extract_count_assertions_from_tests,
    extract_count_from_recipes,
    run_spec_invariant_check,
)


def _write_fixture(tmp_path, recipe_text, test_text):
    """Create a fake repo: recipe/sub/*.yaml + tests/test_*.py."""
    recipe_dir = tmp_path / "recipe" / "sub"
    tests_dir = tmp_path / "tests"
    recipe_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    (recipe_dir / "sub_mas-fake.yaml").write_text(recipe_text)
    (tests_dir / "test_fake.py").write_text(test_text)
    return tmp_path


def _fake_assertion(count, typ):
    """Build a fixture test line `assert "N type" in content`.

    The 'assert' keyword is assembled at runtime so this source file
    itself never contains the assert-quote pattern — keeping the
    real-repo SD/spec-invariant scans free of fixture noise.
    """
    kw = "assert"
    return f'{kw} "{count} {typ}" in content\n'


def test_check18_match_passes(tmp_path):
    """(a) matching test-assert and recipe-declaration -> no finding."""
    count, typ = 110, "sub-agents"
    fake_test = _fake_assertion(count, typ)
    fake_recipe = f"description: 'all {count} {typ} in distribution'\n"
    repo = _write_fixture(tmp_path, fake_recipe, fake_test)

    ta = extract_count_assertions_from_tests(repo / "tests")
    rc = extract_count_from_recipes(repo / "recipe" / "sub")
    assert ta == {"sub-agents": {110}}, ta
    assert rc == {"sub-agents": {110}}, rc

    res = run_spec_invariant_check(repo)
    assert res.to_findings() == []


def test_check18_mismatch_emits_blocker(tmp_path):
    """(b) test asserts 110 sub-agents but recipe declares 96 -> BLOCKER."""
    n_test, n_recipe = 110, 96
    fake_test = _fake_assertion(n_test, "sub-agents")
    fake_recipe = f"description: 'creates distribution with {n_recipe} sub-agents'\n"
    repo = _write_fixture(tmp_path, fake_recipe, fake_test)

    res = run_spec_invariant_check(repo)
    findings = res.to_findings()
    assert len(findings) == 1
    f = findings[0]
    assert f.code == "INVARIANT-sub-agents"
    assert f.severity == "BLOCKER"
    assert "110" in f.description and "96" in f.description


def test_check18_empty_recipe_excluded(tmp_path):
    """(c) empty/comment-only recipe/sub yaml contributes no counts."""
    count, typ = 17, "checks"
    fake_test = _fake_assertion(count, typ)
    fake_recipe = "# no declarations here\n"
    repo = _write_fixture(tmp_path, fake_recipe, fake_test)

    rc = extract_count_from_recipes(repo / "recipe" / "sub")
    # the empty recipe file is excluded: no crash, zero false counts
    assert rc == {}

    res = run_spec_invariant_check(repo)
    findings = res.to_findings()
    # only the missing-recipe-declaration drift is reported, and the
    # empty file itself contributed nothing
    assert all(f.code == "INVARIANT-checks" for f in findings)
    assert all(f.severity == "BLOCKER" for f in findings)
