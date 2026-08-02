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
    """recipes/ must contain at least 20 yaml files (the demo-team recipe set)."""
    yamls = list(RECIPES_DIR.glob("*.yaml"))
    assert len(yamls) >= 20, (
        f"R110-54: {RECIPES_DIR} has only {len(yamls)} yaml files, expected 20+ "
        f"(the demo-team recipe set: code-reviewer + 22 sub_mas-cr-*.yaml)"
    )


def test_demo_team_instructions_exist():
    """instructions/ must contain at least 2 md files (code-reviewer, demo-runner)."""
    mds = list(INSTRUCTIONS_DIR.glob("*.md"))
    assert len(mds) >= 2, (
        f"R110-54: {INSTRUCTIONS_DIR} has only {len(mds)} md files, expected 2+ "
        f"(code-reviewer.md, sub_mas-demo-runner.md)"
    )


def test_demo_team_prompts_exist():
    """prompts/ + prompts-build-optimize-tasks/ must contain at least 3 txt files."""
    txts = list(PROMPTS_DIR.glob("*.txt")) + list(PROMPTS_BUILD_OPTIMIZE_DIR.glob("*.txt"))
    assert len(txts) >= 3, (
        f"R110-54: prompts dirs have only {len(txts)} txt files total, expected 3+ "
        f"(code-reviewer.txt + 3 build-optimize-tasks prompts)"
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
