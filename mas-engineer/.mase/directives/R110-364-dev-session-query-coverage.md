---
sprint: R110-364
topic: dev_session_query.py coverage r1 — 12 public functions, 0% → 50-70% (264 stmts, +30-50 tests)
status: planned
---

# R110-364 — dev_session_query.py coverage r1: 0% → 50-70%

## Goal

Push `tools/dev_session_query.py` coverage from **0% to 50-70%** with
**30-50 NEW tests** targeting the 12 public functions. File is 264 stmts,
512 lines, completely uncovered despite existing imports in
`test_sub_mas_im_session_reader.py` (which only imports the module for
side-effects, doesn't call any public function).

## Inventory data (from R110-323, re-verified 2026-09-07 via /tmp/r110364-map.py)

- File: `tools/dev_session_query.py` (264 stmts, 0% covered, 264 missing, 8 excluded)
- Existing test surface: 6 imports in `test_sub_mas_im_session_reader.py` (just `import` for
  side-effect), 1 smoke test in `test_r110310_e2e_evidence.py` (subprocess)
- No function-level coverage of the 12 public functions — entire public API
  is at 0% per .coveragerc

## 12 public functions to test (file 1-512)

| L    | Function | What it does | Testability |
|------|----------|--------------|-------------|
| 43   | `get_db_path() -> str` | Returns path to session DB under `${GOOSE_DATA_DIR:-~/.local/share/goose}/sessions/sessions.db` | ✅ env-mock |
| 47   | `get_copy_path() -> str` | Returns path to .copy session DB | ✅ env-mock |
| 89   | `read_goosehints_tag(workspace: str) -> str` | Parses .goosehints for GOOSE_SESSION_TAG value | ✅ tmp_path |
| 105  | `query_sessions(db, where, limit) -> list[dict]` | Runs SQL query against sessions table | ✅ sqlite fixture |
| 125  | `has_messages_table(db) -> bool` | Checks if `messages` table exists in DB | ✅ sqlite fixture |
| 138  | `extract_messages_patterns(db, session_ids) -> dict` | Extracts message patterns (tools, errors, recipes) from sessions | ✅ sqlite fixture |
| 219  | `aggregate_metrics(sessions) -> dict` | Aggregates session-level metrics (success rate, avg duration, etc.) | ✅ pure function |
| 256  | `find_stale_sessions(db, days) -> list[dict]` | Finds sessions older than N days | ✅ sqlite fixture |
| 276  | `analyze(workspace, limit, include_messages) -> dict` | Top-level analyze command — 3-level project filter | ✅ tmp_path + sqlite |
| 410  | `show_db_info() -> dict` | Returns DB path, size, mtime, table count | ✅ env-mock |
| 440  | `find_stale(workspace, days) -> list[dict]` | Workspace-aware stale finder | ✅ tmp_path + sqlite |
| 451  | `print_usage() -> None` | Prints help text | ✅ capsys |
| 455  | `main() -> int` | CLI dispatcher (argparse) | ✅ capsys + monkeypatch |

## Target

- 30-50 NEW tests
- Coverage: 0% → 50-70% (conservative — `analyze` and `main` have many branches)
- Wall-clock: <5s
- Per-test @pytest.mark.timeout(30) default; integration tests get @pytest.mark.timeout(120) if any

## Why 50-70% not 100%

- `analyze()` (L276-409) is the 134-stmt main code path with 5 status branches
  (no_db, no_sqlite, no_sessions, no_workspace, success) and 3-level project
  filter. Each branch needs 1-2 tests. ~30 stmts are status-branches with
  1-line returns that are hard to cover exhaustively.
- `main()` (L455-512) is the CLI dispatcher. 5 subcommands. Many branches
  per subcommand. ~30 stmts are argparse-side error paths.
- `query_sessions()` SQL builder has 5 fields × 3 filter levels = many
  combinations. Conservative = test common paths, not all field×level combos.

## Sandbox pattern (R110-347 inheritance)

For functions that touch the filesystem or env (`get_db_path`, `get_copy_path`,
`show_db_info`, `analyze`, `find_stale`, `read_goosehints_tag`):

```python
def test_xxx(monkeypatch, tmp_path):
    # Set env BEFORE exec_module
    monkeypatch.setenv("GOOSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SCAN_SCOPE", str(tmp_path))  # if applicable
    monkeypatch.chdir(tmp_path)
    # ... test code ...
```

For DB-touching functions (`query_sessions`, `has_messages_table`,
`extract_messages_patterns`, `find_stale_sessions`):

```python
import sqlite3
def test_xxx(tmp_path):
    db = tmp_path / "sessions.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE sessions (name TEXT, working_dir TEXT, ...")
    # ... insert fixture rows ...
    conn.commit()
    conn.close()
    # ... call function ...
```

## Files (planned)

- `mas-engineer/tests/test_dev_session_query_r110364.py`
  (NEW, ~600-800 lines, 30-50 tests, 12 TestXxx classes matching the 12 functions)

## Constraints

- DO NOT touch the existing `test_sub_mas_im_session_reader.py` (it has its
  own purpose — module-side-effect verification)
- DO NOT change `dev_session_query.py` source (this is a test-only push)
- DO use `tmp_path` for ALL filesystem state (no hardcoded /tmp paths)
- DO use `monkeypatch.setenv("GOOSE_DATA_DIR", ...)` BEFORE importing the
  module functions that read the env at call-time
- DO use `sqlite3` directly for DB fixtures (NOT a Goose session-DB dump)

## Verification

```bash
# Should PASS in <5s
python3 -m pytest tests/test_dev_session_query_r110364.py \
  -p no:cacheprovider --no-header -q --timeout=30

# Coverage delta
python3 -m pytest tests/test_dev_session_query_r110364.py \
  tests/test_sub_mas_im_session_reader.py \
  -p no:cacheprovider --no-header -q --timeout=30 \
  --cov=tools --cov-report=term 2>&1 | grep dev_session_query
# Expected: 50-70% (vs current 0%)

# Honest fall-back: if analyze() or main() prove harder to cover than
# expected, document the gap and target 40% as the r1 floor
```

## Refs

- R110-347 (sandbox pattern, the model for env+chdir isolation)
- R110-361/362/363 (the coverage-push r1 series for im_finder_scan + workspace)
- R110-323 (inventory, but file coverage claim was 0% — verified via
  /tmp/r110364-map.py 2026-09-07, real 0% on 264 stmts)
- R110-310 (e2e smoke test for sub_mas-im-session-reader, the only existing
  touch-point — runs as subprocess, doesn't measure function-level coverage)
- Skill: mas-engineer-coverage-push-workflow

## Forward-pointer

After R110-364 the queue has 6 more 0%-files (dev_self_auditor, dev_spec_invariant,
dev_parallel, dev_observer, dev_architect, dev_dashboard_refresh). R110-365+ can
pick any of these — the sandbox pattern is now battle-tested across 3 sprints.
