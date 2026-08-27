"""A deployed worker must actually think.

The live cockpit showed 5 ingested signals, 0 beliefs and CYCLE 0: signals had
arrived and nothing had ever processed them. The cause was the worker's default
mode, not the cognition code.

`Dockerfile.worker` pinned `BRAIN_WORKER_MODE=temporal`, and `main()` routes
that to `run_temporal_worker()`, which dials
`TEMPORAL_ADDRESS or TEMPORAL_HOST or "localhost:7233"`. Nothing listens on the
worker container's own loopback, so a deployment without a Temporal server
raised out of `asyncio.run`, exited, restarted, and dialled itself again -- a
crash loop that never ran a single cognitive tick. From the cockpit that is
indistinguishable from a healthy Brain with nothing to do.
"""

from __future__ import annotations

from pathlib import Path

import apps.worker.main as worker

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- the image must not ship a mode it cannot satisfy ---------------------


def test_worker_image_does_not_pin_temporal_mode():
    dockerfile = (REPO_ROOT / "Dockerfile.worker").read_text(encoding="utf-8")
    assert "BRAIN_WORKER_MODE=temporal" not in dockerfile, (
        "the image must not default to a mode that requires a Temporal server "
        "it has no address for"
    )


def test_worker_image_still_runs_the_worker_entrypoint():
    dockerfile = (REPO_ROOT / "Dockerfile.worker").read_text(encoding="utf-8")
    assert "apps.worker.main" in dockerfile


# --- localhost is never a configured Temporal endpoint --------------------


def test_unset_temporal_is_not_treated_as_configured(monkeypatch):
    monkeypatch.delenv("TEMPORAL_ADDRESS", raising=False)
    monkeypatch.delenv("TEMPORAL_HOST", raising=False)
    assert worker.temporal_address() == ""


def test_configured_temporal_is_reported(monkeypatch):
    monkeypatch.delenv("TEMPORAL_HOST", raising=False)
    monkeypatch.setenv("TEMPORAL_ADDRESS", "temporal.internal:7233")
    assert worker.temporal_address() == "temporal.internal:7233"


def test_blank_temporal_address_is_not_configured(monkeypatch):
    monkeypatch.setenv("TEMPORAL_ADDRESS", "   ")
    monkeypatch.delenv("TEMPORAL_HOST", raising=False)
    assert worker.temporal_address() == ""


# --- main() must reach cognition in every non-verify path -----------------


def _capture(monkeypatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(worker, "run_cognition_loop", lambda: calls.append("cognition"))
    return calls


def test_default_mode_runs_cognition(monkeypatch):
    monkeypatch.delenv("BRAIN_WORKER_MODE", raising=False)
    monkeypatch.delenv("TEMPORAL_ADDRESS", raising=False)
    monkeypatch.delenv("TEMPORAL_HOST", raising=False)
    calls = _capture(monkeypatch)
    worker.main()
    assert calls == ["cognition"]


def test_temporal_mode_without_an_address_falls_back_to_cognition(monkeypatch):
    """The exact deployed configuration that produced CYCLE 0."""
    monkeypatch.setenv("BRAIN_WORKER_MODE", "temporal")
    monkeypatch.delenv("TEMPORAL_ADDRESS", raising=False)
    monkeypatch.delenv("TEMPORAL_HOST", raising=False)

    def explode() -> None:
        raise AssertionError("must not dial Temporal without an address")

    monkeypatch.setattr(worker, "run_temporal_worker", explode)
    calls = _capture(monkeypatch)
    worker.main()
    assert calls == ["cognition"]


def test_temporal_mode_with_an_address_still_runs_temporal(monkeypatch):
    monkeypatch.setenv("BRAIN_WORKER_MODE", "temporal")
    monkeypatch.setenv("TEMPORAL_ADDRESS", "temporal.internal:7233")
    ran: list[str] = []

    async def fake_worker() -> None:
        ran.append("temporal")

    monkeypatch.setattr(worker, "run_temporal_worker", fake_worker)
    calls = _capture(monkeypatch)
    worker.main()
    assert ran == ["temporal"]
    assert calls == [], "a reachable Temporal must not be bypassed"


def test_an_unreachable_temporal_degrades_instead_of_crash_looping(monkeypatch):
    monkeypatch.setenv("BRAIN_WORKER_MODE", "temporal")
    monkeypatch.setenv("TEMPORAL_ADDRESS", "temporal.internal:7233")

    async def refuse() -> None:
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(worker, "run_temporal_worker", refuse)
    calls = _capture(monkeypatch)
    worker.main()
    assert calls == ["cognition"], (
        "a worker that cannot reach its orchestrator must still think"
    )


def test_verify_mode_is_unchanged(monkeypatch):
    monkeypatch.setenv("BRAIN_WORKER_MODE", "verify")
    monkeypatch.setattr(worker, "worker_database_url", lambda: "postgresql://x/y")
    calls = _capture(monkeypatch)
    worker.main()
    assert calls == [], "verify must not start a cognition loop"


def test_maintenance_mode_still_runs_cognition(monkeypatch):
    monkeypatch.setenv("BRAIN_WORKER_MODE", "maintenance")
    monkeypatch.delenv("TEMPORAL_ADDRESS", raising=False)
    monkeypatch.delenv("TEMPORAL_HOST", raising=False)
    calls = _capture(monkeypatch)
    worker.main()
    assert calls == ["cognition"]


def test_no_lease_is_taken_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BRAIN_WORKER_DATABASE_URL", raising=False)

    # There is no shared store to double-write and no database to hold a lock
    # in; requiring one would stop an in-memory worker from starting at all.
    assert worker.acquire_cognition_lease() is None


def test_the_worker_waits_for_the_lease_instead_of_polling(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")
    calls = []

    class FakeLease:
        def __init__(self, dsn):
            calls.append(dsn)

        def acquire(self, *, blocking=False):
            calls.append(blocking)
            return True

    monkeypatch.setattr("brain.cognition_lease.CognitionLease", FakeLease)
    monkeypatch.setattr(worker, "_cognition_lease", None, raising=False)

    lease = worker.acquire_cognition_lease()

    assert calls == ["postgres:///brain", True]
    # Held module-level: a garbage-collected lease closes its connection,
    # which releases the lock and re-permits a second writer.
    assert worker._cognition_lease is lease


def test_the_worker_takes_the_lease_before_it_starts_thinking(monkeypatch):
    order = []
    monkeypatch.setattr(
        worker, "acquire_cognition_lease", lambda: order.append("lease")
    )
    monkeypatch.setattr(
        worker,
        "run_forever_with_maintenance",
        lambda **kwargs: order.append("loop"),
    )

    worker.run_cognition_loop()

    assert order == ["lease", "loop"]


def test_the_worker_thinks_anyway_when_the_lease_cannot_be_taken(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres:///brain")

    class RefusingLease:
        def __init__(self, dsn):
            pass

        def acquire(self, *, blocking=False):
            return False

    monkeypatch.setattr("brain.cognition_lease.CognitionLease", RefusingLease)

    # A worker that exits here is a Brain that stops thinking because of a
    # lock, which is strictly worse than the duplicate cycles it prevents.
    assert worker.acquire_cognition_lease() is None
