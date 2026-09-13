from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from brain.adapters.turso import TursoDatabase, TursoTelemetryStore
from brain.storage_policy import StoragePressure

UTC = timezone.utc


def _int_env(name: str, default: int, *, minimum: int = 1, maximum: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    value = default if not raw else int(raw)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _window_key(now: datetime) -> str:
    explicit = (os.environ.get("BRAIN_MAINTENANCE_WINDOW_KEY") or "").strip()
    if explicit:
        return explicit
    rounded = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    return rounded.strftime("%Y-%m-%dT%H:00Z")


def _ensure_run_table(db: TursoDatabase) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS brain_maintenance_runs(
            window_key TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            result TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    db.commit()


def _claim(db: TursoDatabase, window_key: str, now: datetime) -> bool:
    with db._lock:
        row = db.connection.execute(
            "SELECT status,started_at FROM brain_maintenance_runs WHERE window_key=?",
            (window_key,),
        ).fetchone()
        if row is not None:
            # A completed/failed window is immutable for idempotency. A stale
            # started window may be retried only after two hours, covering a
            # runner that died before recording completion.
            status = str(row[0])
            if status != "started":
                return False
            started = datetime.fromisoformat(str(row[1]).replace("Z", "+00:00"))
            if now - started < timedelta(hours=2):
                return False
            db.connection.execute(
                "UPDATE brain_maintenance_runs SET started_at=?,result='{}' WHERE window_key=?",
                (now.isoformat(), window_key),
            )
            db.connection.commit()
            return True
        db.connection.execute(
            "INSERT INTO brain_maintenance_runs(window_key,status,started_at,result) VALUES (?,'started',?,'{}')",
            (window_key, now.isoformat()),
        )
        db.connection.commit()
        return True


def _finish(db: TursoDatabase, window_key: str, status: str, result: dict[str, Any]) -> None:
    db.execute(
        "UPDATE brain_maintenance_runs SET status=?,completed_at=?,result=? WHERE window_key=?",
        (
            status,
            datetime.now(UTC).isoformat(),
            json.dumps(result, sort_keys=True, separators=(",", ":")),
            window_key,
        ),
    )
    db.commit()


def _archive_days(pressure: str) -> int:
    return {
        StoragePressure.NORMAL.value: 30,
        StoragePressure.COMPACT.value: 30,
        StoragePressure.AGGRESSIVE_COMPACTION.value: 7,
        StoragePressure.THROTTLE_OPTIONAL.value: 2,
        StoragePressure.REFUSE_OPTIONAL.value: 1,
    }.get(pressure, 30)


def run() -> dict[str, Any]:
    # The serverless maintenance process must never bind the legacy Railway DSN
    # or start a long-lived cognition thread.
    os.environ["BRAIN_INLINE_COGNITION"] = "0"
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("BRAIN_WORKER_DATABASE_URL", None)

    max_items = _int_env("BRAIN_MAINTENANCE_MAX_ITEMS", 10, maximum=50)
    max_events = _int_env("BRAIN_MAINTENANCE_MAX_EVENTS", 1000, maximum=5000)
    now = datetime.now(UTC)
    window_key = _window_key(now)

    db = TursoDatabase.from_env()
    _ensure_run_table(db)
    if not _claim(db, window_key, now):
        result = {"status": "already_processed", "window_key": window_key}
        print(json.dumps(result, sort_keys=True))
        return result

    try:
        from apps.api import main as api_module
        from apps.api.turso_runtime import configure_api_module

        store = configure_api_module(api_module)
        telemetry = TursoTelemetryStore(db, storage_policy=store.event_store.storage_policy)

        before = store.storage_health()
        pruned = telemetry.prune_expired(now)
        tick = api_module.heartbeat.tick(max_items=max_items)

        pressure = str(before.get("storage_pressure") or "unknown")
        cutoff = now - timedelta(days=_archive_days(pressure))
        compaction = store.event_store.compact_before(cutoff, max_events=max_events)

        latest = db.fetchone(
            "SELECT id,occurred_at FROM brain_event_ids ORDER BY occurred_at DESC,id DESC LIMIT 1"
        )
        after = store.storage_health()
        store.checkpoint_store.save(
            "zero_cost_maintenance",
            last_event_id=UUID(str(latest["id"])) if latest else None,
            event_count=int(after.get("canonical_event_count") or 0),
            state={
                "window_key": window_key,
                "telemetry_pruned": pruned,
                "compaction": compaction,
                "storage": after,
            },
        )

        estimated = after.get("estimated_bytes")
        budget = int(after.get("budget_bytes") or 0)
        if estimated is not None and budget and int(estimated) > budget:
            raise RuntimeError(
                f"zero-cost logical storage budget exceeded: {estimated} > {budget}"
            )

        result = {
            "status": "completed",
            "window_key": window_key,
            "bounded": {"max_items": max_items, "max_events": max_events},
            "tick": tick,
            "telemetry_pruned": pruned,
            "compaction": compaction,
            "storage_before": before,
            "storage_after": after,
        }
        _finish(db, window_key, "completed", result)
        report_path = (os.environ.get("BRAIN_MAINTENANCE_REPORT") or "").strip()
        if report_path:
            Path(report_path).write_text(
                json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(result, sort_keys=True, default=str))
        return result
    except Exception as exc:
        failure = {"status": "failed", "window_key": window_key, "error": type(exc).__name__}
        _finish(db, window_key, "failed", failure)
        raise


if __name__ == "__main__":
    run()
