from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from brain.events import BrainEvent
from brain.schemas import (
    EvidenceItem,
    GraphEdge,
    Prediction,
    ProvenanceRef,
    RawObservation,
    Signal,
)


def test_cross_object_provenance_contract_is_explicit() -> None:
    source_id = str(uuid4())
    observation = RawObservation(
        source_id=source_id,
        content="observed",
        provenance=[ProvenanceRef(source_id=source_id, source_location="https://example.invalid/source")],
    )
    evidence = EvidenceItem(
        claim="claim",
        source_id=source_id,
        observation_id=str(observation.id),
        provenance=[ProvenanceRef(source_id=source_id, source_location="https://example.invalid/source")],
    )
    signal = Signal(
        source_id=source_id,
        evidence_ids=[str(evidence.id)],
        provenance=[ProvenanceRef(source_id=source_id, source_location="https://example.invalid/source")],
        novelty=0.4,
        urgency=0.3,
        commercial_upside=1.0,
        attention_score=0.5,
    )

    assert evidence.observation_id == str(observation.id)
    assert signal.evidence_ids == [str(evidence.id)]
    assert all(ref.source_id == source_id for obj in (observation, evidence, signal) for ref in obj.provenance)


def test_prediction_and_graph_edge_can_carry_shared_source_lineage() -> None:
    source_id = str(uuid4())
    ref = ProvenanceRef(source_id=source_id, source_location="https://example.invalid/source")
    prediction = Prediction(
        belief_id="belief-1",
        forecast_probability=0.8,
        provenance=[ref],
    )
    edge = GraphEdge(
        source="belief-1",
        target="entity-1",
        relation="supports",
        weight=0.7,
        confidence=0.8,
        evidence_ids=[source_id],
        provenance=[ref],
    )

    assert prediction.provenance[0].source_id == edge.provenance[0].source_id
    assert edge.evidence_ids == [source_id]


def test_event_lineage_has_causation_and_correlation_slots() -> None:
    correlation_id = uuid4()
    event = BrainEvent(
        event_type="evidence.observed",
        aggregate_type="evidence",
        aggregate_id=uuid4(),
        payload={"source_id": "source-1"},
        correlation_id=correlation_id,
    )
    child = BrainEvent(
        event_type="signal.created",
        aggregate_type="signal",
        aggregate_id=uuid4(),
        payload={"evidence_id": str(event.aggregate_id)},
        causation_id=event.id,
        correlation_id=correlation_id,
    )

    assert child.causation_id == event.id
    assert child.correlation_id == event.correlation_id
    assert child.occurred_at.tzinfo is not None
