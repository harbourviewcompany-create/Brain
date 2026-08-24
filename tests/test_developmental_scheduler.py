from datetime import UTC, datetime, timedelta

import pytest

from brain.developmental.evidence_store import (
    DevelopmentalReplayService,
    InMemoryDevelopmentalEvidenceStore,
)
from brain.developmental.metacognitive_optimization import (
    BenchmarkEvidenceClass,
    BenchmarkRun,
    CapabilityBenchmark,
)
from brain.developmental.scheduler import (
    DevelopmentalBudget,
    DevelopmentalQueueItem,
    DevelopmentalSchedule,
    DevelopmentalSchedulerService,
)

NOW = datetime(2026, 8, 24, 4, 0, tzinfo=UTC)
EVIDENCE = ["issue:103", "test:developmental-scheduler"]


def _scheduler() -> tuple[InMemoryDevelopmentalEvidenceStore, DevelopmentalSchedulerService]:
    store = InMemoryDevelopmentalEvidenceStore()
    scheduler = DevelopmentalSchedulerService(store)
    scheduler.budgets.set(
        DevelopmentalBudget(
            remaining_runs=10,
            remaining_compute_seconds=1000,
            remaining_tokens=100000,
            remaining_api_cost_units=100,
        ),
        evidence_refs=EVIDENCE,
    )
    return store, scheduler


def test_due_priority_accounts_for_stale_evidence_and_regression_risk():
    _, scheduler = _scheduler()
    scheduler.register_schedule(
        DevelopmentalSchedule(
            capability="memory",
            cadence_seconds=3600,
            priority=0.4,
            regression_risk=0.9,
            last_evidence_at=NOW - timedelta(days=5),
            next_due_at=NOW,
        ),
        evidence_refs=EVIDENCE,
    )
    scheduler.register_schedule(
        DevelopmentalSchedule(
            capability="language",
            cadence_seconds=3600,
            priority=0.4,
            regression_risk=0.0,
            last_evidence_at=NOW,
            next_due_at=NOW,
        ),
        evidence_refs=EVIDENCE,
    )
    queue = scheduler.queue_due(now=NOW, evidence_refs=EVIDENCE)
    assert [item.capability for item in queue] == ["memory", "language"]
    assert "stale_evidence" in queue[0].reason
    assert "regression_risk" in queue[0].reason


def test_not_due_and_backoff_items_do_not_hot_loop():
    _, scheduler = _scheduler()
    schedule = scheduler.register_schedule(
        DevelopmentalSchedule(capability="planning", cadence_seconds=3600, next_due_at=NOW + timedelta(hours=1)),
        evidence_refs=EVIDENCE,
    )
    assert scheduler.queue_due(now=NOW, evidence_refs=EVIDENCE) == []
    schedule.next_due_at = NOW
    scheduler.register_schedule(schedule, evidence_refs=EVIDENCE)
    scheduler.backoff.fail("planning", "boom", now=NOW, evidence_refs=EVIDENCE)
    assert scheduler.queue_due(now=NOW + timedelta(seconds=30), evidence_refs=EVIDENCE) == []
    assert scheduler.queue_due(now=NOW + timedelta(seconds=61), evidence_refs=EVIDENCE)


def test_budget_exhaustion_blocks_run_before_assessment():
    store = InMemoryDevelopmentalEvidenceStore()
    scheduler = DevelopmentalSchedulerService(store)
    scheduler.budgets.set(DevelopmentalBudget(remaining_runs=0), evidence_refs=EVIDENCE)
    item = DevelopmentalQueueItem(
        schedule_id=DevelopmentalSchedule(capability="memory", cadence_seconds=60).id,
        capability="memory",
        due_at=NOW,
        priority_score=1.0,
        reason="due",
    )
    with pytest.raises(ValueError, match="developmental_budget_exhausted"):
        scheduler.start_run(
            item,
            estimated_compute_seconds=1,
            estimated_tokens=1,
            estimated_api_cost_units=0,
            evidence_refs=EVIDENCE,
            now=NOW,
        )
    assert store.list("DevelopmentalRunRecord") == []


def test_scheduler_executes_assessment_only_and_advances_schedule():
    _, scheduler = _scheduler()
    schedule = scheduler.register_schedule(
        DevelopmentalSchedule(capability="memory", cadence_seconds=3600, next_due_at=NOW),
        evidence_refs=EVIDENCE,
    )
    item = scheduler.queue_due(now=NOW, evidence_refs=EVIDENCE)[0]
    benchmark = CapabilityBenchmark(
        name="memory-recall", capability="memory", metric="score", higher_is_better=True
    )
    baseline = BenchmarkRun(
        benchmark_id=benchmark.id,
        score=0.8,
        evidence_refs=EVIDENCE,
        evidence_class=BenchmarkEvidenceClass.INTERNAL,
        implementation_ref="brain/memory_systems.py",
        test_target="tests/test_developmental_scheduler.py",
    )
    current = BenchmarkRun(
        benchmark_id=benchmark.id,
        score=0.82,
        evidence_refs=EVIDENCE,
        evidence_class=BenchmarkEvidenceClass.INTERNAL,
        implementation_ref="brain/memory_systems.py",
        test_target="tests/test_developmental_scheduler.py",
    )
    assessment = scheduler.run_assessment(
        item=item,
        benchmark=benchmark,
        baseline=baseline,
        current=current,
        estimated_compute_seconds=2,
        estimated_tokens=100,
        estimated_api_cost_units=0.1,
        evidence_refs=EVIDENCE,
        now=NOW,
    )
    assert assessment.state == "NO_REGRESSION"
    refreshed = next(item for item in scheduler.schedules() if item.id == schedule.id)
    assert refreshed.next_due_at == NOW + timedelta(seconds=3600)
    assert scheduler.store.list("DevelopmentalRunRecord")[-1].state == "completed"


def test_failure_applies_backoff_and_replay_reconstructs_scheduler_state():
    store, scheduler = _scheduler()
    schedule = scheduler.register_schedule(
        DevelopmentalSchedule(capability="reasoning", cadence_seconds=60, next_due_at=NOW),
        evidence_refs=EVIDENCE,
    )
    item = scheduler.queue_due(now=NOW, evidence_refs=EVIDENCE)[0]
    benchmark = CapabilityBenchmark(name="reason", capability="reasoning", metric="score", higher_is_better=True)
    baseline = BenchmarkRun(
        benchmark_id=benchmark.id,
        score=1,
        evidence_refs=EVIDENCE,
        evidence_class=BenchmarkEvidenceClass.INTERNAL,
        implementation_ref="brain/planning.py",
        test_target="tests/test_developmental_scheduler.py",
    )
    current = BenchmarkRun(
        benchmark_id=DevelopmentalSchedule(capability="wrong", cadence_seconds=1).id,
        score=1,
        evidence_refs=EVIDENCE,
        evidence_class=BenchmarkEvidenceClass.INTERNAL,
        implementation_ref="brain/planning.py",
        test_target="tests/test_developmental_scheduler.py",
    )
    with pytest.raises(ValueError):
        scheduler.run_assessment(
            item=item,
            benchmark=benchmark,
            baseline=baseline,
            current=current,
            estimated_compute_seconds=1,
            estimated_tokens=10,
            estimated_api_cost_units=0,
            evidence_refs=EVIDENCE,
            now=NOW,
        )
    assert scheduler.backoff.active("reasoning", now=NOW + timedelta(seconds=1))

    replayed = DevelopmentalReplayService().replay(store.events())
    restarted = DevelopmentalSchedulerService(replayed)
    assert any(item.id == schedule.id for item in restarted.schedules())
    assert restarted.backoff.active("reasoning", now=NOW + timedelta(seconds=1))


def test_scheduler_has_explicit_no_self_approval_or_mutation_boundary():
    _, scheduler = _scheduler()
    with pytest.raises(ValueError, match="cannot_approve"):
        scheduler.approve_plan()
    with pytest.raises(ValueError, match="cannot_mutate_merge_or_deploy"):
        scheduler.direct_self_modify()
    assert "assessment_only_no_self_approval" in scheduler.snapshot()["authority"]
