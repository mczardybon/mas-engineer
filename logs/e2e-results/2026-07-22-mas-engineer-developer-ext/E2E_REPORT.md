# E2E TEST RESULTS — 2026-07-22 mas-engineer with developer extension

**Tester:** Hermes (per user: "mas-engineer + sub-agents mit bash ausstatten")
**Test method:** Real interactive goose CLI runs via pty, with bash
verification of file existence and mtime.

## ROOT CAUSE (verifiziert)

Mas-engineer recipe (`/root/.config/goose/recipes/dev-mas-engineer.yaml`)
deklarierte **NUR `summon` als platform extension** — kein `developer`.

Resultat: mas-engineer hatte nur 2 tools: `delegate` + `load`. Es konnte
KEINE dateien schreiben, KEIN bash ausführen, NICHTS.

## FIX (verifiziert)

Patch zu `extensions: - name: summon - name: developer` in:
1. `/root/.config/goose/recipes/dev-mas-engineer.yaml` (active config)
2. `/workspace/mas-engineer-src/mas-engineer/recipe/dev-mas-engineer.yaml` (source)

Beide files waren unterschiedlich (eine war copy, andere symlink im
recipes/mas-engineer/ subfolder).

**Test:** Simple prompt "create /tmp/mas_test_static.txt with 'hello
from mas-engineer'":
- BEFORE fix: mas-engineer said "ich habe nur delegate und load"
- AFTER fix: mas-engineer used `shell` + `text_editor`, file exists
  (23 bytes, correct content), read back OK

## E2E TEST 1: research-team demo build (verifiziert)

**Run:** 11 min real pty session with prompt "build the research-team
demo at /tmp/research-team-v2/ with 5 agents, orchestrator, dashboard,
14 test cases. Run all 14 tests. Report PASS/FAIL with file evidence."

**Mas-engineer DID:**
1. Created `/tmp/research-team-v2/` with `.gitignore`, `project.yaml`,
   `workflows.yaml`, `00-GUIDELINES.md`
2. Created 5 sub-agent recipes: `fact-extractor.yaml`,
   `web-searcher.yaml`, `source-verifier.yaml`, `synthesizer.yaml`,
   `health-monitor.yaml`
3. Created orchestrator `research-team.yaml` with sub_recipes section
4. Created `research-team-e2e.yaml`
5. Built `tests/test_cases.yaml` (14 E2E test cases)
6. Built `tests/test_agent_syntax.py` (14 pytest tests)
7. Built `tests/run_test_cases.py` (test runner)
8. Generated `tests/test_results.json`
9. Built `dashboard.html` (8.5KB) and `.mas/mcp/dashboard.html`
10. Built `.mas/mcp/server.js` + npm packages
11. Wrote `workflows.yaml`, `BP-CHECKLIST.md`

**Real verification (Hermes ran):**
- `pytest tests/test_agent_syntax.py -v` → **14/14 PASSED in 0.04s**
- `cat tests/test_results.json` → 14/14 cases, 88 checks, all_passed:true
- File count: 23 files, 58.6 KB on disk
- All mtimes = 2026-07-22 02:28-02:35 (today)

## E2E TEST 2: 3 demo teams params-fix (verifiziert mit caveat)

**Run:** 4 min real pty session with prompt "fix the 3 demo teams'
orchestrator recipes so they actually use --params instead of asking
the user for the same info again."

**Mas-engineer DID:**
1. Diagnosed correctly: "orchestrator fragt nach text/sprache"
2. Proposed fix: add `params:` section + "Parameter FIRST, Frage SECOND"
3. Implemented (R01 confirmation: asked first, then proceeded)
4. Wrote 3 new sub-orchestrator files:
   - `/tmp/sales-team/recipe/sub/sales-orchestrator.yaml` (4515 bytes)
   - `/tmp/marketing-team/recipe/sub/marketing-orchestrator.yaml` (4603 bytes)
   - `/tmp/translator-team/recipe/sub/translator-orchestrator.yaml` (3183 bytes)
5. All 3 files have `params:` section + "## Parameter Handling (IMPORTANT)"

**Caveat (gefunden durch echten test):**
The fix is **INCOMPLETE** — it added text instructions but no
`{{ query }}` Jinja template. When the user runs the recipe with
--params, the LLM can SEE the params (recipe shows "Parameters used:
query: Find AI startups") but **does NOT have a template to inject
them into the prompt** — so it still asks the user.

**Real verification (Hermes ran):**
- `goose run --recipe sales-orchestrator --params "query=Find AI startups"
  --params "lead_type=AI" --params "industry=fintech"`
- Recipe loaded, showed "Parameters used: query: Find AI startups"
- BUT agent responded: "I see you've loaded me as Sales Orchestrator.
  However, no `query` parameter was provided"

The fix is half-complete: the agent needs the params **templated into
the prompt via Jinja** (`{{ query }}`), not just declared in `params:`.

## BOTTOM LINE

**Mas-engineer + developer extension = MAJOR WIN.** It can now:
- Build real frameworks on disk (23 files in 11 min)
- Run and verify its own tests (14/14 pytest pass, 14/14 E2E pass)
- Diagnose and propose fixes for real bugs
- Write code that compiles and runs

**Open issue:**
- Sub-agent recipes need `{{ param_name }}` templates in `prompt:`
  block, not just `params:` declaration + text instructions
- This is the "params actually used" problem from the original test
  — mas-engineer proposed a fix, implemented it, but the fix is
  incomplete

## NEXT STEP

To complete the demo-teams fix, the recipes need a Jinja template
in the `prompt:` field, e.g.:

```yaml
params:
  query:
    type: string
prompt: |
  Process this sales query: {{ query }}
  Lead type: {{ lead_type }}
  Industry: {{ industry }}
```

Mas-engineer can do this itself — it just needs the right instruction.
