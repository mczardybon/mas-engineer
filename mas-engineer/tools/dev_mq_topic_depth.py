#!/usr/bin/env python3
"""dev_mq_topic_depth.py — print current depth of a message-queue topic.

Usage:
  python3 tools/dev_mq_topic_depth.py <topic>

Prints a single number (the depth = number of pending, non-acked
messages in the topic's NDJSON file). Exits 0 if depth>=0, 1 on error.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MQ_ROOT = REPO_ROOT / ".mase" / "mq"


def topic_to_filename(topic: str) -> str:
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in topic)
    return f"{safe}.ndjson"


def main():
    if len(sys.argv) < 2:
        print("usage: dev_mq_topic_depth.py <topic>", file=sys.stderr)
        return 1
    topic = sys.argv[1]
    path = MQ_ROOT / topic_to_filename(topic)
    if not path.exists():
        print(0)
        return 0
    with open(path) as f:
        depth = sum(1 for _ in f)
    print(depth)
    return 0


if __name__ == "__main__":
    sys.exit(main())
