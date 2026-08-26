"""Brain worker — Temporal activities for cognition tick, maintenance, connector ingest."""
from __future__ import annotations

import asyncio
import os
import time
from datetime import timedelta
from typing import Any


try:
    from temporalio import activity, workflow
    from temporalio.client import Client
    from temporalio.exceptions import WorkflowAlreadyStartedError
    from temporalio.worker import Worker

    _HAS_TEMPORAL = True
except ImportError:
    _HAS_TEMPORAL = False

try:
    from brain.tenant_runtime import require_safe_runtime_role, tenant_rls_enforced

    _HAS_TENANT = True
except ImportError:
    _HAS_TENANT = False


_verified_worker_dsn: str | None = None


def worker_database_url() -> str:
    """Validate worker DSN topology; require dedicated trusted-service login under RLS."""
    global _verified_worker_dsn
    if _verified_worker_dsn is not None:
        return _verified_worker_dsn

    dedicated_dsn = os.environ.get("BRAIN_WORKER_DATABASE_URL")
    dsn = dedicated_dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or BRAIN_WORKER_DATABASE_URL is required")

    if _HAS_TENANT:
        import psycopg

        with psycopg.connect(dsn, autocommit=True) as conn:
            if tenant_rls_enforced(conn):
                if not dedicated_dsn:
                    raise RuntimeError(
                        "BRAIN_WORKER_DATABASE_URL is required when tenant RLS is enforced"
                    )
                require_safe_runtime_role(conn, require_trusted_service=True)

    _verified_worker_dsn = dsn
    return dsn


def build_learning(event_store: Any | None = None) -> Any:
    try:
        from brain.adapters.learning_store import InMemoryLearningStore
        from brain.learning import LearningService
        from brain.memory import InMemoryBrainStore

        store = event_store or InMemoryBrainStore()
        mem = InMemoryLearningStore()
        return LearningService(
            store, predictions=mem, edges=mem, attributions=mem, sources=mem
        )
    except Exception:
        return None


def build_runner(*, enable_endogenous: bool = True) -> Any:
    from brain.heartbeat import build_default_heartbeat

    hb = build_default_heartbeat(with_learning=True)
    hb.bootstrap_mind()
    runner = hb._runner
    runner.enable_endogenous = enable_endogenous
    return runner


def build_ingest_service(*, inbox: Any | None = None, event_store: Any | None = None) -> Any:
    from brain.connectors.http_json import HttpJsonConnector
    from brain.connectors.rss import RssConnector
    from brain.connectors.service import IngestService
    from brain.memory import InMemoryBrainStore
    from brain.sensory_inbox import InMemorySensoryInbox

    svc = IngestService(
        inbox=inbox or InMemorySensoryInbox(),
        event_store=event_store or InMemoryBrainStore(),
        connectors=[RssConnector(), HttpJsonConnector()],
    )
    raw = os.environ.get("BRAIN_RSS_SOURCES") or ""
    for part in raw.split(","):
        part = part.strip()
        if not part or "|" not in part:
            continue
        key, url = part.split("|", 1)
        key, url = key.strip(), url.strip()
        if key and url:
            try:
                svc.register_rss(
                    source_key=key,
                    url=url,
                    refresh_seconds=int(os.environ.get("BRAIN_RSS_REFRESH", "300")),
                )
            except Exception:
                pass
    return svc


_runner = None
_learning = None
_ingest = None


def _runner_singleton() -> Any:
    global _runner
    if _runner is None:
        _runner = build_runner(enable_endogenous=True)
    return _runner


def _learning_singleton() -> Any:
    global _learning
    if _learning is None:
        _learning = build_learning()
    return _learning


def _ingest_singleton() -> Any:
    global _ingest
    if _ingest is None:
        runner = _runner_singleton()
        _ingest = build_ingest_service(
            inbox=runner.inbox,
            event_store=getattr(runner.cycle, "event_store", None),
        )
    return _ingest


def run_forever_with_maintenance(
    *, tick_sleep: float = 1.0, ingest_every: int = 30, maintenance_every: int = 60
) -> None:
    runner = _runner_singleton()
    learning = _learning_singleton()
    ingest = _ingest_singleton()
    idle_ticks = 0
    n = 0
    while True:
        n += 1
        if ingest_every > 0 and n % ingest_every == 0:
            try:
                ingest.ingest_due_sources()
            except Exception:
                pass
        worked = runner.run_once()
        if worked:
            idle_ticks = 0
        else:
            idle_ticks += 1
            time.sleep(tick_sleep)
        if maintenance_every > 0 and idle_ticks >= maintenance_every:
            try:
                if learning is not None and hasattr(learning, "expire_due_predictions"):
                    learning.expire_due_predictions()
            except Exception:
                pass
            idle_ticks = 0


if _HAS_TEMPORAL:

    @workflow.defn
    class ContinuousCognitionWorkflow:
        @workflow.run
        async def run(
            self,
            idle_seconds: float = 1.0,
            maintenance_every: int = 60,
            max_iterations: int = 1000,
            remaining_runs: int = -1,
            ingest_every: int = 30,
        ) -> dict[str, int]:
            idle_ticks = 0
            maintenance_runs = 0
            ingest_runs = 0
            for i in range(max_iterations):
                if ingest_every > 0 and i > 0 and i % ingest_every == 0:
                    try:
                        await workflow.execute_activity(
                            "brain.ingest_due_sources",
                            start_to_close_timeout=timedelta(minutes=2),
                        )
                        ingest_runs += 1
                    except Exception:
                        pass
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
                return {
                    "iterations": max_iterations,
                    "maintenance_runs": maintenance_runs,
                    "ingest_runs": ingest_runs,
                }
            next_runs = remaining_runs - 1 if remaining_runs > 1 else -1
            workflow.continue_as_new(
                args=[idle_seconds, maintenance_every, max_iterations, next_runs, ingest_every]
            )
            raise RuntimeError("continue_as_new_returned_unexpectedly")

    @activity.defn(name="brain.cognition_tick")
    async def cognition_tick_activity() -> bool:
        return await asyncio.to_thread(_runner_singleton().run_once)

    @activity.defn(name="brain.prediction_maintenance")
    async def prediction_maintenance_activity() -> int:
        learning = _learning_singleton()
        if learning is None or not hasattr(learning, "expire_due_predictions"):
            return 0
        expired = await asyncio.to_thread(learning.expire_due_predictions)
        return len(expired or [])

    @activity.defn(name="brain.ingest_due_sources")
    async def ingest_due_sources_activity() -> dict[str, Any]:
        svc = _ingest_singleton()
        batch = await asyncio.to_thread(svc.ingest_due_sources)
        return batch.as_dict() if hasattr(batch, "as_dict") else {"ok": True}

    async def run_temporal_worker() -> None:
        address = os.environ.get("TEMPORAL_ADDRESS") or os.environ.get(
            "TEMPORAL_HOST", "localhost:7233"
        )
        namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
        task_queue = os.environ.get(
            "BRAIN_TEMPORAL_TASK_QUEUE",
            os.environ.get("BRAIN_TASK_QUEUE", "brain-cognition"),
        )
        workflow_id = os.environ.get(
            "BRAIN_TEMPORAL_WORKFLOW_ID", "brain-continuous-cognition"
        )
        api_key = os.environ.get("TEMPORAL_API_KEY")
        if api_key:
            client = await Client.connect(
                address,
                namespace=namespace,
                api_key=api_key,
                tls=True,
            )
        else:
            client = await Client.connect(address, namespace=namespace)
        if os.environ.get("BRAIN_TEMPORAL_AUTOSTART", "true").lower() == "true":
            try:
                await client.start_workflow(
                    ContinuousCognitionWorkflow.run,
                    args=[
                        float(os.environ.get("BRAIN_IDLE_SLEEP_SECONDS", "1.0")),
                        int(os.environ.get("BRAIN_MAINTENANCE_EVERY_IDLE", "60")),
                        int(os.environ.get("BRAIN_WORKFLOW_MAX_ITERATIONS", "1000")),
                        -1,
                        int(os.environ.get("BRAIN_INGEST_EVERY", "30")),
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
            activities=[
                cognition_tick_activity,
                prediction_maintenance_activity,
                ingest_due_sources_activity,
            ],
        )
        await worker.run()

else:

    async def run_temporal_worker() -> None:
        raise RuntimeError("temporalio not installed")


def main() -> None:
    mode = (os.environ.get("BRAIN_WORKER_MODE") or "cognition").lower()
    if mode == "verify":
        worker_database_url()
        print("worker database topology verification passed")
        return
    if mode in {"temporal", "worker"} or os.environ.get("TEMPORAL_ADDRESS"):
        asyncio.run(run_temporal_worker())
    elif mode in {"maintenance", "ingest", "ingest_loop"}:
        run_forever_with_maintenance(
            tick_sleep=float(os.environ.get("BRAIN_TICK_SLEEP", "1")),
            ingest_every=int(os.environ.get("BRAIN_INGEST_EVERY", "30")),
            maintenance_every=int(os.environ.get("BRAIN_MAINTENANCE_EVERY_IDLE", "60")),
        )
    else:
        run_forever_with_maintenance()


if __name__ == "__main__":
    main()
