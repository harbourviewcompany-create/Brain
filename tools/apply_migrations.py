"""Apply and verify canonical Brain database migrations for Railway production."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import psycopg
from psycopg import sql as pgsql

from brain.tenant_runtime import inspect_database_role, require_safe_runtime_role


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"
TENANT_RLS_FIRST_VERSION = 19
DESTRUCTIVE = re.compile(
    r"\b(drop\s+table|drop\s+schema|truncate(?:\s+table)?|delete\s+from|"
    r"alter\s+table[\s\S]{0,200}?drop\s+column)\b",
    re.IGNORECASE,
)
REQUIRED_TABLES = (
    "brain_events",
    "beliefs",
    "evidence",
    "predictions",
    "attribution_records",
    "working_memory_snapshots",
    "self_state_snapshots",
    "global_workspace_items",
    "curiosity_tasks",
    "organism_audit_events",
    "cognitive_organism_checkpoints",
)


@dataclass(frozen=True)
class TenantRlsReleaseState:
    runtime_role: str
    worker_role: str


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", sql)


def _migration_version(path: Path) -> int:
    try:
        return int(path.name.split("_", 1)[0])
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid migration filename: {path.name}") from exc


#: The exact colliding filenames that already shipped. Apply order between them
#: is fixed by filename sort and both are long applied in production, so renaming
#: either would orphan its `brain_schema_migrations` row.
#:
#: Keyed by the exact filename set rather than the version number: exempting
#: version 6 wholesale would also accept a *third* `006_*.sql` added later, which
#: `--max-version` still could not isolate -- silently recreating the collision
#: this validator exists to prevent. Mirrors ALLOWED_MIGRATION_COLLISIONS in
#: scripts/validate_build_ready_traceability.py.
GRANDFATHERED_DUPLICATE_FILENAMES = {
    6: frozenset({"006_money_spine.sql", "006_working_memory_predictions_learning.sql"}),
}


def _assert_unique_versions(files: Sequence[Path]) -> None:
    """Refuse a new migration that reuses an existing version number.

    ``--max-version`` and the CI baseline gate both select migrations by this
    number, so two files sharing one version cannot be separated by either.
    """

    seen: dict[int, list[str]] = {}
    for path in files:
        seen.setdefault(_migration_version(path), []).append(path.name)

    collisions = {
        version: names
        for version, names in seen.items()
        if len(names) > 1 and set(names) != GRANDFATHERED_DUPLICATE_FILENAMES.get(version)
    }
    if collisions:
        detail = "; ".join(
            f"{version:03d}: {', '.join(sorted(names))}" for version, names in sorted(collisions.items())
        )
        raise RuntimeError(f"duplicate migration version numbers are not allowed -- {detail}")


def _ensure_compatibility_roles(conn: psycopg.Connection) -> None:
    # These NOLOGIN roles are part of the repository migration contract and
    # are created by CI before migrations are applied.
    conn.execute(
        """
        do $$ begin
          create role anon nologin;
        exception when duplicate_object then null;
        end $$;
        do $$ begin
          create role authenticated nologin;
        exception when duplicate_object then null;
        end $$;
        """
    )


def _verify_required_schema(conn: psycopg.Connection) -> None:
    missing = []
    for table in REQUIRED_TABLES:
        row = conn.execute("select to_regclass(%s)", (f"public.{table}",)).fetchone()
        if not row or row[0] is None:
            missing.append(table)
    if missing:
        raise RuntimeError("required schema missing after migrations: " + ", ".join(missing))
    print("required schema verification passed: " + ", ".join(REQUIRED_TABLES), flush=True)


def _preflight_constrained_login(dsn: str, label: str) -> str:
    with psycopg.connect(dsn, autocommit=True) as conn:
        state = inspect_database_role(conn)
    violations: list[str] = []
    if state.is_database_owner:
        violations.append("database_owner")
    if state.is_superuser:
        violations.append("superuser")
    if state.bypass_rls:
        violations.append("bypassrls")
    if violations:
        raise RuntimeError(
            f"{label} database role is unsafe for tenant RLS: "
            + ", ".join(violations)
        )
    return state.role_name


def _prepare_tenant_rls_release(
    migration_conn: psycopg.Connection,
) -> TenantRlsReleaseState:
    if os.environ.get("BRAIN_TENANT_RLS_RELEASE") != "1":
        raise RuntimeError(
            "tenant RLS migrations require BRAIN_TENANT_RLS_RELEASE=1"
        )
    if os.environ.get("BRAIN_TENANT_MODE", "").strip().lower() != "required":
        raise RuntimeError(
            "tenant RLS migrations require BRAIN_TENANT_MODE=required"
        )
    if not os.environ.get("BRAIN_TENANT_CONTEXT_SECRET"):
        raise RuntimeError(
            "tenant RLS migrations require BRAIN_TENANT_CONTEXT_SECRET"
        )
    if not os.environ.get("BRAIN_MIGRATION_DATABASE_URL"):
        raise RuntimeError(
            "tenant RLS migrations require a separate BRAIN_MIGRATION_DATABASE_URL"
        )

    runtime_dsn = os.environ.get("DATABASE_URL")
    worker_dsn = os.environ.get("BRAIN_WORKER_DATABASE_URL")
    if not runtime_dsn:
        raise RuntimeError("tenant RLS migrations require DATABASE_URL for the API runtime")
    if not worker_dsn:
        raise RuntimeError(
            "tenant RLS migrations require BRAIN_WORKER_DATABASE_URL for the trusted worker"
        )

    runtime_role = _preflight_constrained_login(runtime_dsn, "API runtime")
    worker_role = _preflight_constrained_login(worker_dsn, "worker")
    migration_state = inspect_database_role(migration_conn)

    if runtime_role == worker_role:
        raise RuntimeError("API runtime and trusted worker must use distinct database roles")
    if migration_state.role_name in {runtime_role, worker_role}:
        raise RuntimeError(
            "migration database role must be distinct from API runtime and worker roles"
        )

    print(
        "tenant RLS release preflight passed: separate migrator, constrained API runtime, "
        "and constrained worker roles",
        flush=True,
    )
    return TenantRlsReleaseState(runtime_role=runtime_role, worker_role=worker_role)


def _grant_tenant_runtime_memberships(
    conn: psycopg.Connection,
    release: TenantRlsReleaseState,
) -> None:
    if conn.execute("select to_regrole('brain_runtime_role')").fetchone()[0] is None:
        raise RuntimeError("brain_runtime_role is missing after migration 019")
    if conn.execute("select to_regrole('brain_trusted_service_role')").fetchone()[0] is None:
        raise RuntimeError("brain_trusted_service_role is missing after migration 019")

    conn.execute(
        pgsql.SQL("grant brain_runtime_role to {}").format(
            pgsql.Identifier(release.runtime_role)
        )
    )
    conn.execute(
        pgsql.SQL("revoke brain_trusted_service_role from {}").format(
            pgsql.Identifier(release.runtime_role)
        )
    )
    conn.execute(
        pgsql.SQL("grant brain_trusted_service_role to {}").format(
            pgsql.Identifier(release.worker_role)
        )
    )

    # Commit before verifying. The verification below opens brand-new
    # connections (as the actual runtime/worker roles, to prove those exact
    # credentials pass the safety check - not just that the grant statement
    # ran). A separate connection can never see this connection's
    # uncommitted work, so without this commit the verification below fails
    # deterministically every time, regardless of environment, because the
    # grants above were never actually visible outside this transaction.
    # This call site is no longer nested inside a caller-owned
    # `with conn.transaction():` block (see the two call sites in main()),
    # so this is a real commit, not a no-op savepoint release.
    conn.commit()

    runtime_dsn = os.environ["DATABASE_URL"]
    worker_dsn = os.environ["BRAIN_WORKER_DATABASE_URL"]
    with psycopg.connect(runtime_dsn, autocommit=True) as runtime_conn:
        require_safe_runtime_role(runtime_conn, require_trusted_service=False)
    with psycopg.connect(worker_dsn, autocommit=True) as worker_conn:
        require_safe_runtime_role(worker_conn, require_trusted_service=True)
    print("tenant RLS runtime role memberships verified", flush=True)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-version",
        type=int,
        default=None,
        help="Apply/verify migrations only through this numeric version.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    migration_dsn = os.environ.get("BRAIN_MIGRATION_DATABASE_URL") or os.environ.get(
        "DATABASE_URL"
    )
    if not migration_dsn:
        raise RuntimeError("DATABASE_URL or BRAIN_MIGRATION_DATABASE_URL is required")

    files = sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda path: path.name)
    _assert_unique_versions(files)
    if args.max_version is not None:
        files = [path for path in files if _migration_version(path) <= args.max_version]
    if not files:
        raise RuntimeError(f"no migrations found in {MIGRATIONS_DIR}")

    release_state: TenantRlsReleaseState | None = None
    memberships_granted = False

    with psycopg.connect(migration_dsn, autocommit=False) as conn:
        conn.execute("select pg_advisory_lock(hashtext('brain_schema_migrations'))")
        try:
            with conn.transaction():
                _ensure_compatibility_roles(conn)
                conn.execute(
                    """
                    create table if not exists public.brain_schema_migrations (
                      filename text primary key,
                      sha256 text not null,
                      applied_at timestamptz not null default now()
                    )
                    """
                )

            for path in files:
                sql = path.read_text(encoding="utf-8")
                digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
                dangerous = DESTRUCTIVE.search(_strip_comments(sql))
                if dangerous:
                    raise RuntimeError(
                        f"refusing destructive migration {path.name}: {dangerous.group(1)}"
                    )

                row = conn.execute(
                    "select sha256 from public.brain_schema_migrations where filename = %s",
                    (path.name,),
                ).fetchone()
                if row:
                    if row[0] != digest:
                        raise RuntimeError(
                            f"migration drift detected for {path.name}: recorded hash differs"
                        )
                    print(f"skip {path.name} (already applied)", flush=True)
                    continue

                version = _migration_version(path)
                if version >= TENANT_RLS_FIRST_VERSION and release_state is None:
                    release_state = _prepare_tenant_rls_release(conn)

                if version > TENANT_RLS_FIRST_VERSION and not memberships_granted:
                    if release_state is None:
                        raise RuntimeError("tenant RLS release state is unavailable")
                    _grant_tenant_runtime_memberships(conn, release_state)
                    memberships_granted = True

                print(f"apply {path.name}", flush=True)
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "insert into public.brain_schema_migrations(filename, sha256) values (%s, %s)",
                        (path.name, digest),
                    )
                print(f"applied {path.name}", flush=True)

                if version == TENANT_RLS_FIRST_VERSION:
                    if release_state is None:
                        raise RuntimeError("tenant RLS release state is unavailable")
                    _grant_tenant_runtime_memberships(conn, release_state)
                    memberships_granted = True

            _verify_required_schema(conn)
        finally:
            conn.execute("select pg_advisory_unlock(hashtext('brain_schema_migrations'))")
            conn.commit()


if __name__ == "__main__":
    main()
