# R110-419 — `dev_im_finder_scan` O(L*F) explosion in `.mase/` walk

## Goal

Unified `python3 -m tools.dev_im_finder_scan scan` was effectively
hanging (>5min timeout) even though only ~21 SD-test findings
existed. Root cause: the spec_drift check walks `.mase/` as a
source-of-truth root alongside `recipe/`, `tools/`, `docs/` — and
for each literal it scans every file in every subdir.

The `.mase/mcp/` subdir alone contains **3509 files (~27MB)**
(mostly `node_modules` artifacts from MCP server installs). For ~21
SD-test literals this was ~73K file opens.

## Fix (1 file, +6 lines, 8bdd5a6)

`tools/dev_im_finder_scan_lib.py` — `_SD_DATA_DIRS` extended:

```python
_SD_DATA_DIRS = frozenset({
    'pipeline', 'workflow_runs', 'phoenix_logs', 'checkpoints',
    'mq', 'backups', 'coverage', 'dashboards', 'im', 'recovery',
    # R110-419: added to prevent O(L*F) explosion in check_spec_drift
    'mcp', 'skills', 'knowledge', 'templates',
    'pre_check_benchmark', 'config', 'commits',
})
```

**Kept in scope (real source-of-truth):** `directives`, `rules`.

## Verification

| Metric                           | Before        | After         |
|----------------------------------|---------------|---------------|
| Unified `dev_im_finder_scan scan`| >5min (hang)  | 96s           |
| SD-test findings                 | 21            | 21 (same)     |
| `pytest tests/test_dev_im_finder_scan_lib.py` | 75 passed | 75 passed |

## Why these specific dirs

- **mcp/**: 3509 files / 27MB (MCP server node_modules) — biggest win
- **skills/, knowledge/, templates/**: framework-mirror copies of
  the same source-of-truth in `~/.claude/skills/`, `~/.hermes/skills/`,
  etc. Drift between mirror and source is normal; not a real spec
  violation
- **pre_check_benchmark/, config/, commits/**: ephemeral runtime
  artifacts and historical commit logs, not source-of-truth

## Related

- R110-279 — original `SD-test_zz_r110279_synth-1` finding that this
  fix unblocks (the synth-literal scan path)
- R110-418 — pytest-batch-strategy skill (orthogonal: about reducing
  per-test cycle time, not per-scan file count)
