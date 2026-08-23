from datetime import timedelta
from uuid import uuid4

from brain.attribution import OutcomeAttribution
from brain.domain import Edge, Node, Outcome
from brain.events import BrainEvent
from brain.memory import InMemoryBrainStore
from brain.prediction import PredictionEngine, PredictionStatus
from brain.projections import default_projection_engine, incremental_checkpoint
from brain.working_memory import WorkingMemory


def test_working_memory_capacity_and_eviction():
    wm = WorkingMemory(capacity=2)
    s1, e1 = wm.encode({"k": 1}, salience=0.3)
    s2, e2 = wm.encode({"k": 2}, salience=0.9)
    s3, e3 = wm.encode({"k": 3}, salience=0.5)
    assert e1 == [] and e2 == []
    assert len(e3) == 1
    assert e3[0].id == s1.id
    assert wm.size == 2
    ids = {s.id for s in wm.snapshot()}
    assert s2.id in ids and s3.id in ids


def test_working_memory_decay_drops_weak_items():
    wm = WorkingMemory(capacity=5)
    wm.encode({"a": 1}, salience=0.02)
    wm.encode({"b": 1}, salience=0.9)
    dropped = wm.decay(rate=0.5)
    assert any(s.content.get("a") == 1 for s in dropped)
    assert all(s.salience > 0.01 for s in wm.snapshot())


def test_prediction_resolve_computes_error():
    engine = PredictionEngine()
    pred = engine.create(
        "Market expands",
        expected_value=1.0,
        confidence=0.8,
        horizon=timedelta(days=1),
    )
    assert pred.status is PredictionStatus.OPEN
    outcome = Outcome(
        action_id=uuid4(),
        value_created=0.2,
        operator_time_cost=0.1,
        prediction_accuracy=0.0,
    )
    resolution = engine.resolve(pred, outcome)
    assert resolution.prediction.status is PredictionStatus.RESOLVED
    assert resolution.error == abs(0.2 - 1.0)
    assert resolution.signed_error < 0
    assert resolution.reward_signal < 0


def test_outcome_attribution_reinforces_edges_on_positive_reward():
    a = Node("entity", "supplier")
    b = Node("entity", "buyer")
    edge = Edge(a.id, b.id, "supplies", weight=0.5)
    outcome = Outcome(
        action_id=uuid4(),
        value_created=1.0,
        operator_time_cost=0.05,
        prediction_accuracy=1.0,
        legal_risk=0.0,
        edge_ids=[edge.id],
        source_keys=["regulator"],
    )
    result = OutcomeAttribution().attribute(outcome, edges=[edge], source_keys=["regulator"])
    assert result.attribution.reward_score > 0
    assert result.updated_edges[0].weight > 0.5
    assert result.rewire_events
    assert str(edge.id) in result.attribution.edge_deltas
    assert result.attribution.edge_deltas[str(edge.id)] > 0
    assert outcome.id in result.rewire_events[0].evidence_ids


def test_outcome_attribution_weakens_edges_on_negative_reward():
    a = Node("entity", "x")
    b = Node("entity", "y")
    edge = Edge(a.id, b.id, "related_to", weight=0.4)
    outcome = Outcome(
        action_id=uuid4(),
        value_created=-1.0,
        operator_time_cost=1.0,
        prediction_accuracy=0.0,
        legal_risk=1.0,
    )
    result = OutcomeAttribution(edge_learn_rate=0.1).attribute(outcome, edges=[edge])
    assert result.attribution.reward_score < 0
    if result.updated_edges:
        assert result.updated_edges[0].weight < 0.4
    else:
        assert edge.id in result.pruned_edge_ids


def test_attribution_with_prediction_emits_closed_loop():
    engine = PredictionEngine()
    a = Node("entity", "a")
    b = Node("entity", "b")
    edge = Edge(a.id, b.id, "signals", weight=0.55)
    pred = engine.create(
        "Deal closes",
        expected_value=0.8,
        confidence=0.7,
        edge_ids=[edge.id],
        source_keys=["crm"],
    )
    outcome = Outcome(
        action_id=uuid4(),
        value_created=1.0,
        operator_time_cost=0.1,
        prediction_accuracy=1.0,
        prediction_id=pred.id,
        edge_ids=[edge.id],
    )
    learning = OutcomeAttribution().attribute(outcome, edges=[edge], prediction=pred)
    assert learning.resolution is not None
    assert learning.resolution.prediction.status is PredictionStatus.RESOLVED
    assert learning.attribution.prediction_id == pred.id
    assert learning.updated_edges[0].weight > edge.weight


class MemoryCheckpointStore:
    def __init__(self) -> None:
        self.saved: dict | None = None

    def save(self, projection_name, *, last_event_id, event_count, state):
        self.saved = {
            "projection_name": projection_name,
            "last_event_id": last_event_id,
            "event_count": event_count,
            "state": state,
        }

    def get(self, projection_name: str):
        if self.saved and self.saved["projection_name"] == projection_name:
            return self.saved
        return None


def test_incremental_checkpoint_applies_only_new_events():
    store = InMemoryBrainStore()
    checkpoint = MemoryCheckpointStore()
    engine = default_projection_engine()

    e1 = BrainEvent("belief.created", "belief", uuid4(), {"statement": "A", "confidence": 0.4})
    store.append(e1)
    state1 = incremental_checkpoint(engine, store, checkpoint)
    assert state1["event_count"] == 1
    assert checkpoint.saved["event_count"] == 1

    e2 = BrainEvent(
        "belief.updated",
        "belief",
        e1.aggregate_id,
        {"confidence": 0.7, "statement": "A"},
    )
    store.append(e2)
    state2 = incremental_checkpoint(engine, store, checkpoint)
    assert state2["event_count"] == 2
    assert state2["beliefs"][e1.aggregate_id]["confidence"] == 0.7
    full = engine.replay(store.read_all())
    assert full["event_count"] == state2["event_count"]
    assert full["beliefs"][e1.aggregate_id]["confidence"] == 0.7
