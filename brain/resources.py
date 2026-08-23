from dataclasses import dataclass


@dataclass(slots=True)
class CapabilityInvestment:
    name: str
    cost: float
    expected_intelligence_gain: float
    expected_revenue_gain: float
    reversibility: float
    risk: float

    @property
    def score(self) -> float:
        benefit = self.expected_intelligence_gain + self.expected_revenue_gain + 0.3 * self.reversibility
        return benefit - self.risk - 0.1 * self.cost


class CapitalAllocator:
    def rank(self, investments: list[CapabilityInvestment]) -> list[CapabilityInvestment]:
        return sorted(investments, key=lambda i: i.score, reverse=True)
