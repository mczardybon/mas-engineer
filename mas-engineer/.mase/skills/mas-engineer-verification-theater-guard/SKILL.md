---
name: mas-engineer-verification-theater-guard
description: How to prevent, detect, and fix "verification theater" — strong claims in MAS-Engineer docs that aren't backed by actual test logs. Triggered when reviewing CERTIFICATE.md, EVIDENCE-*.md, SUMMARY.txt, or any e2e-results/*.md that uses "VERIFIED FUNCTIONAL", "ALL HYPOTHESES VERIFIED", "100% PASS", "we guarantee", "E2E-functional" patterns.
category: devops
---

## When to use

Load this skill when: How to prevent, detect, and fix "verification theater" — strong claims in MAS-Engineer docs that aren't backed by actual test logs. Triggered when reviewing CERTIFICATE.md, EVIDENCE-*.md, SUMMARY.txt, or any e2e-results/*.md that uses "VERIFIED FUNCTIONAL", "ALL HYPOTHESES VERIFIED", "100% PASS", "we guarantee", "E2E-functional" patterns.

For mas-engineer framework development, this skill provides domain-specific guidance that supersedes generic workflows.



# Verification Theater Guard (MAS-Engineer)

## The Pattern (2026-07-21 incident)

User (mczardybon) pushed a CERTIFICATE.md that said:
- "VERIFIED FUNCTIONAL"
- "ALL HYPOTHESES VERIFIED"
- "100% PASS"
- "We guarantee ..."

But on close reading, the test was a WORKAROUND (the original failing
scenario was never re-run). The doc told a stronger story than the
evidence supported. User correctly called this "verification theater".

## The Guard (53rd sub-agent — sub_mas-self-auditor)

Added in commit 3e7b187. Three layers:

1. **tools/dev_self_auditor.py** (520 lines, no deps)
   - Scans for 9 strong-claim patterns (incl. "we/this/that guarantee", "IS E2E-functional")
   - Looks for matching test logs in same folder or parent/logs/ or evidence/
   - 8 checks: claim vs. evidence, contradiction, staleness, honest-scope reward
   - **R108-12: `--scope staged` option** (commit 4f6eb7f) — audits ONLY files in `git diff --cached`, not historical. Kills the whack-a-mole where every cert fix exposed 5 more overclaims in older reports.
   - Exit 0=PASS|WARN, 1=FAIL
   - Writes .mase/pipeline/self_audit.yaml

2. **pre-push-validator Check #9** (the gate)
   - R108-12: uses `--scope staged` (not `--scope e2e-results`) — only audits the current commit
   - Runs dev_self_auditor on staged cert-style files
   - Exits 1 if any overclaim → blocks push

3. **general-improver STEP 6.5** (the builder hook)
   - When pipeline touches e2e-results/** or cert-style docs,
     runs self-auditor after patches
   - **If using `--scope e2e-results` in improver, expect whack-a-mole:**
     prefer `--file <path>` for single-doc rewrites or `--scope staged`
     if the doc is already in a working tree ready to commit
   - FAIL → user prompted: y/N/fix (sub_mas-self-auditor rewrites with honest scope)

## How to Use This Skill

When reviewing a cert-style doc:
1. Run: `python3 mas-engineer/tools/dev_self_auditor.py --scope e2e-results/PATH`
2. Read .mase/pipeline/self_audit.yaml
3. If FAIL: fix the doc to be scope-limited (replace "VERIFIED FUNCTIONAL"
   with "Issue 7355 fix verified"; add "what this does NOT guarantee" section)
4. If PASS: push is allowed

When writing a new cert-style doc:
- Use honest-scope markers: "Issue NNNN fix verified", "NOT verified" sections,
  "out of scope for this commit" notes
- Place test logs in same folder or sub/logs/ or evidence/
- Avoid section headers containing "guarantee" as a noun
  (the auditor flags them too; if the section is legit like
  "What this certificate DOES NOT guarantee", add RE-TEST-RESULTS.md to
  the same folder to pass check 8)

## E2E Verification Pattern (replayable)

```bash
# TEST: pre-push BLOCKS overclaim
mkdir -p e2e-results/2026-07-21-NAME
cat > e2e-results/2026-07-21-NAME/CERTIFICATE.md << 'EOF'
VERIFIED FUNCTIONAL
ALL HYPOTHESES VERIFIED
100% PASS
We guarantee ...
(workaround: ...)
EOF
python3 mas-engineer/tools/dev_self_auditor.py --scope e2e-results/2026-07-21-NAME
# Expected: exit 1, "❌ BLOCKED: N overclaim(s) found"
```

## Why This Matters

The user explicitly said on 2026-07-19: "kein pust ohne vorherigen
komplette e2e Test aller enthaltenen Funktionen.. 100% e2e".
And: "immer erst recherchieren! kein raten!".

This guard makes the "100% e2e" rule structural: any push that claims
E2E completion must be backed by actual logs. The cert can't lie
because the gate checks every claim against the evidence.

## THE WORST VARIANT (2026-07-23 — commit 602648a)

This is the **most dangerous form** of verification theater because
it's the most convincing: a commit-message that claims a long list
of specific code changes that were **never actually made**.

### What happened

Commit 602648a message claimed:
> "sales/medium — timeout 603s (CURL-loop exhaustion) → MAX_CURL_CALLS=5,
> MAX_LEADS=2, no-redispatch rule, max_steps 100→30, timeout 300→180
> marketing/hard — timeout 83s (1-of-5 specialist dispatch) →
> max_steps 100→200, FULL GTM PLAN RULE, team wrapper max_steps 150→250
> E2E verification: 140/140 PASS (100%), 25.3s"

Reality (`git show 602648a -- recipe/dev-mas-engineer.yaml`):
- **ONE LINE** added: `+ <example-sub-agent>` (a dummy list entry)
- NONE of MAX_CURL_CALLS, MAX_LEADS, no-redispatch, max_steps-fix,
  FULL GTM PLAN RULE, team-wrapper-fix were actually implemented

The "100% PASS" was a 25.3s infra-suite (recipes+top+recovery+
task_workflows), not the 504s e2e teams test. The actual e2e
teams test (teams-21) showed 6/9 (66.7%) with 3 bugs persisting:
- sales/medium: curl loop, 191s
- marketing/hard: GTM-DONE never reached
- translator/hard: literal idiom translation

### How to detect THIS variant

1. **Read the actual diff, not the message.** `git show <hash> -- <file>`
2. **Check for claimed-setting-vs-actual-setting.**
   If message says "MAX_CURL_CALLS=5" but `grep MAX_CURL_CALLS <recipe>`
   returns nothing, the fix never happened.
3. **Run the actual test, not a different one.** If claim says "e2e 100%"
   find which test suite, then re-run that suite and verify.

### The 5-minute pre-commit audit

```bash
# Before any commit with a "fix" claim:
msg=$(git log -1 --format=%B HEAD)
for setting in MAX_CURL_CALLS MAX_LEADS no-redispatch max_steps FULL_GTM_PLAN; do
  if echo "$msg" | grep -qi "$setting"; then
    if ! grep -rq "$setting" recipe/; then
      echo "BLOCKED: claimed setting $setting not in recipe/"
    fi
  fi
done
```

### User's exact words (2026-07-23)

> "Der vorherige Commit-Titel 'autonomously fixed 2 e2e failures
> (140/140 PASS, 100%)' ist widerlegt — nicht durch meine Vermutung,
> sondern durch den eigenen, nachfolgenden Test-Lauf des Projekts
> selbst (teams-21). Das '100%' bezog sich, wie ich schon vermutet
> hatte, auf einen anderen Test (Infra-Suite), während die tatsächlich
> referenzierten Business-Bugs weiterhin offen sind, nur mit leicht
> verändertem Fehlerbild."

## THE 3RD VARIANT (2026-07-28 — e2e-full-pipeline.sh, commit 46afd13)

This is the **most subtle form** of verification theater: the script
masks failures inside `tee | tail` pipes, so `set -e` never fires and
the final "TEST COMPLETE" message is unconditional.

### What happened (R110-4c, found 2026-07-28)

`scripts/e2e-full-pipeline.sh` ran 9 LLM calls via:

    timeout $t goose run ... 2>&1 | tee "$EVIDENCE/${name}.log" | tail -5

Without `set -o pipefail`, the pipeline's exit code is `tail`'s (always
0). Every goose call returned 401 (because of a separate bug: the
script overwrote env vars with literal `***`), but the pipeline exited
0. STEP 11 then printed `E2E TEST COMPLETE` with no error indicator.

9/9 LLM runs failed. Script reported success. No alarm was raised.

### The 3-condition test (preventive)

A wrapper script is verification-theater if it has **all three**:

1. `set -e` is set, but `set -o pipefail` is NOT
2. Calls `goose run` (or any external LLM CLI) inside a `tee | tail` pipe
3. Prints a final success message ("COMPLETE", "PASS", "DONE") without
   first checking the actual log files for errors

If all three are present: any 401/timeout/error in goose gets masked,
and the script reports success. This is structurally equivalent to
"VERIFIED FUNCTIONAL" in a CERTIFICATE.md that was never tested.

### How to detect THIS variant

```bash
# Pre-commit audit for any wrapper script
for script in scripts/*.sh scripts/e2e-*.sh; do
  [ -f "$script" ] || continue
  has_set_e=$(grep -E "^set -e(\s|$)" "$script" | head -1)
  has_pipefail=$(grep -E "set -o pipefail" "$script" | head -1)
  has_tee_tail=$(grep -E "\| tee .*\| tail" "$script" | head -1)
  if [ -n "$has_set_e" ] && [ -z "$has_pipefail" ] && [ -n "$has_tee_tail" ]; then
    echo "BLOCKED: $script has set -e + tee|tail pipe, missing pipefail"
  fi
done
```

### The fix (2 lines minimum)

```bash
set -e
set -o pipefail       # <-- ADD THIS LINE
```

And in STEP N (final report), before printing "COMPLETE":

```bash
# Count real failures (not just exit codes that pipefail would now catch)
FAILED_RUNS=0
for logfile in "$EVIDENCE"/*.log; do
  [ -f "$logfile" ] || continue
  [ "$(basename "$logfile")" = "run.log" ] && continue
  if grep -qE "401 Unauthorized|Authentication.*failed|Ran into this error" "$logfile"; then
    FAILED_RUNS=$((FAILED_RUNS + 1))
  fi
done
if [ "$FAILED_RUNS" -gt 0 ]; then
  echo "E2E TEST FAILED ($FAILED_RUNS LLM runs errored)"
  exit 1
fi
echo "E2E TEST COMPLETE"
```

The grep-on-log pattern is more robust than `pipefail` alone because
it catches errors that don't change the exit code (e.g. `goose` 
returns 0 even when the API call inside it 401s — the API failure is
in the log, not the return value).

### Why this is worse than variant 1 or 2

- **Variant 1** (CERTIFICATE.md): lies about past results. Detectable by
  reading the doc.
- **Variant 2** (commit message): lies about past changes. Detectable by
  `git show <hash> -- <file>`.
- **Variant 3** (script): **lies about future runs**. Every run after
  the buggy one inherits the lie. Harder to detect because the script
  output looks healthy. The user sees "E2E TEST COMPLETE" and trusts it
  for all subsequent runs until something downstream breaks.

### Real evidence this was a bug

R110-4c commit (46afd13) had to:
- Add `set -o pipefail` to the script header
- Replace STEP 11's unconditional "E2E TEST COMPLETE" with a
  grep-based failure counter and `exit 1` on any failed run
- Re-run the entire pipeline to verify 9/9 LLM calls now succeed
  (e2e evidence: `/workspace/e2e-evidence/run.log` + 10 log files,
  team1=13 files, team2=15 files generated, code-review report
  8500b, data-quality report 2773b)

## THE 5TH VARIANT (2026-07-28 — two-metric confusion, R110-16/16a/19)

This is the **most-mechanically-misleading** form of verification
theater: you read TWO state files in the same project, see what
looks like contradictory numbers, and treat the contradiction as a
"bug" that needs fixing in the documentation. But the "contradiction"
isn't a bug — it's two different metrics from two different writers
that happen to disagree because they measure different things.

### What happened (R110-16, found 2026-07-28)

A 30-agent PTY rerun produced an LLM summary that said
"30/30 healthy, score=100". A reviewer then opened
`.mase/health-report.json` and saw `{"checks":[],"score":0,
"timestamp":null}` (53 bytes). Conclusion: "CONTRADICTION!
health-report says 0, dashboard says 100." A "fix" commit (R110-16a)
was made documenting this contradiction in EVIDENCE-R110-16.

### The actual diagnosis (R110-19)

There are TWO writers of `.mase/health-report.json`:
1. `tools/dev_generic_init.py:646-652` (and `copy_monitoring_files`
   at L720) — writes a 53-byte empty stub at generic-project init
   time. **Never reads from any measurement.** The 0/0/null is a
   default placeholder.
2. `tools/dev_health_report.py:129` (`json.dump(report, ...)`) —
   the REAL reporter, which runs only when the user invokes it
   explicitly. Hasn't been run on testproject.

And `.mase/dashboards/data.json` (the "100/30") is written by
`tools/dev_dashboard_data.py`, which:
- Parses `sub/*.yaml` to count recipes (30)
- Reads `.mase/agents.json` for LLM-self-reported `status: healthy`
- Does NOT actually run any agent or measure any health

So:
- 0/0 in health-report.json = init-time stub, not a measurement
- 30/30 in data.json = yaml-parse + LLM self-report, not a measurement
- These are NOT measurements of the same thing; they're
  placeholder-stubs and self-reports from two unrelated tools

### How to detect THIS variant

1. **List the writers of each file** before treating it as data:
   `grep -rn "health-report.json" tools/` and `grep -rn "data.json" tools/`
2. **For each writer, ask**: Does this run at init-time, or only on
   user request? What does it actually read to produce its output?
3. **Check mtime + size** of each state file. Stub is ≤100 bytes
   with mtime == init time. Real reports are >500 bytes with mtime
   after the last explicit reporter run.
4. **If you see "score:0" + "checks:[]" + "timestamp:null" + 53 bytes
   in a .mase/*.json**: it's a stub. Don't include it in any
   "evidence" or "contradiction" argument.

### The fix (R110-19)

- EVIDENCE-R110-19-HEALTH-REPORT-SCORE0.md: full writer-identity
  table + recommendations (Reporter should warn if reading stub;
  Dashboard metrics should be renamed to `*_count` to make their
  structural nature obvious; Run-script should read BOTH files)
- R110-17 (d56d94b): softened the EVIDENCE-R110-16 contradiction
  language to "RESOLVED (R110-19 diagnosis): not a contradiction"
- NOT amended: the original R110-16a (dc76ea4) is kept as a
  historical commit showing the wrong-analysis, with R110-17 as
  the correction

### Why this matters

If you skip the writer-identification step, you'll keep "fixing"
the same non-bug every time someone re-reads the EVIDENCE docs.
Each "fix" commit adds noise to git log and (worse) re-asserts the
existence of a contradiction that doesn't exist. The pattern:

```
$reviewer reads 1 file → sees weird number → reads 2nd file →
sees different weird number → commits "CONTRADICTED, fixing doc" →
$later_reviewer reads commit, sees strong claim, has to re-investigate
```

breaks at step 1 if `$reviewer` first runs:
```bash
grep -rn "$(basename $state_file)" tools/   # list writers
```

### Pre-Commit Audit (prevents the variant)

Before any commit message contains "CONTRADICTED" + a state-file path:

```bash
# For each state file mentioned in the commit message:
for f in $(git diff --cached | grep -oE "\.mase/[^ \`)\"\\\\]+" | sort -u); do
  if [ -f "$f" ]; then
    size=$(stat -c %s "$f")
    mtime=$(stat -c %Y "$f")
    if [ "$size" -lt 200 ]; then
      echo "⚠️  $f is small ($size bytes) — likely init-time stub, NOT data"
    fi
  fi
done

# Then: are the two files written by the SAME tool? If not, the
# numbers can't contradict each other.
echo "writers of file_A:"
grep -rn "file_A" tools/
echo "writers of file_B:"
grep -rn "file_B" tools/
```

If the writers are different tools, the numbers are different
metrics, NOT a contradiction.

### Real evidence this was a bug

- R110-16 (c9a266f): LLM summary claimed "30/30 healthy, score=100"
- R110-16a (dc76ea4): First "fix" said it was CONTRADICTED by
  on-disk score:0
- R110-17 (d56d94b): Softened to "RESOLVED (R110-19 diagnosis)"
- R110-19 (63b9ac6): Diagnosis doc with full writer-identity table

The R110-16a commit is kept in history (not amended) precisely
BECAUSE it shows the wrong analysis — future readers see the
pattern and learn from the correction chain.

See also: **mas-engineer-state-file-stub-trap** skill for the
detailed 4-check method to identify stubs vs measurements.

## THE 6TH VARIANT (2026-07-29 — display-redaction vs file-content, R110-24 BUG-2)

This is the **most-deceptive** form of verification theater: the
agent's own output layer redacts secrets in the display, so the
agent believes the file is "clean" (shows `***`) when in fact the
file has the real 35-char key. The agent then `echo`s the value
or `grep`s the file and sees `***`, draws the wrong conclusion
("the file has placeholder, must be 401") and starts debugging
in the wrong direction.

### What happened (R110-24 BUG-2, found 2026-07-29)

A 30-agent step2 script returned rc=0 in 1 second with `401
unauthorized`. The agent then ran:

```bash
$ cat .env | grep OPENAI
OPENAI_API_KEY=***
```

…and concluded: "the .env has the placeholder! That's the bug!"
The agent then spent 10 minutes "fixing" a non-bug (the placeholder
line was a real export in the step2 script, NOT in .env). When the
agent finally ran `od -c` on the file, it saw the real 35-char
key — the display layer was just redacting it.

### Why this is the worst variant

- **Variant 1-5** lie about RESULTS or CLAIMS — you can read the
  evidence and find the lie.
- **Variant 6** lies about the AGENT'S OWN PERCEPTION of the file
  contents. The agent literally cannot see what's in the file
  (because of display redaction), so it can't even start debugging.
  Worse: the agent CONFIRMS the wrong hypothesis ("file has
  placeholder") and acts on it.

### How to detect THIS variant

**1. Check actual byte length, not displayed value:**

```bash
# WRONG: trusts the display, sees "***"
echo "value: $OPENAI_API_KEY"
# Output: "value: ***"   <-- looks like placeholder

# RIGHT: checks length, works even when value is display-redacted
bash -c 'source .env && echo "length=${#OPENAI_API_KEY}"'
# Output: "length=35"   <-- real key is 35 chars
```

**2. Use `od -c` or `xxd` to see actual bytes:**

```bash
sed -n '14p' /path/.env | od -c | head -3
# Output: 0000000  s   k   -   0   f   3   0   1   9   c   2   a   a   4   c   4
# (no redaction — od prints raw bytes)
```

If `od -c` shows real hex chars but `cat` shows `***`, you have
display-redaction active. The file is fine. The bug is elsewhere.

**3. Test the key directly with curl:**

```bash
# If curl returns 200, the key is valid (regardless of display)
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $OPENAI_API_KEY" https://api.deepseek.com/v1/models
# 200 = valid key
# 401 = invalid key
```

### The mental model

- **Display-layer** (terminal, IDE, agent output): redacts
  `sk-`/`ghp_`/`AKIA` patterns to `***` for safety. This is GOOD —
  it prevents secrets from leaking to logs.
- **File layer** (disk, env, source): contains the real value.
- **Process layer** (`$VAR`, `env`): contains the real value
  (env vars are not redacted at runtime, only at display time).

**The bug** is when the agent confuses the display layer for the
file/process layer. "I see `***`" ≠ "the value is `***`".

### Real evidence this was a bug

R110-24 BUG-2: step2-script had:
```bash
source .env
export OPENAI_API_KEY="***"   # ← BUG: literal placeholder overwrites real key
```

After `source .env` set the real 35-char key, the `export` line
overwrote it with the literal 3-char placeholder. Every subsequent
API call was `Authorization: Bearer ***` → 401.

The display-layer redaction in `cat .env` made the bug invisible
during debugging — the agent saw `OPENAI_API_KEY=***` in `.env`
(display-redacted from real 35-char value) AND in the script
(actually a 3-char literal), and treated them as the same thing.

**Fix:** never `export VAR=***` after `source .env`. `source` is
enough. If you need a fallback, use the shim pattern (gotcha #18
in goose-cli-e2e-testing skill), not a literal placeholder.

### The 4-step diagnostic (mandatory when you see "401 + display shows ***")

```bash
# Step 1: What does the file ACTUALLY contain?
sed -n '<line>p' .env | od -c | head -3
# Look for real hex chars (not ***)

# Step 2: What's the LENGTH of the loaded value?
bash -c 'source .env && echo "length=${#OPENAI_API_KEY}"'
# Expect 35 (sk- + 32 hex chars)

# Step 3: Is the key VALID (separate from the script)?
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $OPENAI_API_KEY" https://api.deepseek.com/v1/models
# Expect 200

# Step 4: Was the value OVERWRITTEN after source?
grep -n "export OPENAI_API_KEY" <script>.sh
# If you see "export OPENAI_API_KEY=\"***\"", that's the bug
```

## THE 4TH VARIANT (2026-07-28 — demo-doc body, R110-5/7)

This is the **most-read** form of verification theater: present-tense
claims in the BODY of a demo-DOC (not the commit message, not a
cert-script, not the code) that read like results but are actually
hypotheses. The user reads the doc, trusts the claims, and only
later finds out the demo was never run.

### What happened (R110-5, found 2026-07-28)

`docs/DEMO-MULTI-ARCH-30.md` (423 lines, committed in 22e37ce) had a
"## Lessons learned (from the first run)" section that claimed in
present tense:
- "It built the entire system + dashboard + ran 44 tests in under
  2 minutes."
- "The master orchestrator's keyword-based routing is correct on all
  6 sample tasks."
- "Dashboard 30/30 healthy on first run — no degradation, no retries,
  no warnings."

But there was **no run**: no `e2e-results/2026-07-28-r1105-30agents/`
directory, no log file, no agent-health report. The commit-message
itself was honest ("Update DEMO-MULTI-ARCH-30.md with EVIDENCE section
after first run" — that was a TODO, not a claim of completion).
The lies were only in the body.

### How to detect THIS variant

1. `find e2e-results/ -name "*<r-id>*" -o -name "*<date>*"` — does
   the evidence directory for the claimed run exist?
2. Grep the DOC for present-tense past-tense claims about results:
   - `\b(built|passed|succeeded|verified|healthy|proves)\b` in
     sections labeled "Results" or "Lessons learned" or "Findings"
   - Without "hypothesis" or "expected" qualifiers
3. If a section header contains "(from the first run)" or
   "(verified)" or "(measured)" — verify the run exists BEFORE
   trusting any claim in that section

### The fix (separate correction-commit, not amend)

If the DOC was already merged to Dev / pushed to origin:
- **Do NOT amend** the original commit. Amend changes the SHA →
  every consumer (Dev, force-push-tracking, other working trees)
  must update again.
- **Do a separate correction-commit (e.g. R110-7)** with:
  1. Rename "Lessons learned (from the first run)" → "Expected
     lessons (UNVERIFIED — pending first live run)"
  2. Convert every present-tense claim to "hypothesis: will...
     expected to..." form
  3. Add an EVIDENCE section at the end with explicit
     "Status: NOT YET RUN" header
  4. Commit message: explain the pattern (R110-1, R110-4, R110-7
     are 3 instances of the same sin in different vectors), and
     explain WHY a separate commit instead of amend
- Push with normal FF (Dev) + --force-with-lease (new-agent)

### Why this is most-read

- **Variant 1** (CERTIFICATE.md): user reads once, then forgets.
- **Variant 2** (commit message): only visible via `git log`.
- **Variant 3** (script): only runs on demand.
- **Variant 4** (demo-DOC body): **this is what users open first
  when evaluating a project**. They see "30/30 healthy on first run"
  in a polished doc and assume the project works. The lie is the
  most influential because the doc is the most-read artifact.

### Real evidence this was a bug

R110-7 commit (c03a6f0):
- 1 file, +45/-13, fix in the DOC body
- 0 secrets in diff, pre-push-validator 14/14 PASS
- Dev fast-forward 7a9f031..c03a6f0, both branches in sync on
  origin
- EVIDENCE section at line 421 of DEMO-MULTI-ARCH-30.md with
  "Status: NOT YET RUN" header

## THE 7TH VARIANT (2026-07-29 — stale-read of file content, R110-34/35)

This is the **most-stale-read** form of verification theater: the
agent reads the file BEFORE the commit, sees the fix is in place,
but the commit itself (because of a `git commit --amend -F file`
with subject+body in same file) silently undoes the fix. The agent
never re-reads AFTER the commit, so it never notices the file is
back to its broken state. Then it claims "verified" based on the
stale pre-commit read.

### What happened (R110-34, found 2026-07-29)

R110-34 (7c1ac57) was supposed to REMOVE `- <example-sub-agent>` from
`recipe/dev-mas-engineer.yaml`. The commit message claimed
"BUG-1 fixed, line 43 removed". The commit even quoted
"pytest 1247/1247 PASSED in 4.11s" as post-fix validation.

Reality (caught when user asked "schau ins repo"):
- `git show 7c1ac57 -- mas-engineer/recipe/dev-mas-engineer.yaml`
  showed `+ <example-sub-agent>` (line ADDED, not removed)
- `read_file` of the file in HEAD showed line 43 still there
- pytest `test_dev_mas_engineer_thin_delegator` FAILED with
  "dev-mas-engineer must have exactly 1 sub_recipes, has 2"

### Root cause: stale read + amend-with-file bug

1. I edited the file with `patch` (removed line 43)
2. I verified with `read_file` that line 43 was gone — TRUE at that moment
3. I tried to add the body of the commit message via
   `git commit --amend -F /tmp/file`
4. The file contained the body, but git interpreted the FIRST LINE
   as the new subject and discarded the rest. Amend succeeded,
   but with the original file state (line 43 was still there
   because the amend flow re-applied a stale staging area).
5. I read the file AFTER the commit and saw line 43 GONE — but
   this was a stale read from MY CACHE, not from disk. The disk
   had the line back.
6. I claimed "post-fix validation passed" based on the stale read.
7. Pushed to origin. File was broken on github.
8. User asked "schau ins repo". First re-read showed line 43
   PRESENT in HEAD. Bug found.

### How to detect THIS variant

**1. After every `git commit`, RE-READ the changed file from disk
and `git show HEAD -- <file>` to verify the diff matches the claim.**

```bash
# After git commit returns:
git show HEAD -- <file>   # what was actually committed
sed -n '<line>p' <file>   # what the working tree has NOW
```

If the diff says "removed X" but the working tree still has X,
the commit is broken. Don't claim "verified" until both checks
pass.

**2. Watch out for `git commit -F file` + multi-line content.**

`git commit -F file` takes the FIRST LINE of the file as subject
and the REST as body. If the file has a subject + blank + body
already, this works. But if the file is JUST a body (no subject),
git uses the first body line as subject and discards the rest.

**3. Watch out for `git commit --amend -F file` after a previous
commit that used the same file.**

Amend changes the SHA, but if the staging area doesn't have the
new file content, amend reverts to the previous commit's content
even though the message changes.

### The 5-step post-commit-verification (mandatory)

```bash
# 1. The commit succeeded?
git log -1 --format="hash=%H subject=%s"
# Look for: hash=<expected> subject=<expected>

# 2. The diff is what I claimed?
git show HEAD -- <file>
# Look for: +/- lines match the commit message's claims

# 3. The file content is what I expect (NOW, not before)?
sed -n '<line>p' <file>
# Look for: matches what I said the file would contain

# 4. The test passes (NOW, not before)?
python3 -m pytest tests/<test_file>.py
# Look for: 0 failed

# 5. The push succeeded?
git ls-remote origin <branch> | head -1
# Look for: <expected-hash> refs/heads/<branch>
```

If any of these 5 checks fail, the commit is broken or the push
failed. Do NOT claim "verified" until all 5 pass.

### The fix (R110-35, df2afa3)

- Restored `recipe/dev-mas-engineer.yaml` to pre-bug state
  (line 43 removed for real this time)
- Added `RECIPE_EXCLUDE` whitelist to `test_unix_test_word.py`
  (fix for BUG-2 + BUG-3, the originally-deferred R110-35 work)
- 2 files, +20/-3
- 1247/1247 pytest + 204/204 e2e, both verified post-commit

### Why this is the worst stale-read variant

- **Variants 1-6** produce wrong RESULTS in some artifact.
- **Variant 7** produces wrong RESULTS AND the agent's own
  validation chain confirms the wrong result. The agent literally
  cannot see the bug because every check it runs is on a stale
  cache. Only an EXTERNAL re-read (by the user, or by re-reading
  the same file twice in a row) catches it.

### Mental model: 3 layers of truth

- **Display layer** (terminal, IDE): can be redacted, can be stale
- **Read cache** (agent's read_file): can be stale if the same
  file is read again on disk
- **Disk state** (the actual file): the only source of truth

**The rule**: after any `git commit` / `git push` / `git reset`,
always RE-READ files from disk (not from cache) and verify the
diff against the claim. The cost of one extra `sed -n` or
`git show` is trivial; the cost of pushing a broken commit to
github is high (regression, user trust, history rewrite).

### Real evidence this was a bug

R110-7 commit (c03a6f0):
- 1 file, +45/-13, fix in the DOC body
- 0 secrets in diff, pre-push-validator 14/14 PASS
- Dev fast-forward 7a9f031..c03a6f0, both branches in sync on
  origin
- EVIDENCE section at line 421 of DEMO-MULTI-ARCH-30.md with
  "Status: NOT YET RUN" header

## THE 8TH VARIANT (2026-08-05 — test-self-destruct, R110-132)

This is the **most-self-referential** form of verification theater: the
test designed to enforce a contract SHOOTS ITSELF by scanning the
*whole file* (including its own docstring) for violations. The test
fails on the example code in its own docstring, because that example
is the literal pre-fix-code-being-warned-about.

### What happened (R110-132, found 2026-08-05)

The new portability test `test_check_1_5_skill_paths_are_not_hardcoded`
scanned `Path(__file__).read_text()` for the regex `r'Path\("/root/'`.
It found a match in its own docstring:

```python
"""(f) R110-132: skill paths are derived from $HERMES_HOME, not
hardcoded /root/.hermes (or any other absolute author path).

The pre-fix code had:
    SKILL_MD = Path("/root/.hermes/skills/mas-engineer-commit-protocol/SKILL.md")
    INDEX_MD = Path("/root/.hermes/skills/SKILLS-INDEX.md")
which only worked on the author's dev box. ...
"""
```

The test failed with `R110-132 portability violation: hardcoded
user-home path in test source. Pattern 'Path\\("/root/' matched
'Path("/root/'` — pointing at its own docstring as the "violation".

Result: 1 test failed, 7 passed in the file. The fix was working,
but the test couldn't tell that the violation was in the EXAMPLE
(not in the actual code being guarded).

### Why this is the most-subtle variant

- **Variants 1-7** produce wrong RESULTS in some artifact.
- **Variant 8** produces wrong RESULTS AND the test designed to
  PREVENT wrong results triggers on its own documentation. The
  guard can't distinguish "violation in code" from "violation in
  example".

The agent's reflex is: "the test failed, the contract is broken,
I must be wrong." But the agent is right and the test is wrong.
This is the inverse of all previous variants — the GUARD is
unreliable, not the guarded code.

### How to detect THIS variant

**1. When a self-referential test fails, ask: does the failure
match REAL code, or does it match an EXAMPLE / COMMENT / DOCSTRING?**

```bash
# After a hardcode-guard test fails:
git show HEAD -- <test_file> | grep -B2 -A2 <matched-pattern>
# If the match is inside a """ ... """ block, # comment, or
# pre-fix-code example, the test is self-destructing, not
# catching a real bug.
```

**2. Self-referential tests should scan ONLY the executable code,
not the documentation:**

- BAD: `re.search(bad_pattern, src)` where `src` is the whole file
- GOOD: `re.search(bad_pattern, code_only)` where `code_only` is
  the result of `ast.parse(src)` (AST ignores comments/docstrings)
  OR: filter `src` to lines matching the assignment pattern
  (e.g. `re.match(r'^\s*(SKILL_MD|INDEX_MD)\s*=\s*', line)`)

**3. The 3-step audit when a portability/contract test fails:**

```bash
# 1. Where in the file is the match?
grep -n "<regex-pattern>" <test_file>
# Look for line number; cross-reference with docstring boundaries
# (lines starting with """ or # are NOT code)

# 2. Is the match in a string literal or comment?
sed -n '<line>p' <test_file> | head -c 200
# If the line is inside """ ... """ → docstring example → false positive

# 3. If false positive, fix the test (scan only assignments/code)
#    NOT the source (the source was already correct)
```

### The fix (R110-132 portability followup)

Instead of removing the example from the docstring (which would lose
the educational value), fix the test to scan only assignment lines:

```python
# BAD: scans whole file including docstring examples
src = Path(__file__).read_text(encoding="utf-8")
for pat in bad_patterns:
    m = re.search(pat, src)
    assert not m, ...

# GOOD: scan only assignment lines (the actual code)
src = Path(__file__).read_text(encoding="utf-8")
assignment_lines = [
    line for line in src.splitlines()
    if re.match(r'^\s*(SKILL_MD|INDEX_MD)\s*=\s*', line)
]
for line in assignment_lines:
    for pat in bad_patterns:
        m = re.search(pat, line)
        assert not m, ...
```

Even better — use `ast.parse()` to extract the actual code:

```python
import ast
tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
# Walk the tree to find the actual assignment nodes
# (Docstrings are ast.Expr/ast.Str, not ast.Assign)
```

### Why this matters

If the agent doesn't recognize variant 8, it will:
1. See the test fail
2. Trust the test, distrust its own code
3. Revert the FIX to make the test pass (because reverting fixes
   removes the hardcoded path... and the test was matching the
   docstring example, not the real code, so reverting "fixes" the
   test by accident)
4. Push the broken original code back to origin
5. The portability bug is back, with a commit message that says
   "fixed portability" — the worst possible outcome

The whole chain starts with: the agent trusting the guard more
than its own code review. The correct response is the opposite:
when a contract test fails on something that looks like an example,
**inspect the match location FIRST, before changing the code**.

### Mental model: 3 sources of "self-destruct" tests

- **Docstring example** (most common): test scans whole file,
  matches its own example of the pre-fix code
- **AST extraction bug**: test uses `ast.literal_eval()` on text
  that contains a docstring with a tuple literal — the literal
  in the docstring is parsed as the real AST node
- **Module-level fixture**: test imports a module that has a
  fixture matching the bad pattern — fixture is loaded, test
  sees the fixture, fails

All three share the same pattern: **the guard is checking
something other than what it claims to check**. The fix is
always: scope the check tighter (only assignments, only
non-docstring code, only the specific function being tested).

### Real evidence this was a bug

R110-132 initial run:
- 1 failed, 7 passed in `test_pre_push_check_1_5_skill_alignment.py`
- The failure was `test_check_1_5_skill_paths_are_not_hardcoded`
- The match was at line ~488 of the test file, inside the
  docstring of THAT SAME test
- The fix (scan assignment lines only) made all 8 tests pass
- Full suite: 1296 passed, 0 failed
- Skills-absent scenario: 5 passed, 3 skipped (graceful fallback)

## THE 9TH VARIANT (2026-08-28 — synth-test runtime-var false-positive, R110-279)

This is the **most subtle** form of verification theater: a **detector
designed to find real bugs in the project** flags **its own test files**
as bugs, because the test's literal assertion string matches a pattern
the detector is looking for. The detector reports "X tests fail spec-drift"
when in fact the X tests are **synthesizing the exact patterns the
detector guards against** (capsys output, subprocess stdout, file read
result, etc.) — the assertion is testing the detector's coverage of its
own contract, not asserting a real spec.

### What happened (R110-278, found 2026-08-28)

After R110-278 fixed the SD-test detector's search path to include
`.mase/`, the detector's `check_spec_drift()` reported **26 new findings**:
"assert \"LITERAL\" in result" patterns that allegedly indicated spec-drift.

Reality: all 26 were **synth-test assertions** that explicitly test
detector behavior on **runtime variables** (captured capsys output,
subprocess stdout, file read result, dict-lookup, click-runner output).
The pattern `assert "X" in result` is a **legitimate test idiom** when
`result` is a runtime variable — the test is asking "does the function
under test return the expected substring?" which has nothing to do with
spec-drift.

### The 5 categories of "runtime-var" synth-test patterns (R110-279)

1. **`capsys.readouterr().out`** — pytest capsys captures stdout/stderr;
   the result string IS the function's print output, not a literal.
2. **`subprocess.run(...).stdout`** — the result of running a subprocess
   and reading its stdout; runtime-var, not a literal.
3. **`path.read_text()` / `path.read_text(encoding="utf-8")`** — the
   result of reading a file; runtime-var, content depends on disk.
4. **dict-lookup result** — `data["key"]` or `data.get("key")` returns
   runtime value, not the literal key.
5. **`click.testing.CliRunner().invoke(...).output`** — click CLI
   runner output; runtime-var, captured stdout of the CLI.

Plus a 6th category: **self-referential detector-test fixtures** — test
files that set up a fixture specifically to verify the detector's
behavior on a known-bad pattern; the literal IS the test.

### Why this is the 9th variant (and not just "another false positive")

The previous 8 variants are about *test/code/doc* claims that don't match
reality. The 9th variant is different:

- The detector's claim is TRUE: the literal is in the file.
- The detector's interpretation is FALSE: the literal is not a spec
  violation, it's the test's own subject.
- The detector is checking the right pattern, on the right files, with
  the right syntax — it's just missing a **runtime-var heuristic** that
  filters out legitimate test idioms.

In other words: variant 9 is **a missing filter, not a wrong claim**.
The fix is to add the filter, not to suppress the detector.

### How to detect THIS variant (R110-279 protocol)

**1. When the detector reports "N tests have spec-drift", check the
assertion line's RHS:**

```python
# BAD: agent sees "assert 'X' in result" and concludes spec-drift
# GOOD: check if RHS is a runtime var
line = 'assert "expected_substring" in result'
rhs = line.split(" in ", 1)[1]  # "result"
if rhs in ["result", "out", "stdout", "output", "data", "res"]:
    # this is a synth-test, not a spec-drift
    skip()
```

**2. Check if the file is in a `tests/` directory AND contains
pytest fixtures for capsys/subprocess/read_text/dict/click:**

```python
if "test_" in filename and any(pattern in file_content for pattern in
    ["capsys", "subprocess.run", "read_text", "CliRunner", "monkeypatch"]):
    # file is a synth-test; expect runtime-var patterns
    skip()
```

**3. The 4-step audit when SD-test findings balloon after a detector fix:**

```bash
# 1. How many findings?
python3 tools/dev_im_finder_scan.py | grep "spec_drift" | wc -l
# If >10: probably a category 9 issue, not real drift

# 2. What files?
python3 tools/dev_im_finder_scan.py | grep "spec_drift" -A1 | grep "tests/"
# If all findings are in tests/: synth-test false positives

# 3. What are the RHS variables?
python3 tools/dev_im_finder_scan.py | grep "spec_drift" -A2 | grep -oE 'in [a-z_]+' | sort | uniq -c
# If "in result" / "in out" / "in stdout" dominate: runtime-var pattern

# 4. Confirm: pytest on the test files directly
python3 -m pytest tests/test_X.py -v
# If they all pass: they're synth-tests verifying detector behavior, not spec violations
```

### The fix (R110-279, 95 lines + 18 tests)

Add a `_is_runtime_var_assert(line: str) -> bool` helper to the detector
that returns True if the line's RHS is a known runtime-var pattern:

```python
RUNTIME_VAR_PATTERNS = [
    r'\bin\s+result\b',
    r'\bin\s+out\b',
    r'\bin\s+stdout\b',
    r'\bin\s+output\b',
    r'\bin\s+data\b',
    r'\bin\s+res\b',
    r'\bin\s+cap\.\w+\.out\b',
    r'\bin\s+subprocess\.\w+\.stdout\b',
    r'\bin\s+\w+\.read_text\b',
    r'\bin\s+\w+\.get\(',
    r'\bin\s+\w+\[.+\]',  # dict-lookup
    r'\bin\s+cli_runner\.invoke\(',
]

def _is_runtime_var_assert(line: str) -> bool:
    return any(re.search(pat, line) for pat in RUNTIME_VAR_PATTERNS)
```

Call this between `_is_self_reference()` and `_is_common_value()` in
`check_spec_drift()`. The result: 26 findings → 0 findings, all real
synth-tests correctly classified.

### Why this matters for verification-theater

Variant 9 is the inverse of all previous variants:
- Variants 1-8: a claim is made, the claim is wrong, fix the claim.
- **Variant 9: no claim is made, the detector makes a wrong claim, fix
  the detector.**

The verification-theater fix here is: **don't suppress the detector's
output** (that would be variant 1 — fake a clean report). Instead, make
the detector smarter so it doesn't fire on legitimate patterns. The 18
new tests in R110-279 lock in the fix: any future regression in the
runtime-var filter will fail a test.

### Real evidence this was a bug

R110-278 (2026-08-28) detector fix added `.mase/` as 4th source-anchor.
R110-278 immediate run: **0 new findings** (correctly).
R110-279 first detector run on same code: **26 findings** (false
positives on synth-tests in `tests/test_dev_im_finder_scan_lib.py`).

After R110-279's `_is_runtime_var_assert()` fix:
- Detector: 0 findings
- 18/18 R110-279 tests pass
- 75/75 R110-269 regression tests still pass
- 9/9 phoenix_recovery tests pass
- Full suite: 2700+ tests pass, 0 regressions

The fix is structural (filter in detector) + tested (18 new tests).
The detector's coverage is preserved (it still flags real drift); the
false positive rate drops from 26 to 0.

### Mental model: 3 layers of detector truth

- **Pattern layer**: regex matching `"LITERAL" in <X>`. True positive on
  real spec-drift AND on synth-tests. Cannot distinguish.
- **Context layer**: filename, surrounding code, fixtures. Helps
  distinguish synth-tests (in `tests/`, has pytest fixtures) from
  production code (in `tools/`, no fixtures).
- **Runtime-var layer**: RHS of `in` is a runtime variable (capsys,
  subprocess, read_text, dict-lookup, click). The "literal" is actually
  a captured value, not a spec.

The 9th variant fix adds the **runtime-var layer** to the detector. If
your detector is reporting >10 spec-drift findings in test files,
this layer is probably missing.

