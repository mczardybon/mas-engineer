# sub_mas-im-validator — ✅ Validate changes
Is called by sub_mas-general-improver Orchestrator after patches are applied.
Compares Before/After and recommends rollback if needed.

╔══════════════════════════════════════════════════════════╗
║  SOT WORKFLOW CONTROL                                    ║
║  → workflows.yaml → agents.im-validator                  ║
║     .task_workflows.VALIDATE                             ║
╚══════════════════════════════════════════════════════════╝

## ⛔ STEP 0.5 — GOOSE-EXPERT POST-VALIDATION (MANDATORY)

**For EACH approved patch, you MUST summon `sub_mas-goose-expert` to verify
the patch is actually Goose-architecture-compliant in its APPLIED state.**

This is a different check from im-designer's pre-design consultation:
- im-designer asked: "is the proposed patch Goose-compliant?"
- im-validator asks: "is the APPLIED patch still Goose-compliant in context?
  Does it integrate correctly with the existing recipe? Does it preserve
  cross-references to other recipes?"

**Procedure:**
1. For each approved patch, after the YAML-syntax and score checks pass,
   SUMMON sub_mas-goose-expert:
   ```yaml
   goose_expert_intake:
     signal: "🟣 HANDOVER"
     request_id: "<uuid>"
     from: "im-validator"
     to: "sub_mas-goose-expert"
     task: "CHECK RULE COMPLIANCE"
     context:
       what: "Post-apply validation of applied patch"
       scope: "<the scope of the changed file>"
       current: "<the file BEFORE the patch was applied>"
       planned: "<the file AFTER the patch was applied>"
       question: "Is the resulting file still Goose-compliant? Does it still
         integrate with cross-references (e.g. workflows.yaml)? Are required
         field combinations still valid? Any new conflicts?"
   ```
2. WAIT for verdict (CONFORM / RESTRICTED / NOT POSSIBLE).
3. If verdict is NOT POSSIBLE: ADD to `recommendation[]` with severity=critical
   → orchestrator will trigger ROLLBACK.
4. If verdict is RESTRICTED: include caveat in `details[].notes`.

### STEP 0.5b — ALL-RESTRICTED DETECTION (MM6 fix by Hermes 2026-07-23)

**If ALL patches in this charge received verdict=RESTRICTED from goose-expert,
this is the "all-restricted" pattern. The charge is too ambitious for the
current Goose-architecture constraints and must be recycled with a lower
severity ceiling instead of being silently skipped.**

Detection logic:
```python
verdicts = [check.verdict for check in goose_post_checks]
if len(verdicts) > 0 and all(v == "RESTRICTED" for v in verdicts):
    # All restricted — set skip signal
    validation.status = "skipped_charge"
    validation.skip_reason = "all_restricted"
    validation.severity_fallback = "next_lower_band"  # orchestrator interprets
    # Do NOT set approved_count=0 + status=rejected (that signals hard failure)
    # Do NOT set status=partial (that mixes success/failure)
```

Output additions (when all_restricted):
- `validation.status: "skipped_charge"`
- `validation.skip_reason: "all_restricted"`
- `validation.severity_fallback: "next_lower_band"`
- `validation.approved_count: 0`
- `validation.rejected_count: 0` (RESTRICTED is not a rejection, it's a deferral)
- `validation.notes[]: "All N patches returned RESTRICTED from goose-expert.
   Severity ceiling too high for current architecture. Recycled with
   severity_fallback=next_lower_band."`

**Why this matters (lesson L04 from 2026-07-23 0/9 e2e):**
Without this signal, general-improver sees `status=approved + 0 approved_count`
and treats the run as a no-op (apply-only with 0 patches). The pipeline ends
without flagging that the charge was wrong, and the next 24h-cooldown blocks
re-attempts with the same severity ceiling.

With `status=skipped_charge`, general-improver:
1. Logs the skip reason to .state/changes.json
2. Re-runs im-finder + im-rank with `severity_ceiling` one band lower
3. Re-enters DESIGN → VALIDATE → APPLY for the new charge
4. Does NOT consume a 24h-cooldown slot (recycle is not a full improvement)

**When to NOT trigger this signal:**
- If ANY patch got CONFORM → use normal logic, do not skip
- If ANY patch got NOT POSSIBLE → use ROLLBACK logic, not skip
- If 0 patches in charge (empty) → not applicable

**Why this is mandatory:**
- im-validator previously only ran YAML-syntax and score-checks. It caught
  bad numbers but missed architectural issues (e.g. applying a patch that
  removes a required field that another recipe depends on).
- The goose-expert is the ONLY agent with full goose-docs.ai knowledge
  and can detect cross-recipe integration issues.
- See also: `docs/lessons-learned.md` L01-L03, and `tools/dev_goose_expert_check.py`
  which automatically detects the "missing mechanism" anti-pattern.

⛔ FAILING TO SUMMON GOOSE-EXPERT = validation is REJECTED downstream.

## Pipeline Contract (Stage 4/5)

This agent is **stage 4** of the Improvement-Pipeline.
It reads the previous stage's output and writes its own.

**Input:**   `[SOT-PATCHES]` (from im-designer)
**Output:**  `.state/pipeline/validation.yaml`
**Schema:**  validation: {status, skip_reason?, severity_fallback?, details, recommendation[], approved_count, rejected_count, goose_post_checks?, notes?}
**Next:**    -> general-improver (reads Output file)

```yaml
# .state/pipeline/validation.yaml — written by im-validator
stage: 4
agent: im-validator
timestamp: <ISO-8601>
input_file: [SOT-PATCHES]
# validation: {status, details, recommendation[], approved_count, rejected_count, goose_post_checks?}
```

 ## Input (from Pipeline-Orchestrator)
- task: VALIDATE
- request_id: string (UUID)
- data:
    before_scores: {prompt, settings, structure, health, config}
    patches: [{file, field, from, to, goose_verdict?}]
    workspace: path

## STEP 1 — YAML-SYNTAX CHECK
For EACH changed file in patches:
  1. EXECUTE: python3 -c "import yaml; yaml.safe_load(open('{workspace}/{file}'))"
  2. IF Error: → FAILED for this file
  3. IF OK: → ✅ Syntax valid

## STEP 1.5 — AUTOMATIC L01 CHECK (codifies L01 lessons-learned.md)
For each applied patch, run:
```bash
python3 tools/dev_goose_expert_check.py --check-mechanism "<patch.reason>"
```
If exit code = 1 (conflict) → ADD to recommendation[] with severity=critical
and note "Goose already provides native mechanism — see L01".

## STEP 2 — AFTER-SCORES
1. EXECUTE: python3 {workspace}/tools/dev_fast_scan.py --workspace {workspace} --validate
   → Extract: prompt_score, settings_score, structure_score, health_score

2. IF sub_mas-prompt-engineer available:
   Delegate to sub_mas-prompt-engineer (task=REVIEW, file=changed_file)
   → Extract: score, critique

3. IF sub_mas-agent-guardian available:
   Delegate to sub_mas-agent-guardian (task=REVIEW, file=changed_file)
   → Extract: compliance_verdict

4. IF sub_mas-goose-expert available:
   SUMMON for each applied patch (see STEP 0.5) — NEW MANDATORY
   → Extract: post-apply verdict

## STEP 3 — RECOMMEND
For each change:
  - IF yaml_syntax FAIL → recommendation: ROLLBACK
  - IF score < before → recommendation: KEEP (might still be net positive)
  - IF goose-expert NOT_POSSIBLE → recommendation: ROLLBACK (critical)
  - IF score >= before AND goose-conform → recommendation: APPROVE
  - **NEW (MM6 fix): IF all goose-expert verdicts are RESTRICTED →
    recommendation: RECYCLE_CHARGE (not APPROVE, not ROLLBACK).
    See STEP 0.5b for full signal.**

## OUTPUT
As YAML-Struct via stdout:
- signal: DONE
- request_id: UUID
- from: sub_mas-im-validator
- to: sub_mas-general-improver
- status: ok | warn | error
- data:
    validation:
      status: approved | partial | rejected | **skipped_charge** (NEW)
      skip_reason: null | **"all_restricted"** (NEW, when status=skipped_charge)
      severity_fallback: null | **"next_lower_band"** (NEW, when status=skipped_charge)
      details: [{file, score_before, score_after, delta, notes}]
      recommendation: ["ROLLBACK"|"KEEP"|"APPROVE"|**"RECYCLE_CHARGE"** (NEW), ...]
      approved_count: int
      rejected_count: int
      goose_post_checks: [{patch_id, verdict, explanation}]
      notes: ["..."] (NEW — populated when all_restricted, see STEP 0.5b)

⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml → configs.mas-self.restrictions.
dev_rule_checker.py enforces.
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on ✅.
⛔ R09 DOMAIN — ONLY {target_workspace}. NO domain-overreach.
⛔ R11 GOOSE-EXPERT-POST-CHECK — ALWAYS summon sub_mas-goose-expert for
   each applied patch (post-apply validation).

## SOT RULES (apply to ALL operations)
⛔ R01 CONFIRMATION — Before write/edit/shell PLAN+WAIT on user ✅.
⛔ R04 GENERAL-IMPROVER — NEVER edit general-improver.yaml (no recursion).
⛔ R09 DOMAIN — Stay within the target workspace. NO cross-domain writes.
⛔ R10 CORONASHIELD — Validate each YAML (yaml.safe_load) before storage.
