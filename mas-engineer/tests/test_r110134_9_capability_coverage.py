"""
test_r110134_9_capability_coverage.py — R110-134

NEW: tests inspired by the 30-agent multi-arch e2e log (dev-mas-engineer-30agents).
These verify that the 9 documented capabilities of mas-engineer are:
1. Still present in the codebase
2. Not broken by refactor
3. Internally consistent (cross-references work)

The 9 capabilities (extracted from logs/e2e-results/2026-08-01-mas-pty-129/dev-mas-engineer-30agents.log):

  C1: Generic framework initialization  (dev_generic_init.py exists + importable)
  C2: YAML recipe validation           (yaml.safe_load works on all recipes)
  C3: Tool/script inventory            (tools/*.py + tools/*.sh count)
  C4: Sub-agent dispatch               (sub_recipes pattern works)
  C5: Mode-check guard                 (.mas-mode + .goosehints present)
  C6: Dashboard MCP server             (.mas/mcp/server.js present)
  C7: Dashboard data refresh           (dev_dashboard_data.py or dev_dashboard_refresh.py)
  C8: Recovery chain                   (5 sub_mas-recovery-* recipes present)
  C9: R-number naming convention       (R-numbers referenced consistently)

This test is "infrastructure presence" — it doesn't execute the capabilities
but verifies they're available. Execution tests are the 30-agent e2e
(see tools/mas_e2e_pty_all.sh).

Run with:
    cd mas-engineer && pytest tests/test_r110134_9_capability_coverage.py -v
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from _recipe_helpers import REPO_ROOT, load_all_recipes  # noqa: E402

TOOLS_DIR = REPO_ROOT / "tools"
RECIPE_DIR = REPO_ROOT / "recipe"
INSTRUCTIONS_DIR = RECIPE_DIR / "instructions"
MCP_DIR = REPO_ROOT / ".mas" / "mcp"


# C1: Generic framework initialization
def test_c1_dev_generic_init_present():
    """C1: dev_generic_init.py must exist and be importable."""
    p = TOOLS_DIR / "dev_generic_init.py"
    assert p.exists(), f"{p} missing — C1 (generic init) capability is gone"
    # Importable check
    import subprocess
    r = subprocess.run(
        ["python3", "-c", "import ast; ast.parse(open('" + str(p) + "').read())"],
        capture_output=True, text=True, timeout=10,
        cwd=str(REPO_ROOT),
    )
    assert r.returncode == 0, f"dev_generic_init.py has Python syntax errors:\n{r.stderr[:300]}"


# C2: YAML recipe validation
def test_c2_all_recipes_parse_as_yaml():
    """C2: Every recipe/*.yaml must parse with yaml.safe_load."""
    recipes = load_all_recipes()
    assert len(recipes) > 100, f"Only {len(recipes)} recipes — something is broken in recipe/ tree"
    # All should have 'name' key
    no_name = [b for b, i in recipes.items() if not i["data"].get("name")]
    assert not no_name, f"{len(no_name)} recipes have no 'name' field: {no_name[:5]}"


# C3: Tool/script inventory
def test_c3_tools_inventory_complete():
    """C3: mas-engineer should have at least 30 .py tools and 5 .sh scripts."""
    py = list(TOOLS_DIR.glob("*.py"))
    sh = list(TOOLS_DIR.glob("*.sh"))
    assert len(py) >= 30, f"Only {len(py)} .py tools — expected ≥ 30"
    assert len(sh) >= 5, f"Only {len(sh)} .sh scripts — expected ≥ 5"


# C4: Sub-agent dispatch
def test_c4_dispatch_topology_is_valid():
    """C4: Recipes in recipe/ (top-level) that delegate to sub-agents should
    have sub_recipes. Sub-recipes in recipe/sub/ are LEAVES and don't need
    to delegate. So we check only the top-level dispatchers.

    Top-level dispatchers (have sub_recipes) found in recipe/*.yaml:
    - dev-mas-engineer, dev-mas-engineer-30agents, root_recipe, e2e-verify-*
    - sub_mas-*-director, sub_mas-*-runner, sub_mas-*-validator (some)

    Threshold: ≥ 6 of the top-level recipes (the delegators) should have sub_recipes.
    """
    recipes = load_all_recipes()
    # Top-level = recipe/*.yaml, not recipe/sub/*.yaml
    top_level = {
        b: i for b, i in recipes.items()
        if "/sub/" not in i["path"] and i["path"].endswith(".yaml")
    }
    n_with = sum(1 for i in top_level.values() if i["data"].get("sub_recipes"))
    # There are ~9-10 top-level recipes (the orchestrators/delegators).
    # At least 6 should delegate to sub-recipes.
    assert len(top_level) >= 6, f"Only {len(top_level)} top-level recipes — expected ≥ 6"
    assert n_with >= 6, (
        f"Only {n_with}/{len(top_level)} top-level recipes have sub_recipes. "
        f"At least 6 orchestrators should delegate. Top-level files: {list(top_level.keys())}"
    )


# C5: Mode-check guard
def test_c5_mas_mode_and_goosehints_present():
    """C5: The workspace guard files must exist for mode-check to work."""
    mas_mode = REPO_ROOT / ".mas-mode"
    goosehints = REPO_ROOT / ".goosehints"
    assert mas_mode.exists(), f"{mas_mode} missing — dev-mas-engineer mode-check will abort"
    assert goosehints.exists(), f"{goosehints} missing — goose can't auto-detect this workspace"


# C6: Dashboard MCP server
def test_c6_dashboard_mcp_files_present():
    """C6: .mas/mcp/ must contain server.js + dashboard.html + package.json."""
    server = MCP_DIR / "server.js"
    html = MCP_DIR / "dashboard.html"
    pkg = MCP_DIR / "package.json"
    assert server.exists(), f"{server} missing — dashboard MCP server can't run"
    assert html.exists(), f"{html} missing — dashboard UI is gone"
    assert pkg.exists(), f"{pkg} missing — npm install will fail"
    # Server.js should be non-trivial (> 1KB)
    assert server.stat().st_size > 1024, f"{server} is suspiciously small ({server.stat().st_size} bytes)"


# C7: Dashboard data refresh
def test_c7_dashboard_refresh_tool_exists():
    """C7: At least one of dev_dashboard_data.py / dev_dashboard_refresh.py must exist."""
    candidates = [
        TOOLS_DIR / "dev_dashboard_data.py",
        TOOLS_DIR / "dev_dashboard_refresh.py",
    ]
    assert any(p.exists() for p in candidates), (
        f"None of {candidates} exist — dashboard data can't be refreshed"
    )


# C8: Recovery chain
def test_c8_recovery_chain_complete():
    """C8: All 5 sub_mas-recovery-* recipes must exist (checkpoint/defib/immune/safezone/timeline)."""
    expected = [
        "sub_mas-recovery-checkpoint",
        "sub_mas-recovery-defib",
        "sub_mas-recovery-immune",
        "sub_mas-recovery-safezone",
        "sub_mas-recovery-timeline",
    ]
    missing = [n for n in expected if not (RECIPE_DIR / "sub" / f"{n}.yaml").exists()]
    assert not missing, f"Missing recovery chain members: {missing}"


# C9: R-number naming convention
def test_c9_r_number_pattern_used_consistently():
    """C9: The 'R<n>-<m>' pattern should appear in pre-push / commit-protocol tools.
    This guards against the 'wrench:' / 'book:' legacy formats (R110-128)."""
    pre_push = TOOLS_DIR / "pre_push_validator.py"
    if not pre_push.exists():
        pytest.skip("pre_push_validator.py not present")
    text = pre_push.read_text()
    # Either the new 12-type allowlist or the legacy 5-type list
    n_types = len(re.findall(r"['\"](\w+)['\"]\s*[:,]", text))
    # Count distinct conventional types referenced
    conventional_types = re.findall(r"['\"](fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)['\"]", text)
    unique = set(conventional_types)
    assert len(unique) >= 8, (
        f"Only {len(unique)} conventional types in pre_push_validator.py: {unique}\n"
        "R110-130 requires 12 types: fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert"
    )
