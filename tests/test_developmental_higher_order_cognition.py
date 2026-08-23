import pytest

from brain.developmental.higher_order_cognition import (
    BenchmarkRecord,
    BrainRegionMapping,
    CausalHypothesis,
    CognitiveScale,
    CurriculumTask,
    DevelopmentalStage,
    DevelopmentalStageRecord,
    HigherOrderCognitionService,
    ScaleLink,
    ScaleNode,
)


def test_multiscale_map_requires_source_refs_and_links_evidence() -> None:
    service = HigherOrderCognitionService()
    with pytest.raises(ValueError, match="source_refs"):
        service.add_scale_node(ScaleNode(name="unsupported", scale=CognitiveScale.SYSTEM, source_refs=[]))

    system = service.add_scale_node(
        ScaleNode(
            name="belief_update_loop",
            scale=CognitiveScale.SYSTEM,
            source_refs=["docs/brain-readable-concept-manual.md#beliefs"],
        )
    )
    commercial = service.add_scale_node(
        ScaleNode(
            name="opportunity_scoring",
            scale=CognitiveScale.COMMERCIAL,
            source_refs=["docs/brain-readable-concept-manual.md#money-spine"],
        )
    )
    link = service.link_scales(
        ScaleLink(
            parent_node_id=system.id,
            child_node_id=commercial.id,
            relation="constrains",
            evidence_refs=["tests/fixtures/brain/higher_order_cognition_cycle.json"],
            confidence=1.2,
        )
    )
    assert link.confidence == 1.0


def test_brain_region_translation_blocks_unsupported_equivalence_claims() -> None:
    service = HigherOrderCognitionService()
    with pytest.raises(ValueError, match="unsupported_neuroscience_claim"):
        service.map_brain_region(
            BrainRegionMapping(
                region_name="prefrontal cortex",
                functional_claim="the Brain is biologically equivalent",
                brain_module="executive_control",
                implementation_module="brain.developmental.global_workspace",
                analogy_status="neuroscience_claim_without_runtime",
                evidence_refs=["source:neuroscience-abstraction"],
            )
        )

    mapping = service.map_brain_region(
        BrainRegionMapping(
            region_name="prefrontal cortex",
            functional_claim="working control analogy for planning, inhibition, and broadcast gating",
            brain_module="executive_control_proxy",
            implementation_module="brain.developmental.global_workspace",
            analogy_status="analogy_runtime_mapping",
            evidence_refs=["docs/spec/BRAIN_DEVELOPMENTAL_INTELLIGENCE_ARCHITECTURE.md"],
        )
    )
    assert mapping.requires_boundary_label() is True


def test_causal_world_model_preserves_alternatives() -> None:
    service = HigherOrderCognitionService()
    with pytest.raises(ValueError, match="alternatives"):
        service.register_causal_hypothesis(
            CausalHypothesis(
                cause_ref="source_priority_change",
                effect_ref="opportunity_quality",
                mechanism="source reliability affects opportunity quality",
                evidence_refs=["replay:source-priority"],
                confidence=0.7,
            )
        )

    hypothesis = service.register_causal_hypothesis(
        CausalHypothesis(
            cause_ref="source_priority_change",
            effect_ref="opportunity_quality",
            mechanism="source reliability may affect opportunity quality",
            evidence_refs=["replay:source-priority"],
            confidence=1.4,
            alternative_hypotheses=["operator_attention_shift", "market_timing"],
        )
    )
    assert hypothesis.confidence == 1.0
    assert hypothesis.alternative_hypotheses == ["operator_attention_shift", "market_timing"]


def test_curriculum_self_design_cannot_execute_external_action() -> None:
    service = HigherOrderCognitionService()
    with pytest.raises(ValueError, match="external_action"):
        service.design_curriculum_task(
            CurriculumTask(
                target_capability="outreach",
                reason="try sending real offers",
                evidence_refs=["self-model:gap"],
                expected_learning_value=0.9,
                risk=0.2,
                priority=0,
                external_action=True,
            )
        )

    task = service.design_curriculum_task(
        CurriculumTask(
            target_capability="calibration",
            reason="reduce prediction error on buyer reply probability",
            evidence_refs=["prediction-error:buyer-reply"],
            expected_learning_value=0.8,
            risk=0.25,
            priority=0,
        )
    )
    assert task.priority == pytest.approx(0.55)


def test_benchmark_metacognition_blocks_superiority_claim_without_evidence() -> None:
    service = HigherOrderCognitionService()
    with pytest.raises(ValueError, match="benchmark_requires_evidence"):
        service.record_benchmark(
            BenchmarkRecord(
                benchmark_name="unverified_claim",
                capability="planning",
                score=1.0,
                baseline_score=0.1,
                evidence_refs=[],
            )
        )

    record = service.record_benchmark(
        BenchmarkRecord(
            benchmark_name="fixture_replay_quality",
            capability="deterministic_replay",
            score=0.91,
            baseline_score=0.82,
            evidence_refs=["reports/acceptance/AGENT-008-015-DEVELOPMENTAL-RUNTIME-PACKAGE.json"],
        )
    )
    assert record.claim_allowed is True
    assert record.improvement == pytest.approx(0.09)


def test_long_horizon_stage_tracking_requires_evidence() -> None:
    service = HigherOrderCognitionService()
    with pytest.raises(ValueError, match="capability_evidence"):
        service.enter_developmental_stage(
            DevelopmentalStageRecord(
                stage=DevelopmentalStage.METACOGNITIVE,
                entered_because="desired by agent",
                evidence_refs=["self-model:claimed"],
                capabilities_unlocked=[],
            )
        )

    stage = service.enter_developmental_stage(
        DevelopmentalStageRecord(
            stage=DevelopmentalStage.METACOGNITIVE,
            entered_because="self-model can block unsupported claims and route learning debt",
            evidence_refs=["tests/test_developmental_self_model.py"],
            capabilities_unlocked=["claim_boundary_report", "learning_debt_priority"],
            blocked_claims=["superior_intelligence_without_benchmarks"],
        )
    )
    assert stage.stage == DevelopmentalStage.METACOGNITIVE
    assert "superior_intelligence_without_benchmarks" in service.claim_boundary_report()["blocked"]
