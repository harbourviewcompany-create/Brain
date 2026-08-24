from __future__ import annotations

from uuid import uuid4

import pytest

from brain.adapters.cognitive_object_store import InMemoryCognitiveObjectStore
from brain.growth_runtime import CognitiveGrowthRuntime
from brain.protocol import (
    CognitiveConflict,
    CognitiveObjectEnvelope,
    CognitiveProtocolService,
    CognitiveTransition,
    DevelopmentalPlasticityDelta,
    EpistemicState,
    KnowledgeGap,
    KnowledgeGapType,
    LearningEvent,
    ProjectionDecision,
    ProjectionState,
    ProvenanceEdge,
    ReplayBundle,
)


def make_gap() -> KnowledgeGap:
    return KnowledgeGap(
        gap_type=KnowledgeGapType.UNCERTAIN,
        description="Whether the current causal model explains the observation",
        target_refs=["belief:b1"],
        evidence_refs=["evidence:e1"],
        epistemic_state=EpistemicState(confidence=0.4, uncertainty=0.8, evidence_strength=0.3),
        importance=0.9,
        expected_information_gain=0.8,
        downstream_dependency_count=6,
        investigation_cost=0.2,
    )


def test_epistemic_state_preserves_dimensions_and_clamps() -> None:
    state = EpistemicState(confidence=1.4, uncertainty=-0.2, contradiction=0.7)
    assert state.confidence == 1.0
    assert state.uncertainty == 0.0
    assert state.contradiction == 0.7


def test_object_envelope_requires_and_persists_provenance() -> None:
    service = CognitiveProtocolService()
    with pytest.raises(ValueError, match="requires provenance"):
        CognitiveObjectEnvelope(
            object_id="belief:b1",
            object_kind="belief",
            provenance_refs=[],
            lifecycle_state="active",
        )

    envelope = service.register_envelope(
        CognitiveObjectEnvelope(
            object_id="belief:b1",
            object_kind="belief",
            provenance_refs=["evidence:e1"],
            lifecycle_state="active",
            epistemic_state=EpistemicState(confidence=0.6, uncertainty=0.4),
        )
    )
    assert service.store.get("cognitive_object_envelope", envelope.object_id) is not None


def test_lifecycle_transition_is_appendable_and_reversible_only_with_rollback() -> None:
    service = CognitiveProtocolService()
    with pytest.raises(ValueError, match="rollback"):
        CognitiveTransition(
            object_id="hypothesis:h1",
            object_kind="hypothesis",
            from_state="generated",
            to_state="supported",
            trigger="new evidence",
            provenance_refs=["evidence:e1"],
            actor="TruthMaintenanceService",
            reversible=True,
        )

    transition = service.record_transition(
        CognitiveTransition(
            object_id="hypothesis:h1",
            object_kind="hypothesis",
            from_state="generated",
            to_state="supported",
            trigger="new evidence",
            provenance_refs=["evidence:e1"],
            actor="TruthMaintenanceService",
            reversible=True,
            rollback_ref="transition:rollback-1",
        )
    )
    assert transition.from_state == "generated"
    assert transition.to_state == "supported"
    assert service.store.get("cognitive_transition", transition.id) is not None


def test_conflicting_states_coexist_without_forced_resolution() -> None:
    service = CognitiveProtocolService()
    conflict = service.register_conflict(
        CognitiveConflict(
            conflict_class="belief_conflict",
            competing_refs=["belief:b1", "belief:b2"],
            evidence_refs=["evidence:e1", "evidence:e2"],
            severity=0.8,
            unresolved_dimensions=["causal_direction"],
        )
    )
    assert conflict.competing_refs == ["belief:b1", "belief:b2"]
    assert conflict.selected_resolution is None
    assert conflict.lifecycle_state == "detected"
    assert service.store.get("cognitive_conflict", conflict.id) is not None


def test_gap_drives_domain_general_affordance_and_persists() -> None:
    store = InMemoryCognitiveObjectStore()
    service = CognitiveProtocolService(store)
    gap = service.detect_gap(make_gap())
    affordance = service.affordance_from_gap(gap.id)

    assert gap.priority_score > 0.6
    assert affordance.kind == "investigate"
    assert str(gap.id) in affordance.target_refs
    assert affordance.expected_information_gain == gap.expected_information_gain
    assert store.get("knowledge_gap", gap.id) is not None
    assert store.get("cognitive_affordance", affordance.id) is not None


def test_consequential_projection_cannot_bypass_explicit_approval() -> None:
    service = CognitiveProtocolService()
    projection = ProjectionDecision(
        object_refs=["decision:d1"],
        target="external:connector",
        source_refs=["evidence:e1"],
        consequential=True,
    )

    held = service.evaluate_projection(projection)
    assert held.state == ProjectionState.GOVERNANCE_PENDING
    assert held.may_externalize is False

    approved = service.evaluate_projection(held, approve=True, approver="operator:1")
    assert approved.state == ProjectionState.APPROVED
    assert approved.may_externalize is True


def test_learning_requires_outcome_attribution_and_evidence() -> None:
    service = CognitiveProtocolService()
    incomplete = LearningEvent(
        outcome_refs=["outcome:o1"],
        action_refs=["action:a1"],
        prediction_refs=["prediction:p1"],
        attribution_refs=[],
        evidence_refs=["evidence:e1"],
        expected_vs_actual="expected 1, observed 0",
        utility_delta=-0.5,
        information_gain=0.4,
        proposed_updates={"belief:b1": {"confidence_delta": -0.2}},
    )
    with pytest.raises(ValueError, match="attribution"):
        service.record_learning(incomplete)

    complete = LearningEvent(
        outcome_refs=["outcome:o1"],
        action_refs=["action:a1"],
        prediction_refs=["prediction:p1"],
        attribution_refs=["attribution:t1"],
        evidence_refs=["evidence:e1"],
        expected_vs_actual="expected 1, observed 0",
        utility_delta=-0.5,
        information_gain=0.4,
        proposed_updates={"belief:b1": {"confidence_delta": -0.2}},
    )
    assert service.record_learning(complete).lifecycle_state == "supported"


def test_provenance_and_replay_preserve_lineage_without_external_execution() -> None:
    service = CognitiveProtocolService()
    edge = service.add_provenance_edge(
        ProvenanceEdge(
            from_id="evidence:e1",
            to_id="belief:b1",
            edge_type="supports",
            source_refs=["source:s1"],
            confidence=0.8,
        )
    )
    gap = service.detect_gap(make_gap())
    affordance = service.affordance_from_gap(gap.id)
    bundle = ReplayBundle(
        scope="fixture-chain",
        object_refs=["evidence:e1", "belief:b1"],
        provenance_edge_ids=[str(edge.id)],
        epistemic_object_refs=["belief:b1"],
        transition_refs=[],
        affordance_refs=[str(affordance.id)],
        projection_refs=[],
        outcome_refs=[],
        learning_event_refs=[],
        unresolved_gap_refs=[str(gap.id)],
        unresolved_conflict_refs=[],
        source_refs=["source:s1"],
        software_version="test",
    )
    replay = service.build_replay(bundle)
    assert replay.external_actions_executed == 0
    assert service.store.get("cognitive_replay", replay.id) is not None

    with pytest.raises(ValueError, match="never execute external actions"):
        ReplayBundle(
            scope="unsafe",
            object_refs=[],
            provenance_edge_ids=[],
            epistemic_object_refs=[],
            transition_refs=[],
            affordance_refs=[],
            projection_refs=[],
            outcome_refs=[],
            learning_event_refs=[],
            unresolved_gap_refs=[],
            unresolved_conflict_refs=[],
            source_refs=["source:s1"],
            external_actions_executed=1,
        )


def test_plasticity_requires_learning_evidence_and_rollback_and_growth_runtime_shares_store() -> None:
    store = InMemoryCognitiveObjectStore()
    runtime = CognitiveGrowthRuntime(store)
    gap = runtime.protocol.detect_gap(make_gap())
    runtime.protocol.affordance_from_gap(gap.id)

    delta = DevelopmentalPlasticityDelta(
        target_kind="belief_calibration",
        target_id="belief:b1",
        trigger_learning_event_ids=[str(uuid4())],
        before_state_ref="snapshot:before",
        proposed_after_state={"calibration_weight": 0.7},
        mechanism_class="calibration_update",
        evidence_refs=["evidence:e1"],
        expected_benefit=0.4,
        regression_risk=0.2,
        rollback_plan_ref="rollback:r1",
        benchmark_refs=["benchmark:b1"],
    )
    runtime.protocol.propose_plasticity(delta)

    snapshot = runtime.snapshot()
    assert snapshot["protocol_knowledge_gaps"] == 1
    assert snapshot["protocol_cognitive_affordances"] == 1
    assert snapshot["protocol_plasticity_deltas"] == 1
    assert store.get("developmental_plasticity_delta", delta.id) is not None
