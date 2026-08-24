"""Apply and verify canonical Brain database migrations for Railway production."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import psycopg


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"
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


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", sql)


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


def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is required")

    files = sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda path: path.name)
    if not files:
        raise RuntimeError(f"no migrations found in {MIGRATIONS_DIR}")

    with psycopg.connect(dsn, autocommit=False) as conn:
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

                print(f"apply {path.name}", flush=True)
                with conn.transaction():
                    conn.execute(sql)
                    conn.execute(
                        "insert into public.brain_schema_migrations(filename, sha256) values (%s, %s)",
                        (path.name, digest),
                    )
                print(f"applied {path.name}", flush=True)

            _verify_required_schema(conn)
        finally:
            conn.execute("select pg_advisory_unlock(hashtext('brain_schema_migrations'))")
            conn.commit()


if __name__ == "__main__":
    main()
