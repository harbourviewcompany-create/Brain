#!/usr/bin/env python3
"""Validate per-module BUILD-READY traceability documentation.

This validator is dependency-free. It does not decide whether a Brain module
should be built. It enforces that currently enforced Python code paths are
represented in the traceability matrix and that no module is marked BUILD-READY
while unresolved HOLD/missing/partial fields remain.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "control" / "module-build-ready-traceability.md"
POLICY = ROOT / "docs" / "control" / "policy-registry.json"

REQUIRED_FIELDS = [
    "owner object",
    "schema",
    "runtime service",
    "state machine",
    "fixtures",
    "tests",
    "acceptance criteria",
    "audit events",
    "go/hold status",
]


def fail(message: str) -> None:
    raise SystemExit(f"BUILD-READY traceability validation failed: {message}")


def load_policy() -> dict:
    if not POLICY.exists():
        fail(f"missing policy file: {POLICY.relative_to(ROOT)}")
    return json.loads(POLICY.read_text(encoding="utf-8"))


def discover_modules(policy: dict) -> list[str]:
    traceability_policy = policy.get("traceability_policy", {})
    roots = traceability_policy.get("enforced_code_roots", ["apps", "brain", "scripts"])
    excluded = set(traceability_policy.get("excluded_filenames", ["__init__.py"]))
    modules: set[str] = set()
    for root in roots:
        root_path = ROOT / root
        if not root_path.exists():
            fail(f"traceability root does not exist: {root}")
        for path in root_path.rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if path.name in excluded:
                continue
            if "/__pycache__/" in rel or rel.startswith("tests/"):
                continue
            modules.add(rel)
    return sorted(modules)


def table_rows(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("| ")]


def main() -> None:
    if not MATRIX.exists():
        fail(f"missing matrix file: {MATRIX.relative_to(ROOT)}")

    policy = load_policy()
    module_paths = discover_modules(policy)
    text = MATRIX.read_text(encoding="utf-8")
    lower = text.lower()

    for field in REQUIRED_FIELDS:
        if field not in lower:
            fail(f"missing required field phrase: {field}")

    missing_paths = [path for path in module_paths if path not in text]
    if missing_paths:
        fail("missing module paths: " + ", ".join(missing_paths))

    if "build-ready" not in lower:
        fail("matrix must define BUILD-READY readiness rule")

    rows = table_rows(text)
    data_rows = [row for row in rows if any(path in row for path in module_paths)]
    if len(data_rows) < len(module_paths):
        fail(f"expected at least {len(module_paths)} module rows, found {len(data_rows)}")

    for row in data_rows:
        cells = [cell.strip().lower() for cell in row.strip("|").split("|")]
        if cells[-1] == "build-ready":
            if any(cell in {"missing", "partial", "blocked", "hold"} for cell in cells[1:-1]):
                fail("module marked BUILD-READY while unresolved fields remain: " + row)
        if cells[-1] != "hold":
            fail("runtime module rows must remain HOLD until all evidence is present: " + row)

    print(f"Module BUILD-READY traceability validation: GO ({len(module_paths)} enforced modules)")


if __name__ == "__main__":
    main()
