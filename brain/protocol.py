from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from .events import BrainEvent


@dataclass(slots=True)
class EventProtocol:
    """Validation boundary for events entering the cognitive ledger."""

    version: int = 1

    def validate(self, event: BrainEvent) -> None:
        if not event.event_type or "." not in event.event_type:
            raise ValueError("event_type must be namespaced, e.g. belief.created")
        if not event.aggregate_type:
            raise ValueError("aggregate_type is required")
        if not isinstance(event.aggregate_id, UUID):
            raise TypeError("aggregate_id must be a UUID")
        if not isinstance(event.payload, dict):
            raise TypeError("payload must be a dictionary")

    def envelope(self, event: BrainEvent) -> dict[str, Any]:
        self.validate(event)
        return {
            "protocol_version": self.version,
            "id": str(event.id),
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": str(event.aggregate_id),
            "payload": event.payload,
            "causation_id": str(event.causation_id) if event.causation_id else None,
            "correlation_id": str(event.correlation_id) if event.correlation_id else None,
            "occurred_at": event.occurred_at.isoformat(),
        }
