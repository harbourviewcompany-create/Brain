"""Heartbeat + sensory inbox + closed perception→learning loop."""

from __future__ import annotations

from brain.adapters.learning_store import InMemoryLearningStore
from brain.domain import Edge, Node
from brain.heartbeat import HeartbeatService, build_default_heartbeat
from brain.learning import LearningService
from brain.memory import InMemoryBrainStore
from brain.sensory_inbox import InMemorySensoryInbox


def test_inbox_enqueue_claim_complete():
    inbox = InMemorySensoryInbox()
    item = inbox.enqueue(source_key="src", content="hello", claim="world")
    assert inbox.pending_count() == 1
    claimed = inbox.claim_next()
    assert claimed is not None
    assert claimed["id"] == item.id
    assert claimed["content"] == "hello"
    assert inbox.claim_next() is None
    inbox.complete(item.id)
    assert inbox.stats()["completed"] == 1


def test_heartbeat_perceive_and_tick_updates_belief():
    store = InMemoryBrainStore()
    learning = LearningService(store, predictions=None)
    hb = HeartbeatService(event_store=store, learning=learning, auto_predict=False)

    hb.perceive(
        content="Regulator published new guidance",
        claim="Market rules tightened",
        source_key="regulator",
        source_reliability=0.9,
        novelty=0.8,
        urgency=0.6,
        belief_confidence=0.55,
    )
    assert hb.inbox.pending_count() == 1

    result = hb.tick(max_items=1)
    assert result["processed_this_call"] == 1
    assert result["total_processed"] == 1
    assert result["cycles"][0]["attention_score"] is not None
    assert result["inbox"]["completed"] == 1

    types = {e.event_type for e in store.events}
    assert "observation.received" in types
    assert "attention.scored" in types
    assert "evidence.created" in types
    assert "belief.created" in types or "belief.updated" in types
    assert "cycle.completed" in types
    assert "signal.enqueued" in types


def test_closed_loop_predict_and_outcome_rewire():
    store = InMemoryBrainStore()
    lstore = InMemoryLearningStore()
    a, b = Node("entity", "supplier"), Node("entity", "buyer")
    edge = Edge(a.id, b.id, "supplies", weight=0.4)
    lstore.upsert_edge(edge)

    learning = LearningService(
        store,
        predictions=lstore,
        edges=lstore,
        attributions=lstore,
        sources=lstore,
    )
    hb = HeartbeatService(event_store=store, learning=learning, auto_predict=True)

    hb.perceive(
        content="Buyer signed LOI",
        claim="Deal advances",
        source_key="crm",
        source_reliability=0.85,
        novelty=0.7,
        urgency=0.8,
        commercial_upside=0.9,
        belief_confidence=0.7,
    )
    tick = hb.tick(max_items=1)
    assert tick["processed_this_call"] == 1
    cycle = tick["cycles"][0]
    assert "prediction_id" in cycle

    from uuid import UUID

    result = hb.resolve_with_outcome(
        prediction_id=UUID(cycle["prediction_id"]),
        value_created=1.0,
        prediction_accuracy=0.9,
        edge_ids=[edge.id],
        source_keys=["crm"],
    )
    assert result.attribution.reward_score > 0
    updated = lstore.get_edge(edge.id)
    assert updated is not None
    assert updated.weight > 0.4


def test_build_default_heartbeat():
    hb = build_default_heartbeat()
    assert hb.status()["ticks"] == 0
    hb.perceive(content="x", claim="y")
    assert hb.tick()["processed_this_call"] == 1
