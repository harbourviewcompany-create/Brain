#!/usr/bin/env python3
"""Rebuild Neo4j projection from canonical Postgres graph state."""

from __future__ import annotations

import os
import sys


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    if not os.environ.get("NEO4J_URI"):
        print("NEO4J_URI is required", file=sys.stderr)
        return 2

    from brain.adapters.brain_store import PostgresBrainStore

    store = PostgresBrainStore(dsn)
    try:
        result = store.rebuild_neo4j_projection()
    finally:
        store.close()
    print(f"rebuilt neo4j projection: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
