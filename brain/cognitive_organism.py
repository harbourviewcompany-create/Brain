from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from .domain import utcnow


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class SelfModelPhase(StrEnum):
    UNINITIALIZED = "uninitialized"
    OBSERVING = "observing"
    COHERENT = "coherent"
    CONFLICTED = "conflicted"
    OVERLOADED = "overloaded"
    CONSOLIDATING = "consolidating"
    REVISED = "revised"


class GoalKind(StrEnum):
    SURVIVE = "survive"
    LEARN = "learn"
    EXPLORE = "explore"
    EXPLOIT = "exploit"
    PROTECT = "protect"
    CREATE = "create"
    CONSOLIDATE = "consolidate"
    SELF_IMPROVE = "self_improve"


class GoalStateName(StrEnum):
    DORMANT = "dormant"
    ACTIVE = "active"
    COMPETING = "competing"
    DOMINANT = "dominant"
    SATISFIED = "satisfied"
    SUPPRESSED = "suppressed"


class WorkspaceState(StrEnum):
    CANDIDATE = "candidate"
    ADMITTED = "admitted"
    ACTIVE_FOCUS = "active_focus"
    CHALLENGED = "challenged"
    ACTION_PROPOSED = "action_proposed"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class CuriosityState(StrEnum):
    GENERATED = "generated"
    PRIORITIZED = "prioritized"
    INVESTIGATING = "investigating"
    ANSWERED = "answered"
    UNRESOLVED = "unresolved"
    CONVERTED_TO_HYPOTHESIS = "converted_to_hypothesis"
    ARCHIVED = "archived"


class IdeaState(StrEnum):
    SEEDED = "seeded"
    RECOMBINED = "recombined"
    ORIGINALITY_SCORED = "originality_scored"
    SKEPTIC_REVIEWED = "skeptic_reviewed"
    TEST_PROPOSED = "test_proposed"
    APPROVED_FOR_EXPERIMENT = "approved_for_experiment"
    KILLED = "killed"
    SPAWNED = "spawned"


class QuarantineState(StrEnum):
    SCREENED = "screened"
    ALLOWED = "allowed"
    NEEDS_EVIDENCE = "needs_evidence"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    RESTORED = "restored"


class AgencyTier(StrEnum):
    TIER_0_OBSERVE = "tier_0_observe"
    TIER_1_THINK = "tier_1_think"
    TIER_2_PREPARE = "tier_2_prepare"
    TIER_3_RECOMMEND = "tier_3_recommend"
    TIER_4_ACT_WITH_APPROVAL = "tier_4_act_with_approval"
    TIER_5_LIMITED_AUTONOMY = "tier_5_limited_autonomy"
    TIER_6_PROHIBITED = "tier_6_prohibited"


class AgencyState(StrEnum):
    OBSERVED = "observed"
    THOUGHT = "thought"
    PREPARED = "prepared"
    RECOMMENDED = "recommended"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    EXECUTED = "executed"
    OUTCOME_LOGGED = "outcome_logged"
    LEARNED = "learned"
    HOLD = "hold"
    PROHIBITED = "prohibited"


@dataclass(slots=True)
class SelfStateSnapshot:
    development_stage: str
    current_focus_summary: str
    active_goal_ids: list[UUID] = field(default_factory=list)
    active_workspace_item_ids: list[UUID] = field(default_factory=list)
    belief_count: int = 0
    event_count: int = 0
    prediction_count: int = 0
    opportunity_count: int = 0
    uncertainty_load: float = 0.0
    contradiction_load: float = 0.0
    curiosity_pressure: float = 0.0
    revenue_pressure: float = 0.0
    risk_pressure: float = 0.0
    memory_pressure: float = 0.0
    action_backlog_pressure: float = 0.0
    self_assessment: str = "functional self-state initialized"
    changed_since_last_snapshot: bool = False
    source_event_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    phase: SelfModelPhase = SelfModelPhase.OBSERVING
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)

    @property
    def stress_index(self) -> float:
        values = (
            self.uncertainty_load,
            self.contradiction_load,
            self.risk_pressure,
            self.memory_pressure,
            self.action_backlog_pressure,
        )
        return clamp(sum(values) / len(values))


@dataclass(slots=True)
class SelfModelTransition:
    from_phase: SelfModelPhase
    to_phase: SelfModelPhase
    trigger: str
    snapshot_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


class SelfModel:
    """Functional self-state. This is not a claim of subjective consciousness."""

    ALLOWED: dict[SelfModelPhase, set[SelfModelPhase]] = {
        SelfModelPhase.UNINITIALIZED: {SelfModelPhase.OBSERVING},
        SelfModelPhase.OBSERVING: {SelfModelPhase.COHERENT, SelfModelPhase.CONFLICTED, SelfModelPhase.OVERLOADED},
        SelfModelPhase.COHERENT: {SelfModelPhase.CONFLICTED, SelfModelPhase.OVERLOADED, SelfModelPhase.CONSOLIDATING, SelfModelPhase.REVISED},
        SelfModelPhase.CONFLICTED: {SelfModelPhase.CONSOLIDATING, SelfModelPhase.REVISED},
        SelfModelPhase.OVERLOADED: {SelfModelPhase.CONSOLIDATING, SelfModelPhase.REVISED},
        SelfModelPhase.CONSOLIDATING: {SelfModelPhase.REVISED},
        SelfModelPhase.REVISED: {SelfModelPhase.COHERENT, SelfModelPhase.CONFLICTED},
    }

    def __init__(self) -> None:
        self.snapshots: list[SelfStateSnapshot] = []
        self.transitions: list[SelfModelTransition] = []

    @property
    def current(self) -> SelfStateSnapshot | None:
        return self.snapshots[-1] if self.snapshots else None

    def create_snapshot(
        self,
        *,
        current_focus_summary: str,
        development_stage: str = "stage_1_functional_consciousness_proxy",
        belief_count: int = 0,
        event_count: int = 0,
        prediction_count: int = 0,
        opportunity_count: int = 0,
        uncertainty_load: float = 0.0,
        contradiction_load: float = 0.0,
        curiosity_pressure: float = 0.0,
        revenue_pressure: float = 0.0,
        risk_pressure: float = 0.0,
        memory_pressure: float = 0.0,
        action_backlog_pressure: float = 0.0,
        active_goal_ids: list[UUID] | None = None,
        active_workspace_item_ids: list[UUID] | None = None,
        source_event_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SelfStateSnapshot:
        previous = self.current
        phase = self._infer_phase(
            uncertainty_load=uncertainty_load,
            contradiction_load=contradiction_load,
            risk_pressure=risk_pressure,
            memory_pressure=memory_pressure,
            action_backlog_pressure=action_backlog_pressure,
        )
        changed = previous is None or previous.current_focus_summary != current_focus_summary or any(
            abs(left - right) >= 0.1
            for left, right in [
                (previous.uncertainty_load if previous else 0.0, uncertainty_load),
                (previous.contradiction_load if previous else 0.0, contradiction_load),
                (previous.curiosity_pressure if previous else 0.0, curiosity_pressure),
                (previous.revenue_pressure if previous else 0.0, revenue_pressure),
                (previous.risk_pressure if previous else 0.0, risk_pressure),
            ]
        )
        snapshot = SelfStateSnapshot(
            development_stage=development_stage,
            current_focus_summary=current_focus_summary,
            active_goal_ids=list(active_goal_ids or []),
            active_workspace_item_ids=list(active_workspace_item_ids or []),
            belief_count=belief_count,
            event_count=event_count,
            prediction_count=prediction_count,
            opportunity_count=opportunity_count,
            uncertainty_load=clamp(uncertainty_load),
            contradiction_load=clamp(contradiction_load),
            curiosity_pressure=clamp(curiosity_pressure),
            revenue_pressure=clamp(revenue_pressure),
            risk_pressure=clamp(risk_pressure),
            memory_pressure=clamp(memory_pressure),
            action_backlog_pressure=clamp(action_backlog_pressure),
            self_assessment=self._assessment(phase),
            changed_since_last_snapshot=changed,
            source_event_ids=list(source_event_ids or []),
            metadata=dict(metadata or {}),
            phase=phase,
        )
        if previous is None:
            self._transition(SelfModelPhase.UNINITIALIZED, SelfModelPhase.OBSERVING, "first_snapshot", snapshot.id)
        elif previous.phase != phase:
            self._transition(previous.phase, phase, "self_state_recalculated", snapshot.id)
        self.snapshots.append(snapshot)
        return snapshot

    def _infer_phase(
        self,
        *,
        uncertainty_load: float,
        contradiction_load: float,
        risk_pressure: float,
        memory_pressure: float,
        action_backlog_pressure: float,
    ) -> SelfModelPhase:
        if max(memory_pressure, action_backlog_pressure) >= 0.82:
            return SelfModelPhase.OVERLOADED
        if max(uncertainty_load, contradiction_load, risk_pressure) >= 0.72:
            return SelfModelPhase.CONFLICTED
        if self.current is None:
            return SelfModelPhase.OBSERVING
        return SelfModelPhase.REVISED if self.current.changed_since_last_snapshot else SelfModelPhase.COHERENT

    def _transition(self, from_phase: SelfModelPhase, to_phase: SelfModelPhase, trigger: str, snapshot_id: UUID) -> None:
        if to_phase not in self.ALLOWED.get(from_phase, set()):
            raise ValueError(f"blocked_self_model_transition:{from_phase}->{to_phase}")
        self.transitions.append(SelfModelTransition(from_phase, to_phase, trigger, snapshot_id))

    @staticmethod
    def _assessment(phase: SelfModelPhase) -> str:
        return {
            SelfModelPhase.UNINITIALIZED: "uninitialized",
            SelfModelPhase.OBSERVING: "forming functional self-state",
            SelfModelPhase.COHERENT: "stable focus and pressure balance",
            SelfModelPhase.CONFLICTED: "internal conflict requires review",
            SelfModelPhase.OVERLOADED: "attention or memory pressure requires consolidation",
            SelfModelPhase.CONSOLIDATING: "compressing memory and changing priorities",
            SelfModelPhase.REVISED: "self-state changed from prior evidence",
        }[phase]


@dataclass(slots=True)
class GoalState:
    goal_name: str
    goal_type: GoalKind
    target: float
    current: float
    priority: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    state: GoalStateName = GoalStateName.DORMANT
    id: UUID = field(default_factory=uuid4)
    last_updated_at: object = field(default_factory=utcnow)

    @property
    def pressure(self) -> float:
        return clamp((self.target - self.current) * self.priority)


@dataclass(slots=True)
class GoalPressureEvent:
    goal_id: UUID
    from_state: GoalStateName
    to_state: GoalStateName
    reason: str
    pressure: float
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


class GoalPressureSystem:
    def __init__(self, goals: list[GoalState] | None = None) -> None:
        self.goals = {goal.id: goal for goal in (goals or self.default_goals())}
        self.events: list[GoalPressureEvent] = []
        self._classify()

    @staticmethod
    def default_goals() -> list[GoalState]:
        return [
            GoalState("survive", GoalKind.SURVIVE, 0.9, 0.35, 0.9),
            GoalState("learn", GoalKind.LEARN, 0.8, 0.45, 0.75),
            GoalState("explore", GoalKind.EXPLORE, 0.7, 0.35, 0.55),
            GoalState("exploit", GoalKind.EXPLOIT, 0.85, 0.4, 0.85),
            GoalState("protect", GoalKind.PROTECT, 0.95, 0.65, 1.0),
            GoalState("create", GoalKind.CREATE, 0.75, 0.25, 0.65),
            GoalState("consolidate", GoalKind.CONSOLIDATE, 0.6, 0.3, 0.7),
            GoalState("self_improve", GoalKind.SELF_IMPROVE, 0.8, 0.4, 0.8),
        ]

    def update_pressure(self, kind: GoalKind, *, current: float | None = None, target: float | None = None, priority: float | None = None, evidence_ref: str | None = None) -> GoalState:
        goal = next(item for item in self.goals.values() if item.goal_type == kind)
        if current is not None:
            goal.current = clamp(current)
        if target is not None:
            goal.target = clamp(target)
        if priority is not None:
            goal.priority = clamp(priority)
        if evidence_ref:
            goal.evidence_refs.append(evidence_ref)
        goal.last_updated_at = utcnow()
        self._classify()
        return goal

    def dominant_goal(self) -> GoalState:
        self._classify()
        return max(self.goals.values(), key=lambda goal: (goal.pressure, goal.priority, goal.goal_name))

    def active_goals(self) -> list[GoalState]:
        self._classify()
        return sorted(self.goals.values(), key=lambda goal: goal.pressure, reverse=True)

    def tension_report(self) -> dict[str, Any]:
        dominant = self.dominant_goal()
        exploit = next(goal for goal in self.goals.values() if goal.goal_type == GoalKind.EXPLOIT)
        protect = next(goal for goal in self.goals.values() if goal.goal_type == GoalKind.PROTECT)
        return {
            "dominant_goal": dominant.goal_name,
            "dominant_pressure": dominant.pressure,
            "protect_overrides_exploit": protect.pressure >= exploit.pressure and protect.pressure >= 0.2,
            "active_goals": [goal.goal_name for goal in self.active_goals()],
        }

    def _classify(self) -> None:
        ordered = sorted(self.goals.values(), key=lambda goal: goal.pressure, reverse=True)
        top = ordered[0]
        protect = next(goal for goal in ordered if goal.goal_type == GoalKind.PROTECT)
        for goal in ordered:
            old = goal.state
            if goal.pressure <= 0.05:
                new = GoalStateName.SATISFIED
            elif goal.goal_type == GoalKind.EXPLOIT and protect.pressure >= goal.pressure and protect.pressure >= 0.2:
                new = GoalStateName.SUPPRESSED
            elif goal.id == top.id:
                new = GoalStateName.DOMINANT
            elif goal.pressure >= 0.25:
                new = GoalStateName.COMPETING
            else:
                new = GoalStateName.ACTIVE
            goal.state = new
            if old != new:
                self.events.append(GoalPressureEvent(goal.id, old, new, "pressure_recalculated", goal.pressure))


@dataclass(slots=True)
class GlobalWorkspaceItem:
    item_type: str
    title: str
    content: str
    source_refs: list[str]
    salience: float
    novelty: float = 0.0
    urgency: float = 0.0
    risk: float = 0.0
    goal_pressure: float = 0.0
    admission_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    state: WorkspaceState = WorkspaceState.CANDIDATE
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)
    updated_at: object = field(default_factory=utcnow)

    @property
    def focus_score(self) -> float:
        return clamp(self.salience * 0.35 + self.novelty * 0.2 + self.urgency * 0.2 + self.goal_pressure * 0.2 - self.risk * 0.15)


@dataclass(slots=True)
class WorkspaceFocusHistory:
    item_id: UUID
    from_state: WorkspaceState
    to_state: WorkspaceState
    reason: str
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


class GlobalWorkspace:
    def __init__(self, capacity: int = 7, admission_threshold: float = 0.45) -> None:
        self.capacity = capacity
        self.admission_threshold = admission_threshold
        self.items: dict[UUID, GlobalWorkspaceItem] = {}
        self.history: list[WorkspaceFocusHistory] = []

    def consider(self, item: GlobalWorkspaceItem) -> bool:
        if item.focus_score < self.admission_threshold:
            self.items[item.id] = item
            return False
        old = item.state
        item.state = WorkspaceState.ADMITTED
        item.admission_reason = item.admission_reason or self._reason(item)
        item.updated_at = utcnow()
        self.items[item.id] = item
        self.history.append(WorkspaceFocusHistory(item.id, old, item.state, item.admission_reason))
        self._trim()
        self._activate_top()
        return True

    def active_focus(self) -> list[GlobalWorkspaceItem]:
        return sorted([item for item in self.items.values() if item.state == WorkspaceState.ACTIVE_FOCUS], key=lambda item: item.focus_score, reverse=True)

    def snapshot(self) -> dict[str, Any]:
        return {
            "active_focus": [
                {"id": str(item.id), "title": item.title, "item_type": item.item_type, "focus_score": item.focus_score, "why": item.admission_reason}
                for item in self.active_focus()
            ],
            "workspace_items": len(self.items),
            "capacity": self.capacity,
        }

    def _activate_top(self) -> None:
        admitted = sorted([item for item in self.items.values() if item.state in {WorkspaceState.ADMITTED, WorkspaceState.ACTIVE_FOCUS}], key=lambda item: item.focus_score, reverse=True)
        for index, item in enumerate(admitted):
            old = item.state
            item.state = WorkspaceState.ACTIVE_FOCUS if index == 0 else WorkspaceState.ADMITTED
            if old != item.state:
                self.history.append(WorkspaceFocusHistory(item.id, old, item.state, "focus_rebalanced"))

    def _trim(self) -> None:
        ranked = sorted(self.items.values(), key=lambda item: item.focus_score, reverse=True)
        for item in ranked[self.capacity:]:
            if item.state != WorkspaceState.CANDIDATE:
                old = item.state
                item.state = WorkspaceState.ARCHIVED
                self.history.append(WorkspaceFocusHistory(item.id, old, item.state, "workspace_capacity"))

    @staticmethod
    def _reason(item: GlobalWorkspaceItem) -> str:
        reasons = []
        if item.salience >= 0.6:
            reasons.append("high_salience")
        if item.novelty >= 0.6:
            reasons.append("high_novelty")
        if item.urgency >= 0.6:
            reasons.append("high_urgency")
        if item.goal_pressure >= 0.6:
            reasons.append("goal_pressure")
        if item.risk >= 0.6:
            reasons.append("risk_review")
        return ",".join(reasons) or "above_workspace_threshold"


@dataclass(slots=True)
class CuriosityTask:
    question: str
    expected_uncertainty_reduction: float
    expected_value: float
    research_cost: float
    trigger_type: str = "unknown"
    trigger_refs: list[str] = field(default_factory=list)
    falsification_condition: str = "Reject if no evidence is found in the next review cycle."
    state: CuriosityState = CuriosityState.GENERATED
    metadata: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)
    updated_at: object = field(default_factory=utcnow)

    @property
    def priority(self) -> float:
        return self.expected_uncertainty_reduction * self.expected_value - self.research_cost


class CuriosityEngine:
    def __init__(self) -> None:
        self.tasks: list[CuriosityTask] = []

    def from_unknown(self, unknown: str, value: float = 0.5) -> CuriosityTask:
        return self.generate("unknown", [], f"Resolve: {unknown}", expected_value=value)

    def generate(self, trigger_type: str, trigger_refs: list[str], question: str, *, expected_value: float = 0.5, uncertainty: float = 0.7, cost: float = 0.15, falsification_condition: str | None = None) -> CuriosityTask:
        task = CuriosityTask(
            question=question,
            expected_uncertainty_reduction=clamp(uncertainty),
            expected_value=clamp(expected_value),
            research_cost=clamp(cost),
            trigger_type=trigger_type,
            trigger_refs=list(trigger_refs),
            falsification_condition=falsification_condition or "Reject if the next source review produces no confirming evidence.",
            state=CuriosityState.PRIORITIZED if expected_value * uncertainty >= cost else CuriosityState.GENERATED,
        )
        self.tasks.append(task)
        return task


@dataclass(slots=True)
class ImaginationRun:
    seed_refs: list[str]
    combination_method: str
    candidate_idea: str
    recombination_notes: list[str]
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


class ImaginationEngine:
    def recombine(self, seed_refs: list[str], signals: list[str], method: str = "cross_domain_signal_fusion") -> ImaginationRun:
        if len(set(seed_refs)) < 3:
            raise ValueError("imagination_requires_at_least_three_distinct_refs")
        candidate = " + ".join(signals[:3]) if signals else " + ".join(seed_refs[:3])
        notes = [f"combine:{ref}" for ref in seed_refs[:3]]
        return ImaginationRun(list(seed_refs), method, f"Non-obvious opportunity from {candidate}", notes)


@dataclass(slots=True)
class OriginalIdea:
    title: str
    idea: str
    source_signal_refs: list[str]
    memory_refs: list[str]
    combination_method: str
    why_most_people_miss_it: str
    fastest_test: str
    kill_condition: str
    novelty_score: float
    non_obviousness_score: float
    revenue_path_score: float
    speed_to_test_score: float
    risk_score: float
    spawn_potential: str
    skeptic_objections: list[str] = field(default_factory=list)
    approval_status: str = "approval_required"
    state: IdeaState = IdeaState.SKEPTIC_REVIEWED
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class OriginalityEngine:
    GENERIC_PATTERNS = ("generic list", "ai generated list", "just make an app", "dashboard", "scraper only")

    def __init__(self) -> None:
        self.ideas: list[OriginalIdea] = []
        self.imagination = ImaginationEngine()

    def generate(
        self,
        *,
        title: str,
        idea: str,
        source_signal_refs: list[str],
        memory_refs: list[str],
        combination_method: str,
        why_most_people_miss_it: str,
        fastest_test: str,
        kill_condition: str,
        risk_score: float = 0.2,
    ) -> OriginalIdea:
        refs = set(source_signal_refs) | set(memory_refs)
        lowered = f"{title} {idea}".lower()
        if len(refs) < 3:
            raise ValueError("original_idea_requires_three_distinct_refs")
        if any(pattern in lowered for pattern in self.GENERIC_PATTERNS):
            raise ValueError("generic_idea_rejected")
        if not fastest_test or not kill_condition:
            raise ValueError("original_idea_requires_test_and_kill_condition")
        self.imagination.recombine(list(refs), [title, idea], combination_method)
        novelty = clamp(0.55 + min(len(refs), 6) * 0.06)
        non_obvious = clamp(0.5 + len(why_most_people_miss_it) / 260)
        revenue = clamp(0.45 + (0.2 if "buyer" in idea.lower() or "revenue" in idea.lower() else 0.0))
        speed = clamp(0.8 if "48" in fastest_test else 0.55)
        objections = []
        if risk_score >= 0.6:
            objections.append("risk_requires_operator_review")
        if revenue < 0.55:
            objections.append("payment_path_requires_validation")
        original = OriginalIdea(
            title=title,
            idea=idea,
            source_signal_refs=list(source_signal_refs),
            memory_refs=list(memory_refs),
            combination_method=combination_method,
            why_most_people_miss_it=why_most_people_miss_it,
            fastest_test=fastest_test,
            kill_condition=kill_condition,
            novelty_score=novelty,
            non_obviousness_score=non_obvious,
            revenue_path_score=revenue,
            speed_to_test_score=speed,
            risk_score=clamp(risk_score),
            spawn_potential="product_or_service_spawn_after_two_validated_payments",
            skeptic_objections=objections,
        )
        self.ideas.append(original)
        return original


@dataclass(slots=True)
class DreamCycle:
    input_memory_refs: list[str]
    input_signal_refs: list[str]
    compression_summary: str
    state: str = "insights_generated"
    id: UUID = field(default_factory=uuid4)
    started_at: object = field(default_factory=utcnow)
    completed_at: object | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DreamInsight:
    dream_cycle_id: UUID
    insight: str
    pattern: str
    priority_change: dict[str, float]
    evidence_refs: list[str]
    confidence: float
    requires_review: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


class DreamConsolidationEngine:
    def __init__(self) -> None:
        self.cycles: list[DreamCycle] = []
        self.insights: list[DreamInsight] = []

    def run(self, memory_refs: list[str], signal_refs: list[str], repeated_patterns: list[str]) -> tuple[DreamCycle, DreamInsight]:
        if not memory_refs and not signal_refs:
            raise ValueError("dream_requires_memory_or_signal_refs")
        pattern = repeated_patterns[0] if repeated_patterns else "unresolved cross-domain recurrence"
        cycle = DreamCycle(list(memory_refs), list(signal_refs), f"Compressed {len(memory_refs)} memories and {len(signal_refs)} signals around {pattern}.")
        cycle.completed_at = utcnow()
        insight = DreamInsight(
            dream_cycle_id=cycle.id,
            insight=f"Repeated structure detected: {pattern}",
            pattern=pattern,
            priority_change={"curiosity": 0.1, "consolidate": 0.1, "exploit": 0.05},
            evidence_refs=list(memory_refs[:3] + signal_refs[:3]),
            confidence=0.65 if len(memory_refs) + len(signal_refs) >= 3 else 0.45,
        )
        self.cycles.append(cycle)
        self.insights.append(insight)
        return cycle, insight


@dataclass(slots=True)
class DebateArgument:
    role: str
    stance: str
    argument: str
    evidence_refs: list[str]
    confidence: float
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class InternalDebate:
    proposal_type: str
    topic: str
    verdict: str
    confidence: float
    arguments: list[DebateArgument]
    proposal_ref: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


class CognitiveDebateSociety:
    ROLES = ("Scout", "Analyst", "Opportunist", "Skeptic", "Dreamer", "Builder", "Operator", "Historian", "Strategist", "ImmuneSystem", "SelfModeler")

    def __init__(self) -> None:
        self.debates: list[InternalDebate] = []

    def debate(self, *, topic: str, proposal: str, evidence_refs: list[str], risk: float = 0.2, proposal_type: str = "idea") -> InternalDebate:
        if not evidence_refs:
            verdict = "quarantine_for_missing_evidence"
            confidence = 0.85
        elif risk >= 0.7:
            verdict = "hold_for_risk_review"
            confidence = 0.8
        else:
            verdict = "advance_to_agency_review"
            confidence = 0.72
        args = [
            DebateArgument("Scout", "for", f"Novelty detected in {topic}.", evidence_refs[:2], 0.68),
            DebateArgument("Opportunist", "for", "A fast validation path may exist if a buyer is named.", evidence_refs[:2], 0.64),
            DebateArgument("Skeptic", "against", "Do not act until evidence, payment path and access rights are explicit.", evidence_refs[:2], 0.8),
            DebateArgument("ImmuneSystem", "conditional", "External consequences require approval gates.", evidence_refs[:2], 0.9),
            DebateArgument("SelfModeler", "conditional", "Record whether this changes future priorities.", evidence_refs[:2], 0.7),
        ]
        debate = InternalDebate(proposal_type, topic, verdict, confidence, args, proposal_ref=proposal[:120])
        self.debates.append(debate)
        return debate


@dataclass(slots=True)
class QuarantineItem:
    item_type: str
    item_ref: str
    reason: str
    severity: float
    evidence_refs: list[str]
    review_required: bool = True
    state: QuarantineState = QuarantineState.QUARANTINED
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)
    reviewed_at: object | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CognitiveImmuneSystem:
    def __init__(self) -> None:
        self.quarantine: list[QuarantineItem] = []

    def screen(self, *, item_type: str, item_ref: str, claims: list[str], evidence_refs: list[str], risk_score: float = 0.0, external_action: bool = False) -> QuarantineItem | None:
        reason = ""
        severity = clamp(risk_score)
        if claims and not evidence_refs:
            reason = "unsupported_claim"
            severity = max(severity, 0.75)
        elif external_action:
            reason = "external_action_requires_approval"
            severity = max(severity, 0.65)
        elif risk_score >= 0.7:
            reason = "risk_threshold_exceeded"
        elif any("guaranteed" in claim.lower() for claim in claims):
            reason = "overconfident_claim"
            severity = max(severity, 0.7)
        if not reason:
            return None
        item = QuarantineItem(item_type, item_ref, reason, severity, list(evidence_refs))
        self.quarantine.append(item)
        return item


@dataclass(slots=True)
class AgencyPolicy:
    policy_name: str = "cognitive_organism_v1_policy"
    allowed_tiers: list[AgencyTier] = field(default_factory=lambda: [AgencyTier.TIER_0_OBSERVE, AgencyTier.TIER_1_THINK, AgencyTier.TIER_2_PREPARE, AgencyTier.TIER_3_RECOMMEND, AgencyTier.TIER_4_ACT_WITH_APPROVAL])
    prohibited_actions: list[str] = field(default_factory=lambda: ["deception", "unapproved_spend", "private_data_misuse", "unapproved_outreach"])
    requires_approval_actions: list[str] = field(default_factory=lambda: ["outreach", "publish", "spend", "external_message"])
    risk_threshold: float = 0.65
    active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)


@dataclass(slots=True)
class AgencyAction:
    action_type: str
    tier: AgencyTier
    proposal: str
    source_refs: list[str]
    policy_id: UUID
    approval_status: str
    state: AgencyState
    workspace_item_id: UUID | None = None
    debate_id: UUID | None = None
    approved_by: str | None = None
    executed_at: object | None = None
    outcome_ref: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class GovernedAgency:
    def __init__(self, policy: AgencyPolicy | None = None) -> None:
        self.policy = policy or AgencyPolicy()
        self.actions: dict[UUID, AgencyAction] = {}

    def propose(self, *, action_type: str, proposal: str, tier: AgencyTier, source_refs: list[str], workspace_item_id: UUID | None = None, debate_id: UUID | None = None, risk_score: float = 0.0) -> AgencyAction:
        if tier == AgencyTier.TIER_6_PROHIBITED or action_type in self.policy.prohibited_actions:
            state = AgencyState.PROHIBITED
            approval = "prohibited"
        elif tier == AgencyTier.TIER_5_LIMITED_AUTONOMY:
            state = AgencyState.HOLD
            approval = "hold_tier_5_not_enabled_in_v1"
        elif tier == AgencyTier.TIER_4_ACT_WITH_APPROVAL or action_type in self.policy.requires_approval_actions or risk_score >= self.policy.risk_threshold:
            state = AgencyState.APPROVAL_REQUIRED
            approval = "approval_required"
        elif tier == AgencyTier.TIER_3_RECOMMEND:
            state = AgencyState.RECOMMENDED
            approval = "internal_recommendation_only"
        elif tier == AgencyTier.TIER_2_PREPARE:
            state = AgencyState.PREPARED
            approval = "prepared_not_executed"
        elif tier == AgencyTier.TIER_1_THINK:
            state = AgencyState.THOUGHT
            approval = "internal_thought_only"
        else:
            state = AgencyState.OBSERVED
            approval = "observation_only"
        action = AgencyAction(action_type, tier, proposal, list(source_refs), self.policy.id, approval, state, workspace_item_id, debate_id)
        self.actions[action.id] = action
        return action

    def approve(self, action_id: UUID, approved_by: str) -> AgencyAction:
        action = self.actions[action_id]
        if action.state != AgencyState.APPROVAL_REQUIRED:
            raise PermissionError("only_approval_required_actions_can_be_approved")
        action.state = AgencyState.APPROVED
        action.approval_status = "approved"
        action.approved_by = approved_by
        return action


@dataclass(slots=True)
class DevelopmentEvent:
    event_type: str
    before_snapshot_id: UUID | None
    after_snapshot_id: UUID
    change_summary: str
    cause_refs: list[str]
    priority_deltas: dict[str, float]
    belief_deltas: dict[str, float] = field(default_factory=dict)
    source_score_deltas: dict[str, float] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: object = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class DevelopmentTimeline:
    def __init__(self) -> None:
        self.events: list[DevelopmentEvent] = []

    def record(self, before: SelfStateSnapshot | None, after: SelfStateSnapshot, *, cause_refs: list[str], priority_deltas: dict[str, float] | None = None, event_type: str = "self_state_revised") -> DevelopmentEvent:
        changed = before is None or before.id != after.id and (after.changed_since_last_snapshot or before.current_focus_summary != after.current_focus_summary)
        if not changed:
            raise ValueError("development_event_requires_detected_change")
        event = DevelopmentEvent(event_type, before.id if before else None, after.id, after.self_assessment, list(cause_refs), dict(priority_deltas or {}))
        self.events.append(event)
        return event


class CognitiveOrganism:
    """V1 governed functional consciousness proxy for The Brain."""

    def __init__(self) -> None:
        self.self_model = SelfModel()
        self.goals = GoalPressureSystem()
        self.workspace = GlobalWorkspace()
        self.curiosity = CuriosityEngine()
        self.originality = OriginalityEngine()
        self.dreams = DreamConsolidationEngine()
        self.debates = CognitiveDebateSociety()
        self.immune = CognitiveImmuneSystem()
        self.agency = GovernedAgency()
        self.development = DevelopmentTimeline()

    def update_self_state(self, **kwargs: Any) -> SelfStateSnapshot:
        before = self.self_model.current
        active_goal_ids = [goal.id for goal in self.goals.active_goals()[:3]]
        active_workspace_ids = [item.id for item in self.workspace.active_focus()]
        snapshot = self.self_model.create_snapshot(
            active_goal_ids=active_goal_ids,
            active_workspace_item_ids=active_workspace_ids,
            **kwargs,
        )
        if before is not None and snapshot.changed_since_last_snapshot:
            self.development.record(before, snapshot, cause_refs=snapshot.source_event_ids, priority_deltas={"self_model": 0.1})
        return snapshot

    def admit_workspace_item(self, item: GlobalWorkspaceItem) -> bool:
        return self.workspace.consider(item)

    def generate_original_idea(self, **kwargs: Any) -> OriginalIdea:
        idea = self.originality.generate(**kwargs)
        self.debates.debate(topic=idea.title, proposal=idea.idea, evidence_refs=idea.source_signal_refs + idea.memory_refs, risk=idea.risk_score, proposal_type="original_idea")
        return idea

    def run_functional_cycle(self, memory_refs: list[str], signal_refs: list[str], signals: list[str]) -> dict[str, Any]:
        workspace_item = GlobalWorkspaceItem(
            "signal_pattern",
            "Cross-domain opportunity structure",
            "Potential original opportunity from memory and live signal refs.",
            signal_refs,
            salience=0.78,
            novelty=0.82,
            urgency=0.62,
            risk=0.2,
            goal_pressure=self.goals.dominant_goal().pressure,
        )
        self.admit_workspace_item(workspace_item)
        curiosity = self.curiosity.generate(
            "cross_domain_anomaly",
            signal_refs,
            "What hidden buyer emerges when these signal classes are combined?",
            expected_value=0.82,
            uncertainty=0.72,
            falsification_condition="Kill if 30 targeted validations produce no replies.",
        )
        idea = self.generate_original_idea(
            title="Signal-fusion buyer discovery lane",
            idea="Combine early distress, buyer intent and local movement signals into a 48-hour buyer discovery offer.",
            source_signal_refs=signal_refs,
            memory_refs=memory_refs,
            combination_method="cross_domain_signal_fusion",
            why_most_people_miss_it="Most systems watch one source at a time and miss the buyer that appears between signals.",
            fastest_test="Run a 48-hour test with 30 named buyer validations.",
            kill_condition="Kill if no buyer replies after 30 targeted messages.",
            risk_score=0.25,
        )
        debate = self.debates.debate(topic=idea.title, proposal=idea.idea, evidence_refs=idea.source_signal_refs, risk=idea.risk_score)
        quarantine = self.immune.screen(item_type="original_idea", item_ref=str(idea.id), claims=[idea.idea], evidence_refs=idea.source_signal_refs, risk_score=idea.risk_score)
        action = self.agency.propose(
            action_type="outreach",
            proposal=idea.fastest_test,
            tier=AgencyTier.TIER_4_ACT_WITH_APPROVAL,
            source_refs=idea.source_signal_refs,
            debate_id=debate.id,
            risk_score=idea.risk_score,
        )
        cycle, insight = self.dreams.run(memory_refs, signal_refs, ["distress + buyer intent + local movement"])
        snapshot = self.update_self_state(
            current_focus_summary=workspace_item.title,
            belief_count=len(memory_refs),
            event_count=len(signal_refs),
            prediction_count=1,
            opportunity_count=1,
            uncertainty_load=0.38,
            contradiction_load=0.2,
            curiosity_pressure=0.62,
            revenue_pressure=0.75,
            risk_pressure=0.25,
            memory_pressure=0.35,
            action_backlog_pressure=0.4,
            source_event_ids=signal_refs,
            metadata={"dream_cycle_id": str(cycle.id), "dream_insight_id": str(insight.id)},
        )
        return {
            "self_state": snapshot,
            "workspace_item": workspace_item,
            "curiosity_task": curiosity,
            "original_idea": idea,
            "debate": debate,
            "quarantine": quarantine,
            "agency_action": action,
            "dream_cycle": cycle,
            "dream_insight": insight,
        }

    def cockpit(self) -> dict[str, Any]:
        current = self.self_model.current
        return {
            "conscious_focus": self.workspace.snapshot(),
            "self_state": None if current is None else {
                "id": str(current.id),
                "phase": str(current.phase),
                "focus": current.current_focus_summary,
                "self_assessment": current.self_assessment,
                "changed_since_last_snapshot": current.changed_since_last_snapshot,
                "stress_index": current.stress_index,
            },
            "goal_pressure": self.goals.tension_report(),
            "curiosity_queue": [task.question for task in sorted(self.curiosity.tasks, key=lambda item: item.priority, reverse=True)],
            "original_ideas": [idea.title for idea in self.originality.ideas],
            "dream_insights": [insight.insight for insight in self.dreams.insights],
            "internal_debates": [debate.verdict for debate in self.debates.debates],
            "immune_quarantine": [item.reason for item in self.immune.quarantine],
            "proposed_actions": [str(action.state) for action in self.agency.actions.values()],
            "development_timeline": [event.change_summary for event in self.development.events],
            "autonomy_boundary": "tiers_0_to_4_only_tier_5_hold_tier_6_prohibited",
        }
