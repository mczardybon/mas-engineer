# R110-126 — MQ consumer test pattern (R110-168+169 lessons into mas-engineer)

## CONTEXT

R110-168 (commit 221a520) added `wf_phoenix_log_persist` consumer +
`tools/dev_phoenix_log_persister.py` + 6 tests. R110-169 (commit
838ce0d) added phoenix-to-monitor auto-escalation + extended
`dev_recovery_defib.py` with `phoenix_recovery_incomplete`
classification + 5 tests.

R110-168+169 were applied DIRECTLY in `tools/` and `tests/`
instead of going through the directive/spec pattern. They
exposed 5 lessons that are now mas-side concerns, not hermes-side
concerns. This directive codifies them so the next MQ-consumer
work in mas-engineer applies them automatically.

The lessons were captured today in hermes skills
(`mas-engineer-mq-ecosystem-test-pattern`,
`mas-engineer-mq-cross-topic-escalation`) but hermes-side skills
do not propagate to mas-engineer runs. mas-engineer needs the
same knowledge in its own layer (recipe sub-agent instructions).

## ZIEL-REPO

mas-engineer (mczardybon/mas-engineer)
Branch: mas-mq (current as of R110-169)
Parent-Commit: 838ce0d (R110-169 phase 4)
Ref: R110-165 (MQ-1 publishers, commit 266ceb7),
     R110-166 (MQ-2 consumers, commit 2e0963b),
     R110-168 (phoenix consumer, commit 221a520),
     R110-169 (auto-escalation, commit 838ce0d)

================================================================
DIREKTIVE 1: ADD MQ-ECOSYSTEM-TEST-PATTERN section to
             recipe/instructions/sub_mas-dev-tester.md
================================================================

Aktueller zustand: sub_mas-dev-tester.md describes test patterns
for mas-engineer's test suite but has no guidance specific to
MQ-consumer workflows. The next time mas-engineer writes a
consumer test (e.g. for a new topic), it will hit the same
5 traps that R110-168+169 hit.

Add a new section "MQ-CONSUMER TEST PATTERN" (after the existing
"PYTEST ISOLATION" section) with the following hard rules:

  1. SOURCE OF TRUTH FOR PROCESSOR OUTPUT:
     `dev_mq_consumer.py` returns an ENVELOPE on stdout
     (keys: result, msg_id, topic, consumer_id, elapsed_ms,
     processor, reason, count). The processor's return value
     is NOT in the envelope. To assert on processor output
     (e.g. `final_status`, `attention_required`,
     `escalation_msg_id`), read the per-request log file
     written by the processor:
       - .mase/phoenix_logs/<request_id>.json (for
         wf_phoenix_log_persist)
       - .mase/recovery/log/<request_id>.json (for
         wf_recovery_defib)
       - .mase/patches/<request_id>.json (for
         wf_im_design_patches)

  2. USE THE PUBLIC MQ API:
       - `mq.depth(topic)` for topic depth
         (NOT `mq.topic_depth()` — that does not exist)
       - `mq._read_topic(topic, include_in_flight=True)` for
         peek operations
         (NOT `mq.peek_topic()` — that does not exist)

  3. ISOLATE EVERY TEST:
       - monkeypatch MAS_MQ_ROOT to a tmp dir
       - monkeypatch MAS_PHOENIX_LOG_DIR to a tmp dir
       - monkeypatch MAS_RECOVERY_LOG_DIR to a tmp dir
     Without these, the consumer writes to
     <real-repo>/.mase/* which pollutes the live state.

  4. UNIQUE REQUEST_ID PER TEST RUN:
       - Format: f"{prefix}-{int(time.time()*1000)}-
         {uuid.uuid4().hex[:6]}"
       - Reason: MQ-2 dedup is keyed on (payload_hash, topic)
         but reusing a request_id overwrites the
         per-request log file
       - The escalation-id (when using cross-topic
         escalation) MUST be unique even if the source
         request_id is the same

  5. SUBPROCESS, NOT IN-PROCESS:
       - Always run dev_mq_consumer.py via
         `subprocess.run([sys.executable,
         "tools/dev_mq_consumer.py", ...])`
       - In-process calls miss env-var propagation and
         lock-file behavior
       - The first iteration of a new consumer test MUST
         run in subprocess to exercise the same code path
         the workflow runtime will see

These rules come from 5 real bugs hit during R110-168+169:
  - P4.1.1 KeyError on stdout["final_status"]
    (envelope vs processor output)
  - P4.1.2 attempted `mq.topic_depth()` (does not exist)
  - P4.1.2 attempted `mq.peek_topic()` (does not exist)
  - R110-165 lesson: real-repo pollution without env vars
  - R110-165 lesson: MQ-2 dedup collision on reused
    request_ids

================================================================
DIREKTIVE 2: ADD CROSS-TOPIC AUTO-ESCALATION section to
             recipe/instructions/sub_mas-dev-builder.md
================================================================

Aktueller zustand: sub_mas-dev-builder.md describes how to
build new tools but has no guidance for the publisher-re-
publishes-to-recovery-topic pattern that R110-169 used.

Add a new section "CROSS-TOPIC AUTO-ESCALATION" (after the
existing "PUBLISHER PATTERN" section) with these rules:

  1. ESCALATION PAYLOAD SHAPE:
     Must match the recovery topic's existing schema. The
     defib consumer expects (command, summary) at the top
     level. Use:
       {
         "request_id": <UNIQUE esc-id>,
         "source": "<source-component>",
         "command": "<X>_DEGRADED",
         "has_problem": true,
         "issues_found": N,
         "findings_count": 0,
         "summary": {
           "<orig_request_id_key>": <orig>,
           ...structured failure data...
         }
       }

  2. UNIQUE ESCALATION-ID:
     The escalation request_id MUST be unique even when the
     source request_id is the same — the recovery consumer
     writes a per-request log file at
     .mase/recovery/log/<request_id>.json and reusing an id
     overwrites. The source request_id belongs in
     `summary.<orig_request_id_key>` instead.

  3. WRAP ENQUEUE IN TRY/EXCEPT:
     An MQ outage during escalation must not lose the
     source log. Surface `escalation_error` in the
     process_msg return value so the orchestrator can
     display a banner; the log file is still on disk
     for manual inspection.

  4. REWRITE LOG WITH ESCALATION_MSG_ID:
     After enqueueing, re-write the per-run log with
     `escalation_msg_id` set. The log file is the audit
     source-of-truth; tests can
     `assert log["escalation_msg_id"]` without depending
     on the process_msg return value.

  5. DISPATCH BRANCH IN RECOVERY CONSUMER:
     Add a classify branch (e.g. command == "PHOENIX_DEGRADED"
     -> "phoenix_recovery_incomplete") AND a dispatch
     branch (e.g. phoenix_recovery_incomplete ->
     "rebuild_<X>" with the originating request_id and
     degraded levels). Use a `note: "delegated to wf_<X>"`
     field until the rebuild workflow is actually wired —
     do not invent a parallel rebuild pipeline.

================================================================
DIREKTIVE 3: UPDATE STATUS.md with R110-126 entry
================================================================

Aktueller zustand: STATUS.md is the mas-engineer internal
tracker for directive completion. Add a new entry for
R110-126 with the standard table format used by R110-94
and R110-118.

The R110-126 row should record:
  - 2 DIREKTIVE blocks (dev-tester + dev-builder
    instruction updates)
  - Expected effect: future MQ-consumer test work
    follows the 5+5 rules without hermes-side prompting
  - The hermes-side skills
    (mas-engineer-mq-ecosystem-test-pattern,
    mas-engineer-mq-cross-topic-escalation) remain as
    hermes-layer references; R110-126 is the
    mas-engineer-side mirror

================================================================
VERIFICATION (for sub_mas-apply-directive)
================================================================

After applying R110-126, run:

  python3 -m pytest tests/test_dev_phase3_phoenix_log.py \
                    tests/test_dev_phase4_escalation.py -v

Expected: 11 passed (6 from R110-168 + 5 from R110-169).
This is the regression check: R110-126 codifies the rules
that made those 11 tests pass, so they must continue to
pass after the directive is applied.

ALSO: grep the new sub_mas-dev-tester.md and
sub_mas-dev-builder.md sections for the 10 key phrases
("ENVELOPE", "depth(topic)", "_read_topic",
"MAS_MQ_ROOT", "unique request_id", "subprocess.run",
"UNIQUE ESCALATION-ID", "WRAP ENQUEUE", "REWRITE LOG",
"DISPATCH BRANCH") to confirm the directive was applied
verbatim.
