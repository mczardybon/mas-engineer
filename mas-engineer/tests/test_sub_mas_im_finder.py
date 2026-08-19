"""
test_sub_mas_im_finder.py — sanity tests for im-finder (Stage 1).

IM-Finder detects optimization potential (37→53 Feature Types). It's
Stage 1 of the FIND→RANK→DESIGN→... pipeline (R36+).

Run with:
    python3 -m pytest tests/test_sub_mas_im_finder.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-im-finder.yaml"


def test_im_finder_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_im_finder_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_im_finder_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    # im-finder uses prompt-field instead of instructions-field (compact recipe)
    for field in ("name", "version", "prompt", "settings"):
        assert field in data, f"Missing required field: {field}"


def test_im_finder_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_im_finder_is_stage_1():
    """IM-Finder is Stage 1 of the pipeline (R36+)."""
    content = RECIPE.read_text()
    assert "Stage 1" in content or "FINDER" in content, \
        "IM-Finder must be Stage 1 (R36)"


def test_im_finder_summons_goose_expert():
    """R11: must summon sub_mas-goose-expert for goose-related findings."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    subs = [s.get("name") for s in data.get("sub_recipes", [])]
    assert "sub_mas-goose-expert" in subs, \
        f"im-finder must summon sub_mas-goose-expert (R11). sub_recipes: {subs}"


def test_im_finder_no_direct_file_edits():
    """im-finder writes findings.yaml only, doesn't edit recipe code."""
    content = RECIPE.read_text()
    assert "no direct file edits" in content or "no direct edits" in content or \
           "ANALYSIS + DELEGATION" in content, \
        "im-finder must declare no-direct-edits rule (writes findings.yaml only)"


def test_im_finder_writes_findings_yaml():
    """Output: findings.yaml with attached goose_verdicts."""
    content = RECIPE.read_text()
    assert "findings.yaml" in content, \
        "im-finder must write findings.yaml output"


def test_im_finder_timeout_appropriate():
    """Stage 1 analysis — long timeout OK."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    timeout = data.get("settings", {}).get("timeout", 0)
    assert timeout >= 300, \
        f"im-finder timeout should be >= 300s for full analysis, got {timeout}"


def test_im_finder_mentions_feature_types():
    """R36+: detects optimization potential across multiple feature types."""
    content = RECIPE.read_text()
    # Either "Feature Types" or "feature_type" or similar
    assert "Feature" in content or "feature" in content, \
        "im-finder must mention feature-type coverage (R36+)"


def test_step_0_6_self_audit_attaches_mm9_ext():
    """R110-120: STEP 0.6 wires sub_mas-self-audit as MM9-EXT findings."""
    # 1. Run self-audit
    import sys

    # R110-120 adaptation: import tools modules via TOOLS sys.path entry
    # (site-packages 'tools' package would shadow the repo tools/ dir —
    # same pattern as test_pre_push_check_18_spec_invariant.py).
    TOOLS = REPO_ROOT / "tools"
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))

    from dev_self_audit import run_self_audit  # noqa: E402

    result = run_self_audit(
        scope=REPO_ROOT / "recipe" / "instructions",
        repo_root=REPO_ROOT,
    )
    # 2. Verify findings list is non-empty
    assert len(result.findings) > 0, "self-audit should find drift"
    # 3. Verify all are WARN (not BLOCKER, since R110-119 fixed them)
    severities = {f.severity for f in result.findings}
    assert 'BLOCKER' not in severities, \
        f"BLOCKER found after R110-119: {severities}"
    # 4. Verify codes are HARDCODE-*/INVARIANT-* (STEP 0.6 MM9-EXT sources)
    #    R110-120 adaptation: Finding field is `code` (directive draft
    #    used `type`). INVARIANT codes are legitimately absent — the
    #    delegated dev_spec_invariant scan is clean after R110-119.
    codes = {f.code for f in result.findings}
    assert any(c.startswith('HARDCODE') for c in codes), \
        f"expected HARDCODE findings, got: {sorted(codes)}"


# --- R110-124: scanner Pattern A + B (MM9-EXT support) --------------------
def test_scanner_detects_hardcode_stale(tmp_path):
    """R110-124: scanner emits HARDCODE-STALE-* findings (Pattern A).

    R110-209-ADAPTATION (honest, R110-78 lesson): the real repo currently
    has 0 hardcode-stale findings (R110-209 fixed F-082 + added
    HTML-comment/historical-marker detection in
    tools/dev_im_finder_scan.py:1137-1176, commit 766b501). The
    directive's e2e assertion (>=1 HARDCODE-STALE-* on the real repo)
    is therefore not satisfiable post-fix. Instead we prove the wiring
    on a synthetic repo: an instruction file with an uncontextualized
    "N sub-agents" / "N tools" / "N checks" literal (no historical
    marker, no env-var, no HTML-comment) must still be emitted as
    HARDCODE-STALE-*.
    """
    import subprocess
    import json
    # Synthetic repo: one instruction file with a hardcoded count that
    # has NO historical marker, NO env-var context, NO HTML-comment.
    # The scanner's HTML-comment/historical-context filters in
    # dev_im_finder_scan.py:1137-1176 must NOT suppress this.
    instr = tmp_path / "recipe" / "instructions"
    instr.mkdir(parents=True)
    (instr / "sub_mas-synthetic.md").write_text(
        "This is a synthetic instruction with 99 sub-agents and 42 tools "
        "that have no context whatsoever.\n"
    )
    result = subprocess.run(
        ['python3', str(REPO_ROOT / 'tools' / 'dev_im_finder_scan.py'),
         f'--scope={tmp_path}/recipe/instructions/'],
        capture_output=True, text=True, cwd=str(tmp_path))
    out = result.stdout
    assert '---JSON_START---' in out
    j = out.split('---JSON_START---')[1]
    data = json.loads(j)
    types = {f['type'] for f in data['findings']}
    hardcode_findings = [t for t in types if t.startswith('HARDCODE-STALE')]
    assert len(hardcode_findings) >= 1, \
        f"scanner should emit >=1 HARDCODE-STALE-* finding, got: {types}"


def test_scanner_detects_stale_literal(tmp_path):
    """R110-124: scanner emits STALE-LITERAL-* findings (Pattern B).

    R110-124-ADAPTATION (honest, R110-116): the real repo currently has
    0 stale literals (R110-121 fixed all 6; dev_self_audit pre-condition
    "20 WARN, 0 STALE-LITERAL"). The directive's e2e assertion (>=1
    STALE-LITERAL-* on the real repo) is therefore not satisfiable.
    Instead we prove the wiring on a synthetic repo: a path-like
    literal that appears only in recipe/instructions/ (and nowhere else
    in recipe/tools/docs/tests) must be emitted as STALE-LITERAL-*.

    R110-124-ADAPTATION 2 (R110-116): the directive's draft fixture used
    a quoted numeric count-anchor (forty-two checks). Quoted
    "N checks" literals in test source pollute test_combined and trip
    the reverse spec-drift check (R110-111 L26: recipe "18 checks" vs
    test anchor mismatch => spurious BLOCKER). The fixture literal is
    therefore a digit-free path (still matches Pattern B's
    _B_PATH_LIKE_RE), which cannot match _RECIPE_NUMERIC_RE.
    """
    import subprocess
    import json
    # Synthetic repo: one instruction file with an unmatched path literal
    instr = tmp_path / "recipe" / "instructions"
    instr.mkdir(parents=True)
    (instr / "sub_mas-synthetic.md").write_text(
        "Use 'tools/sub_mas-stale-literal-sentinel.py' as canonical path.\n")
    result = subprocess.run(
        ['python3', str(REPO_ROOT / 'tools' / 'dev_im_finder_scan.py'),
         f'--scope={tmp_path}/recipe/instructions/'],
        capture_output=True, text=True, cwd=str(tmp_path))
    out = result.stdout
    assert '---JSON_START---' in out
    j = out.split('---JSON_START---')[1]
    data = json.loads(j)
    types = {f['type'] for f in data['findings']}
    stale_findings = [t for t in types if t.startswith('STALE-LITERAL')]
    assert len(stale_findings) >= 1, \
        f"scanner should emit >=1 STALE-LITERAL-* finding, got: {types}"
