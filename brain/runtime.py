from __future__ import annotations

from dataclasses import asdict

from .beliefs import BeliefEngine
from .contradiction import ContradictionEngine
from .domain import Belief, Evidence
from .events import BrainEvent
from .memory import InMemoryBrainStore


class BrainRuntime:
    """Minimal executable cognitive loop. Production adapters replace the in-memory store."""

    def __init__(self, store: InMemoryBrainStore | None = None):
        self.store = store or InMemoryBrainStore()
        self.beliefs = BeliefEngine()
        self.contradictions = ContradictionEngine()

    def create_belief(self, statement: str, confidence: float = 0.5) -> Belief:
        belief = Belief(statement=statement, confidence=confidence)
        self.store.save(belief)
        self.store.append(BrainEvent("belief.created", "belief", belief.id, asdict(belief)))
        return belief

    def learn(self, belief: Belief, evidence: Evidence, supports: bool) -> Belief:
        self.store.save(evidence)
        contradiction = self.contradictions.inspect(belief, evidence, supports)
        updated = self.beliefs.apply_evidence(belief, evidence, supports)
        self.store.save(updated)
        self.store.append(
            BrainEvent(
                "belief.updated",
                "belief",
                belief.id,
                {"supports": supports, "evidence_id": str(evidence.id), "confidence": updated.confidence},
            )
        )
        if contradiction:
            self.store.append(
                BrainEvent(
                    "contradiction.detected",
                    "belief",
                    belief.id,
                    {"evidence_id": str(evidence.id), "severity": contradiction.severity, "question": contradiction.question},
                )
            )
        return updated
