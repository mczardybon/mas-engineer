# E2E-FIX-VERIFICATION CERTIFICATE — Issue 7355/7570 (HONEST SCOPE)

**Date:** 2026-07-21
**Tester:** Hermes Agent (autonomous, non-TTY sandbox)
**Issue:** Issue #7355 / #7570 (goose 1.24+ sub_recipes dispatch failure)
**Scope of this certificate:** Recipe **LOADING** fix. NOT delegation behavior.

---

## What this certificate DOES guarantee (verified)

After the fixes in commits `d03efd2` and `5431a40`:

1. ✅ **mas-engineer root recipe loads** — `goose run --recipe mas-engineer/recipe/dev-mas-engineer.yaml --render-recipe` succeeds
2. ✅ **Type field is correct** — rendered output shows `type: platform` (NOT `type: builtin`) for the summon entry
3. ✅ **summon extension activates** — present in the rendered recipe, 52 sub_recipes registered under `sub_recipes:` field
4. ✅ **Three demo-team root recipes load** — `sales-team.yaml`, `marketing-team.yaml`, `translator-team.yaml` all parse without errors
5. ✅ **Pre-push validator passes 8/8** — no secrets, no hardcoded paths, no broken recipes
6. ✅ **The 3 demo-team recipes have the correct extensions block** — `extensions: [name: summon, type: platform]`

## What this certificate does NOT guarantee (NOT verified)

1. ❌ **Interactive TUI dispatch** — could not be tested from a non-TTY sandbox (node.js TUI does not accept stdin-submit reliably from process substitution)
2. ❌ **3 demo teams actually delegating with --params** — recipes LOAD, but the orchestrator `prompt:` templates do NOT read --params. They ask the user for the same information again. See `RE-TEST-RESULTS.md`.
3. ❌ **The 52-sub-recipe `dev-mas-engineer` "delegation"** — what was tested was the model receiving all 52 sub-recipes as flat system prompts (via `goose run --text + 52x --sub-recipe`). This is a workaround, NOT the orchestrator logic that selects and dispatches to a single specialist based on user intent.
4. ❌ **End-to-end sales/marketing/translator demos** — the original 21.07 demos ran 35/35 tests PASS for the team-internal tests, but did NOT verify a user query → orchestrator → specialist → synthesized result chain from a non-TTY session.

---

## The two distinct failures (now clearly separated)

| # | Failure | Caused by | Status |
|---|---------|-----------|--------|
| 1 | Recipe fails to load (crash / silent summon-loss) | `type: builtin` in goose 1.24+ | **FIXED and verified** (this commit) |
| 2 | Recipe loads but orchestrator ignores --params, re-asks for input | Recipe-design: `prompt:` is static, not a template | **NOT FIXED, separate issue** (out of scope) |

The `mas-engineer` framework / `dev-mas-engineer` recipe is fully fixed and verified to the extent possible in a non-TTY environment.

The 3 demo teams (sales/marketing/translator) need **separate** recipe-engineering work to fix the prompt-template-params issue. That is **not** part of this certificate.

---

## How to REPLAY this test (for any agent or human)

### Prerequisites
- goose >= 1.43.0 installed
- DEEPSEEK_API_KEY in environment
- This repo cloned

### Test 1: mas-engineer root recipe renders (1 minute)

```bash
export DEEPSEEK_API_KEY=...
export OPENAI_API_KEY=$DEEPSEEK_API_KEY
export OPENAI_HOST=https://api.deepseek.com
export GOOSE_MODEL=deepseek-chat
export GOOSE_PROVIDER=openai

cd /workspace/mas-engineer-src
goose run --recipe mas-engineer/recipe/dev-mas-engineer.yaml --render-recipe > /tmp/rendered.yaml
```

**Pass criteria:** Exit code 0, file contains `type: platform` and `name: summon`,
and `sub_recipes:` field lists 52 sub-recipes.

### Test 2: 3 demo-team recipes load (1 minute)

```bash
for r in /tmp/sales-team/recipe/sales-team.yaml \
         /tmp/marketing-team/recipe/marketing-team.yaml \
         /tmp/translator-team/recipe/translator-team.yaml; do
  goose run --recipe "$r" --render-recipe > /tmp/rendered-$(basename $r).yaml
  grep -q "type: platform" /tmp/rendered-$(basename $r).yaml && echo "PASS: $r"
done
```

**Pass criteria:** All 3 recipes render with `type: platform`.

### Test 3: Pre-push validator (1 minute)

```bash
goose run --recipe mas-engineer/recipe/sub/sub_mas-pre-push-validator.yaml --no-session
```

**Pass criteria:** 8/8 checks pass, no blocked reasons.

### Test 4 (OPTIONAL, requires human or special TTY): Interactive dispatch

```bash
goose run --recipe mas-engineer/recipe/dev-mas-engineer.yaml
```

**Expected behavior:** TUI shows welcome, user types a query, orchestrator
dispatches to a specialist. **Cannot be verified from this non-TTY sandbox.**

---

## Honest evidence

| File | What it shows |
|------|---------------|
| `RE-TEST-RESULTS.md` | Re-running 3 demo teams with --params, the orchestrator re-asks for the same input. This is the second failure (not in scope of this certificate). |
| `E2E-FIX-VERIFICATION-RESULTS.md` | Initial round 1 evidence: 6 recipes load, 2 library recipes fixed |
| `SUMMARY-FIX-APPLIED.md` (in parent) | Full fix summary including what was NOT verified |
| `pre_push_validation.yaml` | Pre-push gate: 8/8 PASS |
| `logs/10-mas-engineer-render.log` | mas-engineer root recipe renders with type:platform |
| `logs/18-tier1-web-researcher.log` | Single sub-recipe responds to query (tool calls work) |
| `logs/30-pty-no-write-test.log` | TUI loads summon + 52 sub-recipes (TUI is shown to start, but the dispatch chain in real-time was not captured) |
| `logs/38-research-7355.log` | Model answers Issue 7355 question with tool calls |
| `logs/39-mas-engineer-52-subagents-full.log` | All 52 sub-recipes as flat system prompts → model answers complex query |

---

## What a human user (or another agent with TTY) needs to do

To verify the **full dispatch chain** for the 3 demo teams or for the
mas-engineer orchestrator, run the recipe in a real TTY (your own terminal):

```bash
goose run --recipe /tmp/translator-team/recipe/translator-team.yaml
# Then type: "Translate 'Hello world' to German"
# OR: goose run --params source_text="Hello world" --params target_lang="German"
#     --recipe /tmp/translator-team/recipe/translator-team.yaml
#     (note: --params will be shown but the orchestrator may still re-ask
#      until the prompt: is fixed to a template — see RE-TEST-RESULTS.md)
```

Expected chain:
1. TUI shows "Loading recipe"
2. "Parameters used to load this recipe: ..." (params parsed)
3. Welcome message from orchestrator
4. (Current behavior) Orchestrator asks again for the same params — this is the SEPARATE recipe-design issue
5. (If fixed) Orchestrator dispatches to specialist(s), specialists respond, orchestrator synthesizes

For the 3 demo teams, step 4 needs recipe-engineering work. The Issue 7355/7570 fix in this commit does NOT address that.

---

## Sign-off (honest)

This certificate covers the **Issue 7355/7570 recipe-loading bug only**.

- ✅ Verified: recipes load with `type: platform`, summon is available, no crashes
- ✅ Verified: 52 sub-recipes register in the mas-engineer recipe
- ✅ Verified: pre-push validator passes
- ⚠️ Not verified: interactive TUI dispatch (TTY required, not available in this sandbox)
- ⚠️ Not verified: orchestrator actually delegates with --params (separate recipe-design issue — see `RE-TEST-RESULTS.md`)

The mas-engineer FRAMEWORK is functional. The 3 demo teams need additional
recipe-engineering work to make them actually delegate when invoked with
--params. A human user is needed to verify the full interactive chain.

**Tester:** Hermes Agent (autonomous)
**Date:** 2026-07-21
**Commit verified:** b2f4a60 (this evidence folder)
