from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class CausalEdge:
    cause: str
    effect: str
    strength: float
    confidence: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class Intervention:
    variable: str
    value: float
    evidence_refs: list[str]


@dataclass(slots=True)
class PlanAction:
    description: str
    intervention: Intervention
    cost: float = 0.0
    risk: float = 0.0
    reversible: bool = True
    external: bool = False
    approval_required: bool = False
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class PlanCandidate:
    actions: list[PlanAction]
    target_variable: str
    target_value: float
    evidence_refs: list[str]
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class CounterfactualResult:
    plan_id: UUID
    predicted_state: dict[str, float]
    target_value: float
    utility: float
    uncertainty: float
    requires_approval: bool
    evidence_refs: list[str]


class CausalGraph:
    def __init__(self) -> None:
        self.edges: list[CausalEdge] = []

    def add_edge(self, edge: CausalEdge) -> None:
        if not edge.evidence_refs:
            raise ValueError("causal edge requires evidence")
        edge.strength = max(-1.0, min(1.0, float(edge.strength)))
        edge.confidence = _clamp01(edge.confidence)
        self.edges.append(edge)

    def downstream(self, variable: str) -> list[CausalEdge]:
        return [edge for edge in self.edges if edge.cause == variable]


class CounterfactualPlanner:
    """Deterministic intervention simulator with explicit uncertainty and approval gates."""

    def __init__(self, graph: CausalGraph) -> None:
        self.graph = graph

    def simulate(
        self,
        plan: PlanCandidate,
        baseline: dict[str, float],
        *,
        max_depth: int = 4,
    ) -> CounterfactualResult:
        if not plan.evidence_refs:
            raise ValueError("planning requires source evidence")
        state = {key: float(value) for key, value in baseline.items()}
        used_evidence = set(plan.evidence_refs)
        uncertainties: list[float] = []
        requires_approval = False

        frontier: list[tuple[str, float, int]] = []
        for action in plan.actions:
            if action.external and (action.approval_required or not action.reversible):
                requires_approval = True
            if not action.intervention.evidence_refs:
                raise ValueError("intervention requires evidence")
            used_evidence.update(action.intervention.evidence_refs)
            state[action.intervention.variable] = action.intervention.value
            frontier.append((action.intervention.variable, action.intervention.value, 0))

        seen: set[tuple[str, int]] = set()
        while frontier:
            variable, delta, depth = frontier.pop(0)
            if depth >= max_depth or (variable, depth) in seen:
                continue
            seen.add((variable, depth))
            for edge in self.graph.downstream(variable):
                used_evidence.update(edge.evidence_refs)
                effect_delta = delta * edge.strength * edge.confidence
                state[edge.effect] = state.get(edge.effect, 0.0) + effect_delta
                uncertainties.append(1.0 - edge.confidence)
                frontier.append((edge.effect, effect_delta, depth + 1))

        target = state.get(plan.target_variable, 0.0)
        gross_utility = 1.0 - min(1.0, abs(plan.target_value - target))
        cost_penalty = sum(max(0.0, action.cost) for action in plan.actions)
        risk_penalty = sum(_clamp01(action.risk) for action in plan.actions) / max(1, len(plan.actions))
        utility = gross_utility - min(1.0, cost_penalty) * 0.2 - risk_penalty * 0.3
        uncertainty = sum(uncertainties) / len(uncertainties) if uncertainties else 0.0
        return CounterfactualResult(
            plan_id=plan.id,
            predicted_state=state,
            target_value=target,
            utility=utility,
            uncertainty=_clamp01(uncertainty),
            requires_approval=requires_approval,
            evidence_refs=sorted(used_evidence),
        )

    def rank(self, results: list[CounterfactualResult]) -> list[CounterfactualResult]:
        return sorted(
            results,
            key=lambda item: (item.utility - item.uncertainty * 0.25, not item.requires_approval),
            reverse=True,
        )
