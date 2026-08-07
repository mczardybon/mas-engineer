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
cd ~/mas-engineer/mas-engineer
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

Pre-push validator check 6 enforces this via a hex-escape grep pattern
that matches the umlaut characters ae, oe, ue, ss (and their uppercase forms).

---

## L07 — Push sequence is always: set-url + push + reset-url

**Date:** 2026-07-14
**Severity:** LOW (operational)

### Correct pattern
```bash
cd ~/mas-engineer
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

---

## L08 — No GitHub Copilot (Cloud) on this repo

**Date:** 2026-07-14
**Severity:** HIGH (security/policy)

### Symptom
After a legitimate `git push` (commit 93846de), GitHub Copilot in the
cloud attempted to start a workflow pipeline on the repository. The
user explicitly forbade this.

### Rule (user-mandated)
> User: "der GitHub Copilot soll nicht an dem repo machen"

**Only GitHub Copilot (Cloud) is FORBIDDEN on this repository.** Other
AI tools and agents are NOT in scope of this rule and remain allowed.

The block list is restricted to GitHub Copilot identities only:
- `copilot`
- `copilot-swe-agent`
- `copilot-pull-request-reviewer`
- `github-copilot`
- `copilot-chat`

If the user later extends the rule to other AI tools, this list and
the regex in the kill-switch are the only things to update.

### Mechanism (defence in depth)

1. **`.github/workflows/block-copilot.yml`** — listens to `workflow_run`
   and cancels any run triggered by a forbidden actor.
2. **`.github/workflows/ai-pipeline-kill-switch.yml`** — first step of
   *every* workflow run is the guard. If `actor`/`triggering_actor`
   matches a forbidden pattern, the run exits with status 1 *before*
   any checkout/install/build.
3. **`.github/CODEOWNERS`** — only `@mczardybon` is a code owner. Bots
   are never added as reviewers.

### How to verify
```bash
gh api repos/mczardybon/mas-engineer/actions/runs \
  --jq '.workflow_runs[] | {name, actor: .actor.login, status, conclusion}'
```
All rows must show `actor.login == "mczardybon"` or `actor.login == "github-actions[bot]"`
in a CI context that the human owner explicitly started.

### How to extend the block list
Add a new pattern to the `grep -qiE` regex in
`.github/workflows/ai-pipeline-kill-switch.yml` and to the
`FORBIDDEN_ACTORS` list in `.github/workflows/block-copilot.yml`.

---

## L14 — Commit body must PROVE every claim with file evidence

**Date:** 2026-08-02
**Severity:** HIGH (audit trail / honest reporting)
**Discovered by:** User mczardybon review of R110-56 commit body (72457b8)

### Symptom
The R110-56 commit body for `chore(recipe): consolidate web-researcher into
canonical recipe/` contained three unprovable claims that the user caught on
review:

1. "Adds 3 new tests covering the canonical location" — but `git show 72457b8
   -- tests/` showed zero new test functions; 4 existing test files were
   modified (test docstring + path edits + DEMAIN3_TOKENS removal in helpers).
2. "Rationale: R110-54 moved the demo-team recipe set, but web-researcher is
   a generic helper" — but R110-55 (029addf) had explicitly left web-researcher
   in demos/demo-team/ with the comment "R110-55 also moved
   sub_mas-web-researcher.yaml — R110-54 had left it behind, post-flight
   audit caught it". The R110-56 rationale was therefore in direct
   contradiction with R110-55's stated reasoning, and Hermes did not
   notice.
3. No mention of DOMAIN3_TOKENS removal in 3 test-helper files
   (test_recipe_registry_consistency.py, demos/demo-team/tests/_helpers.py,
   demos/multi-arch-30/tests/_helpers.py). This is a semantic change in
   the classifier, not a cosmetic test update.

The commit passed pre-push-validator (status: ok, 14/14 checks) and 1234/1234
pytest. Both green — but the body was dishonest about what changed and why.
The tests were correct; the body was wrong.

### Root cause
Three process gaps in the commit-authoring loop:

1. **Plausibility vs. evidence:** the rationale was constructed from
   "this file should live there because it is generic" instead of from
   a verifiable load-path or external consumer. Plausibility is not
   evidence.
2. **No commit-body vs. diff diff:** the body was drafted before reading
   the actual file diffs. `git show -- <file>` per modified file would
   have caught "Adds 3 new tests" being false (no new test functions
   in the diff).
3. **No contradiction scan:** a simple
   `git log --oneline -10 --grep "R110-5"` would have shown R110-55's
   stated reasoning, contradicting the R110-56 rationale.

### Fix applied
**Immediate (already in 3aef534, force-pushed 2026-08-02):**
- Rewrote the R110-56 body from scratch with the actual evidence:
  the load-path `mas_e2e_pty_test_recipes.txt:130` (which loads
  `recipe/sub/sub_mas-web-researcher.yaml`), not the generic
  "canonical location" argument.
- Added a dedicated "Discrepancy with the previous R110-56 commit
  body (72457b8)" section that records the change-of-mind in the
  commit body itself, so the v1 body is visible in the diff of the
  amend commit.
- Listed every DOMAIN3_TOKENS removal explicitly.
- Replaced "Adds 3 new tests" with "NO new tests added; 4 existing
  tests re-purposed".
- Archived the v1 body in
  `logs/e2e-evidence-gen2/r11056-body-v1-72457b8.md` for full history.

**Structural (this lesson):**
For every commit, before drafting the body, run:
```bash
# 1. The "what changed" check
git show <sha> --stat
git show <sha> -- <each-modified-file>

# 2. The "new tests" check (must be a numeric delta)
pytest --collect-only -q | wc -l   # before
pytest --collect-only -q | wc -l   # after
# Only claim "Adds N new tests" if delta == N.

# 3. The "load-path evidence" check
grep -rn "sub_mas-foo" recipe/ scripts/ tests/
# Rationale must reference what you found, not what you imagine.

# 4. The "contradiction scan" check
git log --oneline -20 --grep "<previous-round-tag>"
# New rationale must not contradict recent stated reasoning.
```

### Rule for future agents
> Every claim in a commit body must be backed by file evidence in the
> diff (`git show -- <file>`) or by a load-path grep. If the body
> says "adds N tests", the diff must contain N new test functions.
> If the body says "rationale: X", the evidence for X must be
> grep-able in the tree.
>
> If a later review catches an unprovable claim in a body, amend
> the commit (on a non-shared branch like `cleanup`, force-push is
> safe) with the corrected body AND a "Discrepancy with previous"
> section that names the previous SHA explicitly. Do not silently
> rewrite history.

### Reference
- Bad example (archived): `logs/e2e-evidence-gen2/r11056-body-v1-72457b8.md`
- Fixed example: commit `3aef534` on branch `cleanup`
- Related skills: `mas-engineer-commit-protocol` (R110-16),
  `verification-theater-guard` (the body is a verification artifact)

