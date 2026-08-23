from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID, uuid4

from .attention import AttentionMarket, AttentionSignal
from .beliefs import BeliefEngine
from .cognitive_state import NeuromodulatorState
from .contradiction import ContradictionEngine
from .domain import Belief, Evidence, Observation
from .events import BrainEvent
from .hydrate import hydrate_belief_cache
from .projections import default_projection_engine, incremental_checkpoint
from .scheduler import CognitiveScheduler, CognitiveTask
from .working_memory import WorkingMemory


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

    def register_belief(self, belief: Belief) -> None:
        self._belief_cache[belief.id] = belief

    def hydrate_beliefs(self, *, from_checkpoint: bool = True) -> int:
        """Load beliefs into process cache from checkpoint or event replay."""
        return hydrate_belief_cache(
            self._belief_cache,
            self.event_store,
            self.checkpoint_store,
            from_checkpoint=from_checkpoint,
        )

    def process(self, stimulus: CognitiveStimulus) -> CognitiveCycleResult:
        cycle_id = uuid4()
        event_ids: list[UUID] = []
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

        contradiction = self.contradictions.inspect(belief, evidence, stimulus.supports)
        updated = self.beliefs.apply_evidence(belief, evidence, stimulus.supports)
        self._belief_cache[updated.id] = updated
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
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )

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
                    "working_memory_size": self.working_memory.size,
                    "evicted_count": len(evicted),
                },
                correlation_id=cycle_id,
            ),
            event_ids,
        )
        self._checkpoint()
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
