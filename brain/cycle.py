from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Protocol
from uuid import UUID, uuid4

from .attention import AttentionMarket, AttentionSignal
from .beliefs import BeliefEngine
from .cognitive_state import HomeostaticState, NeuromodulatorState
from .contradiction import ContradictionEngine
from .domain import Belief, Evidence, Observation, utcnow
from .events import BrainEvent
from .homeostasis import HomeostasisEngine
from .hydrate import hydrate_belief_cache
from .learning import (
    LearningService,
    attribute_capital_or_result_outcome,
    emit_predictions_for_selected_tasks,
)
from .logging_config import get_logger
from .metabolism import CapitalLedger, MetabolismEngine
from .projections import default_projection_engine, incremental_checkpoint
from .scheduler import CognitiveScheduler, CognitiveTask
from .working_memory import WorkingMemory

from .affect import AffectAppraisalService, AppraisalInput, emotional_state_to_event
from .circadian import CircadianClock, circadian_forced_wake_event, circadian_phase_changed_event
from .executive import (
    CognitiveControlResource,
    ExecutiveControlService,
    ResponseCandidate,
    ResponseSource,
    executive_decision_to_event,
)
from .hedonic import HedonicSystem, pain_signal_to_event, reward_prediction_error_to_event
from .perception import Modality, PerceptionService, TextPerceptionEncoder, percept_to_event
from .theory_of_mind import TheoryOfMindService, attributed_belief_to_event

log = get_logger("cycle")


class AppendableEventStore(Protocol):
    def append(self, event: BrainEvent) -> None: ...
    def read_all(self, *, limit: int | None = None) -> list[BrainEvent]: ...


class CheckpointStore(Protocol):
    def save(
        self,
        projection_name: str,
        *,
        last_event_id: UUID | None,
        event_count: int,
        state: dict[str, Any],
    ) -> None: ...


@dataclass(slots=True)
class CognitiveStimulus:
    content: str
    source_id: str
    claim: str
    source_reliability: float = 0.5
    supports: bool = True
    belief_id: UUID | None = None
    belief_statement: str | None = None
    belief_confidence: float = 0.5
    commercial_upside: float = 0.0
    novelty: float = 0.5
    urgency: float = 0.0
    contradiction_value: float = 0.0
    uncertainty_reduction: float = 0.5
    noise_probability: float = 0.2
    operator_burden: float = 0.0
    capital_outcome_amount: float = 0.0
    capital_outcome_source: str | None = None
    outcome_action_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CognitiveCycleResult:
    cycle_id: UUID
    observation_id: UUID
    evidence_id: UUID
    belief_id: UUID
    attention_score: float
    contradiction_detected: bool
    task_ids: list[UUID]
    event_ids: list[UUID]
    working_memory_size: int = 0
    evicted_count: int = 0
    emotion_label: str | None = None
    emotion_valence: float | None = None
    circadian_phase: str | None = None
    executive_override_attempted: bool | None = None
    executive_override_succeeded: bool | None = None
    perceived_novelty: float | None = None
    agent_trust: float | None = None
    capital_balance: float | None = None
    budget_pressure: float | None = None
    capital_starving: bool | None = None
    prediction_ids: list[UUID] = field(default_factory=list)
    attribution_recorded: bool = False


class CognitiveCycle:
    """One complete cognition pass over a structured stimulus."""

    def __init__(
        self,
        event_store: AppendableEventStore,
        *,
        checkpoint_store: CheckpointStore | None = None,
        attention_threshold: float = 0.0,
        cognitive_budget: int = 2,
        working_memory: WorkingMemory | None = None,
        working_memory_capacity: int = 7,
        circadian: CircadianClock | None = None,
        affect: AffectAppraisalService | None = None,
        hedonic: HedonicSystem | None = None,
        theory_of_mind: TheoryOfMindService | None = None,
        executive: ExecutiveControlService | None = None,
        perception: PerceptionService | None = None,
        control_resource: CognitiveControlResource | None = None,
        capital_ledger: CapitalLedger | None = None,
        metabolism: MetabolismEngine | None = None,
        homeostasis: HomeostasisEngine | None = None,
        learning: LearningService | None = None,
    ) -> None:
        self.event_store = event_store
        self.checkpoint_store = checkpoint_store
        self.attention = AttentionMarket()
        self.beliefs = BeliefEngine()
        self.contradictions = ContradictionEngine()
        self.scheduler = CognitiveScheduler()
        self.modulation = NeuromodulatorState()
        self.attention_threshold = attention_threshold
        self.cognitive_budget = cognitive_budget
        self.working_memory = working_memory or WorkingMemory(capacity=working_memory_capacity)
        self._belief_cache: dict[UUID, Belief] = {}
        self._projection = default_projection_engine()
        self.learning = learning
        # action_id (task.id) -> prediction_id for outcome attribution across ticks
        self._open_predictions_by_action: dict[UUID, UUID] = {}

        self.circadian = circadian or CircadianClock()
        self.affect = affect or AffectAppraisalService()
        self.hedonic = hedonic or HedonicSystem()
        self.theory_of_mind = theory_of_mind or TheoryOfMindService()
        self.executive = executive or ExecutiveControlService()
        self.control_resource = control_resource or CognitiveControlResource()
        self.perception = perception or self._default_perception_service()

        self.capital_ledger = capital_ledger
        self.metabolism = metabolism or MetabolismEngine()
        self.homeostasis = homeostasis or HomeostasisEngine()
        self.homeostatic_state = HomeostaticState()

    @staticmethod
    def _default_perception_service() -> PerceptionService:
        service = PerceptionService()
        service.register(TextPerceptionEncoder())
        return service

    def register_belief(self, belief: Belief) -> None:
        """Adopt a belief the database already holds into the working cache.

        Cache-only, deliberately. Every caller of this is a resume path -- the
        API's inline resume, the worker's, and build_runner() -- loading what
        some other writer already committed. Persisting here wrote that
        snapshot straight back through save(), which updates the row
        unconditionally: so a belief revised by an unguarded writer (POST
        /learn is not lease-guarded) between the hydrate and the moment this
        loop reached it was silently overwritten with the older version this
        process had just read. A resume must not be a write.

        The cognition paths that genuinely author beliefs call
        _persist_belief() themselves; they are unaffected.
        """

        self._belief_cache[belief.id] = belief

    def _persist_belief(self, belief: Belief) -> None:
        """Write a belief through to the durable projection, when there is one.

        The cycle appends events for everything it does, but the ``beliefs``
        table that ``GET /beliefs`` reads is only written by ``save()``. Without
        this, a cycle running against PostgreSQL produced a durable event stream
        whose belief projection was never updated, so worker-created beliefs
        were invisible to the API and vanished from the working set on restart.

        In-memory stores get the same call and simply keep their dict in step.
        """

        saver = getattr(self.event_store, "save", None)
        if not callable(saver):
            return
        try:
            saver(belief)
        except Exception:
            log.exception("belief projection could not be persisted", extra={"belief_id": str(belief.id)})

    def hydrate_beliefs(self, *, from_checkpoint: bool = True) -> int:
        return hydrate_belief_cache(
            self._belief_cache,
            self.event_store,
            self.checkpoint_store,
            from_checkpoint=from_checkpoint,
        )

    def _blend_modulation(self, source: NeuromodulatorState, weight: float) -> None:
        for name in ("dopamine", "norepinephrine", "serotonin", "acetylcholine", "stress"):
            current = getattr(self.modulation, name)
            incoming = getattr(source, name)
            setattr(self.modulation, name, (1 - weight) * current + weight * incoming)
        self.modulation.clamp()

    def process(self, stimulus: CognitiveStimulus) -> CognitiveCycleResult:
        cycle_id = uuid4()
        event_ids: list[UUID] = []
        attribution_recorded = False
        prediction_ids: list[UUID] = []
        observation = Observation(
            content=stimulus.content,
            source_id=stimulus.source_id,
            metadata=stimulus.metadata,
        )
        self._emit(
            BrainEvent(
                "observation.received",
                "observation",
                observation.id,
                {
                    "content": observation.content,
                    "source_id": observation.source_id,
                    "metadata": observation.metadata,
                    "cycle_id": str(cycle_id),
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )

        self._metabolize_capital(cycle_id, event_ids)

        previous_circadian_phase = self.circadian.phase
        if not self.circadian.is_awake and stimulus.urgency >= 0.85:
            self.circadian.force_wake()
            self._emit(
                circadian_forced_wake_event(
                    previous_phase=previous_circadian_phase,
                    urgency=stimulus.urgency,
                    aggregate_type="cognitive_cycle",
                    aggregate_id=cycle_id,
                    correlation_id=cycle_id,
                ),
                event_ids,
            )
        else:
            self.circadian.advance(ticks=1.0, cognitive_load=max(0.1, stimulus.urgency))
            if self.circadian.phase != previous_circadian_phase:
                self._emit(
                    circadian_phase_changed_event(
                        previous_phase=previous_circadian_phase,
                        new_phase=self.circadian.phase,
                        pressure_ratio=self.circadian.pressure.ratio,
                        aggregate_type="cognitive_cycle",
                        aggregate_id=cycle_id,
                        correlation_id=cycle_id,
                    ),
                    event_ids,
                )
        self._blend_modulation(self.circadian.modulator_profile(), weight=0.15)

        percept = self.perception.perceive(Modality.TEXT, str(observation.id), stimulus.content)
        self._emit(
            percept_to_event(
                percept,
                aggregate_type="observation",
                aggregate_id=observation.id,
                correlation_id=cycle_id,
            ),
            event_ids,
        )

        attention_score = self.attention.score(
            AttentionSignal(
                stimulus.commercial_upside,
                stimulus.novelty,
                stimulus.urgency,
                stimulus.contradiction_value,
                stimulus.source_reliability,
                stimulus.uncertainty_reduction,
                stimulus.noise_probability,
                stimulus.operator_burden,
            )
        )
        attended = attention_score >= self.attention_threshold
        self._emit(
            BrainEvent(
                "attention.scored",
                "observation",
                observation.id,
                {
                    "score": attention_score,
                    "threshold": self.attention_threshold,
                    "attended": attended,
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )

        salience = max(0.0, min(1.0, (attention_score + 1.0) / 6.0))
        salience *= self.circadian.encoding_rate_multiplier()
        slot, evicted = self.working_memory.encode(
            {
                "content": observation.content,
                "source_id": observation.source_id,
                "observation_id": str(observation.id),
                "cycle_id": str(cycle_id),
            },
            salience,
            source_event_id=observation.id,
        )
        self._emit(
            BrainEvent(
                "memory.working_stored",
                "observation",
                observation.id,
                {
                    "content": observation.content,
                    "salience": salience,
                    "slot_id": str(slot.id),
                    "capacity": self.working_memory.capacity,
                    "source_event_id": str(observation.id),
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )
        for victim in evicted:
            self._emit(
                BrainEvent(
                    "memory.working_evicted",
                    "working_memory",
                    victim.id,
                    {
                        "slot_id": str(victim.id),
                        "salience": victim.salience,
                        "content": victim.content,
                        "reason": "capacity",
                    },
                    correlation_id=cycle_id,
                ),
                event_ids,
            )

        belief = self._resolve_belief(stimulus, cycle_id, event_ids)
        evidence = Evidence(
            claim=stimulus.claim,
            source_id=stimulus.source_id,
            reliability=max(0.0, min(1.0, stimulus.source_reliability)),
            observation_id=observation.id,
            metadata={"cycle_id": str(cycle_id)},
        )
        self._emit(
            BrainEvent(
                "evidence.created",
                "evidence",
                evidence.id,
                {
                    "claim": evidence.claim,
                    "source_id": evidence.source_id,
                    "reliability": evidence.reliability,
                    "observation_id": str(observation.id),
                    "supports": stimulus.supports,
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )

        attributed_belief = self.theory_of_mind.attribute_belief(
            stimulus.source_id,
            statement=stimulus.claim,
            confidence=max(0.0, min(1.0, stimulus.source_reliability)),
            evidence_refs=[str(observation.id)],
        )
        self._emit(
            attributed_belief_to_event(
                attributed_belief,
                agent_id=stimulus.source_id,
                aggregate_type="observation",
                aggregate_id=observation.id,
                correlation_id=cycle_id,
            ),
            event_ids,
        )

        contradiction = self.contradictions.inspect(belief, evidence, stimulus.supports)
        prior_confidence = belief.confidence
        updated = self.beliefs.apply_evidence(belief, evidence, stimulus.supports)
        self._belief_cache[updated.id] = updated
        self._persist_belief(updated)
        self._emit(
            BrainEvent(
                "belief.updated",
                "belief",
                updated.id,
                {
                    "statement": updated.statement,
                    "confidence": updated.confidence,
                    "state": str(updated.state),
                    "version": updated.version,
                    "evidence_id": str(evidence.id),
                    "supports": stimulus.supports,
                    # Carried so a cache rebuilt from event replay knows which
                    # assertions have already moved this belief's confidence.
                    "evidence_fingerprints": sorted(updated.evidence_fingerprints),
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )

        rpe = self.hedonic.register_outcome(
            expected_value=prior_confidence, actual_value=updated.confidence
        )
        self._emit(
            reward_prediction_error_to_event(
                rpe, aggregate_type="belief", aggregate_id=updated.id, correlation_id=cycle_id,
            ),
            event_ids,
        )
        pain = None
        if contradiction is not None:
            pain = self.hedonic.register_pain(intensity=contradiction.severity, source="contradiction")
            self._emit(
                pain_signal_to_event(
                    pain, aggregate_type="belief", aggregate_id=updated.id, correlation_id=cycle_id,
                ),
                event_ids,
            )
        self._blend_modulation(self.hedonic.modulator_delta(rpe, pain), weight=0.25)

        appraisal = AppraisalInput(
            goal_congruence=(1.0 if stimulus.supports else -1.0)
            * max(0.0, min(1.0, stimulus.source_reliability)),
            novelty=stimulus.novelty,
            urgency=stimulus.urgency,
            controllability=max(0.0, 1.0 - stimulus.operator_burden),
            certainty=max(0.0, 1.0 - stimulus.noise_probability),
            agency="other",
            norm_compatibility=-contradiction.severity if contradiction is not None else 0.0,
        )
        emotion = self.affect.appraise(appraisal)
        self._blend_modulation(self.affect.modulator_delta(emotion), weight=0.25)
        self._emit(
            emotional_state_to_event(
                emotion,
                aggregate_type="observation",
                aggregate_id=observation.id,
                correlation_id=cycle_id,
                mood_valence=self.affect.mood.valence,
            ),
            event_ids,
        )

        attribution_recorded = self._feed_capital_outcome(stimulus, cycle_id, event_ids)

        tasks: list[CognitiveTask] = []
        if contradiction is not None:
            self._emit(
                BrainEvent(
                    "contradiction.detected",
                    "belief",
                    updated.id,
                    {
                        "evidence_id": str(evidence.id),
                        "severity": contradiction.severity,
                        "question": contradiction.question,
                    },
                    correlation_id=cycle_id,
                ),
                event_ids,
            )
            tasks.append(
                CognitiveTask(
                    name="investigate_contradiction",
                    utility=0.7 + 0.3 * contradiction.severity,
                    urgency=contradiction.severity,
                    novelty=stimulus.novelty,
                    uncertainty_reduction=0.9,
                    cost=0.2,
                    payload={
                        "belief_id": str(updated.id),
                        "evidence_id": str(evidence.id),
                        "question": contradiction.question,
                    },
                )
            )
        if attended:
            tasks.append(
                CognitiveTask(
                    name="consolidate_observation",
                    utility=max(0.0, min(1.0, stimulus.source_reliability)),
                    urgency=stimulus.urgency,
                    novelty=stimulus.novelty,
                    uncertainty_reduction=stimulus.uncertainty_reduction,
                    cost=0.1,
                    payload={
                        "observation_id": str(observation.id),
                        "belief_id": str(updated.id),
                    },
                )
            )
        if self.capital_ledger is not None and self.capital_ledger.is_starving:
            tasks.append(
                CognitiveTask(
                    name="pursue_capital_recovery",
                    utility=0.85,
                    urgency=1.0,
                    novelty=0.0,
                    uncertainty_reduction=0.2,
                    cost=0.05,
                    payload={
                        "capital_ledger_id": str(self.capital_ledger.id),
                        "balance": self.capital_ledger.balance,
                        "survival_threshold": self.capital_ledger.survival_threshold,
                    },
                )
            )

        executive_decision = None
        if len(tasks) >= 2:
            candidates = [
                ResponseCandidate(
                    action=task.name,
                    source=ResponseSource.DELIBERATE
                    if task.name == "investigate_contradiction"
                    else ResponseSource.HABITUAL,
                    prepotency=0.85 if task.name == "consolidate_observation" else 0.4,
                    goal_alignment=0.9 if task.name == "investigate_contradiction" else 0.0,
                    expected_value=task.utility,
                )
                for task in tasks
            ]
            self.control_resource.recover(ticks=0.5)
            executive_decision = self.executive.arbitrate(
                candidates, goals=None, control=self.control_resource, modulation=self.modulation
            )
            self._emit(
                executive_decision_to_event(
                    executive_decision,
                    aggregate_type="cognitive_cycle",
                    aggregate_id=cycle_id,
                    correlation_id=cycle_id,
                    control_remaining=self.control_resource.current,
                ),
                event_ids,
            )

        selected = self.scheduler.select(tasks, self.modulation, self.cognitive_budget)
        for task in selected:
            self._emit(
                BrainEvent(
                    "cognitive_task.selected",
                    "cognitive_task",
                    task.id,
                    {
                        "name": task.name,
                        "payload": task.payload,
                        "priority": self.scheduler.priority(task, self.modulation),
                    },
                    correlation_id=cycle_id,
                ),
                event_ids,
            )

        # Close the learning loop: selected tasks become open predictions.
        if self.learning is not None and selected:
            mapping = emit_predictions_for_selected_tasks(
                self.learning,
                selected,
                belief_id=updated.id,
                cycle_id=cycle_id,
                source_id=stimulus.source_id,
            )
            self._open_predictions_by_action.update(mapping)
            prediction_ids = list(mapping.values())

        self._emit(
            BrainEvent(
                "cycle.completed",
                "cognitive_cycle",
                cycle_id,
                {
                    "observation_id": str(observation.id),
                    "belief_id": str(updated.id),
                    "evidence_id": str(evidence.id),
                    "attention_score": attention_score,
                    "contradiction_detected": contradiction is not None,
                    "task_ids": [str(t.id) for t in selected],
                    "prediction_ids": [str(p) for p in prediction_ids],
                    "working_memory_size": self.working_memory.size,
                    "evicted_count": len(evicted),
                    "capital_balance": self.capital_ledger.balance if self.capital_ledger else None,
                    "budget_pressure": self.homeostatic_state.budget_pressure
                    if self.capital_ledger
                    else None,
                    "capital_starving": self.capital_ledger.is_starving
                    if self.capital_ledger
                    else None,
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )
        self._checkpoint()
        agent_model = self.theory_of_mind.agents.get(stimulus.source_id)
        return CognitiveCycleResult(
            cycle_id,
            observation.id,
            evidence.id,
            updated.id,
            attention_score,
            contradiction is not None,
            [t.id for t in selected],
            event_ids,
            working_memory_size=self.working_memory.size,
            evicted_count=len(evicted),
            emotion_label=str(emotion.label),
            emotion_valence=emotion.valence,
            circadian_phase=str(self.circadian.phase),
            executive_override_attempted=executive_decision.override_attempted
            if executive_decision
            else None,
            executive_override_succeeded=executive_decision.override_succeeded
            if executive_decision
            else None,
            perceived_novelty=percept.novelty,
            agent_trust=agent_model.trust if agent_model else None,
            capital_balance=self.capital_ledger.balance if self.capital_ledger else None,
            budget_pressure=self.homeostatic_state.budget_pressure if self.capital_ledger else None,
            capital_starving=self.capital_ledger.is_starving if self.capital_ledger else None,
            prediction_ids=prediction_ids,
            attribution_recorded=attribution_recorded,
        )

    def _metabolize_capital(self, cycle_id: UUID, event_ids: list[UUID]) -> None:
        if self.capital_ledger is None:
            return
        self.capital_ledger, metabolic_events = self.metabolism.metabolize(self.capital_ledger)
        for event in metabolic_events:
            self._emit(
                BrainEvent(
                    event.event_type,
                    event.aggregate_type,
                    event.aggregate_id,
                    event.payload,
                    causation_id=event.causation_id,
                    correlation_id=cycle_id,
                ),
                event_ids,
            )
        self._refresh_homeostasis_from_capital(cycle_id, event_ids)

    def _feed_capital_outcome(
        self,
        stimulus: CognitiveStimulus,
        cycle_id: UUID,
        event_ids: list[UUID],
    ) -> bool:
        """Credit capital ledger and attribute open predictions when value arrives."""
        if stimulus.capital_outcome_amount <= 0:
            return False

        if self.capital_ledger is not None:
            self.capital_ledger, event = self.metabolism.feed(
                self.capital_ledger,
                stimulus.capital_outcome_amount,
                source=stimulus.capital_outcome_source or "cognitive-cycle-outcome",
            )
            self._emit(
                BrainEvent(
                    event.event_type,
                    event.aggregate_type,
                    event.aggregate_id,
                    event.payload,
                    causation_id=event.causation_id,
                    correlation_id=cycle_id,
                ),
                event_ids,
            )
            self._refresh_homeostasis_from_capital(cycle_id, event_ids)

        if self.learning is None:
            return False

        # Prefer explicit outcome_action_id; else attribute against the oldest open prediction.
        action_id = stimulus.outcome_action_id
        if action_id is None and self._open_predictions_by_action:
            action_id = next(iter(self._open_predictions_by_action.keys()))
        if action_id is None:
            action_id = uuid4()

        try:
            attribute_capital_or_result_outcome(
                self.learning,
                action_id=action_id,
                value_created=float(stimulus.capital_outcome_amount),
                open_by_action=self._open_predictions_by_action,
                source_keys=[stimulus.capital_outcome_source or stimulus.source_id],
            )
            # Drop resolved mapping entry if present
            self._open_predictions_by_action.pop(action_id, None)
            return True
        except Exception:
            # Attribution failures must not abort cognition; ledger already credited.
            return False

    def _refresh_homeostasis_from_capital(self, cycle_id: UUID, event_ids: list[UUID]) -> None:
        if self.capital_ledger is None:
            return
        budget_pressure = self.metabolism.budget_pressure(self.capital_ledger)
        memory_pressure = max(
            0.0,
            min(1.0, self.working_memory.size / max(1, self.working_memory.capacity)),
        )
        self.homeostatic_state = replace(
            self.homeostatic_state,
            memory_pressure=memory_pressure,
            budget_pressure=budget_pressure,
            updated_at=utcnow(),
        )
        self.modulation = self.homeostasis.regulate(self.homeostatic_state, self.modulation)
        self._emit(
            BrainEvent(
                "homeostasis.budget_pressure_updated",
                "capital_ledger",
                self.capital_ledger.id,
                {
                    "budget_pressure": budget_pressure,
                    "stress_index": self.homeostatic_state.stress_index,
                    "balance": self.capital_ledger.balance,
                    "is_starving": self.capital_ledger.is_starving,
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )

    def _resolve_belief(
        self, stimulus: CognitiveStimulus, cycle_id: UUID, event_ids: list[UUID]
    ) -> Belief:
        if stimulus.belief_id is not None:
            if stimulus.belief_id in self._belief_cache:
                return self._belief_cache[stimulus.belief_id]
            if not self._belief_cache:
                self.hydrate_beliefs()
            if stimulus.belief_id in self._belief_cache:
                return self._belief_cache[stimulus.belief_id]
            belief = Belief(
                statement=stimulus.belief_statement or stimulus.claim,
                confidence=stimulus.belief_confidence,
                id=stimulus.belief_id,
            )
            self._belief_cache[belief.id] = belief
            self._persist_belief(belief)
            self._emit(
                BrainEvent(
                    "belief.created",
                    "belief",
                    belief.id,
                    {
                        "statement": belief.statement,
                        "confidence": belief.confidence,
                        "state": str(belief.state),
                        "version": belief.version,
                    },
                    correlation_id=cycle_id,
                ),
                event_ids,
            )
            return belief
        belief = Belief(
            statement=stimulus.belief_statement or stimulus.claim,
            confidence=stimulus.belief_confidence,
        )
        self._belief_cache[belief.id] = belief
        self._emit(
            BrainEvent(
                "belief.created",
                "belief",
                belief.id,
                {
                    "statement": belief.statement,
                    "confidence": belief.confidence,
                    "state": str(belief.state),
                    "version": belief.version,
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )
        return belief

    def _emit(self, event: BrainEvent, event_ids: list[UUID]) -> None:
        self.event_store.append(event)
        event_ids.append(event.id)

    def _checkpoint(self) -> None:
        if self.checkpoint_store is None:
            return
        incremental_checkpoint(
            self._projection,
            self.event_store,
            self.checkpoint_store,
            projection_name="brain.current",
        )
