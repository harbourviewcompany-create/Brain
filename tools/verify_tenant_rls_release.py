"""Verify the Brain tenant/RLS release contract against a real PostgreSQL database.

This is intentionally read/write only against the caller-supplied test database.
It never creates credentials and is designed for ephemeral CI after migrations
019-022 have been applied by tools/apply_migrations.py.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from uuid import UUID

import psycopg

from brain.tenant_runtime import (
    require_safe_runtime_role,
    tenant_rls_enforced,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "db" / "migrations"

TENANT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1")
TENANT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2")
LEGACY_EVENT = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa0")
EVENT_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3")
EVENT_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb4")
AGGREGATE_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5")
AGGREGATE_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb6")
ACTOR_A = "tenant-a-operator"
ACTOR_B = "tenant-b-operator"


def _dsn(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _migration_hashes() -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(MIGRATIONS.glob("*.sql"))
    }


def _migration_version(filename: str) -> int | None:
    prefix = filename.split("_", 1)[0]
    return int(prefix) if prefix.isdigit() else None


def verify_migration_ledger(
    migration_dsn: str,
    *,
    max_version: int | None = None,
) -> None:
    expected_all = _migration_hashes()
    expected = {
        name: digest
        for name, digest in expected_all.items()
        if max_version is None
        or (
            (version := _migration_version(name)) is not None
            and version <= max_version
        )
    }
    with psycopg.connect(migration_dsn, autocommit=True) as conn:
        rows = conn.execute(
            "select filename, sha256 from public.brain_schema_migrations"
        ).fetchall()
    actual = {str(filename): str(digest) for filename, digest in rows}
    missing = sorted(set(expected) - set(actual))
    drift = sorted(
        name for name, digest in expected.items() if actual.get(name) not in {None, digest}
    )
    if missing:
        raise RuntimeError("migration ledger missing: " + ", ".join(missing))
    if drift:
        raise RuntimeError("migration hash drift: " + ", ".join(drift))
    for required in (
        "019_tenant_auth_foundation.sql",
        "020_tenant_scope_cognitive_tables.sql",
        "021_tenant_scope_extended_cognition.sql",
        "022_tenant_runtime_enforcement.sql",
    ):
        if required not in actual:
            raise RuntimeError(f"required tenant migration missing: {required}")
    ceiling = "all" if max_version is None else str(max_version)
    print(
        "migration ledger/hash verification passed "
        f"({len(expected)} files, max_version={ceiling})"
    )


def seed_tenant_fixtures(migration_dsn: str) -> None:
    """Seed only deterministic CI tenant fixtures through the migration authority."""
    with psycopg.connect(migration_dsn, autocommit=True) as conn:
        conn.execute(
            """
            insert into public.tenants (id, name, slug, status)
            values
              (%s, 'Tenant A', 'tenant-a-ci', 'active'),
              (%s, 'Tenant B', 'tenant-b-ci', 'active')
            on conflict (id) do update set
              name = excluded.name,
              status = excluded.status
            """,
            (TENANT_A, TENANT_B),
        )
        conn.execute(
            """
            insert into public.tenant_memberships (
              tenant_id, user_id, role, status
            ) values
              (%s, %s, 'operator', 'active'),
              (%s, %s, 'operator', 'active')
            on conflict (tenant_id, user_id) do update set
              role = excluded.role,
              status = excluded.status,
              removed_at = null
            """,
            (TENANT_A, ACTOR_A, TENANT_B, ACTOR_B),
        )


def _set_tenant(conn: psycopg.Connection, tenant_id: UUID, actor_id: str) -> None:
    conn.execute("select set_config('brain.tenant_id', %s, true)", (str(tenant_id),))
    conn.execute("select set_config('brain.actor_id', %s, true)", (actor_id,))


def verify_runtime_role_and_isolation(runtime_dsn: str) -> None:
    with psycopg.connect(runtime_dsn, autocommit=False) as conn:
        if not tenant_rls_enforced(conn):
            raise RuntimeError("critical tenant tables are not FORCE RLS")
        require_safe_runtime_role(conn, require_trusted_service=False)

        with conn.transaction():
            _set_tenant(conn, TENANT_A, ACTOR_A)
            membership = conn.execute(
                """
                select role from public.tenant_memberships
                where tenant_id = %s and user_id = %s
                """,
                (TENANT_A, ACTOR_A),
            ).fetchone()
            if not membership or membership[0] != "operator":
                raise RuntimeError("tenant A self-membership is not visible")

            inserted = conn.execute(
                """
                insert into public.brain_events (
                  id, event_type, aggregate_type, aggregate_id, payload
                ) values (%s, 'tenant.rls.test', 'tenant_rls_test', %s, %s::jsonb)
                on conflict (id) do update set payload = excluded.payload
                returning tenant_id
                """,
                (EVENT_A, AGGREGATE_A, '{"tenant":"A"}'),
            ).fetchone()
            if not inserted or inserted[0] != TENANT_A:
                raise RuntimeError("tenant A insert was not stamped with tenant_id")

            visible_a = conn.execute(
                "select count(*) from public.brain_events where id = %s",
                (EVENT_A,),
            ).fetchone()[0]
            visible_legacy = conn.execute(
                "select count(*) from public.brain_events where id = %s",
                (LEGACY_EVENT,),
            ).fetchone()[0]
            if visible_a != 1 or visible_legacy != 0:
                raise RuntimeError("tenant A visibility or legacy-null isolation failed")

        with conn.transaction():
            _set_tenant(conn, TENANT_B, ACTOR_B)
            membership = conn.execute(
                """
                select role from public.tenant_memberships
                where tenant_id = %s and user_id = %s
                """,
                (TENANT_B, ACTOR_B),
            ).fetchone()
            if not membership or membership[0] != "operator":
                raise RuntimeError("tenant B self-membership is not visible")

            inserted = conn.execute(
                """
                insert into public.brain_events (
                  id, event_type, aggregate_type, aggregate_id, payload
                ) values (%s, 'tenant.rls.test', 'tenant_rls_test', %s, %s::jsonb)
                on conflict (id) do update set payload = excluded.payload
                returning tenant_id
                """,
                (EVENT_B, AGGREGATE_B, '{"tenant":"B"}'),
            ).fetchone()
            if not inserted or inserted[0] != TENANT_B:
                raise RuntimeError("tenant B insert was not stamped with tenant_id")

            cross_read = conn.execute(
                "select count(*) from public.brain_events where id = %s",
                (EVENT_A,),
            ).fetchone()[0]
            cross_update = conn.execute(
                "update public.brain_events set payload = %s::jsonb where id = %s",
                ('{"cross_tenant":true}', EVENT_A),
            ).rowcount
            if cross_read != 0 or cross_update != 0:
                raise RuntimeError("tenant B crossed tenant A RLS boundary")

        with conn.transaction():
            conn.execute("select set_config('brain.tenant_id', '', true)")
            conn.execute("select set_config('brain.actor_id', '', true)")
            conn.execute("select set_config('brain.service_context', 'true', true)")
            forged_service_visibility = conn.execute(
                "select count(*) from public.brain_events where id in (%s, %s)",
                (EVENT_A, EVENT_B),
            ).fetchone()[0]
            if forged_service_visibility != 0:
                raise RuntimeError("session GUC forged trusted-service RLS bypass")

    print("non-owner runtime role and two-tenant isolation verification passed")


def verify_trusted_worker(worker_dsn: str) -> None:
    with psycopg.connect(worker_dsn, autocommit=True) as conn:
        if not tenant_rls_enforced(conn):
            raise RuntimeError("critical tenant tables are not FORCE RLS")
        require_safe_runtime_role(conn, require_trusted_service=True)
        rows = conn.execute(
            """
            select id, tenant_id
            from public.brain_events
            where id in (%s, %s, %s)
            order by id
            """,
            (LEGACY_EVENT, EVENT_A, EVENT_B),
        ).fetchall()
        ids = {row[0] for row in rows}
        if ids != {LEGACY_EVENT, EVENT_A, EVENT_B}:
            raise RuntimeError(
                "trusted worker cannot see expected legacy and cross-tenant events"
            )
        legacy_tenant = next(row[1] for row in rows if row[0] == LEGACY_EVENT)
        if legacy_tenant is not None:
            raise RuntimeError("legacy pre-tenant row was silently reassigned")
    print("trusted-service worker and legacy-null visibility verification passed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-version",
        type=int,
        default=None,
        help="verify migration ledger/hash only through this canonical version",
    )
    args = parser.parse_args()
    if args.max_version is not None and args.max_version < 22:
        parser.error("--max-version must include tenant migrations 019-022")

    migration_dsn = _dsn("BRAIN_MIGRATION_DATABASE_URL")
    runtime_dsn = _dsn("DATABASE_URL")
    worker_dsn = _dsn("BRAIN_WORKER_DATABASE_URL")

    verify_migration_ledger(migration_dsn, max_version=args.max_version)
    seed_tenant_fixtures(migration_dsn)
    verify_runtime_role_and_isolation(runtime_dsn)
    verify_trusted_worker(worker_dsn)
    print("Brain tenant/RLS release verification: GO for isolated test database")


if __name__ == "__main__":
    main()
