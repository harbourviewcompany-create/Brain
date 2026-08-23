from __future__ import annotations

import os
import time

from brain.adapters.cognition import CognitiveCycleRunStore, PostgresSensoryInbox
from brain.adapters.learning_store import (
    PostgresAttributionStore,
    PostgresEdgeStore,
    PostgresPredictionStore,
    PostgresSourceStore,
)
from brain.adapters.postgres import PostgresEventStore, ProjectionCheckpointStore
from brain.cycle import CognitiveCycle
from brain.learning import LearningService
from brain.runner import ContinuousCognitionRunner


def build_runner() -> ContinuousCognitionRunner:
    dsn = os.environ["DATABASE_URL"]
    event_store = PostgresEventStore(dsn)
    checkpoint_store = ProjectionCheckpointStore(event_store.pool)
    cycle = CognitiveCycle(event_store, checkpoint_store=checkpoint_store)
    try:
        loaded = cycle.hydrate_beliefs(from_checkpoint=True)
        print(f"hydrated {loaded} beliefs from projection checkpoint")
    except Exception as exc:  # noqa: BLE001 - pragma: no cover - startup hydration is best-effort; worker must still boot on failure
        print(f"belief hydration skipped: {exc}")
    inbox = PostgresSensoryInbox(event_store.pool)
    runs = CognitiveCycleRunStore(event_store.pool)
    return ContinuousCognitionRunner(cycle, inbox, runs)


def build_learning() -> LearningService:
    dsn = os.environ["DATABASE_URL"]
    event_store = PostgresEventStore(dsn)
    return LearningService(
        event_store,
        predictions=PostgresPredictionStore(event_store.pool),
        edges=PostgresEdgeStore(event_store.pool),
        attributions=PostgresAttributionStore(event_store.pool),
        sources=PostgresSourceStore(event_store.pool),
    )


def run_forever_with_maintenance(
    *,
    idle_sleep_seconds: float = 1.0,
    expire_every_n_idle: int = 60,
) -> None:
    runner = build_runner()
    learning = build_learning()
    idle_ticks = 0
    while True:
        worked = runner.run_once()
        if worked:
            idle_ticks = 0
            continue
        idle_ticks += 1
        if idle_ticks >= expire_every_n_idle:
            expired = learning.expire_due_predictions()
            if expired:
                print(f"expired {len(expired)} predictions")
            idle_ticks = 0
        time.sleep(idle_sleep_seconds)


def main() -> None:
    mode = os.environ.get("BRAIN_WORKER_MODE", "cognition")
    if mode == "maintenance":
        run_forever_with_maintenance()
    else:
        build_runner().run_forever()


if __name__ == "__main__":
    main()
