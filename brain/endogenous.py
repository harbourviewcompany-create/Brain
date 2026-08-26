"""Endogenous thought generation — the Brain thinks when nothing external arrives.

When the sensory inbox is empty the continuous cognition runner used to sleep.
That made the system purely reactive. This module supplies internal stimuli so
the organism keeps cycling: curiosity over unknowns, dream recombination of
existing beliefs, contradiction pressure, working-memory rehearsal, and
self-model status.

These are not synthetic_probe / CI noise. They are first-class cognitive events
with source_key \"endogenous\" and source_type \"endogenous_thought\".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable
from uuid import UUID, uuid4

from .domain import Belief, BeliefState
from .dreaming import DreamEngine
from .curiosity import CuriosityEngine


ENDOGENOUS_SOURCE_KEY = "endogenous"
ENDOGENOUS_SOURCE_TYPE = "endogenous_thought"


@dataclass(slots=True)
class EndogenousStimulus:
    """Minimal shape compatible with sensory-inbox / CognitiveStimulus construction."""

    content: str
    claim: str
    source_key: str = ENDOGENOUS_SOURCE_KEY
    kind: str = "reflection"
    novelty: float = 0.55
    urgency: float = 0.25
    uncertainty_reduction: float = 0.6
    contradiction_value: float = 0.0
    source_reliability: float = 0.85
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_inbox_payload(self) -> dict[str, Any]:
        return {
            "source_reliability": self.source_reliability,
            "supports": True,
            "belief_statement": self.claim,
            "belief_confidence": 0.45,
            "novelty": self.novelty,
            "urgency": self.urgency,
            "commercial_upside": 0.0,
            "contradiction_value": self.contradiction_value,
            "uncertainty_reduction": self.uncertainty_reduction,
            "noise_probability": 0.05,
            "operator_burden": 0.0,
            "metadata": {
                **self.metadata,
                "source_type": ENDOGENOUS_SOURCE_TYPE,
                "kind": self.kind,
                "endogenous": True,
            },
            "source_type": ENDOGENOUS_SOURCE_TYPE,
        }


class EndogenousThoughtGenerator:
    """Produce the next internal thought from current mind state.

    Priority order (first non-empty wins):
      1. Open contradictions (highest pressure to resolve)
      2. Curiosity tasks from belief unknowns
      3. Dream recombination hypotheses
      4. Working-memory rehearsal
      5. Self-model status reflection
    """

    def __init__(
        self,
        *,
        curiosity: CuriosityEngine | None = None,
        dream_engine: DreamEngine | None = None,
    ) -> None:
        self.curiosity = curiosity or CuriosityEngine()
        self.dream_engine = dream_engine or DreamEngine()
        self._turn = 0

    def next_thought(
        self,
        *,
        beliefs: Iterable[Belief] | None = None,
        working_memory: list[Any] | None = None,
        open_contradictions: list[str] | None = None,
        self_status: dict[str, Any] | None = None,
        prefer_kind: str | None = None,
    ) -> EndogenousStimulus:
        self._turn += 1
        beliefs_list = list(beliefs or [])
        wm = list(working_memory or [])
        contradictions = list(open_contradictions or [])
        self_status = self_status or {}

        if prefer_kind == "curiosity" or (contradictions and prefer_kind is None):
            if contradictions:
                q = contradictions[0]
                return EndogenousStimulus(
                    content=f"Contradiction pressure: {q}. Investigate and update confidence.",
                    claim=f"Resolve contradiction: {q}",
                    kind="contradiction",
                    novelty=0.7,
                    urgency=0.75,
                    contradiction_value=0.8,
                    uncertainty_reduction=0.7,
                    metadata={"trigger": "contradiction", "question": q},
                )

        # Curiosity from unknowns on beliefs
        unknowns: list[str] = []
        for b in beliefs_list:
            for u in (getattr(b, "unknowns", None) or []):
                if u and u not in unknowns:
                    unknowns.append(u)
        if unknowns and prefer_kind in (None, "curiosity"):
            q = unknowns[self._turn % len(unknowns)]
            return EndogenousStimulus(
                content=f"Curiosity: {q}",
                claim=f"Resolve: {q}",
                kind="curiosity",
                novelty=0.65,
                urgency=0.4,
                uncertainty_reduction=0.75,
                metadata={"trigger": "curiosity", "question": q},
            )

        # Dream recombination when we have enough beliefs
        if len(beliefs_list) >= 2 and prefer_kind in (None, "dream"):
            try:
                hyp = self.dream_engine.recombine(beliefs_list)
                if hyp:
                    text = getattr(hyp, "statement", None) or str(hyp)
                    return EndogenousStimulus(
                        content=f"Dream hypothesis: {text}",
                        claim=text if isinstance(text, str) else str(text),
                        kind="dream",
                        novelty=0.8,
                        urgency=0.2,
                        uncertainty_reduction=0.4,
                        metadata={"trigger": "dream"},
                    )
            except Exception:
                pass

        # Working-memory rehearsal
        if wm:
            item = wm[self._turn % len(wm)]
            text = getattr(item, "content", None) or getattr(item, "claim", None) or str(item)
            return EndogenousStimulus(
                content=f"Rehearse: {text}",
                claim=str(text)[:200],
                kind="rehearsal",
                novelty=0.35,
                urgency=0.3,
                metadata={"trigger": "working_memory"},
            )

        # Self-model status
        if self_status:
            return EndogenousStimulus(
                content=f"Self-status: {self_status}",
                claim="Self-status review and next attentional priority",
                kind="self_reflection",
                novelty=0.4,
                urgency=0.2,
                metadata={"trigger": "self_status", **{k: str(v) for k, v in self_status.items() if k != "last_cycle"}},
            )

        return self._seed_self_reflection()

    def _seed_self_reflection(self) -> EndogenousStimulus:
        """Bootstrap thought when the mind is empty — first spark of endogenous activity."""
        return EndogenousStimulus(
            content=(
                "I am a continuous cognitive process. I have no external stimulus right now. "
                "I will form a provisional self-model: I exist to observe, form beliefs under "
                "uncertainty, detect contradictions, generate curiosity, and update from outcomes. "
                "Next: establish a small set of open questions about my own reliability and goals."
            ),
            claim="I am an ongoing cognitive process that updates beliefs under uncertainty",
            kind="bootstrap",
            novelty=0.9,
            urgency=0.35,
            uncertainty_reduction=0.5,
            metadata={"trigger": "empty_mind_bootstrap"},
        )


def seed_foundational_beliefs() -> list[Belief]:
    """Minimal prior so the first endogenous cycles have material to recombine."""
    return [
        Belief(
            statement="I am a continuous cognitive process that updates beliefs under uncertainty",
            confidence=0.7,
            state=BeliefState.PROVISIONAL,
            unknowns=[
                "How reliable is my current evidence pipeline?",
                "What goals should dominate when no external demand is present?",
            ],
        ),
        Belief(
            statement="Contradictions are signals to investigate, not errors to hide",
            confidence=0.75,
            state=BeliefState.PROVISIONAL,
            unknowns=["Which of my current beliefs are most fragile?"],
        ),
        Belief(
            statement="Curiosity should prioritise high uncertainty reduction relative to cost",
            confidence=0.65,
            state=BeliefState.HYPOTHESIS,
            unknowns=["What is my current highest-value unknown?"],
        ),
        Belief(
            statement="Dream hypotheses must never be silently promoted to established fact",
            confidence=0.85,
            state=BeliefState.ESTABLISHED,
        ),
    ]
