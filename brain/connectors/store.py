"""In-memory connector source registry with due scheduling."""

from __future__ import annotations

from datetime import datetime
from threading import RLock

from .protocol import ConnectorSource, utcnow


class InMemoryConnectorRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, ConnectorSource] = {}
        self._lock = RLock()
        self._seen_hashes: set[str] = set()

    def list_sources(self) -> list[ConnectorSource]:
        with self._lock:
            return list(self._sources.values())

    def get(self, source_key: str) -> ConnectorSource | None:
        with self._lock:
            return self._sources.get(source_key)

    def upsert(self, source: ConnectorSource) -> ConnectorSource:
        with self._lock:
            self._sources[source.source_key] = source
            return source

    def due_sources(self, now: datetime | None = None) -> list[ConnectorSource]:
        now = now or utcnow()
        with self._lock:
            due = [s for s in self._sources.values() if s.is_due(now)]
            due.sort(key=lambda s: (s.next_due_at, s.source_key))
            return due

    def mark_fetch(self, source_key: str, *, success: bool) -> None:
        with self._lock:
            src = self._sources.get(source_key)
            if src is None:
                return
            src.schedule_next(success=success)

    def remember_hash(self, content_hash: str) -> bool:
        """Return True if this hash is new (not seen before)."""
        with self._lock:
            if content_hash in self._seen_hashes:
                return False
            self._seen_hashes.add(content_hash)
            if len(self._seen_hashes) > 50_000:
                self._seen_hashes = set(list(self._seen_hashes)[25_000:])
            return True

    def seen_count(self) -> int:
        with self._lock:
            return len(self._seen_hashes)
