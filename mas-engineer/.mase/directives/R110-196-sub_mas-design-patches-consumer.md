# sub_mas-design-patches-consumer — directive (R110-196)

R110-195 + R110-196. The CONSUMER-side counterpart of
`.directives/sub_mas-design-patches.md`.  R110-195 wired the
design sub_recipe and the workflow; R110-196 documents and
tests the consumer integration that drives it.

## Scope

This directive covers the consume-side contract: when
`tools/dev_mq_consumer.py` is run with
`--processor tools.dev_im_design_patches:process_msg`, what
MUST happen end-to-end (per-message), and what the 3 pytest
tests in `tests/test_dev_im_design_patches_consumer.py`
verify about that contract.

The design-side contract (what process_msg returns, what
the patch file looks like) is in
`.directives/sub_mas-design-patches.md`.  The two
directives are siblings, NOT a hierarchy.

## The end-to-end consume-side flow

For ONE message `m` on topic `im.finding.created`:

```
1. mq.consume(topic) returns m + a lease (R-211, in_flight)
2. consumer calls processor(m)
   processor = dev_im_design_patches.process_msg
3. process_msg writes .mase/im/patches/<request_id>.yaml
   (kernel: deterministic, idempotent on re-run)
4. consumer calls mq.ack(m.msg_id)  → lease released
5. mq stats: depth-1, completed+1, lag re-computed
```

If step 3 raises:
```
3'. exception propagates to consumer
4'. consumer calls mq.nack(m.msg_id, reason=...)
     → status back to "pending" (after backoff_schedule delay)
     → next consumer call re-delivers the same m
```

## Why the 3 consumer-side tests are needed

R110-195 added 3 tests for the **kernel** (process_msg in
isolation, tests/test_dev_im_design_patches.py).  Those
verify the patch file shape.  The CONSUMER-side tests
(here, tests/test_dev_im_design_patches_consumer.py)
verify that the consumer correctly:

  1. enqueue → consumer-loop → ack → patch file written
     (the positive loop, end-to-end through the consumer,
     NOT just process_msg in isolation)
  2. redelivery on ack: re-enqueue the SAME idempotency_key
     after the first ack → consumer's idempotency check
     (mq._msg_id_dedup) prevents double-ack
  3. processor raises → consumer nacks (not acks) the msg
     → mq.stats() shows retry_count=1, NOT completed+1
     (this is the negative half — kernel alone can't
      verify the nack path; the consumer must be in the loop)

These 3 tests are the ground truth for the
"consumer loop is real" claim.  Without them, R110-195's
wf_im_consume_findings.yaml could claim to drain the topic
and the only evidence would be a kernel test that never
involved a real MQ.

## R-211 invariant in the consumer

The consumer holds a per-msg lease (set via mq.consume).
If the consumer is killed (SIGTERM, OOM, Ctrl-C) WHILE
holding a lease, R-211's `_handle_sigterm` releases the
lease by calling mq.nack().  Without this, the msg would
be stuck in `in_flight` for the TTL (300s default) before
gc_stale_in_flight recovers it.  The consumer-side tests
do not exercise SIGTERM (that's R-211's own test suite
in tests/test_dev_mq_consumer.py); they exercise the
happy path and the nack path.

## Single-consumer guard (R-211)

`dev_mq_consumer._check_single_consumer(topic, consumer_id)`
returns the consumer_id of any other process holding an
in_flight lease on the topic.  If a second consumer starts
on the same topic, the second one returns rc=3 without
draining.  The consumer tests do not exercise this guard
in isolation (it's covered in
tests/test_dev_mq_consumer.py: R-211 single-consumer
guard), but the e2e test #1 implicitly relies on it: only
ONE consumer is running, so the ack goes to that one.

## Rollback (R10-7)

If R110-196's consumer tests fail in CI, rollback is:

1. Revert the test file (tests/test_dev_im_design_patches_consumer.py).
   No production code change in R110-196 — only directive
   + tests.
2. The kernel, workflow, and sub_recipe from R110-195
   are unaffected.

R110-196 is a TEST-ONLY commit.  No behavior change.
The behavior was already shipped in R110-195.

## Date

2026-08-18 (R110-196, mas-mq branch).
