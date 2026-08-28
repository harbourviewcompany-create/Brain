"""Verify every runtime-visible table is reachable by the constrained runtime login.

Migrations 021, 022 and 025 hand out privileges through `do $$ ... $$` loops that
read `information_schema.columns` or iterate a literal array. Those loops are
evaluated once, when their migration runs, so they can only ever cover tables that
exist at that moment and match that migration's shape. A table created later, or a
pre-tenant table carrying no `tenant_id`, silently ends up with row level security
enabled and no grant at all -- invisible to the non-owner `brain_runtime_role`
login the release topology requires, while remaining fully readable to the owner
that CI and single-role installations happen to use.

That failure mode is not observable from the migration files alone, so this runs
against a real database after `tools/apply_migrations.py` and asserts the property
directly: every table in `public` is either granted to `brain_runtime_role` or
named in EXPECTED_UNGRANTED below, with a reason.
"""

from __future__ import annotations

import argparse
import os

import psycopg


# Tables the constrained runtime login is deliberately not granted.
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

RUNTIME_ROLE = "brain_runtime_role"


def _dsn(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def ungranted_tables(conn: psycopg.Connection) -> list[str]:
    rows = conn.execute(
        """
        select c.relname
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public'
          and c.relkind = 'r'
          and not has_table_privilege(%s, c.oid, 'select')
        order by c.relname
        """,
        (RUNTIME_ROLE,),
    ).fetchall()
    return [row[0] for row in rows]


def verify(conn: psycopg.Connection) -> None:
    if conn.execute("select to_regrole(%s)", (RUNTIME_ROLE,)).fetchone()[0] is None:
        raise RuntimeError(f"{RUNTIME_ROLE} is missing; apply migration 019 first")

    ungranted = set(ungranted_tables(conn))
    unexpected = sorted(ungranted - EXPECTED_UNGRANTED.keys())
    if unexpected:
        raise RuntimeError(
            "tables are unreachable by the constrained runtime login: "
            + ", ".join(unexpected)
            + ". Grant them in a migration, or add them to EXPECTED_UNGRANTED "
            "in tools/verify_runtime_grant_coverage.py with a reason."
        )

    # A stale exclusion is its own bug: it hides a table that has since been
    # granted, so the list stops describing the database it claims to describe.
    stale = sorted(EXPECTED_UNGRANTED.keys() - ungranted)
    present = {
        row[0]
        for row in conn.execute(
            "select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace"
            " where n.nspname = 'public' and c.relkind = 'r'"
        ).fetchall()
    }
    stale = [name for name in stale if name in present]
    if stale:
        raise RuntimeError(
            "EXPECTED_UNGRANTED lists tables that are in fact granted: "
            + ", ".join(stale)
            + ". Remove them from tools/verify_runtime_grant_coverage.py."
        )

    print(
        f"runtime grant coverage verified: {len(present) - len(ungranted)} tables reachable by "
        f"{RUNTIME_ROLE}, {len(ungranted)} deliberately withheld",
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
