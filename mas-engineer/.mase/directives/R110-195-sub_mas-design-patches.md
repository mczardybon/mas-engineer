# sub_mas-design-patches — directive (R110-195, MQ Full Adoption)

R110-194-B / R110-195, branch `mas-mq`. Wired the existing
`im.finding.created` topic consumer into a real workflow that
calls `dev_im_design_patches.process_msg()` per message.

This is the **DESIGN half** of the consume-and-design loop. The
**CONSUME half** is the python `tools/dev_mq_consumer.py`
(driven by the `wf_im_consume_findings.yaml` recipe).

```
im.finder (R110-154, R110-192)
    │
    │  enqueue to im.finding.created
    ▼
.mase/mq/topics/im.finding.created/pending.ndjson
    │
    │  dev_mq_consumer.py drains with --processor tools.dev_im_design_patches:process_msg
    │  per msg: lease (R-211) → process_msg() → ack
    ▼
.mase/im/patches/<request_id>.yaml       ◄── THIS sub_recipe owns this write
    │
    │  (later) a human / director recipe applies the patch
    ▼
real source-file change
```

## Why R110-195 was needed (R110-194-B context)

After R110-192 the **produce** side worked: im-finder could
publish findings to the MQ topic. But there was no **consume**
side. 100 findings enqueued → 100 sit in `pending.ndjson`
forever.  R110-195 closes the loop by:

1. Adding `recipe/wf_im_consume_findings.yaml` — the workflow
   that drains the topic.
2. Adding `recipe/sub/sub_mas-design-patches.yaml` — the
   per-message sub_recipe (1 level deep) that calls the
   existing `dev_im_design_patches.process_msg` kernel.
3. Wiring the consumer's `--processor` to that kernel.
4. Adding `tests/test_dev_im_design_patches.py` — 3 pytest
   tests verifying the loop end-to-end (covered in
   `.directives/sub_mas-design-patches-consumer.md`, Item C).

## Where the python work lives

- `tools/dev_mq_consumer.py`  — the loop driver (R110-193).
  CLI: `--topic im.finding.created --consumer-id im-design-loop
   --processor tools.dev_im_design_patches:process_msg
   --timeout 300 --max-messages 1000`
- `tools/dev_im_design_patches.py` — the deterministic
  per-msg design kernel. Takes the MQ envelope, writes
  `.mase/im/patches/<request_id>.yaml`. (R110-191, R110-192.)
- `tools/dev_message_queue.py` — the MQ itself (R110-154).
- `tools/dev_im_finder_scan.py` — the producer (R110-192).
  Only the producer calls `mq.enqueue(...)`.

The sub_recipe DOES NOT do any of the IO itself. Its only
job is to bind the python pieces together with explicit
verify-on-each-invocation STEP 0.

## Single-consumer invariant (R-211)

`.directives/dev_mq_consumer.md` documents the
`_check_single_consumer` guard. R110-195 respects it: this
workflow is the SOLE consumer of `im.finding.created`. If a
second consumer is started on the same topic, the second one
returns rc=3 and exits without draining. This is intentional
— duplicate consumers would split the ack stream and
double-write patches.

## Evidence (R10)

- `tools/dev_mq_consumer.py` (R110-193) — the loop driver
- `tools/dev_im_design_patches.py` (R110-191/192) — the kernel
- `tools/dev_message_queue.py` (R110-154) — the MQ
- `tools/dev_im_finder_scan.py` (R110-192) — the producer
- `tests/test_dev_im_design_patches.py` — R110-195 pytest
  (3 tests: drain→patch, no-topic→no-side-effect, kernel
  raises → nack not ack)
- `recipe/wf_im_consume_findings.yaml` — R110-195 workflow
- `recipe/sub/sub_mas-design-patches.yaml` — R110-195
  sub_recipe
- `.mase/im_apply_only_log` — patch-application log
  (kernel writes, human applies)

## Anti-theater (R110-194)

This sub_recipe does NOT auto-apply patches. It designs them
and writes the .yaml.  A separate human-approved step
applies them. The im_apply_only_log is the audit trail
of patch APPLICATION (not design), per
`.directives/im-pipeline.md`.

## Rollback (R10-7)

If R110-195 is found to double-write patches, ROLLBACK by:

1. Stop the consumer (SIGTERM the running `dev_mq_consumer.py`
   process — it has a R-211 SIGTERM handler that releases
   the in_flight lease).
2. Revert commit R110-195 (1 file in
   `recipe/sub/sub_mas-design-patches.yaml` +
   1 file in `recipe/wf_im_consume_findings.yaml` +
   1 file in `.directives/sub_mas-design-patches.md` +
   1 new test file).
3. Existing patches in `.mase/im/patches/` are NOT deleted
   by the rollback — they are independently consumable
   design artifacts.

## Date

2026-08-18 (R110-195, mas-mq branch).
