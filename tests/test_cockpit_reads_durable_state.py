"""The cockpit must report the system, not the process that answers.

Two independent defects made the Observatory render zeros while the Brain was
working, and neither was visible from inside apps/api:

* `/health` and `/runner/status` returned `heartbeat.status()` -- the counters
  of an untouched HeartbeatService owned by the API process. All cognition runs
  in apps/worker, in a different process, against a different instance. The
  API's `ticks` were therefore structurally always 0, so the cockpit showed
  CYCLE 0 no matter how much work the worker had done.

* `PostgresBrainStore.hydrate()` runs once, in the constructor. A long-lived API
  process answered every belief read from the snapshot it booted with, so
  beliefs the worker wrote afterwards stayed invisible until a redeploy.

Together they guarantee an all-zero cockpit over a perfectly healthy system,
which is exactly what a live screenshot showed: CYCLE 0, INBOX 0 active,
BELIEF LATTICE 0 UNFORMED.
"""

from __future__ import annotations

import apps.api.main as api
from brain.adapters.brain_store import PostgresBrainStore


class _CountingStore:
    """Stands in for PostgresBrainStore without a live database."""

    def __init__(self, counts: dict[str, int] | None = None) -> None:
        self._counts = counts or {}
        self.counter_calls = 0
        self.counter_ttls: list[float] = []
        self.refresh_calls: list[float] = []

    def cognition_counters(self, max_age_seconds: float = 0.0) -> dict[str, int]:
        self.counter_calls += 1
        self.counter_ttls.append(max_age_seconds)
        return dict(self._counts)

    def refresh_if_stale(self, max_age_seconds: float) -> bool:
        self.refresh_calls.append(max_age_seconds)
        return True


# --- durable counters replace the never-ticked local heartbeat -------------


def test_cognition_status_reports_durable_counts_not_process_counters(monkeypatch):
    monkeypatch.setattr(
        api,
        "_brain_store",
        _CountingStore({"cycle.completed": 412, "observation.received": 97, "signal.enqueued": 130}),
    )
    status = api._cognition_status()

    assert status["ticks"] == 412, "ticks must come from cycle.completed in the shared stream"
    assert status["total_processed"] == 97
    assert status["signals_enqueued"] == 130
    assert status["source"] == "durable"


def test_process_local_heartbeat_is_the_fallback_without_a_durable_store(monkeypatch):
    monkeypatch.setattr(api, "_brain_store", None)
    status = api._cognition_status()
    assert "source" not in status
    assert "ticks" in status, "in-memory deployments still report something"


def test_a_broken_counter_query_degrades_instead_of_failing_health(monkeypatch):
    class Exploding(_CountingStore):
        def cognition_counters(self, max_age_seconds: float = 0.0):
            raise RuntimeError("database went away")

    monkeypatch.setattr(api, "_brain_store", Exploding())
    status = api._cognition_status()
    assert "ticks" in status, "/health must still answer when the count query fails"
    assert status.get("source") != "durable"


def test_counters_are_one_indexed_grouped_query_not_a_full_scan():
    """#75 removed a full brain_events scan from /health; do not reintroduce one."""
    import inspect

    source = inspect.getsource(PostgresBrainStore._count_cognition_events)
    assert "group by event_type" in source
    assert "where event_type = any(" in source
    assert "read_all" not in source, "counting must not materialise the event stream"
    # cognition_counters caches on top of it; the guard belongs on whichever
    # method actually issues the query.
    assert "self._count_cognition_events()" in inspect.getsource(
        PostgresBrainStore.cognition_counters
    )


def test_counted_event_types_are_ones_cognition_actually_emits():
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    emitted: set[str] = set()
    for name in ("cycle.py", "heartbeat.py", "runner.py"):
        path = root / "brain" / name
        if path.exists():
            emitted.update(
                re.findall(r'"([a-z_]+\.[a-z_]+)"', path.read_text(encoding="utf-8"))
            )
    assert emitted, "expected to find event type literals in the cognition modules"
    for event_type in PostgresBrainStore.COGNITION_EVENT_TYPES:
        assert event_type in emitted, f"{event_type} is counted but never emitted"


# --- reads see what the worker wrote --------------------------------------


def test_reads_refresh_the_boot_snapshot(monkeypatch):
    store = _CountingStore()
    monkeypatch.setattr(api, "_brain_store", store)
    api._refresh_reads()
    assert store.refresh_calls, "belief reads must refresh the cached projection"


def test_refresh_ttl_defaults_to_the_observatory_poll_interval(monkeypatch):
    monkeypatch.delenv("BRAIN_READ_REFRESH_SECONDS", raising=False)
    assert api._read_refresh_seconds() == 5.0


def test_refresh_ttl_is_configurable_and_survives_garbage(monkeypatch):
    monkeypatch.setenv("BRAIN_READ_REFRESH_SECONDS", "0.5")
    assert api._read_refresh_seconds() == 0.5
    monkeypatch.setenv("BRAIN_READ_REFRESH_SECONDS", "not-a-number")
    assert api._read_refresh_seconds() == 5.0, "a bad value must not break every read"


def test_a_failing_refresh_serves_the_cached_projection(monkeypatch):
    class Exploding(_CountingStore):
        def refresh_if_stale(self, max_age_seconds):
            raise RuntimeError("pool exhausted")

    monkeypatch.setattr(api, "_brain_store", Exploding())
    api._refresh_reads()  # must not raise


def test_refresh_is_ttl_bounded_rather_than_per_request():
    """A hydrate on every read would put the projection load on every poll."""
    import inspect

    source = inspect.getsource(PostgresBrainStore.refresh_if_stale)
    assert "max_age_seconds" in source
    assert "monotonic" in source
    assert "_refresh_lock" in source, "concurrent readers must not stampede hydrate()"


# --- the routes must actually use them ------------------------------------
#
# Testing the helpers alone passed even with the route wiring reverted, which
# is the whole failure mode: the helpers were never the broken part, the
# routes' choice of source was.


def _client():
    from fastapi.testclient import TestClient

    from tests.conftest import TEST_API_KEY

    return TestClient(api.app, headers={"x-api-key": TEST_API_KEY})


def test_health_endpoint_serves_durable_ticks(monkeypatch):
    monkeypatch.setattr(api, "_brain_store", _CountingStore({"cycle.completed": 77}))
    body = _client().get("/health").json()
    assert body["heartbeat"]["ticks"] == 77, (
        "/health must report the shared event stream, not this process's counters"
    )


def test_runner_status_endpoint_serves_durable_ticks(monkeypatch):
    monkeypatch.setattr(api, "_brain_store", _CountingStore({"cycle.completed": 55}))
    body = _client().get("/runner/status").json()
    assert body["ticks"] == 55
    assert body["source"] == "durable"


def test_belief_reads_refresh_before_answering(monkeypatch):
    store = _CountingStore()
    monkeypatch.setattr(api, "_brain_store", store)
    _client().get("/beliefs")
    assert store.refresh_calls, "GET /beliefs must refresh before reading the projection"


def test_health_and_runner_refresh_before_answering(monkeypatch):
    store = _CountingStore({"cycle.completed": 1})
    monkeypatch.setattr(api, "_brain_store", store)
    client = _client()
    client.get("/health")
    client.get("/runner/status")
    assert len(store.refresh_calls) >= 2
