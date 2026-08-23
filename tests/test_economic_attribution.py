from uuid import uuid4

from brain.economic import RevenueAttribution
from brain.economic_attribution import EconomicAttributionService
from brain.economic_runtime import InMemoryEconomicStore


def test_source_action_opportunity_roi_are_distinct_and_persisted() -> None:
    store = InMemoryEconomicStore()
    service = EconomicAttributionService(store)
    attribution = RevenueAttribution(
        transaction_id=uuid4(),
        opportunity_id=uuid4(),
        source_ids=["registry", "marketplace"],
        gross_revenue=20000,
        net_profit=12000,
        operator_hours=6,
        data_compute_cost=500,
        attribution_confidence=0.9,
    )
    sources = service.attribute_sources(
        attribution,
        source_costs={"registry": 100, "marketplace": 400},
    )
    action = service.attribute_action(attribution, action_id=uuid4(), execution_cost=1000)
    opportunity = service.attribute_opportunity(
        attribution,
        total_cost=2000,
        capital_employed=5000,
    )
    assert len(sources) == 2
    assert sum(s.attributed_net_profit for s in sources) == 12000
    assert action.profit_per_operator_hour == 2000
    assert opportunity.roi == 6
    assert opportunity.return_on_capital == 2.4
    assert len(store.list("source_roi")) == 2
    assert len(store.list("action_roi")) == 1
    assert len(store.list("opportunity_roi")) == 1


def test_attribution_confidence_gates_major_learning() -> None:
    service = EconomicAttributionService(InMemoryEconomicStore(), major_learning_threshold=0.7)
    assert service.learning_gate(0.69) == "HOLD"
    assert service.learning_gate(0.7) == "GO"
