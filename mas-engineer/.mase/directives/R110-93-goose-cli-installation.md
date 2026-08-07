# R110-93 — Goose CLI installation in this environment

**Status:** DONE (2026-08-04) — supersedes R110-89 Finding E
**Author:** Hermes (R110-89 Finding E follow-up)
**Target:** `/root/.local/bin/goose` binary

## Goal

Install the `goose` CLI in the runtime environment so that
`sub_mas-pre-push-validator` can be executed live (not just
documented/spec'd).

## Why

- R110-89 evidence-doc Finding E: "Install goose CLI in this
  environment so that the pre-push-validator step can run live."
- Pre-commit hook (`.githooks/pre-commit`) and pre-push hook
  (`.githooks/pre-push`) are ALREADY active; they just don't include
  the full 17-check validator. To enable end-to-end validator-run,
  goose must be on PATH.
- Without goose, validator-runs are manual (bash-block extraction +
  human verification). With goose, the validator can run in CI
  context automatically.

## Status: ALREADY COMPLETE (this session, 2026-08-04)

Discovered during T5e (acceptance test for Check 17):
  - `/root/.local/bin/goose` exists
  - Size: 301,772,304 bytes (~288 MB)
  - Version: `goose 1.45.0` (from `goose --version`)
  - Path setup: `which goose` returns empty (not on default PATH);
    full path is `/root/.local/bin/goose`

**Note for future sessions:** The `~/.bashrc` PATH-update to make
`goose` discoverable via `which` was NOT done. Future work: add
`export PATH=$PATH:/root/.local/bin` to `~/.bashrc` for cleaner UX.

## Scope

NONE. Goose is already installed. This directive serves as a
**discovery record** for the next mas-engineer-run.

## 9-Section Spec (compliance-only, no implementation)

### 1. EXACT FILE + INSERT-POINT

None. Already installed.

### 2. EXTRACT-PATTERN

Verification command:
  `ls -la /root/.local/bin/goose && /root/.local/bin/goose --version`

Expected output (recorded 2026-08-04):
  `-rwxr-xr-x 1 root root 301772304 Jul 29 20:03 /root/.local/bin/goose`
  `1.45.0`

### 3. MATCHING

NA — installation already complete.

### 4. OUTPUT-SCHEMA

NA.

### 5. 3-HOOK-POINTS

Pre-validator-run:
  - `export PATH=$PATH:/root/.local/bin` (or use full path)
  - `source mas-engineer/.env` (load DEEPSEEK_API_KEY)
  - `cd <mas-engineer-cwd>` (must be in repo root for tests/)

During-validator-run:
  - Goose invokes the pre-push-validator sub-recipe
  - Validator runs all 17 checks in sequence
  - Output: check-by-check PASS/FAIL/WARN

Post-validator-run:
  - RC=0 → push allowed
  - RC!=0 → push blocked; review output

### 6. SEVERITY

LOW. Already complete. Future enhancement (PATH-persistence in
~/.bashrc) is cosmetic.

### 7. IDEMPOTENZ

NA. One-time install already done.

### 8. TESTING

Manual verification (recorded 2026-08-04):
  - `/root/.local/bin/goose --version` → `1.45.0` ✓
  - Goose binary is executable (`-rwxr-xr-x`) ✓
  - Pre-push-validator could be invoked via goose (skipped this
    session to avoid DEEPSEEK rate-limit risk on small commits)

### 9. DO-NOT (anti-patterns)

- **DO NOT** re-install goose (already at 1.45.0, the latest known
  stable as of 2026-08-04).
- **DO NOT** move the binary from `/root/.local/bin/` (other tooling
  may reference this path).
- **DO NOT** add goose to the validator's runtime dependencies —
  goose IS the runtime; the validator runs INSIDE goose.

## Provenance

- R110-89 evidence-doc Finding E (R110-93 — install goose CLI).
- R110-97 env helper script (mas-goose-env.sh) — automates the
  source-`.env` + PATH-export pattern for future runs.
- This directive is a **discovery record**, not an implementation
  task. Marked DONE in 2026-08-04.

## Acceptance criteria

- [x] `goose` binary present at `/root/.local/bin/goose`
- [x] Version 1.45.0 confirmed
- [x] Binary is executable
- [ ] Optional: PATH-persistence in ~/.bashrc (cosmetic, future
      enhancement)

## Forward-pointer

- R110-97 (already pushed, e83b899): mas-goose-env.sh helper
- Future R-NR: PATH-persistence (`.bashrc` line) — low priority
