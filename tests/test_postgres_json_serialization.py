from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from brain.adapters.postgres import _jsonable
from brain.domain import BeliefState


def test_postgres_payload_normalizer_handles_domain_types_deterministically() -> None:
    identifier = uuid4()
    timestamp = datetime(2026, 8, 23, 22, 0, tzinfo=UTC)
    payload = {
        "id": identifier,
        "state": BeliefState.PROVISIONAL,
        "updated_at": timestamp,
        "evidence_ids": {uuid4(), uuid4()},
        "nested": [{"when": timestamp, "owner": identifier}],
    }

    normalized = _jsonable(payload)

    assert normalized["id"] == str(identifier)
    assert normalized["state"] == "provisional"
    assert normalized["updated_at"] == timestamp.isoformat()
    assert normalized["evidence_ids"] == sorted(normalized["evidence_ids"])
    assert normalized["nested"][0]["owner"] == str(identifier)
    json.dumps(normalized)
