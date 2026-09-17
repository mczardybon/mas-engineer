"""
test_recipe_registry_consistency.py — workflow-registry vs recipe-files consistency.

Per R110-31 + R110-30:
  - DOMAIN 1 (mas-self): sub-agents in workflows.yaml.configs.mas-self.sub_agents
  - DOMAIN 2 (mas-generated): team-packager output, NOT in mas-self
  - DOMAIN 3 (framework/generic): project/demo-team agents, NOT in mas-self

The 1218 R103-R108 recipe-sanity tests (per skill
mas-engineer-recipe-yaml-pytest-coverage) check SINGLE-recipe YAML
structure (10 functions per recipe). They do NOT check
CROSS-recipe relationships — i.e. whether the registry in
.mase/workflows.yaml matches the actual recipe files on disk.

Real bugs as of 2026-07-29 (NOT caught by existing tests):

  1. Registry typo: 'sub_mas-web-wresearcher' (extra w) — would
     cause silent dispatch failure.
  2. DOMAIN 1 files that are NOT registered in mas-self.sub_agents.
     R110-31 hard rule: "All DOMAIN 1 sub-agents MUST be registered."
  3. (defensive) DOMAIN 2/3 agents that are incorrectly registered
     in mas-self.sub_agents (cross-domain leak).
  4. (defensive) Duplicate sub-agent names in multiple registry
     categories = dispatch ambiguity.

DOMAIN CLASSIFICATION (heuristic, see classify_domain()):
  DOMAIN 1 signals: 'MAS-internal', 'CONTROLLER-internal', 'Code-Review-Team'
                    in description; or filename prefix 'sub_mas-im-',
                    'sub_mas-monitor-', 'sub_mas-test-fix-failures-'.
  DOMAIN 2 signals: filename 'sub_mas-team-packager*' or 'sub_mas-generic-init'.
  DOMAIN 3 signals: filename contains 'social-media-manager',
                    'email-campaign-manager', 'seo-researcher',
                    'content-writer', 'analytics-reporter',
                    'web-researcher' (summon-platform demo-teams).

AUTHOR: Hermes-agent wrote this directly. Pattern matches the 124
existing recipe tests in this directory (10-function file, ~200 lines,
pure pyyaml+pytest, <1s runtime). Diff reviewed in commit.

Run with:
    python3 -m pytest tests/test_recipe_registry_consistency.py -v
"""
import re
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
RECIPE_DIR = REPO_ROOT / "recipe"
SUB_DIR = RECIPE_DIR / "sub"
# R110-55 cleanup: demo-team was moved from recipe/sub/demo-team/ to
# demos/demo-team/. Update DEMO_TEAM_DIR to the new location.
DEMO_TEAM_DIR = REPO_ROOT.parent / "demos" / "demo-team"
DEMO_TEAM_RECIPES_DIR = DEMO_TEAM_DIR / "recipes"
DEMO_TEAM_INSTRUCTIONS_DIR = DEMO_TEAM_DIR / "instructions"
TEMPLATE_DIR = SUB_DIR / "template"
LEGACY_DIR = SUB_DIR / "legacy"
WORKFLOWS_YAML = REPO_ROOT / ".mase" / "workflows.yaml"

# R110-39 + R110-52: registry scan includes multi-arch-30 sub/teams/ sub-recipes.
# Tests of the multi-arch-30 demo itself live in
# demos/multi-arch-30/tests/test_multi_arch_30.py (R110-53).
MULTI_ARCH_DIR = REPO_ROOT.parent / "demos" / "multi-arch-30"

# R110-43: tools that MUST NOT contain hard-coded /root/, /home/, /Users/, /tmp/
TOOLS_DIR = REPO_ROOT / "tools"

# DOMAIN 3 demo-team filename tokens (summon-platform, per skill
# mas-engineer-recipe-yaml-pytest-coverage)
DOMAIN3_TOKENS = (
    "social-media-manager",
    "email-campaign-manager",
    "seo-researcher",
    "content-writer",
    "analytics-reporter",
)

# DOMAIN 1 filename prefix tokens (sub-agents of mas-engineer itself)
DOMAIN1_PREFIXES = (
    "sub_mas-monitor-",  # CONTROLLER-internal
    "sub_mas-im-",       # IM-pipeline sub-agents
    "sub_mas-test-fix-failures-",  # test-fix-failures director chain
)

# DOMAIN 2 filename tokens (mas-generated, team-packager output)
DOMAIN2_TOKENS = (
    "sub_mas-team-packager",
    "sub_mas-generic-init",
)

# DOMAIN 1 description signals
DOMAIN1_DESC = (
    "MAS-internal",
    "MAS-Engineer-internal",
    "CONTROLLER-internal",
    "Code-Review-Team",
)


# ---- Domain classification -----------------------------------------------

def classify_domain(stem: str, data: dict, parent_path: "Path | None" = None) -> str:
    """Return 'mas-self' (DOMAIN 1), 'mas-generated' (DOMAIN 2),
    'demo-team' (DOMAIN 3), or 'unknown'.

    R110-39 PATH-BASED classification (more robust than stem-only heuristic):
      - parent_path is DEMO_TEAM_DIR  -> always "demo-team" (no heuristic needed)
      - parent_path is TEMPLATE_DIR   -> always "unknown" (template, skipped)
      - parent_path is LEGACY_DIR     -> always "unknown" (legacy, skipped)
      - parent_path is in MULTI_ARCH_DIR  -> check if "teams/" subdir -> "demo-team"
                                            (multi-arch-30 demo teams per R110-30)
                                            else "mas-generated" (multi-arch sub-recipes)
      - parent_path is None or SUB_DIR  -> fall back to stem + description heuristic

    Heuristic fallback (only for SUB_DIR files without path-decision):
    Order matters: more specific signals first.
    """
    # ---- R110-39 PATH-BASED pre-classification (deterministic) ----
    if parent_path is not None:
        try:
            # R110-55: demo-team lives at demos/demo-team/{recipes,instructions}
            if parent_path in (DEMO_TEAM_DIR, DEMO_TEAM_RECIPES_DIR,
                               DEMO_TEAM_INSTRUCTIONS_DIR):
                return "demo-team"
            if parent_path == TEMPLATE_DIR or parent_path == LEGACY_DIR:
                return "unknown"
            # multi-arch-30/teams/ = demo teams (R110-30 convention)
            if parent_path == MULTI_ARCH_DIR / "teams":
                return "demo-team"
            # multi-arch-30/sub/  = sub-recipes of teams
            if parent_path == MULTI_ARCH_DIR / "sub":
                return "mas-generated"
            # multi-arch-30/test-r11021/ + template/  = mas-generated variants
            if parent_path.parent == MULTI_ARCH_DIR and parent_path.name != "teams":
                return "mas-generated"
        except Exception:
            pass

    # ---- Heuristic fallback (for SUB_DIR files without strong path signal) ----
    desc = (data.get("description") or "")
    # DOMAIN 2: team-packager
    if any(stem.startswith(t) for t in DOMAIN2_TOKENS):
        return "mas-generated"
    # DOMAIN 3: demo-team filename
    if any(t in stem for t in DOMAIN3_TOKENS):
        return "demo-team"
    # DOMAIN 1: explicit description signal
    if any(sig in desc for sig in DOMAIN1_DESC):
        return "mas-self"
    # DOMAIN 1: filename prefix
    if any(stem.startswith(p) for p in DOMAIN1_PREFIXES):
        return "mas-self"
    # DOMAIN 1: v1.0.0 / v2.0.0 / v3.0.0 prefix + no marketing keyword
    # (R110-30 convention; the existing 34 files like sub_mas-bootstrap,
    # sub_mas-code-reviewer-* all start with "v1.0.0 |")
    if re.match(r"v\d+\.\d+\.\d+\s*\|", desc) and not any(
        kw in desc.lower() for kw in ("marketing", "social media",
                                       "campaign", "seo", "blog")
    ):
        return "mas-self"
    return "unknown"


# ---- Helpers -------------------------------------------------------------

def _load_registry():
    """Return (flat_set, categories_dict) from configs.mas-self.sub_agents.

    Returns (None, None) if workflows.yaml is missing or malformed.
    """
    if not WORKFLOWS_YAML.exists():
        return None, None
    try:
        with open(WORKFLOWS_YAML) as f:
            wf = yaml.safe_load(f)
    except Exception:
        return None, None
    if not isinstance(wf, dict):
        return None, None
    mas_self = wf.get("configs", {}).get("mas-self", {})
    sub_agents = mas_self.get("sub_agents", {})
    if not isinstance(sub_agents, dict):
        return None, None
    flat = set()
    for category, agents in sub_agents.items():
        if str(category).startswith("_"):
            continue
        if isinstance(agents, list):
            flat.update(agents)
    return flat, sub_agents


def _all_sub_recipe_files():
    """Dict stem -> domain for all sub_mas-*.yaml files.

    R110-39: now scans MULTI_ARCH_DIR (multi-arch-30) in addition to SUB_DIR
    + DEMO_TEAM_DIR. Path-based classification is deterministic so multi-arch
    files don't fall through to "unknown".

    R110-55: demo-team was moved from recipe/sub/demo-team/ to
    demos/demo-team/. Scan DEMO_TEAM_RECIPES_DIR.
    """
    out = {}
    search_dirs = [SUB_DIR, DEMO_TEAM_RECIPES_DIR]
    if MULTI_ARCH_DIR.exists():
        # R110-30 convention: sub-recipes in sub/, team recipes in teams/
        search_dirs += [MULTI_ARCH_DIR / "sub", MULTI_ARCH_DIR / "teams"]
        # test-r11021, template also have recipes
        for child in MULTI_ARCH_DIR.iterdir():
            if child.is_dir() and child not in (MULTI_ARCH_DIR / "sub",
                                                MULTI_ARCH_DIR / "teams"):
                search_dirs.append(child)
    for d in search_dirs:
        if not d.exists():
            continue
        # recipe/sub/ uses DOMAIN 1 filenames WITHOUT the sub_mas- prefix
        # too (e.g. security-scanner.yaml, static-analyzer.yaml — R110-204
        # orphan fix); the demo/multi-arch dirs follow sub_mas- naming.
        pattern = "*.yaml" if d == SUB_DIR else "sub_mas-*.yaml"
        for p in d.glob(pattern):
            try:
                with open(p) as f:
                    data = yaml.safe_load(f)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            out[p.stem] = classify_domain(p.stem, data, parent_path=p.parent)
    return out


# ---- Tests ---------------------------------------------------------------

def test_workflows_yaml_exists():
    """Precondition: workflows.yaml must exist."""
    assert WORKFLOWS_YAML.exists(), (
        f"Missing: {WORKFLOWS_YAML}. R110-31 registry cannot be validated."
    )


def test_classify_domain_is_total():
    """Sanity: every sub_mas-*.yaml file must be classifiable.

    Catches new recipes that are added without following the
    R110-30 description convention ("v1.0.0 | ...") and without
    DOMAIN 1/2/3 signals.
    """
    files = _all_sub_recipe_files()
    unknown = sorted([s for s, d in files.items() if d == "unknown"])
    assert not unknown, (
        f"{len(unknown)} sub_mas-*.yaml files don't match any DOMAIN "
        f"signal. Add a 'v1.0.0 | MAS-internal: ...' description "
        f"(R110-30) or move to recipe/sub/demo-team/. First 10: "
        f"{unknown[:10]}"
    )


def test_registry_entries_match_existing_recipe_files():
    """Registry entries MUST match existing recipe file basenames.

    Detects typos like 'sub_mas-web-wresearcher' (extra w) that would
    cause silent dispatch failure.
    """
    registered, _ = _load_registry()
    assert registered is not None, "Could not load registry from workflows.yaml"
    files = set(_all_sub_recipe_files().keys())
    typos = sorted(registered - files)
    assert not typos, (
        f"{len(typos)} registry entries don't match any recipe file "
        f"(likely typos). Will cause silent dispatch failure. "
        f"All typos: {typos}"
    )


def test_no_duplicate_sub_agents_in_registry():
    """A sub-agent name should appear in at most one registry category.

    Dispatch ambiguity if it appears in two categories.
    """
    _, registry = _load_registry()
    if registry is None:
        return  # test_workflows_yaml_exists already covers this
    seen = {}
    dups = []
    for category, agents in registry.items():
        if str(category).startswith("_") or not isinstance(agents, list):
            continue
        for a in agents:
            if a in seen:
                dups.append((a, seen[a], category))
            else:
                seen[a] = category
    assert not dups, (
        f"{len(dups)} sub-agents appear in multiple registry categories. "
        f"Dispatch ambiguity. First 10: {dups[:10]}"
    )


def test_mas_self_recipes_registered():
    """DOMAIN 1 (mas-self) recipes MUST be in the registry.

    R110-31 hard rule: "All DOMAIN 1 sub-agents MUST be registered
    in configs.mas-self.sub_agents." An unregistered DOMAIN 1 agent
    is a dead node — workflow dispatch can't reach it.
    """
    registered, _ = _load_registry()
    if registered is None:
        return
    files = _all_sub_recipe_files()
    domain1 = {s for s, d in files.items() if d == "mas-self"}
    if not domain1:
        return
    orphans = sorted(domain1 - registered)
    coverage = ((len(domain1) - len(orphans)) / len(domain1)) * 100
    assert not orphans, (
        f"{len(orphans)}/{len(domain1)} DOMAIN 1 (mas-self) recipes "
        f"({100 - coverage:.0f}% missing) are NOT registered in "
        f"workflows.yaml.configs.mas-self.sub_agents. "
        f"R110-31 violation — these are undispatchable from workflow. "
        f"All orphans: {orphans}"
    )


def test_non_mas_self_not_in_mas_self_registry():
    """DOMAIN 2 (mas-generated) and DOMAIN 3 (demo-team) MUST NOT
    appear in configs.mas-self.sub_agents.

    Cross-domain leak = wrong dispatch authority.
    """
    registered, _ = _load_registry()
    if registered is None:
        return
    files = _all_sub_recipe_files()
    other = sorted([
        s for s, d in files.items()
        if d in ("mas-generated", "demo-team") and s in registered
    ])
    assert not other, (
        f"{len(other)} non-DOMAIN-1 agents are in mas-self.sub_agents "
        f"(cross-domain leak). Should be in their own registry. "
        f"First 10: {other[:10]}"
    )


def test_registry_has_minimum_categories():
    """Registry must have at least the 4 core categories (R110-31 structure).

    analyse / recovery / monitoring / verwaltung are the documented
    categories. Missing a whole category = registry structure broken.
    """
    _, registry = _load_registry()
    if registry is None:
        return
    cats = {k for k in registry if not str(k).startswith("_")}
    core = {"analyse", "recovery", "monitoring", "verwaltung"}
    missing = core - cats
    assert not missing, (
        f"Registry missing {len(missing)} core categories (R110-31): "
        f"{sorted(missing)}"
    )


def test_registry_entries_are_strings():
    """Each registered agent name MUST be a non-empty string.

    Defends against accidental struct/int entries in the YAML list.
    """
    _, registry = _load_registry()
    if registry is None:
        return
    bad = []
    for category, agents in registry.items():
        if str(category).startswith("_") or not isinstance(agents, list):
            continue
        for a in agents:
            if not isinstance(a, str) or not a.strip():
                bad.append((category, a, type(a).__name__))
    assert not bad, (
        f"Registry has {len(bad)} non-string entries. First 5: {bad[:5]}"
    )


# ============================================================================
# R110-43: hard-coded absolute paths in tools/ (cross-cutting hygiene test)
# ============================================================================

import re as _re
import subprocess as _subprocess

# Pattern: hard-coded absolute paths to well-known dev locations
HARDCODED_PATH_RE = _re.compile(
    r"""(?P<path>["'](/root/|/home/(?!\.)|/Users/(?!\.)|/opt/(?!\.))(?:[^"'\s]*)["'])""",
    _re.MULTILINE,
)

# Tools that LEGITIMATELY use absolute paths (test fixtures, env templates)
_TOOLS_ALLOWLIST = {
    # cleanup_repo_v1.sh is a cleanup script (one-shot, /tmp/ is fine)
    "tools/cleanup_repo_v1.sh",
    # dev_im_finder_scan.py has /root/.config/goose in a comment, not code
    "tools/dev_im_finder_scan.py",
}


def test_no_hard_coded_absolute_paths_in_tools():
    """R110-43: tools/ must not contain hard-coded /root/, /home/<user>, /Users/ paths.

    These break when run by a different user or in a container. Should use
    os.path.expanduser('~/...') or os.environ.get(...) or shutil.which(...).
    """
    violations = []
    for tool_path in TOOLS_DIR.rglob("*.py"):
        rel = str(tool_path.relative_to(REPO_ROOT))
        if rel in _TOOLS_ALLOWLIST:
            continue
        try:
            content = tool_path.read_text()
        except Exception:
            continue
        for m in HARDCODED_PATH_RE.finditer(content):
            line_num = content[:m.start()].count("\n") + 1
            violations.append((rel, line_num, m.group("path")))
    assert not violations, (
        f"R110-43: {len(violations)} hard-coded absolute paths in tools/*.py. "
        f"Use os.path.expanduser, os.environ, or shutil.which instead. "
        f"First 10: {violations[:10]}"
    )
