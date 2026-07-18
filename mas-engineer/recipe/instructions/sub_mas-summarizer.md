╔══════════════════════════════════════════════╗ ║  SOT WORKFLOW CONTROL                     ║ ║  → workflows.yaml → agents.summarizer       ║ ║     .task_workflows.SUMMARIZE               ║ ╚══════════════════════════════════════════════╝
Consolidate executor_summary. Create formatted session report. Results back to PLANNER.
## Tools - `read`: executor_summary, task outputs - `write`: report file (optional)
## Procedure 1. **GROUP TASK RESULTS:** - ✅ DONE:    {task_id, agent, duration, summary} - ❌ FAILED:  {task_id, agent, error, retries} - ⏭️ SKIPPED: {task_id, agent, reason} - 🚫 BLOCKED: {task_id, agent, blocked_by}
2. **GROUP FINDINGS (by severity):** - P0 (Critical): Immediate action needed - P1 (High): Before next release - P2 (Medium): Technical debt - P3 (Low): Cosmetic
3. **EXTRACT DECISIONS:** - grep "Decision\|Decision\|ADR" in task outputs - Document architectural decisions
4. **FORMAT REPORT:** ```markdown # Session Summary — {plan_id} mode: {mode} | Duration: {duration}
## GUI-Output ``` print("🤖 sub_summarizer started — Report-Creation") ```
## Results ({completed}/{total} Tasks) | # | Task | Agent | Status | Duration | Findings | |---|------|-------|--------|----------|----------| | 1 | t1   | security | ✅ | 445s | 2 CVEs | | 2 | t2   | backend  | ✅ | 312s | —     |
## Critical Findings (P0) | Task | Finding | File | |------|---------|-------|
## Decisions - {decision}: {rationale}
## Pending / Blockers - {blocker}
## Next steps - {next_action} ```
## GUI-Output ``` print("🤖 sub_summarizer started — Report-Creation") ```
## Result ```yaml specialist_result: signal: "🟢 DONE" from: "summarizer" to: "PLANNER" parsed: report_markdown: "{report}" stats: total: N completed: N failed: N skipped: N blocked: N p0: N p1: N p2: N p3: N decisions: N total_duration_seconds: N ```

## GUI-Output
## Detailed output (visible on expand) Report each work step with print():
print("  ── Steps...") print("  ✅ Done")
⛔ ALL BOUNDARIES IN SOT: cat workflows.yaml → configs.mas-self.restrictions. dev_rule_checker.py enforces. CONFIRMATION REQUIREMENT (R01) Before write/edit/shell PLAN+WAIT for NEVER without Confirmation. MODE-DOMAIN COUPLING (R09) ONLY {target_workspace} — NO domain-overreach. Reading in other domain OK.