from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from . import evidence_store as evidence_module
from .evidence_store import DevelopmentalEvidenceStore
from .improvement_cycle import CapabilityAssessment, DevelopmentalImprovementCycleService
from .metacognitive_optimization import BenchmarkRun, CapabilityBenchmark


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class DevelopmentalSchedule:
    capability: str
    cadence_seconds: int
    priority: float = 0.5
    evidence_freshness_seconds: int = 86400
    regression_risk: float = 0.0
    enabled: bool = True
    last_evidence_at: datetime | None = None
    last_run_at: datetime | None = None
    next_due_at: datetime = field(default_factory=utcnow)
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DevelopmentalBudget:
    name: str = "default"
    remaining_runs: int = 10
    remaining_compute_seconds: float = 3600.0
    remaining_tokens: int = 1_000_000
    remaining_api_cost_units: float = 100.0
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DevelopmentalBackoffState:
    capability: str
    consecutive_failures: int = 0
    backoff_until: datetime | None = None
    last_error: str | None = None
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DevelopmentalQueueItem:
    schedule_id: UUID
    capability: str
    due_at: datetime
    priority_score: float
    reason: str
    state: str = "queued"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DevelopmentalRunRequest:
    queue_item_id: UUID
    schedule_id: UUID
    capability: str
    estimated_compute_seconds: float
    estimated_tokens: int
    estimated_api_cost_units: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utcnow)


@dataclass(slots=True)
class DevelopmentalRunRecord:
    request_id: UUID
    schedule_id: UUID
    capability: str
    state: str
    started_at: datetime
    completed_at: datetime | None = None
    assessment_cycle_id: UUID | None = None
    error: str | None = None
    id: UUID = field(default_factory=uuid4)
    updated_at: datetime = field(default_factory=utcnow)


_SCHEDULER_RECORD_TYPES = (
    DevelopmentalSchedule,
    DevelopmentalBudget,
    DevelopmentalBackoffState,
    DevelopmentalQueueItem,
    DevelopmentalRunRequest,
    DevelopmentalRunRecord,
)
for _record_type in _SCHEDULER_RECORD_TYPES:
    evidence_module.RECORD_TYPES[_record_type.__name__] = _record_type


class DevelopmentalBudgetService:
    def __init__(self, store: DevelopmentalEvidenceStore) -> None:
        self.store = store

    def current(self) -> DevelopmentalBudget | None:
        budgets = self.store.list("DevelopmentalBudget")
        if not budgets:
            return None
        return max(budgets, key=lambda item: item.updated_at)

    def set(self, budget: DevelopmentalBudget, *, evidence_refs: list[str]) -> DevelopmentalBudget:
        if budget.remaining_runs < 0 or budget.remaining_compute_seconds < 0:
            raise ValueError("developmental_budget_cannot_be_negative")
        if budget.remaining_tokens < 0 or budget.remaining_api_cost_units < 0:
            raise ValueError("developmental_budget_cannot_be_negative")
        budget.updated_at = utcnow()
        self.store.put(budget, event_type="DEVELOPMENTAL_BUDGET_SET", evidence_refs=evidence_refs)
        return budget

    def consume(
        self,
        *,
        compute_seconds: float,
        tokens: int,
        api_cost_units: float,
        evidence_refs: list[str],
    ) -> DevelopmentalBudget:
        budget = self.current()
        if budget is None:
            raise ValueError("developmental_budget_required")
        if (
            budget.remaining_runs < 1
            or budget.remaining_compute_seconds < compute_seconds
            or budget.remaining_tokens < tokens
            or budget.remaining_api_cost_units < api_cost_units
        ):
            raise ValueError("developmental_budget_exhausted")
        budget.remaining_runs -= 1
        budget.remaining_compute_seconds -= compute_seconds
        budget.remaining_tokens -= tokens
        budget.remaining_api_cost_units -= api_cost_units
        budget.updated_at = utcnow()
        self.store.put(budget, event_type="DEVELOPMENTAL_BUDGET_CONSUMED", evidence_refs=evidence_refs)
        return budget


class DevelopmentalBackoffService:
    def __init__(self, store: DevelopmentalEvidenceStore, *, base_seconds: int = 60, max_seconds: int = 86400) -> None:
        self.store = store
        self.base_seconds = base_seconds
        self.max_seconds = max_seconds

    def current(self, capability: str) -> DevelopmentalBackoffState | None:
        matches = [item for item in self.store.list("DevelopmentalBackoffState") if item.capability == capability]
        return max(matches, key=lambda item: item.updated_at) if matches else None

    def active(self, capability: str, *, now: datetime) -> bool:
        state = self.current(capability)
        return bool(state and state.backoff_until and state.backoff_until > now)

    def fail(self, capability: str, error: str, *, now: datetime, evidence_refs: list[str]) -> DevelopmentalBackoffState:
        previous = self.current(capability)
        failures = (previous.consecutive_failures if previous else 0) + 1
        delay = min(self.max_seconds, self.base_seconds * (2 ** (failures - 1)))
        state = DevelopmentalBackoffState(
            capability=capability,
            consecutive_failures=failures,
            backoff_until=now + timedelta(seconds=delay),
            last_error=error[:1000],
            id=previous.id if previous else uuid4(),
            updated_at=now,
        )
        self.store.put(state, event_type="DEVELOPMENTAL_BACKOFF_APPLIED", evidence_refs=evidence_refs)
        return state

    def clear(self, capability: str, *, now: datetime, evidence_refs: list[str]) -> DevelopmentalBackoffState:
        previous = self.current(capability)
        state = DevelopmentalBackoffState(
            capability=capability,
            consecutive_failures=0,
            backoff_until=None,
            last_error=None,
            id=previous.id if previous else uuid4(),
            updated_at=now,
        )
        self.store.put(state, event_type="DEVELOPMENTAL_BACKOFF_CLEARED", evidence_refs=evidence_refs)
        return state


class DevelopmentalSchedulerService:
    """Resource-bounded scheduler that may trigger assessment only.

    It has no authorization path for plans, experiments, code mutation, merge,
    deployment, spending or external action.
    """

    def __init__(self, store: DevelopmentalEvidenceStore) -> None:
        self.store = store
        self.budgets = DevelopmentalBudgetService(store)
        self.backoff = DevelopmentalBackoffService(store)
        self.cycle = DevelopmentalImprovementCycleService(store)

    def register_schedule(self, schedule: DevelopmentalSchedule, *, evidence_refs: list[str]) -> DevelopmentalSchedule:
        if not schedule.capability.strip() or schedule.cadence_seconds < 1:
            raise ValueError("invalid_developmental_schedule")
        schedule.priority = max(0.0, min(1.0, schedule.priority))
        schedule.regression_risk = max(0.0, min(1.0, schedule.regression_risk))
        schedule.updated_at = utcnow()
        self.store.put(schedule, event_type="DEVELOPMENTAL_SCHEDULE_REGISTERED", evidence_refs=evidence_refs)
        return schedule

    def schedules(self) -> list[DevelopmentalSchedule]:
        latest: dict[UUID, DevelopmentalSchedule] = {}
        for item in self.store.list("DevelopmentalSchedule"):
            previous = latest.get(item.id)
            if previous is None or item.updated_at >= previous.updated_at:
                latest[item.id] = item
        return list(latest.values())

    def queue_due(self, *, now: datetime, evidence_refs: list[str]) -> list[DevelopmentalQueueItem]:
        queued: list[DevelopmentalQueueItem] = []
        for schedule in self.schedules():
            if not schedule.enabled or schedule.next_due_at > now:
                continue
            if self.backoff.active(schedule.capability, now=now):
                continue
            stale_seconds = (
                schedule.evidence_freshness_seconds
                if schedule.last_evidence_at is None
                else max(0.0, (now - schedule.last_evidence_at).total_seconds())
            )
            stale_boost = min(1.0, stale_seconds / max(1, schedule.evidence_freshness_seconds))
            priority = min(1.0, 0.55 * schedule.priority + 0.25 * stale_boost + 0.20 * schedule.regression_risk)
            reason = "due"
            if stale_boost >= 1.0:
                reason += ":stale_evidence"
            if schedule.regression_risk >= 0.5:
                reason += ":regression_risk"
            item = DevelopmentalQueueItem(
                schedule_id=schedule.id,
                capability=schedule.capability,
                due_at=schedule.next_due_at,
                priority_score=priority,
                reason=reason,
            )
            self.store.put(item, event_type="DEVELOPMENTAL_QUEUE_ITEM_CREATED", evidence_refs=evidence_refs)
            queued.append(item)
        return sorted(queued, key=lambda item: (-item.priority_score, item.created_at, str(item.id)))

    def start_run(
        self,
        item: DevelopmentalQueueItem,
        *,
        estimated_compute_seconds: float,
        estimated_tokens: int,
        estimated_api_cost_units: float,
        evidence_refs: list[str],
        now: datetime,
    ) -> DevelopmentalRunRecord:
        if self.backoff.active(item.capability, now=now):
            raise ValueError("developmental_backoff_active")
        self.budgets.consume(
            compute_seconds=estimated_compute_seconds,
            tokens=estimated_tokens,
            api_cost_units=estimated_api_cost_units,
            evidence_refs=evidence_refs,
        )
        request = DevelopmentalRunRequest(
            queue_item_id=item.id,
            schedule_id=item.schedule_id,
            capability=item.capability,
            estimated_compute_seconds=estimated_compute_seconds,
            estimated_tokens=estimated_tokens,
            estimated_api_cost_units=estimated_api_cost_units,
            evidence_refs=list(evidence_refs),
        )
        self.store.put(request, event_type="DEVELOPMENTAL_RUN_REQUESTED", evidence_refs=evidence_refs)
        record = DevelopmentalRunRecord(
            request_id=request.id,
            schedule_id=item.schedule_id,
            capability=item.capability,
            state="running",
            started_at=now,
        )
        self.store.put(record, event_type="DEVELOPMENTAL_RUN_STARTED", evidence_refs=evidence_refs)
        return record

    def run_assessment(
        self,
        *,
        item: DevelopmentalQueueItem,
        benchmark: CapabilityBenchmark,
        baseline: BenchmarkRun,
        current: BenchmarkRun,
        estimated_compute_seconds: float,
        estimated_tokens: int,
        estimated_api_cost_units: float,
        evidence_refs: list[str],
        now: datetime,
    ) -> CapabilityAssessment:
        run = self.start_run(
            item,
            estimated_compute_seconds=estimated_compute_seconds,
            estimated_tokens=estimated_tokens,
            estimated_api_cost_units=estimated_api_cost_units,
            evidence_refs=evidence_refs,
            now=now,
        )
        try:
            assessment = self.cycle.assess_capability(
                benchmark=benchmark,
                baseline=baseline,
                current=current,
                evidence_refs=evidence_refs,
            )
        except Exception as exc:
            run.state = "failed"
            run.error = str(exc)
            run.completed_at = now
            run.updated_at = now
            self.store.put(run, event_type="DEVELOPMENTAL_RUN_FAILED", evidence_refs=evidence_refs)
            self.backoff.fail(item.capability, str(exc), now=now, evidence_refs=evidence_refs)
            raise

        run.state = "completed"
        run.assessment_cycle_id = assessment.cycle_id
        run.completed_at = now
        run.updated_at = now
        self.store.put(run, event_type="DEVELOPMENTAL_RUN_COMPLETED", evidence_refs=evidence_refs)
        self.backoff.clear(item.capability, now=now, evidence_refs=evidence_refs)
        self._advance_schedule(item.schedule_id, now=now, evidence_refs=evidence_refs)
        return assessment

    def _advance_schedule(self, schedule_id: UUID, *, now: datetime, evidence_refs: list[str]) -> None:
        schedule = next((item for item in self.schedules() if item.id == schedule_id), None)
        if schedule is None:
            raise ValueError("unknown_developmental_schedule")
        schedule.last_run_at = now
        schedule.last_evidence_at = now
        schedule.next_due_at = now + timedelta(seconds=schedule.cadence_seconds)
        schedule.updated_at = now
        self.store.put(schedule, event_type="DEVELOPMENTAL_SCHEDULE_ADVANCED", evidence_refs=evidence_refs)

    def snapshot(self) -> dict[str, object]:
        budget = self.budgets.current()
        return {
            "schedules": len(self.schedules()),
            "queue_items": len(self.store.list("DevelopmentalQueueItem")),
            "runs": len(self.store.list("DevelopmentalRunRecord")),
            "active_backoffs": len([
                item for item in self.store.list("DevelopmentalBackoffState")
                if item.backoff_until is not None and item.backoff_until > utcnow()
            ]),
            "budget": budget,
            "authority": "assessment_only_no_self_approval_mutation_merge_deploy_or_external_action",
        }

    def approve_plan(self, *_args, **_kwargs) -> None:
        raise ValueError("developmental_scheduler_cannot_approve_plans_or_experiments")

    def direct_self_modify(self, *_args, **_kwargs) -> None:
        raise ValueError("developmental_scheduler_cannot_mutate_merge_or_deploy")
