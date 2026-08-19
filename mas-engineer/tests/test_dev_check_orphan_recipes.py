"""
test_dev_check_orphan_recipes.py — R110-204 regression tests for
tools/dev_check_orphan_recipes.py.

The tool is the SOURCE OF TRUTH for what "registered" means (R110-31:
"All DOMAIN 1 sub-agents MUST be registered in
configs.mas-self.sub_agents"). pre-push-validator Check 23 (R110-204)
calls it at push time; these tests make sure the tool itself works.

DETECTION→CORRECTION→PREVENTION cycle under test:
  - a DOMAIN 1 recipe in recipe/sub/*.yaml that is NOT in the registry
    is an orphan (undispatchable from workflow)
  - the tool exits 1 with the orphan named in the output
  - once registered (or removed), the tool exits 0

4 test-cases:
  (a) clean state: 0 orphans, exit 0
  (b) temp orphan recipe added -> exit 1, orphan name in output
  (c) temp orphan removed -> exit 0 again
  (d) --json output schema: {"orphans": [{"name", "recipe_file"}]}

Run with:
    python3 -m pytest tests/test_dev_check_orphan_recipes.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOL = REPO_ROOT / "tools" / "dev_check_orphan_recipes.py"


def _make_fixture_repo(tmp_path):
    """Build a mini repo: workflows.yaml registry + 2 registered mas-self
    recipes + 1 mas-generated recipe (must NOT be flagged as orphan)."""
    wf = tmp_path / ".mase" / "workflows.yaml"
    wf.parent.mkdir(parents=True)
    wf.write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents:\n"
        "      analyse:\n"
        "        - sub_mas-fake-analyzer\n"
        "      design:\n"
        "        - sub_mas-fake-designer\n"
    )
    sub_dir = tmp_path / "recipe" / "sub"
    sub_dir.mkdir(parents=True)
    (sub_dir / "sub_mas-fake-analyzer.yaml").write_text(
        "name: Fake Analyzer\n"
        "description: 'v1.0.0 | MAS-internal: fake analyzer'\n"
    )
    (sub_dir / "sub_mas-fake-designer.yaml").write_text(
        "name: Fake Designer\n"
        "description: 'v1.0.0 | MAS-internal: fake designer'\n"
    )
    # DOMAIN 2 (mas-generated) recipe must NOT be an orphan
    (sub_dir / "sub_mas-generic-init.yaml").write_text(
        "name: Generic Init\n"
        "description: 'v1.0.0 | mas-generated template output'\n"
    )
    return tmp_path


def _run_tool(repo, *extra):
    return subprocess.run(
        [sys.executable, str(TOOL), "--repo-root", str(repo), *extra],
        capture_output=True, text=True,
    )


def test_clean_state_no_orphans(tmp_path):
    """(a) registered mas-self recipes -> exit 0, no orphans."""
    repo = _make_fixture_repo(tmp_path)
    res = _run_tool(repo)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "OK" in res.stdout


def test_temp_orphan_detected(tmp_path):
    """(b) unregistered DOMAIN 1 recipe -> exit 1 + name in output."""
    repo = _make_fixture_repo(tmp_path)
    orphan = repo / "recipe" / "sub" / "sub_test-orphan-xyz.yaml"
    orphan.write_text(
        "name: Test Orphan\n"
        "description: 'v1.0.0 | MAS-internal: unregistered orphan'\n"
    )
    res = _run_tool(repo)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "sub_test-orphan-xyz" in res.stdout
    assert "ORPHAN" in res.stdout


def test_orphan_removed_clean_again(tmp_path):
    """(c) removing the temp orphan restores exit 0."""
    repo = _make_fixture_repo(tmp_path)
    orphan = repo / "recipe" / "sub" / "sub_test-orphan-xyz.yaml"
    orphan.write_text(
        "name: Test Orphan\n"
        "description: 'v1.0.0 | MAS-internal: unregistered orphan'\n"
    )
    assert _run_tool(repo).returncode == 1
    orphan.unlink()
    res = _run_tool(repo)
    assert res.returncode == 0, res.stdout + res.stderr


def test_json_output_schema(tmp_path):
    """(d) --json emits {'orphans': [{'name', 'recipe_file'}]}."""
    repo = _make_fixture_repo(tmp_path)
    res = _run_tool(repo, "--json")
    assert res.returncode == 0, res.stdout + res.stderr
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert isinstance(payload["orphans"], list)
    assert payload["orphans"] == []

    # with an orphan present: schema of the orphan entries
    orphan = repo / "recipe" / "sub" / "sub_test-orphan-xyz.yaml"
    orphan.write_text(
        "name: Test Orphan\n"
        "description: 'v1.0.0 | MAS-internal: unregistered orphan'\n"
    )
    res2 = _run_tool(repo, "--json")
    assert res2.returncode == 1
    payload2 = json.loads(res2.stdout)
    assert payload2["ok"] is False
    assert len(payload2["orphans"]) == 1
    entry = payload2["orphans"][0]
    assert entry["name"] == "sub_test-orphan-xyz"
    assert entry["recipe_file"] == "recipe/sub/sub_test-orphan-xyz.yaml"
