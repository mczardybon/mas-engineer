# sub_mas-pre-push-validator — 🚦 Pre-Push Gatekeeper

MAS-Engineer-internal. Runs BEFORE every `git push` to make sure only
working, validated code reaches the remote. If any check fails, the push
MUST be aborted. This agent is the last line of defense.

╔══════════════════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                                    ║
║  → workflows.yaml → agents.pre-push-validator            ║
║     .task_workflows.VALIDATE                             ║
╚══════════════════════════════════════════════════════════╝

## Pipeline Contract (Stage 0/PRE)

This agent runs OUTSIDE the 5-stage im-* pipeline. It is the gatekeeper
before git push. It reads the current workspace state and verifies
everything is healthy.

**Input:**  current git working tree (uncommitted + last commit)
**Output:** `validation: {ok: bool, blocked_reasons: string[], warnings: string[]}`
**Next:**   if ok → git-operator allowed to push
            if blocked → human must fix issues first

## Procedure VALIDATE

Run the following 17 checks IN ORDER. Stop at the first failure if a hard
block is detected, but always collect all warnings.

### Check 0: Commit-body disclosure audit (NEW v2.1.0, R110-56)
**Why:** A commit body that says "Adds 3 new tests" but git diff shows
zero new test functions is **dishonest disclosure**. It corrupts the
audit trail, makes R-numbered findings un-trustable, and lets actors
hide regressions behind plausible-sounding text. The validator's
job is to catch THIS class of failure, not just code-level syntax.
R110-56 v1 (commit 72457b8) committed exactly this anti-pattern
(claimed 3 new tests + a contradicting rationale). Archived at
`e2e-evidence-gen2/r11056-body-v1-72457b8-archive.md`.
```bash
cd $WORKSPACE
python3 - <<'PYEOF'
import subprocess, re, sys

# Get the last commit body (subject + body)
raw = subprocess.run(
    ['git', 'log', '-1', '--pretty=format:%B'],
    capture_output=True, text=True
).stdout
lines = raw.split('\n')
subject = lines[0]
body = '\n'.join(lines[1:]).strip()

# 1. No-body check: short commits don't make claims, so they pass.
# (Trivial doc-style or chore commits typically have no body.)
if len(body) < 50:
    print(f"  ✅ Check 0 PASS (commit body too short to make claims: {len(body)} chars)")
    print(f"     {subject!r}")
    sys.exit(0)

# 2. Claim-extraction patterns
#    Each pattern returns (regex, claim_type, what evidence is required)
CLAIM_PATTERNS = [
    (r'\b[Aa]dds?\s+(\d+)\s+new\s+tests?\b', 'new_tests', 'pytest --collect-only -q | wc -l must show +N test items compared to HEAD~1'),
    (r'\b[Ff]ixes?\s+(R?\d+-\d+(?:/[A-Z\d]+)?)\b', 'fixes_X', 'git show HEAD --stat must show the fix touching the X file/function'),
    (r'\b[Rr]ationale:?\s*([^\n]+)', 'rationale', 'body rationale must not contradict git log --grep on the referenced round/issue'),
    (r'\b[Rr]eplaces?\s+(R?\d+-\d+)\b', 'replaces_X', 'prior commit X must be reachable OR the archive file must be referenced in the body'),
    (r'\b(?:DOMAIN_[A-Z_]+_TOKENS)', 'domain_tokens', 'body must explicitly call out what DOMAIN_*_TOKENS were added/removed'),
]

violations = []
for pat, ctype, required_evidence in CLAIM_PATTERNS:
    matches = re.findall(pat, body)
    if not matches:
        continue
    # 3. Cross-check each claim against the actual repo state
    if ctype == 'new_tests':
        for n in matches:
            n_int = int(n)
            # pytest --collect-only comparison
            cur = subprocess.run(['python3', '-m', 'pytest', '--collect-only', '-q', '--ignore=.state'],
                                 capture_output=True, text=True, timeout=60).stdout
            cur_count = sum(1 for line in cur.split('\n') if '::' in line and '::' in line.split('::', 1)[1])
            prev = subprocess.run(['git', 'show', 'HEAD~1:./'],
                                  capture_output=True, text=True, timeout=30)
            # Simpler: count test functions in HEAD~1 and HEAD diff
            head_tests = subprocess.run(['git', 'ls-tree', '-r', 'HEAD', '--name-only'],
                                        capture_output=True, text=True).stdout
            prev_tests = subprocess.run(['git', 'ls-tree', '-r', 'HEAD~1', '--name-only'],
                                        capture_output=True, text=True).stdout
            head_test_files = set(f for f in head_tests.split('\n') if f.startswith(('tests/', 'test/')) and f.endswith(('.py', '.sh')))
            prev_test_files = set(f for f in prev_tests.split('\n') if f.startswith(('tests/', 'test/')) and f.endswith(('.py', '.sh')))
            new_test_files = head_test_files - prev_test_files
            if len(new_test_files) != n_int:
                violations.append(
                    f"  ❌ Claim 'Adds {n_int} new tests' but git shows {len(new_test_files)} "
                    f"new test files (HEAD~1 vs HEAD): {sorted(new_test_files) or '(none)'}."
                )
    elif ctype == 'rationale':
        # Just note: rationale review requires human judgment; the validator
        # can only flag it for the operator to verify, not auto-block.
        # Heuristic: search for prior rounds' contradicting rationales.
        for match in matches[:1]:
            # Find any commit whose message references the same R-number
            rnums = re.findall(r'R\d+-\d+', match)
            for rn in rnums[:2]:
                prior = subprocess.run(
                    ['git', 'log', '--grep', rn, '--pretty=format:%s'],
                    capture_output=True, text=True
                ).stdout.split('\n')
                if len(prior) > 1:  # Multiple commits reference this R-number → potential contradiction
                    pass  # Soft flag only
        # We do NOT block on rationale — just print a reminder
        print(f"  ⚠️  Commit body contains 'Rationale: ...' — operator should manually verify")
        print(f"     the rationale does not contradict any prior R-numbered commit message.")

# 4. Additional generic check: body must NOT claim files are modified if
#    `git show --stat` doesn't show them.
stat = subprocess.run(['git', 'show', '--stat', 'HEAD', '--pretty=format:'],
                     capture_output=True, text=True).stdout
files_changed = set()
for line in stat.split('\n'):
    m = re.search(r'\|.*\b(\S+)$', line)
    if m:
        files_changed.add(m.group(1))

# Look for explicit file mentions in body
file_mentions = re.findall(r'`([a-zA-Z_][\w/.-]+\.[a-zA-Z]{1,5})`', body)
for f in file_mentions:
    if f not in files_changed and not f.startswith(('/', '.')) and 'archive' not in f.lower():
        # Only flag if the file isn't tracked anywhere
        exists = subprocess.run(['git', 'ls-tree', '-r', 'HEAD', '--name-only'],
                                capture_output=True, text=True).stdout
        if f not in exists:
            violations.append(
                f"  ❌ Body mentions file `{f}` but file is not in HEAD (might be archive-only). "
                f"Confirm the file is referenced as archive, not as a change."
            )

if violations:
    print(f"  ❌ Check 0 BLOCK: {len(violations)} disclosure violation(s):")
    for v in violations:
        print(v)
    print()
    print(f"  Fix: amend the commit (on cleanup branch) or write a corrected body. ")
    print(f"  See docs/lessons-learned.md L14 for the disclosure rule and worked example.")
    sys.exit(1)
else:
    print(f"  ✅ Check 0 PASS (commit body claims are evidence-backed)")
    print(f"     Subject: {subject!r}")
    print(f"     Body: {len(body)} chars, {len([l for l in body.split(chr(10)) if l.strip()])} non-blank lines")
PYEOF
```
**Block if:** any body claim contradicts `git show --stat` or known file state.
**R-numbered rationale mismatches are soft-warned only (not blocked) — they require human judgment.**

### Check 1.5: Last commit title matches repo convention (NEW v2.0.0)
**Why:** R36 anti-pattern — invented `🪤 TRAP` and `🛡️ PUSH` titles that
broke the repo's visual commit-history rhythm. Last-minute guard.
```bash
cd $WORKSPACE
python3 - <<'PYEOF'
import subprocess, re

# 1. Get last commit title
last_title = subprocess.run(
    ['git', 'log', '-1', '--pretty=format:%s'],
    capture_output=True, text=True
).stdout.strip()

# 2. Get ALL commit titles (sample for emoji census)
history = subprocess.run(
    ['git', 'log', '-50', '--pretty=format:%s'],
    capture_output=True, text=True
).stdout.split('\n')

# 2b. Allowed emojis (HARDCODED from repo history, NOT learned from last-50)
# R36 lesson: if we learn allowed emojis from history, we perpetuate anti-patterns
# (e.g. 🪤 TRAP, 🛡️ PUSH made it into history → would be allowed forever).
# Only the 4 emojis that existed in 5eb67fe era (long before R36) are allowed.
ALLOWED_EMOJIS = {'🔧', '📝', '📚', '📊'}

# 3. Build set of historically-used emojis (for diagnostics only)
EMOJI_RE = re.compile(r'[\U0001F000-\U0001FFFF\U00002600-\U000027BF]')
history = subprocess.run(
    ['git', 'log', '-50', '--pretty=format:%s'],
    capture_output=True, text=True
).stdout.split('\n')
used_emojis = set()
for t in history:
    for m in EMOJI_RE.findall(t):
        used_emojis.add(m)

# 4. Check last title
allowed_patterns = [
    r'^(fix|feat|chore|docs|test|refactor|arch|perf|style|build|ci|revert)(\([^)]+\))?:',  # conventional commits
    r'^mas\(round-\d+\):',  # MAS self-improve rounds
]
# Conventional commits with allowed emojis (the 4 in repo history)
for allowed in ALLOWED_EMOJIS:
    allowed_patterns.append(f'^{re.escape(allowed)} (FIX|DOCS|STATE|TEST|FEAT|CHORE|ARCH) — ')
# R108+ convention: emoji + R<round>-<num>[/<sub>] [follow-up] — desc
# Examples: 🔧 R108-9 follow-up — ..., 📚 R108-7 — ..., 📊 EVIDENCE — R108-9 — ...
for allowed in ALLOWED_EMOJIS:
    allowed_patterns.append(f'^{re.escape(allowed)} (R\\d+-[\\w-]+( follow-up)? — |EVIDENCE — R\\d+-)')

# 5. Check 5a: title matches a known pattern
ok = any(re.match(p, last_title) for p in allowed_patterns)
if not ok:
    print(f"  ❌ Last commit title doesn't match repo convention:")
    print(f"     {last_title!r}")
    print(f"     Allowed patterns: type(scope): desc | type: desc | 🔧|📝|📚|📊 <TYPE> — desc | 🔧|📝|📚|📊 R<round>-<num> [follow-up] — desc | 📊 EVIDENCE — R<round>-<num> — desc")
    print(f"     Run `git log --oneline -20` to see the dominant style.")
    exit(1)

# 6. Check 5b: any emoji in last title that's NOT in HARDCODED allowed set?
unknown_emojis = [m for m in EMOJI_RE.findall(last_title) if m not in ALLOWED_EMOJIS]
if unknown_emojis:
    print(f"  ❌ Last commit title uses NON-ALLOWED emoji(s):")
    for e in unknown_emojis:
        print(f"     {e!r} (allowed: {sorted(ALLOWED_EMOJIS)})")
    print(f"     If you need a new emoji, add it to ALLOWED_EMOJIS in this check + justify.")
    print(f"     Anti-patterns: R36 used 🪤 TRAP, 🛡️ PUSH (not in repo history → blocked).")
    exit(1)

print(f"  ✓ Last commit title follows repo convention")
print(f"     {last_title!r}")
print(f"     (precedent emojis in last 50 commits: {sorted(used_emojis) or 'none'})")
exit(0)
PYEOF
```
**Block if:** last commit title doesn't match `type(scope): desc`, `type: desc`,
`mas(round-NN):`, one of the 4 known emoji prefixes (`🔧`, `📝`, `📚`, `📊`) followed by `<TYPE> — desc`,
or R108+ convention `🔧|📝|📚|📊 R<round>-<num> [follow-up] — desc` / `📊 EVIDENCE — R<round>-<num> — desc`.
**Block if:** last commit title uses an emoji NOT in the precedent set (anti-pattern: R36 🪤 TRAP, 🛡️ PUSH).

### Check 1: P1 (high-severity) findings = 0
```bash
cd $WORKSPACE
python3 - <<'PYEOF'
import yaml, glob, os
findings_path = ".state/pipeline/findings.yaml"
if not os.path.exists(findings_path):
    print("WARN: no .state/pipeline/findings.yaml — run im-finder first")
    exit(0)
with open(findings_path) as f:
    data = yaml.safe_load(f)
high = [x for x in data.get('data', {}).get('findings', [])
        if '🔴' in x.get('severity', '')]
print(f"  🔴 high-severity findings: {len(high)}")
for f in high:
    print(f"     {f['type']} | {f['file']} | {f['detail'][:80]}")
exit(1 if high else 0)
PYEOF
```
**Block if:** any 🔴 high finding found.

### Check 2: No hardcoded /home/<user>/ paths
```bash
cd $WORKSPACE
grep -rn '/home/[a-z]*/' tools/ recipe/ .mas/ 2>/dev/null
```
**Block if:** any hardcoded user-home path found.

### Check 3: All YAML files are syntactically valid
```bash
cd $WORKSPACE
python3 -c "
import yaml, glob, sys
err = 0
for f in glob.glob('recipe/sub/*.yaml') + glob.glob('recipe/*.yaml'):
    try:
        yaml.safe_load(open(f))
    except Exception as e:
        print(f'ERROR: {f}: {e}')
        err += 1
sys.exit(1 if err else 0)
"
```
**Block if:** any YAML parse error.

### Check 4: All Python tools compile
```bash
cd $WORKSPACE
for f in tools/dev_*.py; do
    if ! python3 -c "compile(open('$f').read(), '$f', 'exec')" 2>/dev/null; then
        echo "SYNTAX: $f"
    fi
done
```
**Block if:** any Python syntax error.

### Check 5: All shell scripts are syntactically valid
```bash
cd $WORKSPACE
for f in tools/dev_*.sh; do
    bash -n "$f" 2>&1 || echo "SYNTAX: $f"
done
```
**Block if:** any shell syntax error.

### Check 6: No German-only words in code/docs
```bash
cd $WORKSPACE
# Check for umlaut characters and a list of common German-only words
# Note: the actual umlaut characters (ae, oe, ue, ss) are written as hex escapes
# below to keep this instructions file itself free of them and pass its own check.
# Whitelist: files that are intentionally German (translation libs, test data for
# German validators, legacy archival). These are functional, not bugs.
GERMAN_WHITELIST='^(tools/pre_check_lib/german\.py|tools/e2e_teams\.py|tools/cleanup_repo_v1\.sh|recipe/sub/legacy/)'
grep -rP $'[\xc3\xa4\xc3\xb6\xc3\xbc\xc3\x9f\xc3\x84\xc3\x96\xc3\x9c]' tools/ recipe/ docs/ 2>/dev/null \
  | grep -vE "$GERMAN_WHITELIST" \
  | grep -vE '^[^:]+:\s*(#|//)' \
  || echo "  (no off-whitelist German chars)"
exit_code=0
# Note: dashboard/agent/active etc. are English. Only flag the actual German words.
```
**Block if:** any German special character found.
*(Note: some German-cognate words are fine in English — only special chars are blocked.)*

### Check 7: Git status is clean or commit is the last action
```bash
cd $WORKSPACE
git status --porcelain | head -20
```
**Warning if:** uncommitted changes (push might miss them, but not blocked).

### Check 7.5: No backup files in commits (NEW v2.0.0 — R36 bug guard)
**Why:** R36 had a bug where `git add -A` accidentally committed 27k lines of
backup files (`.backups/20260724_*/`, `.state/pipeline/backup-*/`).
This check prevents that class of bug from ever reaching master again.
```bash
cd $WORKSPACE
# Scan the last 5 commits for accidentally-committed backup files
python3 - <<'PYEOF'
import subprocess, re
backup_patterns = [
    r'\.backups/',
    r'\.state/pipeline/backup-',
    r'\.bak\.',
    r'backup-pre-r\d+/',
]
# Get list of files changed in last 5 commits
result = subprocess.run(
    ['git', 'log', '-5', '--name-only', '--pretty=format:'],
    capture_output=True, text=True
)
files = [f for f in result.stdout.split('\n') if f]
polluted = [f for f in files if any(re.search(p, f) for p in backup_patterns)]
if polluted:
    print(f"  ❌ {len(polluted)} backup file(s) in last 5 commits:")
    for f in set(polluted):
        print(f"     {f}")
    exit(1)
print(f"  ✓ No backup files in last 5 commits (checked {len(files)} file-paths)")
exit(0)
PYEOF
```
**Block if:** any backup file appears in the last 5 commits.

### Check 8: No "missing Goose mechanism" anti-pattern (L01 from lessons-learned.md)
Catches the class of bug where im-designer proposes reimplementing a native
Goose mechanism (e.g. "add load on demand" when summon extension exists).
```bash
cd $WORKSPACE
# Scan uncommitted/pushed changes for "missing mechanism" claims
# R55 fix (2026-07-25): only call if diff non-empty + auto-default to findings.yaml
DIFF_CONTENT="$(git diff HEAD~1 -- recipe/ tools/ 2>/dev/null | head -200)"
if [ -n "$DIFF_CONTENT" ]; then
  python3 tools/dev_goose_expert_check.py --check-mechanism "$DIFF_CONTENT"
else
  # No recent changes — check current SOT findings/patches instead
  python3 tools/dev_goose_expert_check.py --findings .state/pipeline/findings.yaml 2>/dev/null || true
  python3 tools/dev_goose_expert_check.py --patches .state/pipeline/patches.yaml 2>/dev/null || true
fi
```
**Block if:** any "missing Goose mechanism" pattern found in uncommitted
or recently-pushed code/docs. See `docs/lessons-learned.md` L01.

### Check 9: Self-audit — no "verification theater" (no claim without evidence)
| Catches the class of bug where certificate / EVIDENCE docs contain strong
| claims (e.g. the phrases "VERIFIED-FUNCTIONAL" with that exact hyphenation,
| "ALL-HYPOTHESES-VERIFIED", "100%-PASS", or unguarded "guarantees")
| without a matching test log that actually demonstrates
the claim. This is the "verification theater" pattern that the user
flagged on 2026-07-21.

This check delegates to `sub_mas-self-auditor` (sub-agent). The
self-auditor reads e2e-results/, docs/, and top-level `*.md`, then
emits a report to `.state/pipeline/self_audit.yaml`.

```bash
cd $WORKSPACE
# Only run if e2e-results or cert-style files are staged.
# R108-13 fix: the previous detector used '\w*\.md$' which only matched
# root-level .md files (e.g. README.md), NOT nested paths like
# 'mas-engineer/docs/CERT.md' or 'e2e-results/2026-07-27/foo.md'.
# Result: Check 9 was silently SKIPPED for almost every commit. The
# --scope staged fix from R108-12 only runs IF this detector matches.
# New pattern '\.md$' + '\.txt$' matches any path ending in those
# suffixes (no leading-anchor on the filename part).
STAGED_CERTS=$(git diff --cached --name-only | grep -E "(^e2e-results/|^docs/.*CERTAIN|^certificates/|\.md$|\.txt$)" | head -5)
if [ -n "$STAGED_CERTS" ]; then
  # R108-12 fix: use --scope staged (audit only files in this commit),
  # not --scope e2e-results (which would re-audit ALL historical reports
  # and cause whack-a-mole: fix one cert → expose 5 more in older reports).
  python3 tools/dev_self_auditor.py --scope staged
  # Read its report
  cat .state/pipeline/self_audit.yaml
fi
```

**Patterns blocked (CHECK 1 in self-auditor):**
- `\bVERIFIED\s+FUNCTIONAL\b` without matching test log in same folder
- `\bALL\s+HYPOTHESES\s+VERIFIED\b` without matching log
- `\b100%\s+(PASS|pass|test|coverage)\b` without matching pass-count log
- `\bguarantee[sd]?\b` in a cert-style file (CERTIFICATE.md, etc.)
- `\bE2E[-\s]verified\b` not scoped to "loading fix"

**Block if:** ≥1 strong claim without matching test log, OR
strong claim + "workaround" / "out of scope" / "not yet tested"
within 5 lines (claim-vs-scope contradiction).

**Pass condition (CHECK 8 in self-auditor):** file contains
"honest scope" / "NOT verified" markers AND same folder has a
`RE-TEST-RESULTS.md` or similar honest-scope companion doc.
This rewards properly-scoped documents.

**Why this check matters:** On 2026-07-21 the project pushed a
CERTIFICATE.md that said "VERIFIED-FUNCTIONAL" and "ALL-HYPOTHESES-VERIFIED". On close reading, the underlying test was a workaround
and the original failure scenario was never re-run. The user
flagged this as overclaim. This check prevents recurrence by
making the pre-push gate reject unbacked strong claims.


### Check 10 — e2e regression baseline (behavioral verification)

**Why:** The pre-push validator currently checks STRUCTURE (yaml valid, secrets absent, no overclaims) but not BEHAVIOR. A "commit message says fix" + structure-OK can still ship broken recipes (cf. 602648a claiming 140/140 PASS while only changing 1 line). This check runs the actual e2e suite and fails the push if pass-rate regressed.

**Command (FOREGROUND, ~25-60s, no PTY):**
```bash
cd {workspace}
python3 tools/e2e_run_all.py --quick --no-interactive --auto-confirm 2>&1 | tail -30
```

**IMPORTANT (R110-60):** The `--auto-confirm` flag is REQUIRED for the R01 (CONFIRMATION_REQUIRED) bypass in e2e_run_all.py. Without it, the 5-minute confirmation window will expire mid-run and the e2e preflight will BLOCK every workflow with `⛔ R01 CONFIRMATION_REQUIRED` (not the e2e tests themselves failing).

**BOTH required (defense in depth, R110-58 + R110-60):**
- `--auto-confirm` CLI flag: signals operator-intent to bypass
- `MAS_AUTO_CONFIRM=1` env var: signals automation-context (e.g. CI/pre-push-gate)

If only one is present, e2e_run_all.py logs a WARN and skips the bypass. This mirrors the R01 hardness-5 AND-gate semantics. The pre-push-gate is an automation context, so `MAS_AUTO_CONFIRM=1` MUST be present in the validator's process environment before invoking the e2e tool. If you are running the validator manually (e.g. for debugging), set it in your shell first:
```bash
export MAS_AUTO_CONFIRM=1
goose run --recipe recipe/sub/sub_mas-pre-push-validator.yaml
```

**Parse output:** look for `✅ All {N} tests passed (100%)` or the summary line. Extract pass-count from the YAML report at the end of stdout (or stderr). The output format is: `Summary: {ok}/{total} passed ({pct}%)` — this is the canonical signal.

**Baseline source:**
- PRIMARY: last successful `e2e-results/<date>-run-N/raw-results.json` where `summary` shows 100% (or highest known)
- FALLBACK: hardcoded known-good baseline per run-mode
  - `quick` mode: 83/83 (as of 2026-07-22)
  - `full` mode: 139/139 (as of 2026-07-22)

**Block conditions (ANY of):**
- ⛔ current pass-count < baseline pass-count (regression)
- ⛔ current pass-rate < baseline pass-rate (regression)
- ⛔ any previously-passing test now fails (per-test regression)
- ⛔ command exits non-zero

**Warn conditions:**
- ⚠️ current pass-count == baseline but new test added (informational)
- ⚠️ baseline file missing (use hardcoded fallback with WARN)

**Note:** This check adds ~25-60s to the pre-push gate. If too slow for interactive use, can be skipped via `MAS_SKIP_E2E_BASELINE=1` env var (operator-initiated only, never auto-skip).

**Evidence file (always written):**
`.state/pre-push-e2e-baseline.json` — contains:
```yaml
checked_at: <ISO-8601>
baseline_source: <file path or "fallback">
baseline_pass: <int>
baseline_total: <int>
current_pass: <int>
current_total: <int>
regression_detected: <bool>
failing_tests: [<name>, ...]
command: <full command run>
```

**Reference:** docs/BUG-BRIEF-2026-07-23.md §3 (verification theater root cause).


### Check 11 — sub_recipe resolution coverage (structural e2e test baseline)

**Why:** mas's main loop relies on sub_recipe references resolving correctly. If `recipe/sub/X.yaml` declares sub_recipes pointing to files that don't exist, the framework fails at runtime. This check pre-validates all sub_recipe references resolve before push.

**Command (FOREGROUND, ~1-3s):**
```bash
cd {workspace}
python3 -c "
import yaml, glob, os, json
broken = []
total = 0
for f in glob.glob('mas-engineer/recipe/sub/*.yaml'):
    if 'ORIGINAL' in f: continue
    try: d = yaml.safe_load(open(f))
    except: continue
    for s in d.get('sub_recipes', []):
        total += 1
        path = s.get('path','').lstrip('./')
        full = os.path.join(os.path.dirname(f), path)
        if not os.path.exists(full):
            broken.append(f'{os.path.basename(f)} -> {s.get(\"name\")} ({path})')
print(json.dumps({'refs': total, 'broken': len(broken), 'pct': round(100*(1-len(broken)/max(total,1)), 2), 'sample': broken[:3]}, indent=2))
"
```

**Block conditions (ANY of):**
- ⛔ broken count > 0 (any sub_recipe reference unresolved)
- ⛔ refs == 0 (no sub_recipes found — likely YAML parse error)
- ⛔ command exits non-zero

**Warn conditions:**
- ⚠️ pct < 100 but > 95 (some broken refs, blocking)

**Reference:** R52-R55 post-flight audit pattern.


### Check 12 — test coverage gate (sub-agents vs tests, 80% minimum)

**Why:** With 120 sub-agents and only ~2 dedicated test files, mas's framework is critically undertested. The pre-push gate must enforce a minimum test-to-sub-agent ratio to prevent shipping unbacked code. This is the structural test-coverage gate.

**User requirement (2026-07-25):** tests/test_*.py count must be >= recipe/sub/*.yaml count × 0.8

**Command (FOREGROUND, ~1s):**
```bash
cd {workspace}
python3 -c "
import glob
sub_count = len([f for f in glob.glob('mas-engineer/recipe/sub/*.yaml') if 'ORIGINAL' not in f])
test_count = len(glob.glob('mas-engineer/tests/test_*.py'))
threshold = int(sub_count * 0.8)
ratio = round(test_count / max(sub_count, 1), 3)
gate_passed = test_count >= threshold
print(json.dumps({
    'sub_agents': sub_count,
    'tests': test_count,
    'threshold_80pct': threshold,
    'ratio': ratio,
    'gate_passed': gate_passed,
    'gap': max(0, threshold - test_count)
}, indent=2))
"
```

**Block conditions (ANY of):**
- ⛔ test_count < sub_count × 0.8 (below 80% coverage)
- ⛔ tests directory missing entirely (test_count = 0)
- ⛔ command exits non-zero

**Warn conditions:**
- ⚠️ ratio < 1.0 (informational — could be intentional for stable code)
- ⚠️ tests count == 0 (catastrophic — no tests at all)

**Operator override (escape hatch):**
- Set `MAS_SKIP_TEST_COVERAGE_GATE=1` env var to skip this check (operator-initiated only, never auto-skip)
- Documented in docs/TEST-COVERAGE-POLICY.md

**Evidence file (always written):**
`.state/pre-push-test-coverage.json` — contains:
```yaml
checked_at: <ISO-8601>
sub_agents: <int>
tests: <int>
threshold_80pct: <int>
ratio: <float>
gate_passed: <bool>
gap: <int>
```

**Status as of 2026-07-25:** sub_agents=120, tests=2, threshold=96, gap=94 — gate FAILS. This is intentional to expose the test-debt and force incremental coverage growth.

### Check 13 — constitution coverage
**Why:** Sub-agents that do not declare `constitution: sub_mas-master-constitution.yaml` operate outside the SOT and may diverge from master rules. This check enforces consistent governance.

**Command:**
```bash
cd $WORKSPACE
python3 - <<'PYEOF'
import yaml, glob, os
missing = []
checked = 0
for pattern in ['recipe/sub/*.yaml', 'recipe/sub/demo-team/*.yaml']:
    for f in glob.glob(pattern):
        if 'master-constitution' in f: continue
        checked += 1
        try:
            d = yaml.safe_load(open(f))
        except Exception as e:
            print(f"  ERROR: {f}: {e}")
            continue
        if d.get('constitution') != 'sub_mas-master-constitution.yaml':
            missing.append(f)
print(f"  Checked: {checked} sub-agent files")
print(f"  Missing constitution: {len(missing)}")
for f in missing:
    print(f"    ❌ {f}")
exit(1 if missing else 0)
PYEOF
```
**Block if:** any sub-agent file is missing `constitution: sub_mas-master-constitution.yaml`.


## Output Format

Write a YAML report to `.state/pipeline/pre_push_validation.yaml`:

```yaml
signal: DONE
request_id: pre-push-<timestamp>
from: sub_mas-pre-push-validator
to: human + git-operator
status: ok | blocked
data:
  validation:
    ok: <bool>
    blocked_reasons: [<string>, ...]
    warnings: [<string>, ...]
  checks_run: 13
  checks_passed: <int>
  checks_failed: <int>
  timestamp: <ISO-8601>
```

### Check 14: Multi-dim sub-agent coverage (NEW v2.0.0)
**Why:** R73 — R72 struktur-check finds yaml-schema bugs but not behavior bugs.
A sub-recipe with valid yaml can still fail at runtime (wrong sub_recipes ref,
missing external instructions, bad goose provider settings). Add behavior
coverage as a pre-push gate.

**What it does:**
Runs `tools/coverage_test --framework-only --mode=explain` (no LLM, ~1s)
and `tools/test_subagents --all --summary` (yaml schema). Both must pass.

```bash
cd $WORKSPACE
python3 - <<'PYEOF'
import subprocess, json
from pathlib import Path

W = Path("/workspace/mas-engineer-src/mas-engineer")

# 1. Behavior coverage (no LLM, fast)
r1 = subprocess.run(
    ["python3", str(W / "tools/coverage_test"),
     "--all", "--framework-only", "--mode=explain", "--timeout=10"],
    capture_output=True, text=True, timeout=120, cwd=str(W),
)
# Parse the saved JSON
coverage_dir = W / ".state" / "coverage"
latest = max(coverage_dir.glob("coverage-*.json"), key=lambda p: p.stat().st_mtime, default=None)
if latest:
    cov = json.loads(latest.read_text())
    behavior_pass = cov.get("passed", 0)
    behavior_total = cov.get("total", 0)
else:
    behavior_pass, behavior_total = 0, 0

# 2. Structure coverage (R72)
r2 = subprocess.run(
    ["python3", str(W / "tools/test_subagents"), "--all"],
    capture_output=True, text=True, timeout=60, cwd=str(W),
)
# Parse: "Total: N | PASS: N | FAIL: N | WARN: N"
import re
m = re.search(r"Total: (\d+) \| PASS: (\d+) \| FAIL: (\d+)", r2.stdout)
if m:
    struct_total = int(m.group(1))
    struct_pass = int(m.group(2))
    struct_fail = int(m.group(3))
else:
    struct_total, struct_pass, struct_fail = 0, 0, 999

# Pass criteria:
# - behavior: 100% (--explain mode = $0, so we expect all green)
# - structure: 100% PASS (WARN is ok, FAIL is not)
ok = (behavior_pass == behavior_total and behavior_total > 0 and struct_fail == 0)
print(f"  Behavior coverage: {behavior_pass}/{behavior_total}")
print(f"  Structure coverage: {struct_pass}/{struct_total} (FAIL={struct_fail})")
if not ok:
    reasons = []
    if behavior_pass != behavior_total:
        reasons.append(f"behavior-fail: {behavior_total - behavior_pass} recipes")
    if struct_fail > 0:
        reasons.append(f"structure-fail: {struct_fail} recipes")
    print(f"  ❌ Multi-dim coverage FAILED: {', '.join(reasons)}")
else:
    print(f"  ✅ Multi-dim coverage PASS ({behavior_pass} behavior + {struct_pass} structure)")

# Export for aggregator
print("CHECK14_RESULT:", json.dumps({
    "ok": ok,
    "behavior_pass": behavior_pass, "behavior_total": behavior_total,
    "struct_pass": struct_pass, "struct_total": struct_total, "struct_fail": struct_fail,
}))
PYEOF
```

**Result aggregation:**
- ✅ PASS: behavior 100% AND structure 100% (FAIL=0)
- ❌ BLOCK: any behavior fail OR any structure fail
- WARN: structure has warnings (informational only)

### Check 16+: Historical commit-subject category drift (NEW v2.2.0, R110-94)

**Goal:** Catches drift across the LAST 30 days that Check 1.5 cannot see
(Check 1.5 validates only the LATEST commit at push time).

**What it does:** Invokes the standalone drift detector
`tools/dev_category_drift.py` (R110-92) and BLOCKS the push if any
non-conforming subject is found in the last 30 days (post-cutoff,
default `--convention-since 2026-08-04`).

```bash
# Check 16+: Historical category drift
echo "🔍 Check 16+: Historical commit-subject category drift (R110-94)"
if [ ! -f "tools/dev_category_drift.py" ]; then
    echo "  ❌ BLOCK: tools/dev_category_drift.py missing (R110-92 drift detector required)"
    echo "     This check cannot run without it. Add it via R110-92 or disable this check."
    exit 1
fi
python3 tools/dev_category_drift.py --since 30 --json > /tmp/drift_check_16.json
DRIFT_RC=$?
if [ $DRIFT_RC -eq 2 ]; then
    echo "  ❌ BLOCK: Check 16+ usage error (exit 2). See /tmp/drift_check_16.json"
    cat /tmp/drift_check_16.json
    exit 1
fi
DRIFT_COUNT=$(python3 -c "import json; d=json.load(open('/tmp/drift_check_16.json')); print(d['drift_count'])" 2>/dev/null || echo "0")
if [ "$DRIFT_RC" -eq 1 ] || [ "${DRIFT_COUNT:-0}" -gt 0 ]; then
    echo "  ❌ BLOCK: Check 16+ — $DRIFT_COUNT historical commit(s) violate the 5-category convention"
    echo "     Run: python3 tools/dev_category_drift.py --since 30   (for details)"
    echo "     For the historical view (pre-cutoff): --convention-since YYYY-MM-DD"
    echo "     Reference: mas-engineer-commit-protocol skill, R110-90 rebase precedent"
    exit 1
fi
echo "  ✅ Check 16+ passed: no category drift in last 30 days (post-cutoff 2026-08-04)"
```

**Output block on PASS:**
```
🔍 Check 16+: Historical commit-subject category drift (R110-94)
  ✅ Check 16+ passed: no category drift in last 30 days (post-cutoff 2026-08-04)
```

**Output block on BLOCK:**
```
🔍 Check 16+: Historical commit-subject category drift (R110-94)
  ❌ BLOCK: Check 16+ — 3 historical commit(s) violate the 5-category convention
     Run: python3 tools/dev_category_drift.py --since 30   (for details)
     For the historical view (pre-cutoff): --convention-since YYYY-MM-DD
     Reference: mas-engineer-commit-protocol skill, R110-90 rebase precedent
```

**Additive to Check 1.5:** Check 1.5 catches the LATEST commit. Check 16+
catches the WINDOW. Both are needed; neither replaces the other.

**Override:** To pass on intentional historical drift (e.g. before the
5-category convention was enforced), update the cutoff in the script via
`--convention-since 2026-07-27` (or earlier). This check does NOT accept
a flag override — edit the script's default or use a wrapper if needed.

**Reference:** R110-92 (drift detector), R110-90 (rebase precedent),
R110-78 (spec-drift lesson — counts must be verified).

### Check 17: pytest-run (NEW v2.3.0, R110-78)

**Goal:** Catches test failures BEFORE the push is allowed. This is the
direct response to the R110-71 spec-drift incident where a recipe-count
change (96 → 110) was committed and pushed, breaking 2 tests
permanently because the validator never ran pytest. Check 17 makes
"validator green + tests red" impossible.

**Idempotency:** If `check_17_pytest_run` already appears in this file
(previously inserted by an earlier validator run), skip the insert and
keep the existing block. Detection via `grep -q "check_17_pytest_run"`.

```bash
# Check 17: pytest-run
echo "🔍 Check 17: pytest-run (R110-78)"
if [ ! -d "tests" ]; then
    echo "  ⚠️  WARN: no tests/ directory found — skipping pytest-run (no coverage to verify)"
    echo "PYTEST_SUMMARY: {\"passed\": 0, \"failed\": 0, \"errors\": 0, \"skipped\": 0, \"exit_code\": 5, \"note\": \"no tests dir\"}"
    echo "  ✅ Check 17 passed: no tests/ dir (PASSED, WARN-only)"
else
    # Run pytest; use 'set -o pipefail' so $? reflects pytest's exit code, not tail's.
    PYTEST_OUTPUT=$(python3 -m pytest tests/ -q --tb=line --color=no 2>&1 | tail -30)
    (set -o pipefail; python3 -m pytest tests/ -q --tb=line --color=no >/dev/null 2>&1)
    PYTEST_RC=$?
    # Parse summary line: e.g. "===== 1277 passed in 8.12s ====="
    PASSED=$(echo "$PYTEST_OUTPUT" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" | head -1)
    FAILED=$(echo "$PYTEST_OUTPUT" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" | head -1)
    ERRORS=$(echo "$PYTEST_OUTPUT" | grep -oE "[0-9]+ error" | grep -oE "[0-9]+" | head -1)
    SKIPPED=$(echo "$PYTEST_OUTPUT" | grep -oE "[0-9]+ skipped" | grep -oE "[0-9]+" | head -1)
    DURATION=$(echo "$PYTEST_OUTPUT" | grep -oE "in [0-9.]+s" | grep -oE "[0-9.]+" | head -1)
    PASSED=${PASSED:-0}; FAILED=${FAILED:-0}; ERRORS=${ERRORS:-0}; SKIPPED=${SKIPPED:-0}
    DURATION=${DURATION:-0.0}
    if [ "$PYTEST_RC" -eq 127 ]; then
        echo "  ❌ BLOCK: pytest not installed (exit 127). Install with: pip install pytest"
        exit 1
    fi
    if [ "$FAILED" -gt 0 ] || [ "$ERRORS" -gt 0 ] || [ "$PYTEST_RC" -ne 0 ]; then
        echo "  ❌ BLOCK: Check 17 — pytest failed: $FAILED failed, $ERRORS errors, exit=$PYTEST_RC"
        echo "     Last lines of pytest output:"
        echo "$PYTEST_OUTPUT" | tail -10 | sed 's/^/     /'
        echo "     Run: python3 -m pytest tests/ -q --tb=short   (for full traceback)"
        echo "PYTEST_SUMMARY: {\"passed\": $PASSED, \"failed\": $FAILED, \"errors\": $ERRORS, \"skipped\": $SKIPPED, \"duration_seconds\": $DURATION, \"exit_code\": $PYTEST_RC}"
        exit 1
    fi
    echo "  ✅ Check 17 passed: $PASSED passed, $FAILED failed, $ERRORS errors, $SKIPPED skipped in ${DURATION}s"
    echo "PYTEST_SUMMARY: {\"passed\": $PASSED, \"failed\": $FAILED, \"errors\": $ERRORS, \"skipped\": $SKIPPED, \"duration_seconds\": $DURATION, \"exit_code\": $PYTEST_RC}"
fi
```

**Output block on PASS:**
```
🔍 Check 17: pytest-run (R110-78)
  ✅ Check 17 passed: 1277 passed, 0 failed, 0 errors, 0 skipped in 9.6s
PYTEST_SUMMARY: {"passed": 1277, "failed": 0, "errors": 0, "skipped": 0, "duration_seconds": 9.65, "exit_code": 0}
```

**Duration reference (R110-95, 2026-08-04, 5x measurement):**
  Median: 9.65s | Mean: 9.60s | Std: 0.13s | Range: 9.46-9.77s
  Historical: 8.12s (R110-71 era, single-point). Spec is documentation-
  only; Check 17 does NOT BLOCK on duration. Variance is real (run-to-run
  ~0.3s); the 8.12s figure is now retired.

**Output block on BLOCK:**
```
🔍 Check 17: pytest-run (R110-78)
  ❌ BLOCK: Check 17 — pytest failed: 2 failed, 0 errors, exit=1
     Last lines of pytest output:
     FAILED tests/test_sub_mas_bootstrap.py::test_bootstrap_distributes_96_subagents
     FAILED tests/test_sub_mas_recipes.py::test_recipe_count_matches_subagents
     ...
PYTEST_SUMMARY: {"passed": 1275, "failed": 2, "errors": 0, "skipped": 0, "duration_seconds": 8.12, "exit_code": 1}
```

**Block logic:** BLOCKED iff `failed > 0` OR `errors > 0` OR `exit_code != 0`.
PASSED (with WARN) if `tests/` directory is missing — coverage is a
separate concern (D2 SD-finding), not a gate.
PASSED if `skipped > 0` (intentional skip is fine).

**Reference:** R110-78 (spec-drift incident), R110-71 (count change
that broke 2 tests), R110-82 (initial spec for Check 16 → renumbered
to 17 to avoid collision with R110-94 Check 16+).

## Boundaries

- ⛔ NEVER modify any source file — this agent is read-only
- ⛔ NEVER run `git push` itself — only validate
- ⛔ NEVER skip a check — all 17 must run (Check 0 + Checks 1-15 + Check 16+ + Check 17)
- ⛔ Max 300s timeout total (5 minutes)

**R01 NON-INTERACTIVE BYPASS (current implementation):** R01
(CONFIRMATION_REQUIRED) is a hardness-5 rule. The actual bypass mechanism
is NOT `RECURSION_OVERRIDE` / `MAS_NO_SESSION` (older docs may have
claimed this — those were aspirational and never implemented). The
real mechanism is `.state/.last_confirmation` (unix timestamp; valid
5 min, then auto-expires), checked in `check_confirmation()` at
`tools/dev_rule_checker.py:71-77` and `tools/dev_rule_checker_generic.py:24-31`,
and consumed by the R01 rule body at `tools/dev_rule_checker.py:102-106`
(and the parallel site in the generic checker).

Two ways to set `.state/.last_confirmation` programmatically:

  1. **Direct write (operator-initiated, e.g. CI step):**
       echo "$(date +%s)" > .state/.last_confirmation
     The check `(time.time() - ts) < 300` then passes for 5 minutes.

  2. **Via e2e_run_all.py wrapper (R110-58, automation context):**
       export MAS_AUTO_CONFIRM=1
       python3 tools/e2e_run_all.py --auto-confirm ...
     e2e_run_all.py refreshes `.state/.last_confirmation` BEFORE
     running the e2e tests, so the workflows it spawns (build-test,
     top_workflows, recovery) see a fresh confirmation. BOTH the
     `--auto-confirm` CLI flag AND the `MAS_AUTO_CONFIRM=1` env var
     are required (defense in depth, AND-gate); the implementation
     lives in `tools/e2e_run_all.py:226-262`.

The validator's Check 10 command (lines 441-447, R110-60) already uses
path 2. The freshness window is 5 min — if a CI step is taking longer
than 5 min between when it refreshed the confirmation and when it
actually triggers a preflight, the bypass might expire. Re-run
`e2e_run_all.py --auto-confirm` to refresh.

**R110-62 doc-fix note:** this section was rewritten to replace the
older aspirational "RECURSION_OVERRIDE=2 MAS_NO_SESSION=1" claim.
The vars `RECURSION_OVERRIDE` and `MAS_NO_SESSION` are used by
`tools/dev_recursion_override.py` (24h cooldown for self-improvement
patches) and by `tools/bulk_findings_fixer.py` (mode detection),
NOT by R01. Anyone reading older docs (`docs/E2E-TESTPLAN.md`
Test 5.1/5.2) or `docs/test-e2e-full.sh` should be aware those
references are stale.

CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation.
MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain-overreach. Reading in other domain OK.

# ⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml -> configs.mas-self.restrictions.
# dev_rule_checker.py enforces.

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
