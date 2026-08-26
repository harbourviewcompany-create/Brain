from __future__ import annotations

import asyncio
import os
import time
from datetime import timedelta

import psycopg
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker

from brain.tenant_runtime import require_safe_runtime_role, tenant_rls_enforced


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


_verified_worker_dsn: str | None = None


def worker_database_url() -> str:
    """Return the worker DSN after validating the tenant-RLS role topology.

    Before tenant RLS is installed, the historical DATABASE_URL remains a valid
    compatibility path. Once forced RLS is active, the worker must use a
    dedicated constrained login that is a member of the audited PostgreSQL
    ``brain_trusted_service_role``; the ordinary API runtime login is rejected.
    """
    global _verified_worker_dsn
    if _verified_worker_dsn is not None:
        return _verified_worker_dsn

    dedicated_dsn = os.environ.get("BRAIN_WORKER_DATABASE_URL")
    dsn = dedicated_dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or BRAIN_WORKER_DATABASE_URL is required")

    with psycopg.connect(dsn, autocommit=True) as conn:
        if tenant_rls_enforced(conn):
            if not dedicated_dsn:
                raise RuntimeError(
                    "BRAIN_WORKER_DATABASE_URL is required when tenant RLS is enforced"
                )
            require_safe_runtime_role(conn, require_trusted_service=True)

    _verified_worker_dsn = dsn
    return dsn


def build_learning():
    from brain.adapters.learning_store import (
        PostgresAttributionStore,
        PostgresEdgeStore,
        PostgresPredictionStore,
        PostgresSourceStore,
    )
    from brain.adapters.postgres import PostgresEventStore
    from brain.learning import LearningService

    dsn = worker_database_url()
    event_store = PostgresEventStore(dsn)
    return LearningService(
        event_store,
        predictions=PostgresPredictionStore(event_store.pool),
        edges=PostgresEdgeStore(event_store.pool),
        attributions=PostgresAttributionStore(event_store.pool),
        sources=PostgresSourceStore(event_store.pool),
    )


def build_runner():
    from brain.adapters.cognition import CognitiveCycleRunStore, PostgresSensoryInbox
    from brain.adapters.postgres import PostgresEventStore, ProjectionCheckpointStore
    from brain.cycle import CognitiveCycle
    from brain.runner import ContinuousCognitionRunner

    dsn = worker_database_url()
    event_store = PostgresEventStore(dsn)
    checkpoint_store = ProjectionCheckpointStore(event_store.pool)
    learning = None
    try:
        learning = build_learning()
    except Exception as exc:  # noqa: BLE001 - learning optional at boot
        print(f"learning service unavailable: {exc}")
    cycle = CognitiveCycle(
        event_store, checkpoint_store=checkpoint_store, learning=learning
    )
    try:
        loaded = cycle.hydrate_beliefs(from_checkpoint=True)
        print(f"hydrated {loaded} beliefs from projection checkpoint")
    except Exception as exc:  # noqa: BLE001 - startup hydration is recoverable
        print(f"belief hydration skipped: {exc}")
    inbox = PostgresSensoryInbox(event_store.pool)
    runs = CognitiveCycleRunStore(event_store.pool)
    return ContinuousCognitionRunner(cycle, inbox, runs)


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
    if mode == "verify":
        worker_database_url()
        print("worker database topology verification passed")
        return
    if mode == "temporal" or os.environ.get("TEMPORAL_ADDRESS"):
        asyncio.run(run_temporal_worker())
    elif mode == "maintenance":
        run_forever_with_maintenance()
    else:
        build_runner().run_forever()


if __name__ == "__main__":
    main()
