from uuid import uuid4

import pytest

from brain.developmental.evidence_store import (
    DevelopmentalEvidenceCodec,
    DevelopmentalEvidenceEvent,
    DevelopmentalReplayService,
    InMemoryDevelopmentalEvidenceStore,
)
from brain.developmental.improvement_experiments import (
    ExperimentResult,
    PromotionDecision,
)
from brain.developmental.metacognitive_optimization import (
    BenchmarkEvidenceClass,
    BenchmarkRun,
    CapabilityBenchmark,
    LearningDebtItem,
    OptimizationPlanState,
    RegressionSignal,
    SelfOptimizationPlan,
)


def evidence() -> list[str]:
    return ["fixture:agent-019", "test:developmental-evidence"]


def test_codec_roundtrips_uuid_datetime_enum_and_typed_records() -> None:
    benchmark = CapabilityBenchmark("planning", "planning", "score", True)
    run = BenchmarkRun(
        benchmark.id,
        0.72,
        evidence(),
        BenchmarkEvidenceClass.THIRD_PARTY,
        "impl:v1",
        "tests:test_planning",
    )
    decoded = DevelopmentalEvidenceCodec.decode(DevelopmentalEvidenceCodec.encode(run))
    assert decoded == run
    assert decoded.evidence_class is BenchmarkEvidenceClass.THIRD_PARTY
    assert decoded.id == run.id
    assert decoded.created_at == run.created_at


def test_unknown_record_type_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown_developmental_record_type"):
        DevelopmentalEvidenceCodec.decode({"__type__": "InventedRecord", "fields": {}})


def test_object_upsert_preserves_append_only_event_history() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    debt = LearningDebtItem("planning", "gap", 0.8, 0.9, evidence())
    store.put(debt, event_type="LEARNING_DEBT_CREATED", evidence_refs=evidence())
    debt.priority = 0.95
    store.put(debt, event_type="LEARNING_DEBT_PRIORITIZED", evidence_refs=evidence())
    assert len(store.list("LearningDebtItem")) == 1
    assert store.get("LearningDebtItem", debt.id).priority == 0.95
    assert [event.sequence for event in store.events()] == [1, 2]
    assert [event.event_type for event in store.events()] == [
        "LEARNING_DEBT_CREATED",
        "LEARNING_DEBT_PRIORITIZED",
    ]


def test_restart_replay_reconstructs_latest_snapshot_without_erasing_history() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    plan = SelfOptimizationPlan(
        objective="repair planning",
        hypothesis_ids=[uuid4()],
        learning_debt_ids=[uuid4()],
        traceability_refs=evidence(),
        rollback_plan="revert candidate",
        test_targets=["tests:test"],
        acceptance_criteria=["score improves"],
    )
    store.put(plan, event_type="PLAN_PROPOSED", evidence_refs=evidence())
    plan.state = OptimizationPlanState.REVIEWED
    store.put(plan, event_type="PLAN_REVIEWED", evidence_refs=evidence())
    replayed = DevelopmentalReplayService().replay(store.events())
    hydrated = replayed.get("SelfOptimizationPlan", plan.id)
    assert hydrated.state is OptimizationPlanState.REVIEWED
    assert len(replayed.events()) == 2
    assert replayed.events()[0].event_type == "PLAN_PROPOSED"


def test_restart_replay_preserves_regressions_and_failed_experiment_results() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    regression = RegressionSignal(
        benchmark_id=uuid4(),
        baseline_run_id=uuid4(),
        current_run_id=uuid4(),
        delta=-0.25,
        severity=0.4,
        evidence_refs=evidence(),
    )
    rejected = ExperimentResult(
        run_id=uuid4(),
        benchmark_deltas={"planning": 0.2},
        controls_passed=False,
        protected_regressions=[],
        evidence_refs=evidence(),
        decision=PromotionDecision.REJECT,
    )
    store.put(regression, event_type="REGRESSION_DETECTED", evidence_refs=evidence())
    store.put(rejected, event_type="EXPERIMENT_REJECTED", evidence_refs=evidence())
    replayed = DevelopmentalReplayService().replay(store.events())
    report = DevelopmentalReplayService.integrity_report(replayed)
    assert report["unresolved_regressions"] == 1
    assert report["failed_or_hold_results"] == 1
    assert report["sequence_contiguous"] is True


def test_replay_fails_closed_on_sequence_gap() -> None:
    record = LearningDebtItem("memory", "gap", 0.5, 0.7, evidence())
    event = DevelopmentalEvidenceEvent(
        sequence=2,
        event_type="LEARNING_DEBT_CREATED",
        record_kind="LearningDebtItem",
        record_id=record.id,
        payload=DevelopmentalEvidenceCodec.encode(record),
        evidence_refs=evidence(),
    )
    with pytest.raises(ValueError, match="sequence_gap"):
        DevelopmentalReplayService().replay([event])


def test_integrity_report_exposes_non_execution_authority() -> None:
    store = InMemoryDevelopmentalEvidenceStore()
    report = DevelopmentalReplayService.integrity_report(store)
    assert report["persistence_authority"] == "evidence_only_no_mutation_merge_deploy"
    assert report["last_sequence"] == 0
