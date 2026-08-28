from __future__ import annotations

import inspect
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.cockpit_read_routes import register_cockpit_read_routes
from brain.adapters.postgres import PostgresEventStore
from brain.domain import Belief, Evidence
from brain.events import BrainEvent
from brain.memory import InMemoryBrainStore


class _LearningStore:
    source_scores: dict[str, float] = {}

    def list_edges(self):
        return []


def _client(store) -> TestClient:
    app = FastAPI()
    learning_store = _LearningStore()
    api_module = SimpleNamespace(
        runtime=SimpleNamespace(store=store),
        learning=SimpleNamespace(edges=None),
        _learning_store=learning_store,
    )
    register_cockpit_read_routes(app, api_module=api_module)
    return TestClient(app)


def _seeded_store() -> tuple[InMemoryBrainStore, str, str, str]:
    store = InMemoryBrainStore()
    cycle_id = uuid4()
    observation_id = uuid4()
    evidence = Evidence(
        claim="Verified source says the rule changed",
        source_id="regulator",
        reliability=0.94,
        observation_id=observation_id,
    )
    belief = Belief(
        statement="The rule changed",
        confidence=0.81,
        supporting_evidence={evidence.id},
    )
    store.save(evidence)
    store.save(belief)

    inbox_id = uuid4()
    store.append(
        BrainEvent(
            "signal.enqueued",
            "sensory_inbox",
            inbox_id,
            {
                "source_key": "operator",
                "content": "Inspect the rule change",
                "claim": "Inspect the rule change",
                "payload": {
                    "source_reliability": 0.7,
                    "novelty": 0.5,
                    "urgency": 0.3,
                    "metadata": {
                        "operator_command": True,
                        "command_mode": "inspect",
                        "ui_surface": "living_brain",
                    },
                },
            },
            correlation_id=cycle_id,
        )
    )
    store.append(
        BrainEvent(
            "memory.working_stored",
            "observation",
            observation_id,
            {
                "content": "Inspect the rule change",
                "salience": 0.72,
                "slot_id": str(uuid4()),
                "capacity": 7,
                "source_event_id": str(observation_id),
            },
            correlation_id=cycle_id,
        )
    )
    store.append(
        BrainEvent(
            "cycle.completed",
            "cognitive_cycle",
            cycle_id,
            {
                "observation_id": str(observation_id),
                "belief_id": str(belief.id),
                "evidence_id": str(evidence.id),
                "attention_score": 0.72,
                "working_memory_size": 4,
                "evicted_count": 1,
            },
            correlation_id=cycle_id,
        )
    )

    outcome_id = uuid4()
    prediction_id = uuid4()
    store.append(
        BrainEvent(
            "outcome.recorded",
            "outcome",
            outcome_id,
            {
                "action_id": str(uuid4()),
                "value_created": 0.8,
                "operator_time_cost": 0.1,
                "prediction_accuracy": 0.9,
                "trust_impact": 0.05,
                "legal_risk": 0.0,
                "prediction_id": str(prediction_id),
                "edge_ids": [],
                "source_keys": ["regulator"],
            },
            correlation_id=cycle_id,
        )
    )
    store.append(
        BrainEvent(
            "learning.attribution_recorded",
            "attribution",
            uuid4(),
            {
                "outcome_id": str(outcome_id),
                "prediction_id": str(prediction_id),
                "edge_ids": [],
                "source_keys": ["regulator"],
                "reward_score": 0.8,
                "prediction_error": 0.1,
                "rationale": ["prediction matched outcome"],
            },
            correlation_id=cycle_id,
        )
    )
    return store, str(belief.id), str(evidence.id), str(outcome_id)


def test_signal_command_history_is_projected_from_real_event_metadata():
    store, _, _, _ = _seeded_store()
    body = _client(store).get("/signals").json()
    assert body["total"] == 1
    signal = body["items"][0]
    assert signal["source_id"] == "operator"
    assert signal["metadata"]["content"] == "Inspect the rule change"
    assert signal["metadata"]["operator_command"] is True
    assert signal["metadata"]["command_mode"] == "inspect"


def test_evidence_read_preserves_belief_relationship_and_provenance():
    store, belief_id, evidence_id, _ = _seeded_store()
    body = _client(store).get("/evidence").json()
    assert body["total"] == 1
    evidence = body["items"][0]
    assert evidence["id"] == evidence_id
    assert evidence["source_id"] == "regulator"
    assert evidence["reliability"] == 0.94
    assert evidence["supports"] is True
    assert evidence["belief_ids"] == [belief_id]
    assert evidence["metadata"]["supporting_belief_ids"] == [belief_id]


def test_working_memory_is_latest_durable_cycle_observation_not_fabricated_state():
    store, _, _, _ = _seeded_store()
    body = _client(store).get("/working-memory").json()
    assert body["source"] == "cycle.completed"
    assert body["size"] == 4
    assert body["capacity"] == 7
    assert body["evicted_count"] == 1
    assert body["cycle_id"]


def test_working_memory_reports_unobserved_when_no_cycle_exists():
    body = _client(InMemoryBrainStore()).get("/working-memory").json()
    assert body == {
        "observed_at": None,
        "size": None,
        "capacity": None,
        "cycle_id": None,
        "source": "unobserved",
        "evicted_count": 0,
        "last_slot_id": None,
    }


def test_outcomes_are_projected_from_learning_event_stream():
    store, _, _, outcome_id = _seeded_store()
    body = _client(store).get("/outcomes").json()
    assert body["total"] == 1
    outcome = body["items"][0]
    assert outcome["id"] == outcome_id
    assert outcome["value_created"] == 0.8
    assert outcome["prediction_accuracy"] == 0.9
    assert outcome["prediction_id"]
    assert outcome["metadata"]["source_keys"] == ["regulator"]


def test_learning_history_is_bounded_to_real_evolution_event_types():
    store, _, _, outcome_id = _seeded_store()
    body = _client(store).get("/learning-events").json()
    event_types = {item["event_type"] for item in body["items"]}
    assert "learning.attribution_recorded" in event_types
    assert "outcome.recorded" in event_types
    assert "memory.working_stored" in event_types
    assert "cycle.completed" in event_types
    attribution = next(item for item in body["items"] if item["event_type"] == "learning.attribution_recorded")
    assert attribution["payload"]["outcome_id"] == outcome_id
    assert attribution["correlation_id"]


def test_nested_durable_event_store_is_authoritative_for_event_reads():
    durable = InMemoryBrainStore()
    durable.append(
        BrainEvent(
            "signal.enqueued",
            "sensory_inbox",
            uuid4(),
            {
                "source_key": "operator",
                "content": "Durable only",
                "claim": "Durable only",
                "payload": {"metadata": {"operator_command": True, "command_mode": "solve"}},
            },
        )
    )
    projection = SimpleNamespace(
        beliefs={},
        evidence={},
        event_store=durable,
        read_all=lambda: (_ for _ in ()).throw(AssertionError("projection read_all must not be used")),
    )
    body = _client(projection).get("/signals").json()
    assert body["total"] == 1
    assert body["items"][0]["metadata"]["content"] == "Durable only"


def test_postgres_recent_event_read_is_index_bounded_not_full_ledger_scan():
    source = inspect.getsource(PostgresEventStore.read_recent)
    assert "where event_type = %s" in source
    assert "order by occurred_at desc" in source
    assert "limit %s" in source
    assert "read_all" not in source
    assert "event_type = any" not in source, "multi-type reads must not build one giant sort input"
