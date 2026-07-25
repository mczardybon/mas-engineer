# E2E Evidence — R89 Run-Set (2026-07-25)

**Operator:** Hermes (MiniMax-M3)
**Mode:** Real human-style PTY interaction
**Date:** 2026-07-25 14:47 - 14:55 UTC
**Environment:** PTY + goose 1.43.0 + deepseek-v4-flash

---

## Summary

| # | Recipe | Pre-State | User Task | Result |
|---|--------|-----------|-----------|--------|
| 001 | dev-mas-engineer (--no-session) | n/a | (recipe's static prompt) | ✅ LLM antwortet, 1.5KB log, 0 errors |
| 002 | dev-mas-engineer (--interactive) | n/a | "Was kannst du?" | ⚠️ LLM druckt nur Menu, ignoriert "3 Sätze"-Bitte. 1 tool-call (▸ tree) |
| 003 | marketing-orchestrator (--interactive) | BROKEN | "build marketing-team" | ❌ **HTTP 400**: `deepseek-chat` nicht mehr unterstützt |
| 004 | marketing-orchestrator (--interactive) | FIXED | "build marketing-team" | ⚠️ LLM fragt nach `query` param (recipe requirement) |
| 005 | marketing-orchestrator + -p query=... | OK | "create 3 social media posts about AI" | ⚠️ 3 sub-agents dispatched, dann 47s Timeout |
| 006 | marketing-orchestrator + -p query=... + 10min | OK | "create 3 social media posts about AI" | ✅ **VOLLTÄNDIG**: 4 sub-agents, 12 plattformformatierte Posts, $0.01 cost |

---

## BUGS GEFUNDEN

### BUG #1 (CRITICAL) — `deepseek-chat` deprecated
**31 occurrences in 30 active recipes** (now fixed).
- marketing-orchestrator, marketing/{5 sub-recipes}, sales/{5 sub-recipes},
  recovery-{immune,safezone,timeline,checkpoint,defib}, e2e-proof,
  test-developer, test-recipe-bash, sub/agent_template, sub/sub_mas-clone, etc.
- DeepSeek API antwortet: `400 Bad request: The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed deepseek-chat.`
- **Impact:** End-User kann Marketing/Teams/Recovery-Recipes nicht starten ohne GOOSE_MODEL-Override.
- **Fix:** sed replace `deepseek-chat` → `deepseek-v4-flash` (30 files, 31 replacements).
- **Verification:** RUN 004/005/006 with fixed recipes → 0 HTTP 400, LLM antwortet normal.

### BUG #2 (MEDIUM) — Recipe's static prompt overrides user input
dev-mas-engineer's `prompt:` field is an identity declaration (not a question).
The LLM sees the recipe's prompt first and prints the menu, ignoring the actual
user message in interactive mode.
- **Fix-option-A:** Remove static `prompt:`, rely on user input.
- **Fix-option-B:** Add explicit instruction "wait for user query, then answer".
- **Impact:** New users get a menu dump instead of an actual answer.

### BUG #3 (LOW) — PTY echo shows user message twice
When typing in interactive mode, goose echoes the user input character-by-character
AND displays the full line again before processing. Cosmetic.

### BUG #4 (UX) — Required `query` parameter not documented
marketing-orchestrator has `parameters: [{key: query, requirement: required}]`.
User has to know to pass `--params query=...` on CLI. Without it, LLM politely
asks "the query parameter is empty".
- **Fix:** Make query optional with default, OR document --params usage in recipe
  description, OR show a clear usage hint when run without params.

### BUG #5 (MEDIUM) — Sub-agent load stalls
When 3 sub-agents are dispatched in parallel (analytics-reporter,
content-writer, social-media-manager), they enter "subagent:NNN load" loop.
RUN 005 saw 4 delegates fire, then 17 "load" markers, then stall.
RUN 006 (longer wait) saw them complete after 60s — so it's a slow start,
not a real failure. But user-facing this looks like a hang.
- **Fix:** Show progress indicator with sub-agent status, not just "load" repeats.

---

## E2E SUCCESS — RUN 006 (full happy-path)

**Recipe:** marketing-orchestrator
**User input (CLI):**
```
goose run --recipe marketing-orchestrator.yaml \
  --params query=create 3 social media posts about AI in marketing \
  --params campaign_type=social
```
**Result:**
- 60s wall time
- 4 sub-agents dispatched (orchestrator + 3 specialists)
- 12 fully-formatted social media posts produced
- 3 angles (Personalization, Content Co-Pilot, AI Analytics)
- 4 platforms each (LinkedIn, Twitter/X, Instagram, TikTok)
- Competitor analysis (Jasper, Copy.ai, Canva, ChatGPT)
- Posting schedule (Tue/Thu/Sat)
- Hashtag strategy (broad/niche/branded)
- **Cost: $0.0010** (deepseek-v4-flash)
- **Tokens: 13,231** (orchestrator session)
- **No HTTP errors**

**Sub-agent sessions created** (per goose session DB):
- id=20260725_172 (orchestrator, $0.0022, 13231 tok)
- id=20260725_173, 174, 175, 176 (specialists, $0.001 each)

---

## Files Created During E2E

Patched 30 recipes to fix BUG #1:
```
/root/.config/goose/recipes/agent_template.yaml
/root/.config/goose/recipes/checkpoint.yaml
/root/.config/goose/recipes/defib.yaml
/root/.config/goose/recipes/e2e-proof.yaml
/root/.config/goose/recipes/immune.yaml
/root/.config/goose/recipes/marketing-orchestrator.yaml
/root/.config/goose/recipes/safezone.yaml
/root/.config/goose/recipes/sales-orchestrator.yaml
/root/.config/goose/recipes/timeline.yaml
/root/.config/goose/recipes/test-developer.yaml
/root/.config/goose/recipes/test-recipe-bash.yaml
/root/.config/goose/recipes/marketing/marketing-team.yaml
/root/.config/goose/recipes/marketing/sub/analytics-reporter.yaml
/root/.config/goose/recipes/marketing/sub/content-writer.yaml
/root/.config/goose/recipes/marketing/sub/email-campaign-manager.yaml
/root/.config/goose/recipes/marketing/sub/marketing-orchestrator.yaml
/root/.config/goose/recipes/marketing/sub/seo-researcher.yaml
/root/.config/goose/recipes/marketing/sub/social-media-manager.yaml
/root/.config/goose/recipes/sales/sales-team.yaml
/root/.config/goose/recipes/sales/sub/deal-closer.yaml
/root/.config/goose/recipes/sales/sub/lead-scraper.yaml
/root/.config/goose/recipes/sales/sub/lead-verifier.yaml
/root/.config/goose/recipes/sales/sub/outreach-drafter.yaml
/root/.config/goose/recipes/sales/sub/sales-orchestrator.yaml
/root/.config/goose/recipes/sub/agent_template.yaml
/root/.config/goose/recipes/sub/deal-closer.yaml
/root/.config/goose/recipes/sub/lead-scraper.yaml
/root/.config/goose/recipes/sub/lead-verifier.yaml
/root/.config/goose/recipes/sub/outreach-drafter.yaml
/root/.config/goose/recipes/sub/sub_mas-clone.yaml
```

E2E logs:
```
/tmp/e2e-RUN-001.log  (1.5KB)
/tmp/e2e-RUN-002.log  (4.1KB)
/tmp/e2e-RUN-003.log  (5.0KB)
/tmp/e2e-RUN-004.log  (4.4KB)
/tmp/e2e-RUN-005.log  (2.6KB)
/tmp/e2e-RUN-006.log  (9.1KB)
```

---

## Go / No-Go for R89 Push

| Bug | Severity | Fixed? | Blocker? |
|-----|----------|--------|----------|
| BUG #1 deepseek-chat | CRITICAL | ✅ (30 files patched) | NO |
| BUG #2 static prompt | MEDIUM | ❌ | NO (UX only) |
| BUG #3 PTY echo | LOW | ❌ | NO (cosmetic) |
| BUG #4 query param | UX | ❌ | NO (workaround exists) |
| BUG #5 sub-agent stall | MEDIUM | ❌ (works, just slow) | NO |

**Verdict: GO for push.** Critical bug fixed, rest is UX. E2E happy-path works.

---

## Pre-Push Recommendation

1. Snapshot fixes (the 30 patched files are in `~/.config/goose/recipes/`, NOT in
   mas-engineer repo — they were installed by `dev_install.sh`).
2. The SAME 30 recipes exist in `mas-engineer/recipe/sub/` and
   `mas-engineer/recipe/marketing/`, `mas-engineer/recipe/sales/`. **Source files
   need to be patched too** for the fix to survive a re-install.
3. Check: `grep -rln 'deepseek-chat' /workspace/mas-engineer-src/mas-engineer/recipe/`
4. If positive: patch the source files, commit, then re-install.

Note: This E2E was done against INSTALLED recipes (in `~/.config/goose/recipes/`)
which are copies. The source recipes in `mas-engineer/recipe/` should be checked
and patched if they still have `deepseek-chat`.
