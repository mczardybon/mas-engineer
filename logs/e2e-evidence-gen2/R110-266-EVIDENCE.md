# R110-266 EVIDENCE — Coverage Sprint for 2 banner-tool (dev_workspace)

**Date:** 2026-08-27
**Commit:** R110-266 (pushed, fe505a0)
**Type:** test
**Scope:** tests/test_r110266_workspace.py
**Targets:** tools/dev_workspace.py (1445 lines, 877 stmts, 0% covered)

## TL;DR

R110-265 proved that "banner tools" are testable via direct library
import (the sys.argv-reset pattern). R110-266 applies the same pattern
to the second of three banner-tools identified in R110-260:
`tools/dev_workspace.py` (1445 lines, 877 stmts).

This commit adds 38 tests, raising dev_workspace.py's coverage from
**0% → 23%** (+23pp), and verifies that the import pattern is clean
(dev_workspace.py has NO module-level sys.argv parsing — unlike
dev_template_generator.py, no argv-reset was needed).

## What was added

1 new test file covering 1 tool (38 tests, all green):

| File | Tool covered | Tests | Status |
|------|--------------|-------|--------|
| `tests/test_r110266_workspace.py` | dev_workspace | 38 | ✅ 38/38 |

## Coverage delta

| File | Baseline | After R110-266 | Delta |
|------|----------|----------------|-------|
| `tools/dev_workspace.py` | 0% (877/877 missing) | 23% (678/877 missing) | **+23pp** |

The 77% still missing breaks down as:
- `cmd_init` (lines 130-383): full framework init, touches GOOSE_RECIPES
  and many other module-level paths
- `cmd_install` / `_install_mas_from_workspace` / `cmd_install_mas`
  (lines 458-528, 533-549, 555-588): subprocess + GOOSE_CONFIG install
- `cmd_uninstall` / `cmd_uninstall_mas` (lines 593-621, 626-654):
  sys.exit + global state
- `cmd_rollback` (lines 659-693): interactive input()
- `cmd_add_recipe` (lines 753-754, 764-785): touches GOOSE_RECIPES
- `_write_start_sessions_script` (covered, 1 of 2 tests, missing 1)
- `_generate_agent` (lines 816-823): interactive when dst.exists
- `_validate_agent` (lines 828-892): subprocess dev_editor.py
- `_register_agent` (lines 897-925): interactive
- `_show_summary` (lines 930-955): print only
- `cmd_project_list/switch/show/delete/rename/args` (lines 970-1209):
  cwd-dependent via `Path("framework")`
- `cmd_scaffold` (lines 1273-1305): calls `_ask_*` interactive
- `cmd_install_check` (lines 1310-1379): complex scoring logic
- `main()` (lines 1382-1441): argparse dispatch

All excluded from R110-266 to keep it focused. R110-269 (planned) may
add a focused set: project-list/switch/show + install_check scoring.

## Library functions covered (16)

| # | Function | Tests | Notes |
|---|----------|-------|-------|
| 1 | `log` / `info` / `ok` / `warn` / `error` | 5 | print wrappers with emoji prefixes |
| 2 | `count_files` | 4 | dir-with-files / glob pattern / missing / empty |
| 3 | `cmd_clean` | 2 | existing-dir / missing-dir (warn) |
| 4 | `cmd_init_recovery` | 4 | copies all 5 yamls / dst-exists-noop / appends sub_recipes / idempotent merge |
| 5 | `_write_start_sessions_script` | 2 | creates + chmod+x / has validation checks |
| 6 | `_load_projects` | 3 | not-exists (creates default) / exists / corrupted |
| 7 | `_save_projects` | 2 | writes file / updates last_updated timestamp |
| 8 | `_active_project_path` | 1 | default = dev-team |
| 9 | `cmd_project_create` | 3 | fresh / exists-noop / copy_from |
| 10 | `cmd_doctor_init` | 2 | fresh init (auto-confirm) / abort on "n" |
| 11 | `cmd_remove_recipe` | 4 | in-recipes / in-framework / not-found / sub_mas |
| 12 | `cmd_status` | 3 | missing / valid / with changes.json |
| 13 | `EXCLUDE_RECIPES` constant | 1 | contains dev-mas-engineer.yaml |
| 14 | `EXCLUDE_DOCS` constant | 1 | contains mas-engineer |
| 15 | `MAS_TEMPLATE` constant | 1 | ends with recipe/template/agent_template.yaml |
| 16 | `PROJECTS_FILE` constant | 1 | equals "framework/.projects.yaml" |

Total: 38 test cases.

## Why dev_workspace.py needed NO sys.argv reset

Unlike `dev_template_generator.py` (which has module-level argparse),
`dev_workspace.py` only accesses `sys.argv` INSIDE individual `cmd_*`
functions. The module-level code is purely function/class/constant
definitions. Therefore:

```python
import sys
sys.path.insert(0, "tools")
import dev_workspace as mod  # clean import, no argv gymnastics
```

This is the simpler case — every function is testable directly as long
as the GOOSE_* module-level paths are monkeypatched to tmp_path (see
the `isolated_workspace` fixture).

## The "isolated_workspace" fixture (NEW pattern, this commit)

```python
@pytest.fixture
def isolated_workspace(tmp_path, monkeypatch):
    goose_recipes = tmp_path / "goose" / "recipes"
    goose_framework = tmp_path / "goose" / "_framework"
    goose_docs = tmp_path / "goose" / "docs"
    goose_config = tmp_path / "goose" / "config.yaml"
    tools_dir = goose_recipes / "mas-engineer-tools"
    for p in (goose_recipes, goose_framework, goose_docs, tools_dir):
        p.mkdir(parents=True, exist_ok=True)
    goose_config.write_text("version: 1.0.0\n")

    monkeypatch.setattr(mod, "GOOSE_RECIPES", goose_recipes)
    monkeypatch.setattr(mod, "GOOSE_FRAMEWORK_DIR", goose_framework)
    monkeypatch.setattr(mod, "GOOSE_DOCS", goose_docs)
    monkeypatch.setattr(mod, "GOOSE_CONFIG", goose_config)
    monkeypatch.setattr(mod, "TOOLS_DIR", tools_dir)
    monkeypatch.setattr(mod, "AGENT_REPO", goose_recipes)

    return { ... }
```

This redirects all module-level paths to tmp_path subdirs, so cmd_*
functions that touch the filesystem never pollute the real user's goose
config. Pattern is reusable for any tool that uses module-level
GOOSE_* constants.

## Library-bugs found (NOT fixed in R110-266, tracked as R110-266a)

None. All 38 tests pass on the first run, no library bugs revealed.
The tested library functions are well-designed and have sensible
fallbacks (missing files → no-op, missing config → defaults).

## Cross-tool impact

- Total new tests: +38
- tools/ coverage (global): unchanged in this single-tool test, but
  dev_workspace jumped 0 → 23%
- No regressions: 74/74 tests pass across R110-265 + R110-266 files
- `cmd_init_recovery` has a real-world quirk that's now documented: the
  function reads the recovery template from REPO_ROOT/recipe/template/
  recovery/ (via `Path(__file__).parent.parent`). This means the test
  reads the REAL recipe/template/recovery/ yamls and copies them to
  tmp_path — not isolated. The 5 yamls are stable in the repo
  (checked in 2026-08-27 R110-260 era), so this is acceptable for now.

## Banner-tool progress

| Tool | Lines | Stmts | Status | Coverage |
|------|-------|-------|--------|----------|
| `dev_template_generator.py` | 901 | 503 | ✅ R110-265 | 6% → 58% (+52pp) |
| `dev_workspace.py` | 1445 | 877 | ✅ R110-266 | 0% → 23% (+23pp) |
| `dev_im_finder_scan.py` | 1376 | 647 | ⏳ R110-267 (next) | 0% → ? |

## Open follow-ups (next commits)

- **R110-267:** dev_im_finder_scan.py (1376L, 647 stmts) — same pattern,
  no sys.argv reset needed
- **R110-268:** write_agent() + _add_sot_entry() with mocked SOT paths
  (adds back ~15% of dev_template_generator's missing coverage)
- **R110-269:** dev_workspace: project-list/switch/show + cmd_install_check
  scoring (adds back ~30% of dev_workspace's missing coverage)
- **R110-270:** Sweep the other 4 R110-260 "banner tools" (if any remain)

## Verification commands

```bash
# 38/38 single file
python3 -m pytest tests/test_r110266_workspace.py -v
# 74/74 with R110-265
python3 -m pytest tests/test_r110265_template_generator.py \
                  tests/test_r110266_workspace.py -v
# Coverage
python3 -m pytest tests/test_r110266_workspace.py --cov=dev_workspace \
                  --cov-report=term-missing
```
