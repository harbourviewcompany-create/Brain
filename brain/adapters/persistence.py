from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from ..events import BrainEvent


@runtime_checkable
class BrainEventStore(Protocol):
    """Provider-neutral contract for the canonical cognitive event ledger."""

    def append(self, event: BrainEvent) -> None: ...

    def append_many(self, events: Iterable[BrainEvent]) -> int: ...

    def read_all(self, *, limit: int | None = None) -> list[BrainEvent]: ...

    def read_recent(
        self,
        *,
        event_types: Iterable[str],
        limit: int = 200,
    ) -> list[BrainEvent]: ...

    def read_after(self, occurred_at: datetime, event_id: UUID) -> list[BrainEvent]: ...

    def health(self) -> dict[str, Any]: ...


@runtime_checkable
class ProjectionStore(Protocol):
    """Disposable projection/checkpoint persistence independent of SQL vendor."""

    def save(
        self,
        projection_name: str,
        *,
        last_event_id: UUID | None,
        event_count: int,
        state: dict[str, Any],
    ) -> None: ...

    def get(self, projection_name: str) -> dict[str, Any] | None: ...
