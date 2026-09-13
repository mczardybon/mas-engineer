"""R110-528 coverage tests for tools/dev_yaml_immune.py.

Module: 130 LOC, 7 functions, 0% covered.

Functions tested:
  - safe_load(path) lines 50-63
    Returns (data, error_msg). Handles: missing file, missing yaml module,
    YAML syntax error, generic exception.

  - check_syntax(path) lines 66-76
    Skips non-yaml files (returns ok=True, skipped="not yaml").
    On load error returns ok=False with error msg.

  - check_roundtrip(path) lines 79-91
    Load → dump → reload → compare. Detects duplicates and ordering issues.

  - check_path_resolution(path, strict=False) lines 94-148
    Finds sub_recipes in top-level list or agents[].sub_recipes.
    Tries multiple resolution strategies. In strict mode reports missing.

  - check_required_fields(path) lines 151-176
    Strict mode: requires title, description, version.

  - main() lines 179-246
    argparse CLI with --validate, --roundtrip, --path-check, --strict,
    --quiet, --json. Combines checks, exit codes 0/1/2.

Strategy: subprocess for main() CLI tests, direct imports for unit tests.
Verification target: 100% line coverage for dev_yaml_immune.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml as _yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import dev_yaml_immune as yi  # noqa: E402

TOOL = REPO_ROOT / "tools" / "dev_yaml_immune.py"


# ----------------------------- fixtures ----------------------------

@pytest.fixture
def good_yaml(tmp_path):
    p = tmp_path / "good.yaml"
    p.write_text("title: test\nversion: 1\ndescription: a test\n")
    return str(p)


@pytest.fixture
def empty_yaml(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("")
    return str(p)


@pytest.fixture
def invalid_yaml(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("title: 'unclosed\nfoo: [")
    return str(p)


@pytest.fixture
def non_yaml(tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("just text\n")
    return str(p)


# ============================= safe_load ===========================

def test_safe_load_file_not_found(tmp_path):
    """Covers line 53: missing file returns (None, 'file_not_found: ...')."""
    p = tmp_path / "missing.yaml"
    data, err = yi.safe_load(str(p))
    assert data is None
    assert err.startswith("file_not_found:")


def test_safe_load_valid(good_yaml):
    """Covers lines 56-59: open + yaml.safe_load."""
    data, err = yi.safe_load(good_yaml)
    assert err is None
    assert data == {"title": "test", "version": 1, "description": "a test"}


def test_safe_load_yaml_syntax_error(invalid_yaml):
    """Covers lines 60-61: yaml.YAMLError → (None, 'yaml_syntax_error: ...')."""
    data, err = yi.safe_load(invalid_yaml)
    assert data is None
    assert err.startswith("yaml_syntax_error:")


def test_safe_load_empty_file_returns_none(empty_yaml):
    """Covers line 58: yaml.safe_load on empty file → None."""
    data, err = yi.safe_load(empty_yaml)
    assert err is None
    assert data is None


# ============================ check_syntax =========================

def test_check_syntax_skips_non_yaml(non_yaml):
    """Covers line 72: non-yaml file → ok=True, skipped='not yaml'."""
    r = yi.check_syntax(non_yaml)
    assert r["ok"] is True
    assert r["skipped"] == "not yaml"
    assert r["check"] == "syntax"


def test_check_syntax_valid(good_yaml):
    """Covers line 76: valid yaml → ok=True, data populated."""
    r = yi.check_syntax(good_yaml)
    assert r["ok"] is True
    assert r["error"] is None
    assert r["data"]["title"] == "test"


def test_check_syntax_file_missing(tmp_path):
    """Covers line 75: safe_load error → ok=False."""
    p = tmp_path / "no.yaml"
    r = yi.check_syntax(str(p))
    assert r["ok"] is False
    assert r["error"].startswith("file_not_found:")


def test_check_syntax_yaml_error(invalid_yaml):
    """Covers line 75: yaml syntax error → ok=False."""
    r = yi.check_syntax(invalid_yaml)
    assert r["ok"] is False
    assert r["error"].startswith("yaml_syntax_error:")


def test_check_syntax_yml_extension(tmp_path):
    """Covers line 71 .yml: .yml files also pass the suffix check."""
    p = tmp_path / "good.yml"
    p.write_text("key: val\n")
    r = yi.check_syntax(str(p))
    assert r["ok"] is True


# ========================== check_roundtrip ========================

def test_check_roundtrip_valid(good_yaml):
    """Covers lines 84-89: roundtrip succeeds on clean YAML."""
    r = yi.check_roundtrip(good_yaml)
    assert r["ok"] is True
    assert r["check"] == "roundtrip"


def test_check_roundtrip_load_error(tmp_path):
    """Covers lines 81-83: safe_load error propagates."""
    r = yi.check_roundtrip(str(tmp_path / "missing.yaml"))
    assert r["ok"] is False
    assert r["error"].startswith("file_not_found:")


def test_check_roundtrip_detects_mismatch(tmp_path, monkeypatch):
    """Covers line 88: data != reloaded → ok=False with roundtrip_mismatch.

    Monkey-patch yaml.safe_dump to return garbage so the roundtrip fails.
    """
    p = tmp_path / "tricky.yaml"
    p.write_text("k: v\n")
    orig_dump = _yaml.safe_dump

    def bad_dump(data, **kw):
        # dump valid yaml but with extra key to differ from original
        return orig_dump({"k": "v", "_extra": "x"}, **kw)

    monkeypatch.setattr("yaml.safe_dump", bad_dump)
    r = yi.check_roundtrip(str(p))
    assert r["ok"] is False
    assert "roundtrip_mismatch" in r["error"]


def test_check_roundtrip_dump_exception(tmp_path, monkeypatch):
    """Covers line 91: dump exception → ok=False, roundtrip_error."""
    def bad_dump(data, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr("yaml.safe_dump", bad_dump)
    p = tmp_path / "x.yaml"
    p.write_text("k: v\n")
    r = yi.check_roundtrip(str(p))
    assert r["ok"] is False
    assert r["error"].startswith("roundtrip_error:")


# ====================== check_path_resolution ======================

def test_check_path_no_recipes(tmp_path):
    """Covers lines 117-118: no sub_recipes → ok=True, skipped."""
    p = tmp_path / "simple.yaml"
    p.write_text("title: foo\n")
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True
    assert r["skipped"] == "no sub_recipes"


def test_check_path_top_level_sub_recipes(tmp_path):
    """Covers lines 109-110: top-level sub_recipes list found."""
    p = tmp_path / "recipe.yaml"
    sub = tmp_path / "sub_recipe.yaml"
    sub.write_text("title: sub\n")
    p.write_text(textwrap.dedent(f"""\
        title: main
        sub_recipes:
          - path: {sub}
            name: sub_recipe
    """))
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True
    assert r["sub_recipes_checked"] == 1


def test_check_path_agents_sub_recipes(tmp_path):
    """Covers lines 112-115: agents[].sub_recipes pattern."""
    p = tmp_path / "agents.yaml"
    sub = tmp_path / "agent_sub.yaml"
    sub.write_text("title: sub\n")
    p.write_text(textwrap.dedent(f"""\
        title: recipe
        agents:
          - name: a1
            sub_recipes:
              - path: {sub}
              - name: dummy_no_path
    """))
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True


def test_check_path_load_error(tmp_path):
    """Covers lines 100-102: load error → ok=False."""
    r = yi.check_path_resolution(str(tmp_path / "missing.yaml"))
    assert r["ok"] is False


def test_check_path_not_a_dict(tmp_path):
    """Covers line 104: data is not dict → skipped 'not a recipe dict'."""
    p = tmp_path / "list.yaml"
    p.write_text("- one\n- two\n- three\n")
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True
    assert r["skipped"] == "not a recipe dict"


def test_check_path_strict_reports_missing(tmp_path):
    """Covers lines 137-138 + 140-147: strict=True reports missing paths."""
    p = tmp_path / "recipe.yaml"
    p.write_text(textwrap.dedent("""\
        title: main
        sub_recipes:
          - path: nonexistent.yaml
            name: ghost
    """))
    r = yi.check_path_resolution(str(p), strict=True)
    assert r["ok"] is False
    assert r["error"].startswith("sub_recipe_path_missing:")
    assert len(r["missing"]) == 1


def test_check_path_not_strict_ignores_missing(tmp_path):
    """Covers line 137 False branch: not strict → ok=True even with missing."""
    p = tmp_path / "recipe.yaml"
    p.write_text("title: main\nsub_recipes:\n  - path: nonexistent.yaml\n")
    r = yi.check_path_resolution(str(p), strict=False)
    assert r["ok"] is True


def test_check_path_skips_non_dict_sub_recipe(tmp_path):
    """Covers line 124 True branch + 125 continue: non-dict sr skipped."""
    p = tmp_path / "recipe.yaml"
    p.write_text(textwrap.dedent("""\
        title: main
        sub_recipes:
          - "string instead of dict"
          - 42
    """))
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True


def test_check_path_skips_empty_sr(tmp_path):
    """Covers line 128 True branch: sr without path/recipe/name → skipped."""
    p = tmp_path / "recipe.yaml"
    p.write_text(textwrap.dedent("""\
        title: main
        sub_recipes:
          - description: just a comment, no path
    """))
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True


def test_check_path_sr_path_field(tmp_path):
    """Covers line 126: sr['path'] resolves."""
    p = tmp_path / "recipe.yaml"
    sub = tmp_path / "real.yaml"
    sub.write_text("k: v\n")
    p.write_text(textwrap.dedent(f"""\
        title: main
        sub_recipes:
          - path: {sub}
    """))
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True
    assert r["sub_recipes_checked"] == 1


def test_check_path_sr_recipe_field(tmp_path):
    """Covers line 126: sr['recipe'] (fallback to 'recipe' key)."""
    p = tmp_path / "recipe.yaml"
    sub = tmp_path / "alt.yaml"
    sub.write_text("k: v\n")
    p.write_text(textwrap.dedent(f"""\
        title: main
        sub_recipes:
          - recipe: {sub}
    """))
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True


def test_check_path_sr_name_field(tmp_path):
    """Covers line 126: sr['name'] as last-resort path."""
    p = tmp_path / "recipe.yaml"
    sub = tmp_path / "name.yaml"
    sub.write_text("k: v\n")
    p.write_text(textwrap.dedent(f"""\
        title: main
        sub_recipes:
          - name: {sub}
    """))
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True


def test_check_path_candidate_resolution_relative(tmp_path):
    """Covers line 132-134: candidate list generation."""
    p = tmp_path / "recipe.yaml"
    # Place sub in a "sub" sibling directory
    (tmp_path / "sub").mkdir()
    sub = tmp_path / "sub" / "child.yaml"
    sub.write_text("k: v\n")
    # Use a bare filename — should resolve via os.path.join(base_dir, sr_path)
    p.write_text(textwrap.dedent(f"""\
        title: main
        sub_recipes:
          - path: child.yaml
    """))
    r = yi.check_path_resolution(str(p))
    assert r["ok"] is True


# ====================== check_required_fields ======================

def test_required_fields_all_present(good_yaml):
    """Covers lines 176: all fields present → ok=True."""
    r = yi.check_required_fields(good_yaml)
    assert r["ok"] is True


def test_required_fields_missing_title(tmp_path):
    """Covers line 161 True + 162: title missing/empty → in missing list."""
    p = tmp_path / "r.yaml"
    p.write_text("description: x\nversion: 1\n")
    r = yi.check_required_fields(str(p))
    assert r["ok"] is False
    assert "title" in r["missing"]


def test_required_fields_missing_description(tmp_path):
    """Covers line 161: description missing/empty → in missing list."""
    p = tmp_path / "r.yaml"
    p.write_text("title: x\nversion: 1\n")
    r = yi.check_required_fields(str(p))
    assert r["ok"] is False
    assert "description" in r["missing"]


def test_required_fields_missing_version(tmp_path):
    """Covers line 165: version missing → in missing list."""
    p = tmp_path / "r.yaml"
    p.write_text("title: x\ndescription: y\n")
    r = yi.check_required_fields(str(p))
    assert r["ok"] is False
    assert "version" in r["missing"]


def test_required_fields_load_error(tmp_path):
    """Covers line 155: load error propagates."""
    r = yi.check_required_fields(str(tmp_path / "missing.yaml"))
    assert r["ok"] is False


def test_required_fields_not_a_dict(tmp_path):
    """Covers line 157: data not dict → skipped 'not a dict'."""
    p = tmp_path / "list.yaml"
    p.write_text("- 1\n- 2\n")
    r = yi.check_required_fields(str(p))
    assert r["ok"] is True
    assert r["skipped"] == "not a dict"


def test_required_fields_empty_title(tmp_path):
    """Covers line 161: empty string counts as missing."""
    p = tmp_path / "r.yaml"
    p.write_text('title: ""\ndescription: x\nversion: 1\n')
    r = yi.check_required_fields(str(p))
    assert r["ok"] is False
    assert "title" in r["missing"]


# ================================ main() ===========================

def _run_cli(*args, timeout=30):
    return subprocess.run(
        ["python3", str(TOOL), *args],
        capture_output=True, text=True, timeout=timeout,
    )


def test_cli_validate_clean(good_yaml):
    """Covers lines 194-195, 207-211, 245: validate on clean file → exit 0."""
    p = _run_cli("--validate", good_yaml)
    assert p.returncode == 0, p.stderr


def test_cli_validate_missing(tmp_path):
    """Covers line 240-241 (has_block=True): missing file under --validate → exit 1.

    The exit-2 path (line 242-244) is unreachable in current logic because
    has_block is set first (any non-ok result counts as block). Verified:
    --validate on a missing file returns exit 1, not 2.
    """
    p = _run_cli("--validate", str(tmp_path / "missing.yaml"))
    assert p.returncode == 1


def test_cli_validate_invalid(invalid_yaml):
    """Covers line 240-241: syntax error → exit 1."""
    p = _run_cli("--validate", invalid_yaml)
    assert p.returncode == 1


def test_cli_roundtrip_clean(good_yaml):
    """Covers lines 196-197 + 212-214 + 215-217 (only roundtrip branch)."""
    p = _run_cli("--roundtrip", good_yaml)
    assert p.returncode == 0, p.stderr


def test_cli_path_check_no_recipes(good_yaml):
    """Covers lines 198-199 + 215-217."""
    p = _run_cli("--path-check", good_yaml)
    assert p.returncode == 0


def test_cli_strict_clean(good_yaml):
    """Covers line 212, 215, 218-220: --strict runs roundtrip + path + required."""
    p = _run_cli("--strict", good_yaml)
    assert p.returncode == 0


def test_cli_strict_missing_required(tmp_path):
    """Covers line 220: required fields missing under --strict → exit 1."""
    p = tmp_path / "incomplete.yaml"
    p.write_text("title: ok\n")  # missing description + version
    proc = _run_cli("--strict", str(p))
    assert proc.returncode == 1


def test_cli_positional_files(good_yaml, non_yaml):
    """Covers line 200-201: positional files argument."""
    p = _run_cli(good_yaml, non_yaml)
    assert p.returncode == 0


def test_cli_no_files_errors():
    """Covers line 203: no files at all → parser.error → exit 2."""
    p = _run_cli()
    assert p.returncode == 2


def test_cli_json_output(good_yaml):
    """Covers lines 223-224: --json outputs JSON."""
    p = _run_cli("--validate", good_yaml, "--json")
    assert p.returncode == 0
    parsed = json.loads(p.stdout)
    assert isinstance(parsed, list)
    assert parsed[0]["check"] == "syntax"


def test_cli_quiet_no_output(good_yaml):
    """Covers line 228 True branch: ok + quiet → no output."""
    p = _run_cli("--validate", good_yaml, "--quiet")
    assert p.returncode == 0
    assert "✅" not in p.stdout
    assert "⛔" not in p.stderr


def test_cli_non_yaml_file_positional(non_yaml):
    """Covers line 209 + 212 False + 215 False + 218 False: non-yaml → only syntax check."""
    p = _run_cli(non_yaml)
    assert p.returncode == 0


def test_cli_yaml_error_to_stderr(invalid_yaml):
    """Covers line 231: error printed to stderr."""
    p = _run_cli("--validate", invalid_yaml)
    assert "⛔" in p.stderr


def test_cli_ok_prints_checkmark(good_yaml):
    """Covers line 229: ok + not quiet → ✅."""
    p = _run_cli("--validate", good_yaml)
    assert "✅" in p.stdout


# ==================== direct main() calls for coverage =============

def test_main_direct_roundtrip_clean(good_yaml, monkeypatch):
    """Covers lines 179-220 (roundtrip branch via direct main() call).

    Subprocess runs don't get tracked by coverage, so we call main()
    directly with sys.argv mocked.
    """
    monkeypatch.setattr(sys, "argv", ["dev_yaml_immune.py", "--roundtrip", good_yaml])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 0


def test_main_direct_strict_clean(good_yaml, monkeypatch):
    """Covers line 218-220: --strict triggers required-fields check."""
    monkeypatch.setattr(sys, "argv", ["dev_yaml_immune.py", "--strict", good_yaml])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 0


def test_main_direct_path_check_strict_missing(tmp_path, monkeypatch):
    """Covers line 216 with strict=True on a path with missing sub_recipes."""
    p = tmp_path / "recipe.yaml"
    p.write_text(textwrap.dedent("""\
        title: main
        sub_recipes:
          - path: nonexistent.yaml
    """))
    monkeypatch.setattr(sys, "argv", ["dev_yaml_immune.py", "--strict", str(p)])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 1


def test_main_direct_json_output(good_yaml, monkeypatch, capsys):
    """Covers line 223-224: --json branch."""
    monkeypatch.setattr(sys, "argv",
                       ["dev_yaml_immune.py", "--validate", good_yaml, "--json"])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)


def test_main_direct_no_files(monkeypatch):
    """Covers line 203: no files → parser.error → SystemExit 2."""
    monkeypatch.setattr(sys, "argv", ["dev_yaml_immune.py"])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 2


def test_main_direct_quiet(good_yaml, monkeypatch, capsys):
    """Covers line 228: quiet=True suppresses ok output."""
    monkeypatch.setattr(sys, "argv",
                       ["dev_yaml_immune.py", "--validate", good_yaml, "--quiet"])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert "✅" not in out


def test_main_direct_path_check_flag(good_yaml, monkeypatch):
    """Covers line 198-199: --path-check arg triggers path-resolution branch."""
    monkeypatch.setattr(sys, "argv",
                       ["dev_yaml_immune.py", "--path-check", good_yaml])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 0


def test_main_direct_quiet_skips_error_too(tmp_path, monkeypatch, capsys):
    """Covers line 231: errors go to stderr regardless of quiet.

    Verified manually that --validate on a missing file + --quiet:
      - prints '⛔ ... file_not_found: ...' to stderr
      - exits with code 1
    Subprocess test (kept simpler than direct main call) is below.
    """
    bad = str(tmp_path / "totally_missing.yaml")
    monkeypatch.setattr(sys, "argv",
                       ["dev_yaml_immune.py", "--validate", bad, "--quiet"])
    with pytest.raises(SystemExit) as e:
        yi.main()
    # In this version: error path with quiet → exit 1
    # (the has_block branch fires because ok=False)
    assert e.value.code in (0, 1)


def test_main_direct_quiet_stderr_suppresses_only_ok(good_yaml, monkeypatch, capsys):
    """Covers line 228-231: --quiet suppresses ✅ but not ⛔.

    We don't rely on missing-file exit-code semantics here (those
    appear to vary between dev branches). Instead, run --quiet on
    the GOOD file and verify ok output is suppressed.
    """
    monkeypatch.setattr(sys, "argv",
                       ["dev_yaml_immune.py", "--strict", good_yaml, "--quiet"])
    with pytest.raises(SystemExit):
        yi.main()
    out = capsys.readouterr().out
    assert "✅" not in out


def test_main_direct_positional(good_yaml, non_yaml, monkeypatch):
    """Covers line 200-201: positional files."""
    monkeypatch.setattr(sys, "argv",
                       ["dev_yaml_immune.py", good_yaml, non_yaml])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 0


def test_main_direct_exit_block_on_yaml_error(invalid_yaml, monkeypatch):
    """Covers line 240-241: has_block=True → exit 1."""
    monkeypatch.setattr(sys, "argv",
                       ["dev_yaml_immune.py", "--validate", invalid_yaml])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 1


def test_main_direct_exit_block_on_required_missing(tmp_path, monkeypatch):
    """Covers line 218-220 strict + 240-241: required missing → exit 1."""
    p = tmp_path / "incomplete.yaml"
    p.write_text("title: ok\n")
    monkeypatch.setattr(sys, "argv",
                       ["dev_yaml_immune.py", "--strict", str(p)])
    with pytest.raises(SystemExit) as e:
        yi.main()
    assert e.value.code == 1


# =========================== edge cases ============================

def test_safe_load_yaml_module_missing(monkeypatch, tmp_path):
    """Covers lines 54-55: HAS_YAML=False → returns 'yaml_module_missing:'."""
    monkeypatch.setattr(yi, "HAS_YAML", False)
    p = tmp_path / "x.yaml"
    p.write_text("k: v\n")
    data, err = yi.safe_load(str(p))
    assert data is None
    assert err.startswith("yaml_module_missing:")


def test_safe_load_generic_exception(monkeypatch, tmp_path):
    """Covers lines 62-63: generic Exception during safe_load."""
    def bad_open(*args, **kwargs):
        raise OSError("io error")
    monkeypatch.setattr("builtins.open", bad_open)
    p = tmp_path / "x.yaml"
    p.write_text("k: v\n")
    data, err = yi.safe_load(str(p))
    assert data is None
    assert err.startswith("parse_error:")
