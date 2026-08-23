from __future__ import annotations

from typing import Any, Protocol

from .beliefs import BeliefEngine
from .contradiction import ContradictionEngine
from .domain import Belief, Evidence
from .events import BrainEvent
from .memory import InMemoryBrainStore


class BeliefProjection(Protocol):
    def upsert(self, belief: Belief) -> None: ...


class EventAppender(Protocol):
    def append(self, event: BrainEvent) -> None: ...


def _belief_payload(belief: Belief) -> dict[str, Any]:
    """JSON-safe snapshot for brain_events.payload (no sets)."""
    return {
        "id": str(belief.id),
        "statement": belief.statement,
        "confidence": belief.confidence,
        "state": str(belief.state),
        "version": belief.version,
        "unknowns": list(belief.unknowns),
        "supporting_evidence": [str(x) for x in belief.supporting_evidence],
        "contradicting_evidence": [str(x) for x in belief.contradicting_evidence],
    }


class BrainRuntime:
    """Minimal executable cognitive loop. Production adapters replace the in-memory store."""

    def __init__(
        self,
        store: InMemoryBrainStore | None = None,
        *,
        event_store: EventAppender | None = None,
        belief_projection: BeliefProjection | None = None,
    ):
        self.store = store or InMemoryBrainStore()
        self.event_store = event_store
        self.belief_projection = belief_projection
        self.beliefs = BeliefEngine()
        self.contradictions = ContradictionEngine()

    def _emit(self, event: BrainEvent) -> None:
        self.store.append(event)
        if self.event_store is not None:
            self.event_store.append(event)

    def _project(self, belief: Belief) -> None:
        if self.belief_projection is not None:
            self.belief_projection.upsert(belief)

    def create_belief(self, statement: str, confidence: float = 0.5) -> Belief:
        belief = Belief(statement=statement, confidence=confidence)
        self.store.save(belief)
        self._emit(BrainEvent("belief.created", "belief", belief.id, _belief_payload(belief)))
        self._project(belief)
        return belief

    def learn(self, belief: Belief, evidence: Evidence, supports: bool) -> Belief:
        self.store.save(evidence)
        contradiction = self.contradictions.inspect(belief, evidence, supports)
        updated = self.beliefs.apply_evidence(belief, evidence, supports)
        self.store.save(updated)
        self._emit(
            BrainEvent(
                "belief.updated",
                "belief",
                belief.id,
                {
                    "supports": supports,
                    "evidence_id": str(evidence.id),
                    "confidence": updated.confidence,
                    "state": str(updated.state),
                    "version": updated.version,
                    "statement": updated.statement,
                },
            )
        )
        self._project(updated)
        if contradiction:
            self._emit(
                BrainEvent(
                    "contradiction.detected",
                    "belief",
                    belief.id,
                    {
                        "evidence_id": str(evidence.id),
                        "severity": contradiction.severity,
                        "question": contradiction.question,
                    },
                )
            )
        return updated
