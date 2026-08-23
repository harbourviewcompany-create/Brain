from __future__ import annotations

import pytest

from brain.developmental.consolidation import (
    ConsolidationService,
    DreamScenario,
    MemoryCompressionService,
    MemoryRecord,
)
from brain.developmental.global_workspace import (
    BroadcastService,
    WorkspaceCompetitionService,
    WorkspaceItem,
)
from brain.developmental.immune import CognitiveImmuneService, QuarantineService, RecoveryService
from brain.developmental.module_genesis import ModuleGenesisService, ModuleMaturityService, ModuleStage
from brain.developmental.plasticity import CognitiveEdge, GraphRewireService, PlasticityService, PruningService
from brain.developmental.prediction_error import (
    CalibrationService,
    DevelopmentPressureService,
    PredictionErrorService,
    PredictionRecord,
)
from brain.developmental.self_model import (
    CapabilityRecord,
    EvidenceGap,
    LearningDebt,
    LimitationRecord,
    SelfModelService,
)
from brain.developmental.spine import DevelopmentScore, DevelopmentalStage, DevelopmentalStageService
from brain.developmental.theory_registry import (
    TheoryCompetitionService,
    TheoryRecord,
    TheoryRegistryService,
    TheoryStatus,
    UnknownMechanism,
    UnknownMechanismRegistryService,
)


def test_prediction_error_updates_attention_and_calibration_trace_is_preserved():
    prediction = PredictionRecord("conversion", 0.8, 0.9, ["source:forecast"])
    error = PredictionErrorService().compute(prediction, 0.2)
    trace = CalibrationService().update(prediction, error)
    pressure = DevelopmentPressureService().score(error, evidence_gap=0.8)
    assert error.absolute_error == pytest.approx(0.6)
    assert trace.confidence_before == 0.9
    assert trace.confidence_after < trace.confidence_before
    assert trace.source_refs == ["source:forecast"]
    assert pressure.learning_priority > 0.4
    assert "prediction_error" in pressure.reasons


def test_reward_strengthens_edge_pain_weakens_edge_and_rewire_is_reversible():
    edge = CognitiveEdge("source", "belief", "supports", weight=0.5, evidence_refs=["outcome:1"])
    plasticity = PlasticityService()
    rewire = GraphRewireService()
    reward_proposal = plasticity.propose(edge, reward=1.0, reliability=1.0)
    strengthened, event, rollback = rewire.apply(edge, reward_proposal)
    assert strengthened.weight > edge.weight
    restored = rewire.rollback(strengthened, rollback)
    assert restored.weight == edge.weight
    assert event.evidence_refs

    pain_proposal = plasticity.propose(strengthened, pain=1.0, evidence_refs=["pain:1"])
    weakened, _, _ = rewire.apply(strengthened, pain_proposal)
    assert weakened.weight < strengthened.weight


def test_pruning_requires_evidence():
    edge = CognitiveEdge("a", "b", "weak", weight=0.01, confidence=0.05, age_cycles=1000)
    with pytest.raises(ValueError):
        PruningService().decide(edge, evidence_refs=[])
    decision = PruningService().decide(edge, evidence_refs=["replay:weak-edge"])
    assert decision.prune is True


def test_module_birth_requires_traceability_and_activation_requires_acceptance():
    genesis = ModuleGenesisService()
    with pytest.raises(ValueError):
        genesis.propose("new cortex", "repeated pattern", [])
    hypothesis = genesis.propose("new cortex", "repeated pattern", ["source:pattern"])
    hypothesis, birth = genesis.specify(
        hypothesis,
        owner_objects=["Owner"],
        schemas=["Schema"],
        services=["Service"],
        fixtures=["fixture.json"],
        tests=["test_new_cortex"],
        dashboards=["Module Nursery"],
    )
    assert birth.missing_requirements == []
    assert hypothesis.state is ModuleStage.SPECIFIED
    with pytest.raises(ValueError):
        ModuleMaturityService().activate(
            hypothesis,
            acceptance_report=None,
            replay_passed=True,
            immune_scan_passed=True,
        )
    active, record = ModuleMaturityService().activate(
        hypothesis,
        acceptance_report="reports/acceptance/new-cortex.json",
        replay_passed=True,
        immune_scan_passed=True,
    )
    assert active.state is ModuleStage.ACTIVE
    assert record.source_refs == ["source:pattern"]


def test_workspace_winner_has_evidence_suppressed_items_are_logged_and_consumers_recorded():
    items = [
        WorkspaceItem(
            "contradiction",
            "critical conflict",
            ["evidence:1"],
            salience=1.0,
            urgency=1.0,
            contradiction=1.0,
            intended_consumers=["beliefs", "planner"],
        ),
        WorkspaceItem("noise", "low value", ["evidence:2"], salience=0.1, noise_probability=0.8),
    ]
    coalition, suppressed = WorkspaceCompetitionService().compete(items)
    assert coalition.winner_ids == [items[0].id]
    assert suppressed and suppressed[0].item_id == items[1].id
    broadcast = BroadcastService().broadcast(coalition, items)
    assert broadcast.evidence_refs == ["evidence:1"]
    assert broadcast.consumers == ["beliefs", "planner"]
    assert broadcast.consciousness_claim is False


def test_dream_outputs_are_simulated_and_consolidation_preserves_provenance():
    memories = [
        MemoryRecord("buyer prefers speed", ["source:call"]),
        MemoryRecord("buyer prefers speed", ["source:email"]),
    ]
    compression = MemoryCompressionService().compress(memories)
    assert set(compression.source_refs) == {"source:call", "source:email"}
    assert compression.reversible is True
    scenario = DreamScenario("rehearse route", ["source:call"], ["strengthen buyer-path edge"])
    run, _, _, proposals = ConsolidationService().run(memories=memories, scenarios=[scenario])
    assert run.external_actions_executed == 0
    assert proposals[0].proposal_only is True
    assert proposals[0].external_action_authorized is False


def test_immune_quarantine_and_recovery_require_evidence():
    immune = CognitiveImmuneService()
    alerts = immune.scan(
        target_id="action-1",
        approval_required=True,
        approval_present=False,
        confidence=0.99,
        evidence_count=0,
        evidence_refs=["audit:1"],
    )
    assert immune.should_block(alerts)
    record = QuarantineService().quarantine("action-1", alerts[0])
    assert record.active
    plan = RecoveryService().plan("action-1", ["obtain approval", "rerun simulation"], ["audit:1"])
    with pytest.raises(ValueError):
        RecoveryService().verify(plan, [])
    assert RecoveryService().verify(plan, ["approval:1"]).verified is True


def test_self_model_blocks_unsupported_capability_and_learning_debt_affects_priority():
    service = SelfModelService()
    with pytest.raises(ValueError):
        service.add_capability(CapabilityRecord("causal planning", 0.9, []))
    service.add_capability(
        CapabilityRecord(
            "causal planning",
            0.8,
            ["source:plan"],
            fixture_refs=["fixture:plan"],
            test_refs=["test:plan"],
            acceptance_refs=["acceptance:plan"],
        )
    )
    assert service.can_claim("causal planning")
    service.add_learning_debt(LearningDebt("causal planning", 0.8, ["benchmark:1"]))
    service.add_evidence_gap(EvidenceGap("causal planning", ["intervention data"], 0.6))
    assert service.learning_priority("causal planning") > 0.6
    service.add_limitation(LimitationRecord("causal planning unavailable for unobserved domains", ["eval:1"]))
    assert service.can_claim("causal planning") is False


def test_unknown_is_preserved_and_theory_promotion_requires_evidence():
    unknowns = UnknownMechanismRegistryService()
    item = unknowns.register(UnknownMechanism("binding", "mechanism unresolved", []))
    assert item.open is True
    with pytest.raises(ValueError):
        unknowns.close(item.id, evidence_refs=[])

    registry = TheoryRegistryService()
    a = registry.register(TheoryRecord("A", "first theory", ["paper:a"], confidence=0.55))
    b = registry.register(TheoryRecord("B", "second theory", ["paper:b"], confidence=0.5))
    competition = TheoryCompetitionService().compete("which model?", [a, b], evidence_refs=["review:1"])
    assert competition.unresolved is True
    assert set(competition.theory_ids) == {a.id, b.id}
    with pytest.raises(ValueError):
        registry.promote(a.id, evidence_refs=[], confidence=0.8)
    promoted = registry.promote(a.id, evidence_refs=["experiment:1"], confidence=0.8)
    assert promoted.status is TheoryStatus.SUPPORTED


def test_developmental_stage_cannot_skip_and_requires_growth_gates():
    service = DevelopmentalStageService()
    score = DevelopmentScore(**{name: 1.0 for name in DevelopmentScore.__dataclass_fields__})
    with pytest.raises(ValueError):
        service.advance(
            DevelopmentalStage.REFLEX,
            DevelopmentalStage.ASSOCIATIVE,
            score,
            replay_passed=True,
            immune_scan_passed=True,
            rollback_path_exists=True,
            acceptance_report_exists=True,
        )
    assert (
        service.advance(
            DevelopmentalStage.REFLEX,
            DevelopmentalStage.PERCEPTUAL,
            score,
            replay_passed=True,
            immune_scan_passed=True,
            rollback_path_exists=True,
            acceptance_report_exists=True,
        )
        is DevelopmentalStage.PERCEPTUAL
    )
