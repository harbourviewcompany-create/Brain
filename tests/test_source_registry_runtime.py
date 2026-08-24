from pathlib import Path
from uuid import uuid4

import pytest

from brain.source_intelligence import (
    AccessMethod,
    IngestionRunStatus,
    LegalAccessStatus,
    PersistentSourceRegistryRuntime,
    SignalReviewStatus,
    SourceHealthStatus,
    SourceLifecycleStatus,
    SourceRegistryRuntimeError,
    load_registry_fixture,
)


FIXTURE = Path("tests/fixtures/brain/source_intelligence_registry.json")


def active_source():
    return load_registry_fixture(FIXTURE)[0].model_copy(update={"lifecycle_status": SourceLifecycleStatus.ACTIVE})


def test_runtime_records_observation_and_routes_signal() -> None:
    runtime = PersistentSourceRegistryRuntime()
    source = runtime.register_source(active_source())
    run = runtime.start_ingestion_run(source.id, source.best_ingestion_method)

    observation = runtime.record_observation(
        source.id,
        ingestion_run_id=run.run_id,
        raw_summary="New insolvency filing with possible asset-sale implications.",
        extract_hash_or_snapshot_id="court-filing-snapshot-001",
        evidence_refs=["snapshot:court-filing-snapshot-001"],
        confidence=0.82,
    )
    signal = runtime.create_signal_from_observation(observation.observation_id)
    completed = runtime.complete_ingestion_run(run.run_id)

    assert completed.status == IngestionRunStatus.COMPLETED
    assert completed.observations_created == 1
    assert signal.review_status == SignalReviewStatus.INBOX
    assert signal.evidence_refs == ["snapshot:court-filing-snapshot-001"]
    assert runtime.dashboard()["open_signals"] == 1
    assert {event.event_type for event in runtime.source_events(source.id)} >= {
        "SOURCE_REGISTERED",
        "INGESTION_RUN_STARTED",
        "SOURCE_OBSERVATION_RECORDED",
        "SIGNAL_INBOX_ITEM_CREATED",
    }


def test_runtime_deduplicates_observations_by_source_and_snapshot_hash() -> None:
    runtime = PersistentSourceRegistryRuntime()
    source = runtime.register_source(active_source())
    run = runtime.start_ingestion_run(source.id, source.best_ingestion_method)

    first = runtime.record_observation(
        source.id,
        ingestion_run_id=run.run_id,
        raw_summary="Filing observed once.",
        extract_hash_or_snapshot_id="dedupe-hash-001",
        evidence_refs=["snapshot:dedupe-hash-001"],
        confidence=0.7,
    )
    second = runtime.record_observation(
        source.id,
        ingestion_run_id=run.run_id,
        raw_summary="Filing observed again through the same snapshot.",
        extract_hash_or_snapshot_id="dedupe-hash-001",
        evidence_refs=["snapshot:dedupe-hash-001"],
        confidence=0.7,
    )

    assert second.observation_id == first.observation_id
    assert runtime.dashboard()["observations"] == 1
    assert runtime.ingestion_runs[run.run_id].observations_created == 1
    assert any(event.event_type == "SOURCE_OBSERVATION_DEDUPED" for event in runtime.events)


def test_runtime_blocks_unapproved_or_manual_automation_paths() -> None:
    base = active_source()
    runtime = PersistentSourceRegistryRuntime()
    paid = runtime.register_source(base.model_copy(update={"legal_access_status": LegalAccessStatus.PAID_LICENSED}))
    manual = runtime.register_source(
        base.model_copy(update={"id": uuid4(), "legal_access_status": LegalAccessStatus.MANUAL_ONLY})
    )

    with pytest.raises(SourceRegistryRuntimeError):
        runtime.start_ingestion_run(paid.id, paid.best_ingestion_method)

    with pytest.raises(SourceRegistryRuntimeError):
        runtime.start_ingestion_run(manual.id, AccessMethod.HTML_SCRAPE)

    manual_run = runtime.start_ingestion_run(manual.id, AccessMethod.MANUAL_REVIEW)
    assert manual_run.access_method == AccessMethod.MANUAL_REVIEW


def test_health_check_updates_lifecycle_and_dashboard() -> None:
    runtime = PersistentSourceRegistryRuntime()
    source = runtime.register_source(active_source())

    health = runtime.record_health_check(
        source.id,
        SourceHealthStatus.BROKEN,
        "Source layout changed and extraction failed.",
        consecutive_failures=3,
    )

    assert health.status == SourceHealthStatus.BROKEN
    assert runtime.sources[source.id].lifecycle_status == SourceLifecycleStatus.BROKEN
    assert runtime.dashboard()["health_checks"] == 1


def test_snapshot_replay_preserves_registry_state() -> None:
    runtime = PersistentSourceRegistryRuntime()
    source = runtime.register_source(active_source())
    run = runtime.start_ingestion_run(source.id, source.best_ingestion_method)
    observation = runtime.record_observation(
        source.id,
        ingestion_run_id=run.run_id,
        raw_summary="Regulated source produced a market-entry signal.",
        extract_hash_or_snapshot_id="snapshot-replay-001",
        evidence_refs=["snapshot:snapshot-replay-001"],
        confidence=0.9,
    )
    signal = runtime.create_signal_from_observation(observation.observation_id)
    reviewed = runtime.review_signal(
        signal.signal_id,
        SignalReviewStatus.APPROVED,
        reviewer="operator",
        review_note="Evidence is sufficient for opportunity-board review.",
    )

    replayed = PersistentSourceRegistryRuntime(runtime.snapshot())

    assert replayed.dashboard() == runtime.dashboard()
    assert replayed.signal_inbox[reviewed.signal_id].review_status == SignalReviewStatus.APPROVED
    assert replayed.record_observation(
        source.id,
        raw_summary="Duplicate after replay.",
        extract_hash_or_snapshot_id="snapshot-replay-001",
        evidence_refs=["snapshot:snapshot-replay-001"],
        confidence=0.9,
    ).observation_id == observation.observation_id
