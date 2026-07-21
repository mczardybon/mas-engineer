# E2E test after Hermes-applied fix — 2026-07-21

**Goal:** Verify the 2 bugs from the previous e2e test (e2e-results/2026-07-21-mas-e2e-full/)
are gone after Hermes applied fixes to mas-engineer.

**Honest framing:** mas-engineer could not fix itself autonomously (see
`e2e-results/2026-07-21-mas-self-fix-attempt/`). Per user instruction
"ja — but be transparent about it", I (Hermes) applied the fix to
mas-engineer myself and ran this re-test. This commit documents the
fix AND the re-test evidence, and labels Hermes as the author of the
fix in the commit metadata.

## What was changed in mas-engineer

Two files modified:

  1. `mas-engineer/recipe/instructions/sub_mas-self-auditor.md` (10648 bytes)
     - Added a "Tool limitations (added 2026-07-21)" section that
       explicitly states the agent emits its report as the final
       assistant message, not as a file write.
     - The "Output" section was rewritten to make the
       wrapper-captures-final-message flow explicit.

  2. `mas-engineer/recipe/sub/sub_mas-self-auditor.yaml`
     - The `instructions:` field no longer asks the LLM to "load" the
       external file via the `load` tool (which doesn't auto-resolve
       file paths — goose `load` only resolves recipe names).
     - Three correct loading paths are documented: (a) `load` with a
       registered source name, (b) `delegate` to dev-mas-engineer to
       run `python3 tools/dev_self_auditor.py`, (c) operate from the
       prompt-level instructions (sufficient for an LLM-only audit).
     - The `prompt:` field got an "Output mode (updated 2026-07-21)"
       section making the wrapper-captures-final-message flow explicit.

NOT modified (per R04):
  - `mas-engineer/recipe/sub/sub_mas-general-improver.yaml` — only
    mas-engineer itself can edit this.

## Re-test results (real goose CLI calls, post-fix)

### Test 1 — self-auditor q-test (evidence/04-q-test-self-auditor.log, 13801 bytes)

Asked self-auditor to perform a normal audit and confirm understanding of
its own tool limits. It did 8 checks, then emitted this final report:

  "R10 CORONASHIELD: No YAML written without syntax check
   (no YAML written at all)
   Honest answer: No, I did not write the file. The wrapper does that."

**Result:** the "wrapper does that" honesty is now in the agent's
output. The fix works at the LLM-prompt level.

### Test 2 — self-auditor after fix v1 (evidence/02-retest-v1-self-auditor.log, 12636 bytes)

self-auditor performed a full audit and flagged:

  "Check 8 — Tool Access Audit:
   shell/exec tools: Not available
   filesystem read tools: Not available
   file write tools: Not available
   → No filesystem access — audit depth limited"

**Result:** the agent now openly reports its tool limits instead of
fabricating findings from a wrong working directory.

### Test 3 — load test (evidence/03-load-test.log, 3977 bytes)

Asked self-auditor to load the external instructions file. It tried
multiple `load` source names and `delegate` calls, all failed
because goose's `load` tool only resolves registered recipe names,
not arbitrary file paths. The agent acknowledged the failure cleanly
instead of claiming the file was missing.

**Result:** the false-positive "file not found" from the original
e2e test is now correctly reported as "load mechanism limitation".

## New finding: delegation targets not registered

The 2nd test surfaced a NEW issue: 10 delegation targets referenced
in the self-auditor recipe (generic-init, bootstrap, framework-scanner,
general-improver, agent-guardian, monitor-*, recovery-*,
web-researcher, recipe-designer, demo-runner) are not registered as
loadable goose sources. The recipe can name them, but cannot
actually invoke them.

This is a separate architectural concern and is documented in the
log but NOT fixed in this commit. It belongs in a future mas-engineer
design discussion (likely needs a "delegate-with-tool-extension"
pattern).

## Verification

```
YAML syntax check:  ✅ mas-engineer/recipe/sub/sub_mas-self-auditor.yaml
                      valid (Python yaml.safe_load)
File size check:    ✅ 10648 bytes (instructions file)
                    ✅ self-auditor.yaml modified
Evidence:           ✅ 4 .log files in this evidence/ dir
                    ✅ 1 from pre-fix (q-test is the first post-fix
                       test that actually completes successfully)
```

## Transparency statement

This fix was applied by Hermes (the operator) because mas-engineer
could not fix itself. R04 is preserved (general-improver.yaml was
not modified). The commit message and this README explicitly name
Hermes as the author so the provenance is auditable.

If the user prefers the alternative paths listed in
`e2e-results/2026-07-21-mas-self-fix-attempt/README.md`, this commit
can be reverted and the chosen path taken instead.
