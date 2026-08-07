---
name: mas-engineer-state-file-stub-trap
description: How to recognize that a "score=0" or "checks:[]" in mas-engineer's .mase/health-report.json (or similar framework metrics files) is an INIT-TIME STUB from dev_generic_init.py, not a real measurement. Triggered any time you see unexpected 0/0/empty/zero in a mas-engineer state file, before treating it as a bug in the producer code.
category: devops
---

# The Init-Time Stub Trap (R110-19, 2026-07-28)

## The Pattern

In mas-engineer, several files under `.mase/` and `.mase/dashboards/`
have **two writers**: one that writes a placeholder stub at
generic-project init time, and one that writes the real measurement
when the user explicitly runs a report.

**If you only check the file content, you can't tell which writer
produced it.** The stub is intentionally minimal (53 bytes) and
passes the most naive consistency checks ("score is a number, checks
is a list, timestamp is null — all valid JSON").

The trap: LLM agents (and human reviewers) see "score=0" and assume
the reporter ran and reported 0, leading to false "the reporter is
broken" diagnoses, redundant investigation, and wrong bug-fix
commits.

## The Two Known Stub-Producing Pairs (as of 2026-07-28)

| File | Stub writer | Real reporter | Stub contents |
|------|-------------|---------------|---------------|
| `.mase/health-report.json` | `tools/dev_generic_init.py:646-652` (+ `copy_monitoring_files` at L720) | `tools/dev_health_report.py:129` | `{"checks":[],"score":0,"timestamp":null}` (53 bytes) |
| `.mase/dashboards/data.json` | (no stub, but LLM self-reports `status: healthy`) | `tools/dev_dashboard_data.py` | N/A — but the `agents: 30/30 healthy` claim is self-reported, not measured |

Note: `data.json` is not a stub-trap, it's a different trap (LLM
self-report masquerading as measurement — see mas-engineer-verification-theater-guard variant 4).

## The 4-Check Identification Method

Before treating a `.mase/*.json` value as data, run:

```bash
file_path=".mase/health-report.json"   # or wherever
project_root="/path/to/project"

# 1. mtime: stub is from init time, not recent
echo "mtime: $(stat -c %Y "$file_path" | xargs -I{} date -d @{})"

# 2. size: stub is 53 bytes exactly (or near); real reports grow
echo "size:  $(stat -c %s "$file_path")"

# 3. content: stub has empty checks list and null timestamp
echo "content:"
cat "$file_path" | python3 -m json.tool

# 4. find writers: which tools can write this file?
grep -rn "$(basename "$file_path")" "$project_root/tools/" | head -10
```

**Decision matrix:**

| Check | Stub (don't treat as data) | Real measurement |
|-------|---------------------------|------------------|
| mtime | Same as project init time | After last report run |
| size | ≤100 bytes | >500 bytes |
| content | `checks:[]`, `score:0`, `timestamp:null` | Populated checks array, real score, ISO timestamp |
| writers | Single file, single `json.dump` call in init script | Dedicated reporter function, called by CLI subcommand |

If 3+ of 4 are stub → it's a stub, not a measurement. Document
this in EVIDENCE and move on. If only 1-2 → treat as data but
note the ambiguity in any commit message.

## The Wrong Fix (R110-16a, supersediert by R110-17)

If you see a contradiction in a state file and immediately commit
a "fix" that says the other file is "CONTRADICTED by on-disk
evidence", you've probably just done what R110-16a did:
- Treated the stub as data
- Treated the LLM-self-report as data
- Concluded the two are contradictory
- "Fixed" the EVIDENCE doc to be more honest about a non-existent contradiction

The right move: identify the two writers FIRST, then ask "are
they measuring the same thing or different things?" Different
metrics from different writers are NOT contradictions — they're
just two different metrics.

## The Correct Diagnosis Flow

When you see an "impossible" state-file combination:

1. **Don't commit a "CONTRADICTED" fix yet.** Open the file, look at it.
2. **List all writers** of each file: `grep -rn "filename" tools/`
3. **Read each writer's code path** — what does it measure, when does it run, what does it write?
4. **Check mtime/size/content** for each file on disk
5. **Decide**: bug in writer, stub, different-metric-but-correct, or actual contradiction
6. **Only THEN** write a commit. And if the answer is "different metrics, both correct", the commit should say "RESOLVED: not a contradiction" not "FIX: contradiction".

## The Pre-Commit Audit (5 seconds, prevents the trap)

Before any commit that mentions "stub" or "score=0" or "CONTRADICTED" in a mas-engineer state-file context:

```bash
# For every state file mentioned in the commit message:
for f in $(git diff --cached | grep -oE "\.mase/[^ \`)\"\\\\]+" | sort -u); do
  if [ -f "$f" ]; then
    size=$(stat -c %s "$f")
    mtime=$(stat -c %Y "$f")
    init_time=$(stat -c %Y .mase/ 2>/dev/null || stat -c %Y .mase/ 2>/dev/null)
    if [ "$mtime" -le "$init_time" ] && [ "$size" -lt 200 ]; then
      echo "⚠️  $f looks like init-time stub (size=$size, mtime<=init_time)"
      echo "    Don't treat its contents as a measurement in this commit."
    fi
  fi
done
```

## Real Evidence This Was a Bug

- R110-16 (c9a266f): LLM claimed "30/30 healthy, score=100"
- R110-16a (dc76ea4): First "fix" said it was CONTRADICTED by on-disk score:0
- R110-17 (d56d94b): Softened to "RESOLVED (R110-19 diagnosis)" — not a contradiction
- R110-19 (63b9ac6): Diagnosis doc with full writer-identity table

The bug was: **the LLM in R110-16 saw `.mase/dashboards/data.json`
(self-reported 30/30) and `.mase/health-report.json` (init-time
stub 0/0) and treated them as two measurements of the same thing**.
They are not. The data.json is from a YAML parser + LLM self-report.
The health-report.json is an unpopulated stub. Different writers,
different metrics, both "correct" for what they measure (the stub
is correctly zero because nothing was run; the data.json is
correctly 30/30 because all 30 yaml files parsed).

## Display-Redaction Caveat (R110-24, 2026-07-29)

When checking `.env` or other secret-bearing files for stub vs
real, the **terminal/agent display layer redacts `sk-*`/`ghp_*`
patterns to `***`**. So `cat .env` showing `OPENAI_API_KEY=***`
doesn't mean the file is a stub — it means the display is
redacting the real 35-char key.

**For `.env`/secret files**, replace the 4-check method's
"content" check with byte-length or `od -c`:

```bash
# Display-redacted — looks like stub but isn't
cat .env
# OPENAI_API_KEY=***

# Real check: length works even when value is redacted
bash -c 'source .env && echo "length=${#OPENAI_API_KEY}"'
# length=35  <-- real key, not stub

# Or: raw bytes via od
sed -n '14p' .env | od -c | head -3
# 0000000   s   k   -   0   f   3   0   1   9   c   2   a   a   4   c   4
```

See mas-engineer-verification-theater-guard "THE 6TH VARIANT"
for the full display-vs-file confusion pattern.

## Why This Trap Recurs

Every time a new state file is added in mas-engineer init, a new
stub exists. Reviewers will keep treating stubs as measurements
until either:
1. (Better) Init scripts stop creating stub files — only create
   state files when the reporter has been run
2. (Worse) Every reviewer runs the 4-check method before trusting
   any state file

The 2nd is cheaper. Adopt it as standard practice in the
verification-theater-guard workflow.
