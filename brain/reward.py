from dataclasses import dataclass

from .domain import Outcome


@dataclass(slots=True)
class RewardWeights:
    value_created: float = 1.0
    prediction_accuracy: float = 0.8
    trust_impact: float = 0.6
    operator_time_cost: float = 0.5
    legal_risk: float = 2.0


class RewardSystem:
    def __init__(self, weights: RewardWeights | None = None):
        self.weights = weights or RewardWeights()

    def score(self, outcome: Outcome) -> float:
        w = self.weights
        return (
            w.value_created * outcome.value_created
            + w.prediction_accuracy * outcome.prediction_accuracy
            + w.trust_impact * outcome.trust_impact
            - w.operator_time_cost * outcome.operator_time_cost
            - w.legal_risk * outcome.legal_risk
        )
