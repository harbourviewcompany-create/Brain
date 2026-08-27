"""In-process cognition: when it runs, when it refuses to, and when it yields."""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from apps.api.inline_cognition import (
    InlineCognition,
    _did_work,
    cognition_dsn,
    inline_cognition_requested,
    start_inline_cognition,
)


class FakeLease:
    def __init__(self, granted=True):
        self.granted = granted
        self.acquired = 0
        self.released = 0
        self.held = False

    def acquire(self, *, blocking=False):
        self.acquired += 1
        self.held = self.granted
        return self.granted

    def release(self):
        self.released += 1
        self.held = False


class FakeClock:
    """A clock the test advances by hand, so the yield interval is exact."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def engine(**kwargs):
    defaults = dict(
        tick=lambda: {"processed_this_call": 1},
        lease=FakeLease(),
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=0,
    )
    defaults.update(kwargs)
    return InlineCognition(**defaults)


def test_disabled_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BRAIN_WORKER_DATABASE_URL", raising=False)
    monkeypatch.delenv("BRAIN_INLINE_COGNITION", raising=False)

    # In-memory cognition would write beliefs no other process can read and
    # lose them on the next deploy: worse than not thinking, because the
    # cockpit would report cycles nobody can account for.
    assert inline_cognition_requested() is False


def test_enabled_by_default_once_a_database_is_configured(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.delenv("BRAIN_INLINE_COGNITION", raising=False)

    assert inline_cognition_requested() is True


@pytest.mark.parametrize("value", ["false", "FALSE", "0", "off", "no", " no "])
def test_explicitly_disabled(monkeypatch, value):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    monkeypatch.setenv("BRAIN_INLINE_COGNITION", value)

    assert inline_cognition_requested() is False


def test_the_worker_dsn_wins_over_the_shared_one(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///shared")
    monkeypatch.setenv("BRAIN_WORKER_DATABASE_URL", "postgres:///worker")

    assert cognition_dsn() == "postgres:///worker"


def test_a_step_with_the_lease_ticks_the_brain():
    ticks = []
    eng = engine(tick=lambda: ticks.append(1) or {"processed_this_call": 1})

    eng._step()

    assert ticks == [1]
    assert eng.holds_lease is True


def test_a_step_without_the_lease_does_not_tick():
    ticks = []
    lease = FakeLease(granted=False)
    eng = engine(tick=lambda: ticks.append(1), lease=lease)

    eng._step()

    # Two processes ticking the same event store double every cycle and race
    # on belief versions.
    assert ticks == []
    assert eng.holds_lease is False
    assert lease.acquired == 1


def test_losing_the_lease_mid_run_stops_the_ticking():
    lease = FakeLease(granted=True)
    ticks = []
    eng = engine(tick=lambda: ticks.append(1), lease=lease)
    eng._step()
    lease.granted = False

    eng._step()

    assert ticks == [1]
    assert eng.holds_lease is False


def test_the_lease_is_yielded_so_a_real_worker_can_take_over():
    lease = FakeLease()
    ticks = []
    clock = FakeClock()
    eng = engine(
        tick=lambda: ticks.append(1), lease=lease, yield_seconds=300, clock=clock
    )
    eng._step()
    assert ticks == [1]

    clock.advance(300)
    eng._step()

    # A dedicated worker blocked on pg_advisory_lock only ever gets in if the
    # API lets go; without this it would wait until the API restarted.
    assert lease.released == 1
    assert eng.holds_lease is False
    assert ticks == [1]


def test_the_lease_is_not_yielded_before_the_interval_elapses():
    lease = FakeLease()
    ticks = []
    clock = FakeClock()
    eng = engine(
        tick=lambda: ticks.append(1), lease=lease, yield_seconds=300, clock=clock
    )

    for _ in range(5):
        clock.advance(59)
        eng._step()

    # Dropping and retaking the lease on every tick would be a reconnect per
    # second, and a window each time for a second writer to slip in.
    assert lease.released == 0
    assert len(ticks) == 5


def test_yielding_is_off_when_the_yield_interval_is_zero():
    lease = FakeLease()
    eng = engine(lease=lease, yield_seconds=0)

    for _ in range(5):
        eng._step()

    assert lease.released == 0


def test_run_survives_failing_ticks():
    lease = FakeLease()
    calls = []

    def explode():
        calls.append(1)
        raise RuntimeError("cycle blew up")

    eng = InlineCognition(
        tick=explode, lease=lease, tick_sleep=0, retry_seconds=0, yield_seconds=0
    )

    def stop_soon():
        while len(calls) < 3:
            pass
        eng._stop.set()

    watcher = threading.Thread(target=stop_soon, daemon=True)
    watcher.start()
    eng.run()
    watcher.join(timeout=2)

    # A thread that dies on one bad cycle takes cognition down until the next
    # deploy, and leaves the lease held so nothing else can take over.
    assert len(calls) >= 3
    assert lease.released >= 1


def test_stop_releases_the_lease():
    lease = FakeLease()
    eng = engine(lease=lease)
    eng._step()

    eng.stop(timeout=1)

    assert lease.released >= 1
    assert eng.holds_lease is False


def test_start_and_stop_run_a_real_thread():
    lease = FakeLease()
    ticked = threading.Event()
    eng = InlineCognition(
        tick=lambda: ticked.set() or {"processed_this_call": 1},
        lease=lease,
        tick_sleep=0,
        retry_seconds=0,
        yield_seconds=0,
    )

    eng.start()
    assert ticked.wait(timeout=5) is True
    assert eng.running is True
    eng.stop(timeout=5)

    assert eng.running is False
    assert lease.released >= 1


def test_idle_endogenous_ticks_are_throttled():
    # Endogenous thought reports nothing processed. Treating that as work
    # would spin a core flat out generating self-stimuli.
    assert _did_work({"processed_this_call": 0}) is False
    assert _did_work({"processed_this_call": 2}) is True
    assert _did_work(None) is False
    assert _did_work(True) is True


def test_start_inline_cognition_returns_none_when_not_requested(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BRAIN_WORKER_DATABASE_URL", raising=False)

    assert start_inline_cognition(lambda: None) is None


def test_constructing_a_test_client_does_not_start_cognition(monkeypatch):
    import apps.api.main as api

    started = []
    monkeypatch.setattr(api, "start_inline_cognition", lambda tick: started.append(tick))

    TestClient(api.app).get("/health")

    # The suite constructs TestClient without entering it 26 times; if that
    # ran the lifespan, every one of those tests would start a cognition
    # thread against whatever DATABASE_URL happened to be set.
    assert started == []


def test_serving_the_app_starts_and_stops_cognition(monkeypatch):
    import apps.api.main as api

    class Recorder:
        def __init__(self):
            self.stopped = False

        def stop(self, timeout=5.0):
            self.stopped = True

    recorder = Recorder()
    started = []

    def fake_start(tick):
        started.append(tick)
        return recorder

    monkeypatch.setattr(api, "start_inline_cognition", fake_start)

    with TestClient(api.app) as client:
        client.get("/health")
        assert len(started) == 1
        assert recorder.stopped is False

    assert recorder.stopped is True


def test_the_lifespan_ticks_the_api_heartbeat(monkeypatch):
    import apps.api.main as api

    captured = {}

    def capture(tick):
        captured["tick"] = tick
        return None

    monkeypatch.setattr(api, "start_inline_cognition", capture)
    ticks = []
    monkeypatch.setattr(
        api.heartbeat, "tick", lambda **kwargs: ticks.append(kwargs) or {}
    )

    with TestClient(api.app):
        pass

    captured["tick"]()

    # The API must drive the heartbeat that its own /health and /runner/status
    # report on, not a second one nobody reads.
    assert ticks == [{"max_items": 1}]
