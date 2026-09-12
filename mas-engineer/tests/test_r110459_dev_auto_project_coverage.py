"""R110-459 — coverage-push r8: tools/dev_auto_project.py 0% → 100%.

Framework-structure auto-detector. JSON output:
{project, main_recipe, mode, has_tests, has_docs, prefix,
project_path}.

Targets:
- detect(path):
  - base = abspath(path)
  - default r: mode='generic', has_tests=False, has_docs=False,
    project/main_recipe/prefix=None
  - if .mas-mode exists → read, strip, if value in
    (mas, framework, generic) → r['mode'] = value (else stays
    'generic')
  - if framework/dev-team/recipes dir exists → first .yaml
    not starting with 'sub_' → r: main_recipe=f, project=
    'dev-team', prefix='fw-', break
  - else if recipes/ dir exists and main_recipe still None →
    first .yaml not sub_ → r: main_recipe, project=basename
    (base), prefix='ag-', break
  - has_tests = tests/ dir exists
  - has_docs = docs/ dir exists
  - project_path = base
  - return r

CLI: path = argv[1] or cwd → json.dumps(detect(path), indent=2)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import tools.dev_auto_project as ap  # noqa: E402


def _make_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────
# detect — defaults
# ─────────────────────────────────────────────────────────────────────
class TestDetectDefaults:
    def test_empty_dir(self, tmp_path):
        r = ap.detect(str(tmp_path))
        assert r["project"] is None
        assert r["main_recipe"] is None
        assert r["mode"] == "generic"
        assert r["prefix"] is None
        assert r["has_tests"] is False
        assert r["has_docs"] is False
        assert r["project_path"] == os.path.abspath(str(tmp_path))

    def test_abspath_normalized(self, tmp_path):
        r = ap.detect(str(tmp_path) + "/.")
        assert r["project_path"] == os.path.abspath(str(tmp_path))


# ─────────────────────────────────────────────────────────────────────
# detect — .mas-mode
# ─────────────────────────────────────────────────────────────────────
class TestDetectMasMode:
    def test_mas_mode(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("mas\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "mas"

    def test_framework_mode(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("framework\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "framework"

    def test_generic_mode(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("generic\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_invalid_mode_keeps_default(self, tmp_path):
        # Unknown value → r['mode'] stays 'generic' (default)
        (tmp_path / ".mas-mode").write_text("unknown_mode\n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"

    def test_mas_mode_with_whitespace(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("  mas  \n")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "mas"

    def test_empty_mas_mode_keeps_default(self, tmp_path):
        (tmp_path / ".mas-mode").write_text("")
        r = ap.detect(str(tmp_path))
        assert r["mode"] == "generic"


# ─────────────────────────────────────────────────────────────────────
# detect — framework/dev-team/recipes
# ─────────────────────────────────────────────────────────────────────
class TestDetectFramework:
    def test_dev_team_recipes(self, tmp_path):
        fw = tmp_path / "framework" / "dev-team" / "recipes"
        fw.mkdir(parents=True)
        (fw / "main.yaml").write_text("version: 1")
        (fw / "sub_x.yaml").write_text("version: 1")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] == "main.yaml"
        assert r["project"] == "dev-team"
        assert r["prefix"] == "fw-"

    def test_dev_team_first_yaml_wins(self, tmp_path):
        # os.listdir order is not guaranteed, but at least ONE
        # non-sub yaml should be picked
        fw = tmp_path / "framework" / "dev-team" / "recipes"
        fw.mkdir(parents=True)
        (fw / "alpha.yaml").write_text("v: 1")
        (fw / "beta.yaml").write_text("v: 1")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] in ("alpha.yaml", "beta.yaml")
        assert not r["main_recipe"].startswith("sub_")

    def test_dev_team_only_sub_yaml_skipped(self, tmp_path):
        fw = tmp_path / "framework" / "dev-team" / "recipes"
        fw.mkdir(parents=True)
        (fw / "sub_x.yaml").write_text("v: 1")
        r = ap.detect(str(tmp_path))
        # Only sub_ files → main_recipe stays None
        assert r["main_recipe"] is None
        assert r["project"] is None

    def test_dev_team_no_yaml_files(self, tmp_path):
        fw = tmp_path / "framework" / "dev-team" / "recipes"
        fw.mkdir(parents=True)
        (fw / "README.md").write_text("notes")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] is None


# ─────────────────────────────────────────────────────────────────────
# detect — recipes/
# ─────────────────────────────────────────────────────────────────────
class TestDetectRecipes:
    def test_recipes_dir(self, tmp_path):
        rc = tmp_path / "recipes"
        rc.mkdir()
        (rc / "main.yaml").write_text("v: 1")
        r = ap.detect(str(tmp_path))
        # project = basename(tmp_path)
        assert r["project"] == os.path.basename(str(tmp_path))
        assert r["main_recipe"] == "main.yaml"
        assert r["prefix"] == "ag-"

    def test_recipes_only_sub_yaml(self, tmp_path):
        rc = tmp_path / "recipes"
        rc.mkdir()
        (rc / "sub_x.yaml").write_text("v: 1")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] is None

    def test_framework_overrides_recipes(self, tmp_path):
        # framework/dev-team/recipes takes priority
        fw = tmp_path / "framework" / "dev-team" / "recipes"
        fw.mkdir(parents=True)
        (fw / "fw_main.yaml").write_text("v: 1")
        rc = tmp_path / "recipes"
        rc.mkdir()
        (rc / "ag_main.yaml").write_text("v: 1")
        r = ap.detect(str(tmp_path))
        assert r["main_recipe"] == "fw_main.yaml"
        assert r["project"] == "dev-team"
        assert r["prefix"] == "fw-"


# ─────────────────────────────────────────────────────────────────────
# detect — has_tests / has_docs
# ─────────────────────────────────────────────────────────────────────
class TestDetectFlags:
    def test_has_tests(self, tmp_path):
        (tmp_path / "tests").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_tests"] is True

    def test_has_docs(self, tmp_path):
        (tmp_path / "docs").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_docs"] is True

    def test_both(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        r = ap.detect(str(tmp_path))
        assert r["has_tests"] is True
        assert r["has_docs"] is True


# ─────────────────────────────────────────────────────────────────────
# CLI (covers __main__ block)
# ─────────────────────────────────────────────────────────────────────
class TestCli:
    def test_cli_with_path(self, tmp_path):
        # Create structure
        (tmp_path / ".mas-mode").write_text("mas\n")
        (tmp_path / "tests").mkdir()
        r = subprocess.run(
            ['python3', 'tools/dev_auto_project.py', str(tmp_path)],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["mode"] == "mas"
        assert data["has_tests"] is True
        assert data["project_path"] == os.path.abspath(str(tmp_path))

    def test_cli_no_argv_uses_cwd(self):
        # Use REPO_ROOT but create a unique marker so cwd-detection
        # is observable. We can't easily make subprocess cwd a
        # non-REPO_ROOT path because the script is in REPO_ROOT.
        # Instead: just verify the no-argv path doesn't crash.
        r = subprocess.run(
            ['python3', 'tools/dev_auto_project.py'],
            capture_output=True, text=True, timeout=5,
            cwd=str(REPO_ROOT))
        assert r.returncode == 0
        data = json.loads(r.stdout)
        # project_path = abspath(REPO_ROOT)
        assert data["project_path"] == os.path.abspath(str(REPO_ROOT))
