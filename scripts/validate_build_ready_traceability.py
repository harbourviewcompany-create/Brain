#!/usr/bin/env python3
"""Validate BUILD-READY traceability and migration integrity."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "control" / "module-build-ready-traceability.md"
POLICY = ROOT / "docs" / "control" / "policy-registry.json"
MIGRATIONS = ROOT / "db" / "migrations"
MIGRATION_NAME = re.compile(r"^(\d{3})_[a-z0-9][a-z0-9_]*\.sql$")
ALLOWED_MIGRATION_COLLISIONS = {
    "006": {
        "006_money_spine.sql",
        "006_working_memory_predictions_learning.sql",
    }
}

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


#: Directory names whose contents are installed dependencies or local
#: environments rather than repository source. Kept in step with
#: scripts/validate_control_layer.py, which discovers the same module set.
VENDORED_DIRECTORIES = frozenset(
    {"node_modules", "site-packages", ".venv", "venv", "build", "dist", ".next"}
)


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
            # Third-party trees are not ours to trace. Without this, running
            # `npm install` in apps/observatory makes the validator demand a
            # matrix row for vendored Python inside node_modules.
            if any(part in VENDORED_DIRECTORIES for part in path.parts):
                continue
            modules.add(rel)
    return sorted(modules)


def validate_migrations() -> None:
    if not MIGRATIONS.is_dir():
        fail("db/migrations directory is missing")
    versions: dict[str, set[str]] = defaultdict(set)
    files = sorted(path for path in MIGRATIONS.iterdir() if path.is_file())
    if not files:
        fail("no migrations found")
    for path in files:
        match = MIGRATION_NAME.match(path.name)
        if path.suffix == ".sql" and match is None:
            fail(f"malformed SQL migration filename: {path.name}")
        if match:
            versions[match.group(1)].add(path.name)

    numeric_versions = sorted(int(version) for version in versions)
    if not numeric_versions or numeric_versions[0] != 1:
        fail("migration sequence must begin at 001")
    expected = list(range(1, numeric_versions[-1] + 1))
    if numeric_versions != expected:
        missing = sorted(set(expected) - set(numeric_versions))
        fail("migration sequence has gaps: " + ", ".join(f"{item:03d}" for item in missing))

    for version, names in versions.items():
        if len(names) <= 1:
            continue
        allowed = ALLOWED_MIGRATION_COLLISIONS.get(version)
        if allowed is None:
            fail(f"duplicate migration version {version}: {', '.join(sorted(names))}")
        if names != allowed:
            fail(
                f"historical collision {version} changed: expected "
                f"{', '.join(sorted(allowed))}; got {', '.join(sorted(names))}"
            )
    for version, allowed in ALLOWED_MIGRATION_COLLISIONS.items():
        if versions.get(version, set()) != allowed:
            fail(f"preserved historical migration set {version} changed")


def table_rows(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("| ")]


def canonical_matrix_text(policy: dict) -> str:
    if not MATRIX.exists():
        fail(f"missing matrix file: {MATRIX.relative_to(ROOT)}")
    paths = [MATRIX]
    extensions = policy.get("traceability_policy", {}).get(
        "canonical_module_matrix_extensions", []
    )
    for rel in extensions:
        path = ROOT / rel
        if not path.is_file():
            fail(f"missing canonical matrix extension: {rel}")
        paths.append(path)
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def main() -> None:
    validate_migrations()
    policy = load_policy()
    module_paths = discover_modules(policy)
    text = canonical_matrix_text(policy)
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

    print(
        f"Module BUILD-READY traceability validation: GO "
        f"({len(module_paths)} enforced modules; migration integrity GO)"
    )


if __name__ == "__main__":
    main()
