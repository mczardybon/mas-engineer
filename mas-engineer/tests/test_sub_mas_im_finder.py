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
