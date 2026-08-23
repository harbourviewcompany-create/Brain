from pathlib import Path
from uuid import uuid4

import pytest

from brain.economic import (
    CounterpartyProfile,
    CounterpartyRole,
    EconomicOpportunity,
    OpportunityType,
    PaymentModel,
    PressureType,
    RevenueAttribution,
    Transaction,
)
from brain.economic_replay import EconomicReplayHarness
from brain.economic_runtime import (
    BusinessModelHypothesis,
    EconomicObjectState,
    EconomicRuntime,
    FeeControl,
    InMemoryEconomicStore,
    SourcePlane,
    SourcePlaneType,
    SourceRightsClass,
    SourceRightsProfile,
)

FIXTURES = Path("tests/fixtures/economic")


def runtime() -> EconomicRuntime:
    return EconomicRuntime(InMemoryEconomicStore())


def test_pressure_requires_evidence_and_decays() -> None:
    service = runtime()
    with pytest.raises(ValueError, match="pressure_requires_evidence"):
        service.infer_pressure(uuid4(), PressureType.CASH, 0.8, 0.8, [])
    pressure = service.infer_pressure(
        uuid4(), PressureType.CASH, 0.8, 0.8, [uuid4()], half_life_days=1
    )
    later = pressure.created_at.replace(day=min(pressure.created_at.day + 1, 28))
    assert service.pressure_effective_magnitude(pressure, later) <= pressure.magnitude


def test_affordance_generation_is_one_to_many() -> None:
    service = runtime()
    affordances = service.generate_affordances(
        uuid4(), [PressureType.EXPANSION], [uuid4()]
    )
    assert len(affordances) >= 3
    assert len({a.verb for a in affordances}) == len(affordances)


def test_money_path_cannot_qualify_without_verified_payer() -> None:
    service = runtime()
    affordance = service.generate_affordances(uuid4(), [PressureType.HIRING], [uuid4()])[0]
    path = service.generate_money_path(
        affordance=affordance,
        payment_model=PaymentModel.RETAINER,
        buyer_entity_id=None,
        gross_value=5000,
        net_value=4500,
        time_to_cash_days=14,
        conversion_probability=0.4,
    )
    with pytest.raises(ValueError, match="verified_payer"):
        service.qualify_money_path(path.id, payer_verified=False)


def test_counterparty_ranking_preserves_explanation() -> None:
    service = runtime()
    strong = CounterpartyProfile(
        entity_id=uuid4(),
        roles={CounterpartyRole.BUYER},
        budget_estimate=100000,
        trust=0.9,
        reachability=0.9,
        decision_authority=0.9,
        urgency=0.8,
    )
    weak = CounterpartyProfile(
        entity_id=uuid4(),
        roles={CounterpartyRole.BUYER},
        budget_estimate=100000,
        trust=0.3,
        reachability=0.2,
        decision_authority=0.4,
        urgency=0.2,
    )
    service.upsert_counterparty(strong, verified=True)
    service.upsert_counterparty(weak, verified=True)
    ranked = service.ranked_counterparties(CounterpartyRole.BUYER)
    assert ranked[0][0].id == strong.id
    assert ranked[0][2]


def _qualified_opportunity(service: EconomicRuntime) -> EconomicOpportunity:
    entity_id = uuid4()
    buyer_id = uuid4()
    affordance = service.generate_affordances(entity_id, [PressureType.INVENTORY], [uuid4()])[0]
    path = service.generate_money_path(
        affordance=affordance,
        payment_model=PaymentModel.SUCCESS_FEE,
        buyer_entity_id=buyer_id,
        gross_value=20000,
        net_value=17000,
        time_to_cash_days=20,
        conversion_probability=0.6,
    )
    service.qualify_money_path(path.id, payer_verified=True)
    opportunity = EconomicOpportunity(
        kind=OpportunityType.BROKERAGE,
        entity_id=entity_id,
        money_path_ids=[path.id],
        gross_value=20000,
        net_value=17000,
        conversion_probability=0.6,
        urgency=0.9,
        access_advantage=0.8,
        evidence_confidence=0.9,
        repeatability=0.7,
        strategic_compounding_value=0.7,
        required_capital=100,
        required_operator_hours=4,
        legal_reputation_risk=0.1,
        operational_complexity=0.2,
        time_decay=0.2,
    )
    service.register_opportunity(opportunity)
    return opportunity


def test_opportunity_score_has_formula_trace_and_portfolio_disposition() -> None:
    service = runtime()
    opportunity = _qualified_opportunity(service)
    decision = service.kill_review(opportunity.id)
    assert opportunity.metadata["formula_run_id"]
    assert service.store.formula_runs
    assert decision.disposition.value in {"act_now", "watch", "build_as_asset"}
    portfolio = service.portfolio()
    surfaced = portfolio.act_now + portfolio.verify_first + portfolio.watch
    assert opportunity.id in surfaced


def test_kill_engine_rejects_no_money_path() -> None:
    service = runtime()
    opportunity = EconomicOpportunity(
        kind=OpportunityType.SERVICE,
        entity_id=uuid4(),
        money_path_ids=[],
        gross_value=1000,
        net_value=900,
        conversion_probability=0.5,
        urgency=0.5,
        access_advantage=0.5,
        evidence_confidence=0.8,
        repeatability=0.5,
        strategic_compounding_value=0.5,
        required_capital=0,
        required_operator_hours=2,
        legal_reputation_risk=0.1,
        operational_complexity=0.1,
    )
    service.register_opportunity(opportunity)
    decision = service.kill_review(opportunity.id)
    assert decision.disposition.value == "kill"
    assert "no_qualified_payer_payment_path" in decision.reasons


def test_transaction_requires_fee_control_and_operator_approval() -> None:
    service = runtime()
    transaction = service.register_transaction(
        Transaction(
            opportunity_id=uuid4(),
            buyer_entity_id=uuid4(),
            seller_entity_id=uuid4(),
            payment_model=PaymentModel.SUCCESS_FEE,
            expected_revenue=10000,
            expected_profit=9000,
            capital_at_risk=50,
            fee_protected=False,
        )
    )
    with pytest.raises(ValueError, match="insufficient_fee"):
        service.approve_transaction_action(transaction.id, operator_approved=True)
    service.set_fee_control(
        FeeControl(
            transaction_id=transaction.id,
            mandate=True,
            introduction_logged=True,
            origination_evidence=True,
            jurisdiction_reviewed=True,
        )
    )
    with pytest.raises(ValueError, match="operator_approval_required"):
        service.approve_transaction_action(transaction.id, operator_approved=False)
    approved = service.approve_transaction_action(transaction.id, operator_approved=True)
    assert approved.status == "approved"


def test_prohibited_source_is_forced_to_hold() -> None:
    service = runtime()
    rights = service.register_source_rights(
        SourceRightsProfile(
            source_key="x",
            rights_class=SourceRightsClass.PROHIBITED,
            jurisdiction="CA",
            permitted_collection=True,
            permitted_storage=True,
            permitted_commercial_use=True,
        )
    )
    assert rights.permitted_collection is False
    source = SourcePlane(
        source_key="x",
        plane=SourcePlaneType.MARKETPLACE,
        jurisdiction="CA",
        rights_profile_id=rights.id,
        refresh_seconds=3600,
        reliability=0.7,
    )
    with pytest.raises(ValueError, match="collection_not_permitted"):
        service.activate_source_plane(source)


def test_sensitive_source_requires_review_notes() -> None:
    service = runtime()
    rights = service.register_source_rights(
        SourceRightsProfile(
            source_key="sensitive",
            rights_class=SourceRightsClass.SCRAPE_SENSITIVE,
            jurisdiction="US",
            permitted_collection=True,
            permitted_storage=True,
            permitted_commercial_use=False,
        )
    )
    source = SourcePlane(
        source_key="sensitive",
        plane=SourcePlaneType.WEB_CHANGE,
        jurisdiction="US",
        rights_profile_id=rights.id,
        refresh_seconds=3600,
        reliability=0.6,
    )
    with pytest.raises(ValueError, match="review_notes"):
        service.activate_source_plane(source)


def test_profit_attribution_gates_major_learning() -> None:
    service = runtime()
    attr = RevenueAttribution(
        transaction_id=uuid4(),
        opportunity_id=uuid4(),
        source_ids=["source-a"],
        gross_revenue=10000,
        net_profit=7000,
        operator_hours=8,
        data_compute_cost=500,
        attribution_confidence=0.6,
    )
    roi = service.attribute_revenue(attr, total_external_cost=500)
    assert roi.net_profit == 7000
    assert service.can_major_learn(attr.attribution_confidence) is False
    assert roi.roi > 0


def test_compounding_requires_repeat_evidence_and_payers() -> None:
    service = runtime()
    weak = service.business_model_hypothesis(
        problem_pattern="one-off",
        solution_pattern="manual intro",
        payer_pattern="seller",
        occurrences=1,
        unique_payers=1,
        expected_net_value=5000,
        resource_estimate=1000,
    )
    strong = service.business_model_hypothesis(
        problem_pattern="repeated distress",
        solution_pattern="buyer matching",
        payer_pattern="seller success fee",
        occurrences=5,
        unique_payers=3,
        expected_net_value=50000,
        resource_estimate=10000,
    )
    assert isinstance(strong, BusinessModelHypothesis)
    assert weak.status is EconomicObjectState.OBSERVED
    assert strong.status is EconomicObjectState.BUILD_CANDIDATE


@pytest.mark.parametrize(
    "fixture_name",
    [
        "economic_distress_pipeline.json",
        "economic_source_rights_hold.json",
        "economic_transaction_hold.json",
        "economic_compounding.json",
    ],
)
def test_economic_fixture_replay_is_deterministic_and_go(fixture_name: str) -> None:
    harness = EconomicReplayHarness()
    first = harness.run(FIXTURES / fixture_name)
    second = harness.run(FIXTURES / fixture_name)
    assert first.passed is True
    assert first.deterministic_signature == second.deterministic_signature


def test_operator_snapshot_exposes_attention_and_control_surfaces() -> None:
    service = runtime()
    opportunity = _qualified_opportunity(service)
    service.kill_review(opportunity.id)
    snapshot = service.operator_snapshot()
    assert set(snapshot) >= {
        "act_now",
        "verify_first",
        "watch",
        "suppressed_count",
        "active_pressures",
        "qualified_money_paths",
        "active_sources",
        "source_roi",
        "transactions",
        "compounding_assets",
    }
