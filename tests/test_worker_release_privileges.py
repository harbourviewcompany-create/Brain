from __future__ import annotations

from pathlib import Path


MIGRATION = Path("db/migrations/026_trusted_worker_release_privileges.sql")
RAILWAY_PRODUCTION = Path("railway.brain-api-live.toml")


def test_migration_026_is_unique_and_preserves_prior_migrations() -> None:
    assert MIGRATION.exists()
    duplicates = [
        path
        for path in Path("db/migrations").glob("026_*.sql")
        if path != MIGRATION
    ]
    assert not duplicates, f"migration version 026 claimed by more than one file: {duplicates}"
    for version in range(19, 26):
        assert len(list(Path("db/migrations").glob(f"{version:03d}_*.sql"))) == 1


def test_migration_026_keeps_api_runtime_out_of_worker_only_tables() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    for table in (
        "source_connector_runtime_state",
        "source_connector_ingestion_runs",
        "source_connector_observations",
    ):
        assert table in sql
    assert "from brain_runtime_role" in sql
    assert "to brain_trusted_service_role" in sql
    assert "current_brain_service_context()" in sql
    assert "money_lanes" in sql
    assert "revenue_source_scores" in sql


def test_production_migration_ceiling_remains_018() -> None:
    config = RAILWAY_PRODUCTION.read_text(encoding="utf-8")
    assert "python tools/apply_migrations.py --max-version 18" in config
