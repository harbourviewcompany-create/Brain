from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True, slots=True)
class FormulaSpec:
    formula_id: str
    name: str
    expression: str
    variables: list[str]
    owner_object: str
    service: str
    table_store: str
    dashboard: str
    decision_consequence: str
    evaluator: Callable[[dict[str, float]], float]


@dataclass(frozen=True, slots=True)
class FormulaRunResult:
    formula_id: str
    run_id: UUID
    owner_object_id: str
    owner_object_type: str
    service: str
    table_store: str
    dashboard: str
    decision_consequence: str
    inputs: dict[str, float]
    output: float
    audit_evidence: dict[str, str | float]


@dataclass
class FormulaRegistry:
    formulas: dict[str, FormulaSpec] = field(default_factory=dict)

    def register(self, spec: FormulaSpec) -> None:
        self.formulas[spec.formula_id] = spec

    def evaluate(
        self,
        formula_id: str,
        inputs: dict[str, float],
        *,
        owner_object_id: str,
        owner_object_type: str,
    ) -> FormulaRunResult:
        spec = self.formulas[formula_id]
        missing = sorted(set(spec.variables) - set(inputs))
        if missing:
            raise ValueError(f"Formula {formula_id} missing inputs: {missing}")
        output = spec.evaluator(inputs)
        run_id = uuid4()
        return FormulaRunResult(
            formula_id=formula_id,
            run_id=run_id,
            owner_object_id=owner_object_id,
            owner_object_type=owner_object_type,
            service=spec.service,
            table_store=spec.table_store,
            dashboard=spec.dashboard,
            decision_consequence=spec.decision_consequence,
            inputs={key: inputs[key] for key in spec.variables},
            output=output,
            audit_evidence={
                "formula_id": formula_id,
                "run_id": str(run_id),
                "owner_object_id": owner_object_id,
                "owner_object_type": owner_object_type,
                "service": spec.service,
                "dashboard": spec.dashboard,
                "decision_consequence": spec.decision_consequence,
                "output": output,
            },
        )


def _source_priority_score(v: dict[str, float]) -> float:
    return clamp(
        0.4 * v["source_reliability"]
        + 0.3 * v["historical_yield"]
        + 0.2 * v["freshness"]
        - 0.1 * v["access_cost"]
    )


def _attention_score(v: dict[str, float]) -> float:
    return (
        1.4 * v["commercial_upside"]
        + 1.1 * v["novelty"]
        + v["urgency"]
        + 1.2 * v["contradiction_value"]
        + 0.9 * v["source_quality"]
        + 1.1 * v["learning_value"]
        - 1.2 * v["noise_probability"]
        - 0.8 * v["operator_load_penalty"]
    )


def _bayesian_belief_update(v: dict[str, float]) -> float:
    prior = clamp(v["prior"])
    likelihood = clamp(v["likelihood"])
    false_likelihood = clamp(v["false_likelihood"])
    denominator = prior * likelihood + (1.0 - prior) * false_likelihood
    if denominator == 0.0:
        return prior
    return clamp((likelihood * prior) / denominator)


def _brier_score(v: dict[str, float]) -> float:
    return (clamp(v["forecast_probability"]) - clamp(v["actual_outcome"])) ** 2


def _reward_score(v: dict[str, float]) -> float:
    return (
        v["commercial_value"]
        + v["prediction_accuracy"]
        + v["source_quality"]
        + v["actionability"]
        + v["novelty"]
        + v["timing_advantage"]
        - v["false_positive_cost"]
        - v["uncertainty_penalty"]
        - v["operator_time_cost"]
    )


def _pain_score(v: dict[str, float]) -> float:
    return max(
        0.0,
        v["false_positive_cost"]
        + v["capital_wasted"]
        + v["trust_damage"]
        + v["legal_or_reputation_risk"]
        + v["operator_time_cost"],
    )


def _graph_weight_update(v: dict[str, float]) -> float:
    return clamp(v["current_weight"] + v["learning_rate"] * v["reward_signal"] - v["decay_rate"])


def _fractional_kelly_exposure(v: dict[str, float]) -> float:
    probability = clamp(v["win_probability"])
    payoff_ratio = max(v["payoff_ratio"], 0.000001)
    fraction = clamp(v["fraction"])
    max_exposure = clamp(v["max_exposure"])
    edge = (probability * payoff_ratio - (1.0 - probability)) / payoff_ratio
    return clamp(fraction * edge, 0.0, max_exposure)


def _trust_adjusted_value(v: dict[str, float]) -> float:
    return (
        v["action_expected_utility"]
        - v["trust_damage_risk"]
        - v["reputation_damage_risk"]
        - v["legal_or_access_risk"]
    )


def default_formula_registry() -> FormulaRegistry:
    registry = FormulaRegistry()
    specs = [
        FormulaSpec(
            "source_priority_score",
            "Source priority score",
            "0.4*reliability + 0.3*yield + 0.2*freshness - 0.1*cost",
            ["source_reliability", "historical_yield", "freshness", "access_cost"],
            "Source",
            "SourceRegistryService",
            "source_scores",
            "Source Quality Console",
            "Rank or demote source review priority.",
            _source_priority_score,
        ),
        FormulaSpec(
            "attention_score",
            "Attention score",
            "positive salience minus noise and operator load",
            [
                "commercial_upside",
                "novelty",
                "urgency",
                "contradiction_value",
                "source_quality",
                "learning_value",
                "noise_probability",
                "operator_load_penalty",
            ],
            "Signal",
            "AttentionAllocatorService",
            "formula_runs",
            "Perception Inbox",
            "Route, monitor, escalate, or suppress a signal.",
            _attention_score,
        ),
        FormulaSpec(
            "bayesian_belief_update",
            "Bayesian belief update",
            "P(H|E) = P(E|H)P(H)/P(E)",
            ["prior", "likelihood", "false_likelihood"],
            "Belief",
            "BeliefUpdateService",
            "belief_formula_runs",
            "Belief Ledger",
            "Raise or lower belief confidence.",
            _bayesian_belief_update,
        ),
        FormulaSpec(
            "brier_score",
            "Brier score",
            "(forecast_probability - actual_outcome)^2",
            ["forecast_probability", "actual_outcome"],
            "Prediction",
            "CalibrationService",
            "prediction_scores",
            "Calibration Console",
            "Penalize miscalibrated prediction confidence.",
            _brier_score,
        ),
        FormulaSpec(
            "reward_score",
            "Reward score",
            "commercial value and learning value minus costs",
            [
                "commercial_value",
                "prediction_accuracy",
                "source_quality",
                "actionability",
                "novelty",
                "timing_advantage",
                "false_positive_cost",
                "uncertainty_penalty",
                "operator_time_cost",
            ],
            "Outcome",
            "RewardPainService",
            "reward_events",
            "Learning Console",
            "Reinforce sources, paths, offers, and actions.",
            _reward_score,
        ),
        FormulaSpec(
            "pain_score",
            "Pain score",
            "avoidable cost, waste, trust damage, and risk",
            [
                "false_positive_cost",
                "capital_wasted",
                "trust_damage",
                "legal_or_reputation_risk",
                "operator_time_cost",
            ],
            "Outcome",
            "RewardPainService",
            "pain_events",
            "Learning Console",
            "Weaken or quarantine harmful pathways.",
            _pain_score,
        ),
        FormulaSpec(
            "graph_weight_update",
            "Graph weight update",
            "current_weight + learning_rate*reward_signal - decay_rate",
            ["current_weight", "learning_rate", "reward_signal", "decay_rate"],
            "GraphEdge",
            "GraphLearningService",
            "graph_edge_updates",
            "Graph Console",
            "Strengthen or weaken relationship topology.",
            _graph_weight_update,
        ),
        FormulaSpec(
            "fractional_kelly_exposure",
            "Fractional Kelly exposure",
            "fraction*((p*b-q)/b)",
            ["win_probability", "payoff_ratio", "fraction", "max_exposure"],
            "Opportunity",
            "CapitalAllocatorService",
            "capital_allocations",
            "Capital Console",
            "Cap risk exposure for opportunities.",
            _fractional_kelly_exposure,
        ),
        FormulaSpec(
            "trust_adjusted_value",
            "Trust-adjusted value",
            "utility - trust risk - reputation risk - legal/access risk",
            [
                "action_expected_utility",
                "trust_damage_risk",
                "reputation_damage_risk",
                "legal_or_access_risk",
            ],
            "CandidateAction",
            "ActionGateService",
            "action_simulations",
            "Approval Inbox",
            "Block, escalate, or approve action simulation.",
            _trust_adjusted_value,
        ),
    ]
    for spec in specs:
        registry.register(spec)
    return registry
