"""Verify the constrained runtime login holds the privileges its queries need.

Migrations 021, 022 and 025 hand out privileges through `do $$ ... $$` loops that
read `information_schema.columns` or iterate a literal array. Those loops are
evaluated once, when their migration runs, so they can only ever cover objects
that exist at that moment and match that migration's shape. An object created
later, or a pre-tenant table carrying no `tenant_id`, silently ends up with row
level security enabled and no grant at all -- invisible to the non-owner
`brain_runtime_role` login the release topology requires, while remaining fully
readable to the owner that CI and single-role installations happen to use.

That failure mode is not observable from the migration files alone, so this runs
against a real database after `tools/apply_migrations.py` and asserts the property
directly. Reachability is not a single bit: a table the runtime writes needs more
than SELECT, and an INSERT into a sequence-backed table needs USAGE on the
sequence that migration 022 granted once, in bulk, to the sequences that existed
then. So every public table is checked against the privilege set its callers
actually need, every public sequence against USAGE and SELECT, and the two
deliberately read-only global catalogues are checked for the *absence* of write
privileges so that boundary cannot widen unnoticed.
"""

from __future__ import annotations

import argparse
import os

import psycopg


RUNTIME_ROLE = "brain_runtime_role"

#: What a tenant-owned runtime table needs. The runtime reads and writes these
#: through the ordinary adapters, so SELECT alone is not reachability: narrowing
#: a grant to SELECT would leave inserts failing at runtime with CI still green.
FULL_DML: tuple[str, ...] = ("select", "insert", "update", "delete")

#: Sequence privileges migration 022 grants in bulk. An INSERT into a
#: sequence-backed table fails with "permission denied for sequence" without them.
SEQUENCE_PRIVILEGES: tuple[str, ...] = ("usage", "select")

# Tables the runtime may read but must never write. Checked in both directions:
# the SELECT must be present, and every write privilege must be absent.
READ_ONLY_TABLES: dict[str, str] = {
    # Migration 022 grants SELECT and then explicitly revokes DML. Tenant
    # lifecycle mutation waits on a durable administration service.
    "tenants": "read-only by migration 022",
    "tenant_memberships": "read-only by migration 022",
    # Global, pre-tenant catalogues carrying no tenant_id. Any runtime may read
    # them -- MoneySpineService loads both when the API builds its revenue spine
    # -- but only the audited trusted worker may mutate them, since a per-tenant
    # runtime writing global learning state would move one tenant's priorities
    # with another tenant's outcomes.
    "money_lanes": "global catalogue; mutable only under trusted service context",
    "revenue_source_scores": "global learning state; mutable only under trusted service context",
}

# Tables the constrained runtime login is deliberately not granted at all.
#
# Each entry must stay unreferenced by runtime SQL -- tests/test_runtime_grant_coverage.py
# fails if any of these names appears in a query under brain/ or apps/, so adding a
# reader forces the grant question back open rather than reintroducing the
# permission-denied class of bug this file exists to catch. tools/ is deliberately
# out of scope: those run under the migration DSN as the table owner.
EXPECTED_UNGRANTED: dict[str, str] = {
    # Created by tools/apply_migrations.py itself, not by a migration. Only the
    # migrator and the release verifiers read it, both under the migration DSN.
    "brain_schema_migrations": "migration ledger, owned by the migrator",
    # Migration 022 revokes these outright: invite and audit rows are reachable
    # only under trusted service context.
    "tenant_invites": "service-context only, revoked by migration 022",
    "tenant_audit_events": "service-context only, revoked by migration 022",
    # Migrations 008-010 registries. Documentation/traceability tables with no
    # runtime reader; they are populated by migration and read by operators.
    "brain_region_maps": "no runtime reader",
    "implementation_hypotheses": "no runtime reader",
    "mechanistic_gaps": "no runtime reader",
    "multiscale_cognition_dependencies": "no runtime reader",
    "multiscale_cognition_levels": "no runtime reader",
    "neuro_abstractions": "no runtime reader",
    "neuro_acceptance_reports": "no runtime reader",
    "neuro_scale_levels": "no runtime reader",
    "neuro_theories": "no runtime reader",
    "neuro_theory_conflicts": "no runtime reader",
    "neuro_unknown_mechanisms": "no runtime reader",
}


def _dsn(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def required_privileges(table: str) -> tuple[str, ...]:
    """Return the privileges `table` must grant the runtime role."""

    if table in EXPECTED_UNGRANTED:
        return ()
    if table in READ_ONLY_TABLES:
        return ("select",)
    return FULL_DML


def table_privileges(conn: psycopg.Connection) -> dict[str, set[str]]:
    rows = conn.execute(
        """
        select c.relname, p.privilege
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        cross join unnest(%s::text[]) as p(privilege)
        where n.nspname = 'public'
          and c.relkind = 'r'
          and has_table_privilege(%s, c.oid, p.privilege)
        """,
        (list(FULL_DML), RUNTIME_ROLE),
    ).fetchall()
    held: dict[str, set[str]] = {}
    for name, privilege in rows:
        held.setdefault(name, set()).add(privilege)
    return held


def public_tables(conn: psycopg.Connection) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace"
            " where n.nspname = 'public' and c.relkind = 'r' order by c.relname"
        ).fetchall()
    ]


def ungranted_sequences(conn: psycopg.Connection) -> list[tuple[str, str]]:
    """Return (sequence, missing privilege) pairs the runtime role cannot use."""

    rows = conn.execute(
        """
        select c.relname, p.privilege
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        cross join unnest(%s::text[]) as p(privilege)
        where n.nspname = 'public'
          and c.relkind = 'S'
          and not has_sequence_privilege(%s, c.oid, p.privilege)
        order by c.relname, p.privilege
        """,
        (list(SEQUENCE_PRIVILEGES), RUNTIME_ROLE),
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def verify(conn: psycopg.Connection) -> None:
    if conn.execute("select to_regrole(%s)", (RUNTIME_ROLE,)).fetchone()[0] is None:
        raise RuntimeError(f"{RUNTIME_ROLE} is missing; apply migration 019 first")

    present = public_tables(conn)
    held = table_privileges(conn)

    missing: list[str] = []
    excess: list[str] = []
    for table in present:
        required = set(required_privileges(table))
        actual = held.get(table, set())

        absent = sorted(required - actual)
        if absent:
            missing.append(f"{table} (missing {', '.join(absent)})")

        # A table listed as read-only or withheld must not quietly gain writes.
        # Only those two lists constrain the upper bound; a tenant-owned table
        # holding full DML is the expected case, not an excess.
        if table in READ_ONLY_TABLES or table in EXPECTED_UNGRANTED:
            unexpected = sorted(actual - required)
            if unexpected:
                excess.append(f"{table} (unexpected {', '.join(unexpected)})")

    if missing:
        raise RuntimeError(
            "the constrained runtime login lacks privileges its queries need: "
            + "; ".join(missing)
            + ". Grant them in a migration, or record the table in READ_ONLY_TABLES "
            "or EXPECTED_UNGRANTED in tools/verify_runtime_grant_coverage.py with a reason."
        )
    if excess:
        raise RuntimeError(
            "tables documented as read-only or withheld hold write privileges: "
            + "; ".join(excess)
            + ". Revoke them, or update tools/verify_runtime_grant_coverage.py if the "
            "trust boundary really did change."
        )

    sequence_gaps = ungranted_sequences(conn)
    if sequence_gaps:
        raise RuntimeError(
            "the constrained runtime login cannot use sequences its inserts need: "
            + "; ".join(f"{name} (missing {privilege})" for name, privilege in sequence_gaps)
            + ". Migration 022's `grant ... on all sequences` covers only the sequences "
            "that existed when it ran, so a later sequence needs its own grant."
        )

    known = set(present)
    stale = sorted(
        name
        for name in (EXPECTED_UNGRANTED.keys() | READ_ONLY_TABLES.keys())
        if name in known and held.get(name, set()) != set(required_privileges(name))
    )
    if stale:  # pragma: no cover - unreachable while the two checks above pass
        raise RuntimeError("privilege documentation is out of date for: " + ", ".join(stale))

    writable = sum(1 for table in present if required_privileges(table) == FULL_DML)
    sequences = conn.execute(
        "select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace"
        " where n.nspname = 'public' and c.relkind = 'S'"
    ).fetchone()[0]
    print(
        f"runtime grant coverage verified: {writable} tables writable by {RUNTIME_ROLE}, "
        f"{len(READ_ONLY_TABLES)} read-only, {len(EXPECTED_UNGRANTED)} withheld, "
        f"{sequences} sequences usable",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dsn-env",
        default="BRAIN_MIGRATION_DATABASE_URL",
        help="environment variable holding the database DSN to inspect",
    )
    args = parser.parse_args()

    with psycopg.connect(_dsn(args.dsn_env), autocommit=True) as conn:
        verify(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
