#!/usr/bin/env python3
"""Fail closed on accidental duplicate or malformed SQL migration versions.

The repository already contains a historical collision at version 006. That
collision is explicitly preserved as source history; this validator prevents
new collisions from being introduced without silently renaming old migrations.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "db" / "migrations"
NAME = re.compile(r"^(\d{3})_[a-z0-9][a-z0-9_]*\.sql$")
ALLOWED_COLLISIONS = {
    "006": {
        "006_money_spine.sql",
        "006_working_memory_predictions_learning.sql",
    }
}


def fail(message: str) -> None:
    print(f"Migration validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not MIGRATIONS.is_dir():
        fail("db/migrations directory is missing")

    versions: dict[str, set[str]] = defaultdict(set)
    files = sorted(path for path in MIGRATIONS.iterdir() if path.is_file())
    if not files:
        fail("no migration files found")

    for path in files:
        match = NAME.match(path.name)
        if path.suffix == ".sql" and match is None:
            fail(f"malformed SQL migration filename: {path.name}")
        if match:
            versions[match.group(1)].add(path.name)

    collisions = {version: names for version, names in versions.items() if len(names) > 1}
    for version, names in collisions.items():
        allowed = ALLOWED_COLLISIONS.get(version)
        if allowed is None:
            fail(f"duplicate migration version {version}: {', '.join(sorted(names))}")
        if names != allowed:
            fail(
                f"historical collision {version} changed: expected "
                f"{', '.join(sorted(allowed))}; got {', '.join(sorted(names))}"
            )

    for version, allowed in ALLOWED_COLLISIONS.items():
        present = versions.get(version, set())
        if present != allowed:
            fail(
                f"preserved historical migration set {version} changed: expected "
                f"{', '.join(sorted(allowed))}; got {', '.join(sorted(present))}"
            )

    print(
        f"Migration validation: GO ({len(files)} files; "
        f"preserved collisions={','.join(sorted(ALLOWED_COLLISIONS))})"
    )


if __name__ == "__main__":
    main()
