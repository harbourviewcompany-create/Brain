from datetime import UTC, datetime
from uuid import uuid4

from brain.adapters.postgres import PostgresEventStore


def test_row_to_event_round_trip_shape():
    event_id = uuid4()
    aggregate_id = uuid4()
    occurred_at = datetime.now(UTC)
    row = {
        "id": event_id,
        "event_type": "belief.created",
        "aggregate_type": "belief",
        "aggregate_id": aggregate_id,
        "causation_id": None,
        "correlation_id": None,
        "payload": {"statement": "test", "confidence": 0.5},
        "occurred_at": occurred_at,
    }

    event = PostgresEventStore._row_to_event(row)

    assert event.id == event_id
    assert event.aggregate_id == aggregate_id
    assert event.payload["statement"] == "test"
    assert event.occurred_at == occurred_at
