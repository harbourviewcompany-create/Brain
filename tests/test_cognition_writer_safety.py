"""What has to hold once the API process itself writes cognition.

The inline loop turned a read-only process into a writer. Everything here is
a way that could go wrong quietly -- cycles counted against a lattice that
never grows, two writers inside one process, a projection blanked by a
transient outage, a lease held by a thread that has stopped thinking.
"""

from __future__ import annotations

import threading
import time

import pytest
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
            f"{route.__name__} must tick through tick_once, not directly"
        )
        assert "tick_once(" in source


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
