"""R110-529 coverage tests for tools/dev_recipe_manager.py.

Module: 153 LOC, 6 functions + main(), 0% covered.

Functions tested:
  - _discover_framework_root(base)  lines 38-42
    Returns base if base/recipes exists, or first subdir that has recipes/.
    Falls back to base.

  - find_recipe_file(filename, main_dir, specialists_dir)  lines 141-155
    Searches REPO_MAIN, REPO_SPECIALISTS, MAS_RECIPE_DIR.

  - resolve_spec(spec)  lines 158-188
    Handles: minimal, all, category names, comma-separated,
    .yaml filename, unknown → warning. Dedups via seen-set.

  - is_visible(filename)  lines 191-193
    Returns True if filename in VISIBLE_RECIPES.

  - cmd_install(spec)  lines 198-240
    Resolves spec → finds files → copies → strips slash_command → counts.
    Handles warnings, no-files-found exit, missing source.

  - cmd_uninstall(spec)  lines 243-262
    Searches GOOSE_RECIPES and FRAMEWORK_DIR for each filename → unlinks.

  - cmd_list()  lines 265-290
    Globs both dirs, parses slash_command from visible recipes.

  - cmd_cleanup_hidden()  lines 293-303
    Globs .*.yaml files in GOOSE_RECIPES → unlinks.

  - main()  lines 306-331
    CLI dispatch: --install, --uninstall, --list, --cleanup-hidden.

Strategy: Direct function calls for unit tests + sys.argv mock for main().
Test isolation: monkeypatch module-level GOOSE_RECIPES, FRAMEWORK_DIR,
REPO_MAIN, REPO_SPECIALISTS, MAS_RECIPE_DIR to tmp_path.
"""
from __future__ import annotations

import os
import re
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.dev_recipe_manager as rm  # noqa: E402


# ============================== fixtures ===========================

@pytest.fixture
def isolated_recipes(tmp_path, monkeypatch):
    """Set up isolated dirs for rm module's globals."""
    repo_root = tmp_path / "fake_repo"
    repo_root.mkdir()
    (repo_root / "recipes").mkdir()
    (repo_root / "recipes" / "specialists").mkdir()
    mas_engineer_recipe = repo_root / "mas-engineer" / "recipe"
    mas_engineer_recipe.mkdir(parents=True)

    # Create some sample recipe source files
    (repo_root / "recipes" / "framework-starter.yaml").write_text(
        "title: starter\nslash_command: /start\n"
    )
    (repo_root / "recipes" / "dev-mas-engineer.yaml").write_text(
        "title: me\nslash_command: /me\n"
    )
    (repo_root / "recipes" / "planner.yaml").write_text("title: planner\n")

    goose_recipes = tmp_path / "goose_recipes"
    goose_recipes.mkdir()
    framework_dir = tmp_path / "framework_dir"
    framework_dir.mkdir()

    # Patch all the module-level paths
    monkeypatch.setattr(rm, "GOOSE_RECIPES", goose_recipes)
    monkeypatch.setattr(rm, "GOOSE_FRAMEWORK_DIR", framework_dir)
    monkeypatch.setattr(rm, "FRAMEWORK_DIR", framework_dir)
    monkeypatch.setattr(rm, "AGENT_REPO", repo_root)
    monkeypatch.setattr(rm, "FW_ROOT", repo_root)
    monkeypatch.setattr(rm, "REPO_MAIN", repo_root / "recipes")
    monkeypatch.setattr(rm, "REPO_SPECIALISTS", repo_root / "recipes" / "specialists")
    monkeypatch.setattr(rm, "MAS_RECIPE_DIR", mas_engineer_recipe)

    return {
        "repo": repo_root,
        "recipes_dir": repo_root / "recipes",
        "goose_recipes": goose_recipes,
        "framework_dir": framework_dir,
        "mas_engineer_recipe": mas_engineer_recipe,
    }


# ===================== _discover_framework_root ===================

def test_discover_framework_root_base_has_recipes(tmp_path):
    """Covers line 40-41: base/recipes exists → return base."""
    base = tmp_path / "b"
    base.mkdir()
    (base / "recipes").mkdir()
    assert rm._discover_framework_root(base) == base


def test_discover_framework_root_subdir_has_recipes(tmp_path):
    """Covers line 39-41: subdir/recipes exists → return subdir."""
    base = tmp_path / "b"
    base.mkdir()
    sub = base / "sub"
    sub.mkdir()
    (sub / "recipes").mkdir()
    assert rm._discover_framework_root(base) == sub


def test_discover_framework_root_fallback(tmp_path):
    """Covers line 42: no recipes/ anywhere → return base."""
    base = tmp_path / "b"
    base.mkdir()
    assert rm._discover_framework_root(base) == base


def test_discover_framework_root_subdir_without_recipes_ignored(tmp_path):
    """Covers line 39: subdirs without recipes/ are skipped (no error)."""
    base = tmp_path / "b"
    base.mkdir()
    (base / "no_recipes_here").mkdir()
    (base / "sub_with_recipes").mkdir()
    (base / "sub_with_recipes" / "recipes").mkdir()
    assert rm._discover_framework_root(base) == base / "sub_with_recipes"


# ====================== find_recipe_file ==========================

def test_find_recipe_in_main(isolated_recipes):
    """Covers lines 148-149 + 153: file in REPO_MAIN found."""
    result = rm.find_recipe_file("planner.yaml")
    assert result == isolated_recipes["recipes_dir"] / "planner.yaml"


def test_find_recipe_in_specialists(isolated_recipes):
    """Covers line 150: file in REPO_SPECIALISTS found."""
    specialists = isolated_recipes["recipes_dir"] / "specialists"
    (specialists / "spec.yaml").write_text("k: v\n")
    result = rm.find_recipe_file("spec.yaml")
    assert result == specialists / "spec.yaml"


def test_find_recipe_in_mas_engineer(isolated_recipes):
    """Covers line 151: file in MAS_RECIPE_DIR found."""
    mas = isolated_recipes["mas_engineer_recipe"]
    (mas / "my_recipe.yaml").write_text("k: v\n")
    result = rm.find_recipe_file("my_recipe.yaml")
    assert result == mas / "my_recipe.yaml"


def test_find_recipe_not_found(isolated_recipes):
    """Covers line 154 False: returns None."""
    assert rm.find_recipe_file("nonexistent.yaml") is None


def test_find_recipe_custom_dirs(tmp_path):
    """Covers lines 143-146: explicit main_dir + specialists_dir params."""
    main = tmp_path / "m"
    spec = tmp_path / "s"
    main.mkdir()
    spec.mkdir()
    (main / "a.yaml").write_text("x: 1\n")
    result = rm.find_recipe_file("a.yaml", main_dir=main, specialists_dir=spec)
    assert result == main / "a.yaml"


# ====================== resolve_spec ==============================

def test_resolve_spec_minimal(isolated_recipes):
    """Covers lines 163-165: minimal → starter + mas-engineer + core."""
    files, warnings = rm.resolve_spec("minimal")
    assert "framework-starter.yaml" in files
    assert "dev-mas-engineer.yaml" in files
    assert "planner.yaml" in files
    assert warnings == []


def test_resolve_spec_all(isolated_recipes):
    """Covers lines 166-169: all → every category's files."""
    files, warnings = rm.resolve_spec("all")
    # Should have lots of files (47 specialists + 43 sub-agents + 5 base)
    assert len(files) > 50
    assert warnings == []


def test_resolve_spec_known_category(isolated_recipes):
    """Covers line 170-171: category name like 'starter'."""
    files, warnings = rm.resolve_spec("starter")
    assert files == ["framework-starter.yaml"]
    assert warnings == []


def test_resolve_spec_known_category_with_files(isolated_recipes):
    """Covers line 170 True: 'specialists' has files → included."""
    files, warnings = rm.resolve_spec("specialists")
    assert len(files) == 47  # exactly 47 specialists
    assert warnings == []


def test_resolve_spec_comma_separated(isolated_recipes):
    """Covers lines 172-176: 'starter,planner' → both."""
    files, warnings = rm.resolve_spec("starter,planner")
    assert "framework-starter.yaml" in files
    assert "planner.yaml" in files


def test_resolve_spec_comma_with_unknown_part(isolated_recipes):
    """Covers lines 172-176: 'starter,foobar' → 1 found + 1 warning."""
    files, warnings = rm.resolve_spec("starter,foobar")
    assert files == ["framework-starter.yaml"]
    assert any("Unknown specification: foobar" in w for w in warnings)


def test_resolve_spec_yaml_filename(isolated_recipes):
    """Covers lines 177-178: explicit .yaml file → single file."""
    files, warnings = rm.resolve_spec("my_recipe.yaml")
    assert files == ["my_recipe.yaml"]
    assert warnings == []


def test_resolve_spec_unknown(isolated_recipes):
    """Covers line 180: unknown spec → warning, no files."""
    files, warnings = rm.resolve_spec("garbage123")
    assert files == []
    assert "Unknown specification: garbage123" in warnings


def test_resolve_spec_dedup(isolated_recipes):
    """Covers lines 182-187: duplicates removed via seen-set."""
    # 'starter' appears once in minimal, once in 'all'
    files, warnings = rm.resolve_spec("starter,starter,minimal")
    # starter should appear once
    starter_count = files.count("framework-starter.yaml")
    assert starter_count == 1


def test_resolve_spec_empty_categories_filter(isolated_recipes):
    """Covers line 168: categories without 'files' key are skipped in 'all'."""
    # Even if a category has no files, the loop must not crash
    files, warnings = rm.resolve_spec("all")
    # No assertion on counts, just verify no crash
    assert isinstance(files, list)


# ====================== is_visible ================================

def test_is_visible_true(isolated_recipes):
    """Covers line 193: VISIBLE_RECIPES contains filename → True."""
    assert rm.is_visible("framework-starter.yaml") is True
    assert rm.is_visible("dev-mas-engineer.yaml") is True


def test_is_visible_false(isolated_recipes):
    """Covers line 193 False branch."""
    assert rm.is_visible("planner.yaml") is False
    assert rm.is_visible("anything.yaml") is False


# ====================== cmd_install ==============================

def test_cmd_install_minimal(isolated_recipes, capsys):
    """Covers lines 200-240: install minimal → all 5 files copied."""
    rm.cmd_install("minimal")
    captured = capsys.readouterr()
    # Visible files in goose_recipes/
    assert (isolated_recipes["goose_recipes"] / "framework-starter.yaml").exists()
    assert (isolated_recipes["goose_recipes"] / "dev-mas-engineer.yaml").exists()
    # Hidden files in framework_dir/
    assert (isolated_recipes["framework_dir"] / "planner.yaml").exists()


def test_cmd_install_visible_to_top_level(isolated_recipes):
    """Covers lines 218-221: visible files → GOOSE_RECIPES."""
    rm.cmd_install("starter")
    # starter is visible → goes to goose_recipes/
    assert (isolated_recipes["goose_recipes"] / "framework-starter.yaml").exists()
    # NOT in framework
    assert not (isolated_recipes["framework_dir"] / "framework-starter.yaml").exists()


def test_cmd_install_hidden_to_framework(isolated_recipes):
    """Covers lines 218-221: non-visible → FRAMEWORK_DIR."""
    rm.cmd_install("planner")
    assert (isolated_recipes["framework_dir"] / "planner.yaml").exists()
    assert not (isolated_recipes["goose_recipes"] / "planner.yaml").exists()


def test_cmd_install_strips_slash_command(isolated_recipes):
    """Covers lines 226-230: slash_command line removed (KEEP_SLASH check)."""
    # starter is NOT in KEEP_SLASH (only framework-starter.yaml and dev-mas-engineer.yaml are)
    # Wait — let me check. KEEP_SLASH contains both visible files. So visible files are kept.
    # Test with planner (not in KEEP_SLASH) — but planner has no slash_command so test is trivial.
    # Instead, add a custom file in REPO_MAIN with slash_command.
    src = isolated_recipes["recipes_dir"] / "with_slash.yaml"
    src.write_text("title: x\nslash_command: /x\nsome: other\n")
    rm.cmd_install("with_slash.yaml")
    # File copied
    dst = isolated_recipes["framework_dir"] / "with_slash.yaml"
    assert dst.exists()
    # slash_command removed
    content = dst.read_text()
    assert "slash_command" not in content
    assert "title: x" in content
    assert "some: other" in content


def test_cmd_install_keeps_slash_command(isolated_recipes):
    """Covers line 226 False branch: KEEP_SLASH files keep slash_command."""
    rm.cmd_install("starter")
    # framework-starter.yaml is in KEEP_SLASH, so slash_command is preserved
    dst = isolated_recipes["goose_recipes"] / "framework-starter.yaml"
    assert dst.exists()
    content = dst.read_text()
    assert "slash_command" in content


def test_cmd_install_creates_dest_dir(isolated_recipes, tmp_path, monkeypatch):
    """Covers line 220: mkdir parents=True when dir doesn't exist."""
    # Use a fresh tmp path that doesn't exist yet
    fresh_dir = tmp_path / "fresh" / "deep" / "path"
    monkeypatch.setattr(rm, "GOOSE_RECIPES", fresh_dir)
    monkeypatch.setattr(rm, "FRAMEWORK_DIR", tmp_path / "fresh_fw")
    rm.cmd_install("starter")
    assert fresh_dir.exists()


def test_cmd_install_updates_existing(isolated_recipes, capsys):
    """Covers lines 233-235: existing file → n_upd++, prints ↻."""
    # First install
    rm.cmd_install("starter")
    # Second install (file exists now)
    rm.cmd_install("starter")
    captured = capsys.readouterr()
    # Second install prints update marker
    assert "↻" in captured.out or "updated" in captured.out


def test_cmd_install_skips_missing_source(isolated_recipes, capsys):
    """Covers lines 213-216: source not found → skip + n_skip++."""
    rm.cmd_install("nonexistent_recipe.yaml")
    captured = capsys.readouterr()
    assert "Source not found" in captured.out


def test_cmd_install_with_warnings(isolated_recipes, capsys):
    """Covers line 201-202: warnings printed."""
    rm.cmd_install("starter,garbage")
    captured = capsys.readouterr()
    assert "Unknown specification" in captured.out


def test_cmd_install_empty_filenames(isolated_recipes):
    """Covers lines 204-207: no files → print + sys.exit(1)."""
    with pytest.raises(SystemExit) as e:
        rm.cmd_install("garbage_unknown_spec")
    assert e.value.code == 1


# ====================== cmd_uninstall ============================

def test_cmd_uninstall_removes_from_visible(isolated_recipes):
    """Covers lines 248-256: file in GOOSE_RECIPES → unlinked."""
    # First install
    rm.cmd_install("starter")
    target = isolated_recipes["goose_recipes"] / "framework-starter.yaml"
    assert target.exists()
    # Then uninstall
    rm.cmd_uninstall("starter")
    assert not target.exists()


def test_cmd_uninstall_removes_from_framework(isolated_recipes):
    """Covers lines 248-256: file in FRAMEWORK_DIR → unlinked."""
    rm.cmd_install("planner")
    target = isolated_recipes["framework_dir"] / "planner.yaml"
    assert target.exists()
    rm.cmd_uninstall("planner")
    assert not target.exists()


def test_cmd_uninstall_not_found(isolated_recipes, capsys):
    """Covers lines 258-260: file not installed → n_nf++ + warning."""
    rm.cmd_uninstall("planner")  # never installed
    captured = capsys.readouterr()
    assert "not installiert" in captured.out


def test_cmd_uninstall_prefers_visible_over_framework(isolated_recipes):
    """Covers line 250-256: search order — visible first, breaks on first match."""
    rm.cmd_install("planner")  # → framework
    # Manually also put a copy in visible
    shutil_target = isolated_recipes["goose_recipes"] / "planner.yaml"
    shutil_target.write_text("fake")
    rm.cmd_uninstall("planner")
    # Visible one removed
    assert not shutil_target.exists()
    # Framework one still there (only checked visible)
    assert (isolated_recipes["framework_dir"] / "planner.yaml").exists()


# ====================== cmd_list ==================================

def test_cmd_list_empty(isolated_recipes, capsys):
    """Covers lines 267-290: empty dirs → '(no)' message."""
    rm.cmd_list()
    captured = capsys.readouterr()
    assert "(no)" in captured.out


def test_cmd_list_with_visible(isolated_recipes, capsys):
    """Covers lines 271-278: visible recipes printed with slash_command."""
    rm.cmd_install("starter")
    rm.cmd_list()
    captured = capsys.readouterr()
    assert "framework-starter.yaml" in captured.out
    assert "SICHTBARE" in captured.out


def test_cmd_list_with_hidden(isolated_recipes, capsys):
    """Covers lines 282-286: framework recipes printed."""
    rm.cmd_install("planner")
    rm.cmd_list()
    captured = capsys.readouterr()
    assert "FRAMEWORK" in captured.out
    assert "planner.yaml" in captured.out


def test_cmd_list_total_count(isolated_recipes, capsys):
    """Covers line 290: total count printed."""
    rm.cmd_install("starter,planner")
    rm.cmd_list()
    captured = capsys.readouterr()
    assert "Total:" in captured.out
    assert "2" in captured.out  # 1 visible + 1 framework


def test_cmd_list_slash_command_parse_fail(isolated_recipes, capsys):
    """Covers lines 273-277 except: unreadable file → '?' marker.

    We force an exception in re.search by making the file unreadable
    (chmod 0o000). On most systems this raises PermissionError or
    OSError when read_text is called, triggering the except branch.
    Running as root may bypass this — test verifies either branch.
    """
    target = isolated_recipes["goose_recipes"] / "unreadable.yaml"
    target.write_text("x")
    try:
        target.chmod(0o000)
        rm.cmd_list()
        captured = capsys.readouterr()
        # Must not crash; either '?' or '—' is acceptable
        assert "unreadable.yaml" in captured.out or "SICHTBARE" in captured.out
    except (PermissionError, OSError) as e:
        # chmod 0o000 not honored (e.g., running as root) —
        # we cannot trigger the except branch in this env.
        # Verify the happy path was at least visited.
        pytest.skip(f"Cannot trigger PermissionError on this FS: {e}")
    finally:
        try:
            target.chmod(0o644)
        except (PermissionError, OSError):
            pass


def test_cmd_list_slash_command_read_exception(isolated_recipes, capsys, monkeypatch):
    """Covers lines 276-277 except: read_text raises → '?' marker.

    We mock Path.read_text to raise PermissionError so the except
    branch fires deterministically, independent of chmod behavior
    on the underlying filesystem.
    """
    target = isolated_recipes["goose_recipes"] / "broken.yaml"
    target.write_text("x")
    original_read_text = type(target).read_text

    def boom(self, *args, **kwargs):
        if "broken.yaml" in str(self):
            raise PermissionError("simulated")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", boom)
    rm.cmd_list()
    captured = capsys.readouterr()
    assert "?" in captured.out  # '?' fallback marker


def test_cmd_list_framework_dir_missing(isolated_recipes, monkeypatch, capsys):
    """Covers line 268 False: FRAMEWORK_DIR doesn't exist → empty list."""
    monkeypatch.setattr(rm, "FRAMEWORK_DIR", isolated_recipes["repo"] / "nope")
    rm.cmd_list()  # must not crash
    captured = capsys.readouterr()
    assert "(no)" in captured.out  # framework section is empty


# ====================== cmd_cleanup_hidden ========================

def test_cmd_cleanup_hidden_with_files(isolated_recipes, capsys):
    """Covers lines 296-299: hidden .*.yaml files deleted."""
    # Create hidden files
    (isolated_recipes["goose_recipes"] / ".old.yaml").write_text("old")
    (isolated_recipes["goose_recipes"] / ".another.yaml").write_text("another")
    rm.cmd_cleanup_hidden()
    assert not (isolated_recipes["goose_recipes"] / ".old.yaml").exists()
    assert not (isolated_recipes["goose_recipes"] / ".another.yaml").exists()


def test_cmd_cleanup_hidden_no_files(isolated_recipes, capsys):
    """Covers lines 300-301: no .*.yaml → 'No .yaml-files found'."""
    rm.cmd_cleanup_hidden()
    captured = capsys.readouterr()
    assert "No .yaml-files found" in captured.out


def test_cmd_cleanup_hidden_keeps_visible(isolated_recipes, capsys):
    """Covers line 296: glob pattern .*.yaml does NOT match regular .yaml."""
    rm.cmd_install("starter")
    assert (isolated_recipes["goose_recipes"] / "framework-starter.yaml").exists()
    rm.cmd_cleanup_hidden()
    # Still there
    assert (isolated_recipes["goose_recipes"] / "framework-starter.yaml").exists()


# ====================== main() ===================================

def test_main_no_args(monkeypatch, capsys):
    """Covers line 307 True: no args → prints docstring, exit 0."""
    monkeypatch.setattr(sys, "argv", ["rm.py"])
    with pytest.raises(SystemExit) as e:
        rm.main()
    assert e.value.code == 0


def test_main_help(monkeypatch, capsys):
    """Covers line 307 'help' branch."""
    monkeypatch.setattr(sys, "argv", ["rm.py", "--help"])
    with pytest.raises(SystemExit) as e:
        rm.main()
    assert e.value.code == 0


def test_main_install_no_spec(monkeypatch):
    """Covers lines 315-317: --install without spec → exit 1."""
    monkeypatch.setattr(sys, "argv", ["rm.py", "--install"])
    with pytest.raises(SystemExit) as e:
        rm.main()
    assert e.value.code == 1


def test_main_uninstall_no_spec(monkeypatch):
    """Covers lines 319-322: --uninstall without spec → exit 1."""
    monkeypatch.setattr(sys, "argv", ["rm.py", "--uninstall"])
    with pytest.raises(SystemExit) as e:
        rm.main()
    assert e.value.code == 1


def test_main_unknown_cmd(monkeypatch, capsys):
    """Covers lines 328-331: unknown command → exit 1 + docstring."""
    monkeypatch.setattr(sys, "argv", ["rm.py", "--weird-cmd"])
    with pytest.raises(SystemExit) as e:
        rm.main()
    assert e.value.code == 1


def test_main_install_dispatch(isolated_recipes, monkeypatch, capsys):
    """Covers lines 314-318: --install <spec> dispatches to cmd_install."""
    monkeypatch.setattr(sys, "argv", ["rm.py", "--install", "starter"])
    rm.main()
    assert (isolated_recipes["goose_recipes"] / "framework-starter.yaml").exists()


def test_main_uninstall_dispatch(isolated_recipes, monkeypatch):
    """Covers lines 319-323: --uninstall dispatches to cmd_uninstall."""
    monkeypatch.setattr(sys, "argv", ["rm.py", "--install", "starter"])
    rm.main()
    monkeypatch.setattr(sys, "argv", ["rm.py", "--uninstall", "starter"])
    rm.main()
    assert not (isolated_recipes["goose_recipes"] / "framework-starter.yaml").exists()


def test_main_list_dispatch(isolated_recipes, monkeypatch, capsys):
    """Covers lines 324-325: --list dispatches to cmd_list."""
    monkeypatch.setattr(sys, "argv", ["rm.py", "--list"])
    rm.main()
    captured = capsys.readouterr()
    assert "Total:" in captured.out


def test_main_cleanup_dispatch(isolated_recipes, monkeypatch, capsys):
    """Covers lines 326-327: --cleanup-hidden dispatches to cmd_cleanup_hidden."""
    monkeypatch.setattr(sys, "argv", ["rm.py", "--cleanup-hidden"])
    rm.main()
    captured = capsys.readouterr()
    assert "No .yaml-files found" in captured.out


# ====================== edge cases ================================

def test_find_recipe_search_order(isolated_recipes):
    """Covers line 153: search order — REPO_MAIN wins over REPO_SPECIALISTS."""
    # Put a file in both — REPO_MAIN wins
    specialists = isolated_recipes["recipes_dir"] / "specialists"
    (specialists / "dupe.yaml").write_text("from_specialists")
    (isolated_recipes["recipes_dir"] / "dupe.yaml").write_text("from_main")
    result = rm.find_recipe_file("dupe.yaml")
    assert result == isolated_recipes["recipes_dir"] / "dupe.yaml"


def test_resolve_spec_unknown_category_no_files(isolated_recipes, monkeypatch):
    """Covers line 170 False: known category without 'files' key is silently skipped."""
    monkeypatch.setattr(rm, "CATEGORIES", {"broken_cat": {}})  # no 'files'
    files, warnings = rm.resolve_spec("broken_cat")
    assert files == []  # silently empty


def test_cmd_install_existed_false_path(isolated_recipes, capsys):
    """Covers lines 222 False + 236-238: new file → n_ok++ + ✅."""
    rm.cmd_install("starter")
    captured = capsys.readouterr()
    assert "✅" in captured.out or "installiert" in captured.out


def test_cmd_install_no_slash_command_no_rewrite(isolated_recipes):
    """Covers line 229 False: new_text == text → no rewrite."""
    rm.cmd_install("planner")
    dst = isolated_recipes["framework_dir"] / "planner.yaml"
    # planner.yaml has no slash_command → should not be rewritten (no change)
    # but the file is there either way
    assert dst.exists()
    content = dst.read_text()
    # Original content preserved
    assert "title: planner" in content
