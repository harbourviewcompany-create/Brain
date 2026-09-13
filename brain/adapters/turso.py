from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
import threading
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from ..events import BrainEvent
from ..storage_policy import DEFAULT_STORAGE_BUDGET_BYTES, StoragePolicy
from .turso_schema import TURSO_SCHEMA


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value, key=str)]
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"))


def _json_loads(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if not str(value).strip():
        return default
    try:
        return json.loads(str(value))
    except (TypeError, ValueError):
        return default


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _uuid(value: Any) -> UUID | None:
    return UUID(str(value)) if value not in (None, "") else None


def _rows(cursor: Any) -> list[dict[str, Any]]:
    names = [str(column[0]) for column in (cursor.description or [])]
    return [dict(zip(names, row, strict=False)) for row in cursor.fetchall()]


class TursoDatabase:
    """Tiny DB-API boundary shared by remote libSQL and local SQLite tests."""

    def __init__(
        self,
        database_url: str | None = None,
        auth_token: str | None = None,
        *,
        connection: Any | None = None,
    ) -> None:
        self._owns_connection = connection is None
        self._lock = threading.RLock()
        if connection is not None:
            self.connection = connection
        else:
            url = (database_url or "").strip()
            if not url:
                raise ValueError("TURSO_DATABASE_URL is required")
            if url == ":memory:" or url.startswith("file:") or "://" not in url:
                self.connection = sqlite3.connect(url, check_same_thread=False, uri=url.startswith("file:"))
            else:
                if not auth_token:
                    raise ValueError("TURSO_AUTH_TOKEN is required for remote Turso")
                try:
                    import libsql
                except ImportError as exc:  # pragma: no cover - packaging guard
                    raise RuntimeError("Turso remote access requires the libsql dependency") from exc
                self.connection = libsql.connect(database=url, auth_token=auth_token)
        self.bootstrap()

    @classmethod
    def from_env(cls) -> "TursoDatabase":
        return cls(
            os.environ.get("TURSO_DATABASE_URL"),
            os.environ.get("TURSO_AUTH_TOKEN"),
        )

    def bootstrap(self) -> None:
        with self._lock:
            self.connection.executescript(TURSO_SCHEMA)
            # Existing migrated ledgers predate the permanent identity/count
            # tables. Populate them only where the identity table is empty so
            # process restarts cannot double counters.
            existing = self.connection.execute("SELECT count(*) FROM brain_event_ids").fetchone()[0]
            if int(existing) == 0:
                self.connection.execute(
                    "INSERT OR IGNORE INTO brain_event_ids(id, occurred_at) "
                    "SELECT id, occurred_at FROM brain_events"
                )
                counts = self.connection.execute(
                    "SELECT event_type, count(*) FROM brain_events GROUP BY event_type"
                ).fetchall()
                for event_type, event_count in counts:
                    self.connection.execute(
                        "INSERT OR REPLACE INTO brain_event_type_counts(event_type, event_count) "
                        "VALUES (?, ?)",
                        (event_type, int(event_count)),
                    )
            self.connection.commit()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        with self._lock:
            return self.connection.execute(sql, params)

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock:
            return _rows(self.connection.execute(sql, params))

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self.fetchall(sql, params)
        return rows[0] if rows else None

    def commit(self) -> None:
        with self._lock:
            self.connection.commit()

    def close(self) -> None:
        if self._owns_connection:
            self.connection.close()

    def estimated_size_bytes(self) -> int | None:
        """Return exact SQLite file pages where supported, otherwise unknown."""
        try:
            with self._lock:
                page_count = int(self.connection.execute("PRAGMA page_count").fetchone()[0])
                page_size = int(self.connection.execute("PRAGMA page_size").fetchone()[0])
            return page_count * page_size
        except Exception:
            return None


class TursoEventStore:
    """Canonical event ledger with idempotency across hot and archived history."""

    def __init__(self, db: TursoDatabase, *, storage_policy: StoragePolicy | None = None) -> None:
        self.db = db
        budget = int(os.environ.get("BRAIN_STORAGE_BUDGET_BYTES") or DEFAULT_STORAGE_BUDGET_BYTES)
        self.storage_policy = storage_policy or StoragePolicy(budget_bytes=budget)

    @staticmethod
    def _event_values(event: BrainEvent) -> tuple[Any, ...]:
        return (
            str(event.id),
            event.event_type,
            event.aggregate_type,
            str(event.aggregate_id),
            str(event.causation_id) if event.causation_id else None,
            str(event.correlation_id) if event.correlation_id else None,
            _json_dumps(event.payload),
            _iso(event.occurred_at),
        )

    def append(self, event: BrainEvent) -> None:
        with self.db._lock:
            cur = self.db.connection.execute(
                "INSERT OR IGNORE INTO brain_event_ids(id, occurred_at) VALUES (?, ?)",
                (str(event.id), _iso(event.occurred_at)),
            )
            if int(cur.rowcount or 0) == 0:
                self.db.connection.rollback()
                return
            self.db.connection.execute(
                """
                INSERT INTO brain_events(
                    id,event_type,aggregate_type,aggregate_id,causation_id,
                    correlation_id,payload,occurred_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                self._event_values(event),
            )
            self.db.connection.execute(
                """
                INSERT INTO brain_event_type_counts(event_type,event_count) VALUES (?,1)
                ON CONFLICT(event_type) DO UPDATE SET event_count=event_count+1
                """,
                (event.event_type,),
            )
            self.db.connection.commit()

    def append_many(self, events: Iterable[BrainEvent]) -> int:
        materialized = list(events)
        if not materialized:
            return 0
        with self.db._lock:
            try:
                self.db.connection.execute("BEGIN")
                for event in materialized:
                    cur = self.db.connection.execute(
                        "INSERT OR IGNORE INTO brain_event_ids(id, occurred_at) VALUES (?, ?)",
                        (str(event.id), _iso(event.occurred_at)),
                    )
                    if int(cur.rowcount or 0) == 0:
                        continue
                    self.db.connection.execute(
                        """
                        INSERT INTO brain_events(
                            id,event_type,aggregate_type,aggregate_id,causation_id,
                            correlation_id,payload,occurred_at
                        ) VALUES (?,?,?,?,?,?,?,?)
                        """,
                        self._event_values(event),
                    )
                    self.db.connection.execute(
                        """
                        INSERT INTO brain_event_type_counts(event_type,event_count) VALUES (?,1)
                        ON CONFLICT(event_type) DO UPDATE SET event_count=event_count+1
                        """,
                        (event.event_type,),
                    )
                self.db.connection.commit()
            except Exception:
                self.db.connection.rollback()
                raise
        # Match PostgresEventStore: report submitted count, not inserted count.
        return len(materialized)

    @staticmethod
    def _row_to_event(row: dict[str, Any]) -> BrainEvent:
        return BrainEvent(
            id=UUID(str(row["id"])),
            event_type=str(row["event_type"]),
            aggregate_type=str(row["aggregate_type"]),
            aggregate_id=UUID(str(row["aggregate_id"])),
            causation_id=_uuid(row.get("causation_id")),
            correlation_id=_uuid(row.get("correlation_id")),
            payload=dict(_json_loads(row.get("payload"), {})),
            occurred_at=_dt(row["occurred_at"]),
        )

    def _archived_events(self) -> list[BrainEvent]:
        rows = self.db.fetchall(
            "SELECT payload,sha256 FROM brain_event_segments ORDER BY first_occurred_at,first_event_id"
        )
        events: list[BrainEvent] = []
        for row in rows:
            payload = bytes(row["payload"])
            if hashlib.sha256(payload).hexdigest() != str(row["sha256"]):
                raise RuntimeError("event segment integrity check failed")
            for line in gzip.decompress(payload).decode("utf-8").splitlines():
                if line:
                    events.append(self._row_to_event(json.loads(line)))
        return events

    def read_all(self, *, limit: int | None = None) -> list[BrainEvent]:
        if limit is not None and limit <= 0:
            return []
        events = self._archived_events()
        rows = self.db.fetchall(
            """
            SELECT id,event_type,aggregate_type,aggregate_id,causation_id,
                   correlation_id,payload,occurred_at
            FROM brain_events ORDER BY occurred_at,id
            """
        )
        events.extend(self._row_to_event(row) for row in rows)
        events.sort(key=lambda event: (event.occurred_at, str(event.id)))
        return events if limit is None else events[:limit]

    def read_recent(
        self,
        *,
        event_types: Iterable[str],
        limit: int = 200,
    ) -> list[BrainEvent]:
        if limit <= 0:
            return []
        wanted = sorted({str(value).strip() for value in event_types if str(value).strip()})
        if not wanted:
            return []
        placeholders = ",".join("?" for _ in wanted)
        rows = self.db.fetchall(
            f"""
            SELECT id,event_type,aggregate_type,aggregate_id,causation_id,
                   correlation_id,payload,occurred_at
            FROM brain_events WHERE event_type IN ({placeholders})
            ORDER BY occurred_at DESC,id DESC LIMIT ?
            """,
            tuple(wanted) + (limit,),
        )
        events = [self._row_to_event(row) for row in rows]
        if len(events) < limit:
            archived = [event for event in self._archived_events() if event.event_type in wanted]
            events.extend(archived)
        events.sort(key=lambda event: (event.occurred_at, str(event.id)), reverse=True)
        return events[:limit]

    def read_after(self, occurred_at: datetime, event_id: UUID) -> list[BrainEvent]:
        cursor = (occurred_at, str(event_id))
        events = [
            event
            for event in self._archived_events()
            if (event.occurred_at, str(event.id)) > cursor
        ]
        rows = self.db.fetchall(
            """
            SELECT id,event_type,aggregate_type,aggregate_id,causation_id,
                   correlation_id,payload,occurred_at FROM brain_events
            WHERE occurred_at > ? OR (occurred_at = ? AND id > ?)
            ORDER BY occurred_at,id
            """,
            (_iso(occurred_at), _iso(occurred_at), str(event_id)),
        )
        events.extend(self._row_to_event(row) for row in rows)
        events.sort(key=lambda event: (event.occurred_at, str(event.id)))
        return events

    def count_by_type(self, event_types: Iterable[str]) -> dict[str, int]:
        wanted = sorted({str(value).strip() for value in event_types if str(value).strip()})
        if not wanted:
            return {}
        placeholders = ",".join("?" for _ in wanted)
        rows = self.db.fetchall(
            f"SELECT event_type,event_count FROM brain_event_type_counts "
            f"WHERE event_type IN ({placeholders})",
            tuple(wanted),
        )
        return {str(row["event_type"]): int(row["event_count"]) for row in rows}

    def compact_before(self, cutoff: datetime, *, max_events: int = 5000) -> dict[str, Any]:
        """Move old hot events into a deterministic immutable gzip segment.

        The transaction inserts and verifies the segment before deleting the hot
        rows. brain_event_ids and type counters are intentionally retained.
        """
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        rows = self.db.fetchall(
            """
            SELECT id,event_type,aggregate_type,aggregate_id,causation_id,
                   correlation_id,payload,occurred_at FROM brain_events
            WHERE occurred_at < ? ORDER BY occurred_at,id LIMIT ?
            """,
            (_iso(cutoff), max_events),
        )
        if not rows:
            return {"compacted": 0, "segment_id": None}
        canonical = b"".join(
            (_json_dumps(row) + "\n").encode("utf-8") for row in rows
        )
        compressed = gzip.compress(canonical, compresslevel=9, mtime=0)
        digest = hashlib.sha256(compressed).hexdigest()
        segment_id = str(uuid4())
        event_types = sorted({str(row["event_type"]) for row in rows})
        created_at = _iso(datetime.now(timezone.utc))
        with self.db._lock:
            try:
                self.db.connection.execute("BEGIN")
                self.db.connection.execute(
                    """
                    INSERT INTO brain_event_segments(
                        segment_id,first_occurred_at,first_event_id,last_occurred_at,
                        last_event_id,event_count,event_types,compression,sha256,payload,created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        segment_id,
                        rows[0]["occurred_at"],
                        rows[0]["id"],
                        rows[-1]["occurred_at"],
                        rows[-1]["id"],
                        len(rows),
                        _json_dumps(event_types),
                        "gzip+ndjson-v1",
                        digest,
                        compressed,
                        created_at,
                    ),
                )
                check = self.db.connection.execute(
                    "SELECT sha256,length(payload) FROM brain_event_segments WHERE segment_id=?",
                    (segment_id,),
                ).fetchone()
                if not check or str(check[0]) != digest or int(check[1]) != len(compressed):
                    raise RuntimeError("event segment verification failed before hot delete")
                self.db.connection.executemany(
                    "DELETE FROM brain_events WHERE id=?",
                    [(str(row["id"]),) for row in rows],
                )
                self.db.connection.commit()
            except Exception:
                self.db.connection.rollback()
                raise
        return {
            "compacted": len(rows),
            "segment_id": segment_id,
            "sha256": digest,
            "compressed_bytes": len(compressed),
        }

    def health(self) -> dict[str, Any]:
        row = self.db.fetchone("SELECT count(*) AS count FROM brain_event_ids") or {"count": 0}
        hot = self.db.fetchone("SELECT count(*) AS count FROM brain_events") or {"count": 0}
        segments = self.db.fetchone(
            "SELECT count(*) AS count,coalesce(sum(event_count),0) AS archived FROM brain_event_segments"
        ) or {"count": 0, "archived": 0}
        used = self.db.estimated_size_bytes()
        payload: dict[str, Any] = {
            "reachable": True,
            "canonical_event_count": int(row["count"]),
            "hot_event_count": int(hot["count"]),
            "archived_event_count": int(segments["archived"]),
            "segment_count": int(segments["count"]),
            "budget_bytes": self.storage_policy.budget_bytes,
        }
        if used is not None:
            payload.update(
                {
                    "estimated_bytes": used,
                    "storage_utilization": self.storage_policy.utilization(used),
                    "storage_pressure": self.storage_policy.pressure(used).value,
                }
            )
        else:
            payload.update(
                {"estimated_bytes": None, "storage_utilization": None, "storage_pressure": "unknown"}
            )
        return payload


class TursoProjectionCheckpointStore:
    def __init__(self, db: TursoDatabase) -> None:
        self.db = db

    def save(
        self,
        projection_name: str,
        *,
        last_event_id: UUID | None,
        event_count: int,
        state: dict[str, Any],
    ) -> None:
        self.db.execute(
            """
            INSERT INTO projection_checkpoints(
                projection_name,last_event_id,event_count,state,updated_at
            ) VALUES (?,?,?,?,?)
            ON CONFLICT(projection_name) DO UPDATE SET
                last_event_id=excluded.last_event_id,
                event_count=excluded.event_count,
                state=excluded.state,
                updated_at=excluded.updated_at
            """,
            (
                projection_name,
                str(last_event_id) if last_event_id else None,
                event_count,
                _json_dumps(state),
                _iso(datetime.now(timezone.utc)),
            ),
        )
        self.db.commit()

    def get(self, projection_name: str) -> dict[str, Any] | None:
        row = self.db.fetchone(
            "SELECT projection_name,last_event_id,event_count,state,updated_at "
            "FROM projection_checkpoints WHERE projection_name=?",
            (projection_name,),
        )
        if not row:
            return None
        return {
            "projection_name": row["projection_name"],
            "last_event_id": _uuid(row.get("last_event_id")),
            "event_count": int(row["event_count"]),
            "state": dict(_json_loads(row.get("state"), {})),
            "updated_at": _dt(row["updated_at"]),
        }


class TursoTelemetryStore:
    """Bounded, explicitly non-canonical telemetry separated from BrainEvent."""

    def __init__(self, db: TursoDatabase, *, storage_policy: StoragePolicy | None = None) -> None:
        self.db = db
        self.storage_policy = storage_policy or StoragePolicy()

    def append(
        self,
        telemetry_type: str,
        payload: dict[str, Any],
        *,
        occurred_at: datetime,
        expires_at: datetime,
    ) -> bool:
        used = self.db.estimated_size_bytes()
        if used is not None and not self.storage_policy.optional_writes_allowed(used):
            return False
        self.db.execute(
            "INSERT OR IGNORE INTO brain_telemetry(id,telemetry_type,payload,occurred_at,expires_at) "
            "VALUES (?,?,?,?,?)",
            (str(uuid4()), telemetry_type, _json_dumps(payload), _iso(occurred_at), _iso(expires_at)),
        )
        self.db.commit()
        return True

    def prune_expired(self, now: datetime) -> int:
        with self.db._lock:
            cur = self.db.connection.execute(
                "DELETE FROM brain_telemetry WHERE expires_at < ?", (_iso(now),)
            )
            self.db.connection.commit()
            return int(cur.rowcount or 0)
