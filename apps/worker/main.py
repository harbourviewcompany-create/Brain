"""Brain worker — Temporal activities for cognition tick + connector ingest."""
from __future__ import annotations
import asyncio
import os
import time
from datetime import timedelta
from typing import Any

def build_learning(event_store: Any | None = None) -> Any:
    try:
        from brain.adapters.learning_store import InMemoryLearningStore
        from brain.learning import LearningService
        from brain.memory import InMemoryBrainStore
        store = event_store or InMemoryBrainStore()
        mem = InMemoryLearningStore()
        return LearningService(store, predictions=mem, edges=mem, attributions=mem, sources=mem)
    except Exception:
        return None

def build_runner(*, enable_endogenous: bool = True) -> Any:
    from brain.cycle import CognitiveCycle
    from brain.heartbeat import build_default_heartbeat
    from brain.memory import InMemoryBrainStore
    from brain.runner import ContinuousCognitionRunner
    from brain.sensory_inbox import InMemorySensoryInbox
    hb = build_default_heartbeat(with_learning=True)
    hb.bootstrap_mind()
    runner = ContinuousCognitionRunner(
        cycle=hb.cycle, inbox=hb.inbox, cycle_runs=hb.cycle_runs,
        enable_endogenous=enable_endogenous, mind=hb.mind_runtime, learning=hb.learning,
        status_provider=lambda: hb.status(),
    )
    return runner

def build_ingest_service(*, inbox: Any | None = None, event_store: Any | None = None) -> Any:
    from brain.connectors.service import IngestService
    from brain.connectors.rss import RssConnector
    from brain.connectors.http_json import HttpJsonConnector
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
                svc.register_rss(source_key=key, url=url, refresh_seconds=int(os.environ.get("BRAIN_RSS_REFRESH", "300")))
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
        _ingest = build_ingest_service(inbox=runner.inbox, event_store=getattr(runner.cycle, "event_store", None))
    return _ingest

def run_forever_with_maintenance(*, tick_sleep: float = 1.0, ingest_every: int = 30) -> None:
    runner = _runner_singleton()
    ingest = _ingest_singleton()
    n = 0
    while True:
        n += 1
        if ingest_every > 0 and n % ingest_every == 0:
            try:
                ingest.ingest_due_sources()
            except Exception:
                pass
        if not runner.run_once():
            time.sleep(tick_sleep)

try:
    from temporalio import activity, workflow
    from temporalio.client import Client
    from temporalio.worker import Worker

    @activity.defn(name="brain.cognition_tick")
    async def cognition_tick_activity(max_items: int = 1) -> dict[str, Any]:
        runner = _runner_singleton()
        processed = 0
        for _ in range(max(1, max_items)):
            if runner.run_once():
                processed += 1
            else:
                break
        return {"processed": processed}

    @activity.defn(name="brain.prediction_maintenance")
    async def prediction_maintenance_activity() -> dict[str, Any]:
        return {"ok": True}

    @activity.defn(name="brain.ingest_due_sources")
    async def ingest_due_sources_activity() -> dict[str, Any]:
        svc = _ingest_singleton()
        batch = svc.ingest_due_sources()
        return batch.as_dict() if hasattr(batch, "as_dict") else {"ok": True}

    @workflow.defn(name="ContinuousCognitionWorkflow")
    class ContinuousCognitionWorkflow:
        @workflow.run
        async def run(self, rounds: int = 10) -> dict[str, Any]:
            total = 0
            for _ in range(max(1, rounds)):
                try:
                    await workflow.execute_activity(ingest_due_sources_activity, start_to_close_timeout=timedelta(seconds=60))
                except Exception:
                    pass
                result = await workflow.execute_activity(cognition_tick_activity, 3, start_to_close_timeout=timedelta(seconds=120))
                total += int((result or {}).get("processed") or 0)
                await workflow.sleep(1)
            return {"processed": total}

    async def run_temporal_worker() -> None:
        target = os.environ.get("TEMPORAL_HOST", "localhost:7233")
        client = await Client.connect(target)
        worker = Worker(client, task_queue=os.environ.get("BRAIN_TASK_QUEUE", "brain-cognition"),
            workflows=[ContinuousCognitionWorkflow],
            activities=[cognition_tick_activity, prediction_maintenance_activity, ingest_due_sources_activity])
        await worker.run()

except ImportError:
    cognition_tick_activity = None  # type: ignore
    prediction_maintenance_activity = None  # type: ignore
    ingest_due_sources_activity = None  # type: ignore
    ContinuousCognitionWorkflow = None  # type: ignore
    async def run_temporal_worker() -> None:
        raise RuntimeError("temporalio not installed")

def main() -> None:
    mode = (os.environ.get("BRAIN_WORKER_MODE") or "loop").lower()
    if mode in {"temporal", "worker"}:
        asyncio.run(run_temporal_worker())
    elif mode in {"ingest", "ingest_loop"}:
        run_forever_with_maintenance(
            tick_sleep=float(os.environ.get("BRAIN_TICK_SLEEP", "1")),
            ingest_every=int(os.environ.get("BRAIN_INGEST_EVERY", "30")))
    else:
        run_forever_with_maintenance()

if __name__ == "__main__":
    main()
