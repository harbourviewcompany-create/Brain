"""SLICE-ALWAYS-ON-P0 acceptance tests.

Traceability:
- SRC-BRAIN-ALWAYS-ON-20260827
- REQ-ALWAYS-ON-002 through REQ-ALWAYS-ON-005
"""

from __future__ import annotations

from uuid import UUID, uuid4

from brain.adapters.cognition import PostgresSensoryInbox
from brain.heartbeat import HeartbeatService, build_default_heartbeat
from brain.memory import InMemoryBrainStore
from brain.sensory_inbox import InboxItem


class _FakeDurableInbox:
    def __init__(self, pool) -> None:
        self.pool = pool
        self.enqueued: list[dict] = []

    def enqueue(self, *, source_key: str, content: str, claim: str, payload=None) -> UUID:
        item_id = uuid4()
        self.enqueued.append(
            {
                "id": item_id,
                "source_key": source_key,
                "content": content,
                "claim": claim,
                "payload": dict(payload or {}),
            }
        )
        return item_id

    def claim_next(self):
        return None

    def complete(self, _item_id) -> None:
        return None

    def fail(self, _item_id, _error, *, retry=True) -> None:
        return None

    def stats(self) -> dict[str, int]:
        return {
            "pending": len(self.enqueued),
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "total": len(self.enqueued),
        }


class _FakeDurableRuns:
    def __init__(self, pool) -> None:
        self.pool = pool
        self.saved: list[tuple] = []

    def save(self, inbox_id, result) -> None:
        self.saved.append((inbox_id, result))


class _FakeLearningStore:
    def __init__(self, pool) -> None:
        self.pool = pool


class _Cursor:
    def __init__(self, rows) -> None:
        self.rows = rows
        self.executed = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, _params=None) -> None:
        self.executed = str(query)

    def fetchall(self):
        return list(self.rows)


class _Connection:
    def __init__(self, rows) -> None:
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self, **_kwargs):
        return _Cursor(self.rows)


class _Pool:
    def __init__(self, rows=None) -> None:
        self.rows = list(rows or [])

    def connection(self):
        return _Connection(self.rows)


def _postgres_marked_memory_store() -> tuple[InMemoryBrainStore, _Pool]:
    """Use the real event-store behavior while presenting a shared pool contract."""
    store = InMemoryBrainStore()
    pool = _Pool()
    store.pool = pool
    return store, pool


def test_postgres_sensory_inbox_exposes_common_queue_health_contract():
    # REQ-ALWAYS-ON-002 / REQ-OBS-001
    inbox = PostgresSensoryInbox(
        _Pool(
            [
                {"status": "pending", "count": 2},
                {"status": "processing", "count": 1},
                {"status": "completed", "count": 7},
                {"status": "failed", "count": 3},
            ]
        )
    )

    assert inbox.stats() == {
        "pending": 2,
        "processing": 1,
        "completed": 7,
        "failed": 3,
        "total": 13,
    }
    assert inbox.pending_count() == 2


def test_postgres_marked_heartbeat_selects_one_durable_queue_and_cycle_store(monkeypatch):
    # REQ-ALWAYS-ON-002 / REQ-ALWAYS-ON-003
    import brain.adapters.cognition as cognition_adapters

    monkeypatch.setattr(cognition_adapters, "PostgresSensoryInbox", _FakeDurableInbox)
    monkeypatch.setattr(cognition_adapters, "CognitiveCycleRunStore", _FakeDurableRuns)

    store, pool = _postgres_marked_memory_store()
    heartbeat = HeartbeatService(event_store=store, learning=None)

    assert isinstance(heartbeat.inbox, _FakeDurableInbox)
    assert heartbeat.inbox.pool is pool
    assert isinstance(heartbeat._runner.cycle_runs._durable, _FakeDurableRuns)
    assert heartbeat._runner.cycle_runs._durable.pool is pool

    result = heartbeat.perceive(
        content="A new observation arrived",
        claim="World state changed",
        source_key="test-source",
    )

    assert isinstance(result, InboxItem)
    assert len(heartbeat.inbox.enqueued) == 1
    assert result.id == heartbeat.inbox.enqueued[0]["id"]
    assert heartbeat.status()["inbox"]["pending"] == 1


def test_default_heartbeat_uses_durable_learning_stores_when_pool_exists(monkeypatch):
    # REQ-ALWAYS-ON-005
    import brain.adapters.cognition as cognition_adapters
    import brain.adapters.learning_store as learning_adapters

    monkeypatch.setattr(cognition_adapters, "PostgresSensoryInbox", _FakeDurableInbox)
    monkeypatch.setattr(cognition_adapters, "CognitiveCycleRunStore", _FakeDurableRuns)
    monkeypatch.setattr(learning_adapters, "PostgresPredictionStore", _FakeLearningStore)
    monkeypatch.setattr(learning_adapters, "PostgresEdgeStore", _FakeLearningStore)
    monkeypatch.setattr(learning_adapters, "PostgresAttributionStore", _FakeLearningStore)
    monkeypatch.setattr(learning_adapters, "PostgresSourceStore", _FakeLearningStore)

    store, pool = _postgres_marked_memory_store()
    heartbeat = build_default_heartbeat(event_store=store)

    assert heartbeat.learning is not None
    assert isinstance(heartbeat.learning.predictions, _FakeLearningStore)
    assert isinstance(heartbeat.learning.edges, _FakeLearningStore)
    assert isinstance(heartbeat.learning.attributions, _FakeLearningStore)
    assert isinstance(heartbeat.learning.sources, _FakeLearningStore)
    assert heartbeat.learning.predictions.pool is pool


def test_foundational_bootstrap_is_idempotent_by_statement():
    # REQ-ALWAYS-ON-004
    heartbeat = build_default_heartbeat()
    first_count = heartbeat.bootstrap_mind()
    first_statements = [
        str(getattr(belief, "statement", "")).strip()
        for belief in heartbeat._cycle._belief_cache.values()
    ]

    second_count = heartbeat.bootstrap_mind()
    second_statements = [
        str(getattr(belief, "statement", "")).strip()
        for belief in heartbeat._cycle._belief_cache.values()
    ]

    assert second_count == first_count
    assert second_statements == first_statements
    assert len(second_statements) == len(set(second_statements))
