"""What has to hold once the API process itself writes cognition.

The inline loop turned a read-only process into a writer. Everything here is
a way that could go wrong quietly -- cycles counted against a lattice that
never grows, two writers inside one process, a projection blanked by a
transient outage, a lease held by a thread that has stopped thinking.
"""

from __future__ import annotations

import threading
import time
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import apps.api.inline_cognition as inline
import apps.api.main as api
import apps.worker.main as worker
from brain.adapters.brain_store import PostgresBrainStore


# --- the inline heartbeat must be able to persist a belief ----------------


def test_the_configured_heartbeat_can_write_the_belief_projection():
    """The defect this whole round exists for.

    PostgresEventStore appends to the ledger but has no save(), and
    CognitiveCycle._persist_belief() looks for exactly that method before
    writing. A heartbeat bound to the event store therefore emitted
    belief.created events forever while the beliefs table -- the one the
    cockpit reads -- never changed. CYCLE would climb over a lattice that
    stays permanently UNFORMED.
    """

    import inspect

    source = inspect.getsource(api._configure_from_env)
    assert "HeartbeatService(event_store=store," in source
    assert "event_store=store.event_store" not in source


def test_the_event_store_alone_cannot_persist_beliefs():
    """Pins why the line above matters, rather than trusting the comment."""

    from brain.adapters.postgres import PostgresEventStore

    assert not hasattr(PostgresEventStore, "save")
    assert hasattr(PostgresBrainStore, "save")


def test_the_default_heartbeat_is_bound_to_the_projection_store():
    assert api.heartbeat.event_store is api._brain_store
    assert hasattr(api.heartbeat.event_store, "save")


# --- resuming what the Brain already believes ------------------------------


class _Belief:
    def __init__(self, ident):
        self.id = ident


class _Store:
    def __init__(self, beliefs):
        self.beliefs = {b.id: b for b in beliefs}


def test_durable_beliefs_are_loaded_into_the_cycle_before_thinking(monkeypatch):
    registered = []

    class Cycle:
        def register_belief(self, belief):
            registered.append(belief.id)

    class Heartbeat:
        _cycle = Cycle()

    monkeypatch.setattr(api, "heartbeat", Heartbeat())
    monkeypatch.setattr(api, "_brain_store", _Store([_Belief("a"), _Belief("b")]))

    api._resume_durable_beliefs()

    # bootstrap_mind() seeds foundational beliefs and nothing else, so without
    # this the loop reasons as though the lattice were empty and re-derives
    # what the database already holds.
    assert sorted(registered) == ["a", "b"]


def test_resuming_beliefs_survives_one_bad_belief(monkeypatch):
    registered = []

    class Cycle:
        def register_belief(self, belief):
            if belief.id == "bad":
                raise RuntimeError("unreadable belief")
            registered.append(belief.id)

    class Heartbeat:
        _cycle = Cycle()

    monkeypatch.setattr(api, "heartbeat", Heartbeat())
    monkeypatch.setattr(
        api, "_brain_store", _Store([_Belief("good"), _Belief("bad")])
    )

    api._resume_durable_beliefs()

    assert registered == ["good"]


def test_resuming_beliefs_is_a_no_op_without_a_cycle(monkeypatch):
    class Heartbeat:
        pass

    monkeypatch.setattr(api, "heartbeat", Heartbeat())
    api._resume_durable_beliefs()


def test_resume_runs_only_after_the_lease_is_won():
    started = []
    lease = _FakeLease(granted=False)
    eng = inline.InlineCognition(
        tick=lambda: {},
        lease=lease,
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=0,
        on_start=lambda: started.append(1),
    )

    eng._step()
    assert started == []

    lease.granted = True
    eng._step()
    eng._step()

    # Once, and only once the process is actually the writer.
    assert started == [1]


class _FakeLease:
    def __init__(self, granted=True):
        self.granted = granted
        self.released = 0

    def acquire(self, *, blocking=False):
        return self.granted

    def release(self):
        self.released += 1


# --- one writer inside this process ---------------------------------------


def test_ticks_are_serialised_within_the_process():
    """The lease keeps two processes apart; it says nothing about this one."""

    overlaps = []
    running = threading.Event()

    def slow_tick(**kwargs):
        overlaps.append(running.is_set())
        running.set()
        time.sleep(0.02)
        running.clear()
        return {}

    original = api.heartbeat.tick
    api.heartbeat.tick = slow_tick
    try:
        threads = [
            threading.Thread(target=lambda: api.tick_once(max_items=1))
            for _ in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
    finally:
        api.heartbeat.tick = original

    # FastAPI runs sync routes in a thread pool, so POST /tick could otherwise
    # interleave with a background cycle mid-mutation of the same unguarded
    # cycle, inbox and belief cache.
    assert overlaps == [False, False, False, False]


def test_every_tick_entry_point_goes_through_the_serialised_helper():
    import inspect

    for route in (api.run_heartbeat_tick, api.enqueue_signal):
        source = inspect.getsource(route)
        assert "heartbeat.tick(" not in source, (
            f"{route.__name__} must not tick the heartbeat directly"
        )
        # request_tick, not tick_once: a request must also check the
        # cross-process lease, which the in-process lock knows nothing about.
        assert "request_tick(" in source


def test_the_inline_loop_ticks_through_the_serialised_helper():
    import inspect

    assert "tick_once(max_items=1)" in inspect.getsource(api._lifespan)


# --- configuration that must not break the loop ---------------------------


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "Infinity", "-1"])
def test_out_of_range_inline_intervals_fall_back(monkeypatch, raw):
    monkeypatch.setenv("BRAIN_TICK_SLEEP", raw)

    # Event.wait(Infinity) raises OverflowError from the tick path, and the
    # handler's own wait raises again -- so the thread dies without releasing
    # the lease and nothing can take over. NaN makes a hot retry loop.
    assert inline._float_env("BRAIN_TICK_SLEEP", 1.0) == 1.0


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf"])
def test_non_finite_read_refresh_falls_back(monkeypatch, raw):
    monkeypatch.setenv("BRAIN_READ_REFRESH_SECONDS", raw)

    # NaN fails every age comparison and hydrates on every request; Infinity
    # makes the boot snapshot fresh forever, restoring the stale-read bug the
    # TTL exists to fix.
    assert api._read_refresh_seconds() == 5.0


def test_finite_read_refresh_is_honoured(monkeypatch):
    monkeypatch.setenv("BRAIN_READ_REFRESH_SECONDS", "0.5")
    assert api._read_refresh_seconds() == 0.5


def test_a_backoff_failure_still_releases_the_lease():
    lease = _FakeLease()

    def explode():
        raise RuntimeError("cycle blew up")

    eng = inline.InlineCognition(
        tick=explode, lease=lease, tick_sleep=0, retry_seconds=0, yield_seconds=0
    )

    class HostileEvent(threading.Event):
        def wait(self, timeout=None):
            raise OverflowError("timeout too large")

    eng._stop = HostileEvent()
    eng.run()

    assert lease.released >= 1


# --- /health must stay fast when the database is gone ---------------------


class _SlowStore:
    def __init__(self):
        self.calls = []

    def database_healthy(self, *, timeout: float = 3.0):
        return False

    def refresh_if_stale(self, max_age_seconds):
        self.calls.append("refresh")
        return True

    def cognition_counters(self, max_age_seconds: float = 0.0):
        self.calls.append("counters")
        return {}


def test_health_does_not_wait_on_a_database_it_already_knows_is_down(monkeypatch):
    store = _SlowStore()
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(api, "_brain_store", store)
    monkeypatch.setattr(api, "runtime", type("R", (), {"store": store})())
    store.beliefs = {}

    response = TestClient(api.app).get("/health")

    assert response.status_code == 503
    # _database_ready() is bounded to ~3s so a dead database fails fast. Both
    # of these open pooled connections with no timeout of their own and can
    # wait out the pool's 30s default, turning a known 503 into a minute.
    assert store.calls == []


# --- counters must not flatter a stalled loop -----------------------------


class _Counting:
    def __init__(self, counts):
        self._counts = counts
        self.ttls = []

    def cognition_counters(self, max_age_seconds: float = 0.0):
        self.ttls.append(max_age_seconds)
        return dict(self._counts)


def test_queued_signals_are_never_reported_as_processed(monkeypatch):
    store = _Counting({"signal.enqueued": 9, "cycle.completed": 3})
    monkeypatch.setattr(api, "_brain_store", store)

    status = api._cognition_status()

    # signal.enqueued is emitted when a signal is queued, before cognition
    # touches it. Counting it as processed would claim work in exactly the
    # stalled-loop case this endpoint exists to expose.
    assert status["total_processed"] == 0
    assert status["signals_enqueued"] == 9


def test_counters_are_asked_for_a_cached_answer(monkeypatch):
    store = _Counting({"cycle.completed": 1})
    monkeypatch.setattr(api, "_brain_store", store)
    monkeypatch.setenv("BRAIN_READ_REFRESH_SECONDS", "5")

    api._cognition_status()

    # The count grows with the lifetime event history and the Observatory asks
    # twice per poll, every five seconds, forever.
    assert store.ttls == [5.0]


# --- the projection must survive a database that goes away ----------------


def _detached_store() -> PostgresBrainStore:
    store = object.__new__(PostgresBrainStore)
    store._refresh_lock = threading.Lock()
    store._counters_lock = threading.Lock()
    store._counters = (0.0, None)
    store._inflight_lock = threading.Lock()
    store._inflight = None
    store.beliefs = {"kept": "belief"}
    store.evidence = {}
    store.nodes = {}
    store.edges = {}
    store.rewires = []
    store._hydrated_at = None
    return store


def test_a_failed_refresh_leaves_the_last_good_projection(monkeypatch):
    store = _detached_store()
    monkeypatch.setattr(
        PostgresBrainStore,
        "_load_projection",
        lambda self: (_ for _ in ()).throw(RuntimeError("database went away")),
    )

    with pytest.raises(RuntimeError):
        store.refresh_if_stale(0)

    # Clearing first meant an outage mid-refresh left the API serving an empty
    # projection, which reads as a Brain that has forgotten everything.
    assert store.beliefs == {"kept": "belief"}


def test_a_failed_refresh_does_not_start_the_ttl(monkeypatch):
    store = _detached_store()
    monkeypatch.setattr(
        PostgresBrainStore,
        "_load_projection",
        lambda self: (_ for _ in ()).throw(RuntimeError("database went away")),
    )

    with pytest.raises(RuntimeError):
        store.refresh_if_stale(60)

    # Advancing the clock on failure would suppress every retry for a full TTL.
    assert store._hydrated_at is None


def test_a_successful_refresh_swaps_the_projection_in_one_step(monkeypatch):
    store = _detached_store()
    fresh = {"new": "belief"}
    monkeypatch.setattr(
        PostgresBrainStore,
        "_load_projection",
        lambda self: (fresh, {}, {}, {}, []),
    )
    before = store.beliefs

    assert store.refresh_if_stale(0) is True

    # Rebinding rather than mutating means a reader already iterating the old
    # dict keeps a complete snapshot instead of watching it empty out.
    assert store.beliefs == fresh
    assert before == {"kept": "belief"}
    assert store._hydrated_at is not None


def test_the_ttl_is_honoured_between_refreshes(monkeypatch):
    store = _detached_store()
    loads = []
    monkeypatch.setattr(
        PostgresBrainStore,
        "_load_projection",
        lambda self: (loads.append(1), ({}, {}, {}, {}, []))[1],
    )

    assert store.refresh_if_stale(60) is True
    assert store.refresh_if_stale(60) is False
    assert len(loads) == 1


@pytest.mark.parametrize("ttl", [float("nan"), float("inf"), -1.0])
def test_out_of_range_refresh_ttls_do_not_hydrate(monkeypatch, ttl):
    store = _detached_store()
    monkeypatch.setattr(
        PostgresBrainStore,
        "_load_projection",
        lambda self: (_ for _ in ()).throw(AssertionError("must not hydrate")),
    )

    assert store.refresh_if_stale(ttl) is False


# --- the worker must keep holding the lease it writes under ---------------


def test_the_worker_stops_writing_when_it_loses_the_lease(monkeypatch):
    class Lost:
        def acquire(self, *, blocking=False):
            return False

    monkeypatch.setattr(worker, "_cognition_lease", Lost())
    assert worker._lease_still_held() is False


def test_an_in_memory_worker_needs_no_lease(monkeypatch):
    monkeypatch.setattr(worker, "_cognition_lease", None)
    # Nothing is shared, so there is nobody to be the second writer.
    assert worker._lease_still_held() is True


def test_a_lease_that_cannot_be_checked_stops_writes(monkeypatch):
    class Broken:
        def acquire(self, *, blocking=False):
            raise RuntimeError("connection reset")

    monkeypatch.setattr(worker, "_cognition_lease", Broken())
    assert worker._lease_still_held() is False


def test_the_cognition_loop_rechecks_the_lease_every_pass():
    import inspect

    source = inspect.getsource(worker.run_forever_with_maintenance)
    # Acquired once and then never checked, the lock can be dropped by a
    # Postgres restart while this process keeps writing under it.
    assert "_lease_still_held()" in source


def test_the_temporal_path_also_takes_the_lease():
    import inspect

    source = inspect.getsource(worker.main)
    temporal = source.split("asyncio.run(run_temporal_worker())")[0]
    # The Temporal activity drives the same runner singleton as the in-process
    # loop, so skipping the lease here lets it race an API replica.
    assert "acquire_cognition_lease()" in temporal


def test_endogenous_cycles_are_paced_not_spun():
    import inspect

    source = inspect.getsource(worker.run_forever_with_maintenance)
    # The mind always has a self-reflection fallback, so run_once() returns
    # true on nearly every pass with an empty inbox. Pacing on that alone ran
    # cycles as fast as the CPU allowed and reset idle_ticks forever, so
    # scheduled maintenance never ran.
    assert "_idle_cycles" in source
    assert "endogenous" in source


# --- every projection-backed route reads fresh state ----------------------


class _RefreshTracking:
    def __init__(self):
        self.refreshes = 0
        self.beliefs = {}
        self.evidence = {}
        self.nodes = {}
        self.edges = {}
        self.rewires = []

    def database_healthy(self, *, timeout: float = 3.0):
        return True

    def refresh_if_stale(self, max_age_seconds):
        self.refreshes += 1
        return True

    def cognition_counters(self, max_age_seconds: float = 0.0):
        return {}


@pytest.mark.parametrize("path", ["/beliefs", "/contradictions", "/curiosity", "/sources"])
def test_every_projection_route_refreshes_before_answering(monkeypatch, path):
    store = _RefreshTracking()
    monkeypatch.setenv("BRAIN_API_KEY", "test-key")
    monkeypatch.setattr(api, "_brain_store", store)

    TestClient(api.app).get(path, headers={"X-Brain-Api-Key": "test-key"})

    # Wiring the refresh into three handlers left the rest serving the boot
    # snapshot indefinitely, and the cockpit polls them all in parallel.
    assert store.refreshes >= 1


def test_health_is_exempt_from_the_read_boundary(monkeypatch):
    store = _SlowStore()
    store.beliefs = {}
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(api, "_brain_store", store)
    monkeypatch.setattr(api, "runtime", type("R", (), {"store": store})())

    TestClient(api.app).get("/health")

    assert store.calls == []


def test_an_unauthenticated_request_does_not_touch_the_database(monkeypatch):
    store = _RefreshTracking()
    monkeypatch.setenv("BRAIN_API_KEY", "test-key")
    monkeypatch.setattr(api, "_brain_store", store)

    response = TestClient(api.app).get("/beliefs")

    # Authentication is the outer middleware, so a rejected request costs
    # nothing: an unauthenticated caller must not be able to make this process
    # hit PostgreSQL at all.
    assert response.status_code == 401
    assert store.refreshes == 0


def test_writes_do_not_pay_for_a_projection_refresh(monkeypatch):
    store = _RefreshTracking()
    monkeypatch.setenv("BRAIN_API_KEY", "test-key")
    monkeypatch.setattr(api, "_brain_store", store)

    TestClient(api.app).post(
        "/beliefs",
        headers={"X-Brain-Api-Key": "test-key"},
        json={"statement": "a belief", "confidence": 0.5},
    )

    assert store.refreshes == 0


def test_projection_reads_are_bounded_so_a_dead_database_fails_fast():
    assert PostgresBrainStore.READ_TIMEOUT_SECONDS <= 10

    import inspect

    for method in (
        PostgresBrainStore._load_projection,
        PostgresBrainStore._count_cognition_events,
    ):
        source = inspect.getsource(method)
        # psycopg_pool defaults to 30s; the cockpit polls eighteen routes at
        # once, so an unbounded wait multiplies into a stalled dashboard.
        assert "timeout=self.READ_TIMEOUT_SECONDS" in source


# --- the lease must fail closed, and never deadlock on itself -------------


def test_the_temporal_fallback_reuses_the_lease_it_already_holds(monkeypatch):
    """The deadlock: a second lease blocks forever on the first one."""

    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    built = []

    class CountingLease:
        def __init__(self, dsn):
            built.append(dsn)

        def acquire(self, *, blocking=False):
            return True

    monkeypatch.setattr("brain.cognition_lease.CognitionLease", CountingLease)
    monkeypatch.setattr(worker, "_cognition_lease", None, raising=False)
    monkeypatch.setattr(worker, "_lease_required", False, raising=False)

    first = worker.acquire_cognition_lease()
    second = worker.acquire_cognition_lease()

    # pg_advisory_lock on a second connection waits for the lock the first one
    # holds, in the same process, forever -- so the advertised in-process
    # fallback after a Temporal failure would never start.
    assert second is first
    assert len(built) == 1


def test_a_configured_worker_that_cannot_take_the_lease_refuses_to_write(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")

    class RefusingLease:
        def __init__(self, dsn):
            pass

        def acquire(self, *, blocking=False):
            return False

    monkeypatch.setattr("brain.cognition_lease.CognitionLease", RefusingLease)
    monkeypatch.setattr(worker, "_cognition_lease", None, raising=False)
    monkeypatch.setattr(worker, "_lease_required", False, raising=False)

    assert worker.acquire_cognition_lease() is None
    # None means two opposite things -- "nobody to race" and "lost the lock".
    # Reading a failed acquisition as the former is how a lease fails open.
    assert worker._lease_required is True
    assert worker._lease_still_held() is False


def test_a_worker_with_no_database_still_writes_freely(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BRAIN_WORKER_DATABASE_URL", raising=False)
    monkeypatch.setattr(worker, "_cognition_lease", None, raising=False)
    monkeypatch.setattr(worker, "_lease_required", True, raising=False)

    assert worker.acquire_cognition_lease() is None
    assert worker._lease_required is False
    assert worker._lease_still_held() is True


def test_ingest_and_maintenance_recheck_the_lease(monkeypatch):
    import inspect

    source = inspect.getsource(worker.run_forever_with_maintenance)
    # A cognition cycle runs between the top-of-pass check and these two, and
    # the lock can be dropped anywhere in that window.
    assert source.count("_lease_still_held()") >= 3


def test_the_temporal_worker_does_not_start_without_the_lease():
    import inspect

    source = inspect.getsource(worker.main)
    assert "acquire_cognition_lease() is None and _lease_required" in source


# --- request-driven ticks answer to the lease too --------------------------


def test_a_request_tick_is_refused_while_another_process_owns_cognition(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(api, "_inline_cognition", None)
    ticked = []
    monkeypatch.setattr(api, "tick_once", lambda **kwargs: ticked.append(1))

    class HeldElsewhere:
        def __init__(self, dsn):
            pass

        def acquire(self, *, blocking=False):
            return False

        def release(self):
            pass

    monkeypatch.setattr(api, "CognitionLease", HeldElsewhere)

    with pytest.raises(Exception) as excinfo:
        api.request_tick(max_items=1)

    # _tick_lock only serialises threads here. A worker holding the database
    # lease is a second writer on the same inbox and belief projection.
    assert getattr(excinfo.value, "status_code", None) == 409
    assert ticked == []


def test_a_request_tick_borrows_the_lease_when_nothing_else_holds_it(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(api, "_inline_cognition", None)
    monkeypatch.setattr(api, "tick_once", lambda **kwargs: {"ticked": True})
    released = []

    class Available:
        def __init__(self, dsn):
            pass

        def acquire(self, *, blocking=False):
            return True

        def release(self):
            released.append(1)

    monkeypatch.setattr(api, "CognitionLease", Available)

    assert api.request_tick(max_items=1) == {"ticked": True}
    # An operator tick is a short-lived writer; holding the lease afterwards
    # would lock out the process that actually runs cognition.
    assert released == [1]


def test_a_request_tick_rides_the_lease_the_inline_loop_already_holds(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(api, "tick_once", lambda **kwargs: {"ticked": True})

    class Holder:
        holds_lease = True
        ready_to_write = True

        def revalidate_lease(self):
            return True

    monkeypatch.setattr(api, "_inline_cognition", Holder())
    monkeypatch.setattr(
        api,
        "CognitionLease",
        lambda dsn: (_ for _ in ()).throw(AssertionError("must not take a second lease")),
    )

    assert api.request_tick(max_items=1) == {"ticked": True}


def test_a_request_tick_needs_no_lease_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(api, "tick_once", lambda **kwargs: {"ticked": True})
    monkeypatch.setattr(
        api,
        "CognitionLease",
        lambda dsn: (_ for _ in ()).throw(AssertionError("must not take a lease")),
    )

    assert api.request_tick(max_items=1) == {"ticked": True}


# --- resuming beliefs on every acquisition, not once ----------------------


def test_resume_runs_again_after_the_lease_is_yielded_and_retaken():
    started = []
    lease = _FakeLease()
    clock = FakeClock()
    eng = inline.InlineCognition(
        tick=lambda: {},
        lease=lease,
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=300,
        yield_pause_seconds=0,
        clock=clock,
        on_start=lambda: started.append(1),
    )

    eng._step()
    assert started == [1]
    clock.advance(300)
    eng._step()
    eng._step()

    # Whoever held it in between has been writing beliefs this cycle cache has
    # never seen; reasoning on from the pre-handoff cache overwrites them.
    assert started == [1, 1]


def test_losing_the_lease_also_arms_the_next_resume():
    started = []
    lease = _FakeLease()
    eng = inline.InlineCognition(
        tick=lambda: {},
        lease=lease,
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=0,
        on_start=lambda: started.append(1),
    )
    eng._step()
    lease.granted = False
    eng._step()
    lease.granted = True
    eng._step()

    assert started == [1, 1]


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


# --- reads that cannot outlive their bound, or lose a concurrent write ----


def test_reads_carry_a_server_side_statement_timeout():
    import inspect

    # pool.connection(timeout=...) bounds only checking a connection out; the
    # query itself then runs with no client-side deadline at all.
    for method in (
        PostgresBrainStore._load_projection,
        PostgresBrainStore._count_cognition_events,
    ):
        assert "self._bound_statements(cur)" in inspect.getsource(method)
    assert "statement_timeout" in inspect.getsource(PostgresBrainStore._bound_statements)


def test_a_belief_written_during_a_load_survives_the_swap(monkeypatch):
    from brain.domain import Belief

    store = _detached_store()
    written = Belief(statement="written mid load", confidence=0.5)

    from brain.memory import InMemoryBrainStore

    def load_and_write(self):
        # Commits after the belief query has already run, which is the window
        # that made the swap lose it -- through the real write path, so this
        # exercises the same lock the swap takes.
        self._apply_local(written, InMemoryBrainStore.save)
        return ({"from-database": "belief"}, {}, {}, {}, [])

    monkeypatch.setattr(PostgresBrainStore, "_load_projection", load_and_write)

    store.hydrate()

    assert store.beliefs["from-database"] == "belief"
    assert store.beliefs[written.id] is written


def test_a_failed_load_does_not_leave_write_recording_armed(monkeypatch):
    store = _detached_store()
    monkeypatch.setattr(
        PostgresBrainStore,
        "_load_projection",
        lambda self: (_ for _ in ()).throw(RuntimeError("database went away")),
    )

    with pytest.raises(RuntimeError):
        store.hydrate()

    # Left armed, every later write would accumulate in a buffer nothing ever
    # drains.
    assert store._inflight is None


def test_counter_cache_misses_are_single_flighted(monkeypatch):
    store = _detached_store()
    counts = []

    def slow_count(self):
        counts.append(1)
        time.sleep(0.02)
        return {"cycle.completed": len(counts)}

    monkeypatch.setattr(PostgresBrainStore, "_count_cognition_events", slow_count)

    threads = [
        threading.Thread(target=lambda: store.cognition_counters(60)) for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    # Releasing the lock before the query let parallel /health and
    # /runner/status polls each run the full lifetime count.
    assert len(counts) == 1


# --- the refresh must not stall the event loop ----------------------------


def test_the_read_boundary_refreshes_off_the_event_loop():
    import inspect

    source = inspect.getsource(api.refresh_projection_reads)
    # refresh_if_stale is synchronous and can hold a pooled connection while
    # it reads; awaiting it inline would stall every other request.
    assert "run_in_threadpool(_refresh_reads)" in source


@pytest.mark.parametrize("raw", ["-1", "-0.5"])
def test_negative_read_refresh_falls_back(monkeypatch, raw):
    monkeypatch.setenv("BRAIN_READ_REFRESH_SECONDS", raw)

    # refresh_if_stale refuses a negative TTL outright, so the projection
    # would serve the boot snapshot forever -- the original bug, wearing a
    # tuning knob as a disguise.
    assert api._read_refresh_seconds() == 5.0


def test_resuming_beliefs_holds_the_tick_lock():
    import inspect

    assert "with _tick_lock:" in inspect.getsource(api._resume_durable_beliefs)


def test_resuming_beliefs_reads_current_state_first():
    import inspect

    source = inspect.getsource(api._resume_durable_beliefs)
    assert source.index("_refresh_reads()") < source.index("with _tick_lock:")


# --- the timeout must be SQL PostgreSQL will actually accept ---------------


def test_the_statement_timeout_is_set_through_set_config():
    """SET is parsed before parameters are bound.

    `set statement_timeout = %s` reaches the server as
    `set statement_timeout = $1`, which is a syntax error -- and because it
    fails inside the transaction, it aborts it, so every query after it dies
    with "current transaction is aborted" instead of anything naming the
    cause. CI's real PostgreSQL caught this; no fake cursor could have.
    set_config is an ordinary function call and takes a bound parameter.
    """

    class Recording:
        def __init__(self):
            self.statements = []

        def execute(self, statement, params=()):
            self.statements.append(statement)

    cur = Recording()
    _detached_store()._bound_statements(cur)
    statement = cur.statements[0]

    # Asserted against the SQL actually sent, not the source text: the
    # docstring explaining this bug quotes the broken form, so a source scan
    # would trip over the explanation.
    assert "set_config" in statement
    assert not statement.lower().lstrip().startswith("set ")
    # Transaction-local, so the bound cannot leak onto a pooled connection a
    # later caller checks out for something deliberately slower.
    assert "true" in statement


def test_the_timeout_value_is_passed_as_text_not_an_integer():
    """set_config's value argument is text; psycopg would send an int as
    integer and the function would reject it."""

    class Recording:
        def __init__(self):
            self.calls = []

        def execute(self, statement, params=()):
            self.calls.append((statement, params))

    store = _detached_store()
    cur = Recording()
    store._bound_statements(cur)

    statement, params = cur.calls[0]
    assert "set_config" in statement
    assert params == (str(int(PostgresBrainStore.READ_TIMEOUT_SECONDS * 1000)),)
    assert isinstance(params[0], str)


# --- ownership checked and used without letting go in between -------------


def test_a_request_cannot_tick_on_a_lease_the_loop_is_giving_away():
    """The TOCTOU CodeRabbit found in the first version of request_tick.

    A request read holds_lease, and before it reached the tick the inline loop
    hit its periodic yield and released -- so a worker could take the advisory
    lock and the request ticked as a second writer, having truthfully observed
    itself to be the first.
    """

    guard = threading.RLock()
    lease = _FakeLease()
    clock = FakeClock()
    eng = inline.InlineCognition(
        tick=lambda: {},
        lease=lease,
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=300,
        yield_pause_seconds=0,
        clock=clock,
        guard=guard,
    )
    eng._step()
    assert eng.holds_lease is True

    observed = []
    released = threading.Event()

    def yielder():
        clock.advance(300)
        eng._step()
        released.set()

    # Hold the guard the way request_tick does, then let the loop try to yield.
    with guard:
        thread = threading.Thread(target=yielder, daemon=True)
        thread.start()
        # It cannot release while the guard is held, so ownership observed
        # inside this block stays true for as long as the block lasts.
        released.wait(timeout=0.2)
        observed.append(eng.holds_lease)
    thread.join(timeout=5)

    assert observed == [True]
    assert eng.holds_lease is False


def test_request_tick_revalidates_rather_than_trusting_a_timestamp(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(api, "tick_once", lambda **kwargs: {"ticked": True})
    borrowed = []

    class StaleHolder:
        # Resumed and owning, as far as this process can tell locally -- but
        # both are timestamps, and the connection behind them is gone.
        holds_lease = True
        ready_to_write = True

        def revalidate_lease(self):
            return False

    monkeypatch.setattr(api, "_inline_cognition", StaleHolder())

    class Available:
        def __init__(self, dsn):
            borrowed.append(dsn)

        def acquire(self, *, blocking=False):
            return True

        def release(self):
            pass

    monkeypatch.setattr(api, "CognitionLease", Available)

    assert api.request_tick(max_items=1) == {"ticked": True}
    # Fell through to taking its own lease rather than writing on a stale one.
    assert borrowed == ["postgres:///brain"]


def test_the_tick_lock_is_reentrant():
    # The inline loop holds the guard across a lease transition and then calls
    # tick_once, which takes it again on the same thread. A plain Lock would
    # deadlock the cognition thread on its first yield.
    assert type(api._tick_lock).__name__ == "RLock"


# --- no write can be lost in the swap, including a rewire -----------------


def test_a_write_between_the_drain_and_the_swap_is_not_lost(monkeypatch):
    """The second race CodeRabbit found.

    Draining _inflight first and assigning afterwards left an interval where a
    write mutated the old projection, found no buffer to record itself in, and
    was then discarded by the assignment.
    """

    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(PostgresBrainStore.hydrate)))

    def guarded_bodies(node):
        """Every statement list that runs while _inflight_lock is held."""

        for child in ast.walk(node):
            if not isinstance(child, ast.With):
                continue
            if any(
                isinstance(item.context_expr, ast.Attribute)
                and item.context_expr.attr == "_inflight_lock"
                for item in child.items
            ):
                yield child

    def mentions(node, text):
        return text in ast.dump(node)

    swapping = [
        block
        for block in guarded_bodies(tree)
        if mentions(block, "'_inflight'") and mentions(block, "attr='beliefs'")
    ]

    # Draining the buffer and assigning the new projection have to be the same
    # critical section. Split across two, a write lands in between, finds no
    # buffer to record itself in, and is discarded by the assignment.
    assert swapping, (
        "the drain and the projection swap must happen under one "
        "_inflight_lock block"
    )


def test_local_writes_mutate_and_record_under_one_lock():
    import inspect

    source = inspect.getsource(PostgresBrainStore._apply_local)
    lock = source.index("with self._inflight_lock")
    mutate = source.index("method(self, item)")
    record = source.index('pending["beliefs"]')
    # A write that has mutated the projection but not yet recorded itself is
    # exactly the write a concurrent swap loses.
    assert lock < mutate < record


def test_a_rewire_written_during_a_load_survives_the_swap(monkeypatch):
    from brain.domain import RewireEvent, RewireOperation
    from brain.memory import InMemoryBrainStore

    store = _detached_store()
    from uuid import uuid4

    event = RewireEvent(
        operation=RewireOperation.STRENGTHEN_EDGE,
        reason="written mid load",
        target_id=uuid4(),
        previous={},
        current={},
    )

    def load_and_write(self):
        self._apply_local(event, InMemoryBrainStore.log_rewire)
        return ({}, {}, {}, {}, [])

    monkeypatch.setattr(PostgresBrainStore, "_load_projection", load_and_write)

    store.hydrate()

    # log_rewire was the one write path the in-flight buffer did not cover.
    assert event in store.rewires


def test_every_projection_write_path_goes_through_apply_local():
    import inspect

    for method in (
        PostgresBrainStore.save,
        PostgresBrainStore.upsert_node,
        PostgresBrainStore.upsert_edge,
        PostgresBrainStore.log_rewire,
    ):
        source = inspect.getsource(method)
        assert "_apply_local" in source, f"{method.__name__} bypasses the swap lock"
        assert "super()." not in source, (
            f"{method.__name__} mutates the projection outside the lock"
        )


# --- failing closed must not mean failing forever -------------------------


def test_a_worker_that_lost_the_lease_tries_to_get_it_back(monkeypatch):
    """Fail closed, but leave a way back open.

    Refusing to write without the lease is right; never retrying is a Brain
    that is correct, permissionless and permanently idle after one transient
    outage.
    """

    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(worker, "_cognition_lease", None, raising=False)
    monkeypatch.setattr(worker, "_lease_required", True, raising=False)
    attempts = []

    class Recovered:
        def __init__(self, dsn):
            attempts.append(dsn)

        def acquire(self, *, blocking=False):
            # Non-blocking: the loop paces its own retries, and blocking here
            # would hold it in a call it cannot pace or log.
            assert blocking is False
            return True

    monkeypatch.setattr("brain.cognition_lease.CognitionLease", Recovered)

    assert worker._lease_still_held() is True
    assert attempts == ["postgres:///brain"]
    assert worker._cognition_lease is not None


def test_a_still_unavailable_lease_keeps_the_worker_quiet(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(worker, "_cognition_lease", None, raising=False)
    monkeypatch.setattr(worker, "_lease_required", True, raising=False)

    class StillDown:
        def __init__(self, dsn):
            pass

        def acquire(self, *, blocking=False):
            return False

    monkeypatch.setattr("brain.cognition_lease.CognitionLease", StillDown)

    assert worker._lease_still_held() is False
    assert worker._cognition_lease is None


def test_a_leaseless_worker_needs_no_reacquisition(monkeypatch):
    monkeypatch.setattr(worker, "_cognition_lease", None, raising=False)
    monkeypatch.setattr(worker, "_lease_required", False, raising=False)
    monkeypatch.setattr(
        "brain.cognition_lease.CognitionLease",
        lambda dsn: (_ for _ in ()).throw(AssertionError("must not take a lease")),
    )

    # No database, nothing shared, nobody to ask.
    assert worker._lease_still_held() is True


def test_the_workflow_does_not_count_activities_that_declined():
    import inspect

    source = inspect.getsource(worker)
    workflow_run = source[source.index("class ContinuousCognitionWorkflow") :]
    workflow_run = workflow_run[: workflow_run.index("def _tick_under_lease")]

    # An activity that returned for want of the lease completed without doing
    # anything; counting it reports work that never ran.
    assert 'batch.get("skipped")' in workflow_run
    assert 'outcome.get("skipped")' in workflow_run


def test_prediction_maintenance_distinguishes_idle_from_declined():
    import inspect

    source = inspect.getsource(worker)
    start = source.index('@activity.defn(name="brain.prediction_maintenance")')
    body = source[start : source.index("@activity.defn", start + 10)]

    # Returning 0 for both "ran and expired nothing" and "did not run" is what
    # let the workflow count maintenance that never happened.
    assert '{"skipped": "cognition_lease_unavailable"}' in body
    assert '{"expired": 0}' in body


def test_a_request_cannot_tick_between_winning_the_lease_and_resuming():
    """The window CodeRabbit found on b8238c8.

    _step() took the guard only around lease.acquire() and let it go before
    setting _held_since and running on_start. That left a moment in which
    request_tick could take _tick_lock, see holds_lease true, revalidate the
    advisory lock successfully -- all truthfully -- and tick against the
    belief cache from before the *previous* lease holder's writes. Which is
    the exact stale-cache write on_start exists to prevent, arriving through
    the one door the lease cannot guard.
    """

    guard = threading.RLock()
    resuming = threading.Event()
    finish_resume = threading.Event()
    taken_during_resume = []

    def on_start():
        resuming.set()
        finish_resume.wait(timeout=5)

    eng = inline.InlineCognition(
        tick=lambda: {},
        lease=_FakeLease(),
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=0,
        on_start=on_start,
        guard=guard,
    )

    stepping = threading.Thread(target=eng._step, daemon=True)
    stepping.start()
    assert resuming.wait(timeout=5) is True

    # Stand in for a request thread arriving mid-resume. request_tick's very
    # first act is to take this lock; if it can, it ticks.
    acquired = guard.acquire(blocking=False)
    taken_during_resume.append(acquired)
    if acquired:
        guard.release()

    finish_resume.set()
    stepping.join(timeout=5)

    assert taken_during_resume == [False]


def test_a_resume_that_fails_is_retried_before_the_next_tick():
    """_started was set before on_start ran, so a raise consumed the retry.

    The exception reaches run()'s handler, which logs and backs off -- but
    _started is already true, so the next pass skips the resume entirely and
    thinks on, permanently, from a cache that was never loaded.
    """

    calls = []

    def on_start():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("resume blew up")

    eng = inline.InlineCognition(
        tick=lambda: {},
        lease=_FakeLease(),
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=0,
        on_start=on_start,
    )

    with pytest.raises(RuntimeError):
        eng._step()
    eng._step()

    assert calls == [1, 1]


def test_a_request_tick_is_refused_while_the_resume_has_not_succeeded(monkeypatch):
    """Belt to the guard's braces.

    If on_start raised, the lease is held but the cache behind it was never
    loaded. Riding that lease would write stale beliefs; refusing sends the
    operator a 409 they can retry, which is the honest answer.
    """

    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(
        api,
        "tick_once",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not tick")),
    )

    class Unresumed:
        holds_lease = True
        ready_to_write = False

        def revalidate_lease(self):
            return True

    monkeypatch.setattr(api, "_inline_cognition", Unresumed())
    # The inline thread holds the advisory lock, so borrowing one fails too.
    monkeypatch.setattr(api, "CognitionLease", lambda dsn: _FakeLease(granted=False))

    with pytest.raises(HTTPException) as refused:
        api.request_tick(max_items=1)

    assert refused.value.status_code == 409


# --- Codex round three, against 890d234 ------------------------------------


def test_a_borrowed_lease_tick_resumes_durable_beliefs_first(monkeypatch):
    """The path taken when inline cognition is off, and the only one unguarded.

    _resume_durable_beliefs() had exactly one caller: the inline engine's
    on_start. Switch inline cognition off and a request that borrows the lease
    ticks against a cycle cache that was never loaded at all -- reasoning from
    the boot snapshot, re-deriving what the database already holds, and
    persisting it over the previous writer's beliefs while holding exclusive
    ownership.
    """

    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(api, "_inline_cognition", None)
    monkeypatch.setattr(api, "CognitionLease", lambda dsn: _FakeLease(granted=True))

    order = []
    monkeypatch.setattr(api, "_resume_durable_beliefs", lambda: order.append("resume"))
    monkeypatch.setattr(api, "tick_once", lambda **kwargs: order.append("tick") or {"ok": True})

    assert api.request_tick(max_items=1) == {"ok": True}
    assert order == ["resume", "tick"]


def test_a_borrowed_lease_tick_is_refused_when_the_resume_fails(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(api, "_inline_cognition", None)
    monkeypatch.setattr(api, "CognitionLease", lambda dsn: _FakeLease(granted=True))
    monkeypatch.setattr(
        api,
        "_resume_durable_beliefs",
        lambda: (_ for _ in ()).throw(RuntimeError("database gone")),
    )
    monkeypatch.setattr(
        api,
        "tick_once",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("must not tick")),
    )

    with pytest.raises(HTTPException) as refused:
        api.request_tick(max_items=1)

    assert refused.value.status_code == 503


def test_resuming_forces_a_hydrate_rather_than_honouring_the_read_ttl(monkeypatch):
    """A yield-and-retake is seconds; BRAIN_READ_REFRESH_SECONDS is longer.

    Delegating to _refresh_reads() meant the resume asked for a TTL-bounded
    refresh, got told the cache was fresh enough, and "succeeded" against the
    very pre-handover snapshot it exists to replace.
    """

    asked = []

    class Store:
        beliefs: dict = {}

        def refresh_if_stale(self, max_age_seconds):
            asked.append(max_age_seconds)
            return True

    monkeypatch.setattr(api, "_brain_store", Store())
    monkeypatch.setattr(api.heartbeat, "_cycle", type("C", (), {"register_belief": lambda s, b: None})())

    api._resume_durable_beliefs()

    # Zero, not the read TTL: no cached answer is fresh enough for this.
    assert asked == [0.0]


def test_a_failed_resume_refresh_is_not_swallowed(monkeypatch):
    """_refresh_reads() swallows, correctly, for read routes. Not for this.

    A swallowed failure reports a resume that never happened -- and that
    report is what marks the process ready to write.
    """

    class Store:
        beliefs: dict = {}

        def refresh_if_stale(self, max_age_seconds):
            raise RuntimeError("database gone")

    monkeypatch.setattr(api, "_brain_store", Store())
    monkeypatch.setattr(api.heartbeat, "_cycle", type("C", (), {"register_belief": lambda s, b: None})())

    with pytest.raises(RuntimeError):
        api._resume_durable_beliefs()


def test_a_queued_signal_survives_a_refused_immediate_tick(monkeypatch):
    """perceive() has already committed by the time the tick is refused.

    Letting the 409 be the response omitted the id and sent a well-behaved
    client back to retry, enqueuing the same signal twice.
    """

    monkeypatch.setenv("BRAIN_API_KEY", "test-key")
    monkeypatch.setattr(
        api,
        "request_tick",
        lambda **kwargs: (_ for _ in ()).throw(
            HTTPException(status_code=409, detail="cognition_lease_held_elsewhere: x")
        ),
    )

    client = TestClient(api.app)
    response = client.post(
        "/signals",
        json={"content": "c", "claim": "k", "process_now": True},
        headers={"X-Brain-Api-Key": "test-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"]
    assert body["tick"]["deferred"] is True
    assert body["tick"]["status_code"] == 409


def test_the_lease_is_rechecked_after_connector_ingest(monkeypatch):
    """Ingest talks to the network and can block for a long time.

    The check happened before it; the lock can be dropped anywhere inside it.
    Falling straight through to run_once() spent that window writing a
    cognition cycle as a second writer.
    """

    ticked = []
    state = {"held": True, "ingested": False}

    def lease_check():
        return state["held"]

    class Ingest:
        def ingest_due_sources(self):
            # The lock is dropped somewhere inside the network call.
            state["ingested"] = True
            state["held"] = False

    class Runner:
        _idle_cycles = 0

        def run_once(self):
            ticked.append(1)
            raise AssertionError("must not tick after losing the lease during ingest")

    def sleeper(_seconds):
        if state["ingested"]:
            raise StopIteration

    monkeypatch.setattr(worker, "_lease_still_held", lease_check)
    monkeypatch.setattr(worker, "_runner_singleton", lambda: Runner())
    monkeypatch.setattr(worker, "_learning_singleton", lambda: None)
    monkeypatch.setattr(worker, "_ingest_singleton", lambda: Ingest())
    monkeypatch.setattr(worker.time, "sleep", sleeper)

    with pytest.raises(StopIteration):
        worker.run_forever_with_maintenance(tick_sleep=0, ingest_every=1, maintenance_every=0)

    assert ticked == []


def test_reacquiring_a_lost_lease_reloads_the_projection(monkeypatch):
    """Getting the lock back is not the same as being current.

    Somebody else held it, and wrote. The runner and its store still carry the
    pre-handover projection, so resuming on it reasons from stale beliefs and
    persists conflicting versions over the writer that actually held the lease.
    """

    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(worker, "_cognition_lease", None)
    monkeypatch.setattr(worker, "_lease_required", True)

    import brain.cognition_lease as lease_module

    monkeypatch.setattr(lease_module, "CognitionLease", lambda dsn: _FakeLease(granted=True))

    resumed = []
    monkeypatch.setattr(worker, "_resume_worker_state", lambda: resumed.append(1))

    assert worker._reacquire_cognition_lease() is True
    assert resumed == [1]


def test_a_reacquisition_that_cannot_reload_does_not_grant_permission(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setattr(worker, "_cognition_lease", None)
    monkeypatch.setattr(worker, "_lease_required", True)

    import brain.cognition_lease as lease_module

    released = _FakeLease(granted=True)
    monkeypatch.setattr(lease_module, "CognitionLease", lambda dsn: released)
    monkeypatch.setattr(
        worker,
        "_resume_worker_state",
        lambda: (_ for _ in ()).throw(RuntimeError("database gone")),
    )

    # Better to stay idle and retry than to write from a cache we know is
    # stale; and the lock goes back so a healthy process can have it.
    assert worker._reacquire_cognition_lease() is False
    assert released.released == 1


def test_the_worker_resume_forces_a_hydrate(monkeypatch):
    asked = []
    registered = []

    class Store:
        beliefs = {"a": object()}

        def refresh_if_stale(self, max_age_seconds):
            asked.append(max_age_seconds)
            return True

    class Cycle:
        event_store = Store()

        def register_belief(self, belief):
            registered.append(belief)

    monkeypatch.setattr(worker, "_runner", type("R", (), {"cycle": Cycle()})())

    worker._resume_worker_state()

    assert asked == [0.0]
    assert len(registered) == 1


@pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "-1", "not-a-number"])
def test_an_unusable_worker_tick_interval_falls_back(monkeypatch, raw):
    """Pacing endogenous cycles put time.sleep() on nearly every pass.

    Before that it was all but unreachable, so a bad BRAIN_TICK_SLEEP sat
    harmless. Now infinity raises OverflowError and a negative raises
    ValueError on the first idle tick, killing the worker.
    """

    monkeypatch.setenv("BRAIN_TICK_SLEEP", raw)

    value = worker._tick_sleep_seconds()

    assert value == 1.0
    time.sleep(value * 0)  # the fallback is a value time.sleep() accepts


def test_a_usable_worker_tick_interval_is_honoured(monkeypatch):
    monkeypatch.setenv("BRAIN_TICK_SLEEP", "0.25")

    assert worker._tick_sleep_seconds() == 0.25


def test_a_rewire_written_during_a_load_is_not_installed_twice():
    """A load is a series of queries, not an instant.

    A rewire committed after the load began but before the rewire_events query
    ran is both read and recorded in flight, and extending unconditionally
    then showed every reader two copies of one durable event.
    """

    from brain.domain import RewireEvent, RewireOperation

    store = _detached_store()
    shared = RewireEvent(
        operation=RewireOperation.STRENGTHEN_EDGE,
        reason="observed twice",
        target_id=uuid4(),
        previous={},
        current={},
    )

    def load():
        # The query returns it, and the in-flight buffer holds it too.
        store._inflight["rewires"].append(shared)
        return {}, {}, {}, {}, [shared]

    store._load_projection = load
    store.hydrate()

    assert [item.id for item in store.rewires] == [shared.id]


def test_temporal_activities_check_the_lease_off_the_event_loop():
    """_lease_still_held() can open a connection and run a query.

    Awaited directly inside an async activity, that blocks the Temporal
    worker's event-loop thread -- stalling dispatch, cancellation and shutdown
    for the whole of a database outage, which is exactly when the check is
    slowest. cognition_tick_activity already went through a thread; the other
    two called it inline. A source-level check because the failure is which
    thread the call runs on, which no return value reveals.
    """

    import ast
    import inspect
    import textwrap

    source = textwrap.dedent(inspect.getsource(worker))
    tree = ast.parse(source)

    guarded = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef) or not node.name.endswith("_activity"):
            continue
        direct = False
        threaded = False
        for inner in ast.walk(node):
            # await asyncio.to_thread(_lease_still_held)
            if isinstance(inner, ast.Await) and isinstance(inner.value, ast.Call):
                call = inner.value
                args = [a for a in call.args if isinstance(a, ast.Name)]
                if any(a.id == "_lease_still_held" for a in args):
                    threaded = True
                    continue
            # _lease_still_held() called straight on the loop
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_lease_still_held"
            ):
                direct = True
        if direct or threaded:
            guarded[node.name] = (direct, threaded)

    assert guarded, "no lease-checking Temporal activities found"
    offenders = {name for name, (direct, _) in guarded.items() if direct}
    assert offenders == set(), f"lease checked on the event loop in: {sorted(offenders)}"


# --- Codex round four, against c8b0a28 -------------------------------------


class _ReconnectingLease:
    """A lease whose acquire() hides a reconnect, as the real one does."""

    def __init__(self):
        self.generation = 1
        self.released = 0

    def acquire(self, *, blocking=False):
        return True

    def release(self):
        self.released += 1

    def sever(self):
        # What CognitionLease does when _still_connected() fails: drop, open a
        # new connection, take the lock again, return True. The lock was free
        # in between.
        self.generation += 1


def test_a_lease_that_reconnected_is_not_mistaken_for_continuous_ownership():
    """acquire() returning True does not mean nobody else held it.

    In the gap between a severed connection and the reconnect the lock is
    free, so another writer can take it, write, and release. Resetting the
    resume only on a False result reads that as uninterrupted ownership and
    thinks on from a cache that is now several versions stale.
    """

    lease = _ReconnectingLease()
    started = []
    eng = inline.InlineCognition(
        tick=lambda: {},
        lease=lease,
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=0,
        on_start=lambda: started.append(1),
    )

    eng._step()
    eng._step()
    assert started == [1]

    lease.sever()
    eng._step()

    assert started == [1, 1]


def test_the_lease_reports_a_new_generation_after_a_reconnect():
    from brain.cognition_lease import CognitionLease

    class Conn:
        def __init__(self):
            self.closed = False

        def execute(self, *args):
            if self.closed:
                raise RuntimeError("connection is gone")
            return self

        def fetchone(self):
            return (True,)

        def close(self):
            self.closed = True

    opened = []

    def connect(dsn, autocommit=False):
        conn = Conn()
        opened.append(conn)
        return conn

    lease = CognitionLease("postgres:///brain", verify_interval_seconds=0, connect=connect)

    assert lease.acquire() is True
    first = lease.generation
    assert lease.acquire() is True
    assert lease.generation == first, "a still-live session is the same generation"

    opened[0].closed = True
    assert lease.acquire() is True

    # Same boolean, different session -- and only the generation says so.
    assert lease.generation != first


def test_every_release_path_takes_the_guard():
    """stop() and run()'s final release skipped the guard.

    A shutdown landing while a request was inside request_tick(), ticking on
    the strength of this lease, handed the lock to a waiting worker mid-write.
    """

    guard = threading.RLock()
    lease = _FakeLease()
    eng = inline.InlineCognition(
        tick=lambda: {},
        lease=lease,
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=0,
        guard=guard,
    )
    eng._step()

    holding = threading.Event()
    release_it = threading.Event()
    released_while_held = []

    def request_side():
        # Stand in for request_tick holding the writer boundary across a tick.
        with guard:
            holding.set()
            release_it.wait(timeout=5)
            released_while_held.append(lease.released)

    worker_thread = threading.Thread(target=request_side, daemon=True)
    worker_thread.start()
    assert holding.wait(timeout=5) is True

    stopper = threading.Thread(target=lambda: eng.stop(timeout=1), daemon=True)
    stopper.start()
    time.sleep(0.1)

    release_it.set()
    worker_thread.join(timeout=5)
    stopper.join(timeout=5)

    # The lease must still have been held for the whole of the request's turn.
    assert released_while_held == [0]


def test_the_worker_takes_the_lease_before_building_a_writing_runner(monkeypatch):
    """build_runner() writes: bootstrap_mind() appends belief.seeded events.

    Constructing it before the first lease check meant a worker that could not
    take the lock still put a batch of cognition events into the shared ledger
    on its way to logging that it was refusing to write.
    """

    built = []
    checks = []

    def lease_check():
        checks.append(1)
        if len(checks) < 3:
            return False
        raise StopIteration  # stop the loop once it gets past the gate

    monkeypatch.setattr(worker, "_lease_still_held", lease_check)
    monkeypatch.setattr(worker, "_runner_singleton", lambda: built.append(1))
    monkeypatch.setattr(worker, "_learning_singleton", lambda: None)
    monkeypatch.setattr(worker, "_ingest_singleton", lambda: None)
    monkeypatch.setattr(worker.time, "sleep", lambda s: None)

    with pytest.raises(StopIteration):
        worker.run_forever_with_maintenance(tick_sleep=0, ingest_every=0, maintenance_every=0)

    # Two refusals happened before anything was constructed.
    assert built == []
