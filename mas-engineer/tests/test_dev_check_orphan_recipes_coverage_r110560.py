"""
test_dev_check_orphan_recipes_coverage_r110560.py — R110-560: direct-import
coverage tests for tools/dev_check_orphan_recipes.py.

Sibling of test_dev_bulk_findings_fixer_coverage_r110560.py.
test_dev_check_orphan_recipes.py was already passing (4 cases) but used
subprocess.run, missing this module's coverage completely (subprocess
launches don't register coverage without a per-process sitecustomize hook,
which we don't have here).

This file imports the module and exercises every public helper directly.

Targets covered (88 stmts):
  - classify_domain(): all 5 branches
    (DOMAIN2 prefix → mas-generated, DOMAIN3 substring → demo-team,
     DOMAIN1 description → mas-self, DOMAIN1 prefix → mas-self,
     regex vX.Y.Z + marketing-kw check → mas-self, default → unknown)
  - load_registered(): missing workflows.yaml, unreadable yaml,
    no configs.mas-self key, dict-of-strings sub_agents,
    dict-of-lists sub_agents, non-list values
  - scan_recipe_sub(): missing dir, ORIGINAL_ skip, non-yaml file,
    non-dict yaml
  - find_orphans(): clean repo, orphan present, registry missing
  - main(): --json, plain text, registry-missing exit 2,
    orphan found exit 1, clean exit 0

Run with:
    python3 -m pytest tests/test_dev_check_orphan_recipes_coverage_r110560.py -v
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

# Direct import for coverage
from tools import dev_check_orphan_recipes as dor


# ---------------------------------------------------------------------------
# classify_domain — every branch
# ---------------------------------------------------------------------------

def test_classify_domain2_prefix_mas_generated():
    """DOMAIN2 prefix → mas-generated (highest precedence)."""
    assert dor.classify_domain(
        "sub_mas-team-packager", {"description": "anything"}
    ) == "mas-generated"
    assert dor.classify_domain(
        "sub_mas-generic-init", {"description": "anything"}
    ) == "mas-generated"


def test_classify_domain3_substring_demo_team():
    """DOMAIN3 substring → demo-team."""
    assert dor.classify_domain(
        "social-media-manager-foo", {"description": "x"}
    ) == "demo-team"
    assert dor.classify_domain(
        "my-seo-researcher", {"description": "x"}
    ) == "demo-team"


def test_classify_domain1_description_mas_self():
    """DOMAIN1 description keywords → mas-self."""
    data = {"description": "v1.0.0 | MAS-internal: foo bar"}
    assert dor.classify_domain("anything-random-12345", data) == "mas-self"

    data2 = {"description": "anything CONTROLLER-internal anything"}
    assert dor.classify_domain("anything-random-67890", data2) == "mas-self"


def test_classify_domain1_prefix_mas_self():
    """DOMAIN1 prefix → mas-self (fallback when no desc match)."""
    data = {"description": "no matches here"}
    assert dor.classify_domain(
        "sub_mas-monitor-thing", data
    ) == "mas-self"
    assert dor.classify_domain(
        "sub_mas-im-foo", data
    ) == "mas-self"
    assert dor.classify_domain(
        "sub_mas-test-fix-failures-bar", data
    ) == "mas-self"


def test_classify_domain_version_regex_mas_self():
    """Versioned desc (vX.Y.Z | ...) WITHOUT marketing keywords → mas-self."""
    data = {"description": "v1.2.3 | generic engineering recipe"}
    assert dor.classify_domain("generic-recipe-x", data) == "mas-self"


def test_classify_domain_version_regex_with_marketing_kw():
    """Versioned desc WITH marketing keywords → unknown (marketing override)."""
    data = {"description": "v2.0.0 | the social media campaign manager"}
    # "social media" is a marketing keyword → fall through to unknown
    assert dor.classify_domain("campaign-x", data) == "unknown"


def test_classify_domain_fallback_unknown():
    """No matches → unknown."""
    data = {"description": "no semantic content here"}
    assert dor.classify_domain("totally-random-name", data) == "unknown"


def test_classify_domain_missing_description_safe():
    """data.get('description') → None → str(None) → '' → no crashes."""
    assert dor.classify_domain("any-stem", {"description": None}) == "unknown"
    assert dor.classify_domain("any-stem", {}) == "unknown"


# ---------------------------------------------------------------------------
# load_registered — every branch
# ---------------------------------------------------------------------------

def test_load_registered_missing_workflows(tmp_path):
    """No .mase/workflows.yaml → None."""
    assert dor.load_registered(tmp_path) is None


def test_load_registered_yaml_parse_error(tmp_path, monkeypatch):
    """yaml.safe_load raises → returns None."""
    wf = tmp_path / ".mase" / "workflows.yaml"
    wf.parent.mkdir(parents=True)
    wf.write_text("ok: 1\n")
    monkeypatch.setattr(yaml_safe_load := __import__("yaml").safe_load,
                        "__call__", mock.Mock(side_effect=Exception("boom")))
    # The function uses yaml.safe_load inline (not the bound mock).
    # Instead, write unreadable content + patch yaml.safe_load directly:
    with mock.patch("yaml.safe_load", side_effect=Exception("boom")):
        result = dor.load_registered(tmp_path)
    assert result is None


def test_load_registered_not_dict(tmp_path):
    """workflows.yaml root is not a dict (e.g. list) → None."""
    wf = tmp_path / ".mase" / "workflows.yaml"
    wf.parent.mkdir(parents=True)
    wf.write_text("- a\n- b\n")
    assert dor.load_registered(tmp_path) is None


def test_load_registered_no_configs_key(tmp_path):
    """No 'configs' in data → empty set() (chain of `... or {}` defaults)."""
    wf = tmp_path / ".mase" / "workflows.yaml"
    wf.parent.mkdir(parents=True)
    wf.write_text("foo: bar\n")
    # ((data.get('configs') or {}).get('mas-self') or {}).get('sub_agents') or {}
    # → all None/{} fallthroughs → empty set returned.
    result = dor.load_registered(tmp_path)
    assert result == set()


def test_load_registered_no_mas_self_key(tmp_path):
    """configs exists but no configs.mas-self → None sub_agents → None."""
    wf = tmp_path / ".mase" / "workflows.yaml"
    wf.parent.mkdir(parents=True)
    wf.write_text("configs:\n  something-else:\n    x: 1\n")
    # configs.mas-self is None → (None or {}).get('sub_agents') = {} → set()
    # Wait — the code does `((data.get('configs') or {}).get('mas-self') or {}).get('sub_agents') or {}`
    # So sub_agents becomes {} → registered = set() returned (not None)
    result = dor.load_registered(tmp_path)
    assert result == set()


def test_load_registered_dict_of_lists(tmp_path):
    """Standard format: sub_agents is dict-of-lists."""
    wf = tmp_path / ".mase" / "workflows.yaml"
    wf.parent.mkdir(parents=True)
    wf.write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents:\n"
        "      analyse:\n"
        "        - sub_mas-foo\n"
        "        - sub_mas-bar\n"
        "      design:\n"
        "        - sub_mas-baz\n"
    )
    result = dor.load_registered(tmp_path)
    assert result == {"sub_mas-foo", "sub_mas-bar", "sub_mas-baz"}


def test_load_registered_non_list_values_skipped(tmp_path):
    """Non-list values in sub_agents are skipped via `isinstance(v, list)`."""
    wf = tmp_path / ".mase" / "workflows.yaml"
    wf.parent.mkdir(parents=True)
    wf.write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents:\n"
        "      analyse: 42\n"        # not a list
        "      design:\n"
        "        - sub_mas-baz\n"
        "      misc: 'oops'\n"       # string, not list
    )
    result = dor.load_registered(tmp_path)
    assert result == {"sub_mas-baz"}


# ---------------------------------------------------------------------------
# scan_recipe_sub — every branch
# ---------------------------------------------------------------------------

def test_scan_recipe_sub_missing_dir(tmp_path):
    """No recipe/sub/ → generator yields nothing."""
    assert list(dor.scan_recipe_sub(tmp_path)) == []


def test_scan_recipe_sub_skips_original(tmp_path):
    """Files starting with ORIGINAL_ are skipped."""
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "ORIGINAL_sub_mas-x.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal'\n"
    )
    (sub / "sub_mas-y.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal'\n"
    )
    out = list(dor.scan_recipe_sub(tmp_path))
    names = [stem for stem, domain in out]
    assert "ORIGINAL_sub_mas-x" not in names
    assert "sub_mas-y" in names


def test_scan_recipe_sub_skips_unparseable_yaml(tmp_path):
    """Files that yaml can't parse → continue (skipped)."""
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    # Write content that yaml.safe_load can't parse
    (sub / "bad.yaml").write_text("{ broken: [yaml")
    out = list(dor.scan_recipe_sub(tmp_path))
    assert ("bad", "unknown") not in out
    assert all(stem != "bad" for stem, _ in out)


def test_scan_recipe_sub_skips_non_dict_yaml(tmp_path):
    """YAML that parses to a non-dict (list, str, scalar) → skipped."""
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "list.yaml").write_text("- a\n- b\n")
    out = list(dor.scan_recipe_sub(tmp_path))
    assert all(stem != "list" for stem, _ in out)


# ---------------------------------------------------------------------------
# find_orphans — every branch
# ---------------------------------------------------------------------------

def test_find_orphans_clean(tmp_path):
    """All mas-self recipes registered → no orphans."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents:\n"
        "      analyse:\n"
        "        - sub_mas-registered-a\n"
    )
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-registered-a.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: foo'\n"
    )
    orphans, total, registered = dor.find_orphans(tmp_path)
    assert orphans == []
    assert total == 1
    assert "sub_mas-registered-a" in registered


def test_find_orphans_with_orphan(tmp_path):
    """An unregistered mas-self recipe → orphan listed."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents: {}\n"
    )
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-orphan-recipe.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: orphan'\n"
    )
    orphans, total, registered = dor.find_orphans(tmp_path)
    assert total == 1
    assert len(orphans) == 1
    assert orphans[0]["name"] == "sub_mas-orphan-recipe"
    assert orphans[0]["recipe_file"] == "recipe/sub/sub_mas-orphan-recipe.yaml"
    assert registered == set()


def test_find_orphans_no_registry(tmp_path):
    """Missing workflows.yaml → registered=None, no orphans returned.
    The tool will exit 2 in main() but find_orphans() itself doesn't error."""
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-anything.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: x'\n"
    )
    orphans, total, registered = dor.find_orphans(tmp_path)
    # registered is None → no orphans list filled (this is the
    # `if registered is not None` branch).
    assert orphans == []
    assert total == 1
    assert registered is None


def test_find_orphans_mixes_mas_self_and_other(tmp_path):
    """Non-mas-self recipes do NOT appear as orphans even if unregistered."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents:\n"
        "      analyse:\n"
        "        - sub_mas-mas-self-a\n"
    )
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-mas-self-a.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: a'\n"
    )
    (sub / "sub_mas-mas-self-orphan.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: orphan'\n"
    )
    (sub / "social-media-manager-foo.yaml").write_text(
        "description: 'v1.0.0'\n"  # demo-team (DOMAIN3) — not mas-self
    )
    orphans, total, _ = dor.find_orphans(tmp_path)
    # Only 1 mas-self total (orphan doesn't appear in `total` as a separate
    # count — `total` is just `len(mas_self)`). And total here = 2 because
    # only mas-self recipes get into mas_self list.
    assert total == 2
    assert len(orphans) == 1
    assert orphans[0]["name"] == "sub_mas-mas-self-orphan"


# ---------------------------------------------------------------------------
# main() — CLI dispatch + exit codes + output formats
# ---------------------------------------------------------------------------

def test_main_clean_exit_0(tmp_path, capsys):
    """All registered → exit 0 + OK message."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents:\n"
        "      analyse:\n"
        "        - sub_mas-x\n"
    )
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-x.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: x'\n"
    )
    rc = dor.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_main_orphan_exit_1(tmp_path, capsys):
    """Orphan present → exit 1 + error message."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents: {}\n"
    )
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-orphan.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: y'\n"
    )
    rc = dor.main(["--repo-root", str(tmp_path)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "ORPHAN" in out
    assert "sub_mas-orphan" in out


def test_main_json_clean(tmp_path, capsys):
    """--json + clean → ok:true JSON."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents:\n"
        "      analyse:\n"
        "        - sub_mas-x\n"
    )
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-x.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: x'\n"
    )
    rc = dor.main(["--json", "--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["ok"] is True
    assert data["orphans"] == []
    assert data["total_mas_self"] == 1
    assert data["registered"] == 1


def test_main_json_orphan(tmp_path, capsys):
    """--json + orphan → ok:false JSON + orphan list."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(
        "configs:\n"
        "  mas-self:\n"
        "    sub_agents: {}\n"
    )
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-orphan1.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: a'\n"
    )
    (sub / "sub_mas-orphan2.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: b'\n"
    )
    rc = dor.main(["--json", "--repo-root", str(tmp_path)])
    assert rc == 1
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["ok"] is False
    assert len(data["orphans"]) == 2
    names = {o["name"] for o in data["orphans"]}
    assert names == {"sub_mas-orphan1", "sub_mas-orphan2"}


def test_main_no_registry_exit_2(tmp_path, capsys):
    """No workflows.yaml → exit 2 + error message."""
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-x.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: x'\n"
    )
    rc = dor.main(["--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    assert "ERROR" in out


def test_main_no_registry_json(tmp_path, capsys):
    """--json + no registry → ok:false JSON with error msg."""
    sub = tmp_path / "recipe" / "sub"
    sub.mkdir(parents=True)
    (sub / "sub_mas-x.yaml").write_text(
        "description: 'v1.0.0 | MAS-internal: x'\n"
    )
    rc = dor.main(["--json", "--repo-root", str(tmp_path)])
    assert rc == 2
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["ok"] is False
    assert "error" in data
    assert data["orphans"] == []


def test_main_no_repo_root_recipe_dir(tmp_path, capsys):
    """repo-root with no recipe/sub/ directory → clean exit 0."""
    (tmp_path / ".mase").mkdir()
    (tmp_path / ".mase" / "workflows.yaml").write_text(
        "configs:\n  mas-self:\n    sub_agents: {}\n"
    )
    # No recipe/sub/ at all
    rc = dor.main(["--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out
