"""The cognition worker must write where the API reads.

`build_runner()` previously called `build_default_heartbeat()` with no event
store, so the continuous loop ran on InMemoryBrainStore regardless of
DATABASE_URL: every belief, prediction and cycle result it produced was
invisible to the API and discarded on restart. `worker_database_url()` -- and
the tenant-RLS role topology it enforces -- ran only under
BRAIN_WORKER_MODE=verify, so CI was proving out a database the worker never
opened.
"""

from __future__ import annotations

import apps.worker.main as worker
from brain.memory import InMemoryBrainStore


class _RecordingStore(InMemoryBrainStore):
    """Stands in for PostgresBrainStore without needing a live database."""


def test_build_brain_store_returns_none_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("BRAIN_WORKER_DATABASE_URL", raising=False)
    assert worker.build_brain_store() is None


def test_build_brain_store_validates_the_role_topology_before_connecting(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://brain:brain@127.0.0.1:5432/brain")
    monkeypatch.setattr(worker, "_verified_worker_dsn", None)

    calls: list[str] = []

    def fake_worker_database_url() -> str:
        calls.append("validated")
        return "postgresql://brain:brain@127.0.0.1:5432/brain"

    monkeypatch.setattr(worker, "worker_database_url", fake_worker_database_url)

    created: list[str] = []

    class FakePostgresBrainStore(InMemoryBrainStore):
        def __init__(self, dsn: str) -> None:
            super().__init__()
            created.append(dsn)

    import brain.adapters.brain_store as adapter

    monkeypatch.setattr(adapter, "PostgresBrainStore", FakePostgresBrainStore)

    store = worker.build_brain_store()

    assert calls == ["validated"], "the DSN must be validated before a pool is opened"
    assert created == ["postgresql://brain:brain@127.0.0.1:5432/brain"]
    assert isinstance(store, FakePostgresBrainStore)


def test_runner_uses_the_durable_store_when_one_is_configured(monkeypatch):
    durable = _RecordingStore()
    monkeypatch.setattr(worker, "build_brain_store", lambda: durable)

    runner = worker.build_runner(enable_endogenous=False)

    assert runner.cycle.event_store is durable, "cognition must run against the durable store"


def test_runner_falls_back_to_memory_and_says_so(monkeypatch, caplog):
    monkeypatch.setattr(worker, "build_brain_store", lambda: None)

    with caplog.at_level("WARNING", logger="brain.worker"):
        runner = worker.build_runner(enable_endogenous=False)

    assert runner.cycle.event_store is not None
    assert any(
        "in-memory" in record.getMessage() for record in caplog.records
    ), "an ephemeral worker must announce itself, not degrade silently"


def test_learning_shares_the_runner_store(monkeypatch):
    durable = _RecordingStore()
    monkeypatch.setattr(worker, "build_brain_store", lambda: durable)
    monkeypatch.setattr(worker, "_runner", None)
    monkeypatch.setattr(worker, "_learning", None)

    learning = worker._learning_singleton()

    assert learning is not None
    assert learning.event_store is durable, "attribution must be written where cognition is"
