from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .economic import RevenueAttribution
from .economic_runtime import EconomicStore


@dataclass(slots=True)
class SourceROI:
    source_key: str
    attributed_gross_revenue: float
    attributed_net_profit: float
    attributed_cost: float
    attribution_confidence: float
    id: UUID = field(default_factory=uuid4)

    @property
    def roi(self) -> float:
        return self.attributed_net_profit / max(self.attributed_cost, 1.0)


@dataclass(slots=True)
class ActionROI:
    action_id: UUID
    attributed_gross_revenue: float
    attributed_net_profit: float
    operator_hours: float
    execution_cost: float
    attribution_confidence: float
    id: UUID = field(default_factory=uuid4)

    @property
    def profit_per_operator_hour(self) -> float:
        return self.attributed_net_profit / max(self.operator_hours, 0.01)


@dataclass(slots=True)
class OpportunityROI:
    opportunity_id: UUID
    attributed_gross_revenue: float
    attributed_net_profit: float
    total_cost: float
    capital_employed: float
    attribution_confidence: float
    id: UUID = field(default_factory=uuid4)

    @property
    def roi(self) -> float:
        return self.attributed_net_profit / max(self.total_cost, 1.0)

    @property
    def return_on_capital(self) -> float:
        return self.attributed_net_profit / max(self.capital_employed, 1.0)


class EconomicAttributionService:
    """Causal economic attribution with confidence-gated promotion outputs."""

    def __init__(self, store: EconomicStore, *, major_learning_threshold: float = 0.7) -> None:
        self.store = store
        self.major_learning_threshold = major_learning_threshold

    def attribute_sources(
        self,
        attribution: RevenueAttribution,
        *,
        source_costs: dict[str, float] | None = None,
    ) -> list[SourceROI]:
        source_costs = source_costs or {}
        source_ids = list(dict.fromkeys(attribution.source_ids))
        if not source_ids:
            raise ValueError("source_attribution_requires_sources")
        share = 1.0 / len(source_ids)
        records = []
        for source_key in source_ids:
            record = SourceROI(
                source_key=source_key,
                attributed_gross_revenue=attribution.gross_revenue * share,
                attributed_net_profit=attribution.net_profit * share,
                attributed_cost=source_costs.get(source_key, 0.0),
                attribution_confidence=attribution.attribution_confidence,
            )
            self.store.put("source_roi", record.id, record)
            records.append(record)
        return records

    def attribute_action(
        self,
        attribution: RevenueAttribution,
        *,
        action_id: UUID,
        execution_cost: float,
    ) -> ActionROI:
        record = ActionROI(
            action_id=action_id,
            attributed_gross_revenue=attribution.gross_revenue,
            attributed_net_profit=attribution.net_profit,
            operator_hours=attribution.operator_hours,
            execution_cost=execution_cost,
            attribution_confidence=attribution.attribution_confidence,
        )
        self.store.put("action_roi", record.id, record)
        return record

    def attribute_opportunity(
        self,
        attribution: RevenueAttribution,
        *,
        total_cost: float,
        capital_employed: float,
    ) -> OpportunityROI:
        record = OpportunityROI(
            opportunity_id=attribution.opportunity_id,
            attributed_gross_revenue=attribution.gross_revenue,
            attributed_net_profit=attribution.net_profit,
            total_cost=total_cost,
            capital_employed=capital_employed,
            attribution_confidence=attribution.attribution_confidence,
        )
        self.store.put("opportunity_roi", record.id, record)
        return record

    def learning_gate(self, confidence: float) -> str:
        return "GO" if confidence >= self.major_learning_threshold else "HOLD"
