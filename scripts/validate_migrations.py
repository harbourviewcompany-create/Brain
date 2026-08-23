#!/usr/bin/env python3
"""Validate Brain SQL migration ordering and duplicate-version policy."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "db" / "migrations"
LEGACY_DUPLICATE_ALLOWLIST = {
    6: {
        "006_money_spine.sql",
        "006_working_memory_predictions_learning.sql",
    }
}


def fail(message: str) -> None:
    raise SystemExit(f"Migration validation failed: {message}")


def main() -> None:
    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files:
        fail("no SQL migrations found")
    by_version: dict[int, set[str]] = defaultdict(set)
    for path in files:
        match = re.match(r"^(\d{3})_[a-z0-9_]+\.sql$", path.name)
        if match is None:
            fail(f"invalid migration filename: {path.name}")
        version = int(match.group(1))
        by_version[version].add(path.name)
        text = path.read_text(encoding="utf-8").lower()
        if "create table" in text and "if not exists" not in text:
            fail(f"migration must be replay-safe for create-table operations: {path.name}")

    for version, names in by_version.items():
        if len(names) <= 1:
            continue
        allowed = LEGACY_DUPLICATE_ALLOWLIST.get(version)
        if allowed != names:
            fail(f"duplicate migration version {version:03d}: {', '.join(sorted(names))}")

    versions = sorted(by_version)
    if versions[0] != 1:
        fail("migration sequence must start at 001")
    missing = [version for version in range(1, max(versions) + 1) if version not in by_version]
    if missing:
        fail("missing migration versions: " + ", ".join(f"{version:03d}" for version in missing))
    if max(versions) >= 7:
        for version in range(7, max(versions) + 1):
            if len(by_version[version]) != 1:
                fail(f"post-legacy migration version {version:03d} must be unique")

    print(
        "Migration validation: GO "
        f"({len(files)} files, versions 001-{max(versions):03d}; legacy 006 duplicate recorded)"
    )


if __name__ == "__main__":
    main()
