"""
test_dev_spec_invariant.py — R110-206 regression tests for the Check 18
scope extension in tools/dev_spec_invariant.py.

R110-118 (DIREKTIVE 2) implemented Check 18 over test count-assertions
vs recipe count-declarations.  R110-206 closes the F-082 scope gap:
test MODULE-DOCSTRINGS and recipe/instructions/*.md prose are now ALSO
cross-checked against the recipe counts for count-declaration types
(checks/check/critical), with diverging files named in the finding.

NOTE (fixture hygiene): this file's OWN module docstring deliberately
contains NO "N checks" / "N critical" literals — otherwise the real-repo
invariant scan would flag this test file itself.  Fixture literals are
assembled at runtime via f-strings (same technique as
tests/test_pre_push_check_18_spec_invariant.py).

4 test-cases:
  (a) extract_count_from_instructions on a synthetic instructions file
  (b) extract_count_from_docstrings on a synthetic module docstring
  (c) run_spec_invariant_check emits INVARIANT-checks BLOCKER when
      instructions prose contradicts the recipe declaration
  (d) idempotency: a second run returns the same finding set

Run with:
    python3 -m pytest tests/test_dev_spec_invariant.py -v
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from dev_spec_invariant import (  # noqa: E402
    extract_count_from_docstrings,
    extract_count_from_instructions,
    run_spec_invariant_check,
)


def _make_repo(tmp_path, recipe_text=None, instructions_text=None):
    """Build a mini repo: recipe/sub/*.yaml + recipe/instructions/*.md."""
    sub_dir = tmp_path / "recipe" / "sub"
    sub_dir.mkdir(parents=True)
    if recipe_text is not None:
        (sub_dir / "sub_mas-fake.yaml").write_text(recipe_text)
    if instructions_text is not None:
        instr_dir = tmp_path / "recipe" / "instructions"
        instr_dir.mkdir(parents=True)
        (instr_dir / "instructions_with_checks.md").write_text(
            instructions_text)
    return tmp_path


def test_extract_count_from_instructions(tmp_path):
    """(a) single-line prose 'N checks' -> {'checks': {3}}."""
    n = 3
    md = (
        "The pipeline runs a checklist.\n"
        f"Checklist summary: all {n} checks completed today.\n"
        f"Follow-up: {n} checks re-run nightly.\n"
    )
    repo = _make_repo(tmp_path, instructions_text=md)
    got = extract_count_from_instructions(repo / "recipe" / "instructions")
    assert got == {"checks": {n}}, got


def test_extract_count_from_docstrings(tmp_path):
    """(b) module-level docstring '22 critical checks' -> {'critical': {22}}."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    n = 22
    (tests_dir / "test_fake.py").write_text(
        '"""\n' 
        f"Test module declaring {n} critical checks.\n"
        '"""\n'
        "def test_nothing():\n    pass\n"
    )
    got = extract_count_from_docstrings(tests_dir)
    assert got == {"critical": {n}}, got


def test_instructions_recipe_mismatch_emits_blocker(tmp_path):
    """(c) instructions '21 checks' vs recipe '22 checks' -> BLOCKER."""
    n_instr, n_recipe = 21, 22
    recipe = f"description: 'runs all {n_recipe} checks in order'\n"
    md = f"The validator runs {n_instr} checks before push.\n"
    repo = _make_repo(tmp_path, recipe_text=recipe, instructions_text=md)

    res = run_spec_invariant_check(repo)
    findings = res.to_findings()
    assert len(findings) == 1, findings
    f = findings[0]
    assert f.code == "INVARIANT-checks"
    assert f.severity == "BLOCKER"
    assert str(n_instr) in f.description
    assert str(n_recipe) in f.description
    assert "instructions_with_checks.md" in f.files


def test_run_is_idempotent(tmp_path):
    """(d) second run on the same repo -> same finding set (no dupes)."""
    n_instr, n_recipe = 21, 22
    recipe = f"description: 'runs all {n_recipe} checks in order'\n"
    md = f"The validator runs {n_instr} checks before push.\n"
    repo = _make_repo(tmp_path, recipe_text=recipe, instructions_text=md)

    first = run_spec_invariant_check(repo).to_findings()
    second = run_spec_invariant_check(repo).to_findings()
    assert [(f.code, f.severity, f.description, tuple(f.files))
            for f in first] == \
           [(f.code, f.severity, f.description, tuple(f.files))
            for f in second]
