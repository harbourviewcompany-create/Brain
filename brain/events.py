from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from .domain import utcnow


@dataclass(slots=True, frozen=True)
class BrainEvent:
    event_type: str
    aggregate_type: str
    aggregate_id: UUID
    payload: dict[str, Any]
    causation_id: UUID | None = None
    correlation_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utcnow)
