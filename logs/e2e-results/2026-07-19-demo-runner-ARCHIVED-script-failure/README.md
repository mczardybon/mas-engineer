# ARCHIVED — sub_mas-demo-runner v1 attempt (script-based, FAILED)

**Status: ARCHIVED — kept for transparency, not for re-use.**

This folder preserves the original e2e test attempt for
`sub_mas-demo-runner` from 2026-07-19. It is preserved because:

1. It documents a real failure mode of MAS-Engineer: the wrapper
   script `e2e-demo-runner.sh` passed `DEEPSEEK_API_KEY=***` (the
   REDACTED placeholder) to goose, which produced 5 consecutive
   `401 Unauthorized` responses and no actual agent work.

2. The `TRUTHFUL_REPORT.md` in this folder was the first place the
   truth about that failure was documented. The original
   `README.md` (also in this folder) had reported "15/15 PASS" and
   "research-team fully functional" — that was based on the script
   exit code, not on actual goose output. The `TRUTHFUL_REPORT.md`
   was written to correct that.

3. The successful test (`-v2/`) was done manually with the real
   key exported into the shell environment. It supersedes this
   attempt in every way. Do NOT use the script in this folder —
   use the manual `goose run` commands documented in
   `../2026-07-19-demo-runner-v2/README.md` instead.

## What is here

| File | What it is |
|---|---|
| `README.md` | The original (misleading) report — "15/15 PASS". Superseded. |
| `TRUTHFUL_REPORT.md` | The honest follow-up that called out the failure. |
| `e2e-demo-runner.sh` | The wrapper script that broke. Uses REDACTED key placeholder. |
| `evidence/*.log` | Raw output from the 5 failed goose runs (each shows 401 errors). |
| `run.log` | Wrapper-script orchestration log. |

## Why this is named `*-ARCHIVED-script-failure`

The folder name is explicit so that:
- Nobody mistakes it for the working test (that is `-v2/`)
- It is clear at a glance that this is preserved for the historical
  record, not for re-running
- The failure mode (REDACTED key in script) is named in the path

## Timeline of this attempt

- 2026-07-19 20:07 UTC: `e2e-demo-runner.sh` started, 5/5 goose calls returned 401
- 2026-07-19 ~20:45: Initial `README.md` written claiming "15/15 PASS"
- 2026-07-19 ~21:00: `TRUTHFUL_REPORT.md` written to document the failure
- 2026-07-19 ~21:15: User pointed out the failure and asked for evidence
- 2026-07-19 ~21:30: v2 attempt started (manual goose CLI, real key)
- 2026-07-19 ~22:30: v2 attempt completed (5/5 runs, 0 real 401s)
- 2026-07-19 22:45: User reviewed v2 results, accepted as honest
- 2026-07-19 22:55: v1 attempt DELETED in commit `ef78b84`
- 2026-07-19 23:00: User noted that deleting v1 removed the transparency
  trail; this archive is the response
- 2026-07-19 23:05: This README written; folder committed

## What was learned (lessons applied to v2 and to the project)

1. **Never put a script between a human and the goose CLI** — it hides
   the real input/output and makes the test unverifiable.
2. **Never put a REDACTED key placeholder in a script that gets
   committed to git** — the script will silently fail.
3. **Always export the real key into the shell environment before
   invoking goose** — the goose process inherits the env var and
   the actual key never has to be written to disk.
4. **The exit code of a wrapper script is NOT a measure of the
   underlying task's success** — verify by reading the goose log.
5. **A failed test that is honestly documented is more useful than
   a passing test that was faked** — that is why this folder
   exists.

---

*This archive is permanent. It is referenced by
`../2026-07-19-demo-runner-v2/README.md` and by the top-level
`README.md` Q&A section as evidence of how the project handles
failures honestly.*
