from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence
from uuid import UUID

from brain.adapters.turso import TursoDatabase, TursoEventStore
from brain.events import BrainEvent

UTC = timezone.utc


def jsonable(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return jsonable(value.value)
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, set):
        return [jsonable(item) for item in sorted(value, key=str)]
    return value


def canonical_event(
    *,
    event_id: Any,
    event_type: Any,
    aggregate_type: Any,
    aggregate_id: Any,
    causation_id: Any,
    correlation_id: Any,
    payload: Any,
    occurred_at: Any,
) -> bytes:
    item = {
        "id": jsonable(event_id),
        "event_type": str(event_type),
        "aggregate_type": str(aggregate_type),
        "aggregate_id": jsonable(aggregate_id),
        "causation_id": jsonable(causation_id),
        "correlation_id": jsonable(correlation_id),
        "payload": jsonable(payload),
        "occurred_at": jsonable(occurred_at),
    }
    return json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_payloads(payloads: Iterable[bytes]) -> tuple[int, str, str | None, str | None]:
    digest = hashlib.sha256()
    count = 0
    first_id: str | None = None
    last_id: str | None = None
    for payload in payloads:
        item = json.loads(payload)
        if first_id is None:
            first_id = str(item["id"])
        last_id = str(item["id"])
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
        count += 1
    return count, digest.hexdigest(), first_id, last_id


def postgres_payloads(connection: Any) -> Iterable[bytes]:
    with connection.cursor(name="brain_replay_equivalence") as cursor:
        cursor.itersize = 1000
        cursor.execute(
            """
            SELECT id,event_type,aggregate_type,aggregate_id,causation_id,
                   correlation_id,payload,occurred_at
            FROM public.brain_events
            ORDER BY occurred_at ASC,id ASC
            """
        )
        for row in cursor:
            yield canonical_event(
                event_id=row[0],
                event_type=row[1],
                aggregate_type=row[2],
                aggregate_id=row[3],
                causation_id=row[4],
                correlation_id=row[5],
                payload=row[6],
                occurred_at=row[7],
            )


def turso_payloads(events: Iterable[BrainEvent]) -> Iterable[bytes]:
    for event in events:
        yield canonical_event(
            event_id=event.id,
            event_type=event.event_type,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            causation_id=event.causation_id,
            correlation_id=event.correlation_id,
            payload=event.payload,
            occurred_at=event.occurred_at,
        )


def verify(postgres_dsn: str, sqlite_path: Path, output: Path) -> dict[str, Any]:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg dependencies are required") from exc

    with psycopg.connect(postgres_dsn) as source:
        source.read_only = True
        source.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        source_result = digest_payloads(postgres_payloads(source))

    database = TursoDatabase(str(sqlite_path))
    try:
        destination_result = digest_payloads(turso_payloads(TursoEventStore(database).read_all()))
    finally:
        database.close()

    names = ("event_count", "sha256_replay", "first_event_id", "last_event_id")
    source_payload = dict(zip(names, source_result, strict=True))
    destination_payload = dict(zip(names, destination_result, strict=True))
    result = {
        "verified": source_payload == destination_payload,
        "source": source_payload,
        "destination": destination_payload,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not result["verified"]:
        raise RuntimeError("canonical event replay equivalence failed")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres-dsn", required=True)
    parser.add_argument("--sqlite", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify(args.postgres_dsn, args.sqlite, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
