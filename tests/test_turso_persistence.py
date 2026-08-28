from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from brain.adapters.turso import (
    TursoDatabase,
    TursoEventStore,
    TursoProjectionCheckpointStore,
    TursoTelemetryStore,
)
from brain.events import BrainEvent
from brain.storage_policy import StoragePolicy, StoragePressure

UTC = timezone.utc
BASE = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def uid(value: int) -> UUID:
    return UUID(int=value)


def event(
    value: int,
    *,
    event_type: str = "belief.updated",
    seconds: int = 0,
    causation: int | None = None,
    correlation: int | None = None,
) -> BrainEvent:
    return BrainEvent(
        id=uid(value),
        event_type=event_type,
        aggregate_type="belief",
        aggregate_id=uid(10_000 + value),
        causation_id=uid(causation) if causation is not None else None,
        correlation_id=uid(correlation) if correlation is not None else None,
        payload={"value": value, "nested": {"stable": True}},
        occurred_at=BASE + timedelta(seconds=seconds),
    )


@pytest.fixture
def db(tmp_path):
    database = TursoDatabase(str(tmp_path / "brain.sqlite"))
    try:
        yield database
    finally:
        database.close()


def test_append_is_idempotent_and_preserves_causation_correlation(db):
    store = TursoEventStore(db)
    original = event(1, causation=91, correlation=92)

    store.append(original)
    store.append(original)

    rows = store.read_all()
    assert len(rows) == 1
    assert rows[0] == original
    assert rows[0].causation_id == uid(91)
    assert rows[0].correlation_id == uid(92)
    assert store.count_by_type(["belief.updated"]) == {"belief.updated": 1}


def test_append_many_matches_postgres_submitted_count_semantics(db):
    store = TursoEventStore(db)
    first = event(1)
    second = event(2, event_type="cycle.completed")

    assert store.append_many([first, second, first]) == 3
    assert [item.id for item in store.read_all()] == [first.id, second.id]
    assert store.count_by_type(["belief.updated", "cycle.completed"]) == {
        "belief.updated": 1,
        "cycle.completed": 1,
    }


def test_chronological_replay_is_occurred_at_then_id_not_append_order(db):
    store = TursoEventStore(db)
    later = event(3, seconds=20)
    same_time_high_id = event(2, seconds=10)
    same_time_low_id = event(1, seconds=10)

    store.append_many([later, same_time_high_id, same_time_low_id])

    assert [item.id for item in store.read_all()] == [
        same_time_low_id.id,
        same_time_high_id.id,
        later.id,
    ]


def test_read_recent_filters_types_and_returns_newest_first(db):
    store = TursoEventStore(db)
    events = [
        event(1, event_type="a", seconds=1),
        event(2, event_type="b", seconds=2),
        event(3, event_type="a", seconds=3),
        event(4, event_type="a", seconds=4),
    ]
    store.append_many(events)

    assert [item.id for item in store.read_recent(event_types=["a"], limit=2)] == [
        uid(4),
        uid(3),
    ]
    assert store.read_recent(event_types=[], limit=10) == []
    assert store.read_recent(event_types=["a"], limit=0) == []


def test_read_after_uses_strict_postgres_cursor_semantics(db):
    store = TursoEventStore(db)
    first = event(1, seconds=10)
    second = event(2, seconds=10)
    third = event(3, seconds=11)
    store.append_many([first, second, third])

    assert [item.id for item in store.read_after(first.occurred_at, first.id)] == [
        second.id,
        third.id,
    ]
    assert [item.id for item in store.read_after(second.occurred_at, second.id)] == [third.id]


def test_projection_checkpoint_save_get_and_overwrite_equivalence(db):
    checkpoints = TursoProjectionCheckpointStore(db)
    assert checkpoints.get("beliefs") is None

    checkpoints.save(
        "beliefs",
        last_event_id=uid(1),
        event_count=7,
        state={"version": 1, "nested": {"ok": True}},
    )
    first = checkpoints.get("beliefs")
    assert first is not None
    assert first["projection_name"] == "beliefs"
    assert first["last_event_id"] == uid(1)
    assert first["event_count"] == 7
    assert first["state"] == {"version": 1, "nested": {"ok": True}}

    checkpoints.save(
        "beliefs",
        last_event_id=uid(2),
        event_count=8,
        state={"version": 2},
    )
    second = checkpoints.get("beliefs")
    assert second is not None
    assert second["last_event_id"] == uid(2)
    assert second["event_count"] == 8
    assert second["state"] == {"version": 2}


def test_compaction_preserves_complete_replay_across_archive_and_hot_history(db):
    store = TursoEventStore(db)
    old = [event(1, seconds=1), event(2, seconds=2), event(3, seconds=3)]
    hot = event(4, seconds=100)
    store.append_many([*old, hot])

    result = store.compact_before(BASE + timedelta(seconds=50), max_events=10)

    assert result["compacted"] == 3
    assert result["segment_id"]
    assert len(result["sha256"]) == 64
    assert [item.id for item in store.read_all()] == [uid(1), uid(2), uid(3), uid(4)]
    assert [item.id for item in store.read_recent(event_types=["belief.updated"], limit=4)] == [
        uid(4), uid(3), uid(2), uid(1)
    ]
    assert [item.id for item in store.read_after(old[1].occurred_at, old[1].id)] == [uid(3), uid(4)]


def test_duplicate_id_stays_idempotent_after_hot_event_is_archived(db):
    store = TursoEventStore(db)
    original = event(1, seconds=1)
    store.append(original)
    assert store.compact_before(BASE + timedelta(seconds=2))["compacted"] == 1

    assert db.fetchone("SELECT count(*) AS n FROM brain_events")["n"] == 0
    assert db.fetchone("SELECT count(*) AS n FROM brain_event_ids")["n"] == 1

    store.append(original)

    assert [item.id for item in store.read_all()] == [original.id]
    assert db.fetchone("SELECT count(*) AS n FROM brain_event_ids")["n"] == 1
    assert store.count_by_type([original.event_type]) == {original.event_type: 1}


def test_archive_segment_tamper_is_detected_before_replay(db):
    store = TursoEventStore(db)
    store.append(event(1, seconds=1))
    store.compact_before(BASE + timedelta(seconds=2))
    db.execute("UPDATE brain_event_segments SET payload=?", (b"tampered",))
    db.commit()

    with pytest.raises(RuntimeError, match="integrity check failed"):
        store.read_all()


def test_telemetry_is_disposable_and_separate_from_canonical_events(db):
    policy = StoragePolicy(budget_bytes=10**12)
    telemetry = TursoTelemetryStore(db, storage_policy=policy)
    store = TursoEventStore(db, storage_policy=policy)

    store.append(event(1))
    assert telemetry.append(
        "request.duration",
        {"ms": 12},
        occurred_at=BASE,
        expires_at=BASE + timedelta(hours=1),
    )
    assert db.fetchone("SELECT count(*) AS n FROM brain_telemetry")["n"] == 1
    assert len(store.read_all()) == 1

    assert telemetry.prune_expired(BASE + timedelta(hours=2)) == 1
    assert db.fetchone("SELECT count(*) AS n FROM brain_telemetry")["n"] == 0
    assert len(store.read_all()) == 1


def test_storage_pressure_refuses_optional_telemetry_but_not_canonical_events(db, monkeypatch):
    policy = StoragePolicy(
        budget_bytes=100,
        compact_at=0.60,
        aggressive_at=0.70,
        throttle_optional_at=0.80,
        refuse_optional_at=0.85,
    )
    monkeypatch.setattr(db, "estimated_size_bytes", lambda: 90)
    telemetry = TursoTelemetryStore(db, storage_policy=policy)
    event_store = TursoEventStore(db, storage_policy=policy)

    assert telemetry.append(
        "disposable",
        {"drop": "allowed"},
        occurred_at=BASE,
        expires_at=BASE + timedelta(days=1),
    ) is False

    canonical = event(1)
    event_store.append(canonical)
    assert [item.id for item in event_store.read_all()] == [canonical.id]


def test_storage_pressure_thresholds_are_machine_deterministic():
    policy = StoragePolicy(budget_bytes=100)
    assert policy.pressure(59) is StoragePressure.NORMAL
    assert policy.pressure(60) is StoragePressure.COMPACT
    assert policy.pressure(70) is StoragePressure.AGGRESSIVE_COMPACTION
    assert policy.pressure(80) is StoragePressure.THROTTLE_OPTIONAL
    assert policy.pressure(85) is StoragePressure.REFUSE_OPTIONAL
    assert policy.optional_writes_allowed(84)
    assert not policy.optional_writes_allowed(85)
