from __future__ import annotations

import asyncio
import os
import time

from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker

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
from brain.orchestration import ContinuousCognitionWorkflow
from brain.runner import ContinuousCognitionRunner


def build_runner() -> ContinuousCognitionRunner:
    dsn = os.environ["DATABASE_URL"]
    event_store = PostgresEventStore(dsn)
    checkpoint_store = ProjectionCheckpointStore(event_store.pool)
    cycle = CognitiveCycle(event_store, checkpoint_store=checkpoint_store)
    try:
        loaded = cycle.hydrate_beliefs(from_checkpoint=True)
        print(f"hydrated {loaded} beliefs from projection checkpoint")
    except Exception as exc:  # noqa: BLE001 - startup hydration is recoverable
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


_runner: ContinuousCognitionRunner | None = None
_learning: LearningService | None = None


def _runner_singleton() -> ContinuousCognitionRunner:
    global _runner
    if _runner is None:
        _runner = build_runner()
    return _runner


def _learning_singleton() -> LearningService:
    global _learning
    if _learning is None:
        _learning = build_learning()
    return _learning


@activity.defn(name="brain.cognition_tick")
async def cognition_tick_activity() -> bool:
    return await asyncio.to_thread(_runner_singleton().run_once)


@activity.defn(name="brain.prediction_maintenance")
async def prediction_maintenance_activity() -> int:
    expired = await asyncio.to_thread(_learning_singleton().expire_due_predictions)
    return len(expired)


async def run_temporal_worker() -> None:
    address = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    task_queue = os.environ.get("BRAIN_TEMPORAL_TASK_QUEUE", "brain-cognition")
    workflow_id = os.environ.get("BRAIN_TEMPORAL_WORKFLOW_ID", "brain-continuous-cognition")
    client = await Client.connect(address, namespace=namespace)
    if os.environ.get("BRAIN_TEMPORAL_AUTOSTART", "true").lower() == "true":
        try:
            await client.start_workflow(
                ContinuousCognitionWorkflow.run,
                float(os.environ.get("BRAIN_IDLE_SLEEP_SECONDS", "1.0")),
                int(os.environ.get("BRAIN_MAINTENANCE_EVERY_IDLE", "60")),
                int(os.environ.get("BRAIN_WORKFLOW_MAX_ITERATIONS", "1000")),
                id=workflow_id,
                task_queue=task_queue,
            )
        except WorkflowAlreadyStartedError:
            pass
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[ContinuousCognitionWorkflow],
        activities=[cognition_tick_activity, prediction_maintenance_activity],
    )
    await worker.run()


def main() -> None:
    mode = os.environ.get("BRAIN_WORKER_MODE", "cognition")
    if mode == "temporal" or os.environ.get("TEMPORAL_ADDRESS"):
        asyncio.run(run_temporal_worker())
    elif mode == "maintenance":
        run_forever_with_maintenance()
    else:
        build_runner().run_forever()


if __name__ == "__main__":
    main()
