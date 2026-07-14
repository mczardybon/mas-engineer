# Lessons Learned — MAS Engineer Evolution

**Purpose:** Codify hard-won knowledge from mas-engineer development sessions so future
agent runs do not repeat the same mistakes.

**Audience:** Every im-* agent (im-finder, im-rank, im-designer, im-validator) and
the general-improver orchestrator. Read this file before proposing changes.

**Last updated:** 2026-07-14 (commit 574596c)

---

## L01 — Always check if Goose already provides a native mechanism

**Date:** 2026-07-14
**Severity:** CRITICAL (caused architectural dead-end)
**Discovered by:** User mczardybon (manual review)

### Symptom
The sub_mas-goose-expert agent was defined in `recipe/sub/sub_mas-goose-expert.yaml`
but **NEVER invoked by any upstream im-* agent** (orphan agent, 0% utilization rate).
im-designer proposed adding a custom "load on demand" mechanism to agents when
Goose already provides the `summon` MCP extension for exactly that use case.

### Root cause
- The static "GOOSE-CHECK (Limits check)" in im-designer only validated
  numerical limits (timeout 60-3600, max_steps 10-500).
- It did NOT validate against Goose's native architecture.
- No upstream agent had `extensions: [summon]` so the expert could not
  technically be delegated to even if someone tried.

### Fix applied
1. Added `extensions: [summon]` to all 5 im-* agents + general-improver.
2. Added STEP 0.5 with mandatory summon of sub_mas-goose-expert for
   types A*/B*/D*/MM*/JJ*/S*/HH*/LL*.
3. Defined R11 GOOSE-EXPERT CONSULTATION in master-constitution.yaml.
4. Attached verdict (CONFORM/RESTRICTED/NOT POSSIBLE) to each finding/patch.

### Rule for future agents
> Before proposing ANY new mechanism, mechanism, or pattern:
> 1. Run sub_mas-goose-expert with the proposed mechanism description
> 2. Ask: "Does Goose already provide this natively?"
> 3. If yes: use the native mechanism, do not reimplement.
> 4. If no: proceed with the proposed mechanism, attach the verdict.

### Reference
- Goose summon extension: https://goose-docs.ai/docs/mcp/summon-mcp/
- Related tools: `tools/dev_goose_expert_check.py` (auto-detects
  "missing mechanism" findings that may already exist in Goose)

---

## L02 — Orphan agents stay orphan without explicit trigger

**Date:** 2026-07-14
**Severity:** HIGH (architectural pattern)

### Symptom
A sub-agent defined in `recipe/sub/` but never referenced in any
orchestrator's dispatch logic or upstream agent's summon calls is
**invisible** to the running system. It wastes recipe file space and
misleads the user about system capabilities.

### Detection rule
An agent is "orphan" if:
- It appears in `recipe/sub/` with a valid YAML structure
- Its name does not appear in any `summon` call across the codebase
- Its name does not appear in any orchestrator's dispatch list

### Prevention
When creating a new sub-agent:
1. Define at least ONE upstream agent that summons it
2. Add the trigger type/prefix to that agent's STEP 0.5
3. Run `tools/dev_goose_expert_check.py` to verify the wiring
4. Add the agent to the orchestrator's dispatch manifest

### Existing orphan risk
As of 2026-07-14:
- sub_mas-goose-expert: was orphan, now wired in via R11
- Other agents in `recipe/sub/` should be audited via
  `tools/dev_orphan_check.py` (not yet implemented)

---

## L03 — Static checks cannot replace expert consultation

**Date:** 2026-07-14
**Severity:** MEDIUM (design pattern)

### Symptom
A common wrong solution to "we need Goose-aware validation" is to add a
static YAML-based rules list (e.g. "timeout must be 60-3600, max_steps
10-500"). This catches bad numbers but MISSES:
- Architectural issues (e.g. "this should use summon extension")
- Deprecated patterns (e.g. Goose v1 had X, v2 has Y)
- Cross-recipe integration conflicts
- Native-mechanism-vs-custom-implementation decisions

### Rule
- Use static checks ONLY for invariants that NEVER change
  (file naming, required fields, basic syntax).
- Use expert consultation (via summon) for everything that requires
  knowledge of external systems (Goose architecture, library APIs,
  framework conventions).
- When in doubt: summon. A wasted summon is better than a wrong patch.

---

## L04 — Pre-push validator is a HARD GATE

**Date:** 2026-07-14
**Severity:** CRITICAL (operational)

### Rule (user-mandated)
> User: "lass vor jedem Push goose mit dem Mas engineer laufen..
>        nur funktionierendes darf gepusht werden.."

Every push to github.com/mczardybon/mas-engineer MUST be preceded by:
```bash
export PATH="/root/.local/bin:$PATH"
# DEEPSEEK_API_KEY must be set in environment (NEVER hardcode here)
cd /tmp/mas-engineer/mas-engineer
goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml --no-session
```

Read `.state/pipeline/pre_push_validation.yaml`. Status MUST be `ok`.
If `blocked`: fix the blocked_reasons FIRST, then re-run.

### The 7 checks
1. P1 (high-severity) findings = 0
2. No hardcoded `/home/<user>/` paths
3. All YAML files valid
4. All Python tools compile
5. All shell scripts syntactically valid
6. No German characters in code/docs
7. Git status warning (uncommitted, not blocked)

This is non-negotiable. No exceptions.

---

## L05 — Always research first, never guess

**Date:** 2026-07-14
**Severity:** MEDIUM (user preference)

### Rule (user-mandated)
> User: "immer erst recherchieren! kein raten!"

When asked to configure/integrate something you do not have docs for:
- **Web search FIRST** before attempting any config.
- Applies to: tool setup, library config, framework integration, API setup.
- Do NOT write code/config from memory or guessing.
- Search the official docs (goose-docs.ai for Goose, etc.).

If you cannot find authoritative docs: SUMMON sub_mas-goose-expert
(or the relevant framework expert) for verification.

---

## L06 — All code and docs must be pure English

**Date:** 2026-07-14
**Severity:** LOW (consistency)

### Rule (user-mandated)
> User: "bitte lese jede datei komplett durch.. es darf kein mis englisch deutsch geben"

All code, comments, strings, YAML descriptions, docstrings — must be
**pure English**. No mixed German/English. The user is German-speaking
but the codebase is English-only.

Pre-push validator check 6 enforces this via grep for [äöüßÄÖÜ].

---

## L07 — Push sequence is always: set-url + push + reset-url

**Date:** 2026-07-14
**Severity:** LOW (operational)

### Correct pattern
```bash
cd /tmp/mas-engineer
git remote set-url origin https://<PAT>@github.com/mczardybon/mas-engineer.git
git push origin master
git remote set-url origin https://github.com/mczardybon/mas-engineer.git
```

The PAT is stored in user memory (Hermes memory), not in the repo.
Always reset the remote URL back to public after push to avoid leaking
the PAT in shell history or further commands.

---

## How to add a new lesson

When you learn something hard-won from a session:

1. Add a section L0X- at the top of this file (L08, L09, etc.)
2. Include: Date, Severity, Symptom, Root cause, Fix applied, Rule
3. Reference the commit hash that introduced the fix
4. If a tool can automate the check, add a reference to
   `tools/dev_<topic>_check.py`
5. If a new R-rule is needed, add it to
   `recipe/sub/sub_mas-master-constitution.yaml` and reference
   it from this file
6. Commit with `docs: add lesson L0X-...` and push (after pre-push-validator)

---

## Cross-references

- R01 (Confirmation requirement): master-constitution.yaml
- R09 (Mode-domain coupling): master-constitution.yaml
- R11 (Goose-expert consultation): master-constitution.yaml
- Pre-push validator: `recipe/sub/sub_mas-pre-push-validator.yaml`
- Goose expert: `recipe/sub/sub_mas-goose-expert.yaml`
- This file: `docs/lessons-learned.md`
