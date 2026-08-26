from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import UUID

from .domain import Edge, RewireEvent
from .rewiring import RewiringEngine


def edge_similarity(a: Edge, b: Edge) -> float:
    """Structural similarity between two edges, in [0, 1].

    Deliberately not an embedding model -- there isn't one in this system,
    and faking one with hashed features would be less honest than a small,
    explainable, testable rule. Two edges are similar to the extent they
    share a relation type AND at least one endpoint (a genuinely related
    pathway, not an arbitrary one), scaled down when their confidence
    diverges a lot (an edge the Brain barely trusts is a poor analogy for
    one it's confident about, even if structurally adjacent).

    Returns 0.0 for a different relation type or no shared endpoint --
    there is no principled transfer across an unrelated pathway.
    """
    if a.id == b.id:
        return 1.0
    if a.relation != b.relation:
        return 0.0
    shared_endpoints = len({a.source, a.target} & {b.source, b.target})
    if shared_endpoints == 0:
        return 0.0
    structural = shared_endpoints / 2.0
    confidence_alignment = 1.0 - abs(a.confidence - b.confidence)
    return max(0.0, min(1.0, structural * confidence_alignment))


@dataclass(slots=True)
class GeneralizationResult:
    updated_edges: list[Edge] = field(default_factory=list)
    rewire_events: list[RewireEvent] = field(default_factory=list)
    edge_deltas: dict[str, float] = field(default_factory=dict)
    pruned_edge_ids: list[UUID] = field(default_factory=list)


class GeneralizationEngine:
    """Partial credit assignment to structurally similar-but-not-identical
    edges. Without this, learning a specific pathway (SourceX supports
    ClaimY) never touches a related-but-distinct one (SourceX supports
    ClaimZ) until that exact pathway has itself been directly tested --
    the point-update problem. A real brain doesn't need the identical
    situation to recur to be wary of similar ones.

    Bounded on every axis on purpose: similarity_threshold excludes weak
    analogies, max_neighbors caps blast radius, transfer_rate keeps any one
    propagation a fraction of the direct update, and RewiringEngine's own
    max_edge_delta still applies underneath all of it.
    """

    def __init__(
        self,
        *,
        transfer_rate: float = 0.35,
        similarity_threshold: float = 0.4,
        max_neighbors: int = 5,
    ) -> None:
        self.transfer_rate = transfer_rate
        self.similarity_threshold = similarity_threshold
        self.max_neighbors = max_neighbors

    def propagate(
        self,
        primary_edge: Edge,
        primary_delta: float,
        candidates: list[Edge],
        rewiring: RewiringEngine,
        evidence_id: UUID,
        *,
        exclude_ids: set[UUID] | None = None,
    ) -> GeneralizationResult:
        exclude = exclude_ids or set()
        if abs(primary_delta) < 1e-9:
            return GeneralizationResult()

        scored = []
        for candidate in candidates:
            if candidate.id == primary_edge.id or candidate.id in exclude:
                continue
            similarity = edge_similarity(primary_edge, candidate)
            if similarity >= self.similarity_threshold:
                scored.append((candidate, similarity))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        scored = scored[: self.max_neighbors]

        result = GeneralizationResult()
        for candidate, similarity in scored:
            transferred = primary_delta * similarity * self.transfer_rate
            if abs(transferred) < 1e-6:
                continue
            previous = candidate.weight
            if transferred >= 0:
                new_edge, event = rewiring.reinforce(candidate, evidence_id, abs(transferred))
            else:
                new_edge, event = rewiring.weaken(candidate, abs(transferred))
            event = replace(
                event,
                reason=(
                    f"Generalized from a structurally similar pathway "
                    f"(similarity={similarity:.3f}, transferred={transferred:.4f})."
                ),
            )
            result.rewire_events.append(event)
            if new_edge is not None:
                result.updated_edges.append(new_edge)
                result.edge_deltas[str(candidate.id)] = new_edge.weight - previous
            else:
                result.pruned_edge_ids.append(candidate.id)
                result.edge_deltas[str(candidate.id)] = -previous
        return result
