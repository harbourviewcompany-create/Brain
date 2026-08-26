from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise
from uuid import UUID

from .attribution import OutcomeAttribution
from .domain import Belief, Edge, Outcome, RewireEvent
from .cognitive_organism import DreamConsolidationEngine, DreamCycle, DreamInsight


@dataclass(slots=True)
class DreamHypothesis:
    statement: str
    reason: str
    confidence: float


class DreamEngine:
    """Offline recombination. It proposes; it never silently converts a dream into fact."""

    def recombine(self, beliefs: list[Belief]) -> list[DreamHypothesis]:
        active = [b for b in beliefs if b.confidence >= 0.55]
        active.sort(key=lambda b: b.confidence, reverse=True)
        hypotheses: list[DreamHypothesis] = []
        for left, right in pairwise(active):
            hypotheses.append(
                DreamHypothesis(
                    statement=f"Possible relationship between [{left.statement}] and [{right.statement}]",
                    reason="High-confidence beliefs were adjacent during offline recombination.",
                    confidence=min(left.confidence, right.confidence) * 0.5,
                )
            )
        return hypotheses


@dataclass(slots=True)
class ConsolidationResult:
    replayed_outcome_ids: list[UUID] = field(default_factory=list)
    updated_edges: list[Edge] = field(default_factory=list)
    rewire_events: list[RewireEvent] = field(default_factory=list)
    generalized_edge_ids: list[str] = field(default_factory=list)
    consolidation_learn_rate: float = 0.0


class ReplayConsolidationEngine:
    """The part of sleep that isn't just narrative pattern-spotting.

    DreamEngine/DreamConsolidationEngine above propose hypotheses and
    priority nudges but deliberately never touch a learned weight --
    that conservatism is correct for hypotheses, since a dream shouldn't
    silently become fact. But real sleep also does something this Brain
    didn't do at all until now: it replays the day's most salient genuine
    experience and consolidates what was actually learned from it, often
    generalizing further from it than waking, one-shot updates do.

    This engine never fabricates an outcome -- it only replays Outcomes
    the Brain already recorded for real, through the exact same
    OutcomeAttribution used while awake, at a reduced rate (consolidation
    stabilizes, it doesn't aggressively relearn), prioritized by how
    salient each outcome was (highest unsigned value, or highest
    prediction error -- the same "replay what mattered most" principle
    behind biological hippocampal replay).
    """

    def __init__(
        self,
        attribution: OutcomeAttribution,
        *,
        replay_rate_scale: float = 0.4,
        max_replays: int = 20,
    ) -> None:
        self.attribution = attribution
        self.replay_rate_scale = replay_rate_scale
        self.max_replays = max_replays

    def consolidate(
        self,
        outcomes: list[Outcome],
        *,
        edges_by_outcome: dict[UUID, list[Edge]],
        candidate_edges: list[Edge] | None = None,
    ) -> ConsolidationResult:
        if not outcomes:
            return ConsolidationResult(consolidation_learn_rate=self.attribution.base_edge_learn_rate)

        salient = sorted(
            outcomes,
            key=lambda o: abs(o.value_created) + abs(o.prediction_accuracy - 0.5),
            reverse=True,
        )[: self.max_replays]

        updated: dict[UUID, Edge] = {}
        events: list[RewireEvent] = []
        generalized: set[str] = set()
        replayed_ids: list[UUID] = []

        original_rate = self.attribution.base_edge_learn_rate
        consolidation_rate = original_rate * self.replay_rate_scale
        self.attribution.base_edge_learn_rate = consolidation_rate
        try:
            for outcome in salient:
                edges = edges_by_outcome.get(outcome.action_id, [])
                if not edges:
                    continue
                cited_ids = {e.id for e in edges}
                result = self.attribution.attribute(
                    outcome,
                    edges=edges,
                    candidate_edges=candidate_edges,
                )
                replayed_ids.append(outcome.id)
                for edge in result.updated_edges:
                    updated[edge.id] = edge
                events.extend(result.rewire_events)
                generalized.update(
                    key for key in result.attribution.edge_deltas if key not in {str(i) for i in cited_ids}
                )
        finally:
            self.attribution.base_edge_learn_rate = original_rate

        return ConsolidationResult(
            replayed_outcome_ids=replayed_ids,
            updated_edges=list(updated.values()),
            rewire_events=events,
            generalized_edge_ids=sorted(generalized),
            consolidation_learn_rate=consolidation_rate,
        )


__all__ = [
    "DreamEngine",
    "DreamHypothesis",
    "DreamConsolidationEngine",
    "DreamCycle",
    "DreamInsight",
    "ReplayConsolidationEngine",
    "ConsolidationResult",
]
