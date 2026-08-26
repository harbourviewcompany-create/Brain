from __future__ import annotations

import asyncio
import os
import time
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker


@workflow.defn
class ContinuousCognitionWorkflow:
    """Durable cognition heartbeat with replay-safe timers and bounded history."""

    @workflow.run
    async def run(
        self,
        idle_seconds: float = 1.0,
        maintenance_every: int = 60,
        max_iterations: int = 1000,
        remaining_runs: int = -1,
    ) -> dict[str, int]:
        idle_ticks = 0
        maintenance_runs = 0
        for _ in range(max_iterations):
            worked = await workflow.execute_activity(
                "brain.cognition_tick",
                start_to_close_timeout=timedelta(minutes=2),
            )
            if worked:
                idle_ticks = 0
            else:
                idle_ticks += 1
                await workflow.sleep(idle_seconds)
            if idle_ticks >= maintenance_every:
                await workflow.execute_activity(
                    "brain.prediction_maintenance",
                    start_to_close_timeout=timedelta(minutes=2),
                )
                maintenance_runs += 1
                idle_ticks = 0

        if remaining_runs == 1:
            return {"iterations": max_iterations, "maintenance_runs": maintenance_runs}
        next_runs = remaining_runs - 1 if remaining_runs > 1 else -1
        workflow.continue_as_new(
            args=[idle_seconds, maintenance_every, max_iterations, next_runs]
        )
        raise RuntimeError("continue_as_new_returned_unexpectedly")


def build_learning():
    from brain.adapters.learning_store import (
        PostgresAttributionStore,
        PostgresEdgeStore,
        PostgresPredictionStore,
        PostgresSourceStore,
    )
    from brain.adapters.postgres import PostgresEventStore
    from brain.learning import LearningService

    dsn = os.environ["DATABASE_URL"]
    event_store = PostgresEventStore(dsn)
    return LearningService(
        event_store,
        predictions=PostgresPredictionStore(event_store.pool),
        edges=PostgresEdgeStore(event_store.pool),
        attributions=PostgresAttributionStore(event_store.pool),
        sources=PostgresSourceStore(event_store.pool),
    )


def build_runner():
    from brain.adapters.learning_store import (
        PostgresAttributionStore,
        PostgresEdgeStore,
        PostgresPredictionStore,
        PostgresSourceStore,
    )
    from brain.adapters.postgres import PostgresEventStore
    from brain.domain import Evidence, Node
    from brain.learning import LearningService
    from brain.runner import ContinuousCognitionRunner
    from brain.runtime import InMemoryBrainStore

    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        from brain.adapters.brain_store import PostgresBrainStore

        store = PostgresBrainStore(dsn)
        event_store = store.event_store
        learning = LearningService(
            event_store,
            predictions=PostgresPredictionStore(event_store.pool),
            edges=PostgresEdgeStore(event_store.pool),
            attributions=PostgresAttributionStore(event_store.pool),
            sources=PostgresSourceStore(event_store.pool),
        )
    else:
        store = InMemoryBrainStore()
        from brain.ports import InMemoryEventStore

        event_store = InMemoryEventStore()
        learning = LearningService(event_store)

    def sensor():
        from uuid import uuid4

        evidence = Evidence(
            id=uuid4(),
            kind="heartbeat",
            content={"source": "worker", "ts": time.time()},
        )
        node = Node(kind="signal", key=f"heartbeat:{evidence.id}", properties={})
        return evidence, node

    return ContinuousCognitionRunner(store=store, learning=learning, sensor=sensor)


def run_forever_with_maintenance() -> None:
    learning = build_learning()
    while True:
        expired = learning.expire_due_predictions()
        time.sleep(float(os.environ.get("BRAIN_IDLE_SLEEP_SECONDS", "1.0")))
        if expired:
            print(f"expired_predictions={len(expired)}")


_runner = None
_learning = None


def _runner_singleton():
    global _runner
    if _runner is None:
        _runner = build_runner()
    return _runner


def _learning_singleton():
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
    connect_kwargs: dict = {"namespace": namespace}
    api_key = os.environ.get("TEMPORAL_API_KEY", "").strip()
    if api_key:
        # Temporal Cloud: TLS + API key authentication
        connect_kwargs["api_key"] = api_key
        connect_kwargs["tls"] = True
    client = await Client.connect(address, **connect_kwargs)
    if os.environ.get("BRAIN_TEMPORAL_AUTOSTART", "true").lower() == "true":
        try:
            await client.start_workflow(
                ContinuousCognitionWorkflow.run,
                args=[
                    float(os.environ.get("BRAIN_IDLE_SLEEP_SECONDS", "1.0")),
                    int(os.environ.get("BRAIN_MAINTENANCE_EVERY_IDLE", "60")),
                    int(os.environ.get("BRAIN_WORKFLOW_MAX_ITERATIONS", "1000")),
                    -1,
                ],
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
