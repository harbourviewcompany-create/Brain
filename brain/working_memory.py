from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any
from uuid import UUID, uuid4

from .domain import utcnow


@dataclass(slots=True)
class WorkingMemorySlot:
    """One item in the capacity-limited active context buffer."""

    content: dict[str, Any]
    salience: float
    source_event_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    entered_at: Any = field(default_factory=utcnow)
    last_accessed_at: Any = field(default_factory=utcnow)
    access_count: int = 0

    def touch(self) -> WorkingMemorySlot:
        return replace(
            self,
            last_accessed_at=utcnow(),
            access_count=self.access_count + 1,
        )


class WorkingMemory:
    """Bounded active context. Eviction prefers lowest salience, then oldest.

    Capacity defaults to 7 (classic Miller-range working-memory span).
    Evicted items are returned so callers can emit episodic consolidation events.
    """

    def __init__(self, capacity: int = 7) -> None:
        if capacity < 1:
            raise ValueError("working memory capacity must be >= 1")
        self.capacity = capacity
        self._slots: list[WorkingMemorySlot] = []

    @property
    def size(self) -> int:
        return len(self._slots)

    def snapshot(self) -> list[WorkingMemorySlot]:
        return list(self._slots)

    def encode(
        self,
        content: dict[str, Any],
        salience: float,
        *,
        source_event_id: UUID | None = None,
    ) -> tuple[WorkingMemorySlot, list[WorkingMemorySlot]]:
        """Insert an item. Returns (stored_slot, evicted_slots)."""
        salience = max(0.0, min(1.0, float(salience)))
        slot = WorkingMemorySlot(
            content=dict(content),
            salience=salience,
            source_event_id=source_event_id,
        )
        self._slots.append(slot)
        evicted: list[WorkingMemorySlot] = []
        while len(self._slots) > self.capacity:
            victim = min(
                self._slots,
                key=lambda s: (s.salience, s.entered_at, str(s.id)),
            )
            self._slots.remove(victim)
            evicted.append(victim)
        return slot, evicted

    def retrieve(self, *, min_salience: float = 0.0) -> list[WorkingMemorySlot]:
        """Return slots above min_salience, most salient first; marks access."""
        matched = [s for s in self._slots if s.salience >= min_salience]
        matched.sort(key=lambda s: (-s.salience, s.entered_at))
        refreshed: list[WorkingMemorySlot] = []
        for slot in matched:
            touched = slot.touch()
            idx = self._slots.index(slot)
            self._slots[idx] = touched
            refreshed.append(touched)
        return refreshed

    def decay(self, rate: float = 0.05) -> list[WorkingMemorySlot]:
        """Reduce salience; drop slots that fall to ~0. Returns dropped slots."""
        rate = max(0.0, min(1.0, rate))
        kept: list[WorkingMemorySlot] = []
        dropped: list[WorkingMemorySlot] = []
        for slot in self._slots:
            new_salience = max(0.0, slot.salience * (1.0 - rate))
            if new_salience <= 0.01:
                dropped.append(slot)
            else:
                kept.append(replace(slot, salience=new_salience))
        self._slots = kept
        return dropped

    def clear(self) -> list[WorkingMemorySlot]:
        cleared = list(self._slots)
        self._slots.clear()
        return cleared
