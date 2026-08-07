"""
demos/demo-team/tests/test_demo_team.py

R110-54: Tests for the demo-team DEMO live IN the demo folder
(per user rule: "tests of demos belong in the demo folder").

R110-54: demos/ is FULLY AUTONOMOUS — zero imports from tests/.
The classify_domain helper is vendored in _helpers.py (intentional
DRY violation, kept in sync manually). The demos/ tree is a closed
unit: it can be copied out of the mas-engineer repo and still work.

The 6 tests validate:
  - recipes/ contains >= 20 yaml files
  - instructions/ contains >= 2 md files
  - prompts/ + prompts-build-optimize-tasks/ contain >= 3 txt files
  - every recipe's external .instructions path resolves
  - every recipe classifies as "demo-team"
  - every recipe is valid YAML (parses to a dict)
"""
from pathlib import Path

import yaml

# Resolve all paths relative to this file. No sys.path manipulation,
# no imports from tests/. demos/ is autonomous.
TESTS_DIR = Path(__file__).resolve().parent
DEMO_DIR = TESTS_DIR.parent                      # demos/demo-team/

RECIPES_DIR = DEMO_DIR / "recipes"
INSTRUCTIONS_DIR = DEMO_DIR / "instructions"
PROMPTS_DIR = DEMO_DIR / "prompts"
PROMPTS_BUILD_OPTIMIZE_DIR = DEMO_DIR / "prompts-build-optimize-tasks"

# classify_domain lives next to this test file (demos/demo-team/tests/_helpers.py).
# pytest adds the test's parent dir to sys.path automatically, so a plain
# `import _helpers` works without making demos/ a package (and thus avoids
# the "tests.test_demo_team" namespace conflict with the central tests/
# directory that contains its own __init__.py).
import _helpers  # noqa: E402
classify_domain = _helpers.classify_domain


# ---- R110-54: demo-team sanity ----

def test_demo_team_recipes_exist():
    """recipes/ must contain at least 25 yaml files (the demo-team recipe set).

    R110-54: initial 23 (code-reviewer.yaml + 22 sub_mas-cr-*.yaml).
    R110-55: +4 (sub_mas-social-media-manager, email-campaign-manager,
            seo-researcher, content-writer).
    """
    yamls = list(RECIPES_DIR.glob("*.yaml"))
    assert len(yamls) >= 25, (
        f"R110-55: {RECIPES_DIR} has only {len(yamls)} yaml files, expected 25+ "
        f"(23 from R110-54 + 4 from R110-55)"
    )


def test_demo_team_instructions_exist():
    """instructions/ must contain at least 5 md files.

    R110-54: 2 (code-reviewer.md, sub_mas-demo-runner.md) + 1 created
             (sub_mas-analytics-reporter.md) = 3.
    R110-55: +4 (sub_mas-content-writer, email-campaign-manager,
             seo-researcher, social-media-manager) = 7 total.
    R110-56: -1 (sub_mas-web-researcher.md moved BACK to
             recipe/instructions/ — it is a FRAMEWORK sub-agent,
             not a demo. The e2e test recipe
             mas_e2e_pty_test_recipes.txt:130 loads it from
             recipe/sub/, and 4 framework instructions reference it
             via DELEGATE).
    """
    mds = list(INSTRUCTIONS_DIR.glob("*.md"))
    assert len(mds) >= 5, (
        f"R110-55: {INSTRUCTIONS_DIR} has only {len(mds)} md files, expected 5+ "
        f"(3 from R110-54 + 4 from R110-55 = 7; R110-56 moved web-researcher "
        f"back to recipe/instructions/, so 7 demo-team + 1 framework = 7 demo)"
    )


def test_demo_team_prompts_exist():
    """prompts/ + prompts-build-optimize-tasks/ must contain at least 8 txt files.

    R110-54: 1 + 3 = 4 (code-reviewer.txt + 3 build-optimize-tasks).
    R110-55: +5 (customer-support, data-analyzer, research-team,
             content-pipeline, security-scanner) = 9 total.
    """
    txts = list(PROMPTS_DIR.glob("*.txt")) + list(PROMPTS_BUILD_OPTIMIZE_DIR.glob("*.txt"))
    assert len(txts) >= 8, (
        f"R110-55: prompts dirs have only {len(txts)} txt files total, expected 8+ "
        f"(4 from R110-54 + 5 from R110-55)"
    )


def test_demo_team_recipe_instruction_paths_resolve():
    """Every recipe's external `instructions: '# Extended instructions: ...'`
    path must resolve to an existing .md file in instructions/."""
    if not RECIPES_DIR.exists():
        return
    missing = []
    for p in RECIPES_DIR.glob("*.yaml"):
        try:
            with open(p) as f:
                content = f.read()
        except Exception:
            continue
        # Heuristic: find '# Extended instructions: <path>' lines
        import re
        m = re.search(r"#\s*Extended instructions:\s*([\w./-]+\.md)", content)
        if m:
            rel = m.group(1)
            # rel is relative to the recipe (e.g. "recipe/instructions/...")
            # or to repo root. We strip the "recipe/" prefix if present
            # and resolve against DEMO_DIR or repo root.
            clean = rel
            if clean.startswith("recipe/"):
                clean = clean[len("recipe/"):]
            # Try DEMO_DIR first, then RECIPES_DIR.parent.parent
            for base in (DEMO_DIR, DEMO_DIR.parent, DEMO_DIR.parent.parent):
                candidate = base / clean
                if candidate.exists():
                    break
            else:
                # Try stripping the leading "instructions/" if it's there
                if not clean.startswith("instructions/"):
                    clean2 = "instructions/" + clean.split("/")[-1]
                else:
                    clean2 = clean
                if not (DEMO_DIR / clean2).exists():
                    missing.append((p.name, rel))
    assert not missing, (
        f"R110-54: {len(missing)} recipes reference instruction paths that don't resolve. "
        f"First 5: {missing[:5]}"
    )


def test_demo_team_recipes_classified():
    """Every recipe under recipes/ is classified as 'demo-team'."""
    if not RECIPES_DIR.exists():
        return
    out = {}
    for p in RECIPES_DIR.glob("*.yaml"):
        try:
            with open(p) as f:
                data = yaml.safe_load(f)
        except Exception:
            continue
        if isinstance(data, dict):
            out[p.name] = classify_domain(p.name, data, parent_path=p.parent)
    wrong = {k: v for k, v in out.items() if v != "demo-team"}
    assert not wrong, (
        f"R110-54: {len(wrong)}/{len(out)} demo-team/recipes/* files are NOT "
        f"classified as 'demo-team'. Wrong: {wrong}"
    )


def test_demo_team_recipes_valid_yaml():
    """Every recipe under recipes/ must be valid YAML (parses to a dict)."""
    if not RECIPES_DIR.exists():
        return
    bad = []
    for p in RECIPES_DIR.glob("*.yaml"):
        try:
            with open(p) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                bad.append((p.name, "not a dict"))
        except Exception as e:
            bad.append((p.name, str(e)[:50]))
    assert not bad, (
        f"R110-54: {len(bad)} demo-team recipes are invalid YAML. "
        f"First 5: {bad[:5]}"
    )


# ---- R110-55: new tests for the R110-55 expansion ----

def test_demo_team_prompts_subdirs_have_expected_files():
    """R110-55: prompts/ should have >= 5 demo-build txt files + README,
    prompts-build-optimize-tasks/ should have >= 3 build-optimize txt files.

    Before R110-55, all 5 demo-build prompts were in prompts/ at the
    repo root (no README there). After R110-55, they live alongside
    code-reviewer.txt in demos/demo-team/prompts/, with the user-facing
    README (catalogue) at the same level.
    """
    demo_build = list(PROMPTS_DIR.glob("*.txt"))
    build_opt = list(PROMPTS_BUILD_OPTIMIZE_DIR.glob("*.txt"))
    readme = PROMPTS_DIR / "README.md"
    assert len(demo_build) >= 5, (
        f"R110-55: prompts/ has only {len(demo_build)} .txt files, expected 5+ "
        f"(code-reviewer + customer-support + data-analyzer + research-team + "
        f"content-pipeline + security-scanner)"
    )
    assert len(build_opt) >= 3, (
        f"R110-55: prompts-build-optimize-tasks/ has only {len(build_opt)} .txt, "
        f"expected 3+ (code-reviewer + customer-support + research-team)"
    )
    assert readme.exists(), (
        f"R110-55: {readme} does not exist — the user-facing catalogue "
        f"MUST travel with the prompts."
    )


def test_demo_team_no_recipe_sub_leftovers():
    """R110-55 regression guard: NO demo-team recipe file must remain
    in recipe/sub/ after the move.

    Before R110-54/R110-55, recipe/sub/ contained ~5 demo-team recipes
    (social-media-manager, email-campaign-manager, seo-researcher,
    content-writer, analytics-reporter) that R110-54 mostly moved
    (forgot 4 of them; R110-55 fixed the rest). This test guarantees
    they never sneak back.
    """
    recipe_sub = Path(__file__).resolve().parent.parent.parent.parent / "recipe" / "sub"
    if not recipe_sub.exists():
        return
    leftovers = []
    for p in recipe_sub.glob("sub_mas-*.yaml"):
        try:
            with open(p) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        c = classify_domain(p.name, data, parent_path=p.parent)
        if c == "demo-team":
            leftovers.append(p.name)
    assert not leftovers, (
        f"R110-55 regression: {len(leftovers)} demo-team recipes are still "
        f"in recipe/sub/ — they should live in demos/demo-team/recipes/. "
        f"Leftovers: {leftovers}"
    )


def test_demo_team_no_instructions_leftovers():
    """R110-55 regression guard: NO demo-team instructions file must remain
    in recipe/instructions/ after the move.

    R110-54 moved code-reviewer.md, sub_mas-demo-runner.md, and created
    sub_mas-analytics-reporter.md. R110-55 moved the remaining 4
    (content-writer, email-campaign-manager, seo-researcher,
    social-media-manager). R110-56 keeps web-researcher in
    recipe/instructions/ (it is a FRAMEWORK sub-agent, not a demo).
    This test guarantees demo-team instructions never sneak back.
    """
    recipe_instructions = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "recipe" / "instructions"
    )
    if not recipe_instructions.exists():
        return
    # DOMAIN3_TOKENS=*** 5 demo-team stems (R110-56: web-researcher removed —
    # it is a framework sub-agent, e2e test recipe loads it from recipe/sub/).
    # Any .md in recipe/instructions/ whose stem contains one of these tokens
    # is a leftover.
    demo_stems = {
        "social-media-manager", "email-campaign-manager", "seo-researcher",
        "content-writer", "analytics-reporter",
    }
    leftovers = [
        p.name for p in recipe_instructions.glob("*.md")
        if any(s in p.stem for s in demo_stems)
    ]
    assert not leftovers, (
        f"R110-55 regression: {len(leftovers)} demo-team instructions are "
        f"still in recipe/instructions/ — they should live in "
        f"demos/demo-team/instructions/. Leftovers: {leftovers}"
    )


def test_demo_team_no_prompts_leftovers():
    """R110-55 regression guard: NO demo-build prompt .txt may remain
    in prompts/ at the repo root after the move.

    R110-55 moved all 5 (customer-support, data-analyzer, research-team,
    content-pipeline, security-scanner) plus README.md into
    demos/demo-team/prompts/. This test guarantees they never sneak back.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    prompts_root = repo_root / "prompts"
    if not prompts_root.exists():
        return
    # These 5 stems are the demo-build prompts. code-reviewer.txt and
    # others may legitimately live elsewhere; we only check the 5.
    demo_prompts = {
        "customer-support.txt", "data-analyzer.txt", "research-team.txt",
        "content-pipeline.txt", "security-scanner.txt",
    }
    leftovers = [
        p.name for p in prompts_root.glob("*.txt")
        if p.name in demo_prompts
    ]
    readme_leftover = (prompts_root / "README.md").exists()
    assert not leftovers, (
        f"R110-55 regression: {len(leftovers)} demo-build prompts are "
        f"still in prompts/ — they should live in "
        f"demos/demo-team/prompts/. Leftovers: {leftovers}"
    )
    assert not readme_leftover, (
        f"R110-55 regression: prompts/README.md is still in prompts/ — "
        f"it should live in demos/demo-team/prompts/ alongside the "
        f"prompts it documents."
    )


def test_demo_team_no_orphan_instructions():
    """R110-55: every .md in instructions/ MUST be referenced by at least
    one recipe (no orphan .md files left behind after moves).

    This is the inverse direction of recipe-counts-match-instructions:
    instead of asking "does every recipe have a .md?" (false-positive
    for derivates like sub_mas-cr-reporter-formatter which legitimately
    share their parent's .md), we ask "does every .md have at least
    one consumer?" (true-positive: if a .md is moved but no recipe
    references it anymore, that's an orphan).
    """
    if not INSTRUCTIONS_DIR.exists() or not RECIPES_DIR.exists():
        return
    all_recipe_text = ""
    for p in RECIPES_DIR.glob("*.yaml"):
        try:
            all_recipe_text += "\n" + p.read_text()
        except Exception:
            continue
    orphans = []
    for p in INSTRUCTIONS_DIR.glob("*.md"):
        stem = p.stem  # e.g. "sub_mas-cr-synthesizer" → also matches
                       # "sub_mas-cr-synthesizer-merger" via startswith
        # Try exact stem match first
        if stem in all_recipe_text:
            continue
        # Try if any recipe whose stem starts with this .md's stem
        # (e.g. .md = "sub_mas-cr-synthesizer", recipe = "sub_mas-cr-synthesizer-merger")
        if any(stem in r for r in [
            rp.stem for rp in RECIPES_DIR.glob("*.yaml")
        ]):
            continue
        # Try if the .md's bare name (without sub_mas- prefix) is in any recipe
        if p.stem.replace("sub_mas-", "") in all_recipe_text:
            continue
        orphans.append(p.name)
    assert not orphans, (
        f"R110-55: {len(orphans)} instructions .md files are NOT referenced "
        f"by any recipe. They might be orphans. Orphans: {orphans}"
    )
