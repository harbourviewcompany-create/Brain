"""Sensory inbox: queue of external stimuli for the continuous cognition runner.

In-memory implementation mirrors the sensory_inbox table contract in
db/migrations/005_continuous_cognition.sql so a Postgres adapter can swap in
without changing ContinuousCognitionRunner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class InboxItem:
    id: UUID
    source_key: str
    content: str
    claim: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    attempts: int = 0
    available_at: datetime = field(default_factory=_utcnow)
    claimed_at: datetime | None = None
    completed_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime = field(default_factory=_utcnow)

    def as_runner_dict(self) -> dict[str, Any]:
        """Shape expected by ContinuousCognitionRunner.run_once."""
        return {
            "id": self.id,
            "source_key": self.source_key,
            "content": self.content,
            "claim": self.claim,
            "payload": dict(self.payload),
            "attempts": self.attempts,
            "status": self.status,
        }


class InMemorySensoryInbox:
    """Thread-safe in-process sensory inbox."""

    def __init__(self) -> None:
        self._items: dict[UUID, InboxItem] = {}
        self._order: list[UUID] = []
        self._lock = Lock()

    def enqueue(
        self,
        *,
        source_key: str,
        content: str,
        claim: str,
        payload: dict[str, Any] | None = None,
    ) -> InboxItem:
        item = InboxItem(
            id=uuid4(),
            source_key=source_key,
            content=content,
            claim=claim,
            payload=dict(payload or {}),
        )
        with self._lock:
            self._items[item.id] = item
            self._order.append(item.id)
        return item

    def claim_next(self) -> dict[str, Any] | None:
        with self._lock:
            now = _utcnow()
            for item_id in self._order:
                item = self._items[item_id]
                if item.status != "pending":
                    continue
                if item.available_at > now:
                    continue
                item.status = "processing"
                item.attempts += 1
                item.claimed_at = now
                return item.as_runner_dict()
        return None

    def complete(self, item_id: UUID) -> None:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return
            item.status = "completed"
            item.completed_at = _utcnow()
            item.last_error = None

    def fail(self, item_id: UUID, error: str, *, retry: bool = True) -> None:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return
            item.last_error = error
            if retry:
                item.status = "pending"
                item.available_at = _utcnow() + timedelta(seconds=min(30, item.attempts))
            else:
                item.status = "failed"
                item.completed_at = _utcnow()

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for i in self._items.values() if i.status == "pending")

    def stats(self) -> dict[str, int]:
        with self._lock:
            counts = {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "total": len(self._items),
            }
            for item in self._items.values():
                if item.status in counts:
                    counts[item.status] += 1
            return counts
