#!/usr/bin/env python3
"""Run connector ingest against the in-memory or configured sensory path.

Examples:
  python scripts/run_ingest.py --rss demo|https://hnrss.org/frontpage
  python scripts/run_ingest.py --rss a|https://example.com/feed.xml --once
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.connectors import IngestService
from brain.connectors.protocol import AccessDisposition
from brain.heartbeat import build_default_heartbeat


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest due connector sources into sensory inbox")
    parser.add_argument(
        "--rss",
        action="append",
        default=[],
        help="source_key|url|refresh_seconds (repeatable)",
    )
    parser.add_argument("--once", action="store_true", default=True)
    parser.add_argument("--think", type=int, default=0, help="Run N cognition ticks after ingest")
    args = parser.parse_args()

    hb = build_default_heartbeat(with_learning=True)
    hb.bootstrap_mind()
    svc = IngestService(inbox=hb.inbox, event_store=hb.event_store)

    for raw in args.rss:
        bits = [b.strip() for b in raw.split("|")]
        if len(bits) < 2:
            print(f"skip invalid --rss {raw!r}", file=sys.stderr)
            continue
        refresh = int(bits[2]) if len(bits) > 2 and bits[2].isdigit() else 300
        svc.register_rss(
            source_key=bits[0],
            url=bits[1],
            name=bits[0],
            refresh_seconds=refresh,
            access=AccessDisposition.ALLOWED,
        )
        print(f"registered {bits[0]} -> {bits[1]}")

    if not svc.registry.list_sources():
        print("No sources registered. Pass --rss key|url", file=sys.stderr)
        return 2

    batch = svc.ingest_due_sources()
    print(json.dumps(batch.as_dict(), indent=2))
    print("inbox", hb.inbox.stats())

    if args.think > 0:
        snap = hb.tick(max_items=args.think)
        print("cognition", {k: snap[k] for k in ("ticks", "processed_this_call", "total_processed")})
        print("status", hb.status().get("mind"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
