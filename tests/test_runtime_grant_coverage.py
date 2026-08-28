"""The constrained runtime login must be able to reach every table it queries.

Migrations 021, 022 and 025 grant privileges through loops evaluated at migration
time, so they cannot cover a table created by a later migration, nor a pre-tenant
table that carries no `tenant_id`. tools/verify_runtime_grant_coverage.py proves the
resulting property against a real database in CI; these tests keep its exclusion
list honest and keep migration 026's grants from being quietly dropped, in the
ordinary suite that runs everywhere.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.verify_runtime_grant_coverage import EXPECTED_UNGRANTED

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "db" / "migrations" / "026_runtime_grants_for_post_022_tables.sql"
# tools/ is excluded on purpose: those scripts connect with the migration DSN as
# the table owner, so they are not bound by brain_runtime_role's privileges.
RUNTIME_DIRS = ("brain", "apps")
VERIFIER = "verify_runtime_grant_coverage.py"

# Reproduced against PostgreSQL 16 with migrations 001-025 applied: as a
# brain_runtime_role member every one of these fails with "permission denied
# for table", while a granted table such as `beliefs` succeeds.
PREVIOUSLY_UNREACHABLE = (
    "money_lanes",
    "revenue_source_scores",
    "source_connector_runtime_state",
    "source_connector_ingestion_runs",
    "source_connector_observations",
)


def _runtime_python_files() -> list[Path]:
    files: list[Path] = []
    for directory in RUNTIME_DIRS:
        for path in (ROOT / directory).rglob("*.py"):
            if path.name == VERIFIER or "test" in path.name:
                continue
            files.append(path)
    return files


def test_every_withheld_table_has_a_stated_reason():
    assert EXPECTED_UNGRANTED, "expected a non-empty exclusion list"
    for table, reason in EXPECTED_UNGRANTED.items():
        assert reason.strip(), f"{table} is withheld without a reason"


def test_no_withheld_table_is_referenced_by_runtime_code():
    """A reader for a withheld table means the exclusion, not the query, is wrong.

    Without this the exclusion list would silently absorb the next occurrence of
    the bug it was written to describe: someone adds an adapter for a table nobody
    had queried, and the database verifier keeps passing because the table is
    still listed as deliberately unreachable.
    """
    offenders: dict[str, list[str]] = {}
    files = _runtime_python_files()
    assert files, "expected runtime sources to scan"
    for path in files:
        source = path.read_text()
        for table in EXPECTED_UNGRANTED:
            if re.search(rf"\b{re.escape(table)}\b", source):
                offenders.setdefault(table, []).append(str(path.relative_to(ROOT)))
    assert not offenders, (
        "tables withheld from brain_runtime_role are referenced by runtime code: "
        f"{offenders}"
    )


def test_migration_026_grants_every_previously_unreachable_table():
    sql = MIGRATION.read_text()
    for table in PREVIOUSLY_UNREACHABLE:
        assert table in sql, f"{table} lost its grant in migration 026"
    assert "to brain_runtime_role" in sql


def test_global_catalogue_stays_read_only_for_a_tenant_runtime():
    """Lane priorities and source scores are global learning state.

    Granting a per-tenant runtime write access to them would let one tenant's
    outcomes move another's, which is why 026 splits the grant by role instead of
    handing `brain_runtime_role` the same DML it gets on tenant-owned tables.
    """
    sql = MIGRATION.read_text()
    assert "grant select on table public.%I to brain_runtime_role" in sql
    assert "grant insert, update, delete on table public.%I to brain_trusted_service_role" in sql
    assert "current_brain_service_context()" in sql
