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

from tools.verify_runtime_grant_coverage import (
    EXPECTED_UNGRANTED,
    FORBIDDEN_PRIVILEGES,
    FULL_DML,
    READ_ONLY_TABLES,
    TRUSTED_SERVICE_ONLY,
    TRUSTED_SERVICE_PRIVILEGES,
    required_privileges,
)

ROOT = Path(__file__).resolve().parents[1]
# tools/ is excluded on purpose: those scripts connect with the migration DSN as
# the table owner, so they are not bound by brain_runtime_role's privileges.
RUNTIME_DIRS = ("brain", "apps")


def _runtime_python_files() -> list[Path]:
    """Return the modules that run under the constrained runtime login.

    Test files are excluded by name pattern, and tools/ is out of scope entirely:
    those scripts connect with the migration DSN as the table owner, so they are
    not bound by brain_runtime_role's privileges.
    """

    files: list[Path] = []
    for directory in RUNTIME_DIRS:
        for path in (ROOT / directory).rglob("*.py"):
            if path.name.startswith("test_") or path.name.endswith("_test.py"):
                continue
            files.append(path)
    return files


def test_every_withheld_table_has_a_stated_reason():
    """A withheld table without a reason is an assertion nobody can re-evaluate.

    The list is the only record of why the runtime is denied these, so an unexplained
    entry becomes permanent by default.
    """

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


def test_a_withheld_table_requires_no_privilege_at_all():
    """Withheld means withheld: requiring even SELECT would contradict the list."""

    for table in EXPECTED_UNGRANTED:
        assert required_privileges(table) == ()


def test_read_only_and_withheld_sets_do_not_overlap():
    """A table in both lists would make its required privileges ambiguous."""
    assert not (READ_ONLY_TABLES.keys() & EXPECTED_UNGRANTED.keys())


def test_every_read_only_table_has_a_stated_reason():
    """Same contract as the withheld list, for the tables the runtime may read."""

    for table, reason in READ_ONLY_TABLES.items():
        assert reason.strip(), f"{table} is read-only without a reason"


def test_a_tenant_owned_table_needs_more_than_select():
    """Reachability is not a single bit.

    A tenant-owned table is read and written through the ordinary adapters, so a
    later migration narrowing its grant to SELECT would break writes at runtime
    while a SELECT-only check stayed green.
    """
    assert required_privileges("beliefs") == FULL_DML
    assert required_privileges("brain_events") == FULL_DML


def test_the_worker_only_tables_are_withheld_from_the_api_runtime():
    """Migration 026 on main revokes these from the runtime role entirely.

    brain/connectors/service.py is imported only by apps/worker/main.py, and the
    tenant API's TenantRevenueStore overrides every global write to a no-op, so
    the ordinary API runtime needs nothing here. Requiring privileges for it would
    widen the surface past what any caller uses.
    """
    for table in (
        "source_connector_runtime_state",
        "source_connector_ingestion_runs",
        "source_connector_observations",
        "money_lanes",
        "revenue_source_scores",
    ):
        assert table in TRUSTED_SERVICE_ONLY
        assert required_privileges(table) == ()


def test_the_worker_only_set_does_not_overlap_the_other_classifications():
    """A table in two classifications has ambiguous required privileges."""

    assert not (TRUSTED_SERVICE_ONLY.keys() & EXPECTED_UNGRANTED.keys())
    assert not (TRUSTED_SERVICE_ONLY.keys() & READ_ONLY_TABLES.keys())
    for table, reason in TRUSTED_SERVICE_ONLY.items():
        assert reason.strip(), f"{table} is worker-only without a reason"


def test_delete_is_not_required_of_the_trusted_worker():
    """Migration 026 grants the worker SELECT, INSERT and UPDATE -- not DELETE."""
    assert TRUSTED_SERVICE_PRIVILEGES == ("select", "insert", "update")


def test_truncate_is_never_a_required_privilege():
    """TRUNCATE is an upper bound, never a requirement.

    PostgreSQL does not apply row level security to TRUNCATE, so a tenant runtime
    holding it could empty every tenant's rows from a table whose per-row policies
    look airtight. `grant all` hands it over silently.
    """
    assert "truncate" in FORBIDDEN_PRIVILEGES
    assert not set(FORBIDDEN_PRIVILEGES) & set(FULL_DML)
    for table in ("beliefs", "money_lanes", "brain_region_maps"):
        assert not set(required_privileges(table)) & set(FORBIDDEN_PRIVILEGES)


def test_policy_commands_cover_every_privilege_that_can_be_required():
    """A privilege with no pg_policy.polcmd letter would silently skip its check.

    policy_coverage_gaps() looks each required privilege up in this map; a missing
    entry would raise KeyError, or worse, be quietly excluded if the lookup were
    ever made forgiving.
    """
    from tools.verify_runtime_grant_coverage import _POLICY_COMMANDS

    for privilege in FULL_DML:
        assert privilege in _POLICY_COMMANDS
    assert set(_POLICY_COMMANDS.values()) == {"r", "a", "w", "d"}
