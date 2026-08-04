"""
test_sub_mas_self_auditor.py — sanity tests for self-auditor.

Self-auditor is the claim-vs-evidence consistency check (R100+).
Prevents "verification theater" by flagging overclaims without
matching test logs. Has 4 sub-agents (architecture split).

Run with:
    python3 -m pytest tests/test_sub_mas_self_auditor.py -v
"""
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE = REPO_ROOT / "recipe" / "sub" / "sub_mas-self-auditor.yaml"
INSTRUCTIONS = REPO_ROOT / "recipe" / "instructions" / "sub_mas-self-auditor.md"


def test_self_auditor_recipe_exists():
    assert RECIPE.exists(), f"Missing: {RECIPE}"


def test_self_auditor_recipe_is_valid_yaml():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_self_auditor_recipe_has_required_fields():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    for field in ("name", "version", "prompt", "settings", "instructions"):
        assert field in data, f"Missing required field: {field}"


def test_self_auditor_references_master_constitution():
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    assert data.get("constitution") == "sub_mas-master-constitution.yaml"


def test_self_auditor_instructions_exist():
    assert INSTRUCTIONS.exists(), f"Missing: {INSTRUCTIONS}"


def test_self_auditor_architecture_split():
    """Spec: orchestrator + 4 sub-agents."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    arch = data.get("architecture_split", "")
    assert "sub-agents" in arch or "4" in arch, \
        f"self-auditor must declare architecture_split, got: {arch[:100]}"


def test_self_auditor_4_subagents():
    """Spec: validator, evidence-scanner, report-builder, claim-matcher."""
    content = RECIPE.read_text()
    assert "4 sub-agents" in content, \
        "self-auditor must declare 4 sub-agents (architecture_split)"
    for sub in ("validator", "evidence-scanner", "report-builder", "claim-matcher"):
        assert sub in content, \
            f"self-auditor must declare sub-agent: {sub}"


def test_self_auditor_prohibition_boundary():
    """Spec: AUDIT-ONLY — never modifies files, never edits docs, never
    pushes, never executes shell. Reads via load tool only."""
    content = INSTRUCTIONS.read_text()
    # The rule is "AUDIT-ONLY" with declarative consequences, not
    # "NEVER modify" imperative
    assert "AUDIT-ONLY" in content, \
        "self-auditor must declare AUDIT-ONLY rule"
    assert "never modifies" in content or "never edits" in content, \
        "self-auditor must declare never-modifies/never-edits consequences"
    assert "never pushes" in content or "no shell" in content or \
           "no shell/write" in content, \
        "self-auditor must declare no-shell/no-push consequences"


def test_self_auditor_external_instructions_ref():
    """Recipe must reference the external instructions file (R37)."""
    content = RECIPE.read_text()
    assert "sub_mas-self-auditor.md" in content, \
        "Recipe must reference external instructions file (R37)"


def test_self_auditor_uses_deepseek():
    """R36+: cost-control via deepseek-v4-flash."""
    with open(RECIPE) as f:
        data = yaml.safe_load(f)
    model = data.get("settings", {}).get("goose_model", "")
    assert "deepseek" in model, \
        f"self-auditor should use deepseek (R36+), got: {model}"


def test_pattern_b_stale_literal_detected():
    """R110-121: Pattern B detects stale references."""
    import sys

    # R110-120 adaptation (same pattern as test_step_0_6): import tools
    # modules via TOOLS sys.path entry — a site-packages 'tools' package
    # would shadow the repo tools/ dir.
    TOOLS = REPO_ROOT / "tools"
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))

    from dev_self_audit import run_self_audit  # noqa: E402

    result = run_self_audit(
        scope=REPO_ROOT / "recipe" / "instructions",
        repo_root=REPO_ROOT,
    )
    # R110-121 adaptation: Finding field is `code`, not `type` (directive
    # draft used f.type — Finding has no type attribute; file:line info is
    # embedded in f.description, see tools/dev_self_audit.py).
    stale_findings = [f for f in result.findings
                      if 'STALE-LITERAL' in f.code]
    # After R110-121 DIREKTIVE 1: should be 0 stale
    # (sales replaced, im-finder false positive fixed)
    assert len(stale_findings) == 0, \
        f"Stale findings remain: {[f.description for f in stale_findings]}"
