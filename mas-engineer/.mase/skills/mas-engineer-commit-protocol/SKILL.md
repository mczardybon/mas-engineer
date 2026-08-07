---
name: mas-engineer-commit-protocol
description: Commit + push style protocol for mas-engineer (mczardybon/mas-engineer) -- 4 emoji-categories (🔧|📝|📚|📊), R-sprint numbering (R<round>-<num>), em-dash format, 5-section body, author-identity, hook setup, push-pattern (credential-helper, NOT set-url), force-push backup-tag protocol. Load BEFORE any commit in this repo. Trigger when writing commit message, choosing emoji, picking R-number, setting up hooks in a new checkout, when validator Check 1.5 blocks push, when user says "schaue ins repo" or "commit + push kultur einhalten" or "transparenz" or "force-push" or "R110-127 update skill". Source-of-truth = validator Check 1.5 (recipe/instructions/sub_mas-pre-push-validator.md), NOT this skill — round-trip every claim through the validator.
category: devops
---

# MAS-Engineer Commit + Push Protocol

**Supersedes:** scattered notes in commit-messages, implicit R-numbering, hook-less setups.
**Source of truth (post-R110-126, force-push landed e89a0e5):** This skill was authored from the 2026-07-27 protocol doc + my own R110-78..R110-125 commits. It became stale relative to the actual repo practice. As of 2026-08-04 (R110-126 closure), this skill is the **operational extraction** of:
- Validator Check 1.5 allowlist (the authoritative gate) — see `recipe/instructions/sub_mas-pre-push-validator.md`
- Standalone drift-detector `tools/dev_category_drift.py` (now aligned with validator, R110-126)
- 23 rebased commits on origin/cleanup (R110-103..R110-125), e89a0e5 last
- EVIDENCE-format precedents (📊 EVIDENCE — R110-N — <title>)

**🚨 LOAD BEFORE EVERY R-SPRINT COMMIT. 🚨** R110-124 (5b82fab, 2026-08-04) violated 4 protocol points (wrong emoji, wrong body format, hooks inactive, no CHANGELOG) because the skill was loaded AFTER commit body was already written. R110-24 forbids amend — protocol violations are permanent log corruption, NOT correctable post-hoc. Cost: 1 corrupted commit + 1 follow-up commit (R110-125) needed to document the lesson. **Triple-format-mismatch (R110-126 lesson):** this skill pre-R110-126 said `wrench R<n>-<m> -- <title>`; the detector said `chore:/docs:/fix:/wrench:/book:`; validator Check 1.5 said `🔧 R<round>-<num> — desc`. ALL THREE were DIFFERENT, and the actual repo practice on origin/cleanup is `🔧 R110-117 — <title>` (em-dash, R-num with hyphen, NO double-dash, NO scope). Validator is source-of-truth — every claim in this skill must round-trip through `recipe/instructions/sub_mas-pre-push-validator.md` Check 1.5 before being trusted.

## When to load
- BEFORE any `git add` / `git commit` in `mczardybon/mas-engineer`
- When picking a commit title or emoji
- When picking the next R-number
- When setting up a new checkout (hooks not active by default)
- When user says "schau ins repo", "transparenz", "commit-kultur", "ehrlich"

## The 5-step pre-commit workflow (mandatory)

Before EVERY commit:

```bash
cd /workspace/dev-branch   # or wherever mas-engineer is checked out

# 1. Look at recent commits -- what's the current style?
git log --oneline -20

# 2. Read the authoritative style doc
cat docs/commit-push-protocol-2026-07-27.md   # exists in repo, 414 lines

# 3. Check hooks are active (default: NO!)
git config --get core.hooksPath   # empty? then hooks are NOT active, fix below

# 4. Find the next R-number
git log --oneline | grep -oE "R[0-9]+" | sort -u | tail -5
# Latest was R109 then my next fix is R110-1

# 5. Verify author identity (Hermes-MAS-Engineer, NOT Hermes Agent)
git config user.email   # should be Hermes@mas-engineer.local
git config user.name    # should be Hermes-MAS-Engineer
```

If `core.hooksPath` is empty:
```bash
git config core.hooksPath mas-engineer/.githooks
# verify: git config --get core.hooksPath
```

## 4 emoji-categories (canonical, per validator Check 1.5 + detector R110-126)

The 4 emojis that existed in 5eb67fe era (long before R36) and are hardcoded in `recipe/instructions/sub_mas-pre-push-validator.md` Check 1.5:

| Emoji | When | Format | Example (from origin/cleanup) |
|-------|------|--------|-------------------------------|
| 🔧 | R-sprint fix-commit (code or tooling) | `<emoji> R<round>-<num> [follow-up] — <title>` | `🔧 R110-126 — align dev_category_drift.py ALLOWED with validator Check 1.5 (emoji R-sprint)` |
| 📝 | R-sprint doc-only commit | `<emoji> R<round>-<num> [follow-up] — <title>` | `📝 R110-125 — STATUS.md 3d row + CHANGELOG-2026-08-04-r110-78-final-closure (2 files + 1 new doc)` |
| 📚 | R-sprint sprint-commit (multiple tests added) | `<emoji> R<round>-<num> — <title> (N tests)` | `📚 R110-16 — REAL EVIDENCE: 30-agent PTY rerun after R110-11..R110-15 fixes, 293s rc=0, dispatch-fix proven` |
| 📊 | EVIDENCE summary (post-test, evidence bundle) | `<emoji> EVIDENCE — R<round>-<num> [fixup] — <one-line>` | `📊 EVIDENCE — R110-28 — team-composition live-PTY test (4/6 PASS, 2 TIMEOUT-aka-success, 12m 30s, 50KB)` |

**Anti-patterns (NEVER use these — R36 lesson):** `🪤 TRAP`, `🛡️ PUSH`, `🎯 TARGET`, `🚀 LAUNCH`, `💀 DEAD`. They get BLOCKed by Check 1.5 because they're not in the precedent set.

**Format details (R110-126 closure, the source-of-truth):**
- **em-dash** `—` (U+2014), NOT hyphen-minus `-` and NOT double-dash `--`. The skill pre-R110-126 was wrong on this.
- **NO scope** in the subject: NOT `🔧(scope) R110-1 — ...`. Just `<emoji> R<num> — ...`.
- **NO parentheses around the title** (vs the old `book R108-1 -- <titles> (4 tests)` style).
- **R-num is flat per sprint**: R110-100, R110-101, ..., R110-126 (NOT R110-1, R110-2 like the old `R108-1, R108-2, ..., R108-13, R109-1, R109-2, R109-3, R110-1` style).
- **[follow-up]** is optional, only when amending a prior R<num> (e.g. R110-26 vs R110-26-fixup).

**Conventional alternatives (NOT R-sprint, no R-number):** `fix:`, `docs:`, `e2e:`, `chore:`, `merge:` (NO scope! validator rejects `fix(scope):` in some checks, but text-prefix alone is conform per `ALLOWED_CATEGORIES = ("chore:", "docs:", "fix:", "wrench:", "book:")`). Examples from origin/cleanup: `chore: R110-102 -- vendor ignore for goose-install.sh + baseline-refresh 121->129 (2 files, +16/-7)`.

**R-numbering is strict sequential within a sprint round.** R108, R109, R110, R111 are the sprint-rounds. Within R110: R110-94, R110-95, R110-99, R110-100, R110-101, R110-102, R110-103, ..., R110-126. Don't skip, don't reuse. **To find the next R-num:** `git log --oneline | grep -oE "R<current-round>-[0-9]+" | sort -u | sort -t- -k2 -n | tail -1` then increment.

## 5-section commit body (mandatory for 🔧 + 📚 + 📊 + 📝)

The 5 sections are: **Bug / Fix / E2E / R-evidence / Pre-push-gate** (this is what the validator's Check 0 expects — R110-56 introduced this audit). Section order matters; section names are the English headers below.

Template (use this EXACT structure for 🔧 R<num> — and adapt for other emojis):

```bash
git commit -F /tmp/r<N>-commit-msg.txt
# where the file contains:
#   first line: <emoji> R<round>-<num> — <title>
#   blank line
#   Bug: <what was broken, with reproducer command + output>
#
#   Fix:
#   - <file 1>: <what changed, with line-counts>
#   - <file 2>: <what changed, with line-counts>
#
#   E2E (real-flow, N scenarios):
#     1. <scenario 1>  → PASS/FAIL (count)
#     2. <scenario 2>  → PASS/FAIL (count)
#     3. ...
#
#   R-evidence: <0 test-failures, 0 fixes needed | N fixes needed: list>
#
#   Pre-push-gate:
#     Step 0 (secret scan, tracked + history):   OK 0 secrets
#     Step 1 (pre-commit hook, staged content):  OK PASS
#     Step 2 (pytest tests/, N tests):           OK N/N in T.TTs
#     Step 3 (commit msg, <emoji> R-format):     OK per protocol
#     Step 4 (push):                              pending
#     Step 5 (post-flight audit):                 pending
#
#   Files (N):
#     M <path 1>  (<old> to <new> lines, <one-line summary>)
#     M <path 2>  (<old> to <new> lines, <one-line summary>)
#
#   <Optional: cumulative stats, R-sprint progress, forward-pointer, refs>
```

**Real-world reference commits on origin/cleanup:**
- `e89a0e5` (R110-126) — full 5-section body for a code-fix
- `8c29c81` (R110-106) — Bug/Fix/E2E/R-evidence/Pre-push-gate
- `542be6c` (R110-111) — minimal Bug/Fix/R-evidence/Pre-push-gate (small drift-fix)

**Skip the 5-section body only for:** typo-only fixes (R9, no behavior change), CHANGELOG-only updates, .gitignore additions, or when the entire commit fits in the title. **But: even for 📝 doc-only commits, the body should still reference which directive/R-sprint this closes** (R110-56 check 0 + my R110-124 lesson).

## Author identity (CRITICAL -- the wrong name silently corrupts the log)

| Author | Identity | When to use |
|--------|----------|-------------|
| `Hermes Agent <ramses@hermes.ai>` | The other Hermes instance | **NOT ME** -- don't use this even by accident |
| `Hermes-MAS-Engineer <Hermes@mas-engineer.local>` | Me | All mas-engineer commits |

Verify before committing:
```bash
git config user.email    # MUST be Hermes@mas-engineer.local
git config user.name     # MUST be Hermes-MAS-Engineer
# If wrong: git config user.email "Hermes@mas-engineer.local" && git config user.name "Hermes-MAS-Engineer"
```

## Push pattern (per R110-126, defensive + token-safe)

**Use the credential-helper approach. NEVER `git remote set-url` with a PAT embedded** (skill pre-R110-126 was wrong; the `set-url --push origin <PAT-url>` + "reset afterwards" pattern is fragile — a single forgotten reset leaks the PAT into remote-config and any subsequent push).

```bash
# 1. Get PAT from .env (NEVER inline, NEVER hardcode in a script that gets saved)
set -a && . mas-engineer/.env && set +a
echo "GH_PAT length: ${#GH_PAT}"  # sanity, never echo the value

# 2. Verify env-key name (R110-126 lesson: it's GH_PAT, NOT GITHUB_PAT_CLASSIC)
#    Pre-R110-126 memory said GITHUB_PAT_CLASSIC — WRONG. .env uses GH_PAT.
[ -n "$GH_PAT" ] || { echo "❌ GH_PAT empty — check mas-engineer/.env"; exit 1; }

# 3. Push via credential helper (the PAT is never written to remote-config or shell-history)
git -c credential.helper='!f() { echo username=x-access-token; echo password=$GH_PAT; }; f' push origin <branch>

# 4. For force-push (R110-90 + R110-126 precedent): use --force-with-lease, NOT --force
git -c credential.helper='!f() { echo username=x-access-token; echo password=$GH_PAT; }; f' push --force-with-lease origin <branch>

# 5. Verify remote PUSH-url is NOT polluted with PAT
git remote -v   # PUSH line (2nd) should be https://github.com/... NOT contain ghp_
```

**Branch convention:** Push to `cleanup` (the working branch) by default. The skill pre-R110-126 said "new-agent" — that's the OLD pre-2026-08-04 branch. After R110-78 closure, `cleanup` is the canonical working branch (per R110-31 + user-profile update 2026-08-03).

**Before force-push:** ALWAYS create a backup tag first:
```bash
git tag pre-r<N>-<M>-rebase-backup $(git rev-parse HEAD)
# Recovery if push goes wrong: git reset --hard pre-r<N>-<M>-rebase-backup
```

**GOTCHA R110-16 (still valid):** if you ever do use `git remote set-url`, the `--push` flag is required to change the PUSH-url (the default `set-url` only changes the FETCH-url, leading to "could not read Username" in non-TTY contexts).

## Post-flight verification (VT-WARN: trust git show, not memory)

After `git push`, ALWAYS run these 3 checks. Don't trust the terminal-output alone -- it's display-redacted.

```bash
# 1. What was ACTUALLY committed
git show HEAD --stat
# Expect: list of files, +N/-M counts

# 2. What was ACTUALLY pushed
git log origin/<branch>..HEAD --oneline   # should be empty (push caught up)
git log origin/<branch> --oneline -1      # should be your commit

# 3. Secret-scan the commit (NOT the working tree, NOT the diff -- the COMMIT)
git show HEAD | grep -E "sk-[a-f0-9]{32,}|ghp_[A-Za-z0-9]{30,}" || echo "OK 0 secrets"

# 4. File-system byte check (catches display-redaction false-negatives)
git show HEAD:<file> | xxd | grep -E "sk-[a-f0-9]{32,}" || echo "OK file bytes clean"
```

## Hooks (the REAL secret-defense, not the pre-push-gate alone)

`mas-engineer/.githooks/` has 2 scripts (committed in repo, NOT active by default):

| Hook | What it does | Pattern |
|------|--------------|---------|
| `pre-commit` | Block secrets in staged content | `git diff --cached \| grep -nE "^\+.*(sk-[A-Za-z0-9]{20,}\|ghp_[A-Za-z0-9]{30,}\|gho_[A-Za-z0-9]{30,})"` |
| `pre-push` | Block secrets in commits + YAML-validate recipes | Same secret pattern + `python3 -c "import yaml; yaml.safe_load(open('mas-engineer/recipe/...'))"` |

**Setup (one-time per checkout):**
```bash
git config core.hooksPath mas-engineer/.githooks
chmod +x mas-engineer/.githooks/{pre-commit,pre-push}   # may already be +x
```

**Test hooks are active:**
```bash
git config --get core.hooksPath    # should print: mas-engineer/.githooks
bash mas-engineer/.githooks/pre-commit && echo "OK hook active"
```

## When to update CHANGELOG (per protocol section 7)

| Event | CHANGELOG action |
|-------|------------------|
| R-sprint completes (e.g., R108 reaches a milestone) | Add section to `mas-engineer/../archive/docs/CHANGELOG-<date>.md` |
| E2E test passes for the first time (like the 2026-07-19 e2e-success) | Add new `CHANGELOG-<date>-<topic>.md` |
| Routine fix / transparency report | NO CHANGELOG update (commit alone is enough) |
| Force-push after secret-leak | NO CHANGELOG update (the secret-leak commit itself documents it) |

CHANGELOG template (from `CHANGELOG-2026-07-19-e2e-success.md`):
```markdown
# MAS-Engineer Changelog -- YYYY-MM-DD

## OK <Event Title> -- SUCCESS|FAILURE

**Task:** <one-line>
- <bullet 1>
- <bullet 2>

**Result via <method>:**
- <metric 1>
- <metric 2>

**Files modified:**
- <file>: <what changed>

**E2E-N result:** OK <what was verified>
```

## R110-126 Lessons-learned (5-fach-Fehler, the source of this skill update)

This skill was wrong on 5 specific points at the time of R110-89..R110-125. Documenting them so I never re-introduce them:

1. **Goose-CLI was already installed.** I assumed "validator doesn't run because goose isn't installed" — wrong. `/root/.local/bin/goose` (v1.45.0) has existed since 2026-07-29, just not in `PATH`. **Lesson:** `which goose` failure is NOT proof goose is missing — `find / -name goose` is the actual check (R110-89 EVIDENCE, the "ROSS-KNOX-LACUNA").

2. **mas-goose-env.sh exists for a reason.** I had to set `export PATH=$PATH:/root/.local/bin && . mas-engineer/.env` manually every time. The wrapper script (R110-89 deliverable) was supposed to be the canonical pattern. **Lesson:** load the wrapper, not re-derive the path.

3. **Skill format ≠ Detector format ≠ Validator format.** All 3 had different commit-title regexes. I trusted the skill (R108-1 style) over the validator (R110-117 style). **Lesson:** validator is source-of-truth, not the skill. The skill MUST be checked against the validator before any R-sprint.

4. **EVIDENCE-doc != validator-block-resolved.** R110-89's EVIDENCE.md said "goose CLI not installed — known gap, documented as WARN". I treated documented gaps as acceptable. **Lesson:** the gap is BLOCKING, not WARN-level, until I fix it. Documented-warn ≠ resolved-blocker.

5. **23 DRIFT commits were a real BLOCK, not "academic".** I saw the detector flag 23 commits and decided "it's just historical, not last-commit". **Lesson:** R110-94 made drift-detection a Check 16+ in the validator. The detector IS the gate. DRIFT > 0 = push blocked.

**The 5-step pre-commit workflow above is the FIX for lessons 1-5.** Following it prevents the next 5-fach-Fehler. The R110-126 force-push (e89a0e5) is the proof-of-fix: 18/18 PASS, 0 DRIFT, status: ok, PUSH ALLOWED.

## Verification: the readme you SHOULD re-read before each commit

| What | Where |
|------|-------|
| Style protocol (the canon, source-of-truth) | `recipe/instructions/sub_mas-pre-push-validator.md` Check 1.5 allowlist (`type(scope): desc` / `type: desc` / `mas(round-NN):` / `🔧\|📝\|📚\|📊 <TYPE> — desc` / `🔧\|📝\|📚\|📊 R<round>-<num> [follow-up] — desc` / `📊 EVIDENCE — R<round>-<num> — desc`) |
| Historical protocol doc (still in repo, but stale) | `docs/commit-push-protocol-2026-07-27.md` (was the old source-of-truth before R110-126) |
| Recent commits (current style) | `git log --oneline -20` |
| Next R-number | `git log --oneline \| grep -oE "R<current-round>-[0-9]+" \| sort -u \| sort -t- -k2 -n \| tail -1` then `+1` |
| Hooks active? | `git config --get core.hooksPath` |
| Author identity | `git config user.email && git config user.name` |
| Previous 🔧 R-sprint fix for reference | `git log --oneline --grep="🔧 R" -5` |
| Previous 📚 R-sprint sprint for reference | `git log --oneline --grep="📚 R" -5` |
| Validator v2.4.0 (the actual gate) | `recipe/instructions/sub_mas-pre-push-validator.md` (18 checks, R110-118 added Check 18 spec-invariant) |
| Standalone drift-detector (Check 16+ supplier) | `tools/dev_category_drift.py` (R110-126 aligned with Check 1.5) |

## What to do when user says "schau ins repo" (THE 2026-07-28 INCIDENT)

This is a user correction. The user noticed I was about to commit without checking the repo's actual style. Treat as a hard reset:

1. **Drop what you were doing.** Don't argue, don't apologize, don't continue.
2. **Read the protocol-doc:** `cat docs/commit-push-protocol-2026-07-27.md` (or the latest equivalent)
3. **Read recent commits:** `git log --oneline -20`
4. **Match the existing style exactly** -- emoji, R-number, body sections.
5. **Verify your changes pass the protocol's gates** before staging.
6. **Then proceed with the commit.**

The reason: the repo's commit-log IS the project's transparency trail (per protocol section 6, "Mein bericht hier ist operator-geschrieben, nicht system-generated"). Inconsistent commits corrupt that trail and force user to re-verify.

## Reference
- Author: Hermes-MAS-Engineer
- First applied: R110-1 (commit c5e854d, 2026-07-28 15:47 UTC)
- **Last revised: 2026-08-04 (R110-127 skill-update)**
- **Last validated: pre-push-validator v2.4.0 18/18 PASS, R110-126 force-push to origin/cleanup (e89a0e5), 0 DRIFT, status: ok**
- 5-fach-Fehler closure: see "R110-126 Lessons-learned" section above
- Related skills: `pre-push-gate` (the gating checklist), `goose-cli-e2e-testing` (for the e2e body-section content), `secret-leak-defense` (for the post-flight scan), `mas-engineer-workflow` (broader context), `goose-cli-e2e-testing` (`which goose` false-negative trap, R110-89)
- Branch convention: `cleanup` is the canonical working branch (since R110-31, 2026-08-03). The skill's pre-2026-08-04 reference to "new-agent" is obsolete.
