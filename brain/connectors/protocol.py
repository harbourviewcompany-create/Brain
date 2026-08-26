"""Connector protocol — automated external observation intake.

Design principles:
  - Connectors never write beliefs; they only produce observations.
  - Every item carries provenance (URL, retrieved_at, content hash).
  - Legal/access disposition is checked before fetch.
  - Dedupe is hash-based so repeated polls are cheap and safe.
  - Failures are typed and recorded for backoff / health.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConnectorKind(StrEnum):
    RSS = "rss"
    ATOM = "atom"
    HTTP_JSON = "http_json"
    HTTP_TEXT = "http_text"


class AccessDisposition(StrEnum):
    ALLOWED = "allowed"
    RATE_LIMITED = "rate_limited"
    MANUAL_ONLY = "manual_only"
    PROHIBITED = "prohibited"
    UNKNOWN = "unknown"


class FetchStatus(StrEnum):
    SUCCESS = "success"
    EMPTY = "empty"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class ConnectorSource:
    """Operational source config for automated fetch (leaner than full registry record)."""

    source_key: str
    url: str
    kind: ConnectorKind
    name: str = ""
    access: AccessDisposition = AccessDisposition.ALLOWED
    refresh_seconds: int = 300
    enabled: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    json_items_path: str = ""
    json_title_field: str = "title"
    json_body_field: str = "body"
    json_url_field: str = "url"
    json_id_field: str = "id"
    max_items_per_fetch: int = 25
    timeout_seconds: float = 20.0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    last_fetched_at: datetime | None = None
    last_success_at: datetime | None = None
    consecutive_failures: int = 0
    next_due_at: datetime = field(default_factory=utcnow)

    def is_due(self, now: datetime | None = None) -> bool:
        now = now or utcnow()
        if not self.enabled:
            return False
        if self.access in {AccessDisposition.PROHIBITED, AccessDisposition.MANUAL_ONLY}:
            return False
        return now >= self.next_due_at

    def schedule_next(self, *, success: bool, now: datetime | None = None) -> None:
        now = now or utcnow()
        self.last_fetched_at = now
        base = max(30, int(self.refresh_seconds))
        if success:
            self.consecutive_failures = 0
            self.last_success_at = now
            delay = base
        else:
            self.consecutive_failures += 1
            delay = min(base * (2 ** min(self.consecutive_failures, 6)), 6 * 3600)
        if self.access == AccessDisposition.RATE_LIMITED:
            delay = max(delay, base * 2)
        self.next_due_at = now + timedelta(seconds=delay)


@dataclass(slots=True)
class RawObservationItem:
    """One unit of fetched content ready for normalize + inbox enqueue."""

    title: str
    content: str
    claim: str
    source_url: str
    item_id: str
    content_hash: str
    observed_at: datetime = field(default_factory=utcnow)
    confidence: float = 0.55
    signal_hints: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchResult:
    source_key: str
    status: FetchStatus
    items: list[RawObservationItem] = field(default_factory=list)
    error: str | None = None
    http_status: int | None = None
    retrieved_at: datetime = field(default_factory=utcnow)
    bytes_read: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in {FetchStatus.SUCCESS, FetchStatus.EMPTY, FetchStatus.PARTIAL}


class SourceConnector(Protocol):
    """Fetch observations for a single source configuration."""

    kind: ConnectorKind

    def supports(self, source: ConnectorSource) -> bool: ...

    def fetch(self, source: ConnectorSource) -> FetchResult: ...


class ConnectorRegistry(Protocol):
    def list_sources(self) -> list[ConnectorSource]: ...

    def get(self, source_key: str) -> ConnectorSource | None: ...

    def upsert(self, source: ConnectorSource) -> ConnectorSource: ...

    def due_sources(self, now: datetime | None = None) -> list[ConnectorSource]: ...

    def mark_fetch(self, source_key: str, *, success: bool) -> None: ...


class InboxEnqueuer(Protocol):
    def enqueue(
        self,
        *,
        source_key: str,
        content: str,
        claim: str,
        payload: dict[str, Any] | None = None,
    ) -> Any: ...
