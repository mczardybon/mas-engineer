#!/usr/bin/env python3
"""dev_mq_consumer.py — R110-166 phase 2: consume-and-process helper.

Wraps the dev_message_queue consume → process → ack/nack pattern into a
single CLI call, so workflow YAML stays declarative. Used by
wf_im_design_patches (consumes im.finding.created) and
wf_recovery_defib (consumes monitor.health.degraded).

USAGE
  python3 tools/dev_mq_consumer.py \\
      --topic im.finding.created \\
      --consumer-id wf_im_design_patches \\
      --processor tools.dev_im_design_patches:process_msg \\
      --timeout 30 \\
      [--max-messages 1]

EXIT CODES
  0 = message processed + acked
  1 = no message on topic within timeout (idle, not an error)
  2 = processor raised an exception (msg was NACKed with reason)
  3 = unexpected error (msg left in_flight for retry)

OUTPUT (JSON to stdout)
  {
    "result": "acked" | "no-message" | "nacked" | "error",
    "msg_id": "<uuid or null>",
    "topic": "<topic>",
    "consumer_id": "<id>",
    "elapsed_ms": <int>,
    "processor": "<module:func>",
    "reason": "<nack reason or null>",
  }
"""
import argparse
import importlib
import json
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR.parent))  # so `import dev_message_queue` works
sys.path.insert(0, str(TOOLS_DIR))         # so processor module imports work

import dev_message_queue as mq

# R-211: TTL for in_flight leases — single source of truth for the
# periodic stale-lease GC (matches mq.gc_stale_in_flight's default).
IN_FLIGHT_LEASE_TTL_SEC = 300

# R-211: tracks the msg_id currently held in_flight so the SIGTERM
# handler can release the lease before exiting cleanly.
_in_flight_lease = {"msg_id": None}


def _handle_sigterm(signum, frame):
    """Release any held in_flight lease, then exit cleanly (R-211)."""
    msg_id = _in_flight_lease["msg_id"]
    if msg_id:
        try:
            mq.nack(msg_id, reason="consumer terminated (SIGTERM): in_flight lease released")
        except Exception:
            pass
    sys.exit(0)


def _check_single_consumer(topic: str, consumer_id: str) -> Optional[str]:
    """Return another consumer-id holding an in_flight lease on `topic`.

    R-211: reuses the message-queue's per-message `consumer_id` lease
    field (set by mq.consume when a msg goes in_flight) as the
    single-consumer-per-topic uniqueness mechanism: if any msg on the
    topic is in_flight under a different consumer-id, that consumer is
    still actively processing — starting another would cause duplicate
    dispatch.  Returns None when we are the only active consumer.
    """
    try:
        msgs = mq._read_topic(topic)
    except Exception:
        return None
    for m in msgs:
        if m.get("status") == "in_flight":
            holder = m.get("consumer_id")
            if holder and holder != consumer_id:
                return holder
    return None


def _load_processor(spec: str):
    """Load a processor callable from 'module.path:func_name'."""
    if ":" not in spec:
        raise ValueError(
            f"--processor must be 'module.path:func_name', got: {spec!r}"
        )
    mod_name, func_name = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, func_name, None)
    if fn is None:
        raise AttributeError(
            f"module {mod_name!r} has no function {func_name!r}"
        )
    return fn


def _find_msg_full(msg_id: str):
    """Locate a msg (even in_flight) and return the full dict, or None.

    mq._find_msg returns (topic, (idx, msg, all_msgs)) or None.
    We unwrap and return just the msg dict.
    """
    found = mq._find_msg(msg_id)
    if found is None:
        return None
    _topic, (idx, msg, _all) = found
    if msg.get("status") == "completed":
        # Already archived — for processor purposes we only consume
        # in_flight msgs, so this means someone else ack'd it. Skip.
        return None
    return msg


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--topic", required=True)
    ap.add_argument("--consumer-id", required=True)
    ap.add_argument("--processor", required=True,
                    help="'module.path:func_name' — called with msg dict, returns None or dict to merge back")
    ap.add_argument("--timeout", type=float, default=60.0,
                    help="consume timeout in seconds (default 60)")
    ap.add_argument("--max-messages", type=int, default=1,
                    help="how many msgs to process before exiting (default 1)")
    args = ap.parse_args()

    # R-211: release in_flight lease (if held) on SIGTERM, then exit cleanly.
    signal.signal(signal.SIGTERM, _handle_sigterm)

    # R-211: enforce single-consumer-per-topic — if another consumer-id
    # already holds an in_flight lease on this topic, refuse to start.
    other_consumer = _check_single_consumer(args.topic, args.consumer_id)
    if other_consumer:
        print(json.dumps({
            "result": "error",
            "msg_id": None,
            "topic": args.topic,
            "consumer_id": args.consumer_id,
            "elapsed_ms": 0,
            "processor": args.processor,
            "reason": (f"single-consumer violation: consumer {other_consumer!r} already "
                       f"holds an in_flight lease on topic {args.topic!r}"),
        }, indent=2))
        return 3

    try:
        processor = _load_processor(args.processor)
    except (ValueError, ImportError, AttributeError) as e:
        print(json.dumps({
            "result": "error",
            "msg_id": None,
            "topic": args.topic,
            "consumer_id": args.consumer_id,
            "elapsed_ms": 0,
            "processor": args.processor,
            "reason": f"processor-load-failed: {e!r}",
        }, indent=2))
        return 3

    overall_start = time.monotonic()
    processed = 0
    while processed < args.max_messages:
        # gc stale in_flight msgs (best-effort, cheap) — R-211: TTL is a
        # module constant so it stays in sync everywhere.
        try:
            mq.gc_stale_in_flight(max_age_sec=IN_FLIGHT_LEASE_TTL_SEC)
        except Exception:
            pass

        # consume (blocks up to timeout)
        start = time.monotonic()
        try:
            msg = mq.consume(args.topic, args.timeout, consumer_id=args.consumer_id)
        except Exception as e:
            print(json.dumps({
                "result": "error",
                "msg_id": None,
                "topic": args.topic,
                "consumer_id": args.consumer_id,
                "elapsed_ms": int((time.monotonic() - overall_start) * 1000),
                "processor": args.processor,
                "reason": f"consume-failed: {e!r}",
            }, indent=2))
            return 3

        if msg is None:
            # no message in the time window
            if processed == 0:
                print(json.dumps({
                    "result": "no-message",
                    "msg_id": None,
                    "topic": args.topic,
                    "consumer_id": args.consumer_id,
                    "elapsed_ms": int((time.monotonic() - overall_start) * 1000),
                    "processor": args.processor,
                    "reason": f"no message on {args.topic} within {args.timeout}s",
                }, indent=2))
                return 1
            else:
                break

        msg_id = msg.get("msg_id", "?")
        # R-211: we now hold the in_flight lease — record it so SIGTERM
        # can release it before exit.
        _in_flight_lease["msg_id"] = msg_id
        # fetch the in_flight copy (more reliable than the snapshot from consume)
        full_msg = _find_msg_full(msg_id)
        if full_msg is None:
            # race: msg got ack'd between consume and _find_msg — skip
            _in_flight_lease["msg_id"] = None
            processed += 1
            continue

        # PROCESSOR
        try:
            result = processor(full_msg)
        except Exception as e:
            tb = traceback.format_exc(limit=4)
            reason = f"processor-exception: {type(e).__name__}: {e}"
            try:
                mq.nack(msg_id, reason=reason)
            except Exception as ne:
                reason = f"{reason}; ALSO nack-failed: {ne!r}"
            # R-211: nack released the lease (or we're exiting regardless)
            _in_flight_lease["msg_id"] = None
            print(json.dumps({
                "result": "nacked",
                "msg_id": msg_id,
                "topic": args.topic,
                "consumer_id": args.consumer_id,
                "elapsed_ms": int((time.monotonic() - overall_start) * 1000),
                "processor": args.processor,
                "reason": reason,
                "traceback": tb,
            }, indent=2))
            return 2

        # ACK
        try:
            ok = mq.ack(msg_id)
        except Exception as e:
            print(json.dumps({
                "result": "error",
                "msg_id": msg_id,
                "topic": args.topic,
                "consumer_id": args.consumer_id,
                "elapsed_ms": int((time.monotonic() - overall_start) * 1000),
                "processor": args.processor,
                "reason": f"ack-failed-after-process: {e!r}",
                "processor_result": result,
            }, indent=2))
            return 3

        if not ok:
            print(json.dumps({
                "result": "error",
                "msg_id": msg_id,
                "topic": args.topic,
                "consumer_id": args.consumer_id,
                "elapsed_ms": int((time.monotonic() - overall_start) * 1000),
                "processor": args.processor,
                "reason": "ack-returned-False (msg not in_flight?)",
                "processor_result": result,
            }, indent=2))
            return 3

        processed += 1
        # R-211: ack removed the msg from the topic — lease released.
        _in_flight_lease["msg_id"] = None
        # Single-message mode: stop after first.
        if args.max_messages == 1:
            break

    # max_messages reached
    print(json.dumps({
        "result": "acked",
        "msg_id": None,
        "topic": args.topic,
        "consumer_id": args.consumer_id,
        "elapsed_ms": int((time.monotonic() - overall_start) * 1000),
        "processor": args.processor,
        "count": processed,
        "reason": f"max-messages reached (drained {processed})",
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
