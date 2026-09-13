from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from brain.adapters.turso_schema import TURSO_SCHEMA
from tools.railway_turso_migration import (
    MultisetDigest,
    canonical_row,
    ensure_runtime_schema,
    import_to_turso,
    normalize,
    verify_existing_sqlite,
)


def make_runtime_sqlite(path: Path, *, event_id: str = "00000000-0000-0000-0000-000000000001") -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(TURSO_SCHEMA)
        connection.execute(
            """
            INSERT INTO brain_events(
                id,event_type,aggregate_type,aggregate_id,causation_id,
                correlation_id,payload,occurred_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                event_id,
                "belief.updated",
                "belief",
                "00000000-0000-0000-0000-000000000100",
                None,
                "00000000-0000-0000-0000-000000000200",
                '{"stable":true}',
                "2026-08-28T12:00:00+00:00",
            ),
        )
        connection.execute(
            "INSERT INTO brain_event_ids(id,occurred_at) VALUES (?,?)",
            (event_id, "2026-08-28T12:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO brain_event_type_counts(event_type,event_count) VALUES ('belief.updated',1)"
        )
        connection.commit()
    finally:
        connection.close()


def fake_libsql(monkeypatch, remote_path: Path) -> None:
    module = SimpleNamespace(
        connect=lambda *, database, auth_token: sqlite3.connect(remote_path)
    )
    monkeypatch.setitem(sys.modules, "libsql", module)
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://existing-free-db.example.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token-not-secret")


def test_normalize_produces_sqlite_stable_values():
    assert normalize(True) == 1
    assert normalize(False) == 0
    assert normalize(UUID(int=1)) == "00000000-0000-0000-0000-000000000001"
    assert normalize({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert normalize([2, 1]) == "[2,1]"


def test_multiset_sha256_is_order_independent_but_count_sensitive():
    rows = [
        canonical_row(["id", "value"], ("a", 1)),
        canonical_row(["id", "value"], ("b", 2)),
        canonical_row(["id", "value"], ("c", 3)),
    ]
    first = MultisetDigest()
    second = MultisetDigest()
    for row in rows:
        first.add(row)
    for row in reversed(rows):
        second.add(row)
    assert first.snapshot() == second.snapshot()

    second.add(rows[0])
    assert first.snapshot() != second.snapshot()


def test_verify_existing_sqlite_generates_integrity_artifacts(tmp_path):
    database = tmp_path / "brain.sqlite"
    evidence = tmp_path / "evidence"
    make_runtime_sqlite(database)

    result = verify_existing_sqlite(database, evidence)

    assert result["verified"] is True
    assert result["table_count"] > 0
    assert (evidence / "sqlite_full_integrity.json").is_file()
    assert (evidence / "sqlite_full_verification.json").is_file()
    hashes = json.loads((evidence / "artifact_sha256.json").read_text())
    assert hashes[database.name]["sha256"]
    assert hashes[database.name]["bytes"] == database.stat().st_size


def test_existing_incompatible_runtime_table_fails_closed(tmp_path):
    database = sqlite3.connect(tmp_path / "bad.sqlite")
    try:
        database.execute("CREATE TABLE brain_events(id TEXT PRIMARY KEY)")
        with pytest.raises(RuntimeError, match="missing required columns"):
            ensure_runtime_schema(database)
    finally:
        database.close()


def test_import_to_existing_free_turso_equivalent_runtime_and_extra_tables(tmp_path, monkeypatch):
    local_path = tmp_path / "local.sqlite"
    remote_path = tmp_path / "remote.sqlite"
    evidence = tmp_path / "evidence"
    make_runtime_sqlite(local_path)
    local = sqlite3.connect(local_path)
    try:
        local.execute("CREATE TABLE source_archive__audit(id TEXT PRIMARY KEY,payload TEXT NOT NULL)")
        local.execute("INSERT INTO source_archive__audit VALUES ('audit-1','complete-source-row')")
        local.commit()
    finally:
        local.close()
    fake_libsql(monkeypatch, remote_path)

    result = import_to_turso(local_path, evidence)

    assert result["verified"] is True
    remote = sqlite3.connect(remote_path)
    try:
        assert remote.execute("SELECT count(*) FROM brain_events").fetchone()[0] == 1
        assert remote.execute("SELECT payload FROM source_archive__audit").fetchone()[0] == "complete-source-row"
    finally:
        remote.close()
    assert (evidence / "turso_destination_integrity.json").is_file()
    assert (evidence / "turso_import_verification.json").is_file()


def test_import_is_idempotent_when_remote_is_already_equivalent(tmp_path, monkeypatch):
    local_path = tmp_path / "local.sqlite"
    remote_path = tmp_path / "remote.sqlite"
    make_runtime_sqlite(local_path)
    make_runtime_sqlite(remote_path)
    fake_libsql(monkeypatch, remote_path)

    result = import_to_turso(local_path, tmp_path / "evidence")

    assert result["verified"] is True
    assert result["table_actions"]["brain_events"] == "already_equivalent"
    remote = sqlite3.connect(remote_path)
    try:
        assert remote.execute("SELECT count(*) FROM brain_events").fetchone()[0] == 1
    finally:
        remote.close()


def test_nonempty_non_equivalent_remote_fails_before_importing_local_rows(tmp_path, monkeypatch):
    local_path = tmp_path / "local.sqlite"
    remote_path = tmp_path / "remote.sqlite"
    make_runtime_sqlite(local_path, event_id="00000000-0000-0000-0000-000000000001")
    make_runtime_sqlite(remote_path, event_id="00000000-0000-0000-0000-000000000999")
    fake_libsql(monkeypatch, remote_path)

    with pytest.raises(RuntimeError, match="non-equivalent data"):
        import_to_turso(local_path, tmp_path / "evidence")

    remote = sqlite3.connect(remote_path)
    try:
        ids = [row[0] for row in remote.execute("SELECT id FROM brain_events").fetchall()]
        assert ids == ["00000000-0000-0000-0000-000000000999"]
    finally:
        remote.close()
