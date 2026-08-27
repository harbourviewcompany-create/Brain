"""Acceptance contracts for restart-safe external observation acquisition."""

from __future__ import annotations

from pathlib import Path

from brain.connectors.protocol import ConnectorKind, ConnectorSource
from brain.connectors.service import IngestService
from brain.connectors.store import InMemoryConnectorRegistry, PostgresConnectorRegistry


MIGRATION = Path("db/migrations/025_durable_connector_runtime.sql")


def test_migration_025_defines_restart_safe_acquisition_state() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    for table in (
        "source_connector_runtime_state",
        "source_connector_ingestion_runs",
        "source_connector_observations",
    ):
        assert f"create table if not exists public.{table}" in sql
        assert "alter table public.%i force row level security" in sql or "force row level security" in sql

    assert "lease_owner" in sql
    assert "lease_expires_at" in sql
    assert "unique (source_id, content_hash)" in sql
    assert "observed_at timestamptz not null" in sql
    assert "retrieved_at timestamptz not null" in sql
    assert "seen_count integer not null default 1" in sql
    assert "current_brain_service_context()" in sql
    assert "current_brain_tenant_id()" in sql


def test_durable_connector_runtime_does_not_reuse_migration_024() -> None:
    assert MIGRATION.exists()
    assert not Path("db/migrations/024_durable_connector_runtime.sql").exists()


def test_durable_public_config_never_persists_credentials() -> None:
    source = ConnectorSource(
        source_key="credentialed-api",
        url="https://example.com/api",
        kind=ConnectorKind.HTTP_JSON,
        headers={"Authorization": "Bearer secret", "X-Api-Key": "secret"},
        metadata={"token": "secret", "safe_note": "not persisted either"},
        json_items_path="items",
    )

    config = PostgresConnectorRegistry._public_config(source)

    assert config["json_items_path"] == "items"
    rendered = repr(config).lower()
    assert "authorization" not in rendered
    assert "api-key" not in rendered
    assert "bearer secret" not in rendered
    assert "token" not in rendered
    assert "safe_note" not in rendered


def test_ingest_service_uses_durable_registry_when_schema_is_available(monkeypatch) -> None:
    class FakeDurableRegistry:
        def __init__(self, pool) -> None:
            self.pool = pool

        def available(self) -> bool:
            return True

    class EventStore:
        pool = object()

    monkeypatch.setattr(
        "brain.connectors.service.PostgresConnectorRegistry", FakeDurableRegistry
    )

    service = IngestService(event_store=EventStore())

    assert isinstance(service.registry, FakeDurableRegistry)
    assert service.registry.pool is EventStore.pool


def test_ingest_service_falls_back_before_migration_025(monkeypatch) -> None:
    class FakeUnavailableRegistry:
        def __init__(self, pool) -> None:
            self.pool = pool

        def available(self) -> bool:
            return False

    class EventStore:
        pool = object()

    monkeypatch.setattr(
        "brain.connectors.service.PostgresConnectorRegistry", FakeUnavailableRegistry
    )

    service = IngestService(event_store=EventStore())

    assert isinstance(service.registry, InMemoryConnectorRegistry)
