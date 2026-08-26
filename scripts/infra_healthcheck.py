#!/usr/bin/env python3
"""Print infrastructure health for Postgres, Neo4j, Temporal, and object storage."""

from __future__ import annotations

import json
import sys

from brain.adapters.infra_health import infrastructure_status


def main() -> int:
    status = infrastructure_status()
    print(json.dumps(status, indent=2))
    return 0 if status.get("all_configured_healthy") else 1


if __name__ == "__main__":
    raise SystemExit(main())
