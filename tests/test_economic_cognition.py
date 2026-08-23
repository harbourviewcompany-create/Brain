from uuid import uuid4

from brain.economic import (
    CapitalState,
    CounterpartyProfile,
    CounterpartyRole,
    EconomicOpportunity,
    MoneyPath,
    MoneyVerb,
    OpportunityType,
    PaymentModel,
)


def test_economic_opportunity_score_rewards_high_value_low_cost() -> None:
    high = EconomicOpportunity(
        kind=OpportunityType.BROKERAGE,
        entity_id=uuid4(),
        money_path_ids=[uuid4()],
        gross_value=20_000,
        net_value=15_000,
        conversion_probability=0.6,
        urgency=0.9,
        access_advantage=0.8,
        evidence_confidence=0.9,
        repeatability=0.7,
        strategic_compounding_value=0.8,
        required_capital=100,
        required_operator_hours=3,
        legal_reputation_risk=0.1,
        operational_complexity=0.2,
        time_decay=0.2,
    )
    weak = EconomicOpportunity(
        kind=OpportunityType.BROKERAGE,
        entity_id=uuid4(),
        money_path_ids=[uuid4()],
        gross_value=20_000,
        net_value=15_000,
        conversion_probability=0.2,
        urgency=0.3,
        access_advantage=0.2,
        evidence_confidence=0.5,
        repeatability=0.2,
        strategic_compounding_value=0.2,
        required_capital=5_000,
        required_operator_hours=25,
        legal_reputation_risk=1.0,
        operational_complexity=1.0,
        time_decay=1.0,
    )
    assert high.score() > weak.score()


def test_money_path_preserves_invoice_mechanics() -> None:
    buyer = uuid4()
    path = MoneyPath(
        verb=MoneyVerb.INTRODUCE,
        payment_model=PaymentModel.SUCCESS_FEE,
        buyer_entity_id=buyer,
        expected_gross_value=10_000,
        expected_net_value=9_000,
        time_to_cash_days=30,
        conversion_probability=0.4,
        collection_risk=0.1,
        fee_protection_required=True,
    )
    assert path.buyer_entity_id == buyer
    assert path.fee_protection_required is True
    assert path.expected_net_value < path.expected_gross_value


def test_counterparty_profile_can_hold_liquidity_role_and_reachability() -> None:
    profile = CounterpartyProfile(
        entity_id=uuid4(),
        roles={CounterpartyRole.BUYER, CounterpartyRole.INVESTOR},
        needs=["distressed processing assets"],
        budget_estimate=250_000,
        urgency=0.8,
        trust=0.7,
        reachability=0.9,
        decision_authority=1.0,
    )
    assert CounterpartyRole.BUYER in profile.roles
    assert profile.reachability == 0.9


def test_capital_state_never_exposes_negative_deployable_capital() -> None:
    state = CapitalState(available_capital=100, reserved_capital=150)
    assert state.deployable_capital == 0.0
