"""Brain worker — Temporal activities for cognition tick, maintenance, connector ingest."""
from __future__ import annotations

import asyncio
import os
import time
from datetime import timedelta
from math import isfinite
from typing import Any

import psycopg

from brain.logging_config import get_logger

log = get_logger("worker")


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
_cognition_lease: Any | None = None
#: Whether a database was configured, and so whether writing requires the
#: lease. Kept apart from _cognition_lease because "no lease" has two
#: opposite meanings: nobody to race (write freely) and lost the lock (do not
#: write at all). Conflating them is how a lease fails open.
_lease_required: bool = False


def worker_database_url() -> str:
    """Return the worker DSN after validating the tenant-RLS role topology."""
    global _verified_worker_dsn
    if _verified_worker_dsn is not None:
        return _verified_worker_dsn

    dedicated_dsn = os.environ.get("BRAIN_WORKER_DATABASE_URL")
    dsn = dedicated_dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or BRAIN_WORKER_DATABASE_URL is required")

    if _HAS_TENANT:
        with psycopg.connect(dsn, autocommit=True) as conn:
            if tenant_rls_enforced(conn):
                if not dedicated_dsn:
                    raise RuntimeError(
                        "BRAIN_WORKER_DATABASE_URL is required when tenant RLS is enforced"
                    )
                require_safe_runtime_role(conn, require_trusted_service=True)

    _verified_worker_dsn = dsn
    return dsn


def build_brain_store() -> Any | None:
    """Return the durable Brain store, or None when no database is configured.

    The continuous cognition loop used to run entirely on InMemoryBrainStore
    regardless of DATABASE_URL, so every belief, prediction and cycle result the
    worker produced was invisible to the API and discarded on restart -- while
    `worker_database_url()`, and the tenant-RLS role topology it enforces, ran
    only under BRAIN_WORKER_MODE=verify.
    """

    if not (os.environ.get("BRAIN_WORKER_DATABASE_URL") or os.environ.get("DATABASE_URL")):
        return None

    # Validates the role topology before opening the pool, and fails closed if
    # tenant RLS is enforced without a dedicated trusted-service login.
    dsn = worker_database_url()

    from brain.adapters.brain_store import PostgresBrainStore

    store = PostgresBrainStore(dsn)
    log.info(
        "worker cognition bound to durable store",
        extra={"beliefs": len(store.beliefs), "persistence": "postgres"},
    )
    return store


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
        log.exception("learning service unavailable; continuing without attribution")
        return None


def build_runner(*, enable_endogenous: bool = True, event_store: Any | None = None) -> Any:
    from brain.heartbeat import build_default_heartbeat

    store = event_store if event_store is not None else build_brain_store()
    if store is None:
        log.warning(
            "no DATABASE_URL or BRAIN_WORKER_DATABASE_URL configured; "
            "worker cognition is in-memory and will be lost on restart"
        )

    hb = build_default_heartbeat(with_learning=True, event_store=store)

    if store is not None:
        # Resume from the durable projection before seeding. bootstrap_mind()
        # only seeds foundational beliefs into the cycle's cache; without this a
        # restarted worker would re-seed over a database that already holds the
        # tenant's beliefs and would not see anything it wrote previously.
        for belief in getattr(store, "beliefs", {}).values():
            hb._cycle.register_belief(belief)
        log.info(
            "worker resumed durable beliefs",
            extra={"beliefs": len(getattr(store, "beliefs", {}))},
        )

    hb.bootstrap_mind()
    runner = hb._runner
    runner.enable_endogenous = enable_endogenous
    return runner


def build_revenue_spine() -> Any:
    """Build a RevenueExecutionSpine, Postgres-backed when DATABASE_URL is
    set. Never raises — ingestion should still run in-memory if the DB
    isn't reachable at boot; this only degrades persistence, not ingest."""
    from brain.money_spine import MoneySpineService, RevenueExecutionSpine

    dsn = os.environ.get("BRAIN_WORKER_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if dsn:
        try:
            from brain.adapters.revenue_store import PostgresRevenueStore

            store = PostgresRevenueStore(dsn)
            money = MoneySpineService(store=store)
            return RevenueExecutionSpine(money=money, store=store)
        except Exception:
            pass
    return RevenueExecutionSpine()


def build_ingest_service(
    *, inbox: Any | None = None, event_store: Any | None = None, revenue: Any | None = None
) -> Any:
    from brain.connectors.http_json import HttpJsonConnector
    from brain.connectors.rss import RssConnector
    from brain.connectors.service import IngestService
    from brain.memory import InMemoryBrainStore
    from brain.sensory_inbox import InMemorySensoryInbox

    svc = IngestService(
        inbox=inbox or InMemorySensoryInbox(),
        event_store=event_store or InMemoryBrainStore(),
        connectors=[RssConnector(), HttpJsonConnector()],
        revenue=revenue if revenue is not None else build_revenue_spine(),
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
                log.exception("RSS source could not be registered", extra={"source_key": key})
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
        # Share the runner's store so attribution is written where cognition
        # is written, instead of into a second, unrelated in-memory store.
        runner = _runner_singleton()
        _learning = build_learning(getattr(runner.cycle, "event_store", None))
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


def _lease_still_held() -> bool:
    """Whether this process may still write cognition.

    True only for a worker with no database at all -- it shares nothing and so
    needs nobody's permission. Otherwise re-asks the lease, which
    revalidates its connection on its own interval and re-acquires when the
    lock has been lost.
    """

    lease = _cognition_lease
    if lease is None:
        # Only a deployment with no database may write unowned. A configured
        # one that has no lease has lost it, or never got it, and must not
        # write until it does -- but "until it does" has to be reachable.
        # Failing closed without ever retrying leaves the worker asleep
        # forever after a transient outage, which is its own kind of silent
        # Brain: correct, permissionless, and permanently idle.
        if not _lease_required:
            return True
        return _reacquire_cognition_lease()
    try:
        return bool(lease.acquire())
    except Exception:
        log.exception("cognition lease could not be revalidated")
        return False


def _reacquire_cognition_lease() -> bool:
    """Try once, without blocking, to take a lease this process has lost.

    Non-blocking on purpose: this runs from inside the cognition loop, which
    already paces its own retries. Blocking here would hold the loop in a
    call that cannot be paced or logged.
    """

    global _cognition_lease

    dsn = os.environ.get("BRAIN_WORKER_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        return False

    from brain.cognition_lease import CognitionLease

    lease = CognitionLease(dsn)
    try:
        if not lease.acquire():
            return False
    except Exception:
        log.exception("cognition lease could not be re-acquired")
        return False

    # Losing the lease means somebody else has been writing. This runner and
    # its store still hold the projection from before that handover, so
    # handing the lock straight back to it would resume cognition from beliefs
    # that are now several versions stale -- and persist conflicting ones over
    # the writer that actually held the lease in the meantime. Getting the
    # lock back is not the same as being current, and only one of those is
    # permission to write.
    try:
        _resume_worker_state()
    except Exception:
        log.exception("durable state could not be reloaded after re-acquiring the lease")
        try:
            lease.release()
        except Exception:
            log.exception("cognition lease could not be released after a failed resume")
        return False

    log.info("cognition lease re-acquired; resuming cognition")
    _cognition_lease = lease
    return True


def _resume_worker_state() -> None:
    """Reload the durable projection into the runner that is about to write.

    The mirror of apps/api/main._resume_durable_beliefs(), and of what
    build_runner() already does once at construction. Forced rather than
    TTL-bounded: a handover is exactly the case where the cached copy is both
    recent and wrong.
    """

    runner = _runner
    if runner is None:
        # Nothing has been built yet, and build_runner() resumes on
        # construction, so there is no stale cache to correct.
        return
    cycle = getattr(runner, "cycle", None)
    register = getattr(cycle, "register_belief", None)
    store = getattr(cycle, "event_store", None)
    if register is None or store is None:
        return
    refresh = getattr(store, "refresh_if_stale", None)
    if refresh is not None:
        refresh(0.0)
    beliefs = getattr(store, "beliefs", {}) or {}
    for belief in list(beliefs.values()):
        try:
            register(belief)
        except Exception:
            log.exception(
                "durable belief could not be resumed",
                extra={"belief_id": str(getattr(belief, "id", ""))},
            )
    log.info(
        "worker reloaded durable beliefs after a lease handover",
        extra={"beliefs": len(beliefs)},
    )


def _tick_sleep_seconds(default: float = 1.0) -> float:
    """A finite, non-negative pause between cognition cycles.

    The twin of apps/api/inline_cognition._float_env, kept here rather than
    imported because a worker must not depend on the API package. float()
    accepts "nan" and "inf" and neither survives time.sleep(): infinity raises
    OverflowError, a negative raises ValueError, and NaN compares false
    against everything so pacing degrades to a hot loop. This used to be
    unreachable in practice -- the loop only slept when the inbox was empty
    *and* the mind produced nothing, which it almost never is. Pacing
    endogenous cycles put that sleep on nearly every pass, which turns a
    typo in one environment variable into a worker that dies on its first
    idle tick.
    """

    raw = (os.environ.get("BRAIN_TICK_SLEEP") or "").strip()
    if not raw:
        return default
    try:
        parsed = float(raw)
    except ValueError:
        log.warning("ignoring non-numeric BRAIN_TICK_SLEEP", extra={"value": raw})
        return default
    if not isfinite(parsed) or parsed < 0:
        log.warning("ignoring out-of-range BRAIN_TICK_SLEEP", extra={"value": raw})
        return default
    return parsed


def run_forever_with_maintenance(
    *, tick_sleep: float = 1.0, ingest_every: int = 30, maintenance_every: int = 60
) -> None:
    # Before the singletons, not after. _runner_singleton() calls
    # build_runner(), which calls hb.bootstrap_mind(), which appends
    # belief.seeded events to the configured durable store. A worker that
    # cannot take the lease would therefore write a batch of cognition events
    # into the shared ledger on its way to logging that it is refusing to
    # write -- as a second writer, while another process legitimately holds
    # the lock. Construction is a write here, so it waits for permission like
    # any other.
    while not _lease_still_held():
        time.sleep(max(tick_sleep, 1.0))

    runner = _runner_singleton()
    learning = _learning_singleton()
    ingest = _ingest_singleton()
    idle_ticks = 0
    n = 0
    while True:
        n += 1
        if not _lease_still_held():
            # The lease lives in a connection, and a Postgres restart or an
            # idle-connection reaper drops it without telling this process.
            # Continuing to write on a lock we no longer hold is exactly the
            # two-writer state the lease exists to prevent, so stop thinking
            # until it is back.
            time.sleep(max(tick_sleep, 1.0))
            continue
        if ingest_every > 0 and n % ingest_every == 0 and _lease_still_held():
            try:
                ingest.ingest_due_sources()
            except Exception:
                log.exception("connector ingest cycle failed")
            # Ingest talks to external connectors and can block for a long
            # time. The check above happened before that; the lock can be
            # dropped anywhere inside it, and an API replica can take over
            # while this process is still waiting on a socket. Falling
            # straight through to run_once() would spend that window writing
            # a cognition cycle as a second writer.
            if not _lease_still_held():
                time.sleep(max(tick_sleep, 1.0))
                continue
        # An empty inbox does not make this loop idle: endogenous cognition
        # always produces a stimulus (the mind falls back to self-reflection),
        # so run_once() returns true on nearly every pass. Pacing on that
        # alone spun a core flat out, grew the event ledger without bound, and
        # reset idle_ticks forever so scheduled maintenance never ran. The
        # runner's own idle counter says which kind of cycle just happened.
        idle_before = getattr(runner, "_idle_cycles", 0)
        processed = runner.run_once()
        endogenous = getattr(runner, "_idle_cycles", 0) != idle_before
        worked = bool(processed) and not endogenous
        if worked:
            idle_ticks = 0
        else:
            idle_ticks += 1
            time.sleep(tick_sleep)
        if maintenance_every > 0 and idle_ticks >= maintenance_every and _lease_still_held():
            # Rechecked here rather than trusted from the top of the pass:
            # ingest and a cognition cycle have run in between, and the lock
            # can be dropped at any point in that window.
            try:
                if learning is not None and hasattr(learning, "expire_due_predictions"):
                    learning.expire_due_predictions()
            except Exception:
                log.exception("prediction expiry maintenance failed")
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
                        batch = await workflow.execute_activity(
                            "brain.ingest_due_sources",
                            start_to_close_timeout=timedelta(minutes=2),
                        )
                        # An activity that declined for want of the lease
                        # completed without doing anything. Counting it would
                        # report ingest runs that never ingested -- the same
                        # class of untruth this PR exists to remove.
                        if not (isinstance(batch, dict) and batch.get("skipped")):
                            ingest_runs += 1
                    except Exception:
                        # workflow.logger, not the module logger: workflow code
                        # must stay deterministic and replay-safe.
                        workflow.logger.warning("ingest activity failed", exc_info=True)
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
                    outcome = await workflow.execute_activity(
                        "brain.prediction_maintenance",
                        start_to_close_timeout=timedelta(minutes=2),
                    )
                    if not (isinstance(outcome, dict) and outcome.get("skipped")):
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

    def _tick_under_lease() -> bool:
        """One cognition cycle, reporting whether it processed a real signal.

        Two things the raw run_once() result could not say. It cannot say
        whether this process still owns the lease -- Temporal keeps its worker
        connected across a Postgres restart, so the activity pool would happily
        go on writing under a lock an API replica had already taken. And it
        cannot distinguish a processed signal from endogenous self-reflection,
        which is nearly always true, so the workflow scheduled the next
        activity immediately, never slept, and never advanced its idle counter
        -- the same hot loop the in-process worker just had fixed.
        """

        if not _lease_still_held():
            return False
        runner = _runner_singleton()
        idle_before = getattr(runner, "_idle_cycles", 0)
        processed = runner.run_once()
        endogenous = getattr(runner, "_idle_cycles", 0) != idle_before
        return bool(processed) and not endogenous

    @activity.defn(name="brain.cognition_tick")
    async def cognition_tick_activity() -> bool:
        return await asyncio.to_thread(_tick_under_lease)

    @activity.defn(name="brain.prediction_maintenance")
    async def prediction_maintenance_activity() -> dict[str, Any]:
        # A dict rather than a bare count, so the workflow can tell "ran and
        # expired nothing" from "declined for want of the lease". Returning 0
        # for both let the workflow count maintenance that never happened.
        #
        # In a thread, like the work it guards: _lease_still_held() can open a
        # PostgreSQL connection and run a query when its verification interval
        # has expired or the lock was lost. Awaiting that on the event loop
        # stalls the whole Temporal worker -- dispatch, cancellation and
        # shutdown included -- for the length of a database outage, which is
        # precisely when it will be slowest.
        if not await asyncio.to_thread(_lease_still_held):
            return {"skipped": "cognition_lease_unavailable"}
        learning = _learning_singleton()
        if learning is None or not hasattr(learning, "expire_due_predictions"):
            return {"expired": 0}
        expired = await asyncio.to_thread(learning.expire_due_predictions)
        return {"expired": len(expired or [])}

    @activity.defn(name="brain.ingest_due_sources")
    async def ingest_due_sources_activity() -> dict[str, Any]:
        # In a thread, for the reason given on prediction_maintenance_activity.
        if not await asyncio.to_thread(_lease_still_held):
            return {"skipped": "cognition_lease_unavailable"}
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
                # Expected on redeploy: the durable workflow is already running.
                log.info("continuous cognition workflow already running", extra={"workflow_id": workflow_id})
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


def temporal_address() -> str:
    """The Temporal endpoint this deployment was actually given, if any.

    run_temporal_worker() falls back to localhost:7233, which is never right in
    a container: nothing listens on the worker's own loopback. Treating that
    default as "configured" is what let a Temporal-mode worker crash-loop
    against itself instead of thinking.
    """
    return (
        os.environ.get("TEMPORAL_ADDRESS") or os.environ.get("TEMPORAL_HOST") or ""
    ).strip()


def acquire_cognition_lease() -> Any | None:
    """Wait until this process is the only one running cognition.

    The API drives cognition itself when no worker holds the lease, so a worker
    that started thinking without taking it would double every cycle for as
    long as both were up. Waiting is the correct behaviour rather than exiting:
    the API yields the lease periodically, so a worker deployed alongside a
    running API takes over on its own, without either being restarted.
    """

    global _cognition_lease, _lease_required

    dsn = os.environ.get("BRAIN_WORKER_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        # In-memory cognition is nobody else's business: there is no shared
        # store to double-write, and no database to hold a lock in.
        _lease_required = False
        return None

    _lease_required = True
    if _cognition_lease is not None:
        # Already ours. Asking again would open a second connection and block
        # on pg_advisory_lock forever, waiting for a lock this same process
        # holds on the first one -- which is exactly what the Temporal
        # fallback did on its way to the in-process loop.
        return _cognition_lease

    from brain.cognition_lease import CognitionLease

    lease = CognitionLease(dsn)
    log.info("waiting for the cognition lease")
    if not lease.acquire(blocking=True):
        # Fails closed. Returning None here would be indistinguishable from
        # "no database configured", and the loop would read that as permission
        # to write without owning the lock.
        log.error("cognition lease could not be acquired; refusing to write")
        return None
    log.info("cognition lease acquired; this worker is the single writer")
    # Module-level, not a local: the lease lives in its connection, and a
    # garbage-collected lease is a released lock and a second writer.
    _cognition_lease = lease
    return lease


def run_cognition_loop() -> None:
    """The durable in-process cognition loop, with env-tunable cadence."""
    acquire_cognition_lease()
    run_forever_with_maintenance(
        tick_sleep=_tick_sleep_seconds(),
        ingest_every=int(os.environ.get("BRAIN_INGEST_EVERY", "30")),
        maintenance_every=int(os.environ.get("BRAIN_MAINTENANCE_EVERY_IDLE", "60")),
    )


def main() -> None:
    mode = (os.environ.get("BRAIN_WORKER_MODE") or "cognition").lower()
    if mode == "verify":
        worker_database_url()
        print("worker database topology verification passed")
        return

    if mode in {"temporal", "worker"} or temporal_address():
        # A worker that cannot reach its orchestrator must still think. Exiting
        # here means the deployment restarts, dials an address nothing answers,
        # and exits again -- a crash loop that records no cognition at all,
        # which is indistinguishable from a healthy-but-idle Brain in the
        # cockpit. Degrading to the in-process loop keeps the system alive and
        # says so loudly.
        if not temporal_address():
            log.error(
                "temporal worker mode requested without TEMPORAL_ADDRESS; "
                "running in-process cognition instead of dialling localhost",
                extra={"mode": mode},
            )
            run_cognition_loop()
            return
        try:
            # The lease guards writes, not a code path. The Temporal activity
            # drives the same _runner_singleton() as the in-process loop, so
            # without taking it here a Temporal worker and an API replica
            # running inline cognition would both write cycles to the same
            # event store, each believing it was the only one.
            if acquire_cognition_lease() is None and _lease_required:
                log.error(
                    "refusing to start the temporal worker without the cognition lease"
                )
                return
            asyncio.run(run_temporal_worker())
            return
        except Exception:
            log.exception(
                "temporal worker could not run; falling back to in-process cognition",
                extra={"temporal_address": temporal_address()},
            )
            run_cognition_loop()
            return

    run_cognition_loop()


if __name__ == "__main__":
    main()
