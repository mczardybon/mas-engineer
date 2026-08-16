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
import sys
import time
import traceback
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR.parent))  # so `import dev_message_queue` works
sys.path.insert(0, str(TOOLS_DIR))         # so processor module imports work

import dev_message_queue as mq


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
    ap.add_argument("--timeout", type=float, default=30.0,
                    help="consume timeout in seconds (default 30)")
    ap.add_argument("--max-messages", type=int, default=1,
                    help="how many msgs to process before exiting (default 1)")
    args = ap.parse_args()

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
        # gc stale in_flight msgs (best-effort, cheap)
        try:
            mq.gc_stale_in_flight(max_age_sec=300.0)
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
        # fetch the in_flight copy (more reliable than the snapshot from consume)
        full_msg = _find_msg_full(msg_id)
        if full_msg is None:
            # race: msg got ack'd between consume and _find_msg — skip
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
