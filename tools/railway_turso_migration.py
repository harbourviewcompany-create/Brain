"""Read-only PostgreSQL -> SQLite/libSQL migration tooling for the $0 Brain runtime.

The source PostgreSQL instance is never mutated. The production rescue workflow
runs this tool only against PostgreSQL recovered from a runner-local PGDATA copy.
Remote Turso import is a separate explicit subcommand and is allowed only after
local source/destination manifests verify.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence
from urllib.parse import urlparse
from uuid import UUID

from brain.adapters.turso_schema import TURSO_SCHEMA

MASK_256 = (1 << 256) - 1
SYSTEM_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast"}

# Required by the production Turso adapters. Source tables may contain additional
# columns; those are preserved. Missing required columns are a hard migration HOLD.
REQUIRED_RUNTIME_COLUMNS: dict[str, set[str]] = {
    "brain_events": {"id", "event_type", "aggregate_type", "aggregate_id", "causation_id", "correlation_id", "payload", "occurred_at"},
    "beliefs": {"id", "statement", "confidence", "state", "unknowns", "version", "updated_at"},
    "evidence": {"id", "observation_id", "claim", "reliability", "stance", "created_at", "metadata"},
    "belief_evidence": {"belief_id", "evidence_id", "relation"},
    "graph_nodes": {"id", "kind", "node_key", "properties"},
    "graph_edges": {"id", "source_id", "target_id", "relation", "weight", "confidence", "evidence_ids", "updated_at"},
    "rewire_events": {"id", "operation", "target_id", "reason", "previous", "current", "evidence_ids", "created_at"},
    "predictions": {"id", "statement", "expected_value", "confidence", "horizon_seconds", "belief_id", "action_id", "edge_ids", "source_keys", "status", "created_at", "resolve_by", "resolved_at", "metadata"},
    "attribution_records": {"id", "outcome_id", "prediction_id", "edge_ids", "source_keys", "reward_score", "prediction_error", "edge_deltas", "source_deltas", "rationale", "created_at"},
    "sources": {"id", "key", "authority_score", "historical_utility"},
    "money_lanes": {"lane_key", "title", "opportunity_class", "packaged_offer", "buyer_type", "seller_or_target_type", "first_48_hour_action", "price_low", "price_high", "repeatability", "fulfillment_difficulty", "time_to_cash_days", "automation_readiness", "legal_access_risk", "priority_score", "updated_at"},
    "revenue_source_scores": {"source_id", "score", "updated_at"},
    "revenue_execution_actions": {"id", "opportunity_id", "offer_id", "lane_id", "source_id", "action_type", "target_contact", "proposal", "evidence_refs", "approval_required", "state", "approved_by", "manual_proof_ref", "created_at", "updated_at"},
    "revenue_followups": {"id", "action_id", "due_at", "script", "state", "completed_at"},
    "revenue_outcome_ledger": {"id", "action_id", "lane_id", "source_id", "outcome_type", "revenue", "reply", "meeting_booked", "paid_conversion", "legal_risk", "operator_hours", "lesson", "created_at"},
}


def qident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sqlite_table_name(schema: str, table: str) -> str:
    return table if schema == "public" else f"{schema}__{table}"


def sqlite_affinity(data_type: str, udt_name: str) -> str:
    kind = data_type.lower()
    udt = udt_name.lower()
    if kind in {"smallint", "integer", "bigint", "boolean"} or udt in {"int2", "int4", "int8", "bool"}:
        return "INTEGER"
    if kind in {"real", "double precision", "numeric", "decimal"} or udt in {"float4", "float8", "numeric"}:
        return "REAL"
    if kind == "bytea" or udt == "bytea":
        return "BLOB"
    return "TEXT"


def normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return value
    if isinstance(value, (float, Decimal)):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address, ipaddress.IPv4Network, ipaddress.IPv6Network)):
        return str(value)
    if isinstance(value, dict):
        return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"))
    if isinstance(value, (list, tuple, set)):
        items = sorted(value, key=str) if isinstance(value, set) else list(value)
        return json.dumps(_jsonable(items), sort_keys=True, separators=(",", ":"))
    return str(value)


def _jsonable(value: Any) -> Any:
    normalized = normalize(value)
    if isinstance(normalized, bytes):
        return {"__bytes_sha256__": hashlib.sha256(normalized).hexdigest(), "length": len(normalized)}
    return normalized


def canonical_row(columns: Sequence[str], row: Sequence[Any]) -> bytes:
    payload = {column: _jsonable(value) for column, value in zip(columns, row, strict=True)}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass
class MultisetDigest:
    count: int = 0
    xor_value: int = 0
    sum_value: int = 0

    def add(self, payload: bytes) -> None:
        digest = hashlib.sha256(payload).digest()
        value = int.from_bytes(digest, "big")
        self.count += 1
        self.xor_value ^= value
        self.sum_value = (self.sum_value + value) & MASK_256

    def hexdigest(self) -> str:
        material = (
            self.count.to_bytes(16, "big")
            + self.xor_value.to_bytes(32, "big")
            + self.sum_value.to_bytes(32, "big")
        )
        return hashlib.sha256(material).hexdigest()

    def snapshot(self) -> dict[str, Any]:
        return {"row_count": self.count, "sha256_multiset": self.hexdigest()}


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    udt_name: str
    nullable: bool

    @property
    def affinity(self) -> str:
        return sqlite_affinity(self.data_type, self.udt_name)


@dataclass(frozen=True)
class Table:
    schema: str
    name: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]

    @property
    def sqlite_name(self) -> str:
        return sqlite_table_name(self.schema, self.name)


class EvidenceWriter:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def write_json(self, name: str, payload: Any) -> Path:
        path = self.directory / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        return path

    def finalize_hashes(self, sqlite_path: Path | None = None) -> Path:
        hashes: dict[str, dict[str, Any]] = {}
        for path in sorted(self.directory.iterdir()):
            if path.is_file() and path.name != "artifact_sha256.json":
                data = path.read_bytes()
                hashes[path.name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        if sqlite_path is not None and sqlite_path.is_file():
            data_hash = hashlib.sha256()
            size = 0
            with sqlite_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    data_hash.update(chunk)
                    size += len(chunk)
            hashes[sqlite_path.name] = {"sha256": data_hash.hexdigest(), "bytes": size}
        return self.write_json("artifact_sha256.json", hashes)


def pg_tables(connection: Any) -> list[Table]:
    tables: list[Table] = []
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
              AND table_schema NOT IN ('pg_catalog','information_schema')
              AND table_schema NOT LIKE 'pg_toast%'
            ORDER BY table_schema, table_name
            """
        )
        names = cur.fetchall()
    for schema, table in names:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name,data_type,udt_name,is_nullable
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s
                ORDER BY ordinal_position
                """,
                (schema, table),
            )
            columns = tuple(
                Column(str(name), str(data_type), str(udt_name), str(nullable) == "YES")
                for name, data_type, udt_name, nullable in cur.fetchall()
            )
            regclass = f'{qident(str(schema))}.{qident(str(table))}'
            cur.execute(
                """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey)
                WHERE i.indrelid=to_regclass(%s) AND i.indisprimary
                ORDER BY array_position(i.indkey,a.attnum)
                """,
                (regclass,),
            )
            primary = tuple(str(row[0]) for row in cur.fetchall())
        tables.append(Table(str(schema), str(table), columns, primary))
    return tables


def create_sqlite_table(connection: sqlite3.Connection, table: Table) -> None:
    pieces: list[str] = []
    for column in table.columns:
        definition = f"{qident(column.name)} {column.affinity}"
        if not column.nullable:
            definition += " NOT NULL"
        pieces.append(definition)
    if table.primary_key:
        pieces.append("PRIMARY KEY (" + ",".join(qident(name) for name in table.primary_key) + ")")
    ddl = f"CREATE TABLE {qident(table.sqlite_name)} (" + ",".join(pieces) + ")"
    connection.execute(ddl)


def source_rows(connection: Any, table: Table, batch_size: int = 1000) -> Iterator[list[tuple[Any, ...]]]:
    names = ",".join(qident(column.name) for column in table.columns)
    sql = f"SELECT {names} FROM {qident(table.schema)}.{qident(table.name)}"
    with connection.cursor(name=f"brain_migrate_{hashlib.sha1(table.sqlite_name.encode()).hexdigest()[:12]}") as cur:
        cur.itersize = batch_size
        cur.execute(sql)
        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break
            yield [tuple(row) for row in rows]


def digest_sqlite_table(connection: Any, table_name: str, columns: Sequence[str]) -> dict[str, Any]:
    digest = MultisetDigest()
    select = ",".join(qident(column) for column in columns)
    cursor = connection.execute(f"SELECT {select} FROM {qident(table_name)}")
    while True:
        rows = cursor.fetchmany(1000)
        if not rows:
            break
        for row in rows:
            digest.add(canonical_row(columns, tuple(row)))
    return digest.snapshot()


def sqlite_columns(connection: Any, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({qident(table_name)})").fetchall()
    return [str(row[1]) for row in rows]


def sqlite_tables(connection: Any) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(row[0]) for row in rows]


def ensure_runtime_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(TURSO_SCHEMA)
    connection.commit()
    existing = set(sqlite_tables(connection))
    for table, required in REQUIRED_RUNTIME_COLUMNS.items():
        if table not in existing:
            raise RuntimeError(f"required runtime table missing after bootstrap: {table}")
        actual = set(sqlite_columns(connection, table))
        missing = sorted(required - actual)
        if missing:
            raise RuntimeError(f"runtime table {table} missing required columns: {missing}")


def convert(postgres_dsn: str, sqlite_path: Path, evidence_dir: Path) -> dict[str, Any]:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("PostgreSQL conversion requires project psycopg dependencies") from exc

    if sqlite_path.exists():
        raise RuntimeError(f"refusing to overwrite destination SQLite database: {sqlite_path}")
    writer = EvidenceWriter(evidence_dir)
    source_manifest: dict[str, Any] = {}
    destination_manifest: dict[str, Any] = {}
    inventory: list[dict[str, Any]] = []

    with psycopg.connect(postgres_dsn) as source:
        source.execute("SET default_transaction_read_only = on")
        source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        tables = pg_tables(source)
        names = [table.sqlite_name for table in tables]
        if len(names) != len(set(names)):
            raise RuntimeError("schema/table encoding collision in SQLite destination names")

        destination = sqlite3.connect(sqlite_path)
        try:
            destination.execute("PRAGMA journal_mode=DELETE")
            destination.execute("PRAGMA synchronous=FULL")
            destination.execute(
                "CREATE TABLE migration_table_map(schema_name TEXT NOT NULL,table_name TEXT NOT NULL,sqlite_table_name TEXT PRIMARY KEY)"
            )
            for table in tables:
                create_sqlite_table(destination, table)
                destination.execute(
                    "INSERT INTO migration_table_map(schema_name,table_name,sqlite_table_name) VALUES (?,?,?)",
                    (table.schema, table.name, table.sqlite_name),
                )
                columns = [column.name for column in table.columns]
                inventory.append(
                    {
                        "schema": table.schema,
                        "table": table.name,
                        "sqlite_table": table.sqlite_name,
                        "primary_key": list(table.primary_key),
                        "columns": [
                            {
                                "name": column.name,
                                "postgres_type": column.data_type,
                                "postgres_udt": column.udt_name,
                                "sqlite_affinity": column.affinity,
                                "nullable": column.nullable,
                            }
                            for column in table.columns
                        ],
                    }
                )
                digest = MultisetDigest()
                insert_sql = (
                    f"INSERT INTO {qident(table.sqlite_name)} ("
                    + ",".join(qident(name) for name in columns)
                    + ") VALUES ("
                    + ",".join("?" for _ in columns)
                    + ")"
                )
                for batch in source_rows(source, table):
                    normalized_rows: list[tuple[Any, ...]] = []
                    for row in batch:
                        normalized = tuple(normalize(value) for value in row)
                        digest.add(canonical_row(columns, normalized))
                        normalized_rows.append(normalized)
                    destination.executemany(insert_sql, normalized_rows)
                destination.commit()
                source_manifest[table.sqlite_name] = digest.snapshot()
                destination_manifest[table.sqlite_name] = digest_sqlite_table(
                    destination, table.sqlite_name, columns
                )
                if source_manifest[table.sqlite_name] != destination_manifest[table.sqlite_name]:
                    raise RuntimeError(f"source/destination integrity mismatch for {table.sqlite_name}")

            ensure_runtime_schema(destination)
            destination.execute("VACUUM")
            destination.commit()
        finally:
            destination.close()

    verification = {
        "verified": source_manifest == destination_manifest,
        "source_table_count": len(source_manifest),
        "destination_table_count": len(destination_manifest),
        "source_row_count": sum(item["row_count"] for item in source_manifest.values()),
        "destination_row_count": sum(item["row_count"] for item in destination_manifest.values()),
        "mismatched_tables": sorted(
            name for name in source_manifest if source_manifest[name] != destination_manifest.get(name)
        ),
    }
    if not verification["verified"]:
        raise RuntimeError("SQLite migration verification failed")

    writer.write_json("table_inventory.json", inventory)
    writer.write_json("source_integrity.json", source_manifest)
    writer.write_json("destination_integrity.json", destination_manifest)
    writer.write_json(
        "source_counts.json",
        {name: item["row_count"] for name, item in source_manifest.items()},
    )
    writer.write_json(
        "destination_counts.json",
        {name: item["row_count"] for name, item in destination_manifest.items()},
    )
    writer.write_json("migration_verification.json", verification)
    writer.finalize_hashes(sqlite_path)
    return verification


def load_local_manifest(sqlite_path: Path) -> dict[str, dict[str, Any]]:
    connection = sqlite3.connect(sqlite_path)
    try:
        result: dict[str, dict[str, Any]] = {}
        for table in sqlite_tables(connection):
            columns = sqlite_columns(connection, table)
            result[table] = digest_sqlite_table(connection, table, columns)
        return result
    finally:
        connection.close()


def remote_table_names(connection: Any) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return {str(row[0]) for row in rows}


def remote_columns(connection: Any, table: str) -> list[str]:
    return [str(row[1]) for row in connection.execute(f"PRAGMA table_info({qident(table)})").fetchall()]


def remote_digest(connection: Any, table: str, columns: Sequence[str]) -> dict[str, Any]:
    return digest_sqlite_table(connection, table, columns)


def local_table_sql(connection: sqlite3.Connection, table: str) -> str:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"SQLite table DDL unavailable: {table}")
    return str(row[0])


def import_to_turso(sqlite_path: Path, evidence_dir: Path) -> dict[str, Any]:
    url = (os.environ.get("TURSO_DATABASE_URL") or "").strip()
    token = (os.environ.get("TURSO_AUTH_TOKEN") or "").strip()
    if not url or not token:
        raise RuntimeError("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are required")
    if not (url.startswith("libsql://") or url.startswith("https://")):
        raise RuntimeError("remote import requires an existing libSQL/Turso URL")
    try:
        import libsql
    except ImportError as exc:
        raise RuntimeError("remote Turso import requires the libsql dependency") from exc

    local = sqlite3.connect(sqlite_path)
    remote = libsql.connect(database=url, auth_token=token)
    writer = EvidenceWriter(evidence_dir)
    try:
        local_tables = sqlite_tables(local)
        local_manifest = {
            table: digest_sqlite_table(local, table, sqlite_columns(local, table))
            for table in local_tables
        }
        remote_existing = remote_table_names(remote)

        # Complete preflight before inserting any row. Existing non-empty tables
        # must already be exact normalized equivalents; otherwise stop rather
        # than merging two unknown histories.
        preflight: dict[str, str] = {}
        for table in local_tables:
            if table not in remote_existing:
                preflight[table] = "create_and_import"
                continue
            local_cols = sqlite_columns(local, table)
            remote_cols = remote_columns(remote, table)
            count = int(remote.execute(f"SELECT count(*) FROM {qident(table)}").fetchone()[0])
            if count == 0:
                preflight[table] = "empty_import"
                continue
            if set(local_cols) != set(remote_cols):
                raise RuntimeError(
                    f"remote table {table} is non-empty with incompatible columns; refusing mutation"
                )
            if remote_digest(remote, table, local_cols) != local_manifest[table]:
                raise RuntimeError(
                    f"remote table {table} contains non-equivalent data; refusing mutation"
                )
            preflight[table] = "already_equivalent"

        imported: dict[str, str] = {}
        for table in local_tables:
            action = preflight[table]
            if action == "already_equivalent":
                imported[table] = action
                continue
            if table not in remote_table_names(remote):
                remote.execute(local_table_sql(local, table))
                remote.commit()
            else:
                existing_columns = set(remote_columns(remote, table))
                local_info = local.execute(f"PRAGMA table_info({qident(table)})").fetchall()
                for row in local_info:
                    name, affinity = str(row[1]), str(row[2] or "TEXT")
                    if name not in existing_columns:
                        remote.execute(
                            f"ALTER TABLE {qident(table)} ADD COLUMN {qident(name)} {affinity}"
                        )
                        existing_columns.add(name)
                remote.commit()

            columns = sqlite_columns(local, table)
            placeholders = ",".join("?" for _ in columns)
            insert = (
                f"INSERT INTO {qident(table)} ("
                + ",".join(qident(column) for column in columns)
                + f") VALUES ({placeholders})"
            )
            cursor = local.execute(
                f"SELECT {','.join(qident(column) for column in columns)} FROM {qident(table)}"
            )
            remote.execute("BEGIN")
            try:
                while True:
                    rows = cursor.fetchmany(500)
                    if not rows:
                        break
                    remote.executemany(insert, rows)
                remote.commit()
            except Exception:
                remote.rollback()
                raise
            imported[table] = "imported"

        remote_manifest = {
            table: remote_digest(remote, table, sqlite_columns(local, table))
            for table in local_tables
        }
        mismatches = sorted(
            table for table in local_tables if local_manifest[table] != remote_manifest.get(table)
        )
        verification = {
            "verified": not mismatches,
            "table_count": len(local_tables),
            "row_count": sum(item["row_count"] for item in local_manifest.values()),
            "mismatched_tables": mismatches,
            "table_actions": imported,
            "destination": {
                "scheme": urlparse(url).scheme,
                "host": urlparse(url).hostname,
            },
        }
        writer.write_json("turso_destination_integrity.json", remote_manifest)
        writer.write_json(
            "turso_destination_counts.json",
            {table: item["row_count"] for table, item in remote_manifest.items()},
        )
        writer.write_json("turso_import_verification.json", verification)
        writer.finalize_hashes(sqlite_path)
        if mismatches:
            raise RuntimeError(f"Turso import verification failed: {mismatches}")
        return verification
    finally:
        try:
            remote.close()
        finally:
            local.close()


def verify_existing_sqlite(sqlite_path: Path, evidence_dir: Path) -> dict[str, Any]:
    connection = sqlite3.connect(sqlite_path)
    writer = EvidenceWriter(evidence_dir)
    try:
        ensure_runtime_schema(connection)
        manifest = {
            table: digest_sqlite_table(connection, table, sqlite_columns(connection, table))
            for table in sqlite_tables(connection)
        }
        verification = {
            "verified": True,
            "table_count": len(manifest),
            "row_count": sum(item["row_count"] for item in manifest.values()),
        }
        writer.write_json("sqlite_full_integrity.json", manifest)
        writer.write_json("sqlite_full_verification.json", verification)
        writer.finalize_hashes(sqlite_path)
        return verification
    finally:
        connection.close()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    convert_parser = sub.add_parser("convert")
    convert_parser.add_argument("--postgres-dsn", required=True)
    convert_parser.add_argument("--sqlite", required=True, type=Path)
    convert_parser.add_argument("--evidence-dir", required=True, type=Path)

    verify_parser = sub.add_parser("verify-sqlite")
    verify_parser.add_argument("--sqlite", required=True, type=Path)
    verify_parser.add_argument("--evidence-dir", required=True, type=Path)

    import_parser = sub.add_parser("import-turso")
    import_parser.add_argument("--sqlite", required=True, type=Path)
    import_parser.add_argument("--evidence-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "convert":
        result = convert(args.postgres_dsn, args.sqlite, args.evidence_dir)
    elif args.command == "verify-sqlite":
        result = verify_existing_sqlite(args.sqlite, args.evidence_dir)
    elif args.command == "import-turso":
        result = import_to_turso(args.sqlite, args.evidence_dir)
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
